---
author: claude
agent: oracle
type: work-plan-item
date: 2026-05-08
phase: 4
item-id: F4-01
status: pending-after-real-bot-test
---

# F4-01. Integrar roteamento para agentes EvoNexus

**Fase:** Fase 4 — Integração EvoNexus e cutover controlado  
**Eixo:** evonexus-native  
**Tipo:** [EVOLUIR]  
**Prazo sugerido:** depois da POC estável

## O que é

Transformar a bridge em uma interface operacional real do EvoNexus, com comandos textuais e roteamento seguro para agentes/skills.

## O que fazer

- Mapear comandos textuais iniciais: `/oracle`, `/flux`, `/bolt`, `/status`, `/cancel`.
- Montar prompts seguros em pt-BR com contexto do Discord.
- Definir allowlist de skills/agentes expostos pelo Discord.
- Exigir confirmação para ações destrutivas ou sensíveis.
- Avaliar integração futura com tickets/sessões do EvoNexus para rastreabilidade no dashboard.

## Agente / Skill / Rotina

Oracle define experiência e guardrails. @compass planeja evolução. @bolt implementa. @vault revisa segurança.

## O que o usuário precisa decidir/fornecer

- Lista inicial de comandos/agentes expostos no Discord.
- Política de permissões por usuário/canal.
- Se comandos nativos do Discord entram agora ou ficam para fase posterior.

## Impacto esperado

A bridge deixa de ser apenas um bot que chama OpenClaude e passa a ser uma entrada controlada para o EvoNexus.

## Dependências

POC estável com status, logs e testes.

## Riscos

- Expor skills perigosas no Discord.
- Confundir comandos textuais com slash commands nativos.
- Perder contexto se chamadas forem stateless.

## Agente sugerido pra implementação

**Time:** @oracle → @compass → @vault → @bolt → @oath

| Fase | Agente | Papel |
|---|---|---|
| 1. Framing | @oracle | Definir UX e guardrails com o usuário |
| 2. Spec | @compass | Planejar comandos e integração |
| 3. Segurança | @vault | Revisar exposição de ações e permissões |
| 4. Build | @bolt | Implementar roteamento |
| 5. Verify | @oath | Verificar critérios de aceite |

**Por quê esse time:** integração com agentes e skills via Discord tem impacto de segurança e produto.

## Status

- [x] Pendente
- [ ] Em progresso
- [ ] Concluído
