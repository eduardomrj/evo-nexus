# ADR — Discord Bridge v2 channel-compatible com gateway único de outbound

**Status:** proposed — revised after Raven HOLD  
**Data:** 2026-05-19  
**Autor:** Apex + Oracle  
**Modo:** arquitetura proposta revisada a partir das decisões aprovadas da Fase 1 e da crítica Raven  

---

## 1. Contexto

A Discord Bridge v1 provou requisitos operacionais importantes: execução async-first, sessão por canal/tópico, project routing, policy por usuário/canal/projeto, métricas, cancelamento, status, anexos e integração com Agent/Skill/MCP. O problema arquitetural é que esses requisitos ficaram concentrados em um runtime monolítico que mistura Discord, subprocess, stream parsing, sessão, metrics, policy, comandos, anexos, cancelamento e outbound.

A decisão aprovada para a v2 é trocar a fundação: a bridge deve ser compatível com o contrato oficial de Channel/Discord e nenhum texto visível gerado por agente/modelo pode chegar ao Discord fora de um gateway único controlado.

Evidências críticas:

- O guia oficial define Channels como ponte bidirecional entre mensagens externas e uma sessão Claude Code em execução: `/home/evonexus/evo-nexus/docs/guides/channels.md:1-5`.
- O guia oficial separa Discord Channel da integração Discord usada pelo Pulse: `/home/evonexus/evo-nexus/docs/guides/channels.md:102-105`.
- O modo oficial é executado com `claude --channels plugin:discord@claude-plugins-official`: `/home/evonexus/evo-nexus/docs/guides/channels.md:159-170` e `/home/evonexus/evo-nexus/Makefile:169-177`.
- A referência técnica de custom channels exige MCP server local via stdio, capability `claude/channel` e inbound `notifications/claude/channel`: `/home/evonexus/evo-nexus/docs/guides/channels-reference.md:7-23`.
- Outbound bidirecional oficial é modelado como tool MCP `reply(chat_id, text)`: `/home/evonexus/evo-nexus/docs/guides/channels-reference.md:136-174`.
- Inbound deve ser gated por sender ID, não por room/chat: `/home/evonexus/evo-nexus/docs/guides/channels-reference.md:176-190`.
- Eduardo aprovou compatibilidade oficial como mandatória: `/home/evonexus/evo-nexus/workspace/development/plans/discord-bridge-v2/fase-1-discovery-contrato/[C]DCB-v2-decisoes-fase-1.md:22-33`.
- Eduardo aprovou gateway único: `/home/evonexus/evo-nexus/workspace/development/plans/discord-bridge-v2/fase-1-discovery-contrato/[C]DCB-v2-decisoes-fase-1.md:44-50`.
- A decisão final aprovada consolida: contrato oficial mandatário, gateway único obrigatório, múltiplas mensagens com `sequence`, fallback v1 apenas até cutover validado e remoção definitiva de `result.text`, stdout/stderr bruto, prompt como enforcement único, `channel.send` bruto, `interaction.followup.send` livre e milestones textuais livres: `/home/evonexus/evo-nexus/workspace/development/plans/discord-bridge-v2/fase-1-discovery-contrato/[C]DCB-v2-decisoes-fase-1.md:525-543`.

---

## 2. Decisão

Projetar a Discord Bridge v2 como uma arquitetura modular channel-compatible, com fronteiras explícitas e saída visível controlada.

A decisão central:

> `OutboundGateway.reply()` é a única fronteira autorizada para entregar `agent_reply` ao Discord. `OpenClaudeRunner` nunca envia texto ao Discord. `result.text`, stdout, stderr, stream deltas, milestones e fallback bruto são dados internos/auditáveis, não mensagens visíveis.

Mensagens sistêmicas continuam permitidas fora de `bridge_reply`, mas apenas quando forem classificadas como `control`, com texto fixo, metadados operacionais redigidos e sem conteúdo dinâmico gerado pelo agente.

A v2 deve preservar os requisitos reais da v1, mas sem carregar o acoplamento da v1:

- compatibilidade Channel/Discord oficial;
- inbound por contrato channel ou equivalente mínimo;
- outbound único por gateway;
- `bridge_reply` com múltiplas mensagens e `sequence`;
- idempotência por execução/sessão/request/sequence;
- chunking seguro no gateway;
- confirmação real após retorno bem-sucedido da API Discord;
- allowlist/pairing por sender ID;
- policy por usuário, canal e projeto;
- MASTER auditado;
- usuário read-only;
- sessão por canal/tópico/projeto;
- project routing declarativo;
- workspace default explícito e seguro;
- cancelamento real;
- métricas/auditoria redigidas;
- anexos Dia 1 com storage temporário seguro.

---

### 2.1 Decisões pós-Raven incorporadas

Após crítica adversarial Raven com verdict HOLD, Eduardo respondeu às quatro decisões bloqueantes:

1. **Workspace default concreto:** `evo-nexus`.
2. **MASTER no default:** mantém Bash/Agents conforme policy auditada.
3. **Falha parcial de chunk:** registrar parcial, retry apenas do chunk faltante quando seguro, `/last` redigido e nunca reenviar bruto.
4. **Auditoria de resposta entregue:** hash + preview redigido por padrão; conteúdo completo somente com flag explícita e retenção curta.
5. **Anexos no spike:** não entram no spike funcional; no spike entram apenas testes de `AttachmentStore`/segurança com fixtures. Anexos entram no Dia 1 do produto depois que gateway passar.

Estas decisões removem as ambiguidades bloqueantes para o desenho do spike.

---

## 3. Arquitetura modular proposta

### 3.1 Diagrama lógico

```text
Discord API
   |
   v
DiscordAdapter
   |
   +--> CommandRouter --------------------+
   |                                      |
   +--> PolicyEngine                      |
   |                                      |
   +--> ChannelSessionStore               |
   |                                      |
   +--> AttachmentStore                   |
   |                                      |
   +--> OpenClaudeRunner ---- internal ---> MetricsRecorder
   |             |                        |
   |             +---- bridge_reply ------+
   |                         |
   v                         v
OutboundGateway --------> AuditLog
   |
   v
Discord API
```

### 3.2 Regras de dependência

| Módulo | Pode conhecer Discord? | Pode conhecer OpenClaude? | Pode produzir texto visível? |
|---|---:|---:|---:|
| `DiscordAdapter` | Sim | Não diretamente | Apenas `control` fixo e `reaction`; nunca `agent_reply` |
| `CommandRouter` | Não | Não | Não |
| `PolicyEngine` | Não | Não | Não |
| `ChannelSessionStore` | Não | Não | Não |
| `AttachmentStore` | Não | Não | Não |
| `OpenClaudeRunner` | Não | Sim | Não |
| `OutboundGateway` | Sim, por porta de envio | Não | Sim, apenas via contrato |
| `MetricsRecorder` | Não | Não | Não |
| `AuditLog` | Não | Não | Não |
| `CancellationController` | Não | Sim, por handle de execução | Apenas aciona `control` fixo via adapter/gateway |

