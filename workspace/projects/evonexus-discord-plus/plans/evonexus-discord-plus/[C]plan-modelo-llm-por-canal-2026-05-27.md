---
author: claude
agent: oracle
type: work-plan
date: 2026-05-27
plan-name: evonexus-discord-plus-modelo-llm-por-canal
status: planned
mode: direct
source: oracle-consultoria-com-apex-scout-compass
---

# Work Plan — evonexus-discord-plus: modelo LLM por canal

## Contexto

Eduardo quer que o Discord Plus permita configurar o modelo LLM por canal/thread/DM e, se possível, alterar essa preferência pelo Discord usando `/model`. A sessão deve usar **OpenClaude como padrão**, não `claude`, para permitir providers como Codex/OpenRouter/OpenAI.

Validação pré-planejamento concluída com Scout, Apex e Compass:

- O plugin Discord Plus é um **MCP/channel**: conecta Discord à sessão Claude/OpenClaude, mas não escolhe modelo.
- O modelo pertence ao processo que inicia a sessão (`claude`/`openclaude`) no spawn.
- OpenClaude suporta providers/modelos; neste workspace o provider ativo é `codex_auth`, com `cli_command=openclaude` e `OPENAI_MODEL=codexplan`.
- O plugin local pode ser carregado via:

```bash
openclaude \
  --plugin-dir /home/evonexus/evo-projects/evonexus-discord-plus \
  --channels plugin:discord@inline
```

## Veredito

É possível implementar **modelo LLM por canal**, mas não dentro do plugin MCP sozinho.

A arquitetura correta é adicionar uma camada de **Session Supervisor / Launcher** acima do plugin:

```text
Discord
  ↓
Discord Plus plugin
  ↓
policy v2 autoriza usuário/operação
  ↓
models.json resolve modelo por canal/thread/DM
  ↓
Session Supervisor inicia OpenClaude
  ↓
openclaude com provider/model correto
```

Não tentar hot-swap de modelo em sessão viva. O comando `/model` deve alterar preferência persistida e aplicar na próxima sessão ou por restart controlado.

## Guardrails

### Must Have

- Usar OpenClaude como caminho padrão para providers não-Anthropic.
- Preservar policy v2 sem perfis: usuário Discord + recurso + operação explícita.
- Separar autorização (`access.json`/policy v2) de preferência operacional (`models.json`).
- Autorizar alteração de modelo com operação explícita, ex. `model.preference.write`.
- Validar modelo/provider por allowlist; nunca aceitar env arbitrário vindo do Discord.
- Não imprimir tokens, env completo, prompts, secrets ou conteúdo sensível.
- `/model` não pode virar prompt para o LLM.

### Must NOT Have

- Não guardar modelo dentro de `access.json` como parte da policy.
- Não reintroduzir perfis/papéis.
- Não usar `claude` como default do novo launcher.
- Não prometer troca de modelo em sessão viva sem restart.
- Não permitir que duas sessões respondam no mesmo canal/thread.

## MVP recomendado

Implementar primeiro:

1. `models.json` + resolver por escopo.
2. Operação de autorização `model.preference.write`.
3. `/model` textual como MVP, interceptado antes do envio ao LLM.
4. Resposta clara: “modelo alterado; vale para a próxima sessão”.
5. Testes unitários e integração local.

Depois:

6. Slash command real `/model`.
7. Session Supervisor com lock/restart controlado.

## Fase 1 — Model Registry persistente

### Objetivo

Criar armazenamento próprio de preferência de modelo, separado de `access.json`, em `models.json` dentro do `STATE_DIR`.

### Arquivos previstos

No repo `/home/evonexus/evo-projects/evonexus-discord-plus`:

```text
src/models/types.ts
src/models/model-store.ts
src/models/model-resolver.ts
```

### Formato proposto

```json
{
  "version": 1,
  "default": {
    "provider": "codex_auth",
    "cli_command": "openclaude",
    "model": "codexplan"
  },
  "preferences": {
    "guild:<guildId>:channel:<channelId>": {
      "provider": "codex_auth",
      "model": "codexplan"
    },
    "guild:<guildId>:thread:<threadId>": {
      "provider": "codex_auth",
      "model": "codexspark"
    },
    "dm:<userId>": {
      "provider": "codex_auth",
      "model": "codexplan"
    }
  }
}
```

### Regras de chave

