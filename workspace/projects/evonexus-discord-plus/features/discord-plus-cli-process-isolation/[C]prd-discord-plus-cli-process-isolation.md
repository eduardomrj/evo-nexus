# PRD — Isolamento de processo CLI do Discord Plus (Fix 3: cgroup separado via systemd-run)

- **Autor:** Compass (planner) — fase 2 Planning
- **Data:** 2026-06-05
- **Projeto:** evonexus-discord-plus (`/home/evonexus/evo-projects/evonexus-discord-plus/`)
- **Entrada:** `[C]discovery-discord-plus-cli-process-isolation.md` (Echo, 2026-06-05)
- **Fase anterior:** Discovery concluída — 8 perguntas em aberto, 9 riscos, 6 ACs sugeridos.

> Convenção: artefato físico no repo próprio do usuário (gitignored no EvoNexus). Salvo direto na feature folder do EvoNexus conforme `dev-phases.md`. Se o Eduardo quiser versionar no repo do discord-plus, criar symlink.

---

## 1. Problema

O serviço `evonexus-discord-plus.service` (Bun/TypeScript, `Type=simple`, `MemoryMax=4G`, `OOMPolicy=kill`) spawna processos `claude`/`openclaude -p` que rodam **dentro do cgroup do serviço**. Quando um processo filho — ou um neto, ex: `pytest` rodando dentro do Claude com 10,5 GB — estoura `MemoryMax=4G`, o `OOMPolicy=kill` mata o **cgroup inteiro**: o Bun server e **todas as sessões ativas** caem junto. O `Restart=on-failure` reergue o serviço, mas todo o estado em memória (sessões supervisionadas, execução em curso, registry) é perdido.

**Causa-raiz:** todos os processos compartilham o mesmo limite de memória e a mesma política de OOM-kill por cgroup.

## 2. Objetivo

Spawnar cada processo Claude em um **cgroup separado** (scope transiente via `systemd-run --scope`), com seu próprio `MemoryMax`. Em OOM, somente o scope morre; o Bun server e as demais sessões sobrevivem.

**Resultado mensurável:** `systemctl is-active evonexus-discord-plus` permanece `active` durante e após um OOM-kill de uma execução Claude pesada; outra sessão concorrente continua respondendo.

## 3. Fixes já aplicados (NÃO reverter)

- Timeout de 5 min (`DISCORD_SDK_INBOUND_CLI_TIMEOUT_MS=300000` no `.env`).
- `MemoryMax=4G` no unit do systemd.

Fix 3 (este PRD) é **complementar**, não substitui os anteriores.

## 4. Decisões a tomar (resolver antes/durante o plano)

| # | Decisão | Opções | Recomendação Compass | Owner |
|---|---------|--------|----------------------|-------|
| D1 | Mecanismo de spawn | (a) `sudo systemd-run --scope` (system manager); (b) `loginctl enable-linger` + `systemd-run --user --scope` | **(b) linger + `--user`** — evita `sudo` no caminho quente, scope é dono do user `evonexus`, morre com a sessão/host de forma previsível, sem ampliar superfície root. (a) só se sysops vetar linger. | Eduardo + @custom-sysops |
| D2 | Naming do unit | `--unit=dplus-cli-<hash>` único por execução | Hash de `sessionKey + startedAt + pid`; `--collect` para auto-limpar units falhados | @apex-architect |
| D3 | Passagem de env | (a) só `spawn({env})`; (b) `--setenv=K=V` por var do `minimalCliEnv` | **(b)** — `systemd-run` não herda env do chamador para dentro do scope; cada var precisa de `--setenv` explícito | @apex-architect / @bolt-executor |
| D4 | Estratégia de kill (cancel/timeout) | (a) `process.kill(-pid)`; (b) `systemctl --user stop <unit>`; (c) sinal propagado pelo systemd-run | **(b) `systemctl stop <unit>`** como caminho primário (mata o cgroup inteiro = Claude + netos); fallback (a) para ambiente de teste sem systemd | @apex-architect |
| D5 | Teto de memória por scope + agregado | `MemoryMax` por scope; teto agregado via slice pai `dplus.slice` | `MemoryMax` por scope baixo (sugestão 6G — acima dos 4G atuais, configurável via env) + `maxSessions` coerente; slice pai opcional na v2 | Eduardo + @custom-sysops |
| D6 | Re-herdar namespaces (`PrivateTmp`/`ProtectHome`/`ReadWritePaths`) no scope | (a) re-aplicar via `-p`; (b) aceitar FS do host | `--user` herda contexto do usuário; validar acesso a `~/.openclaude`/`~/.claude` no smoke. Se sudo/system manager: re-aplicar `-p ReadWritePaths=...` | @custom-sysops |
| D7 | UX em OOM-kill | Mensagem específica de falta de memória | Mensagem dedicada `formatOomKilledReply()` distinta de `max_turns` e de falha genérica | Eduardo / @nova-product |

