---
author: claude
agent: oracle
type: activation-plan-item
date: 2026-05-08
plan-name: discord-openclaude-bridge
phase: fase-4-integracao-cutover
item-id: F4-04
status: future
kind: DECIDIR
---

# F4-04 — Transformar a bridge Discord OpenClaude em plugin EvoNexus

## Veredito

Dá para transformar a bridge em plugin EvoNexus, mas em duas camadas:

1. **Plugin instalável hoje**, usando o contrato atual de plugins para empacotar artefatos, skills, commands, rules, rotinas, heartbeats, integrações/env vars e documentação.
2. **Serviço persistente completo**, que exige uma evolução do contrato de plugins para suportar `services`/`daemons` ou uma integração formal com systemd/supervisor.

A bridge Discord → OpenClaude é essencialmente um processo long-running conectado ao Discord Gateway. O sistema de plugins atual é forte para instalar extensões do workspace, mas ainda não oferece uma capacidade nativa observada para gerenciar daemons persistentes com start/stop/restart, logs e uninstall operacional.

## Evidências do EvoNexus

### Capacidades de plugin existentes no código

O enum `Capability` em `dashboard/backend/plugin_schema.py` inclui:

- `agents`
- `skills`
- `rules`
- `heartbeats`
- `sql_migrations`
- `widgets`
- `claude_hooks`
- `readonly_data`
- `goals`
- `tasks`
- `triggers`
- `ui_pages`
- `writable_data`
- `public_pages`
- `safe_uninstall`

Evidência: `dashboard/backend/plugin_schema.py:45-67`.

O `CHANGELOG.md` também descreve o Plugin System v1 com 15 capacidades, incluindo agents, skills, commands, rules, routines, heartbeats, widgets, data, hooks, goals, tasks, triggers, MCP servers e UI pages.

Evidência: `CHANGELOG.md:70-84`.

### Instalação de agents/skills/commands/rules

O installer copia artefatos para:

- `.claude/agents`
- `.claude/skills`
- `.claude/commands`
- `.claude/rules`

Evidência:

- Agents: `dashboard/backend/routes/plugins.py:923-930`
- Skills: `dashboard/backend/routes/plugins.py:932-939`
- Commands: `dashboard/backend/routes/plugins.py:941-948`
- Rules: `dashboard/backend/routes/plugins.py:950-962`

O sistema aplica namespace `plugin-{slug}-*` para evitar colisões.

Evidência: `dashboard/backend/plugin_file_ops.py:59-76`.

Para skills, o installer copia diretórios inteiros e reescreve `name:` dentro de `SKILL.md` para bater com o diretório prefixado.

Evidência: `dashboard/backend/plugin_file_ops.py:167-202`.

### Rotinas de plugin

O dashboard escaneia rotinas de plugins em:

```text
plugins/{slug}/routines.yaml
plugins/{slug}/routines/routines.yaml
```

E resolve scripts relativos ao YAML.

Evidência: `dashboard/backend/routes/_helpers.py:145-202`.

O install também executa etapa de `routines_union` e tenta recarregar o scheduler via SIGHUP.

Evidência: `dashboard/backend/routes/plugins.py:991-997`.

### Heartbeats de plugin

O loader de heartbeats mescla:

```text
config/heartbeats.yaml
plugins/*/heartbeats.yaml
```

Cada heartbeat vindo de plugin recebe `source_plugin`.

Evidência:

- `dashboard/backend/heartbeat_schema.py:90-143`
- `dashboard/backend/heartbeat_schema.py:146-208`

O installer também tenta sincronizar heartbeats na instalação.

Evidência: `dashboard/backend/routes/plugins.py:976-989`.

### Integrações/env vars

O schema suporta integrações de plugin com env vars e health checks.

Evidência:

- `dashboard/backend/plugin_schema.py:146-193`
- `dashboard/backend/plugin_schema.py:865-901`
- `dashboard/backend/plugin_integration_health.py:107-127`

Isso permite declarar variáveis da bridge, como:

```env
DISCORD_OPENCLAUDE_BRIDGE_TOKEN
DISCORD_OPENCLAUDE_BRIDGE_DATA_DIR
DISCORD_OPENCLAUDE_BRIDGE_CHANNEL_ID
DISCORD_OPENCLAUDE_BRIDGE_ALLOWED_USER_ID
DISCORD_OPENCLAUDE_BRIDGE_TIMEOUT_SECONDS
DISCORD_OPENCLAUDE_BRIDGE_STATUS_UPDATE_SECONDS
```

### Safe uninstall

O contrato documentado de `safe_uninstall` preserva dados e roda hook pré-uninstall sandboxed.

Evidência: `docs/plugin-contract.md:82-127`.