- Canal: `guild:{guildId}:channel:{channelId}`
- Thread: `guild:{guildId}:thread:{threadId}`
- DM: `dm:{userId}`

### Fallback recomendado

1. Thread específica.
2. Canal pai, se thread não tiver preferência.
3. DM.
4. Default `codex_auth/openclaude/codexplan`.

### Critérios de aceite

- Sem `models.json`, resolver usa default sem falhar.
- Com preferência de canal, resolver retorna modelo do canal.
- Com preferência de thread, resolver retorna modelo da thread.
- Thread sem preferência herda canal pai.
- JSON corrompido falha para default e registra erro sanitizado.
- Campos perigosos/desconhecidos como `env`, `token`, `cli_command` vindo do usuário não são preservados.

## Fase 2 — Autorização v2 para alteração de modelo

### Objetivo

Adicionar operação explícita para permitir alterar preferência de modelo.

### Arquivos previstos

```text
src/auth/types.ts
src/auth/authorization-service.ts
tests/auth/*
```

### Operação proposta

```ts
'model.preference.write'
```

### Critérios de aceite

- Usuário sem `model.preference.write` não altera `models.json`.
- Usuário autorizado no canal consegue alterar preferência.
- DM autorizado com essa operação funciona.
- Canal/thread não permitido nega antes de persistir alteração.
- Operações existentes não sofrem regressão.

## Fase 3 — Comando textual `/model` como MVP

### Objetivo

Interceptar `/model` antes da entrega ao Claude/OpenClaude, evitando que o comando vire prompt.

### Arquivos previstos

```text
server.ts
src/models/model-command.ts
```

### Local provável

Em `handleInbound`, depois de `gate(msg)` e do bloco de permissão textual, antes do typing/ack/`mcp.notification()`.

Referências mapeadas:

```text
server.ts:820  messageCreate
server.ts:825  handleInbound
server.ts:848  intercept textual existente
server.ts:889  mcp.notification
```

### Sintaxe MVP

```text
/model
/model current
/model set codexplan
/model set codexspark
/model reset
/model list
```

### Critérios de aceite

- `/model` mostra modelo efetivo e escopo.
- `/model set codexplan` salva preferência no escopo atual.
- `/model set codexspark` salva preferência no escopo atual.
- `/model reset` remove preferência local.
- `/model list` mostra allowlist permitida.
- Modelo inválido gera erro claro e não altera state.
- Usuário sem permissão recebe negação e não altera state.
- `/model` não chama `mcp.notification`.

## Fase 4 — Slash command real `/model`

### Objetivo

Adicionar suporte real a Discord slash command, mantendo botões `perm:*` funcionando.

### Arquivos previstos

```text
server.ts
src/models/model-command.ts
```

### Local provável

`interactionCreate` hoje só trata botões. Ajustar para fluxo separado:

1. `interaction.isButton()` mantém handler atual.
2. `interaction.isChatInputCommand()` e `commandName === 'model'` processa `/model`.
3. Outras interações retornam sem efeito.

### Subcomandos sugeridos

```text
/model current
/model set model:<string>
/model reset
/model list
```

### Critérios de aceite

- Botões `perm:*` continuam sem regressão.
- Slash command usa a mesma autorização e lógica do comando textual.
- Respostas podem ser ephemeral para reduzir ruído.
- Slash real não expõe secrets ou env.

## Fase 5 — Aplicar preferência no spawn OpenClaude

### Objetivo

Garantir que o modelo resolvido por canal/thread/DM chegue ao processo OpenClaude que atende aquela sessão.

### Caminho esperado

O launcher/session manager deve iniciar sessão com:

```text
cli_command = openclaude
provider = codex_auth
OPENAI_MODEL = codexplan | codexspark | modelo allowlisted
```

### Regras

- Não aceitar `cli_command` arbitrário via Discord.
- Para Codex OAuth, usar aliases (`codexplan`, `codexspark`), não nomes crus como `gpt-5.4`.
- Se sessão já estiver viva, MVP informa que vale na próxima sessão.
- Arquitetura final pode suportar restart controlado.

### Critérios de aceite

- Canal com preferência `codexplan` inicia sessão com `OPENAI_MODEL=codexplan`.
- Canal com preferência `codexspark` inicia sessão com `OPENAI_MODEL=codexspark`.
- Canal sem preferência usa default OpenClaude/codexplan.
- Nenhum log imprime env completo ou secrets.

