# Discovery — Isolamento de processo CLI do Discord Plus (Fix 3: systemd-run --scope)

- **Autor:** Echo (analyst) — fase 1 Discovery
- **Data:** 2026-06-05
- **Projeto:** evonexus-discord-plus (`/home/evonexus/evo-projects/evonexus-discord-plus/`)
- **Problema:** processos `claude`/`openclaude` filhos rodam no cgroup do serviço systemd. Quando um filho estoura memória (ex: pytest 10.5 GB), `MemoryMax=4G` + `OOMPolicy=kill` mata **o serviço inteiro** (Bun server + todas as sessões), não só o processo pesado.
- **Fix proposto:** spawnar o processo Claude via `systemd-run --scope` em um cgroup separado, isolando o OOM-kill ao scope.

> Convenção do projeto: artefato físico deve ficar no git de `go-control-erp`/projeto próprio com symlink no workspace. Este discovery é sobre `evonexus-discord-plus` (repo próprio do usuário, gitignored no EvoNexus) — salvo direto na feature folder conforme a `dev-phases.md`. Se o usuário quiser versioná-lo no repo do discord-plus, criar symlink.

---

## 1. Sumário — Top 3 gaps que bloqueiam o planejamento

1. **[CRÍTICO] `systemd-run --scope` NÃO funciona como user `evonexus` sem `sudo`.** Verificado em runtime:
   - `systemd-run --scope` (system manager) → `Failed to start transient scope unit: Access denied` (precisa root/polkit).
   - `systemd-run --user --scope` → `Failed to connect to bus: No such file or directory` — **não existe user systemd manager**: `loginctl` reporta `User ID 1000 is not logged in or lingering` e `/run/user/1000` não existe.
   - `sudo -n systemd-run --scope -p MemoryMax=2G ...` → **funciona** (RC=0), porque há `/etc/sudoers.d/evonexus: evonexus ALL=(ALL) NOPASSWD: ALL`.
   - **Decisão bloqueante:** o caminho viável hoje é `sudo systemd-run --scope`, OU habilitar lingering (`loginctl enable-linger evonexus`) para ter user manager e usar `--user`. Cada opção tem implicações de segurança/propriedade diferentes. Compass/Apex precisam escolher antes de qualquer código.

2. **[CRÍTICO] Não há contrato definido para "scope foi OOM-killed".** O `runCli` (cli-session-runner.ts:381-420) trata `close` com `code`/`signal`. Com `systemd-run --scope`, o **wrapper** systemd-run vira o processo filho do Bun, não o `claude`. Quando o cgroup do scope é OOM-killed, qual exit code/signal o `systemd-run` propaga? Não está especificado nem testado. Hoje há heurística perigosa (linha 408-411): `exit≠0, sem result, stderr vazio → trata como max_turns`. Um OOM-kill pode cair exatamente nesse caso e ser **silenciosamente reportado como "limite de turnos atingido"** em vez de "ficou sem memória".

3. **[ALTO] Compatibilidade com `PrivateTmp=true` + namespaces do serviço.** O serviço roda com `PrivateTmp=true` e `ProtectHome=read-only` + `ReadWritePaths=...`. Um scope transiente criado pelo **system manager** (via `sudo systemd-run`) roda FORA dos namespaces do serviço — ganha `/tmp` do host (não o privado) e perde as restrições de `ProtectHome`/`ReadWritePaths`. O `claude` pode passar a enxergar/gravar caminhos diferentes dos de hoje. Precisa decidir se o scope deve re-herdar essas proteções (`-p PrivateTmp=true -p ProtectHome=read-only` etc.) ou se isso quebra o acesso a `~/.openclaude`, `~/.claude`, `/home/evonexus/evo-projects`.

---

## 2. Perguntas em aberto (scope / prioridade / restrição)

