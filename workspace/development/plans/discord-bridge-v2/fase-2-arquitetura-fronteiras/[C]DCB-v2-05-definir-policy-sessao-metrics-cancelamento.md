---
author: claude
agent: oracle
type: work-plan-item
date: 2026-05-19
phase: 2
item-id: DCB-v2-05
status: pending
---

# DCB-v2-05. Definir contrato de policy, sessão, metrics e cancelamento

**Fase:** Fase 2 — Arquitetura v2 e interfaces de fronteira
**Eixo:** runtime-governanca
**Tipo:** [EVOLUIR]
**Prazo sugerido:** antes do spike

## O que é

Separar policy, sessão, metrics e cancelamento em contratos próprios, evitando regras espalhadas nos handlers do Discord.

## O que fazer

- Definir `PolicyEngine`: quem pode chamar, onde pode chamar, quais comandos são permitidos e comportamento em negação.
- Definir `ChannelSessionStore`: chave de sessão, vínculo com thread/canal/usuário, recuperação após restart e expiração.
- Definir `MetricsRecorder`: início/fim, tokens/custo se disponível, duração, status, erro e agente/skill/MCP.
- Definir `CancellationController`: cancelamento por usuário, timeout, propagação ao subprocess e resposta via gateway.
- Definir comportamento quando não houver `bridge_reply`.
- Definir comportamento quando erro ocorre antes da primeira resposta.

## Agente / Skill / Rotina

`@apex-architect`, `@echo-analyst`, `@vault-security`, `@grid-tester`.

## O que o usuário precisa decidir/fornecer

- Política inicial: MASTER equivalente ao terminal, por usuário, por canal e por projeto.
- Se sessão por thread é obrigatória ou opcional.

## Impacto esperado

Reduz regressões em sessão/metrics/policy, torna cancelamento previsível e permite fallback seguro.

## Dependências

Inventário must-have e decisão sobre policy desejada.

## Riscos

- Policy permissiva demais.
- Sessão incompatível com histórico atual.
- Metrics virarem dependência bloqueante da resposta.

## Agente sugerido pra implementação

**Time:** @compass-planner → @apex-architect → @vault-security → @grid-tester → @bolt-executor → @oath-verifier

| Fase | Agente | Papel |
|---|---|---|
| 1. Plano | @compass-planner | Quebrar evolução em passos |
| 2. Arquitetura | @apex-architect | Contratos de runtime |
| 3. Segurança | @vault-security | Policy e dados sensíveis |
| 4. Testes | @grid-tester | Matriz de regressão |
| 5. Build | @bolt-executor | Implementação futura |
| 6. Verify | @oath-verifier | Verificação evidence-based |

**Por quê esse time:** evolução de runtime com impacto em segurança, sessão e operação.

## Status

- [x] Pendente
- [ ] Em progresso
- [ ] Concluído
