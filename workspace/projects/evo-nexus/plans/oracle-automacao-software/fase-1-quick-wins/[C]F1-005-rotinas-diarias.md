---
author: claude
agent: oracle
type: work-plan-item
date: 2026-04-17
phase: 1
item-id: F1-005
status: pending
---

# F1-005. Rotinas Diárias — Good Morning + EOD

**Fase:** 1 — Quick Wins
**Eixo:** Organização
**Tipo:** [ATIVAR]
**Prazo sugerido:** Sem 2

## O que é

Ativar as rotinas matinal (07:00) e noturna (21:00) da Clawdia para que Eduardo comece e termine cada dia com briefing estruturado: agenda, emails, pendências, resumo do dia. Entrega via Telegram ou Discord no fuso America/Fortaleza.

## O que fazer

- Configurar Gmail MCP com credenciais de Eduardo (`gog-email-triage` + `gog-calendar`)
- Ativar rotina `prod-good-morning` (07:00) no scheduler
- Ativar rotina `prod-end-of-day` (21:00) no scheduler
- Configurar `int-telegram` para entrega dos briefings
- Ajustar horários para o fuso America/Fortaleza (UTC-3)

## Agente / Skill / Rotina

`@clawdia` + skills `prod-good-morning`, `prod-end-of-day`, `gog-calendar`, `gog-email-triage` + `int-telegram` para entrega

## O que o usuário precisa decidir/fornecer

- Credenciais Gmail MCP (autenticação OAuth)
- Canal de entrega: Telegram (preferido) ou Discord?
- Quer incluir revisão do backlog de tickets no briefing matinal?

## Impacto esperado

Eduardo nunca começa o dia sem saber o que está pendente. Decisões priorizadas desde as 07:00. Resumo noturno fecha o dia com o que foi feito e o que fica para amanhã.

## Dependências

- Gmail MCP configurado (OAuth Google)
- Telegram bot ativo (`make telegram`)

## Riscos

- Fadiga de notificações se o briefing for muito longo — mitigação: briefing condensado, máximo 5 itens prioritários

## Agente sugerido pra implementação

**Agente:** @clawdia

**Por quê:** item [ATIVAR] direto — Clawdia é dona das rotinas de produtividade pessoal.

## Status

- [x] Pendente
- [ ] Em progresso
- [ ] Concluído
