---
author: compass
type: plan
date: 2026-06-03
feature: discord-plus-renew-confirm
status: ready-for-build
repo: /home/evonexus/evo-projects/evonexus-discord-plus
prd: workspace/development/features/discord-plus-renew-confirm/[C]prd-discord-plus-renew-confirm-2026-06-03.md
owner_handoff: "@bolt-executor"
---

# Plano — Discord Plus: Session Renew com Confirmação Explícita

## Contexto

O `/session renew` atual evicta a sessão imediatamente e só usa o checkpoint na próxima
mensagem (mecanismo `pendingRenew` no `SessionCheckpointStore`). O PRD pede um fluxo de
confirmação explícita: `renew` entra em `pending_confirm` (TTL 15 min), exibe um summary
rico, permite ajustar model/agent/project/dirs/effort, e só evicta a sessão no `/session
confirm`. Durante o pending, mensagens normais são ignoradas com um lembrete.

Além do PRD, o summary deve incluir **effort** (`EffortStoreService`) e **dirs**
(`ExtraDirsStore`) — dois stores que entraram depois da escrita do PRD e seguem o mesmo
padrão fs-only dos demais.

## Objetivos (resultados testáveis)

1. `renew` não evicta mais a sessão; marca `pending_confirm` com TTL de 15 min e devolve o summary completo.
2. Summary exibe `engine / agent / model / project / dirs / effort / checkpoint`.
3. Mensagens normais durante pending são ignoradas com lembrete; comandos de ajuste continuam funcionando.
4. `/session confirm` evicta a sessão, limpa o pending e prepara a próxima mensagem (checkpoint injetado).
5. `reset` cancela pending; `status` mostra pending; `confirm` sem pending dá mensagem clara.
6. `bun test` verde sem regressão (incluindo o guardrail de isolamento SDK).

## Guardrails

**Must have**
- `pending-confirm-store.ts` em `src/sessions/` — escrita atômica `tmp + rename`, `mode 0o600`, padrão do `effort-store.ts`.
- Nenhum `child_process` / `Bun.spawn` em `server.ts` (test `tests/sessions/sdk-isolation-guardrails.test.ts` deve continuar passando). O novo store é fs-only, então é seguro.
- `confirm` NÃO exige `session.reset` permission (qualquer usuário do canal confirma). `reset`/`renew` continuam exigindo `session.reset`.
- Reusar `SessionCheckpointStore.markPendingRenew` / `consumePendingRenew` para a injeção do checkpoint na 1ª mensagem — não duplicar essa lógica.

**Must NOT have**
- Não criar slash command top-level `/confirm` separado — usar subcomando `/session confirm` (evita poluição; decisão do PRD §4).
- Não mexer no `cwd` nem na ordem `--add-dir` dos dirs.
- Não adicionar janitor/timeout automático (out of scope — prune é on-demand).

---

## Steps

### Step 1 — Criar `PendingConfirmStore`
**What:** Novo store persistente por scope, espelhando o padrão de `effort-store.ts`
(fs-only, atômico). Arquivo `pending-confirm.json` no `STATE_DIR`.

**Arquivos:**
- novo: `src/sessions/pending-confirm-store.ts`

**API:**
```typescript
type PendingConfirmEntry = { initiatedAt: string; expiresAt: string }
class PendingConfirmStore {
  constructor(stateDir: string)
  set(scopeKey: string, now?: () => Date): void   // expiresAt = initiatedAt + 15min
  get(scopeKey: string): PendingConfirmEntry | undefined
  remove(scopeKey: string): void
  isExpired(entry: PendingConfirmEntry, now?: () => Date): boolean
  prune(now?: () => Date): void                    // remove expirados
}
const PENDING_CONFIRM_TTL_MS = 15 * 60 * 1000      // exportado p/ reuso
```

