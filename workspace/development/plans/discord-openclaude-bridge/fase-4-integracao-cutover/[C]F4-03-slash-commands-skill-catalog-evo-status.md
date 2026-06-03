---
author: claude
agent: oracle
type: activation-plan-item
date: 2026-05-08
plan-name: discord-openclaude-bridge
phase: fase-4-integracao-cutover
item-id: F4-03
status: future
kind: EVOLUIR
---

# F4-03 — Slash commands Discord + catálogo dinâmico de skills EvoNexus

## Objetivo

Transformar a bridge Discord → OpenClaude/EvoNexus de um chat livre em uma interface operacional do EvoNexus dentro do Discord.

A ideia é que o usuário não precise lembrar nomes exatos de skills, comandos internos ou prompts longos. O bot deve expor comandos registrados no Discord, autocomplete para skills disponíveis e comandos extras para consultar status do ambiente EvoNexus.

## Decisão de arquitetura

Não registrar uma slash command para cada skill individual.

O EvoNexus tem muitas skills em `.claude/skills/`, e registrar uma command por skill criaria três problemas:

1. poluição da interface do Discord;
2. risco de bater limites práticos do Discord para comandos/opções;
3. manutenção difícil quando skills forem adicionadas, removidas ou renomeadas.

A arquitetura recomendada é:

- registrar poucos comandos fixos e estáveis no Discord;
- criar um catálogo dinâmico de skills lendo o workspace;
- usar autocomplete no comando `/skill` para sugerir skills disponíveis;
- adicionar atalhos curados apenas para fluxos muito usados.

## Comandos Discord propostos

### Operação da bridge

| Comando | Função |
|---|---|
| `/ping` | Confirma que o bot está vivo e autorizado |
| `/help` | Mostra como usar a bridge, comandos disponíveis e limites |
| `/status` | Mostra a última execução do canal/tópico |
| `/cancel` | Cancela a execução ativa do canal/tópico |
| `/ask prompt:` | Envia uma pergunta livre para o OpenClaude |

### Status do EvoNexus

Preferência: usar um grupo de comandos do Discord chamado `/evo`.

| Comando | Função |
|---|---|
| `/evo status` | Resumo geral do ambiente EvoNexus |
| `/evo health` | Checks rápidos: bridge, token, OpenClaude CLI, data dir, SQLite |
| `/evo services` | Status de serviços relevantes: dashboard, scheduler, terminal-server, bridge |
| `/evo routines` | Lista rotinas configuradas e/ou últimas execuções quando disponível |
| `/evo heartbeats` | Lista heartbeats e status quando disponível |
| `/evo logs` | Mostra últimos eventos relevantes da bridge sem expor segredos |
| `/evo version` | Mostra versões detectadas: OpenClaude, Python, EvoNexus quando disponível |

### Skills

| Comando | Função |
|---|---|
| `/skills query:` | Busca skills por nome, prefixo, domínio ou descrição |
| `/skill name: args:` | Executa uma skill escolhida via autocomplete |

Exemplo esperado:

```text
/skill name:fin-daily-pulse args:rode o pulso financeiro de hoje
```

O bot deve transformar isso em um prompt controlado para o OpenClaude, por exemplo:

```text
Use a skill `fin-daily-pulse` com os argumentos abaixo, respeitando as confirmações necessárias para ações com efeito externo:

rode o pulso financeiro de hoje
```

## Catálogo dinâmico de skills

### Fonte

Ler skills instaladas em:

```text
.claude/skills/*/SKILL.md
```

### Dados mínimos por skill

Para cada skill, o catálogo deve extrair:

- `slug`: nome da pasta da skill;
- `path`: caminho do `SKILL.md`;
- `prefix`: trecho antes do primeiro `-`, quando existir (`fin`, `prod`, `social`, `int`, `create`, etc.);
- `title`: título detectado no markdown, quando existir;
- `description`: primeira descrição útil do arquivo;
- `risk_level`: classificação local para execução direta vs. confirmação;
- `category`: categoria inferida pelo prefixo ou metadados.

### Cache

O catálogo deve usar cache em memória com TTL curto, por exemplo 60–300 segundos.

Motivos:

- evitar ler centenas de arquivos a cada autocomplete;
- permitir que novas skills apareçam sem reiniciar o bot;
- manter o autocomplete rápido.

### Autocomplete Discord

O Discord limita a quantidade de sugestões retornadas por autocomplete. O bot deve:

- filtrar por substring no `slug`, `title`, `description` e `prefix`;
- priorizar match exato de prefixo e início do slug;
- retornar no máximo o limite aceito pelo Discord;
- mostrar labels curtos, por exemplo:

```text
fin-daily-pulse — pulso financeiro diário
create-ticket — criar ticket persistente
social-post-writer — escrever post social
```

## Atalhos curados para skills

Depois do `/skill` genérico estar validado, adicionar atalhos para os fluxos mais usados.

Sugestões iniciais:

| Atalho Discord | Skill/fluxo |
|---|---|
| `/morning` | `prod-good-morning` |
| `/financeiro` | `fin-daily-pulse` |
| `/weekly-finance` | `fin-weekly-report` |
| `/ticket` | `create-ticket` |
| `/goal` | `create-goal` |
| `/heartbeat` | `create-heartbeat` |
| `/meeting` | `int-fathom` |
| `/todoist` | `int-todoist` |
| `/social-post` | `social-post-writer` |
| `/social-calendar` | `social-content-calendar` |

Critério: atalhos só entram quando forem usados com frequência suficiente para justificar comando próprio.

