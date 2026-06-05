---
author: claude
agent: compass-planner
type: work-plan
date: 2026-05-28
plan-name: evonexus-discord-plus-sdk-inbound-shadow-blocked
status: proposed
base-commit: e2ef8d0
---

# Work Plan — Discord Plus: SDK inbound shadow/blocked

## Contexto

O projeto `evonexus-discord-plus` está no commit `e2ef8d0 feat(sessions): add flagged SDK inbound dry-run bridge`.

O patch atual habilita o caminho SDK inbound atrás de `EVONEXUS_DISCORD_PLUS_SDK_INBOUND=1`, mas ainda em modo dry-run/passivo, sem side effects reais no Discord. Oath aprovou o patch antes do commit com:

- `bun test tests/sessions tests/auth` → `100 pass`, `1 skip`, `0 fail`
- `bun test` → `151 pass`, `1 skip`, `0 fail`

Apex deu **GO CONDICIONADO** apenas para `reply` real futuro. Raven deu **HOLD** para side effects reais agora. A decisão consolidada é criar uma fase intermediária: **SDK inbound shadow/blocked**.

## Escopo desta fase

Transformar o dry-run em shadow/blocked:

- Resolver o alvo real de cada intent.
- Autorizar contra o recurso real.
- Registrar decisão em outbox/ledger idempotente.
- Preparar contratos para side effects futuros.
- Melhorar lifecycle e observabilidade.
- **Não enviar nada real ao Discord.**

## Fora do escopo

- Não enviar `reply` real.
- Não habilitar `react`, `edit_message`, `download_attachment` ou `fetch_messages` reais.
- Não alterar deploy, systemd, tokens, `.env` ou gateway Discord oficial.
- Não usar `--channels plugin:discord@...` por sessão.
- Não alterar OpenClaude core.

## Passo 1 — Resolver alvo real do intent

### Objetivo

Antes de autorizar qualquer intent, resolver o recurso real que ela pretende tocar.

### Arquivos prováveis

- `src/sessions/gateway-intent-executor.ts`
- novo módulo provável: `src/sessions/discord-intent-target-resolver.ts`
- `server.ts` para adaptar resolução com `client.channels.fetch` / `messages.fetch`
- `tests/sessions/gateway-intent-executor.test.ts`
- novo teste provável: `tests/sessions/intent-target-resolver.test.ts`

### Acceptance criteria

- Dado `reply`, `react`, `edit_message` ou `download_attachment` com `messageId`, quando o `messageId` existir, então o executor resolve `channelId`, `threadId`, `parentChannelId`, `guildId`, `isThread` e `isDm` reais antes da autorização.
- Dado `fetch_messages.channelId` diferente do canal/session atual, quando não houver autorização explícita para esse canal, então a intent é `blocked`, não `ready`.
- Dado `messageId` inexistente ou inacessível, então a intent é `blocked` com reason seguro, sem fallback para `ctx.channelId`.
- Nenhum envio Discord ocorre nesta fase.

### Testes

- Intent com `messageId` em canal autorizado vira `ready`.
- `messageId` apontando para outro canal não autorizado vira `blocked`.
- `fetch_messages.channelId` divergente sem permissão vira `blocked`.
- Regressão: auth context não usa apenas `ctx.channelId`.

### Riscos

- Resolução real pode exigir mocks de Discord.js bem isolados.
- Threads precisam preservar o contrato atual de parent channel.

## Passo 2 — Propagar `requireMention` corretamente

### Objetivo

Side effects derivados de inbound autorizado não devem falhar por perderem o fato de que o inbound passou pelo gate, mas também não podem usar isso para autorizar recurso divergente.

### Arquivos prováveis

- `src/sessions/gateway-dispatcher.ts`
- `src/sessions/gateway-intent-executor.ts`
- `src/sessions/sdk-types.ts`
- `server.ts`

### Acceptance criteria

- Dado inbound guild com `requireMention=true` e mensagem mencionada, quando a intent mira o mesmo recurso autorizado, então `message.mentioned=true` é propagado para a autorização shadow.
- Dado intent mirando recurso diferente do inbound, quando esse recurso também exige mention, então não herda mention do canal original automaticamente.
- Dado DM, a propagação não cria requisito artificial de mention.
- O envelope/dispatch context registra se o inbound passou por mention sem expor conteúdo.

### Testes

- Same-resource + mentioned permite.
- Cross-resource + mentioned original não autoriza recurso divergente.
- Regressão: comportamento legacy do gate permanece intacto.

### Riscos

- Escopo errado pode bloquear respostas legítimas em canais `requireMention`.
- Escopo permissivo demais reintroduz side effect cross-channel.

## Passo 3 — Implementar outbox/ledger shadow

### Objetivo

Registrar cada intent capturada como decisão auditável, sem executar Discord real.

### Arquivos prováveis

- novo módulo provável: `src/sessions/shadow-outbox.ts` ou `src/sessions/intent-ledger.ts`
- `src/sessions/gateway-dispatcher.ts`
- `src/sessions/gateway-intent-executor.ts`
- novo teste provável: `tests/sessions/shadow-outbox.test.ts`

### Estados mínimos

- `planned`
- `blocked`
- `ready`
- `started`
- `sent`
- `failed`

Nesta fase, usar apenas:

- `planned`
- `blocked`
- `ready`

`started`, `sent` e `failed` entram como contrato futuro, sem transição real para envio.