### Mecanismo de spawn
- Q1. Usar `sudo systemd-run --scope` (system manager) ou habilitar `enable-linger` + `--user`? *(determina segurança, propriedade do cgroup e herança de namespace)*
- Q2. Se `sudo`: aceitamos que o processo Claude rode num scope cujo dono é o **system manager** (PID 1), não o serviço? O scope sobrevive a um restart do serviço (vira órfão controlado pelo systemd) — isso é desejado ou queremos `--scope` morrer junto com o serviço?
- Q3. `--scope` (síncrono, herda fds/stdin/stdout do pai — necessário porque o runner usa `child.stdin.end(prompt)` e lê `stdout`) vs `--service`? **Resposta provável: tem de ser `--scope`** porque o runner depende de stdin/stdout pipes diretos. Confirmar.
- Q4. Nome do unit: usar `--unit=discord-plus-cli-<sessionKey-hash>-<pid>` para rastreabilidade/observabilidade? `--collect` para auto-limpar units falhados?

### Limites de recurso
- Q5. Qual `MemoryMax` por scope? O serviço hoje tem `MemoryMax=4G`. Se cada scope ganha o seu, qual o teto? E o teto agregado (N sessões × scope) não pode derrubar o host.
- Q6. Manter `MemorySwapMax=0` no scope (como no serviço)? Define se OOM vem mais cedo.
- Q7. Definir `OOMScoreAdjust` no scope para que o kernel mate o scope antes do Bun em pressão de memória global do host?

### Sinalização / ciclo de vida
- Q8. Como `terminateChild` (kill de grupo `process.kill(-pid)`) interage com o scope? Matar o `systemd-run` mata o scope inteiro, ou precisamos `systemctl stop <unit>`? *(ver suposição S3)*
- Q9. O timeout de 5min (`DISCORD_SDK_INBOUND_CLI_TIMEOUT_MS=300000`) continua sendo aplicado pelo runner via `setTimeout`+SIGTERM, ou passamos `-p RuntimeMaxSec=300` ao scope para o systemd matar? (Dois mecanismos podem colidir.)

### UX / Observabilidade
- Q10. Quando o scope é OOM-killed, **o usuário do Discord é notificado**? Com qual mensagem? ("Sua execução foi encerrada por uso excessivo de memória (>NG).") Hoje a mensagem genérica é `CLI_OPERATIONAL_ERROR`.
- Q11. A sessão (`SupervisedSession`) deve ser marcada `failed` e a próxima mensagem recria, ou marcamos algo específico ("killed_oom") para diferenciar de falha normal? `attachHandle` (session-supervisor.ts:158-166) seta `failed` em `code !== 0` — OOM cairia em `failed`, perdendo a causa.
- Q12. `listActiveClaudeProcesses` (claude-process-inspector.ts) usa `ps` filtrando por linha de comando contendo ` -p`. Com `systemd-run --scope ... claude -p ...` a linha de comando ainda casa? O regex `CLAUDE_BINARY_RE` precisa continuar funcionando para `/session status` mostrar processos ativos.

---

## 3. Guardrails não definidos (o que não está limitado)

- **Teto agregado de memória.** Hoje 1 teto global de 4G mata tudo. Com scopes isolados, N execuções concorrentes podem somar muito mais que 4G e pressionar o **host** (LXC no Proxmox — ver memória de infra). Sem um teto agregado, trocamos "derruba o serviço" por "derruba o container".
- **Número de scopes simultâneos.** `SessionSupervisor.maxSessions` limita sessões, mas não há limite explícito de scopes systemd-run vivos. Scope órfão (se sobreviver a restart) pode acumular.
- **Limpeza de units falhados.** Sem `--collect`, units de scope que falham ficam em estado `failed` no systemd até `systemctl reset-failed`. Pode poluir `systemctl list-units`.
- **Privilégio do sudo.** `NOPASSWD: ALL` é amplo demais. Se formos por sudo, o guardrail correto é restringir a um comando específico em sudoers (ex: só `systemd-run --scope ...`), não `ALL`.
- **Timeout duplo.** Runner `setTimeout` (5min) + possível `RuntimeMaxSec` no scope — qual ganha, e o que o usuário vê em cada caso.

---

## 4. Suposições ocultas (podem ser inválidas com a mudança)

