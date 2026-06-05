---
author: claude
agent: oath-verifier
type: verification-report
date: 2026-05-28
target: evonexus-discord-plus reply side effects gate
verdict: INCOMPLETE
confidence: medium
---

# Verification Report — evonexus-discord-plus reply side effects gate

## Verdict

**Status:** INCOMPLETE
**Confidence:** medium
**Blockers:** 1

## Evidence

| Check | Result | Command/Source | Output |
|-------|--------|----------------|--------|
| Tests focados | PASS | `cd /home/evonexus/evo-projects/evonexus-discord-plus && bun test tests/sessions/gateway-intent-executor.test.ts tests/sessions/sdk-inbound-flag.test.ts tests/sessions/sdk-reply-sender.test.ts` | 18 pass, 0 fail |
| Sender isolado | PASS | `cd /home/evonexus/evo-projects/evonexus-discord-plus && bun test tests/sessions/sdk-reply-sender.test.ts` | 5 pass, 0 fail |
| Sessions/Auth | PASS | `cd /home/evonexus/evo-projects/evonexus-discord-plus && bun test tests/sessions tests/auth` | 115 pass, 1 skip, 0 fail |
| Suite completa | PASS | `cd /home/evonexus/evo-projects/evonexus-discord-plus && bun test` | 166 pass, 1 skip, 0 fail; aviso: `discord models: models.json is corrupt, using default` |
| Guardrails SDK | PASS | `cd /home/evonexus/evo-projects/evonexus-discord-plus && bun test tests/sessions/sdk-isolation-guardrails.test.ts` | 7 pass, 0 fail |
| Diff check | PASS | `cd /home/evonexus/evo-projects/evonexus-discord-plus && git diff --check` | exit 0 |
| Runtime/Discord real | NOT RUN | restrição do escopo | Sem deploy, systemd, tokens, `.env` ou smoke real Discord |

## Acceptance Criteria

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | Flag separada `EVONEXUS_DISCORD_PLUS_SDK_SIDE_EFFECTS=reply`, default off; só literal `reply` habilita | VERIFIED | `src/sessions/sdk-inbound-flag.ts` retorna igualdade estrita; teste cobre `{}`, `reply`, `all`, `true`, `1`, `yes`, vazio, espaço |
| 2 | Apenas intent `reply` executa side effect real; demais continuam shadow/blocked | PARTIAL | Executor só chama `sender` quando `enableReplySideEffects && intent.type === 'reply'`; teste confirma `react` não chama sender. Porém `sideEffect` legado ainda é chamado para não-reply quando fornecido no executor, então a garantia depende de runtime não injetar sideEffect real |
| 3 | Ledger/outbox transiciona `ready -> started -> sent|failed`; `started` antes da primeira chamada Discord | VERIFIED | Executor faz `transition(..., 'started')` antes de `sender`; testes validam `sent` e `failed`; sender test confirma chamadas Discord ocorrem dentro do sender |
| 4 | Sender real usa somente `execution.target.resource` resolvido/autorizado; não usa `ctx.channelId` cru | PARTIAL | `fetchMessage` recebe `resource` e usa `resource.channelId`; mas `sendSdkReply` também compara contra `ctx.channelId` em `assertAuthorizedTarget`, então há uso direto de `ctx.channelId` no sender para validação, não para envio |
| 5 | Sem fallback legacy depois de qualquer `started` | VERIFIED | Executor lança `side_effect_started_failed`; `trySdkInboundOrLegacy` retorna sem `legacy()` quando mensagem contém `side_effect_started`; testes cobrem falha sem shadow fallback |
| 6 | Chunking com limites efetivos legacy e cap Discord 2000; falha parcial, timeout e 429 viram `failed`, nunca fallback | VERIFIED | Sender limita a `min(chunkLimit, 2000)`; testes cobrem cap 2000, falha parcial, timeout e 429 sem retry; executor transforma erro em `failed` + `side_effect_started_failed` |
| 7 | Não houve deploy/systemd/tokens/.env/smoke real Discord | VERIFIED | Não executei comandos de deploy/systemd/tokens/.env; buscas por termos proibidos não apontaram alteração de deploy; runtime real não testado por escopo |
| 8 | Ledger/logs sem conteúdo bruto, tokens, URLs sensíveis, anexos privados | VERIFIED | `shadow-outbox.ts` serializa `hasContent`, `hasUrl`, attachmentId e `safeReason`; testes verificam ausência de conteúdo bruto e URL em falha |

## Gaps

- Arquivos novos não aparecem no `git diff --stat` padrão porque estão untracked; precisam ser adicionados antes de commit. **Risk:** medium — **Suggestion:** revisar staging explicitamente.
- Critério 2 não é estruturalmente blindado contra injeção futura de `sideEffect` real em não-reply; hoje o runtime não passa `sideEffect`, mas o executor ainda permite. **Risk:** medium — **Suggestion:** documentar/renomear para shadow-only ou bloquear sideEffect real quando side effects estiverem enabled.
- Critério 4 é funcionalmente seguro para envio, mas não literal: o sender lê `ctx.channelId` para validar target. **Risk:** low/medium — **Suggestion:** se a regra for literal, mover validação para fora do sender ou validar apenas contra `execution.target.resource` + message fetched.

## Regression Risk Assessment

- **Related features checked:** sessions, auth, SDK isolation guardrails, suite completa Bun.
- **Potentially affected:** inbound SDK dry-run fallback, reply sender, shadow outbox, comandos/intercepts legados.
- **Verified unaffected:** `bun test tests/sessions tests/auth` e `bun test` passaram.

## Recommendation

**NEEDS_MORE_EVIDENCE**

A implementação passa nos testes e cobre o gate principal, mas mantenho INCOMPLETE/PARTIAL por duas leituras estritas do escopo: uso de `ctx.channelId` dentro do sender e API ainda permitindo `sideEffect` em não-reply.

## Follow-ups

- [ ] Decidir se `ctx.channelId` no sender é aceitável apenas para validação ou se deve ser removido do sender.
- [ ] Blindar executor para não permitir side effects reais fora de `reply` mesmo por configuração futura equivocada.
- [ ] Incluir explicitamente os arquivos untracked no staging quando for commitar.