Atenção: isso preserva principalmente tabelas/entidades gerenciadas pelo plugin. A bridge usa dados externos em:

```text
/home/evonexus/evo-projects/discord-openclaude-bridge/
```

Esse diretório deve ser preservado por design e documentado no plugin.

## Limitação principal

Não foi observado suporte nativo de plugin para declarar e gerenciar um processo persistente/daemon.

A bridge precisa ficar conectada ao Discord Gateway. Rotina e heartbeat ajudam a monitorar, mas não substituem o processo long-running.

Portanto, o plugin MVP pode instalar e configurar a bridge, mas a operação persistente ainda dependeria de:

- start manual;
- tmux/screen;
- systemd configurado por `@custom-sysops`;
- ou uma futura capability `services`/`daemons` no EvoNexus.

## Estrutura recomendada do plugin MVP

```text
evonexus-plugin-discord-openclaude-bridge/
  plugin.yaml
  README.md

  skills/
    discord-openclaude-bridge/
      SKILL.md

  commands/
    discord-openclaude-bridge.md

  rules/
    discord-openclaude-bridge.md

  routines/
    routines.yaml
    bridge_health.py

  heartbeats.yaml

  bridge/
    discord_openclaude_bridge.py
    start-discord-openclaude-bridge.sh

  ui/
    pages/
      bridge-status.js        # opcional futuro
```

## `plugin.yaml` conceitual

```yaml
id: discord-openclaude-bridge
name: Discord OpenClaude Bridge
version: 0.1.0
description: Discord bot bridge for OpenClaude/EvoNexus with status reactions, cancellation and skill routing.
author: EvolutionAPI
min_evonexus_version: 0.33.0
tier: essential

capabilities:
  - skills
  - commands
  - rules
  - heartbeats
  - widgets

integrations:
  - slug: discord-openclaude-bridge
    label: Discord OpenClaude Bridge
    category: messaging
    env_vars:
      - name: DISCORD_OPENCLAUDE_BRIDGE_TOKEN
        description: Discord bot token for the bridge.
        required: true
        secret: true
      - name: DISCORD_OPENCLAUDE_BRIDGE_DATA_DIR
        description: Persistent data directory.
        required: true
        secret: false
        default: /home/evonexus/evo-projects/discord-openclaude-bridge
      - name: DISCORD_OPENCLAUDE_BRIDGE_CHANNEL_ID
        description: Discord channel/thread allowed to use the bridge.
        required: true
        secret: false
      - name: DISCORD_OPENCLAUDE_BRIDGE_ALLOWED_USER_ID
        description: Discord user allowed to use the bridge.
        required: true
        secret: false
      - name: DISCORD_OPENCLAUDE_BRIDGE_TIMEOUT_SECONDS
        description: OpenClaude execution timeout.
        required: false
        secret: false
        default: "120"
      - name: DISCORD_OPENCLAUDE_BRIDGE_STATUS_UPDATE_SECONDS
        description: Interval for still-working messages.
        required: false
        secret: false
        default: "45"
```

Antes de implementar, validar o formato exato aceito por `PluginManifest` para `integrations` e capabilities.

## O que cabe bem no plugin atual

- Skill de operação da bridge.
- Command interno para abrir documentação/controle da bridge.
- Rules com instruções de uso e segurança.
- Rotina de health check.
- Heartbeat de monitoramento.
- Integração/env vars com secret masking.
- UI futura de status.
- Documentação do catálogo de slash commands e skills.
- SQL migrations se futuramente houver dados no DB do dashboard.

## O que cabe parcialmente

- Script principal da bridge dentro de `plugins/{slug}/bridge/`.
- Script de start que busca token no Vaultwarden ou lê `.env`.

Isso é instalável como arquivo do plugin, mas não é automaticamente gerenciado como daemon.

## O que não cabe nativamente hoje

- Criar systemd service automaticamente como parte segura do contrato de plugin.
- Garantir restart automático do processo.
- Gerenciar start/stop/restart pelo dashboard de plugins.
- Vincular logs do processo long-running ao painel de plugins sem UI/API extra.
- Uninstall operacional que pare serviço antes de remover plugin, sem capability específica.

## Segurança

### Segredos

A bridge atual usa Vaultwarden para buscar `DISCORD_OPENCLAUDE_BRIDGE_TOKEN` sem gravar segredo em texto claro no `.env`.

O plugin system suporta env vars secretas em integrações, mas a fonte de verdade do token precisa ser decidida:

1. manter Vaultwarden como fonte de verdade;
2. usar `.env` gerenciado pela integração de plugin;
3. criar wizard/skill de configuração que escreve no local seguro aprovado.

Não duplicar token sem necessidade.

