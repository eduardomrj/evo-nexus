---
author: claude
agent: oath-verifier
type: verification-report
date: 2026-05-27
target: evonexus-discord-plus — modelo LLM por canal (Fases 1–3)
verdict: PASS
confidence: high
---

# Verification Report — evonexus-discord-plus: modelo LLM por canal (Fases 1–3)

## Verdict

**Status:** PASS
**Confidence:** high
**Blockers:** 0

## Evidence

| Check | Result | Command/Source | Output |
|-------|--------|----------------|--------|
| Tests | PASS | `bun test` (cwd: /home/evonexus/evo-projects/evonexus-discord-plus) | 79 pass, 0 fail, 160 expect() calls, 7 files, 118ms |
| Types | N/A — projeto usa Bun; sem tsc separado | — | — |
| Lint | N/A — sem eslint configurado | — | — |
| Build | PASS implícito | `bun test` roda transpile on-the-fly; 0 erros de compilação | — |
| Runtime | N/A — smoke real requer Discord; fora do escopo desta verificação | — | ver gotcha em agent-memory |

Nota: a linha `discord models: models.json is corrupt, using default` no output de teste é intencional — produzida pelo teste `JSON corrompido retorna default e renomeia arquivo` em `model-store.test.ts:65`.

## Acceptance Criteria

### Fase 1 — Model Registry

| # | Critério | Status | Evidência |
|---|----------|--------|-----------|
| F1-01 | Sem `models.json` → resolver usa default sem falhar | VERIFIED | `model-store.test.ts:21` — "retorna default quando models.json não existe"; `model-store.ts:67-69` captura ENOENT e retorna DEFAULT_STORE |
| F1-02 | Com preferência de canal → retorna modelo do canal | VERIFIED | `model-resolver.test.ts:19` — "preferência de canal retorna modelo do canal"; resolve para `codexspark` com scope `guild:g1:channel:c1` |
| F1-03 | Com preferência de thread → retorna modelo da thread | VERIFIED | `model-resolver.test.ts:29` — "preferência de thread retorna modelo da thread"; resolve para scope `guild:g1:thread:t1` |
| F1-04 | Thread sem preferência herda canal pai | VERIFIED | `model-resolver.test.ts:44` — "thread sem preferência herda canal pai"; `model-resolver.ts:51-57` implementa fallback para channelKey quando thread não tem pref |
| F1-05 | JSON corrompido → fallback para default + log sanitizado | VERIFIED | `model-store.test.ts:65` — "JSON corrompido retorna default e renomeia arquivo"; `model-store.ts:70-72` escreve em stderr sem conteúdo do JSON; arquivo corrompido renomeado com timestamp |
| F1-06 | Campos perigosos (`env`, `token`, `cli_command`, `Authorization`) não são preservados | VERIFIED | `model-store.test.ts:84` — "descarta preferência com campo env"; `model-store.ts:19-29` — `DANGEROUS_KEYS` Set com todos os 4 campos; `sanitizePreference` retorna null se qualquer chave perigosa presente |
| F1-07 | Allowlist aceita apenas `codexplan` e `codexspark` | VERIFIED | `types.ts:1` — `MODEL_ALLOWLIST = ['codexplan', 'codexspark'] as const`; `model-store.test.ts:98` — "descarta preferência com modelo fora da allowlist" (gpt-9000-turbo rejeitado) |

### Fase 2 — Autorização

| # | Critério | Status | Evidência |
|---|----------|--------|-----------|
| F2-01 | Operação `model.preference.write` existe em `src/auth/types.ts` | VERIFIED | `auth/types.ts:10` — `'model.preference.write'` na union `AuthorizationOperation` |
| F2-02 | Usuário sem `model.preference.write` → nega sem persistir alteração | VERIFIED | `authorization-service.test.ts:197` — "model.preference.write é negado quando ausente da lista de operações"; `server.ts:900-903` verifica `authDecision.effect !== 'allow'` e retorna antes de chamar `setPreference` |
| F2-03 | Usuário autorizado no canal → consegue alterar preferência | VERIFIED | `authorization-service.test.ts:179` — "model.preference.write é permitido quando na lista de operações do usuário"; `server.ts:912-915` executa `setPreference` somente após allow |
| F2-04 | Operações existentes sem regressão | VERIFIED | 79/79 testes passam incluindo todos os testes de `legacy-access-adapter.test.ts` e `runtime-adapter.test.ts` (38 testes pré-existentes) |

