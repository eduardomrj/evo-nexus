# PRD — Discord Plus Multi-provider Model Allowlist

Data: 2026-05-31

## Problema

O Discord Plus hoje trata seleção de modelo como uma lista curta e fixa de aliases Codex (`codexplan`, `codexspark`) e executa sessões com provider `codex_auth`. Isso impede usar modelos que funcionam no terminal OpenClaude com outro provider, como `gpt5.5` via `openai`, e também impede expor modelos Anthropic (`sonnet`, `opus`, `haiku`) no Discord.

A investigação confirmou:

- `openclaude -p --model gpt5.5 ...` falha no provider padrão/Codex com: `The 'gpt5.5' model is not supported when using Codex with a ChatGPT account.`
- `openclaude -p --provider openai --model gpt5.5 ...` funciona e retorna `modelUsage: gpt-5.5`.

Logo, não basta aumentar uma allowlist de modelos; o Discord Plus precisa rotear **provider + model**.

## Objetivos

1. Criar uma allowlist JSON como fonte de verdade dos providers/modelos permitidos.
2. Permitir seleção explícita no Discord:
   - `/model set provider:openai model:gpt5.5`
   - `/model set provider:anthropic model:sonnet`
   - `/model set provider:codex_auth model:codexplan`
3. Permitir aliases quando provider for omitido:
   - `/model set model:gpt5.5` → `openai/gpt5.5`
   - `/model set model:sonnet` → `anthropic/sonnet`
   - `/model set model:codexplan` → `codex_auth/codexplan`
4. Fazer o runner CLI chamar OpenClaude com provider/model efetivos:
   - `openclaude -p --provider <provider> --model <model> ...`
5. Preservar fallback seguro para `codex_auth/codexplan` se o JSON estiver ausente/corrupto.
6. Manter validação rígida: nada fora do JSON pode ser usado.

## Não objetivos

- Não gerenciar tokens ou credenciais de providers.
- Não descobrir automaticamente todos os modelos remotos em tempo real.
- Não alterar o core OpenClaude.
- Não expor env, tokens ou headers no Discord/logs.
- Não mudar o Project Context nem o controle de sessão.

## Usuários

- Eduardo usando Discord Plus em `#nexus-bridge` e threads.
- Futuros operadores autorizados que precisem alternar modelos por canal/tópico.

## Fonte de verdade JSON

Local recomendado:

```text
/home/evonexus/evo-projects-data/evonexus-discord-plus/model-allowlist.json
```

Formato inicial:

```json
{
  "version": 1,
  "default": {
    "provider": "codex_auth",
    "model": "codexplan"
  },
  "providers": {
    "codex_auth": {
      "label": "OpenAI Codex OAuth",
      "models": {
        "codexplan": {
          "label": "GPT-5.4 Codex Plan",
          "description": "Raciocínio alto para tarefas complexas"
        },
        "codexspark": {
          "label": "GPT-5.3 Codex Spark",
          "description": "Mais rápido para iteração"
        }
      }
    },
    "openai": {
      "label": "OpenAI API",
      "models": {
        "gpt5.5": {
          "label": "GPT-5.5",
          "description": "Modelo OpenAI via provider openai"
        }
      }
    },
    "anthropic": {
      "label": "Anthropic",
      "models": {
        "sonnet": {
          "label": "Claude Sonnet",
          "description": "Equilíbrio entre qualidade e velocidade"
        },
        "opus": {
          "label": "Claude Opus",
          "description": "Raciocínio mais forte"
        },
        "haiku": {
          "label": "Claude Haiku",
          "description": "Mais rápido e barato"
        }
      }
    }
  },
  "aliases": {
    "codexplan": { "provider": "codex_auth", "model": "codexplan" },
    "codexspark": { "provider": "codex_auth", "model": "codexspark" },
    "gpt5.5": { "provider": "openai", "model": "gpt5.5" },
    "sonnet": { "provider": "anthropic", "model": "sonnet" },
    "opus": { "provider": "anthropic", "model": "opus" },
    "haiku": { "provider": "anthropic", "model": "haiku" }
  }
}
```

## Requisitos funcionais

### RF1 — Loader/validator

- Carregar JSON do data dir.
- Validar schema mínimo:
  - `version` inteiro;
  - `default.provider` e `default.model` existem na allowlist;
  - providers/models/aliases com strings seguras;
  - alias aponta para provider/model existente.