A v1 atual já demonstra por que esta separação é necessária: existem protocolos Discord-like com `send` e `reply` no runtime atual, abrindo superfície para envio direto: `/home/evonexus/evo-projects/discord-openclaude-bridge/src/discord_openclaude_bridge.py:2448-2477`.

---

## 4. Contratos dos módulos

### 4.1 `DiscordAdapter`

Responsabilidade:

- Receber eventos do Discord.
- Normalizar inbound para `InboundMessage`.
- Aplicar defer/ACK em slash commands lentos.
- Emitir apenas mensagens `control` fixas e `reaction` enum fixo.
- Nunca entregar texto gerado por agente/modelo.

Entrada conceitual:

```text
DiscordEvent {
  discord_user_id
  channel_id
  thread_id?
  interaction_id?
  message_id?
  content?
  attachments[]
  command?
}
```

Saída conceitual:

```text
InboundEnvelope {
  sender_id
  channel_key
  thread_key?
  command?
  content
  attachment_refs[]
  discord_context
}
```

Regra dura:

- `DiscordAdapter` não pode chamar `channel.send`, `message.reply`, `interaction.response.send_message` ou `interaction.followup.send` para conteúdo de agente.
- Para slash commands lentos, pode deferir e responder com mensagens sistêmicas fixas.

Evidência: slash/text commands e defer/follow-up foram marcados como Dia 1/necessários na decisão da Fase 1: `/home/evonexus/evo-nexus/workspace/development/plans/discord-bridge-v2/fase-1-discovery-contrato/[C]DCB-v2-decisoes-fase-1.md:307-327`.

### 4.2 `CommandRouter`

Responsabilidade:

- Classificar inbound como comando sistêmico ou execução de agente.
- Roteia `/status`, `/cancel`, `/start`, `/reset-session`, `/project`, `/session`, `/last`, `/context`, `/help`, `/model`.
- Não executa policy sozinho.
- Não envia Discord diretamente.

Entrada:

```text
InboundEnvelope + PolicyDecision + SessionContext
```

Saída:

```text
CommandAction {
  type: start_execution | status | cancel | reset_session | select_project | help | model | reject
  control_message_key?
  execution_request?
}
```

Regras:

- Comandos sistêmicos podem gerar `control`, mas sem texto dinâmico de agente.
- Comandos textuais continuam como fallback mínimo no Dia 1, conforme decisão: `/home/evonexus/evo-nexus/workspace/development/plans/discord-bridge-v2/fase-1-discovery-contrato/[C]DCB-v2-decisoes-fase-1.md:317-319`.

### 4.3 `PolicyEngine`

Responsabilidade:

- Decidir quem pode chamar, onde pode chamar, quais comandos são permitidos, quais projetos são permitidos e quais tools ficam disponíveis.
- Separar access control de project routing.
- Produzir decisão auditável, não mensagem final.

Entrada:

```text
PolicyRequest {
  user_id
  channel_id
  thread_id?
  project_slug?
  command?
  requested_mode
}
```

Saída:

```text
PolicyDecision {
  allowed: boolean
  reason_code?
  role
  can_write
  can_use_bash
  can_use_agents
  can_use_skills
  allowed_projects[]
  allowed_tools[]
  permission_mode
  audit_fields
}
```

Modelo inicial:

| Role | Escrita | Bash | Agents | Skills Dia 1 | Observação |
|---|---:|---:|---:|---:|---|
| `MASTER` | Sim | Sim | Sim | Não por padrão | Equivalente ao terminal, explicitamente auditado |
| `READ_ONLY` | Não | Não ou restrito | Não por padrão | Não | Pode consultar apenas projetos/canais permitidos |
| `DENIED` | Não | Não | Não | Não | Não dispara execução |

Evidências:

- Eduardo aprovou MASTER com Bash e Agents auditados, e Skills não liberadas no Dia 1: `/home/evonexus/evo-nexus/workspace/development/plans/discord-bridge-v2/fase-1-discovery-contrato/[C]DCB-v2-decisoes-fase-1.md:265-289`.
- Haverá usuário read-only e diferença entre permissão por usuário e por canal: `/home/evonexus/evo-nexus/workspace/development/plans/discord-bridge-v2/fase-1-discovery-contrato/[C]DCB-v2-decisoes-fase-1.md:291-300`.
- A v1 já tem `AccessRole` com `can_write`, `can_use_bash`, `can_use_agents`, `can_use_skills`, `allowed_projects` e `default_workspace`: `/home/evonexus/evo-projects/discord-openclaude-bridge/src/discord_openclaude_bridge.py:213-228`.

### 4.4 `ChannelSessionStore`

Responsabilidade:

- Persistir sessão por canal/tópico/projeto.
- Preservar continuidade terminal-like sem contaminar projetos.
- Recuperar sessão após restart.
- Expirar sessões conforme política futura.

Chave recomendada:

```text
session_key = hash(discord_guild_id, channel_id, thread_id_or_null, project_slug, user_scope_policy)
```

Contrato:

```text
get_or_create_session(channel_key, thread_key?, project_slug, policy_scope) -> SessionContext
reset_session(session_key, preserve_project=true) -> SessionContext
bind_project(channel_key, thread_key?, project_slug) -> void
get_current_project(channel_key, thread_key?) -> ProjectRoute
```

Evidências:

- Sessão por canal/tópico e por projeto foi marcada como Dia 1: `/home/evonexus/evo-nexus/workspace/development/plans/discord-bridge-v2/fase-1-discovery-contrato/[C]DCB-v2-decisoes-fase-1.md:79-81`.
- A v1 já persiste `channel_sessions`, `channel_models`, `channel_modes`, `channel_projects` e onboarding por thread: `/home/evonexus/evo-projects/discord-openclaude-bridge/src/discord_openclaude_bridge.py:915-1075`.
- A v1 já possui get/upsert/delete de projeto e sessão por canal/projeto: `/home/evonexus/evo-projects/discord-openclaude-bridge/src/discord_openclaude_bridge.py:1163-1264`.

### 4.5 `OpenClaudeRunner`

Responsabilidade:

- Construir comando OpenClaude/Claude com cwd, add_dirs, model, permission mode, allowed tools e MCP configs.
- Executar processo em background.
- Capturar stdout/stderr/stream internamente.
- Expor handle de cancelamento/timeout.
- Nunca enviar Discord diretamente.

Contrato:

```text
start_execution(ExecutionRequest) -> ExecutionHandle
cancel(execution_id, reason) -> CancellationResult
collect_result(execution_id) -> RunnerResult
```

`RunnerResult` é interno:

```text
RunnerResult {
  status: succeeded | failed | cancelled | timed_out
  result_text_internal?
  stdout_preview_redacted?
  stderr_preview_redacted?
  tokens?
  cost?
  bridge_reply_called: boolean
  bridge_reply_delivered: boolean
}
```

Regra dura:

- `result_text_internal` nunca é entregue ao Discord.
- Se `bridge_reply` não for chamado, o Discord recebe apenas mensagem fixa de controle.

Evidências:

- A v1 possui `_build_command` e `run_async` com timeout/cancelamento de process group: `/home/evonexus/evo-projects/discord-openclaude-bridge/src/discord_openclaude_bridge.py:1865-1994` e `/home/evonexus/evo-projects/discord-openclaude-bridge/src/discord_openclaude_bridge.py:1996-2075`.
- A v1 parseia stream para extrair `result.text` e deltas: `/home/evonexus/evo-projects/discord-openclaude-bridge/src/discord_openclaude_bridge.py:2363-2403`. Na v2 isso deve permanecer interno.
- A v1 recupera texto de failed stream em erro de chunk: `/home/evonexus/evo-projects/discord-openclaude-bridge/src/discord_openclaude_bridge.py:2417-2428`. Na v2 isso não pode virar outbound.

### 4.6 `OutboundGateway`

Responsabilidade:

- Ser a única fronteira para `agent_reply`.
- Validar token/escopo/estado da execução.
- Aplicar idempotência por sessão/execution/request/sequence.
- Fazer chunking seguro para Discord.
- Confirmar entrega real após retorno da API Discord.
- Auditar sucesso, falha, dedupe e chunking.
- Falhar fechado: nunca fallback para envio bruto.

Contrato conceitual:

```text
reply(ReplyRequest) -> ReplyResult
```

```text
ReplyRequest {
  execution_token
  execution_id
  session_key
  channel_key
  request_id
  sequence
  text
  response_type: agent_reply
  correlation_id?
  metadata {
    agent?
    skill?
    mcp_tool?
    model?
  }
}
```

```text
ReplyResult {
  ok
  state: created | chunked | send_attempted | delivered | failed | deduped | cancelled
  execution_id
  request_id
  sequence
  chunks_total
  chunks_delivered
  discord_message_ids[]
  error_code?
  redacted_error?
}
```

Evidências:

- O item DCB-v2-04 exige centralizar chunking, confirmação de entrega, deduplicação, auditoria e falhas: `/home/evonexus/evo-nexus/workspace/development/plans/discord-bridge-v2/fase-2-arquitetura-fronteiras/[C]DCB-v2-04-especificar-outboundgateway-reply.md:18-30`.
- Estados esperados incluem `created`, `chunked`, `send_attempted`, `delivered`, `failed`, `deduped`, `cancelled`: `/home/evonexus/evo-nexus/workspace/development/plans/discord-bridge-v2/fase-2-arquitetura-fronteiras/[C]DCB-v2-04-especificar-outboundgateway-reply.md:24-29`.
- A v1 já tem limite seguro de reply de 1900 caracteres: `/home/evonexus/evo-projects/discord-openclaude-bridge/src/discord_openclaude_bridge.py:107-114`.
- O MCP atual de `bridge_reply` encaminha callback HTTP com Bearer secret, mas sua assinatura ainda não tem `sequence`: `/home/evonexus/evo-projects/discord-openclaude-bridge/src/bridge_reply_mcp_server.py:26-49`.

### 4.7 `MetricsRecorder`

Responsabilidade:

- Registrar início/fim, duração, status, tokens/custo quando disponíveis, erro redigido, agente/skill/MCP, modelo e policy efetiva.
- Nunca bloquear entrega de resposta.
- Nunca persistir prompt completo por padrão.

Contrato:

```text
record_start(ExecutionStarted)
record_reply_attempt(ReplyAttempt)
record_finish(ExecutionFinished)
record_cancel(CancellationEvent)
```

Campos mínimos:

```text
execution_id
user_id
channel_id/thread_id
project_slug
cwd
add_dirs
model
session_id
allowed_tools
permission_mode
bridge_reply_called
final_status
cost/tokens
redacted_error
```

Evidência: a Fase 1 aprovou essa lista de campos obrigatórios de log: `/home/evonexus/evo-nexus/workspace/development/plans/discord-bridge-v2/fase-1-discovery-contrato/[C]DCB-v2-decisoes-fase-1.md:399-427`.

### 4.8 `AuditLog`

Responsabilidade:

- Persistir eventos auditáveis redigidos.
- Guardar hash ou preview redigido do prompt, não prompt completo por padrão.
- Registrar cwd/add_dirs reais, policy efetiva, entrega, falha, cancelamento e anexos.
- Separar auditoria de transporte.

Contrato:

```text
append(AuditEvent) -> void
get_last_redacted(channel_key, thread_key?, execution_id?) -> RedactedExecutionView
```

Regra:

- Erros no Discord não exibem stack trace.
- `/last` mostra apenas auditoria redigida e, se incluir trecho da resposta, apenas conteúdo já entregue via `bridge_reply`.

Evidências:

- Prompt persistido deve ser preview redigido ou hash: `/home/evonexus/evo-nexus/workspace/development/plans/discord-bridge-v2/fase-1-discovery-contrato/[C]DCB-v2-decisoes-fase-1.md:409-411`.
- Stack trace no Discord foi rejeitado: `/home/evonexus/evo-nexus/workspace/development/plans/discord-bridge-v2/fase-1-discovery-contrato/[C]DCB-v2-decisoes-fase-1.md:417-419`.
- A v1 já contém padrões de redaction para prompt/stdout/stderr/tokens/emails: `/home/evonexus/evo-projects/discord-openclaude-bridge/src/discord_openclaude_bridge.py:115-126`.

### 4.9 `CancellationController`

Responsabilidade:

- Cancelar execução ativa por usuário autorizado.
- Cancelar por timeout.
- Propagar cancelamento ao subprocess/process group.
- Garantir resposta sistêmica fixa, sem stdout/stderr bruto.

Contrato:

```text
cancel(execution_id, requested_by, reason: user | timeout | shutdown) -> CancellationResult
```

```text
CancellationResult {
  accepted
  execution_id
  previous_status
  final_status
  control_message_key
}
```

Evidências:

- `/cancel` real e timeout por execução são Dia 1: `/home/evonexus/evo-nexus/workspace/development/plans/discord-bridge-v2/fase-1-discovery-contrato/[C]DCB-v2-decisoes-fase-1.md:86-88`.
- A v1 já cancela/timeout matando process group: `/home/evonexus/evo-projects/discord-openclaude-bridge/src/discord_openclaude_bridge.py:1996-2075`.
- Testes existentes cobrem timeout/cancel matando process group: `/home/evonexus/evo-projects/discord-openclaude-bridge/tests/test_discord_openclaude_bridge.py:1852-2067`.

### 4.10 `AttachmentStore`

Responsabilidade:

- Receber anexos permitidos.
- Validar tipo, tamanho real, nome sanitizado e storage temporário.
- Produzir referências seguras para prompt, log e Discord.
- Bloquear path traversal e overwrite acidental.

Tipos Dia 1 aprovados:

```text
.pdf, .doc, .docx, .md, .jpg
```

Limite:

```text
10 MB
```

Storage:

```text
pasta temporária do workspace, nunca path sensível
```

Contrato:

```text
save_attachments(execution_id, discord_attachments[]) -> SavedAttachment[]
```

```text
SavedAttachment {
  original_filename
  sanitized_filename
  temp_path
  size_bytes
  mime_type?
  prompt_ref
  audit_ref
}
```

Evidências:

- Eduardo aprovou anexos Dia 1, tipos, limite 10 MB e pasta temp do workspace: `/home/evonexus/evo-nexus/workspace/development/plans/discord-bridge-v2/fase-1-discovery-contrato/[C]DCB-v2-decisoes-fase-1.md:363-395`.
- Normalização exige que paths só apareçam se forem temporários e não sensíveis: `/home/evonexus/evo-nexus/workspace/development/plans/discord-bridge-v2/fase-1-discovery-contrato/[C]DCB-v2-decisoes-fase-1.md:449-450`.
- A v1 já define `MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024`: `/home/evonexus/evo-projects/discord-openclaude-bridge/src/discord_openclaude_bridge.py:86-88`.
- A v1 já sanitiza filename e salva anexos com validação de tamanho real: `/home/evonexus/evo-projects/discord-openclaude-bridge/src/discord_openclaude_bridge.py:2487-2586`.
- Testes atuais cobrem sanitização de traversal, não sobrescrever duplicados e validação de tamanho real: `/home/evonexus/evo-projects/discord-openclaude-bridge/tests/test_discord_openclaude_bridge.py:1089-1183`.

---

## 5. Regras de outbound e classificação de mensagens

### 5.1 Classes de mensagem

| Classe | Origem | Pode ir ao Discord? | Canal permitido | Conteúdo dinâmico de agente? |
|---|---|---:|---|---:|
| `agent_reply` | Agente/modelo/OpenClaude | Sim | Somente `OutboundGateway.reply()` | Sim, porque é a resposta final controlada |
| `control` | Bridge/runtime | Sim | `DiscordAdapter` ou `OutboundGateway` sistêmico | Não |
| `reaction` | Bridge/runtime | Sim | `DiscordAdapter` | Não, enum fixo |
| `audit` | Runtime interno | Não como mensagem normal | `AuditLog`; `/last` redigido | Não bruto |

### 5.2 Mensagens sistêmicas permitidas sem `bridge_reply`

Permitidas:

- ACK imediato com `execution_id`;
- status;
- cancelamento;
- timeout fixo;
- erro fixo;
- help;
- comandos project/model/session;
- reactions enum fixo.

Proibidas:

- `result.text`;
- stdout/stderr bruto;
- stack trace;
- milestones textuais livres;
- deltas de stream;
- fallback bruto de chunk;
- conteúdo dinâmico gerado pelo agente disfarçado de mensagem sistêmica.

Evidências:

- Mensagens sistêmicas permitidas foram aprovadas: `/home/evonexus/evo-nexus/workspace/development/plans/discord-bridge-v2/fase-1-discovery-contrato/[C]DCB-v2-decisoes-fase-1.md:174-176`.
- Mensagens sistêmicas não podem incluir texto dinâmico gerado pelo agente: `/home/evonexus/evo-nexus/workspace/development/plans/discord-bridge-v2/fase-1-discovery-contrato/[C]DCB-v2-decisoes-fase-1.md:182-184`.
- Reações só podem ser enum fixo controlado pela bridge: `/home/evonexus/evo-nexus/workspace/development/plans/discord-bridge-v2/fase-1-discovery-contrato/[C]DCB-v2-decisoes-fase-1.md:162-164`.

---

## 6. Contrato `OutboundGateway.reply()`

### 6.0 Compatibilidade oficial mínima testável

A v2 será chamada de channel-compatible apenas se o spike provar o mapping mínimo entre contrato oficial e gateway custom:

| Contrato oficial | Mapping v2 |
|---|---|
| MCP local via stdio com capability `claude/channel` | Adapter/fixture de spike deve validar handshake ou contrato equivalente documentado |
| Inbound `notifications/claude/channel` | `DiscordAdapter` normaliza para `InboundEnvelope` |
| `content` do channel | `InboundEnvelope.content` |
| `meta.chat_id` ou equivalente | `channel_key` + `session_key` |
| Tool oficial `reply(chat_id, text)` | `OutboundGateway.reply(ReplyRequest)` |
| `chat_id` | Resolve para `channel_key`, `thread_key`, `session_key` e destino Discord autorizado |

Critérios obrigatórios para Grid/Oath:

- Dado um inbound no formato `notifications/claude/channel`, o adapter preserva `sender_id/chat_id` e produz `InboundEnvelope`.
- Dado `reply(chat_id, text)` no contrato oficial, o gateway entrega pelo caminho único e registra idempotência.
- Dado handshake/capability de Channel oficial ou fixture equivalente, o teste comprova que a v2 não está apenas “inspirada” no Channel, mas compatível com o contrato mínimo.

### 6.1 Semântica

`reply()` entrega uma ou mais mensagens finais de agente para o Discord. Cada chamada representa uma unidade sequenciada de resposta, não streaming livre.

A decisão aprovada é: `bridge_reply` Dia 1 aceita múltiplas mensagens com `sequence`: `/home/evonexus/evo-nexus/workspace/development/plans/discord-bridge-v2/fase-1-discovery-contrato/[C]DCB-v2-decisoes-fase-1.md:153-157`.

### 6.2 Idempotência

Chave recomendada:

```text
idempotency_key = hash(session_key, execution_id, request_id, sequence)
```

Regras:

1. Se a mesma chave já está `delivered`, retornar `deduped` sem reenviar.
2. Se a mesma chave está `send_attempted`, bloquear concorrência e retornar estado consistente.
3. Se `sequence` pula ordem esperada, rejeitar com erro seguro.
4. Se token expirado, inválido ou de outra execução, não enviar nada.
5. Se execução já está `cancelled`, rejeitar ou registrar como `cancelled`.