## Segurança e confirmação

Nem toda skill deve rodar diretamente a partir do Discord.

### Pode executar direto, em geral

- relatórios;
- resumos;
- análises;
- consultas de status;
- geração de conteúdo;
- criação de rascunhos.

### Deve exigir confirmação explícita

- enviar email;
- enviar mensagem para terceiro;
- editar arquivos;
- criar rotina;
- ativar/desativar heartbeat;
- criar ticket/goal quando isso tiver efeito persistente relevante;
- ações financeiras;
- ações legais/compliance;
- qualquer integração com efeito externo.

### Comportamento esperado para ações sensíveis

O bot deve responder com uma prévia:

```text
Vou executar a skill `X` com estes argumentos:

...

Isso pode causar efeito externo/persistente. Confirma?
```

E só continuar após confirmação explícita.

## Allowlist e escopo

O recurso deve continuar respeitando a allowlist da bridge:

- canal/tópico permitido;
- usuário permitido;
- futuramente guild permitida;
- futuramente roles permitidas.

Nenhum comando registrado deve permitir bypass da allowlist.

## Status do ambiente EvoNexus

Criar um componente futuro `EvoStatusProvider` ou equivalente.

### Checks iniciais

- bridge process ativo;
- `DISCORD_OPENCLAUDE_BRIDGE_TOKEN` configurado, sem imprimir valor;
- `DISCORD_OPENCLAUDE_BRIDGE_DATA_DIR` existe;
- SQLite acessível;
- últimos registros de execução;
- últimos erros JSONL;
- `openclaude --version`;
- `python3 --version`;
- configuração de timeout/status update;
- canal/user allowlist ativos.

### Checks futuros

Quando seguro e disponível, consultar também:

- dashboard EvoNexus via SDK/API local;
- scheduler;
- heartbeats;
- tickets;
- rotinas;
- terminal-server;
- status de systemd quando a bridge virar serviço persistente.

## Integração técnica com discord.py

Usar `discord.py` com `app_commands`.

### Estratégia de registro

Primeiro registrar como guild commands no servidor/canal de teste, porque:

- sincroniza rápido;
- reduz risco em produção;
- facilita iterar sem impacto global.

Depois de estabilizar, avaliar global commands.

### Comandos básicos de MVP

Primeiro MVP recomendado:

```text
/ping
/help
/status
/cancel
/ask prompt:
/skills query:
/skill name: args:
/evo status
```

Depois expandir para:

```text
/evo health
/evo services
/evo routines
/evo heartbeats
/evo logs
/evo version
```

## Relação com streaming real do OpenClaude

Este recurso é complementar ao streaming real.

Slash commands e catálogo de skills resolvem UX e descoberta.
Streaming real resolve observabilidade durante execução.

Ambos devem coexistir:

- slash commands: como o usuário inicia ações;
- streaming real: como o bot mostra progresso e eventos internos.

## Plano de implementação sugerido

### Etapa 1 — SkillCatalog read-only

- Criar classe/função para listar `.claude/skills/*/SKILL.md`.
- Extrair slug, prefixo, título e descrição.
- Implementar busca por query.
- Criar testes unitários.

### Etapa 2 — Slash commands básicos

- Registrar `/ping`, `/help`, `/status`, `/cancel`.
- Manter compatibilidade com comandos por texto já existentes.
- Registrar commands como guild commands no servidor de teste.
- Testar no tópico/canal permitido.

### Etapa 3 — `/skills` e `/skill`

- Implementar `/skills query:`.
- Implementar `/skill name: args:`.
- Implementar autocomplete dinâmico.
- Garantir split de resposta em chunks de 1900 caracteres.

### Etapa 4 — Segurança por risco

- Classificar skills por risco usando prefixo/lista local.
- Bloquear/confirmar ações sensíveis.
- Registrar decisão nos logs.

### Etapa 5 — `/evo status`

- Criar provider de status do ambiente.
- Responder em linguagem operacional simples.
- Não expor segredos.

### Etapa 6 — Atalhos curados

- Adicionar atalhos só para fluxos validados e frequentes.
- Documentar cada atalho.

## Critérios de aceite

- Slash commands aparecem no Discord do servidor de teste.
- `/skill name:` mostra autocomplete com skills reais do EvoNexus.
- `/skills query:financeiro` retorna skills financeiras relevantes.
- `/skill` executa pelo OpenClaude respeitando allowlist.
- Skills sensíveis exigem confirmação antes de efeito externo.
- `/evo status` retorna status útil sem expor segredo.
- Testes automatizados cobrem catálogo, busca, autocomplete e montagem de prompt.
- Plano preserva compatibilidade com mensagens livres e comandos textuais existentes.

## Riscos

- Registrar commands globalmente cedo demais pode demorar para atualizar e dificultar rollback.
- Autocomplete lendo arquivos em toda interação pode ficar lento sem cache.
- Executar skills sensíveis pelo Discord sem confirmação pode causar efeitos indesejados.
- Expor logs/status sem filtro pode vazar caminhos ou contexto sensível.
- Criar atalhos demais pode poluir a UX que o recurso tenta melhorar.

## Decisão pendente

Antes de implementar, decidir:

1. guild ID de teste para registrar os commands;
2. lista inicial de atalhos curados;
3. política de confirmação para skills sensíveis;
4. se `/skill` deve aceitar qualquer skill instalada ou apenas allowlist inicial;
5. se `/evo status` deve consultar só estado local da bridge no MVP ou também dashboard/scheduler.
