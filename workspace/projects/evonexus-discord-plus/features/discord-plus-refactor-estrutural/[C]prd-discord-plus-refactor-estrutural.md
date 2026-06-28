# [C] PRD — Discord Plus: Refactor Estrutural (dual-sink, cancelamento, auth global)

**Data:** 2026-06-23
**Autor:** @compass-planner
**Fase:** 2 — Planning
**Ticket:** `bc89ef74-4d4b-43d1-9817-510b2c9355bf`
**Reviews de base:** [`[C]review-apex-2026-06-23.md`](./[C]review-apex-2026-06-23.md), [`[C]review-lens-2026-06-23.md`](./[C]review-lens-2026-06-23.md)
**Repo:** `/home/evonexus/evo-projects/evonexus-discord-plus/`

---

## Problema

O code review completo (Lens + Apex, 2026-06-23) concluiu que **todos os problemas de produção do Discord Plus rastreiam para 3 decisões arquiteturais ruins**, não para bugs pontuais:

- **D3 — dual-sink:** `progressSink` e `intentSink` entregam ao Discord sem barreira de fim-de-turno. Causa chunks tardios (até 56s após `done`), 6 mensagens extras por turno, e um band-aid frágil (`alreadyDelivered` por comparação de strings).
- **D5+D6 — cancelamento teatral:** o timeout rejeita a promise mas não cancela o trabalho subjacente (sem `AbortSignal`); o prune do registry é lazy. Causa travamentos de 57min e sessões sem deadline efetivo.
- **D8 — divergência thread/canal:** os dois handlers inbound logam e autorizam de forma diferente. Vaza para autorização (base do C1) e observabilidade.

Além disso há um **defeito de segurança CRITICAL (C1)**: `currentSessionUserId` é uma variável global mutável usada para autorizar tool calls; mensagens concorrentes de usuários diferentes causam autorização cross-usuário (OWASP A01).

Hotfixes continuam ressurgindo porque a raiz nunca foi endereçada. Os commits recentes (`2b04e62`, `3bf249f`) acertam o sintoma mas **não têm teste de regressão** — então o próximo refactor pode revertê-los silenciosamente.

## Goals

1. Eliminar a race de autorização cross-usuário (C1) com propagação de identidade por contexto de execução.
2. Unificar a entrega ao Discord: conteúdo durável só pelo `intentSink` com barreira de fim-de-turno; `progressSink` só para sinais efêmeros (D3/R1).
3. Tornar o cancelamento real: `AbortController` propagado até o processo + prune ativo por timer (D5+D6/R2), pré-requisito de `cli-process-isolation`.
4. Consolidar `chunk()` num módulo único (H1) e blindar o exit handler do `runCli` contra hang→max_turns mascarado (H2).
5. Impedir que um erro de side-effect derrube o batch inteiro de intents (H5) e cobrir `shadow-outbox` com testes (H4).
6. Paridade total thread/canal em logging e autorização (D8/R3).
7. **Travar cada fix com teste de regressão** — nenhum comportamento corrigido pode regredir sem um teste falhar.

## Non-goals

- **`cli-process-isolation` (Fix 3 / cgroup)** — fica fora deste refactor; ele **consome** R2 como pré-requisito, mas é uma feature separada já planejada ([[discord-plus-cli-isolation]]).
- Reescrita do parsing `stream-json` — é conhecimento caro e sólido; preservar.
- Mudança de comportamento funcional visível ao usuário além da correção dos bugs (sem novos comandos/features).
- Remoção do caminho legacy/SDK — manter ambos; o refactor é estrutural, não de produto.

## User stories

- **US-1 (segurança):** Como operador do Discord Plus, quero que cada tool call seja autorizada com a identidade real do autor da mensagem, mesmo sob mensagens concorrentes, para que nunca ocorra autorização cross-usuário.
- **US-2 (entrega limpa):** Como usuário do canal, quero receber exatamente uma resposta durável por turno, sem chunks tardios nem mensagens duplicadas.
- **US-3 (cancelamento):** Como operador, quero que cancelar/timeout de uma sessão de fato mate o trabalho subjacente, para não acumular processos travados de 57min.
- **US-4 (robustez de batch):** Como usuário, quando uma das ações do bot falha, quero que as demais ainda sejam executadas e que a falha seja sinalizada — não um drop silencioso.
- **US-5 (paridade):** Como operador, quero que threads e canais logem e autorizem identicamente, para diagnosticar os dois com o mesmo ferramental.

## Acceptance criteria (Given/When/Then)

### AC-1 (C1) — Autorização por contexto
- **Given** duas mensagens concorrentes de usuários A e B chegando em paralelo
- **When** cada uma dispara uma tool call que invoca `authorizeAccess`
- **Then** cada tool call é autorizada com o `userId` do seu próprio autor (A com A, B com B), via `AsyncLocalStorage` — sem leitura de global mutável
- **E** um teste de regressão simula a concorrência e falha se a identidade vazar.

