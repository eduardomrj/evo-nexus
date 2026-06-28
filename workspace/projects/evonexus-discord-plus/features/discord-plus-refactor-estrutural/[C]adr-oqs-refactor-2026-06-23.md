---
author: claude
agent: apex-architect
type: architecture-decision
date: 2026-06-23
topic: discord-plus refactor estrutural — fechamento de 3 open questions (ticket bc89ef74)
status: proposed
---

# ADR — Fechamento de 3 Open Questions (refactor estrutural Discord Plus)

Ticket: `bc89ef74`. Plano de 6 steps aprovado. Este ADR fecha 3 decisões que bloqueiam a execução. Todas as 3 foram decididas após leitura do código real (file:line abaixo).

**Nota de paths:** a OQ referencia `cli-session-runner.ts` na raiz, mas o arquivo real é `src/sessions/cli-session-runner.ts`. `server.ts` está na raiz. As linhas citadas abaixo são as reais no estado atual do repo.

---

## OQ-1 — Bypass do Oracle via progressSink (Step 2 — R1, média)

**Decisão: MANTER como efêmero — NÃO migrar para intentSink.** Porém com uma correção de rótulo: o `progressSink` aqui NÃO entrega progresso, entrega a **resposta final durável** do Oracle. A decisão é manter o caminho de entrega fora do intentQueue, mas tratá-lo como um *sink de entrega direta* explícito (não confundir com o canal de sinais de progresso).

**Evidência:**
- `src/sessions/cli-session-runner.ts:576-590` — `scheduleAsyncAgentResult` entrega `output.result` (a resposta real do sub-agente assíncrono ao usuário) via `this.options.progressSink.capture({ type: 'reply', ... })`. O comentário na linha 576 diz explicitamente: "bypasses intentQueue/GatewayDispatcher". O `messageId` é o snowflake real do Discord (linha 582), não sintético — ou seja, é uma reply de verdade, durável.
- Contraste: `cli-session-runner.ts:614-627` (`runAutoCompactIfNeeded`) usa o MESMO `progressSink.capture` para um sinal transitório ("🗜️ Compactando contexto..."). Ou seja, o progressSink JÁ é usado para os dois tipos hoje — conteúdo durável (Oracle) e sinal efêmero (compact).
- O caminho async do Oracle é disparado fora do ciclo normal de turno (`scheduleAsyncAgentResult` roda depois que o sub-agente termina, num `catch`-guarded fire-and-forget, linha 600-603). Não há barreira de fim-de-turno aplicável porque não há turno do dispatcher em andamento — o turno original do Oracle já terminou quando o resultado async chega.

**Racional:** migrar para intentSink exigiria que o resultado async passasse pela barreira de fim-de-turno do GatewayDispatcher, mas esse resultado chega FORA de qualquer turno (é um callback de processo async já concluído). Não há turno para "fechar". Forçar o intentSink criaria um turno sintético só para entregar uma reply que já está pronta — adiciona o GatewayIntentExecutor (authz, target resolver, side-effects) no caminho de uma reply cujo `messageId`/`channelId` já são conhecidos e confiáveis (vêm do envelope original autorizado, linhas 582-588). Blast radius da migração: tocaria o contrato do dispatcher para aceitar entrega out-of-turn, exatamente o acoplamento que o refactor quer reduzir.

**Consequência para o plano (Bolt):** No Step 2, ao limpar o progressSink para conter apenas sinais transitórios, NÃO mover a entrega do Oracle (linha 577) para o intentSink. Em vez disso, separar conceitualmente: introduzir um caminho de entrega nomeado (ex: `deliverySink` ou um método `progressSink.deliverFinal(...)`) que deixe explícito que esta é entrega durável out-of-turn, distinta dos sinais de progresso. O comportamento de runtime permanece idêntico; só o nome/contrato fica honesto. Se o refactor unificar tudo num `progressSink` "só sinais", então o caso do Oracle precisa de um sink próprio — não pode ser dobrado em intentSink sem inventar um turno.

---

## OQ-2 — AsyncLocalStorage vs carregador explícito no caminho MCP (Step 1 — C1, alta — bloqueia fix de segurança)

