---
author: oracle
type: prd
date: 2026-05-14
status: draft
source: discord-openclaude-bridge/docs/PRD-discord-terminal-mode.md
---

# PRD — Discord Terminal Mode para OpenClaude Bridge

> Cópia EvoNexus do PRD salvo também no repo do bridge em `/home/evonexus/evo-projects/discord-openclaude-bridge/docs/PRD-discord-terminal-mode.md`.

## Objetivo

Transformar o `discord-openclaude-bridge` em uma interface Discord capaz de operar de forma o mais parecida possível com o terminal EvoNexus/OpenClaude, copiando os contratos de controle do terminal: sessão, permissões, MASTER, project routing, escrita em projetos autorizados, opção explícita para EvoNexus, delegação de agentes, progresso, cancelamento, histórico e approvals futuros.

## Tese arquitetural

O Discord não deve tentar virar um terminal visual. Ele deve ser um terminal remoto assíncrono governado por política declarativa:

```text
Discord user/message/thread
  → Discord Bridge
  → AccessPolicy(user/channel/project/tool)
  → SessionResolver(user/channel/thread/project/agent)
  → ProjectRegistry
  → RunnerPolicy
  → OpenClaude Runner
  → Progress/Event Adapter
  → Discord UX Adapter
```

## Contexto

O terminal EvoNexus tem dois caminhos:

1. **PTY interativo** via `dashboard/terminal-server/src/claude-bridge.js` + `AgentTerminal.tsx`, com `node-pty`, input/output bruto e sessões vivas.
2. **Chat estruturado via Agent SDK** via `dashboard/terminal-server/src/chat-bridge.js` + `AgentChat.tsx`, com `canUseTool`, `PreToolUse`, `permission_request`, `permission_response`, `agentProgressSummaries`, `resume` e eventos semânticos.

O Discord Bridge já tem execução async, SQLite, sessão por canal/tópico/projeto, project routing, `/status`, `/last`, `/cancel`, milestones e recovery de chunk/runner. O gap é uma camada explícita de política por usuário/canal/projeto/tool.

## Requisitos principais

### RF-01 — `config/access.yaml`

Criar política declarativa de acesso:

```yaml
version: 1

defaults:
  unknown_user: blocked
  require_project_for_write: false

users:
  "783488179000442891":
    name: Eduardo Martins
    role: master
    enabled: true

roles:
  master:
    description: "Acesso total equivalente ao terminal EvoNexus"
    permission_mode: bypassPermissions
    tools: default
    can_write: true
    can_use_bash: true
    can_use_agents: true
    can_use_skills: true
    can_use_evonexus_workspace: true
    allowed_projects: "*"
    default_workspace: evonexus

  readonly:
    description: "Consulta sem escrita"
    permission_mode: default
    tools: [Read, Grep, Glob]
    can_write: false
    can_use_bash: false
    can_use_agents: false
    can_use_evonexus_workspace: false
    allowed_projects: []

  blocked:
    description: "Sem acesso"
    enabled: false
```

### RF-02 — MASTER equivalente ao terminal

Para Eduardo MASTER:

- com projeto ativo: `cwd=/home/evonexus/evo-projects/<projeto>`;
- sem projeto ativo e `default_workspace=evonexus`: `cwd=/home/evonexus/evo-nexus`;
- comando deve usar `--tools default` e `--permission-mode bypassPermissions`;
- pode editar arquivos, usar Bash, skills e agentes.

### RF-03 — EvoNexus workspace explícito

Acesso ao EvoNexus só se:

```yaml
can_use_evonexus_workspace: true
default_workspace: evonexus
```

Se falso, sem projeto ativo deve bloquear ou exigir `/project select <slug>`.

### RF-04 — Project routing obrigatório

`cwd` e `add_dirs` vêm apenas de `config/projects.yaml` ou do workspace EvoNexus explicitamente habilitado. Nunca aceitar path arbitrário vindo de mensagem Discord.

### RF-05 — Bloqueio de paths sensíveis

Mesmo MASTER não deve ignorar bloqueios básicos: `/`, `/home`, `/home/evonexus`, `.ssh`, secrets e diretórios sensíveis.

### RF-06 — Status com política

`/status` deve mostrar usuário, perfil, escrita, workspace EvoNexus, projeto ativo, CWD, tools e permission mode.

### RF-07 — Auditoria

Toda execução deve persistir/logar role, policy, permission mode, tools, can_write, workspace, projeto, CWD e motivo da decisão.

### RF-08 — Approval queue futura

Prever `/approvals`, `/approve`, `/deny`, timeout e redaction para perfis não-MASTER.

## Fases

1. **AccessPolicy + MASTER** — `config/access.yaml`, loader, policy resolver, integração com execução normal e `/status`.
2. **Project routing + EvoNexus option** — `allowed_projects`, `can_use_evonexus_workspace`, bloqueios e auditoria.
3. **Auditoria e status** — JSONL/SQLite com snapshot da policy, `/last` mostrando policy usada.
4. **Approval queue** — approvals por tool para usuários não-MASTER.
5. **Runner SDK / terminal-server backend** — avaliar herdar `ChatBridge` ou manter CLI com policy.

## Critérios de aceite

- Usuário MASTER listado executa com permissão equivalente ao terminal.
- Usuário não listado é bloqueado.
- Usuário readonly não escreve.
- Projeto selecionado define `cwd`.
- EvoNexus só é usado se `can_use_evonexus_workspace=true`.
- MASTER usa `--tools default` e `--permission-mode bypassPermissions`.
- Sessões continuam por canal/tópico/projeto.
- `/cancel` continua matando processo.
- `/status` mostra policy.
- Toda execução registra role/policy/cwd/tools.
- Logs não vazam secrets.

## Decisões pendentes

1. Confirmar nome final: recomendado `config/access.yaml`.
2. Confirmar MASTER sem projeto ativo: recomendado `can_use_evonexus_workspace=true` + `default_workspace=evonexus`.
3. Confirmar usuários não listados bloqueados por padrão.
4. Confirmar approval queue só depois da fase MASTER.

## Fora de escopo inicial

- PTY real no Discord.
- UI visual igual terminal.
- Streaming token-by-token.
- Reimplementar todo `ChatBridge`.
- Workspace global sem restrição de path.

## Recomendação final

Implementar primeiro:

```text
AccessPolicy + MASTER + EvoNexus workspace option
```

Depois evoluir para approvals de usuários não-MASTER e, em fase posterior, avaliar integração com `terminal-server`/Agent SDK.