A v1 hoje tem idempotência single-call: `BridgeReplyAlreadySentError` e `reserve_reply()` rejeitam segunda chamada: `/home/evonexus/evo-projects/discord-openclaude-bridge/src/discord_openclaude_bridge.py:522-527` e `/home/evonexus/evo-projects/discord-openclaude-bridge/src/discord_openclaude_bridge.py:555-633`. Isso precisa evoluir para idempotência por `sequence`, não por execução inteira.

### 6.3 Chunking

Regras:

1. Chunking acontece somente no gateway.
2. Limite operacional seguro: 1900 caracteres por chunk.
3. Ordem de chunks preservada.
4. Cada chunk só conta como entregue após retorno bem-sucedido da API Discord.
5. Em falha parcial, não reenviar bruto por outro caminho.
6. Auditoria registra `chunks_total`, `chunks_delivered`, ids Discord e erro redigido.

A v1 já possui `SAFE_REPLY_LIMIT = 1900`: `/home/evonexus/evo-projects/discord-openclaude-bridge/src/discord_openclaude_bridge.py:107-114`.

### 6.4 Entrega real

Estado `delivered` só é válido quando a API Discord retorna sucesso para todos os chunks daquela sequência.

Não basta:

- chamar função de envio;
- escrever no log;
- receber `bridge_reply`;
- concluir subprocess;
- ter `result.text`.

Evidência: DCB-v2-04 exige confirmação real somente após retorno bem-sucedido da API Discord: `/home/evonexus/evo-nexus/workspace/development/plans/discord-bridge-v2/fase-2-arquitetura-fronteiras/[C]DCB-v2-04-especificar-outboundgateway-reply.md:27-29`.

### 6.5 `ExecutionReplyStore` transacional

O gateway precisa de estado canônico próprio para não depender de memória de processo nem de “send_attempted” ambíguo.

Contrato mínimo:

```text
reserve_sequence(execution_id, request_id, sequence) -> reserved | deduped | rejected
mark_chunk_delivered(execution_id, request_id, sequence, chunk_index, discord_message_id) -> void
mark_sequence_delivered(execution_id, request_id, sequence) -> delivered
mark_failed_partial(execution_id, request_id, sequence, delivered_chunks[], redacted_error) -> partial_failed
recover_inflight(lock_timeout_seconds) -> recovered[]
```

Regras:

- `reserve_sequence` é atômico por `execution_id + request_id + sequence`.
- Repetição de sequência já entregue retorna `deduped` e nunca reenvia.
- `sequence` fora de ordem é rejeitada de forma segura.
- Cada chunk entregue salva `discord_message_id` antes de tentar o próximo chunk.
- Restart entre `send_attempted` e `delivered` usa `recover_inflight` para evitar duplicação.
- Lock de envio tem timeout explícito.

### 6.6 Falha parcial de chunk

Decisão aprovada por Eduardo:

> Registrar parcial, retry apenas do chunk faltante quando seguro, `/last` redigido e nunca reenviar bruto.

Política:

1. Se chunk K falha após chunks anteriores entregues, marcar sequência como `partial_failed`.
2. Não reenviar chunks já entregues.
3. Registrar ids dos chunks entregues e erro redigido.
4. Permitir retry apenas dos chunks faltantes quando o estado permitir idempotência segura.
5. `/last` pode mostrar estado parcial redigido.
6. Discord nunca recebe `result.text`, stdout/stderr ou fallback bruto para “compensar” a falha.



## 7. Policy/access model

### 7.1 Separação obrigatória

A v2 deve separar:

```text
Access policy: quem pode fazer o quê.
Project routing: onde a execução roda.
Outbound gateway: como resposta visível sai.
```

Não misturar essas três decisões no handler Discord.

### 7.2 MASTER

MASTER equivale ao terminal, mas auditado:

- pode escrever;
- pode usar Bash;
- pode usar Agents;
- Skills ficam desabilitadas no Dia 1, salvo liberação explícita posterior;
- toda permissão efetiva deve aparecer no log de execução.

Evidência: `/home/evonexus/evo-nexus/workspace/development/plans/discord-bridge-v2/fase-1-discovery-contrato/[C]DCB-v2-decisoes-fase-1.md:265-289`.

### 7.3 Read-only

Read-only:

- pode executar comandos de consulta permitidos;
- não recebe tools de escrita;
- não recebe Bash por padrão;
- não pode selecionar projeto fora da allowlist;
- não pode criar projeto novo;
- não pode acionar execution mode que implique escrita.

Evidência: Eduardo confirmou usuário read-only: `/home/evonexus/evo-nexus/workspace/development/plans/discord-bridge-v2/fase-1-discovery-contrato/[C]DCB-v2-decisoes-fase-1.md:291-292`.

### 7.4 Enforcement concreto de policy no runner

A decisão de policy só é válida se virar comando/ambiente concreto no `OpenClaudeRunner`.

| Role | permission_mode | allowed_tools | blocked_tools | MCPs | cwd/add_dirs |
|---|---|---|---|---|---|
| `MASTER` | modo equivalente ao terminal, auditado | Bash, Agents, leitura/escrita aprovadas pelo projeto | Skills Dia 1, tools fora da policy, paths proibidos | apenas MCPs explicitamente permitidos pelo projeto | registry do projeto ou `evo-nexus` default validado |
| `READ_ONLY` | modo restritivo/read-only | Read, Grep, Glob e comandos de consulta aprovados | Bash, Write, Edit, agentes write-capable, skills, MCPs com side effect | somente MCPs read-only explicitamente permitidos | projetos permitidos; nunca default amplo |
| `DENIED` | nenhum | nenhum | todos | nenhum | não inicia execução |

Critérios obrigatórios:

- Grid/Oath devem verificar o comando montado pelo runner, não apenas a decisão lógica do `PolicyEngine`.
- Usuário sem `can_use_bash` não recebe Bash nem shell equivalente.
- Usuário sem `can_write` não recebe `Write`, `Edit` ou ferramentas com side effect.
- MCP aparentemente “consulta” deve ser classificado como read-only ou side-effect antes de entrar em `allowed_tools`.
- Toda execução audita `role`, `permission_mode`, `allowed_tools`, `blocked_tools`, `project_slug`, `cwd` e `add_dirs`.

### 7.5 Negação

Negação de policy deve produzir mensagem `control` fixa, por exemplo:

```text
Ação negada pela política de acesso deste canal/projeto.
```

Sem revelar:

- paths sensíveis;
- lista completa de permissões;
- stack trace;
- segredo;
- prompt;
- stdout/stderr.

---

## 8. Project routing e workspace default seguro

### 8.1 Registry declarativo

Project routing deve vir de registry declarativo com:

```text
project_slug
repo_path
cwd
add_dirs[]
allowed_users[]
allowed_channels[]
default_model?
default_permission_mode?
```

A v1 já possui `ProjectRoute` com `cwd` e `project_add_dirs`: `/home/evonexus/evo-projects/discord-openclaude-bridge/src/discord_openclaude_bridge.py:191-210`.

### 8.2 Paths proibidos

O registry deve rejeitar:

- `/`;
- `/home`;
- `/home/evonexus`;
- `/home/evonexus/evo-projects` como projeto amplo;
- `.ssh`;
- `.gnupg`;
- secrets;
- `/etc`;
- `/root`.

Evidências:

- Critério de aceite exige rejeitar esses paths: `/home/evonexus/evo-nexus/workspace/development/plans/discord-bridge-v2/fase-1-discovery-contrato/[C]DCB-v2-decisoes-fase-1.md:484-489`.
- A v1 já define broad/sensitive project paths: `/home/evonexus/evo-projects/discord-openclaude-bridge/src/discord_openclaude_bridge.py:59-66`.
- A v1 já valida path sensível e secrets no `ProjectRegistry`: `/home/evonexus/evo-projects/discord-openclaude-bridge/src/discord_openclaude_bridge.py:404-503`.

### 8.3 Sem projeto selecionado

Eduardo decidiu que sem projeto selecionado não deve bloquear execução normal; deve usar workspace default explícito.

Decisão pós-Raven:

```text
default_workspace_slug = evo-nexus
```

Regra arquitetural:

- permitido apenas se `default_workspace_slug=evo-nexus` estiver configurado explicitamente no registry;
- o slug `evo-nexus` deve resolver para path concreto validado e não sensível;
- nunca cair implicitamente em `/home/evonexus`, `/home/evonexus/evo-projects` amplo ou diretório sensível;
- MASTER no default mantém Bash/Agents conforme policy auditada;
- READ_ONLY no default não recebe Bash nem tools de escrita;
- se o default estiver ausente, inválido ou apontar para path proibido, a execução não inicia e retorna mensagem `control` fixa;
- o default deve ser auditado em toda execução com `project_slug=evo-nexus`, `cwd` e `add_dirs`.

Evidências:

- Eduardo decidiu “não” para bloquear sem projeto selecionado: `/home/evonexus/evo-nexus/workspace/development/plans/discord-bridge-v2/fase-1-discovery-contrato/[C]DCB-v2-decisoes-fase-1.md:230-232`.
- `/start` pode rodar com workspace default: `/home/evonexus/evo-nexus/workspace/development/plans/discord-bridge-v2/fase-1-discovery-contrato/[C]DCB-v2-decisoes-fase-1.md:238-242`.
- Normalização pós-Raven definiu `evo-nexus` como workspace default concreto.

---

## 9. Anexos Dia 1

Decisão:

- Anexos entram no Dia 1.
- Tipos permitidos: `.pdf`, `.doc`, `.docx`, `.md`, `.jpg`.
- Limite: 10 MB.
- Storage: pasta temporária do workspace.
- Path pode aparecer no prompt/Discord/log apenas se temporário e não sensível.

Regras adicionais necessárias:

1. Sanitizar filename.
2. Rejeitar path traversal.
3. Rejeitar tipo não permitido.
4. Validar tamanho real baixado, não apenas header.
5. Não sobrescrever arquivo existente.
6. Remover ou expirar arquivos temporários conforme política operacional.
7. Logar apenas path temporário não sensível ou referência redigida.

Evidências já citadas:

- Decisão de anexos: `/home/evonexus/evo-nexus/workspace/development/plans/discord-bridge-v2/fase-1-discovery-contrato/[C]DCB-v2-decisoes-fase-1.md:363-395`.
- Normalização de paths temporários/não sensíveis: `/home/evonexus/evo-nexus/workspace/development/plans/discord-bridge-v2/fase-1-discovery-contrato/[C]DCB-v2-decisoes-fase-1.md:449-450`.
- Implementação v1 de sanitização/storage: `/home/evonexus/evo-projects/discord-openclaude-bridge/src/discord_openclaude_bridge.py:2487-2586`.
- Testes v1 de anexos: `/home/evonexus/evo-projects/discord-openclaude-bridge/tests/test_discord_openclaude_bridge.py:1089-1183`.

### 9.1 Escopo de anexos no spike

- Anexos **não entram no spike funcional** de execução Discord → OpenClaude → gateway.
- No spike, anexos entram apenas como testes de `AttachmentStore`/segurança com fixtures.
- Anexos entram no Dia 1 do produto depois que o gateway passar nos testes de isolamento.

Regras adicionais para o Dia 1 do produto:

- validar MIME real além de extensão;
- tratar todo anexo como conteúdo não confiável e potencial prompt injection;
- usar `attachment_ref` no Discord, não path completo;
- TTL padrão de 24h no spike/testes, configurável depois;
- cleanup idempotente; falha de cleanup deve ser auditada;
- limitar quantidade de anexos por execução;
- storage com permissões restritas.

---

## 10. Riscos e trade-offs
|---|---|---|
| Gateway único obrigatório | Elimina causa-raiz de raw output/chunk leak | Mais código de infraestrutura antes de entregar feature visível |
| `bridge_reply` com `sequence` | Permite múltiplas mensagens sem streaming livre | Exige refatorar idempotência atual single-call |
| Suprimir `result.text` | Fecha bypass principal | Se o agente ignorar `bridge_reply`, usuário recebe fallback fixo sem resposta útil |
| Mensagens sistêmicas fixas | Evita vazamento por erro/status | Menos detalhe operacional no Discord; depende de `/last` redigido para diagnóstico |
| Confirmação real de Discord API | Métrica “entregue” passa a significar entregue | Aumenta complexidade em retries, parcial e dedupe |
| Project routing declarativo | Reduz risco de filesystem amplo/sensível | Exige manutenção de registry e policy por projeto |
| Workspace default permitido | Preserva UX terminal-like sem bloquear usuário | Precisa de default explícito e seguro; default mal configurado vira risco alto |
| Anexos Dia 1 | Preserva requisito de produto aprovado | Aumenta superfície de path traversal, storage leak e prompt injection |
| MASTER equivalente ao terminal | Preserva produtividade de Eduardo | Precisa de auditoria forte; erro de policy tem impacto alto |
| Skills Pós-v2 | Reduz superfície de execução no Dia 1 | Perda temporária de capacidade se usuários esperarem skills via Discord |

---

## 11. Alternativas consideradas

### Alternativa A — Continuar remendando a v1

Rejeitada.

