---
author: claude
agent: oracle
type: work-plan-item
date: 2026-04-17
phase: 1
item-id: F1-001
status: pending
---

# F1-001. Zara — Triagem Automática de Suporte via WhatsApp

**Fase:** 1 — Quick Wins
**Eixo:** Suporte
**Tipo:** [ATIVAR]
**Prazo sugerido:** Sem 1-2

## O que é

Configurar a agente Zara com heartbeat a cada 2h para triagem automática dos tickets de suporte que chegam via WhatsApp. Zara classifica por prioridade (P1-P4), pesquisa a resposta no histórico e base de conhecimento, e redige a resposta para aprovação. Problemas críticos (P1-P2) são escalados para Eduardo ou técnico via Telegram.

## O que fazer

- Habilitar heartbeat `zara-2h` em `config/heartbeats.yaml` com `enabled: true` e decision prompt adaptado ao contexto: clientes de varejo, dúvidas sobre NFe, PDV, Emporion, licenças
- Criar base de conhecimento inicial com as 20 perguntas mais frequentes do suporte via skill `cs-kb-article`
- Configurar `int-evolution-api` apontando para a instância WhatsApp de suporte atual
- Ativar `cs-ticket-triage` com critérios P1-P4 customizados para a Automação Software
- Configurar escalonamento: P3-P4 → Zara responde; P1-P2 → alerta imediato via `int-telegram` para Eduardo/técnico

## Agente / Skill / Rotina

`@zara-cs` como agente dono + heartbeat `zara-2h` + skills: `cs-ticket-triage`, `cs-kb-article`, `cs-draft-response`, `cs-customer-escalation`, `cs-customer-research` + integração `int-evolution-api` + `int-telegram` para escalação

## O que o usuário precisa decidir/fornecer

- Lista das 20 perguntas mais frequentes do suporte (Eduardo e técnico constroem a KB inicial)
- Critérios de prioridade: o que é P1 (sistema caído?), P2 (funcionalidade quebrada?), P3 (dúvida operacional?), P4 (cosmético?)
- Tom de voz das respostas automáticas (formal? informal? nome da empresa na assinatura?)
- Credenciais da instância WhatsApp (Evolution API key + URL)

## Impacto esperado

Redução de 60-70% do tempo gasto com suporte repetitivo. Eduardo e técnico entram apenas quando o problema é novo ou crítico. Cada problema resolvido vira documentação automática — a próxima vez que aquela dúvida chegar, Zara já tem a resposta.

## Dependências

- Instância WhatsApp ativa com Evolution API (já existe)
- Dashboard EvoNexus rodando (porta 8080)

## Riscos

- Respostas imprecisas na primeira semana — mitigação: modo draft por 7 dias (Zara sugere, humano aprova antes de enviar)
- KB inicial incompleta — mitigação: Zara escala para humano quando confiança < 80%

## Agente sugerido pra implementação

**Agente:** @zara-cs (item [ATIVAR] — skill já existe, só precisa de configuração e KB inicial)

| Fase | Agente | Papel |
|---|---|---|
| 1. Config | @zara-cs | Habilitar heartbeat e configurar decision prompt |
| 2. KB | @zara-cs + cs-kb-article | Criar as 20 perguntas iniciais |
| 3. Teste | @zara-cs + @probe-qa | Testar fluxo de triagem com tickets fictícios |

**Por quê:** item [ATIVAR] com infraestrutura existente — Zara é dona do domínio CS, só precisa de configuração e conteúdo inicial.

## Status

- [x] Pendente
- [ ] Em progresso
- [ ] Concluído