### Dados persistentes

Manter dados fora do repo, conforme convenção local:

```text
/home/evonexus/evo-projects/discord-openclaude-bridge/
```

O plugin uninstall não deve apagar esse diretório por padrão.

### Slash commands Discord

Registrar slash commands no Discord é efeito externo. O plugin não deve registrar comandos automaticamente no install sem confirmação.

A ativação deve ser explícita via skill/comando de setup.

## Capacidade futura recomendada: `services` ou `daemons`

Para transformar isso em plugin completo de produção, criar capability nova no EvoNexus:

```yaml
capabilities:
  - services

services:
  - id: discord-openclaude-bridge
    description: Discord Gateway bridge for OpenClaude/EvoNexus
    command: python3 ${PLUGIN_DIR}/bridge/discord_openclaude_bridge.py
    working_dir: ${WORKSPACE}
    env:
      DISCORD_OPENCLAUDE_BRIDGE_DATA_DIR: ${ENV:DISCORD_OPENCLAUDE_BRIDGE_DATA_DIR}
      DISCORD_OPENCLAUDE_BRIDGE_CHANNEL_ID: ${ENV:DISCORD_OPENCLAUDE_BRIDGE_CHANNEL_ID}
      DISCORD_OPENCLAUDE_BRIDGE_ALLOWED_USER_ID: ${ENV:DISCORD_OPENCLAUDE_BRIDGE_ALLOWED_USER_ID}
    secrets:
      DISCORD_OPENCLAUDE_BRIDGE_TOKEN: ${ENV:DISCORD_OPENCLAUDE_BRIDGE_TOKEN}
    restart: always
    health_check:
      command: python3 ${PLUGIN_DIR}/bridge/discord_openclaude_bridge.py --check-config
      timeout_seconds: 10
    logs:
      stdout: workspace/ADWs/logs/plugins/discord-openclaude-bridge/stdout.log
      stderr: workspace/ADWs/logs/plugins/discord-openclaude-bridge/stderr.log
```

### Host responsibilities para `services`

- Validar comandos permitidos.
- Impedir shell metacharacters.
- Criar unit/supervisor config segura.
- Start/stop/restart via dashboard.
- Parar serviço antes de uninstall.
- Preservar logs/dados conforme política.
- Mostrar status no plugin detail.
- Auditar ações do operador.

## Plano de implementação recomendado

### Fase 1 — Plugin MVP instalável

- Criar repo/estrutura de plugin.
- Mover/duplicar bridge para `bridge/discord_openclaude_bridge.py` dentro do plugin.
- Adicionar `plugin.yaml` validado.
- Adicionar skill de controle/configuração.
- Adicionar command de documentação/controle.
- Adicionar rule de segurança.
- Adicionar rotina/heartbeat de health check.
- Declarar integração/env vars.
- Documentar dados externos preservados.

### Fase 2 — Slash commands + skill catalog

Usar o F4-03 como referência:

- `/skill` com autocomplete lendo `.claude/skills/`;
- `/skills query:`;
- `/evo status`;
- atalhos curados;
- confirmação para ações sensíveis.

### Fase 3 — Operação persistente

Escolher uma das opções:

1. manter setup via `@custom-sysops` criando systemd fora do plugin;
2. criar capability `services` no core;
3. criar dashboard UI/API para start/stop/restart do serviço.

### Fase 4 — Marketplace/reuso

- Testar install/update/uninstall em workspace limpo.
- Rodar plugin security scan.
- Garantir rollback.
- Publicar em repositório próprio.

## Critérios de aceite do MVP plugin

- `plugin.yaml` passa validação do EvoNexus.
- Plugin instala via fluxo oficial.
- Skills/commands/rules aparecem com prefixo `plugin-discord-openclaude-bridge-*`.
- Integração lista env vars necessárias com segredo mascarado.
- Rotina/heartbeat de health aparece no EvoNexus.
- `--check-config` funciona usando variáveis configuradas.
- Uninstall remove artefatos do plugin sem apagar `/home/evonexus/evo-projects/discord-openclaude-bridge/`.
- Documentação explica claramente que o daemon ainda precisa de operação externa até existir capability `services`.

## Decisões pendentes

1. Nome oficial do plugin: `discord-openclaude-bridge` ou `evo-discord-bridge`.
2. Fonte de segredo: Vaultwarden vs `.env` plugin integration.
3. Se o MVP plugin deve trazer o script da bridge em `plugins/{slug}/bridge/` ou continuar apontando para `ADWs/routines/evo-projects/`.
4. Se vamos criar capability `services` agora ou deixar para depois.
5. Se slash commands entram no primeiro plugin ou como versão `0.2.0`.