- Se ausente/corrupto, usar fallback embutido `codex_auth/codexplan` + `codexspark`.
- Logar erro redigido sem crash.

### RF2 — `/model list`

- Mostrar providers agrupados.
- Mostrar label e description por modelo.
- Não mostrar tokens/env.
- Indicar default.

### RF3 — `/model current`

- Mostrar provider/model efetivo do canal/thread.
- Mostrar se vem de preferência do scope ou default.

### RF4 — `/model set`

- Aceitar `model` obrigatório.
- Aceitar `provider` opcional.
- Se provider vier:
  - validar exatamente provider/model no JSON.
- Se provider não vier:
  - resolver por `aliases[model]`.
  - se alias inexistente ou ambíguo, rejeitar com mensagem clara.
- Exigir `model.preference.write` como hoje.
- Salvar `{ provider, model }` no store de preferência.

### RF5 — Runner CLI

- Usar provider/model efetivos no spawn:
  - `--provider <provider>`
  - `--model <model>`
- Continuar usando `--resume <session_id>` para continuidade.
- Não passar modelo cru GPT para `codex_auth` se JSON não permitir.
- Preservar `codex_auth/codexplan` como default.

### RF6 — Compatibilidade

- Preferências antigas com `provider: codex_auth` e `model: codexplan/codexspark` continuam válidas.
- Se houver preferência antiga sem provider, migrar/normalizar para `codex_auth` somente se modelo for alias conhecido.

## Segurança

- JSON não contém segredos.
- Regex segura para provider/model/alias: exemplo `^[a-zA-Z0-9._-]{1,80}$`.
- Labels/descriptions devem ter tamanho máximo e escapar Markdown/Discord quando exibidos.
- Não aceitar provider/model fora da allowlist.
- Não imprimir env ou tokens em logs.
- Fallback seguro se JSON inválido.

## UX esperada

```text
/model list
```

Retorna algo como:

```text
Default: codex_auth/codexplan

OpenAI Codex OAuth
- codexplan — GPT-5.4 Codex Plan: Raciocínio alto
- codexspark — GPT-5.3 Codex Spark: Mais rápido

OpenAI API
- gpt5.5 — GPT-5.5

Anthropic
- sonnet — Claude Sonnet
- opus — Claude Opus
- haiku — Claude Haiku
```

```text
/model set model:gpt5.5
```

Retorna:

```text
Model preference set to openai/gpt5.5 for this scope. Use /session reset to start a fresh session with the new model.
```

```text
/model set provider:anthropic model:opus
```

Retorna:

```text
Model preference set to anthropic/opus for this scope.
```

## Critérios de aceite

### Given/When/Then

1. **Listagem**
   - Given allowlist JSON válido
   - When usuário executa `/model list`
   - Then Discord mostra providers/modelos agrupados e o default.

2. **Alias OpenAI**
   - Given alias `gpt5.5` aponta para `openai/gpt5.5`
   - When usuário executa `/model set model:gpt5.5`
   - Then preferência salva provider `openai`, model `gpt5.5`.

3. **Anthropic explícito**
   - Given `anthropic/sonnet` está na allowlist
   - When usuário executa `/model set provider:anthropic model:sonnet`
   - Then preferência salva corretamente.

4. **Bloqueio fora da allowlist**
   - Given model `foo` não existe
   - When usuário executa `/model set model:foo`
   - Then comando rejeita sem alterar preferência.

5. **Runner CLI**
   - Given preferência `openai/gpt5.5`
   - When mensagem normal cria sessão
   - Then spawn inclui `--provider openai --model gpt5.5`.

6. **Fallback JSON inválido**
   - Given arquivo JSON ausente/corrupto
   - When serviço inicia
   - Then usa `codex_auth/codexplan` e não quebra.

## Riscos

- Provider/model válido no JSON, mas credencial do provider ausente no ambiente: o comando `/model set` passa, mas execução da mensagem pode falhar. Mitigar com smoke e erro operacional claro.
- Discord slash choices têm limite de opções. Evitar choices estáticos se a lista crescer; usar string option livre validada no runtime.
- Mudança no spawn pode afetar Codex. Cobrir com testes para `codex_auth/codexplan`.