> **D1 é o bloqueador #1.** O plano assume D1=(b) linger+`--user` como caminho-base e trata sudo como fallback no Step 1. Confirmar com sysops antes do Step 2.

## 5. User stories

- **US-1 (operador):** como Eduardo, quero que uma execução Claude que estoure memória **não derrube** o bot inteiro, para que outras sessões/usuários não percam contexto.
- **US-2 (usuário Discord):** como usuário, quando minha execução for encerrada por falta de memória, quero **saber que foi memória** (não "limite de passos" nem erro genérico), para entender que devo reduzir o escopo do pedido.
- **US-3 (operador):** como Eduardo, quero que `/session cancel` e o timeout de 5 min continuem matando o Claude **e todos os netos** (ex: pytest), sem deixar processos órfãos consumindo memória.
- **US-4 (operador):** como Eduardo, não quero scopes/units órfãos acumulando em `systemctl list-units` após execuções terminadas.

## 6. Acceptance criteria (Given/When/Then)

### AC-1 — Isolamento (cgroup separado)
- **Given** uma execução Claude rodando em um scope systemd com `MemoryMax` próprio
- **When** o processo (ou um neto, ex: pytest) aloca acima do `MemoryMax` do scope e é OOM-killed
- **Then** `systemctl is-active evonexus-discord-plus` permanece `active` (PID do Bun inalterado) **e** uma segunda sessão concorrente recebe resposta normal.
- *Evidência:* `systemctl show -p MainPID` antes/depois idêntico; log de OOM aparece em `journalctl` referenciando o **scope**, não o serviço.

### AC-2 — Causa correta (OOM ≠ max_turns ≠ genérico)
- **Given** um scope encerrado por OOM-kill (`Result=oom-kill` e/ou exit code 137 / signal SIGKILL)
- **When** o runner classifica o encerramento
- **Then** ele reporta **falta de memória** (código tipado, ex: `oom_killed`) e **nunca** cai na heurística de `max_turns` (cli-session-runner.ts:408-411).
- *Evidência:* teste cobrindo o cenário "exit≠0 + stdout vazio + stderr vazio + scope OOM" → classificado como `oom_killed`, não `max_turns_reached`.

### AC-3 — Env intacto dentro do scope
- **Given** o user master (`--tools all --permission-mode bypassPermissions --dangerously-skip-permissions`)
- **When** uma execução roda dentro do scope
- **Then** `claude` inicia com `PATH`, `HOME`, `USER`, `LANG`, `LC_ALL`, `OPENAI_MODEL`, `DASHBOARD_API_TOKEN` corretos (os mesmos de `minimalCliEnv`) e a execução de uma ferramenta (ex: leitura de arquivo) funciona.
- *Evidência:* smoke test do user master roda uma ferramenta com sucesso; nenhuma var ausente.

### AC-4 — Cancel e timeout matam o scope inteiro
- **Given** uma execução ativa no scope com um neto (ex: pytest) rodando
- **When** o usuário aciona `/session cancel` **ou** o timeout de 5 min dispara
- **Then** o `claude` **e todos os netos** são encerrados (cgroup do scope esvaziado) e **nenhum processo órfão** permanece.
- *Evidência:* `ps` sem processos remanescentes da execução após cancel/timeout; `systemctl show <unit>` reporta unit inativo/coletado.

### AC-5 — Limpeza de scopes/units
- **Given** um scope que terminou (sucesso, falha ou OOM)
- **When** consultado
- **Then** não restam units `failed` acumulando em `systemctl list-units` (auto-`--collect` ou reset-failed).
- *Evidência:* após N execuções (sucesso + falha + OOM), `systemctl list-units 'dplus-cli-*'` retorna vazio.

### AC-6 — `/session status` continua listando processos
- **Given** uma execução Claude ativa dentro de um scope
- **When** o usuário roda `/session status`
- **Then** o inspector (`listActiveClaudeProcesses`) ainda lista o processo Claude ativo.
- *Evidência:* `ps -eo pid,etimes,args` casa o regex mesmo com `systemd-run ... claude -p ...` no command line; teste de unidade do regex atualizado.