- **S1. `detached: process.platform !== 'win32'` (cli-session-runner.ts:340) cria um grupo de processo cujo líder é `child.pid`.** Com `systemd-run --scope`, `child.pid` passa a ser o PID do **`systemd-run`/`sudo`**, não do `claude`. `process.kill(-child.pid)` mata o grupo do wrapper — mas o `claude` agora vive no **cgroup do scope**, que pode ter PIDs em outro grupo de processo. **A suposição "kill do grupo mata os netos" deixa de valer; o caminho correto vira `systemctl stop <scope-unit>` ou `systemd-run` propagando o sinal.**

- **S2. `minimalCliEnv` (linhas 44-51) repassa só PATH/HOME/USER/LANG/LC_ALL/OPENAI_MODEL/DASHBOARD_API_TOKEN via `env:` do spawn.** `systemd-run` por padrão **não herda** o environment do chamador para o processo do scope — precisa de `--setenv=KEY=VALUE` por variável (ou `-E`). Se passarmos o env só no `spawn({env})`, ele chega ao `systemd-run` mas **não necessariamente ao processo dentro do scope**. Risco concreto: `claude` dentro do scope perde `PATH`/`HOME`/`DASHBOARD_API_TOKEN` e falha no startup. Precisa mapear cada var de `minimalCliEnv` para `--setenv`.

- **S3. O runner assume pipes diretos de stdin/stdout/stderr com o filho** (`child.stdin.end()`, `child.stdout.on('data')`). `systemd-run --scope` herda os fds do chamador (ok), mas `systemd-run --service`/`--pipe` se comporta diferente. Confirma que `--scope` preserva o pipe stream-json. Se usado `sudo` no meio, `sudo` também precisa preservar stdin (`sudo` pode fechar stdin sem `-S`/tty handling adequado).

- **S4. `child.on('close', code/signal)` reflete o exit do `claude`.** Com wrapper, o `code`/`signal` passam a ser do `systemd-run`/`sudo`. `systemd-run --scope` normalmente propaga o exit status do comando interno, **mas em OOM-kill o systemd reporta via journal/`systemctl show`**, não necessariamente como signal no exit do `systemd-run`. A heurística de `max_turns` (linhas 408-411) vira fonte de bug.

- **S5. `cwd` e `--add-dir`** (linhas 220-224) assumem que o processo enxerga o filesystem do serviço (com `ProtectHome=read-only` + `ReadWritePaths`). Scope no system manager não tem esses namespaces → enxerga o FS real do host. Pode mudar comportamento de escrita (ex: pytest gravando em paths antes protegidos).

- **S6. `PrivateTmp=true`** dá ao serviço um `/tmp` privado. Hoje o `claude` filho compartilha esse `/tmp` privado. No scope (system manager), o `claude` ganha o `/tmp` do host. Qualquer estado em `/tmp` (locks, sockets, arquivos temporários do openclaude) muda de localização — possível regressão silenciosa.

- **S7. `executionRegistry.setChild(sessionKey, child)`** guarda o `ChildProcessWithoutNullStreams` para `/session cancel`. Se `child` agora é o `systemd-run`, o `cancel()` mata o wrapper — confirmar que isso encerra o scope (depende de S1/S3).

---

## 5. Restrições técnicas

- **Ambiente verificado (2026-06-05, host do LXC):**
  - `systemd 255` — `systemd-run` em `/usr/bin/systemd-run` (existe).
  - `evonexus`: uid=1000, grupos `sudo`, `docker`; `/etc/sudoers.d/evonexus: NOPASSWD: ALL`.
  - **Sem user manager:** `enable-linger` desligado, `/run/user/1000` ausente → `systemd-run --user` inviável sem habilitar lingering.
  - `systemd-run --scope` (system) exige privilégio → só via `sudo` (disponível por NOPASSWD).
- **Unit do serviço:** `Type=simple`, `ExecStart=/bin/bash -lc 'exec /usr/bin/tail -f /dev/null | /usr/local/bin/bun server.ts'`, `MemoryMax=4G`, `MemorySwapMax=0`, `OOMPolicy=kill`, `PrivateTmp=true`, `ProtectSystem=full`, `ProtectHome=read-only`, `ReadWritePaths` inclui `~/.openclaude ~/.claude /home/evonexus/evo-projects /home/evonexus/evo-nexus`.
  - Observação: o `ExecStart` é um pipe `tail -f /dev/null | bun` — só o `bun` é relevante. O `OOMPolicy=kill` mata o cgroup do serviço inteiro em OOM de qualquer membro — **esta é a causa-raiz** que o Fix 3 ataca.
