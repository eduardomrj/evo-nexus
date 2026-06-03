---
author: claude
agent: oracle
type: work-plan-item
date: 2026-04-17
phase: 3
item-id: F3-002
status: pending
---

# F3-002. GO Platform — PDV Web

**Fase:** 3 — Ciclo Completo
**Eixo:** Produto / Engineering
**Tipo:** [CONSTRUIR NOVO]
**Prazo sugerido:** Sem 15-20

## O que é

O PDV (Ponto de Venda) web — módulo core da Plataforma GO para varejo. Depende da validação da stack pelo primeiro módulo (F3-001). MVP focado em fluxo de venda básico sem complexidades de periféricos ou fiscal no v1.

## O que fazer

- Discovery com @echo-analyst: requisitos do PDV web — offline-first?, periféricos (impressora, leitor de código)?, TEF?, NFCe no v1?
- PRD com @compass-planner: escopo MVP do PDV web (tela de venda, carrinho, fechamento, formas de pagamento)
- Arquitetura com @apex-architect: decisões de offline capability, sincronização, integração com periféricos
- Build com @bolt-executor: tela de venda → fechamento → integração Asaas (pagamento)
- UI/UX com @canvas-designer: interface de PDV (touchscreen-friendly, rápida, sem distrações)
- Verify com @oath-verifier

## Agente / Skill / Rotina

`@echo-analyst` + `@compass-planner` + `@apex-architect` + `@bolt-executor` + `@canvas-designer` + `@oath-verifier` + `@grid-tester`

## O que o usuário precisa decidir/fornecer

- PDV precisa funcionar offline no v1? (complexidade alta — recomendado: não)
- Integração TEF (cartão de crédito/débito) no MVP ou no v1.1?
- NFCe no MVP ou no v1.1?
- Design: manter visual familiar do Emporion PDV ou novo design?
- Quais formas de pagamento no v1: Pix, boleto, cartão, dinheiro?

## Impacto esperado

PDV web funcional substituindo o Emporion PDV para novos clientes. Primeira demonstração da Plataforma GO com módulos integrados (Contas + PDV).

## Dependências

- F3-001 (stack validada com o primeiro módulo)

## Riscos

- **ALTO** — PDV é o módulo mais complexo do ecossistema. MVP extremamente enxuto. Sem offline no v1. TEF e NFCe no v1.1.
- Concorrência com Emporion Desktop pode confundir clientes existentes — mitigação: posicionar como "nova geração" para novos clientes apenas

## Agente sugerido pra implementação

| Fase | Agente | Papel |
|---|---|---|
| 1. Discovery | @echo-analyst | Requisitos reais do PDV web |
| 2. PRD | @compass-planner | Escopo MVP fechado |
| 3. UI/UX | @canvas-designer | Interface touchscreen-friendly |
| 4. Arquitetura | @apex-architect | ADR de offline/sync/periféricos |
| 5. Build | @bolt-executor | Implementação |
| 6. Verify | @oath-verifier | Validação end-to-end |

**Por quê:** item [CONSTRUIR NOVO] de alta complexidade — processo completo de 6 fases obrigatório.

## Status

- [x] Pendente
- [ ] Em progresso
- [ ] Concluído
