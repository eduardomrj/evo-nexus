---
author: claude
agent: lens-reviewer
type: code-review
date: 2026-05-30
target: evonexus-discord-plus current working tree
verdict: REQUEST_CHANGES
---

# Code Review — evonexus-discord-plus current working tree

## Summary
**Files reviewed:** 13
**Total issues:** 1

### By Severity
- **CRITICAL:** 0
- **HIGH:** 1
- **MEDIUM:** 0
- **LOW:** 0

## Stage 1 — Spec Compliance

| Requirement | Status | Notes |
|---|---|---|
| HIGH anterior: fallback de assistant text não fica ativo por padrão quando há side effects reais `reply`; só ativa com `EVONEXUS_DISCORD_PLUS_ASSISTANT_TEXT_FALLBACK=1` ou override controlado | ❌ MISSING | `server.ts:120` liga side effects reais via `isSdkReplySideEffectsEnabled()`, mas `createSdkInboundRuntime()` é chamado sem `allowAssistantTextFallback` em `server.ts:135-143`. Em `sdk-inbound-runtime.ts:46`, o default fica `isSdkAssistantTextFallbackEnabled() || !isSdkReplySideEffectsEnabled()`. O bug estrutural foi mitigado para runtime real quando env side-effects está exatamente `reply`, mas continua permitindo fallback por default em qualquer modo sem side effects. O requisito explicitamente restringia fallback a env explícita ou override controlado. |
| MEDIUM anterior: prompt não mente sobre texto normal/inércia do transcript | ✅ MET | `sdk-session-runner.ts:14-15` agora obriga tool passiva `reply` e descreve texto normal como conversível somente por fallback operacional explicitamente autorizado. Não há afirmação de que texto normal será enviado automaticamente em todos os casos. |
| Bypass de policy | ✅ MET | `gateway-dispatcher.ts:98-105` passa intents capturadas/fallback por `authz.allow`; no runtime real o executor também chama `authorizeAccess()` em `server.ts:97-99` e bloqueia mismatch em `gateway-intent-executor.ts:112-119`. |
| Deny sem execução | ✅ MET | `gateway-dispatcher.ts:99-105` só chama `executor.execute()` quando `authz.allow()` permite; resultado `denied` do executor entra em `denied_intents`, não em `executed_intents` (`gateway-dispatcher.ts:100-103`). |
| Sem duplicação quando tool `reply` já capturada | ✅ MET | Fallback só é sintetizado quando `capturedIntents.length === 0` em `gateway-dispatcher.ts:84-94`. |
| Texto vazio não gera reply | ✅ MET | `extractAssistantTextFromSdkEvents()` faz trim e retorna `undefined` se vazio (`sdk-assistant-text.ts:19-20`, `23-25`, `46-47`). |
| messageId/thread/canal preservados | ✅ MET | Envelope inclui `messageId`, `channelId`, `threadId` (`gateway-dispatcher.ts:117-129`); fallback usa `messageId: ctx.messageId` (`gateway-dispatcher.ts:88-92`); session key isola thread quando `ctx.isThread && ctx.threadId` (`types.ts:31-36`). Target resolver impede reply/react/edit para mensagem fora do inbound resource (`discord-intent-target-resolver.ts:48-73`). |

## Stage 2 — Code Quality

### Issues Found

#### [HIGH] Fallback de assistant text ainda é default-on fora do env explícito
- **File:** `/home/evonexus/evo-projects/evonexus-discord-plus/src/sessions/sdk-inbound-runtime.ts:46`
- **Issue:** O default de `allowAssistantTextFallback` é `isSdkAssistantTextFallbackEnabled() || !isSdkReplySideEffectsEnabled()`. Isso deixa o fallback ativo por padrão sempre que `EVONEXUS_DISCORD_PLUS_SDK_SIDE_EFFECTS` não é `reply`, mesmo sem `EVONEXUS_DISCORD_PLUS_ASSISTANT_TEXT_FALLBACK=1` e sem override controlado do caller. Como o fallback transforma texto normal do assistant em intent `reply` (`gateway-dispatcher.ts:84-94`), a semântica operacional permanece default-on em parte dos modos.
- **Why it matters:** O finding anterior pedia que o fallback só existisse por opt-in explícito ou override controlado. Manter default-on preserva risco de mensagens normais do transcript virarem reply executável em ambientes shadow/test/legacy e dificulta validar que o modelo só responde via tool passiva. Também mantém divergência perigosa entre modo com side effects reais e outros modos.
- **Fix:** Mudar o default para estritamente opt-in: `allowAssistantTextFallback: options.allowAssistantTextFallback ?? isSdkAssistantTextFallbackEnabled()`. Se houver necessidade de shadow fallback para testes, passar `allowAssistantTextFallback: true` explicitamente no teste/caller controlado, não por negação de `SDK_SIDE_EFFECTS`.

## Security Checklist
- [x] No hardcoded secrets observados nos arquivos revisados
- [x] Inputs de tool passiva exigem strings não vazias (`passive-discord-tools.ts:10-20`)
- [x] Injection de conteúdo tratado como não confiável no prompt (`sdk-session-runner.ts:12-13`)
- [x] XSS não aplicável diretamente ao trecho backend Discord revisado
- [x] Auth/policy aplicada antes de execução de intents (`gateway-dispatcher.ts:98-105`, `gateway-intent-executor.ts:130-137`)

## Code Quality Checklist
- [x] Funções revisadas estão curtas e focadas
- [x] Complexidade ciclomática aceitável nos trechos alterados
- [x] Sem nesting profundo nos fluxos revisados
- [x] Sem duplicação relevante introduzida
- [x] Naming claro para flags e fallback

## Positive Observations
- A correção do prompt é objetiva e reduz a mentira operacional: o modelo agora recebe instrução para usar `reply`, com fallback tratado como exceção autorizada.
- O dispatcher evita duplicação corretamente: se uma tool passiva capturou `reply`, o assistant-text fallback não cria segundo reply.
- A cadeia de target resolution e executor separa bem autorização, guarda de target e side effect, com deny registrado sem execução.

## Recommendation
**REQUEST_CHANGES**

O MEDIUM anterior foi corrigido e os checks de policy/deny/duplicação/vazio/target passam na leitura, mas o HIGH ainda não cumpre o contrato de fallback somente por env explícita ou override controlado.

## Follow-ups
- [ ] Tornar `allowAssistantTextFallback` default-off e habilitar apenas com `EVONEXUS_DISCORD_PLUS_ASSISTANT_TEXT_FALLBACK=1` ou override explícito do caller.
- [ ] Ajustar testes que dependem do comportamento shadow para passar `allowAssistantTextFallback: true` explicitamente.