- **Discord oficial protegido:** regra do CLAUDE.md — diagnóstico restrito a `evonexus-discord-plus` (este projeto está no escopo permitido). OK.
- **Para `--user` funcionar** seria preciso: `loginctl enable-linger evonexus` (cria `/run/user/1000` persistente) + o serviço exportar `XDG_RUNTIME_DIR` e `DBUS_SESSION_BUS_ADDRESS` ao chamar `systemd-run --user`. Mais limpo de segurança (sem sudo), mas adiciona dependência de infra. **Recomendado consultar @custom-sysops** (regra de memória: infra/systemd/LXC → sysops).

---

## 6. Riscos da migração

| # | Risco | Severidade | Mitigação sugerida |
|---|-------|-----------|--------------------|
| R1 | `sudo systemd-run` com `NOPASSWD: ALL` amplia superfície: qualquer bug no monta-comando vira execução arbitrária como root. | Alta | Restringir sudoers a um único comando systemd-run parametrizado; validar/escapar `--unit` e args. |
| R2 | OOM-kill do scope confundido com `max_turns` (heurística linhas 408-411) → usuário recebe mensagem errada e não sabe que faltou memória. | Alta | Distinguir via `systemctl show <unit> -p Result` (`oom-kill`) ou exit code 137; só então classificar. |
| R3 | Env não chega ao processo do scope (S2) → `claude` falha no startup; toda execução quebra após a migração. | Alta | Mapear `minimalCliEnv` para `--setenv` explícito; testar com user master `--tools all`. |
| R4 | Perda das proteções de namespace (`PrivateTmp`, `ProtectHome`) no scope → comportamento de FS diferente, possível escrita indevida no host. | Média | Re-aplicar `-p PrivateTmp=true -p ProtectHome=read-only -p ReadWritePaths=...` no scope; testar acesso a `~/.openclaude`. |
| R5 | Scope órfão sobrevive a restart do serviço / units `failed` acumulam. | Média | `--collect`; janitor que faz `systemctl reset-failed` de units `discord-plus-cli-*`. |
| R6 | Sem teto agregado, N scopes somam memória e derrubam o **LXC** (troca de problema). | Média | Definir `MemoryMax` por scope baixo + `maxSessions` coerente; ou um slice pai `discord-plus.slice` com teto agregado. |
| R7 | `child.pid` agora é o wrapper → `terminateChild`/`/session cancel`/timeout não matam o `claude` real (S1, S7). | Média | Encerrar via `systemctl stop <unit>` ou garantir propagação de sinal pelo systemd-run; cobrir com teste. |
| R8 | `listActiveClaudeProcesses` (`ps ... ` casando ` -p`) deixa de casar com `systemd-run ... claude -p` → `/session status` para de listar. | Baixa | Ajustar regex/dedupe; teste de fumaça. |
| R9 | `sudo` no caminho quente adiciona latência e mais um processo por execução. | Baixa | Aceitável; medir. |

---

## 7. Critérios de aceite faltando (por requisito)

O Fix 3 ainda não tem AC testáveis. Sugestão para Compass formalizar (Given/When/Then):

- **AC-1 (isolamento):** Dado um processo Claude que aloca >MemoryMax do scope, Quando ele é OOM-killed, Então **o serviço Bun continua rodando** (PID inalterado) e as demais sessões respondem normalmente. *(Pass/fail objetivo: `systemctl is-active` permanece `active`; outra sessão recebe resposta.)*
- **AC-2 (causa correta):** Dado um OOM-kill de scope, Quando o runner reporta ao usuário, Então a mensagem indica **falta de memória**, não `max_turns` nem erro genérico.
- **AC-3 (env intacto):** Dado o user master (`--tools all --dangerously-skip-permissions`), Quando uma execução roda no scope, Então `claude` inicia com `PATH/HOME/DASHBOARD_API_TOKEN` corretos e a execução de uma ferramenta (ex: leitura de arquivo) funciona.
- **AC-4 (cancel/timeout):** Dado `/session cancel` ou timeout de 5min, Quando acionado, Então o `claude` E todos os netos (ex: pytest) são encerrados — nenhum processo órfão remanesce (`ps` limpo).
- **AC-5 (limpeza):** Dado um scope que terminou (sucesso ou falha), Quando consultado, Então não restam units `failed` acumulando em `systemctl list-units`.
- **AC-6 (status):** `/session status` continua listando processos Claude ativos via inspector.

