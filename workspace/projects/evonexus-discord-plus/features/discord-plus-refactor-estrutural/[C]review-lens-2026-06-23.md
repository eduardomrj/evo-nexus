# [C] Code Review — Lens — Discord Plus Refactor Estrutural

**Data:** 2026-06-23
**Autor:** @lens-reviewer
**Veredito:** REFATORAR
**Ticket:** `bc89ef74-4d4b-43d1-9817-510b2c9355bf`

---

## Resumo

**1 CRITICAL · 5 HIGH · 6 MEDIUM · 3 LOW.**

Build saudável: **404 testes passando, 0 falhando, `tsc --noEmit` limpo**. A dívida é **concentrada, não difusa** — vive em 3 hotspots, não espalhada pelo código. Isso favorece o refactor: o blast radius é contido e a infra de teste é sólida.

## CRITICAL

### C1 — `currentSessionUserId` global mutável → race cross-usuário (OWASP A01)
`server.ts:104` declara `let currentSessionUserId: string | undefined`. É escrita em **dois** handlers fire-and-forget (`server.ts:252` caminho canal, `server.ts:1408` caminho thread) e **lida** na autorização em `server.ts:776` (`authorizeAccess(access, operation, currentSessionUserId, resource)`).

Como os handlers são fire-and-forget, duas mensagens concorrentes de usuários diferentes sobrescrevem a global entre a escrita e a leitura. Tool calls (`download_attachment`, `fetch_messages`) autorizam com o `userId` errado → **usuário A executa autorizado com a identidade de B**. Broken Access Control, OWASP A01.

**Fix:** `AsyncLocalStorage` propagando `userId` por toda a cadeia de despacho. A identidade vira contexto da execução, não estado global.

## HIGH

### H1 — `chunk()` triplicado e divergente
Três cópias idênticas (por origem) que já divergiram:
- `server.ts:738` — `function chunk(...)`
- `sdk-reply-sender.ts:54` — `export function chunk(...)`
- `discord-side-effect-guards.ts:15` — `chunkDiscordMessage(...)`

O fix de menção (`mentionUserId`) foi aplicado em **só uma** das três. **Fix:** módulo único `chunk.ts`, as três passam a importar.

### H2 — `runCli` exit handler com heurística ruim
`cli-session-runner.ts:713-916` (~110 linhas, handlers `exit` em `:805` e `close` em `:873` com lógica duplicada). A heurística `!maxTurnsReached && !lastResult && stderr.trim() === '' → maxTurnsReached = true` (`:858`, `:903`) **mascara hang silencioso como max_turns**. Um processo que travou e morreu sem emitir result nem stderr é classificado como max_turns → dispara **AUTO_RESUME num travamento real**, perpetuando o loop.

**Fix:** extrair um `SettleResolver` único (um caminho de resolução, não dois). Testes cobrindo: `exit=0` sem result; `exit≠0` sem stderr; max_turns real vs hang silencioso.

### H3 — drops silenciosos sem feedback
Caminhos de erro descartam a intent sem sinalizar ao usuário nem ao log estruturado. O usuário fica esperando uma resposta que nunca chega. (Resolvido como efeito de R1 + H5.)

### H4 — `shadow-outbox.ts` com zero testes
`shadow-outbox.ts` rastreia a máquina de estados `planned→blocked→ready→started→sent→failed` — núcleo da entrega de side-effects. **Cobertura zero.** Qualquer refactor de R1 pode quebrar transições sem nenhum teste pegar.

### H5 — erro de side-effect aborta o batch inteiro
`gateway-intent-executor.ts:156` lança `SideEffectStartedError` **dentro do loop** de intents, sem try-catch que isole a iteração. Intent #1 falha → intents #2..N são **droppadas silenciosamente**. **Fix:** isolar cada intent; falha de uma não derruba as demais.

## Positivos (preservar)

- parsing `stream-json` sólido — conhecimento **caro de reconquistar**, não reescrever
- `redact()` para segredos em log
- `minimalCliEnv` (superfície de env mínima por spawn)
- auto-compact funcional
- commits recentes (`2b04e62`, `3bf249f`) **acertam o alvo** — faltam só os testes de regressão

## Veredito

**REFATORAR.** Dívida concentrada em 3 hotspots, infra de teste saudável (404 pass), conhecimento de `stream-json` caro de reconquistar. O risco de reescrita total não se justifica — refactor cirúrgico com testes de regressão é o caminho.

## Handoffs sugeridos

- **@hawk-debugger** — reproduzir C1 (race cross-usuário) e H2 (hang→max_turns mascarado) antes do fix, para travar repro em teste.
- **@grid-tester** — testes de regressão para C1, H2, H4 (shadow-outbox), R1, R2.
