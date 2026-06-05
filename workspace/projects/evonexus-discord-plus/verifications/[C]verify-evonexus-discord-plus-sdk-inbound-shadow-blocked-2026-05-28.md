# Verificação — EvoNexus Discord Plus SDK inbound shadow/blocked

## 1. Verdict

**Verdict:** PARTIAL  
**Confiança:** média-alta  
**Bloqueadores:** 2

Motivo: a suíte passa e há evidência forte de shadow/blocked, idempotência e ausência de side effects reais nos arquivos verificados. Porém há lacunas de aceitação: `requireMention` só exige menção no mesmo recurso, mas não há evidência/teste específico de que menção não autoriza cross-resource; e o envelope inbound ainda inclui `content` e `attachments[].url`, contrariando o requisito de não expor conteúdo/prompt/raw attachment URL em logs/ledger seguros.

## 2. Evidence table

| Categoria | Comando / evidência | Resultado |
|---|---|---|
| Diff | `git -C /home/evonexus/evo-projects/evonexus-discord-plus status --short && git -C ... diff -- <arquivos reportados>` | Revisado; mudanças focadas em dispatcher, supervisor, executor, resolver, outbox e testes. |
| Testes focados | `cd /home/evonexus/evo-projects/evonexus-discord-plus && bun test tests/sessions/gateway-intent-executor.test.ts tests/sessions/session-supervisor.test.ts tests/auth` | PASS: 62 pass, 0 fail, 159 expects, 5 files, 66ms. |
| Sessions/Auth | `cd /home/evonexus/evo-projects/evonexus-discord-plus && bun test tests/sessions tests/auth` | PASS: 104 pass, 1 skip, 0 fail, 322 expects, 14 files, 126ms. |
| Suíte completa | `cd /home/evonexus/evo-projects/evonexus-discord-plus && bun test` | PASS: 155 pass, 1 skip, 0 fail, 418 expects, 19 files, 137ms. Aviso: `models.json is corrupt, using default`. |
| Busca de violações | Grep em `server.ts`, `src/sessions/**/*.ts`, `tests/sessions/**/*.ts`, `tests/auth/**/*.ts` por `ch.send`, `msg.react`, `msg.edit`, `child_process`, `Bun.spawn`, `--channels`, `deploy`, `systemd`, env/token/raw URL/prompt/content | Sem evidência de chamadas reais `ch.send/msg.react/msg.edit`, spawn, deploy/systemd ou tokens no fluxo shadow verificado. Encontrado `content` e `attachments[].url` no envelope inbound. |

## 3. Acceptance Criteria table