---

## 8. Edge cases (priorizados por impacto)

1. **[Alto] OOM-kill exatamente quando stdout está vazio** → casa a heurística `max_turns` (linhas 408-411). Bug de classificação.
2. **[Alto] `sudo` indisponível/sudoers alterado em runtime** → toda execução falha. Precisa fallback ou health-check no startup.
3. **[Alto] Env não propagado (S2)** → falha 100% silenciosa pós-deploy. Validar no smoke test antes de cortar.
4. **[Médio] Restart do serviço durante execução** → scope órfão (system manager) continua vivo consumindo memória; o registry em memória do Bun perde a referência.
5. **[Médio] Concorrência: várias sessões pesadas** → soma de scopes excede memória do LXC.
6. **[Médio] `--unit` colidindo** se nome não for único (mesma sessão re-disparando rápido) → `systemd-run` falha com "unit already exists".
7. **[Baixo] Caracteres especiais no sessionKey** ao compor `--unit` → nome inválido para systemd (precisa sanitizar; usar hash).
8. **[Baixo] Scope em LXC** — confirmar que o cgroup v2 do container permite scopes filhos (delegation). Em LXC unprivileged pode haver restrição de cgroup delegation.

---

## 9. Perguntas em aberto (formato para open-questions.md)

- [ ] **[discord-plus-cli-isolation]** Mecanismo de spawn: `sudo systemd-run --scope` (system) vs habilitar `enable-linger` + `--user`? — bloqueia o plano. (Owner: Eduardo + @custom-sysops)
- [ ] **[discord-plus-cli-isolation]** Como detectar/classificar OOM-kill do scope vs `max_turns` vs falha normal? (Owner: Compass/Apex)
- [ ] **[discord-plus-cli-isolation]** Re-aplicar namespaces (PrivateTmp/ProtectHome/ReadWritePaths) no scope ou aceitar FS do host? (Owner: @custom-sysops)
- [ ] **[discord-plus-cli-isolation]** Teto de memória por scope e teto agregado para não derrubar o LXC? (Owner: Eduardo)
- [ ] **[discord-plus-cli-isolation]** Como repassar env (`minimalCliEnv`) para dentro do scope — `--setenv` por var? (Owner: Apex/Bolt)
- [ ] **[discord-plus-cli-isolation]** Encerramento: matar wrapper basta ou precisa `systemctl stop <unit>`? Como cancel/timeout matam os netos (pytest)? (Owner: Apex)
- [ ] **[discord-plus-cli-isolation]** Restringir sudoers de `NOPASSWD: ALL` para só o comando systemd-run específico? (Owner: @custom-sysops — segurança)
- [ ] **[discord-plus-cli-isolation]** Usuário do Discord é notificado em OOM-kill? Qual mensagem? (Owner: Eduardo/Nova)

---

## 10. Próximo passo recomendado

1. **@custom-sysops** primeiro — decisão de infra é o bloqueador #1: sudo-vs-linger, namespaces no scope, cgroup delegation no LXC, e endurecimento do sudoers. (Regra de memória: infra/systemd/LXC → sysops.)
2. Depois **@compass-planner** com este discovery para PRD + plano, fechando as 8 perguntas em aberto.
3. **@apex-architect** para o ponto de integração runner↔systemd-run (S1-S7: pid do wrapper, propagação de sinal, env via `--setenv`, classificação de OOM).

**Arquivo:** `/home/evonexus/evo-nexus/workspace/development/features/discord-plus-cli-process-isolation/[C]discovery-discord-plus-cli-process-isolation.md`
