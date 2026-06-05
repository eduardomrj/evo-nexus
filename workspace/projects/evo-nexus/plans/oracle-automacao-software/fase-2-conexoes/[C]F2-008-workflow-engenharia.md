---
author: claude
agent: oracle
type: work-plan-item
date: 2026-04-17
phase: 2
item-id: F2-008
status: pending
---

# F2-008. Workflow de Engenharia — Feature Folders + 6 Fases

**Fase:** 2 — Conexões
**Eixo:** Engineering
**Tipo:** [ATIVAR]
**Prazo sugerido:** Sem 5

## O que é

Ativar o workflow de 6 fases (Discovery → Planning → Solutioning → Build → Verify → Retro) para todo desenvolvimento novo da Automação Software. Emporion, GO Platform e SERKET passam a ter feature folders com artefatos organizados. O Helm orquestra o sequenciamento entre features.

## O que fazer

- Criar feature folders para os projetos em andamento: `workspace/development/features/go-platform-stack/`, `workspace/development/features/chatwoot-to-evocrm/`, `workspace/development/features/serket-inovaaf/`
- Ativar @helm-conductor como orquestrador do ciclo de desenvolvimento
- Configurar @lens-reviewer para code review nas PRs críticas (novos módulos, mudanças de arquitetura)
- Configurar @flow-git para commits atômicos com detecção de estilo dos repos da Automação Software
- Documentar as convenções de desenvolvimento no contexto dos produtos da Automação Software

## Agente / Skill / Rotina

`@helm-conductor` (orquestração) + `@lens-reviewer` (code review) + `@flow-git` (git) + `@atlas-project` (monitoramento)

## O que o usuário precisa decidir/fornecer

- Quer code review automático em todas as PRs ou apenas nas críticas (novos módulos, mudanças de API)?
- Linear vs GitHub Issues para tracking de desenvolvimento? (ou apenas GitHub Issues?)
- Quais repos entram no workflow primeiro: Emporion? GO? SERKET? Todos?

## Impacto esperado

Desenvolvimento estruturado. Nenhuma feature começa sem planejamento. Cada decisão arquitetural fica documentada em ADR. Facilita onboarding de novos devs no futuro.

## Dependências

- F1-006 (Atlas monitorando GitHub)

## Riscos

- Overhead de processo para time de 2 — mitigação: usar a tabela de "quando pular fases" do dev-phases.md. Bugs simples vão direto para Build → Verify, sem Discovery.

## Agente sugerido pra implementação

**Agente:** @helm-conductor (com apoio de @atlas-project)

**Por quê:** item [ATIVAR] de orquestração — Helm é o dono desse domínio.

## Status

- [x] Pendente
- [ ] Em progresso
- [ ] Concluído
