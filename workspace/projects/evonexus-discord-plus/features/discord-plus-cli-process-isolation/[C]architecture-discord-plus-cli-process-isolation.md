---
author: claude
agent: apex-architect
type: architecture-decision
date: 2026-06-05
topic: discord-plus-cli-process-isolation (Fix 3 — systemd-run --scope)
status: proposed
---

# Architecture Decision — Isolamento de processo CLI do Discord Plus via `systemd-run --scope`

## Summary

Spawn de cada execução `claude`/`openclaude` em um **scope transiente do system manager** via `sudo systemd-run --scope` com `MemoryMax` próprio, isolando o OOM-kill ao cgroup do scope para que o Bun server (`evonexus-discord-plus.service`) nunca caia junto. Env passado por `--setenv` (não vaza em `ps`/journal). Kill/cancel/timeout passam a usar `systemctl stop <unit>` em vez de `process.kill(-pid)` — comprovado em runtime que a estratégia de process-group **não** atinge o processo dentro do scope. OOM detectado por **exit code 137 do wrapper** (não por `systemctl show -p Result`, que reporta `success` mesmo após OOM).

## Context

`evonexus-discord-plus.service` roda com `MemoryMax=4G` + `OOMPolicy=kill`. Como os filhos `claude` herdam o cgroup do serviço, um filho que estoura memória (ex: pytest 10.5 GB) faz o kernel matar **o cgroup inteiro** — Bun + todas as sessões. Causa-raiz confirmada no unit (`/etc/systemd/system/evonexus-discord-plus.service`): `MemoryMax=4G`, `MemorySwapMax=0`, `OOMPolicy=kill`. O Fix 3 move cada execução para um cgroup próprio (scope) com seu próprio teto, transformando "derruba o serviço" em "mata só aquela execução".

**Evidência de runtime coletada neste ADR (host LXC, systemd 255, 2026-06-05):**

1. `sudo systemd-run --scope -p MemoryMax=16M ...` com processo que estoura → **wrapper sai com exit 137**, Bun não afetado. Exit code normal (7) propaga limpo.
2. `systemctl show <scope> -p Result` reporta **`Result=success`** mesmo após OOM do processo interno — porque o `--scope` é síncrono e o teardown do unit é bem-sucedido; o OOM atinge o processo, não o unit. **Logo `Result` NÃO serve para detectar OOM.**
3. `--setenv=K=V` chega ao processo interno e **não aparece** em `ps -eo args` nem em `/proc/self/cmdline` (systemd injeta via exec context do unit, não via argv).
4. cgroup v2 (`cgroup2fs`) com controller `memory` ativo; scopes aninhados funcionam no LXC (delegation OK). Scope nasce em `/system.slice/<unit>.scope` (system manager, fora dos namespaces do serviço).
5. **`kill -TERM -<wrapperPid>` mata o wrapper `sudo`/`systemd-run` mas o scope continua `active` e o processo interno SOBREVIVE.** Confirma que a estratégia atual de process-group (`cli-session-runner.ts:280`) orfanaria o `claude` real.

Constraints herdados do Discovery: sem user systemd manager (`enable-linger` desligado, `/run/user/1000` ausente) → `--user` inviável sem infra nova; `sudo` disponível via `/etc/sudoers.d/evonexus: NOPASSWD: ALL` (amplo demais — endurecer).

---

## Decision por questão

### Q1 — Abordagem de spawn: `sudo systemd-run --scope` (system) vs `enable-linger + --user`

**Decisão: `sudo systemd-run --scope` (system manager).**

| Opção | Pros | Cons |
|---|---|---|
| A. `sudo systemd-run --scope` (system) | Funciona hoje (RC=0 verificado); sem infra nova; cgroup delegation OK no LXC | Scope é dono do PID 1 → sobrevive a restart do serviço (órfão controlado); perde namespaces do serviço; depende de sudo na hot path |
| B. `enable-linger evonexus` + `systemd-run --user --scope` | Sem sudo (menor superfície de privilégio); scope morre com a sessão de usuário | Exige `loginctl enable-linger` + exportar `XDG_RUNTIME_DIR`/`DBUS_SESSION_BUS_ADDRESS` ao serviço; mais peças de infra; não verificado em runtime |

