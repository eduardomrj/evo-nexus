---
author: claude
agent: compass-planner
type: work-plan
date: 2026-06-23
plan-name: discord-plus-refactor-estrutural
status: draft
mode: direct
---

# Work Plan — Discord Plus: Refactor Estrutural (dual-sink, cancelamento, auth global)

## Context

Code review completo (Lens + Apex, 2026-06-23) concluiu que os 7 problemas de produção do Discord Plus rastreiam para 3 decisões arquiteturais ruins (D3 dual-sink, D5+D6 cancelamento teatral, D8 divergência thread/canal) + 1 defeito CRITICAL de segurança (C1 auth global). Veredito de ambos: **REFATORAR** com testes de regressão. Ticket `bc89ef74-4d4b-43d1-9817-510b2c9355bf`.

**Repo:** `/home/evonexus/evo-projects/evonexus-discord-plus/` (externo ao EvoNexus — delegar com `cwd` sem `isolation`).
**Base:** [`[C]prd-...`](./[C]prd-discord-plus-refactor-estrutural.md) · [`[C]review-apex-...`](./[C]review-apex-2026-06-23.md) · [`[C]review-lens-...`](./[C]review-lens-2026-06-23.md)

## Objectives

- Eliminar a race de autorização cross-usuário (C1) via `AsyncLocalStorage`.
- Unificar entrega ao Discord com barreira de fim-de-turno (R1/D3).
- Tornar o cancelamento real (`AbortController` + prune ativo) — pré-requisito de `cli-process-isolation` (R2/D5+D6).
- Consolidar `chunk()`, blindar exit handler do `runCli`, resiliência de batch, cobertura shadow-outbox (H1/H2/H5/H4).
- Paridade thread/canal em logging e autorização (R3/D8).
- Travar cada fix com teste de regressão (≥404 testes, 0 falhas, tsc limpo).

## Guardrails

### Must Have
- **Ordem fixada pelos revisores** — C1 → R1 → H2 → (H1+H5) → H4 → R2 → R3. Segurança primeiro; R2 antes de R3.
- Cada fix acompanhado de teste de regressão que falha se o comportamento corrigido regredir.
- Preservar parsing `stream-json`, `redact()`, `minimalCliEnv`, auto-compact.
- Padrão de teste `FakeChild extends EventEmitter` com `sessionKey` único por cenário.
- R2 deve expor `AbortSignal` consumível por `cli-process-isolation`.

### Must NOT Have
- Implementação de `cli-process-isolation`/cgroup (feature separada — só consumir a interface de R2).
- Reescrita do parsing `stream-json`.
- Novos comandos/features de produto.
- Remoção dos caminhos legacy/SDK.
- Tocar o runtime oficial do Discord (escopo protegido).

## Task Flow

```
Step 1 (C1 auth)
   ↓
Step 2 (R1 dual-sink)
   ↓
Step 3 (H2 SettleResolver)
   ↓
Step 4 (H1 chunk único + H5 batch resiliente + H4 testes shadow-outbox)
   ↓
Step 5 (R2 AbortController + prune ativo)   ← pré-requisito cli-process-isolation
   ↓
Step 6 (R3 paridade thread/canal)
```

> Dependências reais: R3 (Step 6) consome o `AsyncLocalStorage` de C1 (Step 1) e a unificação de entrega de R1 (Step 2); por isso fecha por último. H4 (testes shadow-outbox) vem antes de R2 porque R2 mexe na máquina de estados e precisa da rede de segurança pronta.

## Detailed TODOs

### Step 1 — C1: Autorização por contexto (AsyncLocalStorage)
- **Tipo:** REFACTOR (segurança)
- **What:** Substituir a global `currentSessionUserId` (`server.ts:104`, escrita em `:252` e `:1408`, lida em `:776`) por `AsyncLocalStorage<{ userId: string }>`. O `userId` é estabelecido no início de cada handler inbound e propagado por toda a cadeia de despacho até `authorizeAccess`. Antes do fix, **@hawk-debugger** reproduz a race cross-usuário e trava o repro num teste falhando.
- **Arquivos:** `server.ts:104,252,776,1408`; cadeia de despacho até as tools `download_attachment`/`fetch_messages` (resolver OQ-2 no caminho MCP).
- **Owner agent:** @hawk-debugger (repro) → @bolt-executor (fix) → @grid-tester (regressão)
- **Acceptance criteria (AC-1):** sob duas mensagens concorrentes de A e B, cada tool call autoriza com o próprio autor; nenhuma leitura de global mutável permanece; teste de concorrência falha se a identidade vazar. `tsc` limpo.
- **Critério de saída (Oath):** rodar o teste de regressão de C1 (deve passar); `grep currentSessionUserId server.ts` retorna 0 ocorrências de uso como autorização; `bun x tsc --noEmit` limpo.
- **Complexidade:** HIGH