### AC-7 — UX de OOM
- **Given** uma execução encerrada por OOM
- **When** o dispatcher notifica o usuário
- **Then** a mensagem indica explicitamente **falta de memória** e orienta reduzir o escopo (ex: "Sua execução foi encerrada por uso excessivo de memória. Tente uma tarefa menor.").
- *Evidência:* `notifySessionError` mapeia `code === 'oom_killed'` para `formatOomKilledReply()`.

## 7. Riscos e mitigações

| # | Risco | Sev | Mitigação |
|---|-------|-----|-----------|
| R1 | `sudo NOPASSWD: ALL` amplia superfície root (se D1=sudo) | Alta | Preferir D1=(b) linger+`--user` (sem sudo). Se sudo: restringir sudoers a um único comando systemd-run, escapar/validar args |
| R2 | OOM-kill confundido com `max_turns` (heurística :408-411) | Alta | Classificar OOM via `systemctl show <unit> -p Result` (`oom-kill`) **ou** exit 137/SIGKILL **antes** da heurística de max_turns (AC-2) |
| R3 | Env não chega ao scope → falha 100% silenciosa pós-deploy | Alta | `--setenv` explícito por var (D3); validar no smoke (AC-3) antes de cortar |
| R4 | `child.pid` vira o PID do wrapper (`systemd-run`/`sudo`) → kill não alcança os netos | Média | Kill via `systemctl stop <unit>` (D4); cobrir com teste (AC-4) |
| R5 | Scope órfão sobrevive a restart do serviço / units `failed` acumulam | Média | `--collect`; janitor opcional de `systemctl reset-failed` de `dplus-cli-*` (AC-5) |
| R6 | Sem teto agregado, N scopes somam memória e derrubam o **LXC** | Média | `MemoryMax` por scope + `maxSessions` coerente (D5); slice pai na v2 |
| R7 | Perda de namespaces (`PrivateTmp`/`ProtectHome`) muda comportamento de FS | Média | `--user` herda contexto do usuário; validar `~/.openclaude`/`~/.claude` no smoke; re-aplicar `-p` se sudo (D6) |
| R8 | `listActiveClaudeProcesses` deixa de casar com `systemd-run ... claude -p` | Baixa | Ajustar regex/dedupe + teste (AC-6) |
| R9 | Timeout duplo (runner setTimeout 5min vs `RuntimeMaxSec` no scope) colidem | Baixa | Manter timeout no runner (já existe); **não** adicionar `RuntimeMaxSec` na v1 para evitar colisão |
| R10 | LXC unprivileged pode restringir cgroup delegation de scopes filhos | Média | Validar no Step 1 (sysops) antes de qualquer código; é pré-requisito |

## 8. Dependências

- **Infra (@custom-sysops — bloqueante):** decisão D1 (linger vs sudo), validação de cgroup delegation no LXC (R10), namespaces no scope (D6), endurecimento do sudoers se D1=sudo. Regra de memória: infra/systemd/LXC → sysops.
- **Código (@apex-architect + @bolt-executor):** `cli-session-runner.ts` (spawn, classificação de exit, kill), `claude-process-inspector.ts` (regex), `gateway-dispatcher.ts` (mensagem OOM), `session-execution-registry.ts` (referência ao scope para kill).
- **Stack:** TypeScript + Bun; testes via `bun test`; padrão de teste `FakeChild extends EventEmitter` (ver memória [[discord-plus-max-turns]]).

## 9. Fora de escopo

- Auto-continuação após OOM ou max_turns (decisão futura do Eduardo).
- Slice pai `dplus.slice` com teto agregado de memória (candidato v2; v1 usa `MemoryMax` por scope + `maxSessions`).
- `RuntimeMaxSec` no scope (mantém o timeout existente no runner para evitar colisão — R9).
- Reescrita do mecanismo de sessão/registry; mudança é cirúrgica no ponto de spawn.
- Tratamento de OOM global do **host/LXC** (mitigado por D5, não eliminado).
- Não tocar no Discord oficial nem em qualquer runtime fora de `evonexus-discord-plus` (regra CLAUDE.md).

## 10. Perguntas em aberto

Ver `## Open Questions` do plano e `[C]open-questions.md`. A decisão D1 (linger vs sudo) é o bloqueador que deve ser fechado por Eduardo + sysops no Step 1.