**Decisão: NEM "propaga automaticamente" NEM "precisa de carregador explícito no envelope da tool" — a premissa da OQ está parcialmente desatualizada. O caminho MCP ativo (SDK) NÃO usa a global `currentSessionUserId` para autorizar tool calls; ele já carrega identidade via `sessionKey` no intent. A global só é load-bearing para o caminho LEGACY (mcp.notification stdio). Portanto: o `AsyncLocalStorage` substitui a global APENAS no caminho legacy, e nesse caminho PRECISA DE CARREGADOR EXPLÍCITO (o ALS não cruza o boundary stdio do MCP legacy sozinho).**

**Evidência — existem DOIS caminhos:**

1. **Caminho SDK (ativo, gated por `isSdkInboundEnabled()`):**
   - `server.ts:276` decide SDK vs legacy; `server.ts:1427` `trySdkInboundOrLegacy(...)`.
   - As tools `download_attachment` e `fetch_messages` no SDK são criadas por `createPassiveDiscordTools(tool, supervised.key, intentSink)` — `src/sessions/sdk-session-runner.ts:81`.
   - Cada handler captura um **intent carregando `sessionKey`**, não chama `fetchAllowedChannel`: `src/sessions/passive-discord-tools.ts:106-115` (`download_attachment`) e `:117-130` (`fetch_messages`). O `sessionKey` é fechado por closure na criação da tool (`:53-57`), ligado a `supervised.key` daquela sessão.
   - A autorização desses intents acontece no `GatewayIntentExecutor`, que usa `ctx.subject.userId` derivado do envelope — `server.ts:158` (`authorize: (ctx) => authorizeAccess(loadAccess(), ctx.operation, ctx.subject.userId, ctx.resource, ctx.message)`). **A global `currentSessionUserId` não participa.**

2. **Caminho legacy (gated, `mcp.notification` via stdio):**
   - `server.ts:804` `new Server(...)`, `:1064` `mcp.connect(new StdioServerTransport())`.
   - O handler `CallToolRequestSchema` (`server.ts:942`) trata `download_attachment` (`:1033-1048`) e `fetch_messages` (`:998`) chamando `fetchAllowedChannel(...)` (`:770-780`), que autoriza com a GLOBAL: `authorizeAccess(access, operation, currentSessionUserId, resource)` — `server.ts:776`.
   - A global é escrita em DOIS pontos: `server.ts:252` (dentro de `dispatchSdkInboundRuntime`) e `server.ts:1408` (dentro de `deliverLegacy`). Declaração em `server.ts:104`, com comentário (`:100-103`) descrevendo o propósito.

**Por que o ALS NÃO propaga automaticamente no caminho legacy:** O MCP legacy é um `Server` com `StdioServerTransport` (`server.ts:1064`). O handler de tool (`:942`) é invocado pelo loop de mensagens do transport MCP — um tick de event loop **separado** da chamada `dispatcher.dispatch(ctx)` que setou o contexto. Um `AsyncLocalStorage.run(...)` em volta do `dispatch` (`server.ts:256`) NÃO envolve o callback do `setRequestHandler`, porque o request da tool chega como uma mensagem inbound nova no transport stdio, fora da cadeia `await` do dispatch original. ALS só propaga por continuação assíncrona encadeada (await/then/callbacks agendados dentro do mesmo fluxo), não atravessa um boundary de I/O orientado a mensagens onde o produtor e o consumidor são desacoplados.

**Racional / decisão operacional:**
- **No caminho SDK (o que o refactor de segurança deve priorizar):** a substituição da global é, na prática, **remover a global** — o SDK já não depende dela para authz de tool. O `userId` correto já flui via `sessionKey`→intent→`ctx.subject.userId`. Nenhum ALS é necessário aqui para o authz das tools.
- **No caminho legacy (enquanto existir):** se o objetivo é eliminar a global mutável compartilhada (o risco de segurança: duas sessões concorrentes sobrescrevem `currentSessionUserId` entre o set na linha 252/1408 e o read na linha 776 — race de identidade), o ALS por si só **não** resolve, porque não cruza o stdio. **Precisa de carregador explícito:** o `userId` tem que viajar no próprio request da tool (no envelope/meta da `mcp.notification`, server.ts:1409) e ser lido de `req.params` no handler (`:942`), OU o caminho legacy deve ser aposentado.