### AC-2 (R1) — Barreira de fim-de-turno
- **Given** um turno que produz texto de planejamento (preview) e um resultado final
- **When** o turno completa
- **Then** o conteúdo durável é entregue **uma única vez** pelo `intentSink`, e o `progressSink` carrega **apenas** sinais efêmeros (typing, "🗜️ compactando")
- **E** não há chunk entregue após o `done`; o band-aid `alreadyDelivered` por comparação de strings é removido.

### AC-3 (H2) — SettleResolver determinístico
- **Given** as saídas do `runCli`: (a) `exit=0` sem result, (b) `exit≠0` sem stderr, (c) max_turns real, (d) hang silencioso (sem result, sem stderr)
- **When** o processo encerra
- **Then** cada caso resolve por um **único** caminho (`SettleResolver`), e **hang silencioso NÃO é classificado como max_turns** (não dispara AUTO_RESUME)
- **E** os 4 casos têm testes.

### AC-4 (H1) — chunk único
- **Given** os três call-sites de chunking (`server.ts`, `sdk-reply-sender.ts`, `discord-side-effect-guards.ts`)
- **When** o refactor é aplicado
- **Then** todos importam de um módulo único `chunk.ts`, e o tratamento de menção é idêntico nos três.

### AC-5 (H5) — Batch resiliente
- **Given** um batch de N intents onde a intent #1 falha no `sender`
- **When** o executor processa o batch
- **Then** as intents #2..N ainda são processadas, a falha da #1 é registrada na `shadow-outbox` como `failed` e sinalizada no log — sem drop silencioso das demais.

### AC-6 (H4) — Cobertura shadow-outbox
- **Given** a máquina de estados `planned→blocked→ready→started→sent→failed`
- **When** a suíte roda
- **Then** existem testes cobrindo cada transição válida e as inválidas, partindo de cobertura zero.

### AC-7 (R2) — Cancelamento real + prune ativo
- **Given** uma sessão que excede o `dispatchTimeoutMs` ou é cancelada
- **When** o timeout/cancel dispara
- **Then** o `AbortController` propaga até o `runCli`/`spawn` e o **processo subjacente é morto** (não só a promise rejeitada)
- **E** o `session-execution-registry` poda execuções expiradas por um **timer dedicado**, sem depender de `tryStart`/`get`
- **E** a interface exposta é suficiente para `cli-process-isolation` consumir o signal.

### AC-8 (R3) — Paridade thread/canal
- **Given** mensagens inbound chegando por thread e por canal
- **When** cada uma é processada
- **Then** ambas emitem `SDK inbound start` **antes** do branch SDK/legacy e passam pelo **mesmo** gate de autorização e logging — sem divergência.

### AC-9 (regressão global) — Build verde
- **Given** o estado final do refactor
- **When** `bun test` e `bun x tsc --noEmit` rodam
- **Then** ≥404 testes passam (baseline + novos), 0 falham, typecheck limpo.

## Constraints

- Stack: TypeScript + Bun. `bun test`, `bun x tsc --noEmit`.
- Repo externo ao EvoNexus → usar `cwd` sem `isolation` ao delegar (ver `.claude/rules/worktree-isolation.md`).
- Preservar parsing `stream-json`, `redact()`, `minimalCliEnv`, auto-compact.
- Não tocar o runtime oficial do Discord (escopo protegido — CLAUDE.md).
- Padrão de teste: `FakeChild extends EventEmitter` com `sessionKey` único por cenário ([[discord-plus-max-turns]]).
- Ordem de execução **fixada pelos revisores** — não reordenar (segurança primeiro, R2 antes de R3).

## Open questions

- **OQ-1 (R1):** o `progressSink` hoje também entrega resultado do Oracle direto (`cli-session-runner.ts:576-577`, bypass do intentQueue). Esse bypass continua válido como "efêmero" ou deve migrar para o `intentSink` com barreira? — **Risk: med** — decide o blast radius de R1.
- **OQ-2 (C1):** `AsyncLocalStorage` cobre a cadeia de despacho, mas os tool calls (`download_attachment`/`fetch_messages`) entram por um caminho MCP separado. Confirmar que o contexto propaga até lá ou se precisa de um carregador explícito de `userId` no envelope da tool. — **Risk: high** — se não propagar, C1 não está fechado.
- **OQ-3 (R2):** o `killFallbackMs` atual e o novo `AbortController` precisam de uma ordem definida (abort → graceful → SIGKILL). Qual o grace period antes do SIGKILL? — **Risk: med** — afeta `cli-process-isolation`.
