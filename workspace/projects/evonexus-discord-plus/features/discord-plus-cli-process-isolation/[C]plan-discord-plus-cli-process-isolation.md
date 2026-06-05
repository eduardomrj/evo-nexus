# Plano — Isolamento de processo CLI do Discord Plus (Fix 3: systemd-run --scope)

- **Autor:** Compass (planner) — fase 2 Planning
- **Data:** 2026-06-05
- **PRD:** `[C]prd-discord-plus-cli-process-isolation.md`
- **Discovery:** `[C]discovery-discord-plus-cli-process-isolation.md`
- **Projeto:** evonexus-discord-plus (`/home/evonexus/evo-projects/evonexus-discord-plus/`)

## Contexto

OOM-kill de um processo Claude filho (ou neto, ex: pytest 10,5 GB) derruba o serviço inteiro porque todos rodam no cgroup do `evonexus-discord-plus.service` (`MemoryMax=4G`, `OOMPolicy=kill`). Este plano isola cada execução Claude em um cgroup separado (scope systemd) com `MemoryMax` próprio, para que o OOM mate só o scope e o Bun sobreviva.

## Objetivos (testáveis)

1. Processo Claude roda em cgroup separado do serviço (AC-1).
2. OOM-kill do Claude **não** derruba o Bun nem outras sessões (AC-1).
3. OOM classificado como falta de memória, nunca como `max_turns` (AC-2).
4. Env (`minimalCliEnv`) chega íntegro ao processo dentro do scope (AC-3).
5. `/session cancel` e timeout matam Claude + netos via `systemctl stop <unit>` (AC-4).
6. Sem scopes/units órfãos acumulando (AC-5).
7. `/session status` continua listando processos (AC-6); UX de OOM dedicada (AC-7).

## Guardrails

**Must have:**
- Mudança cirúrgica no ponto de spawn de `cli-session-runner.ts` — não reescrever sessão/registry.
- Manter os fixes anteriores (timeout 5 min no runner; `MemoryMax` do serviço).
- Classificação de OOM **antes** da heurística de `max_turns`.
- Testes em `bun test` cobrindo cada AC; padrão `FakeChild extends EventEmitter` (ver [[discord-plus-max-turns]]).

**Must NOT have:**
- Auto-continuação após OOM (fora de escopo).
- `RuntimeMaxSec` no scope (colide com o timeout do runner — R9).
- `sudo NOPASSWD: ALL` no caminho quente sem endurecimento (preferir linger+`--user`).
- Tocar Discord oficial ou qualquer runtime fora de `evonexus-discord-plus`.
- Slice pai com teto agregado (v2).

---

## Steps

### Step 1 — [infra] Decidir mecanismo de spawn e validar cgroup no LXC
- **Tipo:** Infra / decisão (bloqueante)
- **Agente:** @custom-sysops (+ Eduardo para D1/D5)
- **Descrição:** Fechar D1 (linger+`--user` vs `sudo systemd-run`). Recomendação: habilitar `loginctl enable-linger evonexus`, garantir `/run/user/1000` + `XDG_RUNTIME_DIR`/`DBUS_SESSION_BUS_ADDRESS` exportados ao serviço, e validar que o LXC unprivileged permite **cgroup delegation** para scopes filhos do user manager (R10). Definir `MemoryMax` por scope (sugestão 6G, via env `DISCORD_CLI_SCOPE_MEMORY_MAX`) e `maxSessions` coerente (D5). Se linger inviável: endurecer sudoers para um único comando `systemd-run --scope` parametrizado (D1 fallback, R1) e mapear re-aplicação de namespaces (`ReadWritePaths`) no scope (D6).
- **Critério de saída:** mecanismo escolhido e provado em runtime (`systemd-run --user --scope -p MemoryMax=... true` retorna RC=0 OU caminho sudo endurecido provado); `MemoryMax` por scope e `maxSessions` definidos; namespaces/FS validados (acesso a `~/.openclaude`, `~/.claude`, `/home/evonexus/evo-projects`). Decisões registradas no PRD §4.