**Acceptance:**
- `set` grava `initiatedAt`/`expiresAt`; arquivo com `mode 0o600` via `tmp+rename`.
- `isExpired` retorna `true` quando `now > expiresAt`.
- `get` em scope inexistente → `undefined`; `prune` remove só os expirados.
- `now` injetável para teste determinístico.

**Complexidade:** Baixa.

---

### Step 2 — Enriquecer o summary (`formatNextSessionSummary`)
**What:** Estender o summary para incluir `dirs`, `effort` e `checkpoint`, além de
`engine/agent/model/project` já existentes. Tornar a função exportável (ou extrair uma
`formatPendingConfirmSummary`) para reuso no confirm/status.

**Arquivos:**
- `src/sessions/session-command.ts` — `formatNextSessionSummary`, `SessionCommandDeps`

**Detalhes:**
- Adicionar a `SessionCommandDeps` (todos opcionais, mesmo padrão de `projectContextStore`):
  - `agentStore?: { get(k: string): string | undefined }`
  - `effortStore?: { get(k: string): string | undefined }`
  - `extraDirsStore?: { list(k: string): { path: string }[] }`
- `agent`: preferir `agentStore.get(scope)` → fallback `deps.defaultAgent` → `'oracle'`.
- `dirs`: `extraDirsStore.list(scope)` — listar paths ou `nenhum`.
- `effort`: `effortStore.get(scope)` ou `cli default`.
- `checkpoint`: ler do `checkpointStore.read().checkpoints[key]` → `timestamp — "note"`, ou `nenhum`.
- Acrescentar bloco de instruções de ajuste + rodapé `/session confirm` + aviso de mensagens ignoradas + "expira em 15 min" (texto do PRD §summary).

**Acceptance:**
- Summary mostra as 7 linhas (`engine/agent/model/project/dirs/effort/checkpoint`).
- Sem store correspondente → linha cai em `nenhum`/default sem quebrar.
- Função reutilizável por renew, confirm e status (sem duplicar formatação).

**Complexidade:** Média.

---

### Step 3 — `renew` entra em `pending_confirm` (sem evictar)
**What:** Separar `renew` de `reset` em `handleSessionCommandAction`. `renew` passa a:
salvar checkpoint implícito (reusar caminho de `markPendingRenew`), marcar `pending_confirm`,
e devolver o summary — **sem** `cliSessionStore.delete` nem `supervisor.evictSession`.
`reset` mantém o comportamento atual + limpa qualquer `pending_confirm`. `renew` é idempotente.

**Arquivos:**
- `src/sessions/session-command.ts` — `handleSessionCommandAction`, `SessionCommandDeps` (+`pendingConfirmStore`)

**Detalhes:**
- `SessionCommandDeps.pendingConfirmStore?: PendingConfirmStore`.
- `renew`:
  - se execução ativa → mesma guarda atual (`use /session cancel`).
  - `checkpointStore.markPendingRenew(key)` (mantém injeção na 1ª msg).
  - `pendingConfirmStore.set(scope)`.
  - retorna summary (Step 2) com prefixo "Sessão preparada para reinício."
  - idempotente: se já pending, re-exibe summary atual.
- `reset`: `pendingConfirmStore.remove(scope)` antes do reset normal.

**Acceptance (AC-1, AC-6):**
- `renew` NÃO chama `evictSession`/`delete` (verificar via mock/spy no teste).
- `pending-confirm.json` contém o scope após `renew`.
- `renew` repetido devolve summary sem erro e sem duplicar estado.
- `reset` durante pending limpa o pending e executa reset.

**Complexidade:** Média.

---

### Step 4 — Subcomando `/session confirm`
**What:** Adicionar `confirm` ao builder e ao handler. Confirm evicta sessão, limpa pending,
devolve summary final. Sem pending → mensagem clara. Não exige `session.reset`.

