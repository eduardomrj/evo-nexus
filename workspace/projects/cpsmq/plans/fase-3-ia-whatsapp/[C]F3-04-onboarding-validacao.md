---
author: claude
agent: oracle
type: work-plan-item
date: 2026-04-26
phase: 3
item-id: F3-04
status: pending
---

# F3-04. Onboarding e validação com Elistênio

**Fase:** IA + WhatsApp
**Eixo:** produto
**Tipo:** [DECIDIR]
**Prazo sugerido:** Sem 5 — fechamento do MVP

## O que é

Cerimônia de entrega do MVP: Elistênio recebe acesso, valida os dados de pelo menos 1 mês fechado comparando com a planilha manual antiga, acompanha 3 dias de extração automática e usa o bot ao vivo. Fecha o ciclo do MVP e abre o caminho comercial para os outros consórcios.

## O que fazer

- Reunião de kickoff (vídeo ou presencial em Quixadá)
- Walkthrough das telas: cadastros, painel, extrações, bot
- **Validação crítica:** consolidado de 1 mês fechado vs planilha manual antiga — os números batem?
- Acompanhar extração nos dias D+1, D+2, D+3 com olho aberto
- Elistênio faz 5-10 perguntas ao bot ao vivo e avalia as respostas
- Coletar feedback estruturado (form simples ou conversa gravada)
- Definir SLA mínimo: uptime, prazo de resposta a falha de extração
- Definir período de cortesia antes de cobrar (se houver)
- Colher depoimento curto em vídeo (com autorização) → uso comercial

## Agente / Skill / Rotina

`@nova-product` (conduz a validação com o cliente) + `@mirror-retro` (lições aprendidas do MVP)

## O que o usuário precisa decidir/fornecer

- **Precificação:** quanto cobrar do CPSMQ (referência) e qual o pricing para os outros 20 consórcios?
- **SLA mínimo:** uptime contratual e prazo máximo para resolver falha de extração?
- **Período de cortesia:** quantos meses de uso antes de formalizar contrato?
- **Modelo comercial:** mensalidade fixa ou % do valor gerenciado?

## Impacto esperado

Fecha o ciclo MVP com evidência de funcionamento real. O depoimento do Elistênio é o argumento de venda para os outros 20 consórcios do Ceará.

## Dependências

F3-03 (bot funcionando), F3-02 (notificações funcionando), F2-04 (painel validado com dados reais).

## Riscos

Elistênio não validar os números → MVP volta para ajuste. Mitigação: entregar já com 1-2 meses de dados pré-carregados e validados antes da reunião de entrega.

## Agente sugerido pra implementação

**Agente:** @oracle (conduz) + @nova-product (validação produto) + @mirror-retro (retro)

**Por quê:** item [DECIDIR] com decisões comerciais estratégicas — Oracle e Nova garantem que o alinhamento com o cliente está completo antes de avançar para os outros consórcios.

## Status

- [x] Pendente
- [ ] Em progresso
- [ ] Concluído
