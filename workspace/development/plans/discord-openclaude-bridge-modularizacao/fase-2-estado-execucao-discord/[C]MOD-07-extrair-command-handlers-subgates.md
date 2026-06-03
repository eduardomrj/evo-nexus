---
author: claude
agent: oracle
type: work-plan-item
date: 2026-05-13
phase: 2
item-id: MOD-07
status: pending
---

# MOD-07. Extrair command handlers em subgates

**Fase:** Extração de Estado, Execução e Interface Discord
**Eixo:** comandos-ux-operacional
**Tipo:** [EVOLUIR]
**Prazo sugerido:** final da Fase 2

## O que é

Separar comandos em handlers menores, por risco, sem mudar copy/semântica pública. O objetivo é evitar uma extração grande que quebre vários comandos ao mesmo tempo.

## O que fazer

- Extrair handlers read-only: `/status`, `/context`, `/last`.
- Extrair handlers bootstrap: `/start` e `/reset-session`.
- Extrair handlers de projeto: `/project current/select/clear` e manter `/project new` placeholder sem side effects.
- Preservar current-only/historical split.
- Preservar reset bootstrap e sessão por `channel_id + project_slug`.
- Rodar testes por subgate e suíte completa.

## Agente / Skill / Rotina

@bolt-executor + @grid-tester + @probe-qa + @lens-reviewer + @oath-verifier.

## O que o usuário precisa decidir/fornecer

Decidir se a UX textual será congelada byte-a-byte ou por equivalência semântica. Recomendação: byte-a-byte apenas para mensagens críticas de instrução; semântica para status longos.

## Impacto esperado

Facilita evolução futura de comandos sem inflar `BridgeHandler` novamente.

## Dependências

MOD-04, MOD-05 e MOD-06.

## Riscos

Regressão simultânea em comandos se os subgates não forem respeitados.

## Critérios de aceite

- `/status` e `/context` não mostram histórico antigo.
- `/last` mostra histórico e última execução corretamente.
- `/start` cria/usa sessão leve no escopo correto e preserva projeto ativo.
- `/reset-session` bloqueia execução ativa, reseta escopo atual e faz bootstrap automático.
- `/project new` continua placeholder sem criar pastas/editar registry/metas.

## Agente sugerido pra implementação

**Time:** @compass → @bolt → @grid → @lens → @oath → @probe

| Fase | Agente | Papel |
|---|---|---|
| 1. Plano curto | @compass | Fatiar handlers por subgate |
| 2. Build | @bolt | Extrair handlers |
| 3. Testes | @grid | Validar cada subgate |
| 4. Review | @lens | Revisar regressões e UX |
| 5. Verify | @oath | Verificar evidência final |
| 6. QA | @probe-qa | Smoke Discord quando autorizado |

**Por quê esse time:** comandos são a interface pública; exigem extração incremental e validação independente.

## Status

- [x] Pendente
- [ ] Em progresso
- [ ] Concluído
