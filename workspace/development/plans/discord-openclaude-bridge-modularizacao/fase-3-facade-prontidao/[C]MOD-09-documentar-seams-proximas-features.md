---
author: claude
agent: oracle
type: work-plan-item
date: 2026-05-13
phase: 3
item-id: MOD-09
status: pending
---

# MOD-09. Documentar seams para próximas features sem implementar

**Fase:** Facade Fina e Prontidão para Próximas Features
**Eixo:** prontidao-produto-extensibilidade-controlada
**Tipo:** [ATIVAR]
**Prazo sugerido:** fechamento da modularização

## O que é

Preparar pontos de extensão e backlog para `/skills`, `add_dirs management` e `/project new` sem alterar runtime behavior, slash tree, schema do banco ou schema do `projects.yaml`.

## O que fazer

- Documentar onde `/skills` entra na camada de command handlers.
- Documentar como `add_dirs management` deve usar routing/store sem quebrar propagação atual.
- Documentar contrato futuro de `/project new` com wizard confirmado e side effects explícitos.
- Criar TODOs/backlog técnicos rastreáveis, sem mudar slash tree, DB schema ou YAML schema.
- Atualizar `docs/OPERATIONS.md` com nova estrutura e limites operacionais.

## Agente / Skill / Rotina

@nova-product + @apex-architect + @quill-writer + @compass-planner.

## O que o usuário precisa decidir/fornecer

Prioridade pós-modularização: `/skills`, `add_dirs management` ou `/project new`.

## Impacto esperado

Conecta o refactor às próximas entregas sem scope creep. Ajuda futuras features a entrarem em pontos claros, sem reabrir o monólito.

## Dependências

MOD-08.

## Riscos

Extension seam virar implementação disfarçada. Este item não pode mudar comportamento público.

## Critérios de aceite

- Nenhuma feature futura foi implementada nesta onda.
- Slash tree pública, DB schema e `projects.yaml` não mudam por causa de MOD-09.
- Próximas features têm ponto de extensão claro.

## Agente sugerido pra implementação

**Time:** @nova → @apex → @quill → @compass

| Fase | Agente | Papel |
|---|---|---|
| 1. Produto | @nova-product | Priorizar valor pós-modularização |
| 2. Arquitetura | @apex | Definir seams sem feature creep |
| 3. Docs | @quill-writer | Atualizar docs com clareza |
| 4. Plano futuro | @compass | Preparar próximos planos quando aprovados |

**Por quê esse time:** fecha o refactor conectando arquitetura a roadmap sem implementar features fora do escopo.

## Status

- [x] Pendente
- [ ] Em progresso
- [ ] Concluído
