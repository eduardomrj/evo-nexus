---
author: claude
agent: oracle
type: work-plan-item
date: 2026-05-19
phase: 5
item-id: DCB-v2-11
status: pending
---

# DCB-v2-11. Decomissionar v1 como arquitetura principal

**Fase:** Fase 5 — Cutover/rollback e decomissionamento v1
**Eixo:** manutencao-divida-tecnica
**Tipo:** [EVOLUIR]
**Prazo sugerido:** após estabilidade da v2

## O que é

Após estabilização da v2, remover a v1 do caminho principal e mantê-la apenas como referência histórica ou fallback temporário com prazo.

## O que fazer

- Definir período de observação pós-cutover.
- Congelar desenvolvimento na v1.
- Remover v1 de caminhos automáticos de produção.
- Marcar v1 como fallback temporário ou legacy.
- Migrar testes relevantes da v1 para a v2.
- Arquivar ou reduzir código morto.
- Atualizar runbook operacional.
- Registrar retro: o que quebrou na v1, por que gateway único virou regra e quais features ficaram para v2.x.

## Agente / Skill / Rotina

`@zen-simplifier`, `@lens-reviewer`, `@mirror-retro`, `@quill-writer`, `@flow-git`.

## O que o usuário precisa decidir/fornecer

- Prazo para desligar fallback v1.
- Se v1 será arquivada, mantida read-only ou removida.
- Quais features pós-v2 entram no backlog.

## Impacto esperado

Evita recaída para remendos no monólito e reduz superfície de manutenção.

## Dependências

v2 estável em produção, runbook atualizado e backlog de features pendentes priorizado.

## Riscos

- Remover fallback cedo demais.
- Manter fallback tempo demais e voltar a remendar v1.
- Perder teste útil da v1.

## Agente sugerido pra implementação

**Time:** @mirror-retro → @zen-simplifier → @lens-reviewer → @quill-writer → @flow-git

| Fase | Agente | Papel |
|---|---|---|
| 1. Retro | @mirror-retro | Lições e decisão de encerramento |
| 2. Simplificação | @zen-simplifier | Remover/arquivar legado |
| 3. Review | @lens-reviewer | Verificar risco de remoção |
| 4. Docs | @quill-writer | Runbook e notas |
| 5. Git/release | @flow-git | Commit/release se aprovado |

**Por quê esse time:** decomissionamento precisa preservar lições, reduzir dívida e evitar remoção perigosa.

## Status

- [x] Pendente
- [ ] Em progresso
- [ ] Concluído