**Arquivos:**
- `src/sessions/session-command.ts` — `buildSessionCommand` (+ subcomando), tipo da action, `handleSessionCommandAction`
- `server.ts` — `handleSessionSlashCommand` (auth + dispatch)

**Detalhes:**
- `buildSessionCommand`: `.addSubcommand(s => s.setName('confirm')...)`.
- Tipo da action: incluir `'confirm'`.
- `handleSessionCommandAction('confirm', ...)`:
  - `const pending = pendingConfirmStore.get(scope)`; se ausente/expirado → `"Nenhum renew pendente para confirmar neste scope."`
  - se ativo: `pendingConfirmStore.remove(scope)`, `cliSessionStore.delete(key)`, `await supervisor.evictSession(key)`.
  - retorna summary final + "Próxima mensagem inicia a sessão."
- `server.ts` `handleSessionSlashCommand`:
  - mapa de operação: `confirm` → **não** roda `authorizeAccess` (qualquer usuário do canal). Apenas `reset/renew`→`session.reset`, `cancel`→`session.cancel`, `save`→`session.write`.
  - passar `pendingConfirmStore`, `agentStore`, `effortStore`, `extraDirsStore` no objeto deps.

**Acceptance (AC-4, AC-9):**
- `confirm` com pending: `pending-confirm.json` perde o scope, sessão evictada (spy), resposta com summary final.
- `confirm` sem pending: mensagem "Nenhum renew pendente...".
- `confirm` não exige permissão de reset.

**Complexidade:** Média.

---

### Step 5 — Interceptar mensagens normais durante pending + `status`
**What:** No handler de `messageCreate` (server.ts, antes de `trySdkInboundOrLegacy` na
linha ~1357), checar pending. Se ativo e não expirado → responder lembrete e `return`.
Se expirado → `remove` e deixar passar. Acrescentar linha de pending ao `/session status`.

**Arquivos:**
- `server.ts` — corpo do handler de mensagem (perto da linha 1357), instanciar `pendingConfirmStore` junto aos demais stores (~linha 80-92)
- `src/sessions/session-command.ts` — branch `status`

**Detalhes:**
- Instanciar `const pendingConfirmStore = new PendingConfirmStore(STATE_DIR)` perto da linha 92.
- Antes de `trySdkInboundOrLegacy`: usar `sessionCtx.scope` já disponível na linha 1328.
  ```ts
  const pending = pendingConfirmStore.get(sessionCtx.scope)
  if (pending && !pendingConfirmStore.isExpired(pending)) {
    await msg.reply('⏳ Aguardando `/session confirm`. Ajuste com `/model`, `/agent`, `/project`, `/dirs`, `/effort` ou confirme.').catch(() => {})
    return
  }
  if (pending) pendingConfirmStore.remove(sessionCtx.scope)
  ```
- `status` branch: se `pendingConfirmStore.get(scope)` ativo, adicionar linha `renew pending: sim (expira em Nmin — use /session confirm ou /session reset)`. Passar `pendingConfirmStore` em `SessionCommandDeps`.
- Garantir: o novo store é fs-only → `server.ts` não ganha `child_process`/`Bun.spawn` (guardrail intacto).

**Acceptance (AC-2, AC-7, AC-8):**
- Mensagem normal durante pending: Oracle NÃO é despachado, lembrete enviado.
- Pending expirado: `remove` + mensagem segue fluxo normal.
- `status` mostra a linha de pending com minutos restantes.

**Complexidade:** Média.

---

### Step 6 — Testes + smoke
**What:** Cobrir o store e os fluxos de comando, validar AC end-to-end, rodar suite e
smoke no Discord.

**Arquivos:**
- novo: `tests/sessions/pending-confirm-store.test.ts`
- `tests/sessions/session-command.test.ts` (ou novo `*-renew-confirm.test.ts`) — fluxos renew/confirm/reset/status
- (verificar) `tests/sessions/sdk-isolation-guardrails.test.ts` continua verde

