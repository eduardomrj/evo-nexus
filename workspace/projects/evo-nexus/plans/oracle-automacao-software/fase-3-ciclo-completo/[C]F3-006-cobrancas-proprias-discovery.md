---
author: claude
agent: oracle
type: work-plan-item
date: 2026-04-17
phase: 3
item-id: F3-006
status: pending
---

# F3-006. Sistema Próprio de Cobranças — Discovery

**Fase:** 3 — Ciclo Completo
**Eixo:** Financeiro / Produto
**Tipo:** [DECIDIR]
**Prazo sugerido:** Sem 20-24

## O que é

Avaliar a viabilidade de substituir o Asaas por uma solução própria de cobranças dentro da Plataforma GO. Eduardo quer eventualmente ter controle total sobre a camada de pagamentos — mas construir um gateway de pagamentos com 2 pessoas é extremamente ambicioso. Este item produz um ADR honesto antes de qualquer investimento.

## O que fazer

- Research com @scroll-docs: regulação BACEN para intermediação de pagamentos, PIX API direta (BACEN Open Finance), registro de boletos (CIP), conformidade PCI-DSS
- Discovery com @echo-analyst: requisitos funcionais (Pix, boleto, cartão, split marketplace, assinatura recorrente)
- ADR de viabilidade com @apex-architect + @raven-critic: build vs buy, estimativa de esforço, certificações necessárias, custo real vs Asaas
- Recomendação final: continuar Asaas, migrar para outro gateway (ex: Pagar.me, Stripe), ou construir próprio

## Agente / Skill / Rotina

`@echo-analyst` + `@scroll-docs` + `@apex-architect` + `@raven-critic`

## O que o usuário precisa decidir/fornecer

- Objetivo principal: reduzir custo de transação? ou oferecer cobrança como feature dentro da Plataforma GO para os clientes?
- Aceita a complexidade regulatória do BACEN e PCI-DSS? (certificação cara e demorada)
- Este é realmente o momento certo, dado o tamanho do time?

## Impacto esperado

Decisão informada antes de qualquer investimento. Evita gastar meses em um projeto que pode não ser viável para um time de 2. Se a resposta for "construir", o ADR define o roadmap. Se for "continuar no Asaas", o trabalho termina aqui.

## Dependências

- Nenhuma técnica — mas faz mais sentido após a Plataforma GO ter módulos rodando (para avaliar o volume real de transações)

## Riscos

- **ALTO** — construir gateway de pagamentos com 2 pessoas é muito ambicioso. O ADR precisa ser honesto sobre viabilidade.
- Regulação BACEN é complexa e mutável — discovery profundo obrigatório antes de qualquer código

## Agente sugerido pra implementação

| Fase | Agente | Papel |
|---|---|---|
| 1. Research | @scroll-docs | Regulação BACEN + alternativas de mercado |
| 2. Discovery | @echo-analyst | Requisitos + volume estimado |
| 3. ADR | @apex-architect | Viabilidade técnica + estimativa |
| 4. Adversarial | @raven-critic | Challenge da decisão |
| 5. Alinhamento | @oracle + Eduardo | Decisão final |

**Por quê:** item [DECIDIR] de alto impacto estratégico — processo completo com perspectiva adversarial obrigatória.

## Status

- [x] Pendente
- [ ] Em progresso
- [ ] Concluído