**Consequência para o plano (Bolt):** O fix de C1 (Step 1) deve:
1. Tratar o caminho SDK e o legacy separadamente — eles têm mecanismos de identidade diferentes. Não existe um único `AsyncLocalStorage` que cubra os dois.
2. **SDK:** confirmar que nenhum outro consumidor lê `currentSessionUserId` no fluxo SDK (grep já mostra os 3 reads: `:252` write, `:776` read, `:1408` write — o único READ é `:776`, dentro de `fetchAllowedChannel`, que é chamado SÓ pelo handler legacy `:942`). Logo a global é 100% legacy. Pode-se remover a global do fluxo SDK sem ALS.
3. **Legacy:** se for mantido, carregar `userId` explicitamente no request da tool (não na global) — carregador explícito no envelope. Se for aposentado no refactor, a global morre junto e o problema de race desaparece. **Recomendação:** confirmar com Eduardo se o caminho legacy (`isSdkInboundEnabled()===false`) ainda é usado em produção; se não, removê-lo é o fix mais limpo de C1 e elimina a global sem introduzir ALS.

**Cadeia de chamadas (resumo file:line):**
- Global: `server.ts:104` (decl) → `:252` (write SDK dispatch) → `:1408` (write legacy deliver) → `:776` (único read, em `fetchAllowedChannel`).
- `fetchAllowedChannel` só é chamado por: `server.ts:952` (reply), `:999` (fetch_messages), `:1022` (react), `:1028` (edit_message), `:1034` (download_attachment) — todos dentro do handler MCP legacy `:942`.
- SDK tools: `passive-discord-tools.ts:106-130` → intent com `sessionKey` → `GatewayIntentExecutor.authorize` `server.ts:158` usa `ctx.subject.userId`.

---

## OQ-3 — Grace period abort→SIGTERM→SIGKILL e relação com killFallbackMs e cli-process-isolation (Step 5 — R2, média)

**Decisão: grace period de 5s (SIGTERM→SIGKILL), reusando a constante já existente `killFallbackMs` (default 5000). NÃO introduzir uma constante nova com semântica concorrente. E SIM, o contrato muda quando o cli-process-isolation está ativo: com scope systemd, o kill deixa de ser process-group e passa a `systemctl stop <unit>`, que já implementa o ciclo SIGTERM→SIGKILL internamente — nesse caso o `killFallbackMs` do runner vira backstop redundante (inofensivo), não o mecanismo primário.**

**Evidência:**
- `killFallbackMs` JÁ existe: declarado em `src/sessions/cli-session-runner.ts:39` (opcional na options), default aplicado em `:306` (`options.killFallbackMs ?? 5000`).
- O padrão SIGTERM→delay→SIGKILL já está implementado em 3 call-sites, todos usando `killFallbackMs` como grace:
  - `stop()` — `cli-session-runner.ts:420` (`terminateRunning('SIGTERM')`) + `:424-426` (`setTimeout(... SIGKILL, this.options.killFallbackMs)`).
  - `cancelRunning()` — `:439` (SIGTERM) + `:440-442` (SIGKILL após `killFallbackMs`).
  - timeout/cleanup — `:745-748` (mesmo padrão).