**Cobertura mínima:**
- Store: set/get/remove/isExpired/prune com `now` injetável (AC-7).
- `renew` marca pending sem evictar (spy em supervisor/cliSessionStore) (AC-1).
- `confirm` evicta + limpa pending (AC-4); `confirm` sem pending (AC-9).
- `reset` limpa pending (AC-6); summary inclui dirs+effort+checkpoint (AC-3 indireto).
- `status` mostra pending (AC-8).
- Interceptação: a verificação de que a 1ª mensagem após confirm injeta checkpoint (AC-5) reusa `prependCheckpointOnce` (já testado) — apenas confirmar que `markPendingRenew` foi chamado no renew.

**Acceptance (AC-10):**
- `bun test` → mesmo número de testes anteriores + novos, 0 fail (baseline 348 pass / 1 skip).
- Smoke manual no Discord: renew → ajuste model → confirm → 1ª mensagem (handoff @oath-verifier / @probe-qa).

**Complexidade:** Média.

---

## Success criteria (checklist)

- [ ] `PendingConfirmStore` criado, fs-only, TTL 15min, atômico (Step 1)
- [ ] Summary com `engine/agent/model/project/dirs/effort/checkpoint` (Step 2)
- [ ] `renew` entra em pending sem evictar; idempotente (Step 3)
- [ ] `/session confirm` evicta + limpa pending; sem permissão de reset (Step 4)
- [ ] Mensagens normais ignoradas durante pending; expiração on-demand; status mostra pending (Step 5)
- [ ] `bun test` verde, guardrail SDK intacto (Step 6)
- [ ] Todos os AC-1..AC-10 do PRD mapeados a evidência

## Mapa AC → Step

| AC | Step |
|---|---|
| AC-1 renew→pending+summary | 2, 3 |
| AC-2 msg ignorada | 5 |
| AC-3 /model set atualiza summary | 2 (summary lê stores ao vivo) |
| AC-4 confirm evicta+limpa | 4 |
| AC-5 checkpoint na 1ª msg | 3 (markPendingRenew) + reuso `prependCheckpointOnce` |
| AC-6 reset cancela pending | 3 |
| AC-7 expira 15min | 1, 5 |
| AC-8 status mostra pending | 5 |
| AC-9 confirm sem pending | 4 |
| AC-10 bun test | 6 |

## Open Questions

- [ ] **`/model set` / `/agent set` durante pending NÃO re-exibem o summary automaticamente** — Risk: baixo. O PRD (AC-3, tabela §"Comportamento por input") diz "executa + exibe summary atualizado", mas hoje esses handlers (server.ts) só confirmam o ajuste. Opção A: cada handler de ajuste, ao detectar pending no scope, anexa o summary atualizado à resposta. Opção B: usuário re-roda `/session renew` (idempotente) para rever. **Recomendação: Opção A** (melhor UX, alinhado ao PRD) — adicionar como sub-tarefa no Step 4/5. Confirmar com Eduardo antes do build.
- [ ] **Subcomando `/session confirm` vs top-level `/confirm`** — Risk: baixo. Plano adota `/session confirm` (recomendação do PRD §4). Confirmar que não há expectativa de `/confirm` curto.

## Handoff

**→ @bolt-executor** (Phase 4 — Build)
- Source: este plano + PRD em `workspace/development/features/discord-plus-renew-confirm/`
- Ordem: Step 1 → 2 → 3 → 4 → 5 → 6
- Aberto: 2 open questions acima (resolver AC-3 auto-summary antes/durante Step 4)
- Esperado: implementação dos 6 steps + suite verde, depois @lens-reviewer (review) e @oath-verifier (verificação evidência-based dos AC-1..AC-10)
- Lembrete crítico: store novo fica em `src/`, NUNCA introduzir `child_process`/`Bun.spawn` em `server.ts` (guardrail `tests/sessions/sdk-isolation-guardrails.test.ts`)
