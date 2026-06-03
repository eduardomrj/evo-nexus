---
author: claude
agent: oracle
type: work-plan-item
date: 2026-04-17
phase: 2
item-id: F2-004
status: pending
---

# F2-004. Stack da Plataforma GO — Madbuilder/Adianti vs Laravel/Filament

**Fase:** 2 — Conexões
**Eixo:** Engineering
**Tipo:** [DECIDIR]
**Prazo sugerido:** Sem 5-7 (timebox: 2 semanas para decidir)

## O que é

A decisão mais crítica da Plataforma GO. Continuar com Madbuilder/Adianti (limitações visuais, lowcode, menos adequado para vibe coding com IA) ou migrar para Laravel + Filament (mais flexível, comunidade ativa, melhor para desenvolvimento com IA). Precisa ser resolvida com ADR formal antes de qualquer código dos módulos da Fase 3.

## O que fazer

- Discovery com @echo-analyst: levantar requisitos reais da Plataforma GO (módulos, integrações, multi-tenant, escala, time de 1-2 devs, velocidade com IA)
- Research com @scroll-docs: documentação de ambas as stacks (Madbuilder/Adianti e Laravel/Filament), comparação de ecossistemas, maturidade
- ADR via @apex-architect: Decision, Drivers (velocidade de desenvolvimento com IA, flexibilidade visual, comunidade PHP, curva de aprendizado, custo), Alternatives, Consequences
- Review adversarial via @raven-critic: steelman da opção não-escolhida para evitar viés
- Se necessário: protótipo rápido de 1 módulo simples em cada stack (1-2 dias) antes da decisão final

## Agente / Skill / Rotina

`@echo-analyst` + `@scroll-docs` + `@apex-architect` + `@raven-critic` + skill `dev-ralplan` (consensus mode para decisão de alto impacto)

## O que o usuário precisa decidir/fornecer

- Critérios de peso: velocidade de desenvolvimento com IA é o mais importante? Ou flexibilidade a longo prazo? Ou curva de aprendizado?
- Restrições: precisa ser PHP? Considera outro stack além dos dois listados (ex: NestJS, FastAPI)?
- Aprovação final do ADR — Eduardo decide, Apex e Raven apresentam a análise

## Impacto esperado

Decisão documentada e fundamentada. Zero retrabalho por troca de stack no meio do desenvolvimento. Toda a Fase 3 desbloqueada.

## Dependências

- Nenhuma técnica — pode iniciar no começo da Fase 2

## Riscos

- **ALTO** — decisão errada atrasa meses e cria dívida técnica enorme
- Paralisia de análise — mitigação: timebox de 2 semanas. Se não decidir, protótipo de 2 dias desfaz a dúvida
- Viés de confirmação (já usar Madbuilder/Adianti) — mitigação: @raven-critic faz steelman obrigatório da outra opção

## Agente sugerido pra implementação

| Fase | Agente | Papel |
|---|---|---|
| 1. Discovery | @echo-analyst | Requisitos reais da GO Platform |
| 2. Research | @scroll-docs | Documentação comparativa |
| 3. ADR | @apex-architect | Decision Record com recomendação |
| 4. Adversarial | @raven-critic | Steelman da opção não-escolhida |
| 5. Decisão | @oracle + Eduardo | Alinhamento final |

**Por quê:** decisão de alto impacto com risco alto — processo completo com perspectivas múltiplas obrigatório.

## Status

- [x] Pendente
- [ ] Em progresso
- [ ] Concluído
