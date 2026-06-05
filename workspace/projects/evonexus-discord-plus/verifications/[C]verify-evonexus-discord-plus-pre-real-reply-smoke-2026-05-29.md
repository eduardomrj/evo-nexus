---
author: claude
agent: oath-verifier
type: verification-report
date: 2026-05-29
target: evonexus-discord-plus-pre-real-reply-smoke
verdict: INCOMPLETE
confidence: medium
---

# Verification Report — evonexus-discord-plus-pre-real-reply-smoke

## Verdict

**Status:** INCOMPLETE
**Confidence:** medium
**Blockers:** 1

## Evidence

| Check | Result | Command/Source | Output |
|-------|--------|----------------|--------|
| Repo state | pass | `git status --short`; `git rev-parse --abbrev-ref HEAD`; `git rev-parse HEAD` | branch `master`, commit `693173338996b97a32b41b16d3cba96028e57e19`; status limpo antes/depois |
| Tests | pass | `cd /home/evonexus/evo-projects/evonexus-discord-plus && bun test` | 181 pass, 1 skip, 0 fail, 497 expect() calls, 22 files |
| Audit | pass | `cd /home/evonexus/evo-projects/evonexus-discord-plus && bun audit` | No vulnerabilities found |
| Real SDK smoke | pass | `cd /home/evonexus/evo-projects/evonexus-discord-plus && EVONEXUS_DISCORD_PLUS_REAL_SDK_SMOKE=1 bun test tests/sessions/gateway-dispatcher-real-sdk.smoke.test.ts` | 1 pass, 0 fail, 7 expect() calls |
| Shadow probe | pass | local Bun eval using real SDK, stub executor, no Discord token/service | `sideEffectsEnabled=false`, `captured=1`, `executed=1`, `denied=0`, `executedStub=1` |
| Runtime gate | pass | `/home/evonexus/evo-projects/evonexus-discord-plus/src/sessions/sdk-inbound-flag.ts:9-10`; `/home/evonexus/evo-projects/evonexus-discord-plus/server.ts:120-130` | real sender is wired only through `enableReplySideEffects: isSdkReplySideEffectsEnabled()`, and flag is true only when `EVONEXUS_DISCORD_PLUS_SDK_SIDE_EFFECTS === reply` |
| Fallback behavior | pass | `/home/evonexus/evo-projects/evonexus-discord-plus/server.ts:189-198`; `/home/evonexus/evo-projects/evonexus-discord-plus/src/sessions/gateway-intent-executor.ts:26-39`; tests at `tests/sessions/gateway-intent-executor.test.ts:137-165` | `SideEffectStartedError` prevents legacy fallback after side-effect failure |
| Policy v2 restriction | partial | `/home/evonexus/evo-projects/evonexus-discord-plus/ACCESS.md:72-79`; `/home/evonexus/evo-projects/evonexus-discord-plus/tests/auth/runtime-adapter.test.ts:222-243`; `access.json` missing in repo | Code/docs enforce v2 style restrictions, but the real local runtime policy file with production bot/canal/usuário was absent, so exact IDs could not be verified |

## Acceptance Criteria

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | `bun test` passa. | VERIFIED | Fresh run: 181 pass, 1 skip, 0 fail. |
| 2 | `bun audit` passa. | VERIFIED | Fresh run: No vulnerabilities found. |
| 3 | `EVONEXUS_DISCORD_PLUS_REAL_SDK_SMOKE=1 bun test tests/sessions/gateway-dispatcher-real-sdk.smoke.test.ts` passa. | VERIFIED | Fresh run: 1 pass, 0 fail. |
| 4 | Código exige `EVONEXUS_DISCORD_PLUS_SDK_SIDE_EFFECTS=reply` para envio real. | VERIFIED | `isSdkReplySideEffectsEnabled()` returns true only for exact `reply`; server wires this into `enableReplySideEffects`, with `sendSdkReply` only in the real sender path. |
| 5 | Com flag off, smoke real validou shadow: captured=1 executed=1 denied=0, sem envio real. | VERIFIED | Additional read-only shadow probe produced `sideEffectsEnabled=false`, `captured=1`, `executed=1`, `denied=0`, `executedStub=1`. No Discord token/service was used. |
| 6 | Policy v2 do discord-plus está restrita ao bot/canal/usuário corretos. | PARTIAL | V2 policy semantics are documented/tested deny-by-default and channel/user scoped. However `/home/evonexus/evo-projects/evonexus-discord-plus/access.json` does not exist, so exact live bot/canal/usuário could not be inspected without external/runtime config. |
| 7 | Fallback pós-side-effect usa erro tipado e não volta para legacy. | VERIFIED | `SideEffectStartedError` / `isSideEffectStartedError` exists; `trySdkInboundOrLegacy` logs and returns without `legacy()` on typed side-effect error; unit test asserts failed real side-effect throws typed error and no shadow fallback. |

## Gaps

- Policy real de produção não verificada — **Risk:** medium — **Suggestion:** antes do smoke com `EVONEXUS_DISCORD_PLUS_SDK_SIDE_EFFECTS=reply`, inspecionar de forma redigida o `access.json`/config efetivamente carregado pelo serviço e confirmar bot/canal/usuário esperados.

## Regression Risk Assessment

- **Related features checked:** SDK inbound dispatcher, passive intent queue, real SDK smoke, reply side-effect gate, fallback-to-legacy guard, runtime auth adapter.
- **Potentially affected:** próximo smoke real com envio Discord; política runtime fora do repo; configuração do serviço systemd/env.
- **Verified unaffected:** suíte local completa e audit passaram; repo alvo permaneceu limpo após a verificação read-only.

## Recommendation

**NEEDS_MORE_EVIDENCE**

A base técnica está aprovada para preparar o próximo smoke, mas eu não aprovo o smoke real de reply até confirmar a policy runtime real com os IDs corretos e redigidos.

## Follow-ups

- [ ] Verificar a policy efetivamente carregada no runtime, sem imprimir tokens e com IDs sensíveis redigidos se necessário.
- [ ] Executar o próximo smoke real somente com `EVONEXUS_DISCORD_PLUS_REAL_SDK_SMOKE=1` e `EVONEXUS_DISCORD_PLUS_SDK_SIDE_EFFECTS=reply` em bot/canal/usuário allowlisted, sem iniciar serviço Discord real adicional.
