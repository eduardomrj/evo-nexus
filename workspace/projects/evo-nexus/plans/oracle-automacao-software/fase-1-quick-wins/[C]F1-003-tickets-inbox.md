---
author: claude
agent: oracle
type: work-plan-item
date: 2026-04-17
phase: 1
item-id: F1-003
status: pending
---

# F1-003. Sistema de Tickets Nativo — Inbox Centralizado

**Fase:** 1 — Quick Wins
**Eixo:** Organização
**Tipo:** [ATIVAR]
**Prazo sugerido:** Sem 1

## O que é

Ativar o sistema de tickets nativo do EvoNexus como inbox único para toda a operação. Substitui o modelo atual de "tudo no WhatsApp e na memória". Cada ticket tem status, prioridade, agente responsável, e timeline de atividade. Os agentes (Zara, Flux, Nex) consultam e atuam nos seus respectivos inboxes.

## O que fazer

- Definir assignees padrão: suporte → `@zara-cs`, financeiro → `@flux-finance`, comercial → `@nex-sales`, desenvolvimento → `@atlas-project`
- Criar backlog inicial de tickets: os 10 problemas de suporte e pendências comerciais mais recorrentes
- Configurar categorias e prioridades padrão para o contexto da Automação Software
- Treinar Eduardo e técnico no uso da UI `/issues` — criar, atualizar, atribuir, fechar

## Agente / Skill / Rotina

Skill `create-ticket` para criação + UI `/issues` para gestão + @zara-cs, @flux-finance, @nex-sales como assignees

## O que o usuário precisa decidir/fornecer

- Categorias de tickets (suporte operacional, suporte bug, financeiro, comercial, desenvolvimento)
- Quem recebe notificação de tickets P1/urgent (Eduardo? técnico? ambos?)
- O backlog inicial — lista das pendências atuais que precisam de ticket

## Impacto esperado

Nenhum pedido se perde. Visibilidade total de pendências. Base para que os heartbeats dos agentes funcionem — Zara, Flux e Nex consultam seus inboxes automaticamente.

## Dependências

- Dashboard EvoNexus rodando (porta 8080) — `/issues` disponível

## Riscos

- Adoção: Eduardo e técnico precisam migrar o hábito de "resolver no WhatsApp" para criar tickets — mitigação: começar com só os P1/P2, não forçar tickets para tudo

## Agente sugerido pra implementação

**Agente:** @oracle (conduz a criação do backlog inicial com Eduardo) + domínios owners para assignees

**Por quê:** item [ATIVAR] de configuração — Oracle acompanha Eduardo para criar as primeiras categorias e o backlog inicial.

## Status

- [x] Pendente
- [ ] Em progresso
- [ ] Concluído
