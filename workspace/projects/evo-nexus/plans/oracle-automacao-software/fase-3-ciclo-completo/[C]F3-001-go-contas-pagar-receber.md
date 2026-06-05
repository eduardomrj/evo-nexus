---
author: claude
agent: oracle
type: work-plan-item
date: 2026-04-17
phase: 3
item-id: F3-001
status: pending
---

# F3-001. GO Platform — Primeiro Módulo (Contas a Pagar/Receber)

**Fase:** 3 — Ciclo Completo
**Eixo:** Produto / Engineering
**Tipo:** [CONSTRUIR NOVO]
**Prazo sugerido:** Sem 11-14

## O que é

O primeiro módulo funcional da Plataforma GO, construído com a stack escolhida em F2-004. Contas a Pagar/Receber foi sugerido por ser autocontido, ter escopo claro, e validar a stack rapidamente sem as complexidades do PDV ou fiscal. MVP com timebox de 4 semanas.

## O que fazer

- PRD com @compass-planner: requisitos do módulo (CRUD de contas, categorias, dashboard, relatórios, integração Asaas)
- Arquitetura com @apex-architect: modelo de dados multi-tenant, API REST, autenticação, integração Asaas
- Build incremental com @bolt-executor: CRUD → dashboard → integração Asaas → relatórios
- TDD com @grid-tester: regras de negócio (juros, multa, parcelamento, baixa automática)
- Verify com @oath-verifier + @lens-reviewer contra o PRD
- UI/UX com @canvas-designer: interface web do módulo

## Agente / Skill / Rotina

`@compass-planner` + `@apex-architect` + `@bolt-executor` + `@grid-tester` + `@oath-verifier` + `@lens-reviewer` + `@canvas-designer` + `int-asaas`

## O que o usuário precisa decidir/fornecer

- Confirmar que Contas a Pagar/Receber é o primeiro módulo (ou prefere outro?)
- Multi-tenant desde o início ou single-tenant no v1?
- Integração com Asaas no v1 ou apenas CRUD manual primeiro?
- Regras de negócio específicas: juros de mora, multa, descontos? Parcelamento?

## Impacto esperado

Primeiro módulo funcional da Plataforma GO em produção. Valida a stack escolhida. Demonstra o modelo micro-SaaS para os primeiros clientes.

## Dependências

- **F2-004 (decisão de stack — OBRIGATÓRIA)** — não iniciar sem isso

## Riscos

- **ALTO** — scope creep é o maior inimigo. PRD fechado e timebox de 4 semanas. MVP only — features adicionais vão para v1.1
- Stack escolhida pode revelar limitações durante o build — mitigação: circuit breaker (3 tentativas → escala para @apex-architect)

## Agente sugerido pra implementação

| Fase | Agente | Papel |
|---|---|---|
| 1. PRD | @compass-planner | Requisitos + acceptance criteria |
| 2. Arquitetura | @apex-architect | ADR + modelo de dados + API design |
| 3. UI/UX | @canvas-designer | Interface web do módulo |
| 4. Build | @bolt-executor | Implementação incremental |
| 5. Testes | @grid-tester | TDD para regras de negócio |
| 6. Verify | @oath-verifier + @lens-reviewer | Validação contra PRD |

**Por quê:** item [CONSTRUIR NOVO] crítico — primeiro módulo define padrões para todos os outros.

## Status

- [x] Pendente
- [ ] Em progresso
- [ ] Concluído