### Step 2 — R1: Unificar entrega (matar o dual-sink)
- **Tipo:** REFACTOR
- **What:** `progressSink` passa a carregar **apenas** sinais efêmeros (typing, "🗜️ compactando"). Todo conteúdo durável passa pelo `intentSink` com **barreira de fim-de-turno**. Remover o band-aid `alreadyDelivered` por comparação de strings (`cli-session-runner.ts:374-392`). Decidir OQ-1 (bypass do Oracle em `:576-577`) antes de codar.
- **Arquivos:** `sdk-inbound-runtime.ts:65-85`, `cli-session-runner.ts:374-392,472,519,576-577,614`.
- **Owner agent:** @apex-architect (decisão de barreira + OQ-1) → @bolt-executor → @grid-tester
- **Acceptance criteria (AC-2):** conteúdo durável entregue uma única vez via `intentSink`; nenhum chunk após `done`; `alreadyDelivered` removido; teste cobre turno simples e turno com tools.
- **Critério de saída (Oath):** teste de "sem chunk tardio" passa; `grep alreadyDelivered` retorna 0; suíte de entrega verde.
- **Complexidade:** HIGH

### Step 3 — H2: SettleResolver único no runCli
- **Tipo:** REFACTOR + TEST
- **What:** Extrair um `SettleResolver` único que consolida os handlers `exit` (`:805`) e `close` (`:873`) de `runCli` (`cli-session-runner.ts:713-916`). Eliminar a heurística `!lastResult && stderr==='' → maxTurnsReached` (`:858`, `:903`) que mascara hang silencioso como max_turns. @hawk-debugger reproduz o hang→max_turns mascarado antes do fix.
- **Arquivos:** `cli-session-runner.ts:713-916`.
- **Owner agent:** @hawk-debugger (repro) → @bolt-executor → @grid-tester
- **Acceptance criteria (AC-3):** 4 casos cobertos por teste — `exit=0` sem result, `exit≠0` sem stderr, max_turns real, hang silencioso; hang silencioso **não** dispara AUTO_RESUME; um único caminho de resolução.
- **Critério de saída (Oath):** os 4 testes passam; `exit`+`close` resolvem pelo `SettleResolver` (sem lógica duplicada); a contagem de linhas do handler cai materialmente.
- **Complexidade:** HIGH

### Step 4 — H1 + H5 + H4: chunk único, batch resiliente, testes shadow-outbox
- **Tipo:** REFACTOR + TEST
- **What:** (H1) criar `chunk.ts` único; `server.ts:738`, `sdk-reply-sender.ts:54`, `discord-side-effect-guards.ts:15` passam a importar, com tratamento de menção idêntico. (H5) envolver cada iteração do loop em `gateway-intent-executor.ts:147-157` num try-catch que isola a intent: falha de uma não derruba as demais, marca `failed` na shadow-outbox e loga. (H4) escrever testes para a máquina `planned→blocked→ready→started→sent→failed` de `shadow-outbox.ts` (cobertura zero hoje) — fazer **antes** de R2.
- **Arquivos:** novo `chunk.ts`; `server.ts:738`, `sdk-reply-sender.ts:54`, `discord-side-effect-guards.ts:15`; `gateway-intent-executor.ts:147-157`; `shadow-outbox.ts` (+ test).
- **Owner agent:** @bolt-executor (H1+H5) ∥ @grid-tester (H4)
- **Acceptance criteria (AC-4, AC-5, AC-6):** três call-sites importam de `chunk.ts`; batch com intent #1 falhando ainda processa #2..N e registra `failed`; transições válidas e inválidas da shadow-outbox cobertas por teste.
- **Critério de saída (Oath):** `grep -c "function chunk" src server.ts` mostra uma definição; teste de batch resiliente passa; suíte shadow-outbox sai de 0 para cobertura das 6 transições.
- **Complexidade:** MEDIUM

