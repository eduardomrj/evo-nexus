---
author: claude
agent: oath-verifier
type: verification-report
date: 2026-05-30
target: discord-plus-fallback-reply
verdict: PASS
confidence: high
---

# Verification Report — Discord Plus fallback assistant text seguro por padrão

## Verdict

**Status:** PASS
**Confidence:** high
**Blockers:** 0

## Evidence

| Check | Result | Command/Source | Output |
|-------|--------|----------------|--------|
| Tests focados | PASS | `cd /home/evonexus/evo-projects/evonexus-discord-plus && bun test tests/sessions/sdk-inbound-runtime.test.ts tests/sessions/gateway-dispatcher.test.ts tests/sessions/sdk-inbound-flag.test.ts tests/sessions/sdk-session-runner.test.ts` | `32 pass`, `0 fail`, `120 expect() calls`, 4 files |
| Suíte completa | PASS | `cd /home/evonexus/evo-projects/evonexus-discord-plus && bun test` | `188 pass`, `1 skip`, `0 fail`, `529 expect() calls`, 22 files. Observação: log não bloqueante `discord models: models.json is corrupt, using default` |
| Diff esperado | PASS | `git -C /home/evonexus/evo-projects/evonexus-discord-plus diff -- ...` | Apenas os 7 arquivos esperados aparecem modificados no status curto |
| Inspeção de gate | PASS | `/home/evonexus/evo-projects/evonexus-discord-plus/src/sessions/sdk-inbound-runtime.ts:46` e `sdk-inbound-flag.ts:14-16` | Runtime usa `allowAssistantTextFallback: options.allowAssistantTextFallback ?? (isSdkAssistantTextFallbackEnabled() || !isSdkReplySideEffectsEnabled())`; env só habilita com `EVONEXUS_DISCORD_PLUS_ASSISTANT_TEXT_FALLBACK === '1'` |
| Inspeção de execução | PASS | `/home/evonexus/evo-projects/evonexus-discord-plus/src/sessions/gateway-dispatcher.ts:85-105` | Fallback só cria intent se não houve tool capturada; intent passa por `authz.allow` antes de `executor.execute`; deny vai para `denied_intents` |

## Acceptance Criteria

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | Side effects reais sem env explícita não converte assistant text | VERIFIED | Teste `side effects reais sem env explícita não converte assistant text` em `/home/evonexus/evo-projects/evonexus-discord-plus/tests/sessions/sdk-inbound-runtime.test.ts:57` passou nos testes focados e suíte completa; implementação em `sdk-inbound-runtime.ts:46` desabilita fallback quando `SDK_SIDE_EFFECTS=reply` e fallback env não é `1`, salvo override explícito de options. |
| 2 | Com env explícita converte e passa por auth/executor | VERIFIED | Teste `side effects reais com env explícita converte assistant text e passa por auth/executor` em `sdk-inbound-runtime.test.ts:89` passou; asserts validam `captured_intents`, `executed_intents`, `allowed` e `executed` com conteúdo `PASS discord-plus semântico`. |
| 3 | Override de options habilita fallback | VERIFIED | Testes `assistant text fallback real passa por auth e executor` e `assistant text fallback real respeita auth deny` em `/home/evonexus/evo-projects/evonexus-discord-plus/tests/sessions/gateway-dispatcher.test.ts:399` e `:436` usam `{ allowAssistantTextFallback: true }` e passaram. |
| 4 | Deny não executa | VERIFIED | Teste `assistant text fallback real respeita auth deny` em `gateway-dispatcher.test.ts:436` passou; asserts validam `executed_intents=[]`, `denied_intents=captured_intents`, `executed=[]`. Implementação em `gateway-dispatcher.ts:98-105` não chama executor quando `authz.allow` retorna falso. |
| 5 | Texto vazio não gera intent | VERIFIED | Teste `assistant text vazio não gera intent` em `gateway-dispatcher.test.ts:468` passou; asserts validam `captured_intents=[]` e `executed_intents=[]`. |
| 6 | Prompt não afirma falsamente que texto normal nunca chega ao Discord | VERIFIED | `/home/evonexus/evo-projects/evonexus-discord-plus/src/sessions/sdk-session-runner.ts:14-16` instrui tool reply como obrigatória e diz que texto normal só pode ser convertido por fallback operacional explicitamente autorizado; teste em `sdk-session-runner.test.ts:131` passou. |
| 7 | Testes solicitados passam | VERIFIED | Comando focado: `32 pass`, `0 fail`; suíte completa: `188 pass`, `1 skip`, `0 fail`. |

## Gaps

- Nenhum blocker encontrado.
- Observação não bloqueante: a suíte completa emitiu `discord models: models.json is corrupt, using default`; não falhou teste, mas é ruído de ambiente/configuração a acompanhar se afetar validações futuras. **Risk:** low — **Suggestion:** investigar em tarefa separada se esse warning crescer ou mascarar configuração real.

## Regression Risk Assessment

- **Related features checked:** runtime SDK inbound, dispatcher de intents passivas, flag/env parsing, instruções do SDK session runner, auth/executor path, comportamento de texto vazio, suíte Bun completa.
- **Potentially affected:** fallback assistant text em modo shadow/default continua permitido quando side effects reais não estão ativos; execução real de reply depende de env/override explícito.
- **Verified unaffected:** tool capturada impede fallback; policy v2 com usuário autoriza reply; policy v2 sem usuário nega; executor denied não vira executed; todos cobertos pela suíte focada/completa.

## Recommendation

**APPROVE**

A mudança atende aos critérios com evidência fresca: fallback fica seguro por padrão para side effects reais, só converte com opt-in explícito/override, e a conversão passa pelo mesmo auth/executor com deny preservado.

## Follow-ups

- [ ] Opcional: registrar/investigar o warning `discord models: models.json is corrupt, using default` se ele aparecer em verificações futuras ou em produção.