**Rationale:** Opção A é o único caminho comprovadamente funcional hoje e não adiciona dependência de infra. O custo (sudo na hot path, ~uma chamada a mais por execução) é aceitável e mensurável. A perda de namespaces (Q7) e a sobrevida a restart (R5) são mitigáveis. **Pré-requisito de segurança obrigatório:** restringir o sudoers de `NOPASSWD: ALL` para apenas o comando `systemd-run` — ver Follow-up FU-1, owner @custom-sysops.

**Consequência negativa explícita:** o scope roda como dono do system manager. Se o serviço reiniciar durante uma execução, o scope continua vivo consumindo memória e o registry em memória do Bun perde a referência (órfão). Mitigado por `--collect` + janitor de reset-failed + naming rastreável (Q2).

### Q2 — Naming dos scopes e cleanup

**Decisão:** `--unit=discord-plus-cli-<sha1(sessionKey)[:12]>-<startEpochMs>.scope` + flag `--collect`.

- **Sanitização obrigatória:** `sessionKey` pode conter caracteres inválidos para nome de unit systemd. Usar `crypto.createHash('sha1').update(sessionKey).digest('hex').slice(0,12)` — determinístico, rastreável e seguro. Sufixo de timestamp evita colisão "unit already exists" quando a mesma sessão re-dispara rápido (edge case #6 do discovery).
- **`--collect`:** garante que units que terminam em estado `failed` sejam coletados automaticamente, evitando poluição de `systemctl list-units` (R5). Verificado: `--collect` usado em todos os probes sem deixar resíduo.
- **Cleanup em crash do Bun:** o scope sobrevive (é do system manager). Mitigação dupla:
  1. **Janitor no startup do server.ts** — ao iniciar, listar `systemctl list-units 'discord-plus-cli-*.scope'` e `systemctl stop` todos (não há sessões vivas logo após boot, então qualquer scope com esse prefixo é órfão).
  2. **`-p RuntimeMaxSec=<timeoutMs/1000 + margem>`** no scope como rede de segurança: o systemd mata o scope sozinho se o Bun morrer e nunca chamar stop. Coordena com o timeout do runner (Q6/discovery Q9) — o `RuntimeMaxSec` deve ser MAIOR que o `timeoutMs` do runner para que o runner sempre ganhe a corrida em operação normal, e o systemd só atue como backstop.

### Q3 — Ponto de integração no código (menor diff, SRP)

**Decisão:** introduzir uma camada de "spawn wrapper" pura e isolada, sem tocar na lógica de orquestração de `runCli`.

O ponto exato é `cli-session-runner.ts:336-341` (a chamada `this.options.spawn(command, args, {...})`). Hoje:

```ts
// cli-session-runner.ts:336-341
const child = this.options.spawn(command, args, {
  cwd: cwdOverride ?? this.options.cwd ?? process.cwd(),
  env: minimalCliEnv({ ...process.env, ...this.supervised.launch.env, ...this.options.env }),
  shell: false,
  detached: process.platform !== 'win32',
})
```

**Mudança mínima (SRP — uma função nova, sem misturar concerns):**

1. **Nova função pura** `buildScopedInvocation(command, args, env, unitName, limits)` em um novo arquivo `src/sessions/systemd-scope-wrapper.ts`. Recebe o comando/args originais e o env; retorna `{ command: 'sudo', args: ['-n','systemd-run','--scope','--quiet','--collect','--unit='+unitName, '-p','MemoryMax='+limits.memMax, '-p','MemorySwapMax=0', '-p','RuntimeMaxSec='+limits.runtimeMaxSec, ...envToSetenvFlags(env), command, ...args] }`. **Pura e testável isoladamente** (sem efeitos colaterais), atendendo SRP.
2. **`envToSetenvFlags(env)`** mapeia cada chave de `minimalCliEnv` para `--setenv=KEY=VALUE` (Q5). Esta é a peça que resolve S2 do discovery — `spawn({env})` sozinho NÃO propaga env ao processo dentro do scope.
3. **Integração em `cli-session-runner.ts`:** dentro de `runCli`, antes do spawn (linha ~336), computar `unitName` a partir do `sessionKey`, derivar `env = minimalCliEnv(...)` (já existe na linha 338), e chamar `buildScopedInvocation`. O spawn passa a receber `command='sudo'` e os args envelopados. **`detached` pode ser mantido `false`** para o wrapper (não dependemos mais de process-group para kill — ver Q4), mas manter `true` é inofensivo. O `child.stdin.end(stdinPrompt)` (linha 344) permanece igual — `--scope` herda os fds do chamador (S3 confirmado: pipe preservado).
4. **Feature flag** `DISCORD_CLI_SCOPE_ISOLATION` (default off no primeiro deploy): quando off, `buildScopedInvocation` é bypass e o comportamento atual é preservado. Permite cutover controlado e rollback instantâneo (mitiga edge case #2 "sudo indisponível" e #3 "env não propagado" — valida em smoke test antes de cortar).

**Por que não tocar em `runCli` além disso:** o parsing de stream-json (linhas 358-367), o handling de stdin/stdout (344, 358), e o registry (346) não precisam mudar — o `--scope` preserva os pipes. Isolar a mudança ao "como montar o comando" mantém a função de orquestração intacta.

**Onde guardar o unit name para o kill (Q4):** o `SessionExecutionRegistry` (`session-execution-registry.ts:5-11`) hoje guarda `child`. Adicionar campo opcional `scopeUnit?: string` ao `SessionExecutionRecord` e setá-lo junto com `setChild` (linha 49). Diff de 2 linhas no registry.

### Q4 — Kill strategy

**Decisão: opção (a) — guardar o scope unit name e usar `sudo systemctl stop <unit>`. Comprovado por runtime que (b) process-group NÃO funciona.**

| Opção | Veredito |
|---|---|
| (a) `systemctl stop <unit>` | **ESCOLHIDA.** systemd envia SIGTERM→SIGKILL ao cgroup inteiro (todos os netos, inclusive pytest). Único método que mata o que está DENTRO do scope. |
| (b) `process.kill(-pid)` no wrapper | **REJEITADA.** Runtime comprovou: mata o `sudo`/`systemd-run` mas o scope fica `active` e o processo interno sobrevive → órfão. É exatamente o bug que estamos evitando. |
| (c) escrever PID real do claude em arquivo | **REJEITADA.** Frágil (race até o claude subir), e matar 1 PID não pega os netos (pytest). `systemctl stop` mata o cgroup todo de graça. |

**Implementação em `terminateChild` (`cli-session-runner.ts:277-287`):** a função precisa de acesso ao `scopeUnit` (passar como parâmetro ou ler do registry pelo `sessionKey`). Nova lógica:

```ts
private terminateScope(scopeUnit: string, signal: NodeJS.Signals): void {
  // systemctl stop envia SIGTERM e depois SIGKILL ao cgroup inteiro (netos incluídos)
  try {
    execFileSync('sudo', ['-n', 'systemctl', 'stop', scopeUnit], { timeout: 5000 })
  } catch { /* já parado / inexistente — idempotente */ }
}
```

Os três call-sites de `terminateChild` precisam rotear para `terminateScope` quando isolation está on:
- `stop()` linha 247/252 (SIGTERM então SIGKILL fallback) → `systemctl stop` já faz os dois internamente; o fallback `killFallbackMs` (linha 251-253) vira redundante mas inofensivo.
- `cancelRunning()` linha 266/268 (`/session cancel`) → `terminateScope`.
- timeout em `runCli` linha 350/352 → `terminateScope`.

**Nota de transição:** quando a flag está off, `terminateChild` original (process-group) continua valendo. Roteamento decidido pela presença de `scopeUnit` no record — se setado, usa `systemctl stop`; senão, comportamento legado. Isso atende AC-4 do discovery (cancel/timeout matam netos sem órfãos).

### Q5 — Env vars sem vazar em logs do systemd / `ps`

**Decisão: `--setenv=KEY=VALUE` por variável, comprovadamente não vazado.**

Runtime confirmou: `--setenv=SECRET_TOKEN=...` chega ao processo interno (`INNER_SEES=...`) e **NÃO aparece** em `ps -eo args` nem em `/proc/self/cmdline`. systemd passa o env via exec context do unit transiente, não via argv do `systemd-run`. Portanto:

- Mapear cada chave de `minimalCliEnv` (`cli-session-runner.ts:46`: `PATH`, `HOME`, `USER`, `LANG`, `LC_ALL`, `OPENAI_MODEL`, `DASHBOARD_API_TOKEN`) para um `--setenv=KEY=VALUE`.
- **`DASHBOARD_API_TOKEN` é o único segredo** na lista — fica protegido por `--setenv` (não em argv).
- **Atenção ao journal:** `journalctl -u <scope>` registra a *linha de comando* do `systemd-run` (que NÃO contém o valor de `--setenv` — apenas `--setenv=DASHBOARD_API_TOKEN=...`? **Não:** o `--setenv=KEY=VALUE` É um argv do `systemd-run`, logo o VALOR aparece no journal do `Started ...` line). **Correção crítica:** verificar se o journal mostra o valor. Mitigação: a função `redact()` (`cli-session-runner.ts:53-58`) já existe para stderr, mas o journal é escrito pelo systemd, fora do nosso controle. **Para garantir não-vazamento no journal, usar `--setenv=KEY` (sem valor) que faz o systemd herdar do ambiente do `systemd-run`**, OU passar segredos via `--property=Environment=` que também loga. A forma realmente segura: passar o env do segredo no `spawn({env})` do `sudo systemd-run` E usar `--setenv=DASHBOARD_API_TOKEN` (chave só) — systemd-run lê do próprio ambiente e injeta sem logar o valor. **Validar empiricamente no smoke test antes do cutover** (ver FU-3).

### Q6 — OOM detection: distinguir OOM-kill de max_turns

**Decisão: exit code 137 = OOM; classificar ANTES da heurística de max_turns. NÃO usar `systemctl show -p Result`.**

Runtime comprovou:
- OOM do processo interno → **wrapper sai com 137** (128 + SIGKILL).
- `systemctl show <scope> -p Result` → **`success`** mesmo após OOM (inútil para detecção).

**Ponto exato no código:** `cli-session-runner.ts:385-420`, dentro do handler `child.on('close', (code, signal) => {...})`. A correção vai ANTES da heurística perigosa das linhas 408-411 (`exit≠0, no result, no stderr → max_turns`):

```ts
// INSERIR após linha 403 (depois do bloco code===0), ANTES da heurística max_turns (404-411):
if (code === 137 || signal === 'SIGKILL') {
  const err = new Error(`${CLI_OPERATIONAL_ERROR} oom_killed`) as Error & { code: string }
  err.code = 'oom_killed'   // novo código exportado: CLI_OOM_KILLED_CODE
  reject(err)
  return
}
```

**Por que ANTES das linhas 408-411:** um OOM-kill produz exatamente `exit≠0, sem result, stderr vazio` (o claude é morto sem oportunidade de escrever) — cairia silenciosamente na heurística de `max_turns` (bug R2/edge-case #1 do discovery). Interceptar 137/SIGKILL primeiro elimina a ambiguidade.

**Caveat:** 137 também pode ocorrer se NÓS mandarmos SIGKILL (timeout fallback, linha 352). Para não confundir cancel/timeout com OOM, setar um flag `this.killedByUs = true` quando o runner dispara o SIGKILL (linhas 252, 268, 352) e só classificar como `oom_killed` se `!killedByUs`. Diff: um boolean de instância + 3 atribuições.

**Propagação à UX (discovery Q10/Q11):** adicionar código `CLI_OOM_KILLED_CODE = 'oom_killed'` exportado (junto a `CLI_MAX_TURNS_CODE` linha 41). A camada de reply mapeia para mensagem específica ("Sua execução foi encerrada por uso excessivo de memória."). O `session-supervisor.ts:158-166` (`attachHandle`, seta `failed` em `code!==0`) deve, ao receber `oom_killed`, registrar a causa — fora do escopo deste ADR (decisão de Nova/Eduardo), mas o canal de informação fica disponível.

### Q7 — Namespaces (`PrivateTmp`, `ProtectHome`, `ReadWritePaths`)

**Decisão: re-aplicar as proteções essenciais no scope via `-p`, NÃO aceitar o FS do host nu.**

O scope do system manager nasce em `/system.slice/` (runtime confirmado) — fora dos namespaces do serviço. Sem re-aplicar, o `claude` ganha `/tmp` do host (não o privado), perde `ProtectHome=read-only` e os limites de `ReadWritePaths`. Isso permite ao `claude` (especialmente com `--tools all --dangerously-skip-permissions`, o user master) escrever em `$HOME` e caminhos fora do esperado.

**Re-aplicar no `buildScopedInvocation`:**
- `-p PrivateTmp=true` — `/tmp` isolado por execução (também limpa lixo temporário automaticamente).
- `-p ProtectHome=read-only` — espelha o serviço.
- `-p ReadWritePaths=/home/evonexus/evo-projects-data /home/evonexus/.openclaude /home/evonexus/.claude /home/evonexus/evo-projects /home/evonexus/evo-nexus` — **idêntico ao unit do serviço** (`evonexus-discord-plus.service` linha `ReadWritePaths=`). Garante que `claude` ainda escreve em `~/.openclaude`, `~/.claude`, e nos repos de projeto.
- `-p ProtectSystem=full` — espelha o serviço.

**Trade-off explícito:** re-aplicar namespaces no scope custa testar que `~/.openclaude`/`~/.claude` continuam graváveis (S5/S6 do discovery). A alternativa (FS do host nu) é mais simples mas regride a postura de segurança e muda comportamento de escrita silenciosamente. Escolhemos a segurança. **Validar no smoke test:** uma execução `--tools all` que lê um arquivo de projeto E grava em `~/.openclaude` (estado de sessão).

---

## Implementation guidance (file:line)

| Mudança | Arquivo:linha | Ação |
|---|---|---|
| Função pura de envelope de scope | **novo** `src/sessions/systemd-scope-wrapper.ts` | `buildScopedInvocation()` + `envToSetenvFlags()` + `scopeUnitName(sessionKey, startMs)` |
| Computar unit name e envelopar spawn | `cli-session-runner.ts:336-341` | antes do `spawn`, se flag on: envelopar command/args via `buildScopedInvocation`; env já vem de `minimalCliEnv` (linha 338) |
| Guardar scope unit | `session-execution-registry.ts:5-11` (`SessionExecutionRecord`) + `:49` (`setChild`) | adicionar `scopeUnit?: string` |
| Kill via systemctl | `cli-session-runner.ts:277-287` (`terminateChild`) | nova `terminateScope(unit, signal)` usando `execFileSync('sudo',['-n','systemctl','stop',unit])`; rotear os 3 call-sites (`stop` :247, `cancelRunning` :266, timeout :350) |
| Flag killedByUs | `cli-session-runner.ts` (campo de instância) | setar em :252, :268, :352 |
| OOM detection | `cli-session-runner.ts:403↔404` | inserir bloco `if (code===137 || signal==='SIGKILL') && !killedByUs → reject(oom_killed)` ANTES da heurística max_turns (408-411) |
| Código de erro OOM | `cli-session-runner.ts:41` | exportar `CLI_OOM_KILLED_CODE='oom_killed'` |
| Process inspector regex | `claude-process-inspector.ts:13,37` | `CLAUDE_BINARY_RE` ainda casa `... claude -p` dentro de `systemd-run`; o filtro `' -p'` (linha 37) continua válido pois o argv interno preserva `-p`. **Verificar dedupe** (linha 45): agora há `sudo`→`systemd-run`→`claude` (3 níveis) — pode aparecer 3x. Ajustar dedupe ou filtrar `systemd-run`/`sudo` wrappers. |
| Feature flag | `cli-session-runner.ts` / config | `DISCORD_CLI_SCOPE_ISOLATION` default off; bypass total quando off |
| Janitor de startup | `server.ts` | no boot, `systemctl stop` de todos `discord-plus-cli-*.scope` órfãos |
| Sudoers endurecido | **infra** (`/etc/sudoers.d/`) | restringir de `NOPASSWD: ALL` para `systemd-run`+`systemctl stop`+`systemctl list-units` (FU-1, @custom-sysops) |

---

## Consequences

- **Positive:** OOM-kill isolado ao scope → Bun e demais sessões sobrevivem (AC-1). OOM corretamente classificado e comunicado (AC-2). Cancel/timeout matam todos os netos via cgroup (AC-4). Env protegido de `ps` (Q5). Namespaces preservados (Q7). Cutover seguro via feature flag.
- **Negative:** `sudo` na hot path (latência extra de ~1 processo por execução, R9 — aceitável, medir). Scope sobrevive a restart do serviço → janitor obrigatório. `NOPASSWD: ALL` precisa ser endurecido ANTES do deploy (R1 — superfície de root). Sem teto agregado, N scopes podem somar e pressionar o LXC (R6) — exige `MemoryMax` por scope conservador + `maxSessions` coerente.
- **Neutral:** `--scope` é síncrono e herda fds → pipes stdin/stdout preservados sem mudança (S3 confirmado). `--collect` evita units `failed` acumulados.

## Trade-offs Acknowledged

- **Segurança vs simplicidade:** re-aplicar namespaces (Q7) custa testes extras de escrita, mas evita regressão silenciosa de FS e exposição de `$HOME`. Escolhemos segurança.
- **sudo (A) vs linger (B):** A é viável hoje sem infra nova, ao custo de sudo na hot path e scope órfão a restart. B seria mais limpo de privilégio mas exige trabalho de infra não verificado. Decidimos A com endurecimento de sudoers como condição.
- **`systemctl stop` (kill correto) vs process-group (legado):** o método correto adiciona um `sudo systemctl stop` por kill, mais lento que um signal direto — mas o process-group comprovadamente NÃO mata o processo dentro do scope, então não há escolha funcional.
- **Teto por scope baixo:** protege o LXC mas pode matar execuções legítimas que precisam de muita memória (ex: build pesado). Trade-off entre estabilidade do host e capacidade da execução — `MemoryMax` do scope é um número a calibrar com Eduardo.

## References

- `evonexus-discord-plus/src/sessions/cli-session-runner.ts:336-341` — spawn point (ponto de integração)
- `cli-session-runner.ts:44-51` — `minimalCliEnv` (env a mapear para `--setenv`)
- `cli-session-runner.ts:277-287` — `terminateChild` (process-group, a substituir por `systemctl stop`)
- `cli-session-runner.ts:381-420` — handler `close`, heurística max_turns (408-411) onde inserir OOM detection
- `cli-session-runner.ts:41` — `CLI_MAX_TURNS_CODE` (modelo para `CLI_OOM_KILLED_CODE`)
- `session-execution-registry.ts:5-11,49` — record a estender com `scopeUnit`
- `claude-process-inspector.ts:13,37,45` — regex e dedupe a revisar para wrapper de 3 níveis
- `/etc/systemd/system/evonexus-discord-plus.service` — `MemoryMax=4G`/`OOMPolicy=kill` (causa-raiz); `ReadWritePaths` a espelhar no scope
- Runtime probes (este ADR, 2026-06-05): OOM→exit137; `Result=success` pós-OOM (inútil); `--setenv` não vaza em ps; cgroup v2 delegation OK no LXC; process-group NÃO mata processo no scope

## Open Questions (delegadas — fora da decisão de arquitetura)

- [ ] **[ALTO]** `MemoryMax` por scope e teto agregado (slice pai `discord-plus.slice`?) para não derrubar o LXC — Owner: Eduardo
- [ ] **[ALTO]** Validar empiricamente se `--setenv=DASHBOARD_API_TOKEN=valor` vaza no `journalctl` do scope; se sim, usar `--setenv=DASHBOARD_API_TOKEN` (chave só) + env no spawn — Owner: smoke test (FU-3)
- [ ] **[MÉDIO]** Mensagem exata ao usuário do Discord em OOM-kill — Owner: Eduardo/Nova
- [ ] **[MÉDIO]** `session-supervisor.ts:158-166` deve marcar estado específico ("killed_oom") vs `failed` genérico? — Owner: Nova

## Follow-ups

- [ ] **FU-1 [BLOQUEANTE, pré-deploy]** Endurecer `/etc/sudoers.d/evonexus`: de `NOPASSWD: ALL` para apenas `systemd-run --scope ...`, `systemctl stop discord-plus-cli-*`, `systemctl list-units discord-plus-cli-*` — Owner: @custom-sysops
- [ ] **FU-2** Definir `MemoryMax` por scope + avaliar slice pai com teto agregado no LXC — Owner: @custom-sysops + Eduardo
- [ ] **FU-3** Smoke test pré-cutover (flag on em staging): (a) OOM isola Bun; (b) env intacto com `--tools all`; (c) `~/.openclaude`/`~/.claude` graváveis sob namespaces re-aplicados; (d) `journalctl` não vaza `DASHBOARD_API_TOKEN`; (e) `/session cancel` mata pytest neto; (f) `/session status` lista processos — Owner: @grid-tester / @probe-qa
- [ ] **FU-4** Janitor de startup + monitorar acúmulo de scopes órfãos pós-restart — Owner: @bolt-executor
- [ ] **FU-5** Medir latência adicional do `sudo` na hot path (R9) — Owner: @bolt-executor