### Step 5 — R2: AbortController + prune ativo (pré-requisito cli-process-isolation)
- **Tipo:** REFACTOR
- **What:** Propagar um `AbortController` de `gateway-dispatcher.withTimeout` (`:241-259`) → `cli-session-runner` (`:343-407`) → `runCli`/`spawn`. No abort, **matar o processo** (não só rejeitar a promise), respeitando a ordem abort → graceful → SIGKILL (resolver OQ-3 / `killFallbackMs`). Adicionar **timer dedicado de prune** ao `session-execution-registry` (hoje `pruneExpired` em `:79` só roda lazy via `:29,45,75`). Expor o `AbortSignal` de forma que `cli-process-isolation` consiga consumir.
- **Arquivos:** `gateway-dispatcher.ts:241-259`, `cli-session-runner.ts:343-407`, `session-execution-registry.ts:29,45,75,79`.
- **Owner agent:** @apex-architect (interface do signal + OQ-3) → @bolt-executor → @grid-tester
- **Acceptance criteria (AC-7):** timeout/cancel mata o processo subjacente (verificável: o `FakeChild` recebe kill); registry poda por timer sem depender de `tryStart`/`get`; interface do signal documentada para o consumidor downstream.
- **Critério de saída (Oath):** teste de "cancel mata processo" passa; teste de prune por timer (sem chamar `tryStart`) passa; handoff para `cli-process-isolation` referencia a interface exposta.
- **Complexidade:** HIGH

### Step 6 — R3: Paridade thread/canal
- **Tipo:** REFACTOR
- **What:** Emitir `SDK inbound start` (hoje só em `server.ts:254`, caminho canal) **antes** do branch SDK/legacy **também** no caminho thread (`deliverLegacy`, `:1407`). Unificar o gate de autorização e o logging entre os dois handlers, reutilizando o `AsyncLocalStorage` de C1. Garantir que a bifurcação de sessionKey (`types.ts:33-34`) não cause divergência de comportamento downstream.
- **Arquivos:** `server.ts:120,132-134,252-254,1262-1427`, `types.ts:33-34`.
- **Owner agent:** @bolt-executor → @grid-tester → @oath-verifier (verificação final do refactor inteiro)
- **Acceptance criteria (AC-8):** thread e canal emitem `SDK inbound start` antes do branch e passam pelo mesmo gate de autorização/logging; teste cobre as duas entradas.
- **Critério de saída (Oath):** `grep "SDK inbound start" server.ts` aparece nos dois caminhos; teste de paridade passa; verificação final: `bun test` ≥404 pass / 0 fail + `bun x tsc --noEmit` limpo (AC-9).
- **Complexidade:** MEDIUM

## Success Criteria
- [ ] AC-1..AC-8 cobertos por evidência (teste por fix), AC-9 (build verde ≥404/0) confirmado pelo Oath
- [ ] `currentSessionUserId` como autorização: 0 ocorrências; identidade via `AsyncLocalStorage`
- [ ] `alreadyDelivered` removido; nenhum chunk após `done`
- [ ] `SettleResolver` único; hang silencioso não vira max_turns
- [ ] `chunk()` definido em um só lugar; batch resiliente; shadow-outbox coberta
- [ ] `AbortController` mata processo no cancel; prune por timer; interface pronta para `cli-process-isolation`
- [ ] Paridade thread/canal em logging e autorização
- [ ] `bun test` ≥404 pass / 0 fail; `bun x tsc --noEmit` limpo

## Open Questions
- [ ] **OQ-1 (R1, med):** o bypass do Oracle (`cli-session-runner.ts:576-577`) entregando direto via `progressSink` continua como "efêmero" ou migra para `intentSink` com barreira? — define o blast radius de R1. Owner: @apex-architect no Step 2.
- [ ] **OQ-2 (C1, high):** o `AsyncLocalStorage` propaga até os tool calls que entram pelo caminho MCP (`download_attachment`/`fetch_messages`), ou precisa de carregador explícito de `userId` no envelope da tool? — se não propagar, C1 não fecha. Owner: @hawk-debugger/@bolt no Step 1.
- [ ] **OQ-3 (R2, med):** grace period entre abort → SIGKILL (relação com `killFallbackMs`)? — afeta `cli-process-isolation`. Owner: @apex-architect no Step 5.

## Handoff
- **Próximo agente:** @apex-architect (Fase 3 — ADR) se OQ-1/OQ-2/OQ-3 exigirem decisão arquitetural formal antes da execução; senão @hawk-debugger inicia o repro de C1 (Step 1).
- **Sequência de execução:** Hawk (repro C1+H2) → Bolt (fixes por step) → Grid (regressão por step) → Oath (verificação final, AC-9).
- **Próxima skill:** `dev-verify` para formalizar os critérios de saída por step.
- **Downstream:** após R2 (Step 5), desbloqueia `cli-process-isolation` ([[discord-plus-cli-isolation]]).