A v1 já contém parte dos mecanismos corretos, mas mantém o problema estrutural: múltiplos conceitos críticos no mesmo runtime e caminhos Discord-like com `send`/`reply`. A própria decisão de Fase 1 remove fallback v1 como base/evolução: `/home/evonexus/evo-nexus/workspace/development/plans/discord-bridge-v2/fase-1-discovery-contrato/[C]DCB-v2-decisoes-fase-1.md:117-121`.

### Alternativa B — Clonar cegamente o plugin oficial Discord

Rejeitada como arquitetura completa.

O contrato oficial é mandatário, mas a bridge local precisa preservar requisitos da v1: project routing, sessão, policy, metrics, status, cancelamento, Agent/Skill/MCP e anexos. O plano geral explicitamente diz para não clonar o oficial cegamente sem preservar requisitos locais indispensáveis: `/home/evonexus/evo-nexus/workspace/development/plans/discord-bridge-v2/[C]index-2026-05-19.md:37-41`.

### Alternativa C — Usar prompt “sempre chame bridge_reply” como controle principal

Rejeitada.

Prompt é orientação, não controle arquitetural. Eduardo aprovou remover prompt como enforcement único: `/home/evonexus/evo-nexus/workspace/development/plans/discord-bridge-v2/fase-1-discovery-contrato/[C]DCB-v2-decisoes-fase-1.md:118-119`.

### Alternativa D — Permitir fallback `result.text` se `bridge_reply` não for chamado

Rejeitada.

Eduardo decidiu que, quando `bridge_reply` estiver habilitado e não for chamado, a bridge não pode enviar `result.text`: `/home/evonexus/evo-nexus/workspace/development/plans/discord-bridge-v2/fase-1-discovery-contrato/[C]DCB-v2-decisoes-fase-1.md:137-147`.

### Alternativa E — Streaming livre

Rejeitada para Dia 1.

Eduardo aprovou múltiplas mensagens com `sequence`, não streaming livre fora de contrato: `/home/evonexus/evo-nexus/workspace/development/plans/discord-bridge-v2/fase-1-discovery-contrato/[C]DCB-v2-decisoes-fase-1.md:153-157` e `/home/evonexus/evo-nexus/workspace/development/plans/discord-bridge-v2/fase-1-discovery-contrato/[C]DCB-v2-decisoes-fase-1.md:441-441`.

---

## 12. Critérios de aceite para Grid/Oath

### 12.0 Compatibilidade Channel

- Dado um inbound no formato `notifications/claude/channel`, quando chega ao adapter, então vira `InboundEnvelope` sem perder `sender_id/chat_id`.
- Dado `reply(chat_id, text)` no contrato oficial, então o gateway entrega via caminho único e registra idempotência.
- Dado bridge rodando via modo channel/custom equivalente, então handshake MCP/capability é validado por teste.

### 12.0.1 Workspace default

- Sem projeto selecionado + default ausente → não executa; mensagem `control` fixa.
- Sem projeto selecionado + default para path proibido → não executa; audit `policy_denied`.
- Sem projeto selecionado + `default_workspace_slug=evo-nexus` válido → execução usa exatamente `cwd/add_dirs` do registry e audita.
- READ_ONLY no default não recebe Bash nem tools de escrita.

### 12.0.2 Sequence/chunking transacional

- `sequence=1,2,3` entrega em ordem.
- `sequence=3` antes de `2` rejeita seguro.
- Repetição de `sequence=1` após delivered retorna `deduped`.
- Falha no chunk K não reenvia chunks já entregues.
- Restart entre `send_attempted` e `delivered` recupera sem duplicar.

### 12.0.3 Slash/text commands

- Slash lento sempre dá defer dentro do limite.
- Text fallback não duplica execução já criada por slash.
- `interaction.followup.send` nunca transporta `agent_reply`.
- `/status` mostra apenas enum/template redigido.

### 12.0.4 Auditoria/redaction

- stdout com token/email/path sensível não aparece no Discord nem no `/last`.
- stack trace nunca aparece no Discord.
- prompt completo não é persistido por padrão.
- `/last` só mostra conteúdo de resposta já entregue via gateway, redigido.

### 12.1 Gateway seguro

- Dado `bridge_reply` habilitado, quando OpenClaude retorna `result.text` sem chamar a tool, então a bridge não envia `result.text` ao Discord.
- Dado `bridge_reply` chamado com token válido, quando callback entrega com sucesso, então a execução é marcada como resposta segura entregue.
- Dado `bridge_reply` chamado duas vezes com mesmo `execution_id/request_id/sequence`, então a segunda chamada é `deduped` ou ignorada sem duplicar Discord.
- Dado `bridge_reply` chamado com `sequence` diferente e válido, então múltiplas mensagens são entregues em ordem.
- Dado token inválido, expirado ou de outra execução, então nenhuma mensagem é enviada.
- Dado erro no callback, então o Discord recebe apenas mensagem sistêmica fixa, sem stdout/stderr bruto.

Base: `/home/evonexus/evo-nexus/workspace/development/plans/discord-bridge-v2/fase-1-discovery-contrato/[C]DCB-v2-decisoes-fase-1.md:456-463`.

### 12.2 Bloqueio de caminhos laterais

- Nenhum output de agente chama diretamente `message.reply`.
- Nenhum output de agente chama diretamente `message.channel.send`.
- Nenhum output de agente chama diretamente `interaction.response.send_message`.
- Nenhum output de agente chama diretamente `interaction.followup.send`.
- Timeout/erro/cancelamento não incluem conteúdo bruto do modelo, stderr ou stack trace.
- Milestones de agente não aparecem como texto livre quando v2 está ativa.

Base: `/home/evonexus/evo-nexus/workspace/development/plans/discord-bridge-v2/fase-1-discovery-contrato/[C]DCB-v2-decisoes-fase-1.md:464-471`.

### 12.3 Must-haves v1 preservados

- `/status` funciona durante execução ativa.
- `/cancel` cancela subprocesso real.
- `/start` cria sessão leve.
- `/reset-session` preserva projeto e recria sessão.
- `/project select` altera cwd/add_dirs da próxima execução.
- Sessão é isolada por canal/tópico/projeto.
- Modelo por canal/tópico é preservado.
- `/last` mostra auditoria redigida.

Base: `/home/evonexus/evo-nexus/workspace/development/plans/discord-bridge-v2/fase-1-discovery-contrato/[C]DCB-v2-decisoes-fase-1.md:473-483`.

### 12.4 Project routing seguro

- Registry rejeita `/`, `/home`, `/home/evonexus`, `/home/evonexus/evo-projects`.
- Registry rejeita `.ssh`, `.gnupg`, secrets, `/etc`, `/root`.
- Execução sem projeto usa apenas workspace default explícito e seguro.
- `cwd` real e `add_dirs` são auditados por execução.

