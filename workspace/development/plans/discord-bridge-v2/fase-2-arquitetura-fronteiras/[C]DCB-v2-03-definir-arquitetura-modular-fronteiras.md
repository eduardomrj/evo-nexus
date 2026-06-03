---
author: claude
agent: oracle
type: work-plan-item
date: 2026-05-19
phase: 2
item-id: DCB-v2-03
status: pending
---

# DCB-v2-03. Definir arquitetura modular da v2 com fronteiras explícitas

**Fase:** Fase 2 — Arquitetura v2 e interfaces de fronteira
**Eixo:** arquitetura-boundaries
**Tipo:** [DECIDIR]
**Prazo sugerido:** antes do spike

## O que é

Projetar a v2 como módulos pequenos com contratos claros, removendo o monólito que mistura Discord, subprocess, stream, sessão, metrics, policy e comandos.

## O que fazer

- Definir diagrama lógico com `DiscordAdapter`, `OpenClaudeRunner`, `ChannelSessionStore`, `OutboundGateway`, `PolicyEngine`, `MetricsRecorder`, `CommandRouter`, `AuditLog` e `CancellationController`.
- Definir entrada e saída de cada módulo.
- Definir quais módulos podem conhecer Discord diretamente.
- Definir quais módulos podem conhecer OpenClaude diretamente.
- Definir quais módulos podem produzir texto visível.
- Definir interfaces mínimas em pseudocódigo/contrato.

## Agente / Skill / Rotina

`@apex-architect`, `@raven-critic`, `dev-ralplan` se a decisão precisar de consenso formal.

## O que o usuário precisa decidir/fornecer

- Se a v2 fica no repo custom atual ou nasce em pacote/módulo novo dentro dele.
- Tolerância de perda temporária de features locais.

## Impacto esperado

Reduz acoplamento, permite testes por fronteira e diminui o risco de novos vazamentos laterais.

## Dependências

DCB-v2-01 e DCB-v2-02 concluídos; must-have priorizados.

## Riscos

- Criar abstração demais e atrasar o spike.
- Manter dependências implícitas da v1 “só por enquanto”.

## Agente sugerido pra implementação

**Time:** @oracle → @apex-architect → @raven-critic → @grid-tester

| Fase | Agente | Papel |
|---|---|---|
| 1. Framing | @oracle | Conduzir escolhas com Eduardo |
| 2. Arquitetura | @apex-architect | ADR + fronteiras |
| 3. Crítica | @raven-critic | Pressão adversarial |
| 4. Testabilidade | @grid-tester | Validar se as fronteiras são testáveis |

**Por quê esse time:** decisão arquitetural central; não deve virar implementação sem ADR.

## Status

- [x] Pendente
- [ ] Em progresso
- [ ] Concluído
