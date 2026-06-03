---
author: claude
agent: oracle
type: activation-plan-item
date: 2026-05-08
plan-name: discord-openclaude-bridge
phase: fase-4-integracao-cutover
item-id: F4-05
status: future
kind: EVOLUIR
---

# F4-05 — Sessão persistente OpenClaude por canal/tópico Discord

## Objetivo

Fazer com que cada canal/tópico Discord funcione como uma conversa contínua com o OpenClaude, em vez de cada mensagem ser tratada como uma execução isolada.

O comportamento desejado é:

```text
Discord channel/thread ID
→ sessão OpenClaude persistente
→ mensagens seguintes retomam a mesma conversa
```

Isso permite contexto acumulado dentro do tópico/canal, melhora continuidade e aproxima a experiência de um chat real com agente.

## Estado atual da bridge

Hoje a bridge cria uma execução por mensagem e salva resultado/status no SQLite local, mas ainda não usa `session_id` para continuar a conversa.

O parser já captura `session_id` quando ele aparece no stream JSON do OpenClaude.

Evidência no código atual:

- `OpenClaudeResult` possui `session_id`: `ADWs/routines/evo-projects/discord_openclaude_bridge.py`.
- `parse_openclaude_stream()` captura `event["session_id"]` quando disponível.
- O sucesso da execução grava `session_id` no log, mas não usa esse ID para retomar mensagens futuras.

## Capacidades confirmadas do OpenClaude instalado

Versão instalada:

```text
0.9.2 (OpenClaude)
```

Flags relevantes observadas em `openclaude --help` e `openclaude -p --help`:

```text
-c, --continue
    Continue the most recent conversation in the current directory

-r, --resume [value]
    Resume a conversation by session ID, or open interactive picker with optional search term

--session-id <uuid>
    Use a specific session ID for the conversation (must be a valid UUID)

--fork-session
    When resuming, create a new session ID instead of reusing the original
    (use with --resume or --continue)

--no-session-persistence
    Disable session persistence - sessions will not be saved to disk and cannot be resumed
    (only works with --print)
```

Conclusão: OpenClaude 0.9.2 suporta retomada de sessão por ID via `--resume <session_id>` e também permite usar ID específico via `--session-id <uuid>`.

## Decisão recomendada

Implementar sessão persistente por canal/tópico usando `--resume <session_id>`.

Fluxo recomendado:

1. Primeira mensagem do canal/tópico:
   - criar execução normal;
   - deixar OpenClaude gerar sessão;
   - capturar `session_id` do stream;
   - salvar associação `channel_id/thread_id → session_id`.

2. Mensagens seguintes no mesmo canal/tópico:
   - recuperar `session_id` ativo;
   - chamar OpenClaude com `--resume <session_id>`;
   - atualizar `last_used_at`;
   - se OpenClaude retornar outro `session_id`, atualizar associação.

3. Se `--resume` falhar:
   - responder ao Discord informando que a sessão anterior não pôde ser retomada;
   - criar nova sessão automaticamente ou pedir confirmação, conforme política definida.

## Modelo de dados sugerido

Adicionar tabela SQLite local da bridge:

```sql
CREATE TABLE IF NOT EXISTS channel_sessions (
    channel_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    last_message_id TEXT,
    title TEXT,
    status TEXT NOT NULL DEFAULT 'active'
);
```

Campos:

- `channel_id`: canal/tópico Discord.
- `session_id`: sessão OpenClaude ativa.
- `created_at`: criação da associação.
- `updated_at`: última atualização.
- `last_message_id`: última mensagem Discord processada.
- `title`: nome opcional para UX futura.
- `status`: `active`, `archived`, `reset`, `broken`.

## Mudanças no runner

Adicionar suporte opcional a `resume_session_id`.

Assinatura conceitual:

```python
def run(self, prompt: str, *, resume_session_id: str | None = None) -> OpenClaudeResult:
    ...
```

No comando OpenClaude:

```text
openclaude -p --resume <session_id> ... <prompt>
```

ou, na primeira execução, sem `--resume`.

Importante: manter MCP vazio e `--strict-mcp-config` como hoje para evitar carregar MCPs problemáticos do workspace.

## Comandos Discord recomendados

### `/session`

Mostra a sessão OpenClaude ativa para o canal/tópico:

```text
Sessão ativa: <session_id>
Última atualização: <timestamp>
Status: active
```

### `/new-session`

Cria uma nova sessão para o canal/tópico, sem apagar histórico SQLite.

Comportamento:

- marca sessão antiga como `reset` ou `archived`;
- remove associação ativa ou cria nova no próximo prompt;
- responde com confirmação.

### `/resume session_id:`

Opcional. Permite vincular manualmente um canal/tópico a uma sessão OpenClaude existente.

Deve exigir allowlist e talvez confirmação.

### `/sessions`

Opcional futuro. Lista sessões recentes do canal/tópico.

## UX esperada

### Primeira mensagem

```text
👀 recebido
🛠️ executando
✅ sucesso
```

A bridge salva o `session_id` retornado.

### Mensagem seguinte

A bridge responde com contexto da sessão anterior, sem o usuário precisar repetir tudo.

### Reset

Usuário envia:

```text
/new-session
```

Bot responde:

```text
Nova sessão será criada na próxima mensagem deste tópico.
```

## Riscos

### Contexto acidental entre assuntos

Se o mesmo canal/tópico for usado para assuntos diferentes, a sessão acumulada pode contaminar respostas.

Mitigação:

- preferir mapear por thread/tópico, não por canal amplo;
- oferecer `/new-session` fácil;
- mostrar sessão atual com `/session`.

### Sessão expirada ou inválida

`--resume <session_id>` pode falhar se a sessão não existir mais ou estiver corrompida.

Mitigação:

- capturar erro;
- marcar sessão como `broken`;
- responder com instrução clara;
- permitir criar nova sessão automaticamente.

### Privacidade

Sessão persistente acumula contexto. Não permitir que usuário não autorizado acesse canal/tópico com sessão de outro usuário.

Mitigação:

- manter allowlist atual;
- futuramente adicionar guild/role allowlist;
- registrar `user_id` dono da sessão, se necessário.

### Crescimento de storage

Muitas sessões podem acumular registros no SQLite.

Mitigação:

- comando futuro `/sessions prune` ou rotina de limpeza;
- arquivar sessões antigas por TTL.

## Critérios de aceite

- Primeira mensagem em um tópico cria/captura `session_id`.
- Segunda mensagem no mesmo tópico chama OpenClaude com `--resume <session_id>`.
- `/session` mostra sessão ativa.
- `/new-session` reseta a associação sem apagar histórico.
- Erro de resume é tratado sem derrubar a bridge.
- Testes automatizados cobrem:
  - primeira execução sem session;
  - captura e persistência de `session_id`;
  - segunda execução com `--resume`;
  - reset de sessão;
  - falha de resume.

## Decisões pendentes

1. Mapear sessão por `channel_id`, por `thread_id` ou por combinação `guild_id + channel_id + thread_id`.
2. Definir se `/new-session` cria sessão imediatamente com `--session-id` ou apenas limpa a associação para a próxima mensagem.
3. Definir se a bridge deve usar `--resume <session_id>` ou `--session-id <uuid>` para controle mais explícito.
4. Definir TTL/arquivamento de sessões antigas.
5. Definir se cada usuário terá sessão separada dentro do mesmo tópico ou se a sessão é compartilhada por tópico.
