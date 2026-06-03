# Plano — Discord Plus Multi-provider Model Allowlist

Data: 2026-05-31

## Objetivo

Evoluir o `/model` do Discord Plus para suportar múltiplos providers e modelos via `model-allowlist.json`, permitindo OpenAI GPT-5.5 e modelos Anthropic sem quebrar o fallback atual Codex.

## Etapa 1 — Model registry JSON

**Tipo:** construir novo

Arquivos prováveis:

- `src/models/model-allowlist.ts`
- `tests/models/model-allowlist.test.ts`

Tarefas:

1. Definir tipos do JSON.
2. Criar fallback embutido:
   - `codex_auth/codexplan`
   - `codex_auth/codexspark`
3. Carregar arquivo de:
   - env opcional `DISCORD_PLUS_MODEL_ALLOWLIST_PATH`
   - default `/home/evonexus/evo-projects-data/evonexus-discord-plus/model-allowlist.json`
4. Validar schema, aliases e default.
5. Redigir erros e fazer fallback sem crash.

Testes:

- JSON válido.
- JSON ausente.
- JSON corrupto.
- alias apontando para modelo inexistente.
- strings inválidas rejeitadas.

## Etapa 2 — Atualizar `/model`

**Tipo:** evoluir existente

Arquivos prováveis:

- `src/models/model-slash-command.ts`
- `server.ts`
- testes existentes/novos de model command

Tarefas:

1. Adicionar option opcional `provider` em `/model set`.
2. Manter `model` obrigatório.
3. `/model list` usa allowlist JSON agrupada por provider.
4. `/model current` mostra provider/model efetivo.
5. `/model set` resolve:
   - provider informado → validar provider/model.
   - provider omitido → resolver por alias.
6. Rejeitar fora da allowlist.
7. Manter `model.preference.write`.

Testes:

- `/model set model:gpt5.5` salva `openai/gpt5.5`.
- `/model set provider:anthropic model:sonnet` salva `anthropic/sonnet`.
- `/model set model:foo` rejeita.
- `/model list` mostra providers.
- `/model current` continua funcionando.

## Etapa 3 — Runner CLI com provider/model

**Tipo:** evoluir existente

Arquivos prováveis:

- `src/sessions/cli-session-runner.ts`
- `src/sessions/openclaude-session-launcher.ts`
- `src/sessions/sdk-inbound-runtime.ts`
- testes de runner CLI

Tarefas:

1. Garantir que preferência efetiva inclui `{ provider, model }`.
2. Montar spawn com args:
   - `--provider <provider>`
   - `--model <model>`
3. Preservar:
   - `-p`
   - `--agent`
   - `--tools ""`
   - `--output-format json`
   - `--resume <session_id>` quando aplicável.
4. Não usar `--channels` nem plugin Discord.
5. Validar que Codex continua com `codex_auth/codexplan`.

Testes:

- spawn openai/gpt5.5 contém `--provider openai --model gpt5.5`.
- spawn anthropic/sonnet contém `--provider anthropic --model sonnet`.
- spawn codex_auth/codexplan continua válido.
- `--resume` preservado.

## Etapa 4 — Criar JSON inicial no deploy

**Tipo:** operação/deploy

Arquivo:

- `/home/evonexus/evo-projects-data/evonexus-discord-plus/model-allowlist.json`

Conteúdo inicial:

- `codex_auth`: `codexplan`, `codexspark`
- `openai`: `gpt5.5`
- `anthropic`: `sonnet`, `opus`, `haiku`

Tarefas:

1. Criar backup se arquivo existir.
2. Escrever JSON inicial se ausente.
3. Se existir, validar antes de sobrescrever; preferir preservar customizações.
4. Não incluir segredos.

## Etapa 5 — Verificação local

Comandos:

```bash
bun test tests/models/model-allowlist.test.ts
bun test tests/sessions/cli-session-runner.test.ts
bun test
```

Também validar manualmente, sem Discord:

```bash
openclaude -p --provider openai --model gpt5.5 --tools "" --output-format json "Responda apenas OK"
openclaude -p --provider anthropic --model sonnet --tools "" --output-format json "Responda apenas OK"
```

Observação: se Anthropic não estiver configurado no ambiente, registrar como bloqueio operacional, não bug de código.

## Etapa 6 — Deploy e smoke real

Pré-condição:

- Oath PASS.
- Usuário autorizado para `model.preference.write`.

Passos:

1. Reiniciar `evonexus-discord-plus.service`.
2. Confirmar comandos no Discord.
3. Executar no Discord:

```text
/model list
/model set provider:anthropic model:sonnet
/model current
```

4. Enviar mensagem curta no mesmo tópico.
5. Testar OpenAI:

```text
/model set provider:openai model:gpt5.5
/model current
```

6. Enviar mensagem curta.
7. Se falhar por credencial/provider, voltar para:

```text
/model set provider:codex_auth model:codexplan
/session reset
```

## Rollback

1. Remover/renomear `model-allowlist.json` para cair no fallback.
2. Definir `/model set provider:codex_auth model:codexplan` no escopo afetado.
3. Reiniciar serviço se necessário.
4. Se código falhar, reverter commit e reiniciar.

## Critério de pronto

- Testes passam.
- Oath PASS.
- `/model list` mostra Codex, OpenAI e Anthropic.
- `/model set model:gpt5.5` resolve para `openai/gpt5.5`.
- `/model set provider:anthropic model:sonnet` salva corretamente.
- Mensagem normal usa provider/model selecionado no spawn CLI.
