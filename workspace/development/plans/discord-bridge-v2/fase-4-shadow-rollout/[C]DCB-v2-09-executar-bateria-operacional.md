---
author: claude
agent: oracle
type: work-plan-item
date: 2026-05-19
phase: 4
item-id: DCB-v2-09
status: pending
---

# DCB-v2-09. Executar bateria operacional obrigatória

**Fase:** Fase 4 — Prova operacional e shadow rollout
**Eixo:** qa-verificacao
**Tipo:** [ATIVAR]
**Prazo sugerido:** antes de qualquer cutover

## O que é

Executar e evidenciar a matriz obrigatória antes de qualquer cutover.

## O que fazer

- Testar resposta longa com chunking, ordem e status entregue.
- Testar subagente sem vazamento intermediário e resposta final via gateway.
- Testar skill/MCP sem bypass do gateway.
- Testar erro antes de resposta com erro controlado ou log seguro.
- Testar caso sem `bridge_reply` sem saída lateral.
- Testar sessão/metrics sem acoplar metrics ao envio.
- Testar cancelamento com interrupção real e aviso via gateway.
- Testar policy: autorizado passa, negado não executa e não vaza detalhes.
- Produzir relatório PASS/FAIL/INCOMPLETE com evidências.

## Agente / Skill / Rotina

`@grid-tester`, `@probe-qa`, `@oath-verifier`, `dev-verify`.

## O que o usuário precisa decidir/fornecer

- Se algum FAIL pode ser aceito temporariamente.
- Severidade mínima para bloquear cutover.

## Impacto esperado

Impede cutover por sensação subjetiva e cria evidência objetiva.

## Dependências

Ambiente shadow ativo, gateway com auditoria e casos de teste definidos.

## Riscos

- Testes manuais sem evidência reproduzível.
- Cobertura focar happy path e perder vazamentos históricos.

## Agente sugerido pra implementação

**Time:** @grid-tester → @probe-qa → @oath-verifier → @bolt-executor

| Fase | Agente | Papel |
|---|---|---|
| 1. Testes | @grid-tester | Matriz automatizada |
| 2. QA | @probe-qa | Testes interativos |
| 3. Verify | @oath-verifier | Relatório evidence-based |
| 4. Fix | @bolt-executor | Correções se necessário |

**Por quê esse time:** item de verificação operacional; precisa evidência antes de cutover.

## Status

- [x] Pendente
- [ ] Em progresso
- [ ] Concluído