### Step 2 — [arch] Definir contrato runner↔systemd-run
- **Tipo:** Solutioning (ADR curto)
- **Agente:** @apex-architect
- **Descrição:** Com o mecanismo de Step 1, especificar: (a) composição do comando wrapper (`systemd-run --user --scope --unit=dplus-cli-<hash> --collect -p MemoryMax=... --setenv=K=V ... -- claude -p ...`), preservando pipes stdin/stdout (S3) — `--scope` herda fds; (b) naming/hash do `--unit` único por execução (D2, sanitizar sessionKey, edge case de colisão); (c) detecção de OOM: ordem de checagem `systemctl show <unit> -p Result` (`oom-kill`) → exit 137 / SIGKILL → só então heurística max_turns (D3/R2); (d) estratégia de kill via `systemctl --user stop <unit>` com fallback `process.kill(-pid)` em ambiente sem systemd (D4/S1/S7); (e) lista exata de vars `minimalCliEnv` → `--setenv` (S2). Avaliar como obter o unit name de volta para classificar/kill (guardar no registry junto ao child).
- **Critério de saída:** ADR `[C]architecture-discord-plus-cli-process-isolation.md` com o contrato dos 5 pontos acima; pontos S1–S7 do discovery endereçados ou explicitamente deferidos.

### Step 3 — [code] Spawn no scope + passagem de env
- **Tipo:** Build
- **Agente:** @bolt-executor
- **Descrição:** Em `cli-session-runner.ts`: introduzir um wrapper de spawn (feature-flag via env, ex: `DISCORD_CLI_SCOPE_ISOLATION=1`, default ligado em prod) que envelopa `command`/`args` com `systemd-run --user --scope --unit=<hash> --collect -p MemoryMax=$DISCORD_CLI_SCOPE_MEMORY_MAX --setenv=...` conforme o ADR. Mapear cada var de `minimalCliEnv` (PATH/HOME/USER/LANG/LC_ALL/OPENAI_MODEL/DASHBOARD_API_TOKEN) para `--setenv` (S2/AC-3). Guardar o `<unit>` resolvido no `executionRegistry` junto ao child para uso no kill/classificação. Quando a flag estiver off, comportamento atual (spawn direto) — para testes e fallback.
- **Critério de saída:** `claude -p` roda dentro de um scope nomeado; env chega ao processo (verificável por smoke do user master); flag off preserva o caminho antigo. `bun test` existente verde.

### Step 4 — [code] Classificação OOM vs max_turns + kill via systemctl
- **Tipo:** Build
- **Agente:** @bolt-executor
- **Descrição:** (a) No `close` handler (cli-session-runner.ts:385-420), **antes** da heurística de max_turns (:408-411), checar OOM: consultar `systemctl --user show <unit> -p Result` (`Result=oom-kill`) e/ou exit code 137 / signal `SIGKILL`; se OOM, rejeitar com erro tipado `code='oom_killed'` (constante `CLI_OOM_CODE`). (b) Reescrever `terminateChild`/`cancelRunning`/`stop`/timeout para, quando houver `<unit>` associado, encerrar via `systemctl --user stop <unit>` (mata o cgroup = Claude + netos), com fallback `process.kill(-pid)` quando sem unit (testes) (D4/S1/S7/AC-4). (c) Garantir `--collect` ou `systemctl reset-failed` para não acumular units falhados (AC-5).
- **Critério de saída:** OOM classificado como `oom_killed` (nunca `max_turns`); cancel/timeout encerram o scope inteiro; sem units `failed` remanescentes.

### Step 5 — [code] Inspector regex + UX de OOM no dispatcher
- **Tipo:** Build
- **Agente:** @bolt-executor
- **Descrição:** (a) `claude-process-inspector.ts`: ajustar `CLAUDE_BINARY_RE`/filtros para continuar casando `systemd-run ... claude -p ...` (e dedupe não contar o wrapper duas vezes) (AC-6/R8). (b) `gateway-dispatcher.ts`: adicionar `formatOomKilledReply()` (mensagem dedicada de falta de memória, orienta reduzir escopo) e mapear `code === 'oom_killed'` em `notifySessionError` (:183-199), distinto de `max_turns_reached` e do erro genérico (AC-7).
- **Critério de saída:** `/session status` lista o processo no novo formato de command line; OOM gera mensagem específica de memória no Discord.

