---
author: claude
agent: oracle
type: work-plan-item
date: 2026-05-19
phase: 5
item-id: DCB-v2-10
status: pending
---

# DCB-v2-10. Planejar cutover com rollback imediato para v1

**Fase:** Fase 5 — Cutover/rollback e decomissionamento v1
**Eixo:** operacao-release
**Tipo:** [DECIDIR]
**Prazo sugerido:** após shadow aprovado

## O que é

Definir ativação gradual da v2 e retorno seguro para v1 em caso de falha.

## O que fazer

- Definir pré-condições de cutover: Gate G1 aprovado, Gate G3 aprovado, shadow sem duplicidade e rollback testado.
- Definir estratégia: canal piloto, allowlist, expansão por servidor/canal e produção total.
- Definir rollback: flag única para desligar v2, v1 fallback ativo, preservação/reset de sessões e mensagem operacional.
- Definir janela de mudança.
- Definir responsável por monitoramento.
- Definir critérios de abortar: duplicidade, chunking quebrado, policy bypass, falha de entrega, crash recorrente ou saída fora do gateway.

## Agente / Skill / Rotina

`@custom-sysops`, `@flow-git`, `@oath-verifier`, `@atlas-project`, `ops-change-request` se quiser registrar como mudança operacional.

## O que o usuário precisa decidir/fornecer

- Janela de cutover.
- Se sessões podem ser resetadas.
- Canal/público inicial.
- Rollback automático ou manual.

## Impacto esperado

Troca controlada sem big bang e com retorno seguro para v1.

## Dependências

Shadow rollout aprovado, v1 fallback operacional e flags/config prontas.

## Riscos

- Rollback não preservar contexto.
- Usuários verem respostas duplicadas.
- Falha parcial sem alerta.

## Agente sugerido pra implementação

**Time:** @oracle → @custom-sysops → @bolt-executor → @oath-verifier → @flow-git

| Fase | Agente | Papel |
|---|---|---|
| 1. Decisão | @oracle | Conduzir janela e risco com Eduardo |
| 2. Infra | @custom-sysops | Serviço, flags, rollback |
| 3. Técnico | @bolt-executor | Ajustes necessários |
| 4. Verify | @oath-verifier | Verificar cutover/rollback |
| 5. Git/release | @flow-git | Commit/release se aprovado |

**Por quê esse time:** cutover é decisão operacional com risco de produção.

## Status

- [x] Pendente
- [ ] Em progresso
- [ ] Concluído