### Acceptance criteria

- Dado intent capturada, quando processada em shadow, então grava registro por `{messageId, intentHash}`.
- Dado a mesma intent reprocessada, então não duplica; atualiza ou retorna o mesmo registro idempotente.
- Dado decisão deny, então estado final shadow é `blocked` com reason seguro.
- Dado decisão allow, então estado final shadow é `ready`, mas sem chamar Discord.
- Ledger não grava prompt, conteúdo completo, token, env, nem raw attachment URL.

### Testes

- Idempotência por `{messageId, intentHash}`.
- Allow → `ready`.
- Deny → `blocked`.
- Conteúdo sensível não aparece no registro.
- Dispatcher retorna intents e ledger correspondente.

### Riscos

- Escolher backend persistente agora pode acoplar demais.
- Recomendação inicial: store injetável/testável ou JSONL em `STATE_DIR`, sem schema pesado.

## Passo 4 — Preparar guardas legacy para execução futura

### Objetivo

Preparar execução real futura reaproveitando proteções existentes do legacy, sem duplicar lógica.

### Proteções a reusar/extrair

- Chunking e limite Discord.
- `assertSendable` para arquivos.
- Limite de anexos.
- `fetchAllowedChannel`.
- Sanitização de nomes em download.
- `noteSent` para reply-to-bot mention futuro.

### Arquivos prováveis

- novo módulo provável: `src/sessions/discord-side-effect-guards.ts`
- `server.ts` futuramente deve importar/reusar, não copiar
- testes novos de guardrails

### Acceptance criteria

- Guardas legacy ficam testáveis fora de `server.ts`.
- Shadow usa os mesmos validadores para classificar `ready`/`blocked`.
- Nenhuma chamada `ch.send`, `msg.react`, `msg.edit` ou download real é feita pelo fluxo shadow.
- Contrato documentado no código: quando futuro side effect entrar em `started`, fallback legacy fica proibido.

### Testes

- Arquivo dentro de state privado é bloqueado.
- Mais de 10 attachments bloqueia.
- Mensagem longa calcula chunks sem envio.
- Guardrail garante que shadow executor não chama métodos reais de Discord.

### Riscos

- `server.ts` é monolítico; extração deve ser mínima e coberta por testes.

## Passo 5 — Lifecycle e observabilidade segura

### Objetivo

Tornar o caminho SDK inbound operável sem side effects reais.

### Arquivos prováveis

- `src/sessions/session-supervisor.ts`
- `src/sessions/sdk-session-runner.ts`
- `src/sessions/gateway-dispatcher.ts`
- `server.ts`
- `tests/sessions/session-supervisor.test.ts`
- `tests/sessions/sdk-session-runner.test.ts`
- `tests/sessions/gateway-dispatcher.test.ts`

### Lifecycle mínimo

- Timeout por dispatch em `sendMessage`.
- Fila/lock por `session_key` para serializar dispatches da mesma sessão.
- Limite máximo de sessões.
- Idle TTL com stop efetivo.
- `stop()` chama `sdkSession.stop` ou `close`.

### Observabilidade segura

Registrar somente:

- `route`
- `session_key`
- `intent_type`
- `decision`
- `reason`
- `duration_ms`
- `fallback_reason`

Não registrar:

- prompt
- conteúdo da mensagem
- token
- env
- raw attachment URL
- texto completo de resposta

### Acceptance criteria

- Dois dispatches simultâneos da mesma `session_key` executam serializados.
- Dispatch travado expira com reason seguro.
- Sessão idle é parada após TTL.
- Ao exceder `max sessions`, nova sessão é bloqueada ou recusada com reason seguro.
- Logs shadow contêm campos permitidos e não contêm conteúdo/prompt/env/token.

### Testes

- Lock por `session_key`.
- Timeout por dispatch.
- Idle TTL chama `stop`.
- Max sessions bloqueia criação nova.
- Logger redige campos proibidos.
- Rodar `bun test tests/sessions tests/auth`.
- Rodar `bun test`.

### Riscos

- Fake timers em Bun podem exigir clock injetável.
- Timeout mal posicionado pode deixar sessão viva sem cleanup.

## Handoff para Bolt

Implementar a fase **SDK inbound shadow/blocked** no projeto `/home/evonexus/evo-projects/evonexus-discord-plus`, partindo do commit `e2ef8d0`.

Resultado esperado:

- Intents capturadas pelo SDK são resolvidas contra alvo real.
- Autorização usa contexto correto.
- Decisões são registradas em outbox/ledger idempotente.
- Intents ficam `ready` ou `blocked`.
- Lifecycle mínimo e logs seguros estão implementados.
- Nenhum side effect real é enviado ao Discord.

## Próximos agentes

- **Bolt:** implementar este plano.
- **Oath:** obrigatório após implementação, validando testes e ausência de side effects reais.
- **Raven:** obrigatório antes de qualquer transição futura `ready → started/sent`.
- **Apex:** chamar apenas se Bolt precisar mudar contrato de ledger persistente ou lifecycle do supervisor.

## Critério de conclusão da fase

A fase só estará concluída quando:

- `bun test tests/sessions tests/auth` passar.
- `bun test` passar.
- Oath confirmar que o fluxo shadow não chama Discord real.
- O ledger/outbox não grava conteúdo sensível.
- Side effects reais permanecerem bloqueados.
