---
author: claude
agent: oracle
type: work-plan-item
date: 2026-04-17
phase: 1
item-id: F1-004
status: pending
---

# F1-004. Goals — Missão e Projetos Estruturados

**Fase:** 1 — Quick Wins
**Eixo:** Organização
**Tipo:** [ATIVAR]
**Prazo sugerido:** Sem 1

## O que é

Criar a hierarquia Mission → Project → Goal → Task no EvoNexus para os 3 projetos ativos. Toda ação dos agentes passa a ter um objetivo mensurável associado. O painel `/goals` mostra o progresso em tempo real.

## O que fazer

- Criar missão: "Automação Software — Plataforma micro-SaaS de varejo e saúde" (ou nome que Eduardo preferir)
- Criar os 3 projetos: **Emporion Desktop** (manutenção), **Plataforma GO** (construção), **SERKET** (evolução)
- Definir goals para 90 dias — sugestões:
  - Emporion: "Zero bugs P1 abertos" (count)
  - Plataforma GO: "Stack definida e primeiro módulo iniciado" (boolean)
  - SERKET: "Discovery Hub InovaAF concluído" (boolean)
- Vincular tickets e heartbeats futuros a esses goals via `goal_id`

## Agente / Skill / Rotina

Skill `create-goal` (wizard interativo) + @atlas-project para monitoramento + UI `/goals` para visualização

## O que o usuário precisa decidir/fornecer

- Nome da missão (sugestão acima ou outro)
- Metas específicas para 90 dias — confirmar ou ajustar as sugeridas
- Métrica principal de sucesso para cada projeto (count, boolean, currency, percentage?)

## Impacto esperado

Painel de progresso visual em `/goals`. Cada ação dos agentes conectada a um objetivo mensurável. Eduardo sabe a qualquer momento o que está avançando e o que está parado.

## Dependências

- Nenhuma técnica — pode começar agora

## Riscos

- Goals muito abstratos não avançam — mitigação: usar `metric_type: boolean` ou `count` em vez de percentual genérico

## Agente sugerido pra implementação

**Agente:** @oracle (conduz com Eduardo via skill create-goal)

**Por quê:** decisão de negócio que precisa de alinhamento — Oracle mantém a conversa enquanto cria.

## Status

- [x] Pendente
- [ ] Em progresso
- [ ] Concluído
