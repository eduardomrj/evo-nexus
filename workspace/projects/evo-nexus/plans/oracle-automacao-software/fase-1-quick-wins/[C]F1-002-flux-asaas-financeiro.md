---
author: claude
agent: oracle
type: work-plan-item
date: 2026-04-17
phase: 1
item-id: F1-002
status: pending
---

# F1-002. Flux + Asaas — Visibilidade Financeira

**Fase:** 1 — Quick Wins
**Eixo:** Financeiro
**Tipo:** [ATIVAR]
**Prazo sugerido:** Sem 1-2

## O que é

Configurar o agente Flux com heartbeat a cada 6h para monitorar cobranças via Asaas: inadimplência, boletos vencidos, status de pagamentos. Gera pulso financeiro diário às 19h com snapshot de receita e alertas de risco. Base para a automação de cobranças da Fase 2.

## O que fazer

- Configurar `int-asaas` com API key da conta Asaas
- Habilitar heartbeat `flux-6h` com decision prompt focado em: clientes inadimplentes > 5 dias, boletos vencidos, falhas de cobrança
- Ativar rotina `fin-daily-pulse` (19:00) para relatório diário de cobranças e receita
- Configurar alerta automático via `int-telegram` para inadimplência > 15 dias (gatilho de atenção) e > 30 dias (pré-bloqueio)

## Agente / Skill / Rotina

`@flux-finance` + heartbeat `flux-6h` + skill `fin-daily-pulse` + `int-asaas` + `int-telegram` para alertas

## O que o usuário precisa decidir/fornecer

- API key do Asaas (modo produção ou sandbox para testes)
- Regra de inadimplência: D+X para alerta, D+Y para notificação de bloqueio
- Canal de alerta: Telegram (qual número/grupo?) ou Discord?

## Impacto esperado

Visibilidade diária de receita e inadimplência sem acessar o Asaas manualmente. Alerta proativo antes do cliente ficar inadimplente demais. Fundação para o escalonamento automático de cobranças (F2-009).

## Dependências

- Conta Asaas com API key habilitada
- Telegram bot ativo (para alertas) — ou substituir por Discord

## Riscos

- API key com permissões insuficientes — mitigação: testar com `int-asaas` manualmente antes de habilitar heartbeat

## Agente sugerido pra implementação

**Agente:** @flux-finance

**Por quê:** item [ATIVAR] direto — skill e integração já existem, só precisa de configuração.

## Status

- [x] Pendente
- [ ] Em progresso
- [ ] Concluído