- O kill atual é por process-group: `terminateChild` (`:450-460`) faz `process.kill(-child.pid, signal)` (`:453`) com fallback para `child.kill(signal)` (`:459`).
- **Contrato do cli-process-isolation:** o ADR em `/home/evonexus/evo-nexus/workspace/projects/evonexus-discord-plus/features/discord-plus-cli-process-isolation/[C]architecture-discord-plus-cli-process-isolation.md` (Q4, linhas 84-110) **comprovou em runtime** que `process.kill(-pid)` (process-group) NÃO mata o processo dentro do scope systemd — mata só o wrapper `sudo`/`systemd-run` e orfana o `claude` real (evidência runtime #5, linha 26 daquele ADR). O método correto é `sudo systemctl stop <unit>`, que envia SIGTERM→SIGKILL ao cgroup inteiro (todos os netos, ex: pytest). Aquele ADR observa explicitamente (linha 106): com `systemctl stop`, "o fallback `killFallbackMs` (linha 251-253) vira redundante mas inofensivo".

**Racional:**
- 5s é o grace já calibrado e em uso em todos os 3 call-sites. Introduzir uma constante nova (ex: `abortGraceMs`) criaria DOIS timers de grace potencialmente divergentes para a mesma operação de kill — fonte clássica de bug (qual ganha a corrida?). O AbortController do R2 deve disparar o MESMO caminho de terminação (`terminateRunning`/`terminateScope`), herdando `killFallbackMs`.
- Quando cli-process-isolation está OFF (flag `DISCORD_CLI_SCOPE_ISOLATION` off): o AbortController → `terminateChild` (process-group) → SIGTERM, espera `killFallbackMs` (5s), SIGKILL. Grace = 5s, controlado pelo runner.
- Quando cli-process-isolation está ON: o AbortController deve rotear para `terminateScope` (`sudo systemctl stop <unit>`), conforme decidido no ADR de isolation (Q4). O `systemctl stop` aplica o `TimeoutStopSec` do systemd (default 90s no system manager, mas o scope pode setar `-p TimeoutStopSec=`). **Aqui está o ponto de coordenação:** se quisermos que o grace efetivo continue ~5s sob isolation, o scope precisa nascer com `-p TimeoutStopSec=5` no `buildScopedInvocation`. Senão o `systemctl stop` espera o default do systemd antes do SIGKILL do cgroup, e o `killFallbackMs` do runner (5s) dispararia ANTES — mas o SIGKILL do runner (process-group) é justamente o que NÃO funciona no scope. Resultado: sob isolation sem `TimeoutStopSec`, o abort pode levar até o default do systemd para matar de fato.

**Consequência para o plano (Bolt):**
1. **R2 (Step 5):** o AbortController deve disparar o caminho de terminação existente, NÃO um novo. Sinal de abort → `terminateRunning('SIGTERM')` (ou `terminateScope` se isolation on) → SIGKILL após `killFallbackMs`. Reusar `killFallbackMs` (cli-session-runner.ts:39,306). Não criar `abortGraceMs`.
2. **Roteamento por isolation:** replicar a decisão do ADR de isolation — se `scopeUnit` estiver setado no record do registry, abort → `sudo systemctl stop <scopeUnit>`; senão → process-group legacy. O AbortController não deve assumir process-group.
3. **Coordenação de grace sob scope:** quando cli-process-isolation entrar, adicionar `-p TimeoutStopSec=5` (= `killFallbackMs/1000`) ao `buildScopedInvocation`, para que o grace efetivo do `systemctl stop` case com os 5s do runner. Documentar que sob isolation o grace é governado pelo systemd (`TimeoutStopSec`), não pelo `setTimeout` do runner. Sem isso, o abort sob scope pode demorar o default do systemd.
4. **Constante nomeada:** manter `killFallbackMs` como a fonte única do grace (5000ms). Se uma env var for desejada, expor `DISCORD_CLI_KILL_FALLBACK_MS` mapeando para `options.killFallbackMs`, e derivar `TimeoutStopSec` dela quando montar o scope — uma fonte, dois consumidores coordenados.

---

## Referências (file:line)

- `src/sessions/cli-session-runner.ts:576-603` — entrega async do Oracle via progressSink (OQ-1)
- `src/sessions/cli-session-runner.ts:614-627` — progressSink usado para sinal transitório de compact (OQ-1, contraste)
- `server.ts:104` — declaração da global `currentSessionUserId` (OQ-2)
- `server.ts:252,1408` — writes da global; `server.ts:776` — único read (em `fetchAllowedChannel`) (OQ-2)
- `server.ts:942-1062` — handler MCP legacy `CallToolRequestSchema` (download_attachment :1033, fetch_messages :998) (OQ-2)
- `server.ts:158` — `GatewayIntentExecutor.authorize` usa `ctx.subject.userId` (caminho SDK, sem global) (OQ-2)
- `server.ts:276,1064,1427` — gate SDK vs legacy, `mcp.connect` stdio, `trySdkInboundOrLegacy` (OQ-2)
- `src/sessions/sdk-session-runner.ts:81` — `createPassiveDiscordTools(tool, supervised.key, intentSink)` (OQ-2)
- `src/sessions/passive-discord-tools.ts:106-130` — tools `download_attachment`/`fetch_messages` capturam intent com `sessionKey` (OQ-2)
- `src/sessions/cli-session-runner.ts:39,306` — `killFallbackMs` decl + default 5000 (OQ-3)
- `src/sessions/cli-session-runner.ts:420,424-426,439-442,745-748` — padrão SIGTERM→SIGKILL com killFallbackMs (OQ-3)
- `src/sessions/cli-session-runner.ts:450-460` — `terminateChild` process-group `process.kill(-pid)` (OQ-3)
- `workspace/projects/evonexus-discord-plus/features/discord-plus-cli-process-isolation/[C]architecture-discord-plus-cli-process-isolation.md` Q4 (linhas 84-110) — `systemctl stop` substitui process-group; killFallbackMs vira redundante sob scope (OQ-3)