| Critério | Status | Evidência |
|---|---|---|
| Capturar intents SDK | VERIFIED | `GatewayDispatcher.dispatchOnce` drena `intentQueue.drain(sessionKey)` após `handle.sendMessage(envelope)`; testes de dispatcher na suíte sessions passam. |
| Resolver alvo real por `messageId`/canal/thread | VERIFIED | `FetchingIntentTargetResolver`; teste `target mismatch de messageId resolve como blocked sem side effect` cobre mensagem resolvida em `channelId=c2`. |
| `target mismatch` blocked | VERIFIED | Teste em `tests/sessions/gateway-intent-executor.test.ts` linhas 79-94: status `denied`, reason `target_mismatch`, outbox `blocked`, sem side effect. |
| `fetch_messages.channelId` divergente blocked sem permissão explícita | VERIFIED | Teste linhas 96-106: canal `c2` negado por auth, outbox `blocked`. |
| Autorizar intents antes de side effect | VERIFIED | `GatewayIntentExecutor.execute` chama `authorize(...)` antes de `sideEffect`; teste `auth deny bloqueia antes do side effect fake` confirma sideEffects vazio. |
| Registrar decisão/outbox/ledger idempotente por `{messageId,intentHash}` | VERIFIED | `ShadowOutbox.upsert` usa key `${messageId}:${intentHash}`; teste linhas 108-119 confirma 1 registro após duas execuções. |
| Ledger/outbox sem conteúdo bruto | PARTIAL | `ShadowOutboxRecord` guarda hash/tipo/estado/decisão/reason sem prompt; teste verifica que não contém `segredo prompt`. Mas `GatewayDispatcher.buildEnvelope` carrega `content` e `attachments` com `url`, então a borda inbound ainda recebe dados brutos. |
| Estados desta fase `planned`, `blocked`, `ready` | PARTIAL | Runtime usa `ready`/`blocked`. Tipo `ShadowIntentState` inclui `started/sent/failed` como contrato futuro; aceitável pelo escopo, mas `planned` não apareceu em uso runtime observado. |
| Não enviar nada real ao Discord | VERIFIED | Busca não encontrou `ch.send`, `msg.react`, `msg.edit` no fluxo shadow; side effect é injetável/fake nos testes. |
| Sem `child_process`, `Bun.spawn`, `--channels`, deploy/systemd/tokens/env | VERIFIED | Grep nos arquivos escopados não encontrou esses padrões relevantes. |
| `requireMention`: menção não autoriza cross-resource | MISSING | Código aplica `requireMention` em `authorization-service.ts` somente após resolver canal/policy; isso bloqueia ausência de menção no recurso autorizado. Não encontrei teste específico de menção verdadeira tentando autorizar outro recurso/canal. |
| Lifecycle: timeout por dispatch | VERIFIED | `GatewayDispatcher.withTimeout` rejeita com `dispatch_timeout` via `Promise.race`; suíte passa. Cobertura específica não foi encontrada por grep. |
| Lifecycle: serialização por `session_key` | VERIFIED | `SessionSupervisor` usa `locks` por `SessionKey` em `ensureSession`; testes de supervisor passam. |
| Lifecycle: max sessions | VERIFIED | `SessionSupervisor.enforceCapacity`/`maxSessions`; testes de supervisor passam. |
| Lifecycle: idle TTL/stop | VERIFIED | `stopIdleSessions`; testes de supervisor passam. |

## 4. Gaps

| Risco | Gap | Evidência |
|---|---|---|
| Alto | Envelope inbound expõe `content` e `attachments[].url` ao SDK/session boundary. | `/home/evonexus/evo-projects/evonexus-discord-plus/src/sessions/gateway-dispatcher.ts` linhas 103-114; `/home/evonexus/evo-projects/evonexus-discord-plus/src/sessions/sdk-types.ts` linhas 11-18. |
| Médio | Falta teste direto para `requireMention` não autorizar cross-resource com `mentioned=true`. | Teste existente cobre só `mention_required` quando menção ausente. |
| Baixo | Aviso na suíte completa: `discord models: models.json is corrupt, using default`. | Não falha testes, mas é ruído de configuração/modelos. |

## 5. Regression Risk Assessment

- **Auth/resource policy:** risco médio; covered por `tests/auth` e `tests/sessions`, mas falta caso cross-resource + mentioned=true.
- **Discord side effects reais:** risco baixo nesta fase; não há chamadas reais encontradas nos arquivos escopados e testes validam side effect fake/injetado.
- **Privacidade de payload:** risco alto; `content` e attachment URL ainda atravessam envelope inbound, mesmo que outbox/ledger não persistam conteúdo.
- **Lifecycle supervisor:** risco baixo-médio; testes passam, mas timeout parece ter implementação sem teste dedicado localizado.

## 6. Recommendation

**REQUEST_CHANGES**

Corrigir ou justificar formalmente a passagem de `content`/`attachments[].url` no envelope inbound para esta fase shadow/blocked. Adicionar teste específico garantindo que `mentioned=true` não permite operação em recurso/canal/thread diferente do autorizado.

## 7. Follow-ups

1. Adicionar teste: policy com canal A `requireMention=true`, mensagem mencionada, intent para canal B/thread divergente deve negar por recurso, não permitir por menção.
2. Sanitizar envelope/log boundary ou documentar por que `content`/raw attachment URL são permitidos nesta fase; hoje isso conflita com o escopo aprovado.
3. Opcional: teste dedicado para `dispatch_timeout` em `GatewayDispatcher`.