### Fase 3 — Comando /model

| # | Critério | Status | Evidência |
|---|----------|--------|-----------|
| F3-01 | `/model` e `/model current` mostram modelo efetivo e escopo | VERIFIED | `model-command.test.ts:11,16` — parse correto; `server.ts:888-891` chama `resolveModel` + `formatCurrentModel` + `return` |
| F3-02 | `/model set codexplan` salva preferência | VERIFIED | `model-command.test.ts:36` — parse retorna `{action:'set', model:'codexplan'}`; `server.ts:912-915` executa `setPreference` |
| F3-03 | `/model set codexspark` salva preferência | VERIFIED | `model-command.test.ts:41` — parse retorna `{action:'set', model:'codexspark'}`; mesmo caminho em `server.ts:912-915` |
| F3-04 | `/model reset` remove preferência local | VERIFIED | `model-command.test.ts:32` — parse retorna `{action:'reset'}`; `server.ts:918-922` chama `removePreference` + `return` |
| F3-05 | `/model list` mostra allowlist | VERIFIED | `model-command.test.ts:27` — parse retorna `{action:'list'}`; `server.ts:883-885` chama `formatModelList()` + `return` |
| F3-06 | Modelo fora da allowlist → erro claro, sem alterar state | VERIFIED | `model-command.test.ts:46` — "model set inválido → invalid com razão" (gpt-9000 rejeitado, razão contém o nome); `server.ts:894-896` retorna o `modelCmd.reason` antes de tocar no store |
| F3-07 | `/model` nunca chama `mcp.notification()` | VERIFIED | `server.ts:870-926` — bloco `/model` inteiro dentro de `if (modelCmd !== null)` com `return` em todos os branches (linhas 885, 891, 896, 903, 909, 915, 922, 925); `mcp.notification()` em linha 952 está após `}` do bloco (linha 926), fora de alcance |

### Regressão

| # | Critério | Status | Evidência |
|---|----------|--------|-----------|
| R-01 | `bun test` passa todos os 79 testes | VERIFIED | Output direto: `79 pass / 0 fail / 160 expect() calls / Ran 79 tests across 7 files [118.00ms]` |
| R-02 | Zero falhas | VERIFIED | Idem acima |

## Gaps

Nenhum gap identificado nas Fases 1–3.

Observação: as Fases 4–6 (slash command real, aplicação no spawn OpenClaude, Session Supervisor) não fazem parte do escopo desta verificação.

## Regression Risk Assessment

- **Features verificadas:** autorização (legacy-access-adapter, runtime-adapter, authorization-service), inbound handler (server.test.ts), model store, model resolver, model command
- **Potencialmente afetado:** fluxo de inbound em `handleInbound` — verificado via `server.ts:870-926` que o intercept retorna antes de typing/ack/notification
- **Verificado não afetado:** botões `perm:*` (linha `server.ts:764` — `if (!interaction.isButton()) return` permanece intacto; nenhuma alteração em `interactionCreate`)

## Recommendation

**APPROVE**

Todas as 21 criterios das Fases 1–3 foram verificadas com evidência direta (arquivo:linha + output de testes frescos). 79/79 testes passando. Nenhum bloqueador.

## Follow-ups

- Fase 4 (slash command Discord real) aguarda aprovação para implementação
- Smoke manual no Discord requer plugin carregado com `openclaude --plugin-dir` (fora do escopo desta verificação estática)