### Step 6 — [test] Suite de testes dos ACs
- **Tipo:** Test
- **Agente:** @grid-tester
- **Descrição:** Em `bun test`, com `FakeChild extends EventEmitter` (sessionKey único por cenário — o registry bloqueia paralelo): (1) OOM via exit 137 / `Result=oom-kill` → `code='oom_killed'`, **não** max_turns, mesmo com stdout/stderr vazios (AC-2); (2) env mapeado para `--setenv` corretamente (asserção sobre args do spawn) (AC-3); (3) cancel/timeout chamam `systemctl stop <unit>` (mock) (AC-4); (4) `--collect`/reset-failed presente (AC-5); (5) regex do inspector casa `systemd-run ... claude -p` (AC-6); (6) `formatOomKilledReply` mapeado em `notifySessionError` (AC-7). Flag off mantém os testes legados verdes.
- **Critério de saída:** todos os testes verdes; cobertura de AC-2 a AC-7 no nível de unidade.

### Step 7 — [verify] Verificação ponta-a-ponta dos ACs
- **Tipo:** Verify
- **Agente:** @oath-verifier
- **Descrição:** Verificação baseada em evidência: rodar uma execução real que estoura memória (ex: prompt que dispara `pytest` pesado ou `python -c` alocando >MemoryMax do scope) e provar AC-1 — `systemctl is-active evonexus-discord-plus` permanece `active`, `MainPID` inalterado, OOM aparece no `journalctl` referenciando o **scope**, e uma segunda sessão concorrente responde. Mapear cada AC (1-7) a evidência concreta (output real, não "deveria funcionar"). Smoke do user master para AC-3.
- **Critério de saída:** `[C]verification-discord-plus-cli-process-isolation.md` com PASS/FAIL por AC e evidências; AC-1 provado em execução real.

---

## Success criteria (checklist)

- [ ] AC-1 — Bun sobrevive ao OOM do Claude; outra sessão responde
- [ ] AC-2 — OOM classificado como `oom_killed`, nunca `max_turns`
- [ ] AC-3 — env íntegro dentro do scope (smoke user master)
- [ ] AC-4 — cancel/timeout matam Claude + netos via `systemctl stop`
- [ ] AC-5 — sem units `failed` acumulando
- [ ] AC-6 — `/session status` lista processos no novo formato
- [ ] AC-7 — mensagem de OOM dedicada no Discord
- [ ] Fixes anteriores (timeout 5min, `MemoryMax` do serviço) preservados
- [ ] Discord oficial e runtimes externos intocados

## Open Questions

- [ ] **[discord-plus-cli-isolation]** D1 — Mecanismo de spawn: `loginctl enable-linger` + `--user` (recomendado) vs `sudo systemd-run --scope`? — bloqueia Step 2+. Risk: alta. (Owner: Eduardo + @custom-sysops)
- [ ] **[discord-plus-cli-isolation]** R10 — LXC unprivileged permite cgroup delegation para scopes filhos do user manager? — pré-requisito do mecanismo. Risk: média. (Owner: @custom-sysops)
- [ ] **[discord-plus-cli-isolation]** D5 — `MemoryMax` por scope (sugestão 6G) e `maxSessions` para não derrubar o LXC? Risk: média. (Owner: Eduardo)
- [ ] **[discord-plus-cli-isolation]** D6 — Re-aplicar namespaces (`PrivateTmp`/`ProtectHome`/`ReadWritePaths`) no scope ou aceitar FS do host/contexto do user? Risk: média. (Owner: @custom-sysops)
- [ ] **[discord-plus-cli-isolation]** D7/AC-7 — Texto exato da mensagem de OOM ao usuário do Discord. Risk: baixa. (Owner: Eduardo/@nova-product)

## Handoff

- **Próximo:** @custom-sysops (Step 1 — decisão de infra é o bloqueador #1). Depois @apex-architect (Step 2 — ADR do contrato runner↔systemd-run).
- **O que está aberto:** D1 (linger vs sudo) precisa fechar antes do código (Step 3+).
- **Saída esperada:** decisão de infra registrada no PRD §4 + ADR de Step 2, então Build (Steps 3-5, @bolt-executor) → Test (Step 6, @grid-tester) → Verify (Step 7, @oath-verifier).
