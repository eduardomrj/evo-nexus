---
author: claude
agent: oracle
type: work-plan-item
date: 2026-05-13
phase: 0
item-id: MOD-01
status: completed
---

# MOD-01. Definir boundaries, pacote, imports e estratégia de trabalho

**Fase:** Contratos e Segurança de Baseline
**Eixo:** governanca-tecnica-arquitetura-incremental
**Tipo:** [DECIDIR]
**Prazo sugerido:** antes de mover código

## O que é

Decidir a estrutura alvo da modularização antes de extrair helpers ou classes. Este item controla blast radius, evita imports circulares e define como o trabalho será entregue.

## O que fazer

- Definir árvore de módulos alvo: `constants/config/models`, `routing`, `store/repositories`, `runner`, `progress`, `discord_adapter`, `commands`.
- Criar mapa `old symbol -> new module`.
- Definir política de imports e como evitar circular imports.
- Definir shims/reexports temporários e critério de remoção.
- Decidir política para o worktree existente `agent-a6bf225d`: manter, ignorar ou pedir limpeza manual posterior.
- Decidir granularidade: commits/PRs por extração lógica ou lote único com checkpoints internos.

## Agente / Skill / Rotina

@apex-architect + @compass-planner + @flow-git.

## O que o usuário precisa decidir/fornecer

Estratégia de branch/worktree e granularidade de entrega. Também decidir o que fazer com o worktree existente observado.

## Impacto esperado

Evita refactor improvisado e reduz retrabalho. Garante que a primeira extração já siga uma arquitetura aprovada.

## Dependências

MOD-00.

## Riscos

Shims temporários podem virar API permanente se não tiverem prazo/gate de remoção.

## Critérios de aceite

- Boundaries aprovados antes de mover código.
- Política de imports documentada.
- Shims têm prazo/gate de remoção.
- Worktree existente não é limpo sem aprovação.

## Agente sugerido pra implementação

**Time:** @oracle → @apex → @compass → @flow

| Fase | Agente | Papel |
|---|---|---|
| 1. Decisão | @oracle | Conduzir as escolhas com Eduardo |
| 2. Arquitetura | @apex | Definir boundaries e riscos |
| 3. Plano | @compass | Converter decisões em execução incremental |
| 4. Git | @flow | Aplicar estratégia de branch/commit quando autorizado |

**Por quê esse time:** é item [DECIDIR]; precisa de framing humano e desenho técnico antes de execução.

## Status

- [ ] Pendente
- [ ] Em progresso
- [x] Concluído

## Decisões registradas em 2026-05-20

- Linha ativa: v1 (`src/discord_openclaude_bridge.py` + pacote `src/discord_openclaude_bridge/`).
- v2 permanece congelada e fora do gate padrão.
- Gate padrão durante a modularização v1: `python3 -m pytest -q tests/test_discord_openclaude_bridge.py`.
- A suíte completa ainda falha por `tests/v2/*` importarem `discord_openclaude_bridge.v2`; isso não é gate da v1 enquanto a v2 estiver congelada.
- Granularidade: commit por extração lógica.
- Execução: usar worktree isolada para agentes write-capable e aplicar na branch principal só após revisão/verificação.
- Sem restart de serviço ou smoke Discord manual sem aprovação explícita.
- Contrato mínimo do pacote `import discord_openclaude_bridge`: `BridgeConfig`, `ProjectRegistry`, `AccessRegistry`, `ExecutionStore`, `JsonlLogger`.
- `BridgeHandler` e `OpenClaudeRunner` ficam fora do contrato mínimo do pacote para evitar import pesado/circularidade.
- Finding HIGH da revisão Lens sobre import normal do pacote resolvido em `530fbd1 fix(discord): expose v1 legacy package contract`.

## Evidência de conclusão

- Commit de correção de contrato: `530fbd1 fix(discord): expose v1 legacy package contract`.
- Import normal validado: `PYTHONPATH=src python3 -c "import discord_openclaude_bridge as b; ..."`.
- Runtime direto validado: `python3 src/discord_openclaude_bridge.py --help`.
- Gate v1 validado após a correção: `203 passed, 1 warning`.