## Fase 6 — Session Supervisor com lock por `session_key`

### Objetivo

Evitar duas sessões simultâneas para o mesmo canal/thread e permitir restart seguro quando modelo muda.

### Arquivos possíveis

```text
src/sessions/session-supervisor.ts
src/sessions/session-lock.ts
src/sessions/types.ts
```

### Session keys

```text
discord:guild:{guildId}:thread:{threadId}
discord:guild:{guildId}:channel:{channelId}
discord:dm:{userId}
```

### Responsabilidades

- Manter lock por `session_key`.
- Controlar estado `starting | running | stopping | stopped`.
- Registrar modelo aplicado no spawn.
- Reiniciar sessão com motivo `model_changed` quando solicitado.
- TTL/idle cleanup no futuro.

### Critérios de aceite

- Duas mensagens simultâneas no mesmo canal criam no máximo uma sessão.
- Mensagens em canais diferentes podem criar sessões separadas.
- `/model set --restart`, se implementado, encerra e recria sessão com modelo novo.
- Falha de restart gera erro claro, sem loop infinito.

## Testes recomendados

### Unitários

- `model-store`: cria default quando arquivo não existe.
- `model-store`: salva/remove preferência por canal, thread e DM.
- `model-resolver`: aplica fallback thread → canal → default.
- `model-command`: parseia `/model`, `/model set`, `/model reset`, `/model list`.
- `model-command`: rejeita modelo fora da allowlist.
- `authorization-service`: autoriza/nega `model.preference.write`.
- Regressão: operações existentes continuam passando.

### Integração

- Mensagem comum ainda chega em `mcp.notification`.
- `/model` textual não chega em `mcp.notification`.
- Slash `/model` não quebra botões `perm:*`.
- Preference persiste após reload.
- Thread usa chave de thread quando configurada explicitamente.
- DM usa `dm:{userId}`.

### Smoke manual

```bash
openclaude \
  --plugin-dir /home/evonexus/evo-projects/evonexus-discord-plus \
  --channels plugin:discord@inline
```

No Discord:

1. Em canal autorizado, enviar `/model`.
2. Enviar `/model set codexplan`.
3. Enviar pergunta normal.
4. Confirmar que nova sessão usa modelo selecionado.
5. Com usuário sem permissão, tentar `/model set codexspark` e confirmar negação.
6. Em thread, configurar modelo e confirmar que não altera canal pai.

## Riscos e mitigação

| Risco | Severidade | Mitigação |
|---|---:|---|
| Troca de modelo em sessão viva gera comportamento inconsistente | Alta | MVP: vale na próxima sessão; final: restart controlado |
| Misturar policy com preferência operacional | Média | `models.json` separado de `access.json` |
| Injeção por provider/model arbitrário | Alta | Allowlist; nunca aceitar env arbitrário |
| Duas sessões respondendo no mesmo canal | Alta | Session Supervisor com lock por `session_key` |
| Regressão em botões de permissão | Média | Separar handlers `isButton()` e `isChatInputCommand()` |
| Vazamento de secrets/env | Alta | Logs redigidos; nunca imprimir env completo |

## Decisões abertas

1. **Modelos permitidos no MVP**
   - Recomendação: `codexplan`, `codexspark`.

2. **Escopo de preferência em thread**
   - Recomendação: thread própria com fallback para canal pai.

3. **Troca com sessão viva**
   - Recomendação MVP: vale na próxima sessão.
   - Recomendação final: `/model set --restart` explícito.

4. **Provider múltiplo no MVP**
   - Recomendação: começar só com provider ativo/default `codex_auth`.

5. **Resposta do slash command**
   - Recomendação: `current/list` ephemeral; `set/reset` também ephemeral para reduzir ruído.

## Handoff futuro para Bolt

Quando Eduardo aprovar implementação, chamar Bolt com escopo inicial:

1. Criar `models.json` + resolver + testes.
2. Adicionar operação `model.preference.write`.
3. Implementar `/model` textual interceptado antes do LLM.
4. Rodar `bun test`.
5. Só depois avançar para slash real e Session Supervisor.

Não alterar `access.json` para guardar modelo. Não imprimir segredos. Preservar policy v2 sem perfis.

## Histórico

- **2026-05-27:** plano salvo por Oracle após validação paralela com Scout, Apex e Compass. Status: planejado, implementação pendente de aprovação explícita de Eduardo.