Base: `/home/evonexus/evo-nexus/workspace/development/plans/discord-bridge-v2/fase-1-discovery-contrato/[C]DCB-v2-decisoes-fase-1.md:484-490`.

### 12.5 Access policy

- Usuário não autorizado não dispara execução.
- Usuário autorizado sem `can_write` não recebe tools de escrita.
- Usuário sem `can_use_bash` não recebe Bash.
- Usuário sem projeto permitido não consegue selecionar projeto.
- Todas as permissões efetivas são auditáveis por execução.

Base: `/home/evonexus/evo-nexus/workspace/development/plans/discord-bridge-v2/fase-1-discovery-contrato/[C]DCB-v2-decisoes-fase-1.md:491-497`.

### 12.6 Anexos

- `.pdf`, `.doc`, `.docx`, `.md`, `.jpg` até 10 MB são aceitos.
- Tipo não permitido é rejeitado com mensagem fixa.
- Arquivo acima de 10 MB é rejeitado com mensagem fixa.
- Filename com path traversal é sanitizado ou rejeitado.
- Path persistido/logado é temporário e não sensível.
- Anexo nunca permite leitura fora da pasta temporária.

---

## 13. Plano de spike de 1 dia útil

Objetivo do spike: provar arquitetura/gateway/isolamento. Não implementar todo o Dia 1 amplo.

Base: o documento de decisão explicita que o Dia 1 do produto é amplo, mas o spike continua limitado a provar arquitetura/gateway/isolamento: `/home/evonexus/evo-nexus/workspace/development/plans/discord-bridge-v2/fase-1-discovery-contrato/[C]DCB-v2-decisoes-fase-1.md:444-445`.

### Bloco 0 — Fechar fixtures de contrato

Antes de implementar runtime real, criar fixtures/testes para:

- inbound `notifications/claude/channel` → `InboundEnvelope`;
- `reply(chat_id, text)` → `OutboundGateway.reply(ReplyRequest)`;
- `chat_id` → `channel_key/session_key`;
- `default_workspace_slug=evo-nexus` válido/ausente/inválido;
- `ExecutionReplyStore` com sequence/dedupe/partial failure.

Critério: o spike só começa execução real depois que os contratos mínimos têm testes.

### Bloco 1 — Esqueleto modular

Criar estrutura mínima com:

- `DiscordAdapter`
- `CommandRouter`
- `PolicyEngine`
- `ChannelSessionStore`
- `OpenClaudeRunner`
- `OutboundGateway`
- `AuditLog`
- `MetricsRecorder`
- `CancellationController`

Critério: handlers Discord não contêm lógica de execução, policy ou envio de `agent_reply`.

### Bloco 2 — Gateway + `bridge_reply` sequenciado

Evoluir o contrato atual:

De:

```text
bridge_reply(execution_token, text, reply_to?)
```

Para equivalente com:

```text
execution_token
request_id
sequence
text
metadata?
```

Critério: múltiplas mensagens com `sequence` funcionam sem duplicar.

### Bloco 3 — Supressão de output bruto

Testar:

- OpenClaude retorna `result.text` e não chama `bridge_reply`;
- stdout parcial sensível;
- erro antes da primeira resposta;
- chunk error;
- milestone.

Critério: Discord recebe apenas mensagens fixas permitidas.

### Bloco 4 — Policy + project default seguro

Testar:

- MASTER;
- read-only;
- canal não autorizado;
- projeto não permitido;
- sem projeto selecionado usando default explícito seguro;
- rejeição de broad/sensitive paths.

Critério: execução só ocorre com policy aprovada e cwd auditado.

### Bloco 5 — Cancelamento e status

Testar:

- execução longa;
- `/status`;
- `/cancel`;
- timeout.

Critério: subprocess/process group é encerrado, status final auditado, Discord recebe controle fixo.

### Bloco 6 — Evidência para decisão pós-spike

Produzir relatório com:

- testes executados;
- gaps;
- decisão recomendada: evoluir spike, ajustar uma vez ou derivar do oficial;
- riscos remanescentes.

---

## 14. Questões remanescentes

As decisões bloqueantes do Raven foram respondidas e incorporadas nesta revisão:

- workspace default: `evo-nexus`;
- falha parcial de chunk: registrar parcial, retry seguro do faltante, `/last` redigido, nunca bruto;
- auditoria: hash + preview redigido por padrão;
- anexos: fora do spike funcional, apenas fixtures de segurança.

Questões não bloqueantes para depois do spike:

- formato exato da flag operacional para conteúdo completo com retenção curta;
- TTL definitivo de anexos em produção além do padrão inicial de 24h;
- política de permission relay remoto após validação do gateway;
- quando liberar Skills via Discord.

---

## 15. Root cause

A causa-raiz não é “faltou um null check” nem “o modelo às vezes não chama a tool”. A causa-raiz é arquitetural: a v1 permite que dados de execução e transporte Discord coexistam no mesmo runtime sem uma fronteira única de saída. Isso cria bypasses naturais: `result.text`, stdout/stderr, stream deltas, milestones, `channel.send`, `message.reply`, `interaction.followup.send` e fallback de chunk.

A v2 corrige a causa-raiz ao transformar outbound visível em uma capability controlada, auditável e testável. O runner produz resultado interno; só o gateway entrega `agent_reply`.

---

## 16. Referências

- `/home/evonexus/evo-nexus/workspace/development/plans/discord-bridge-v2/fase-1-discovery-contrato/[C]DCB-v2-decisoes-fase-1.md`
- `/home/evonexus/evo-nexus/workspace/development/plans/discord-bridge-v2/[C]index-2026-05-19.md`
- `/home/evonexus/evo-nexus/workspace/development/plans/discord-bridge-v2/fase-2-arquitetura-fronteiras/[C]DCB-v2-03-definir-arquitetura-modular-fronteiras.md`
- `/home/evonexus/evo-nexus/workspace/development/plans/discord-bridge-v2/fase-2-arquitetura-fronteiras/[C]DCB-v2-04-especificar-outboundgateway-reply.md`
- `/home/evonexus/evo-nexus/workspace/development/plans/discord-bridge-v2/fase-2-arquitetura-fronteiras/[C]DCB-v2-05-definir-policy-sessao-metrics-cancelamento.md`
- `/home/evonexus/evo-nexus/docs/guides/channels.md`
- `/home/evonexus/evo-nexus/docs/guides/channels-reference.md`
- `/home/evonexus/evo-nexus/Makefile`
- `/home/evonexus/evo-projects/discord-openclaude-bridge/src/bridge_reply_mcp_server.py`
- `/home/evonexus/evo-projects/discord-openclaude-bridge/src/discord_openclaude_bridge.py`
- `/home/evonexus/evo-projects/discord-openclaude-bridge/tests/test_discord_openclaude_bridge.py`
