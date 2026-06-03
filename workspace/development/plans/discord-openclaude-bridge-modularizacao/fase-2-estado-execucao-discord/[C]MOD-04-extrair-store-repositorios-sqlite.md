---
author: claude
agent: oracle
type: work-plan-item
date: 2026-05-13
phase: 2
item-id: MOD-04
status: completed
---

# MOD-04. Extrair store e repositórios com compatibilidade SQLite

**Fase:** Extração de Estado, Execução e Interface Discord
**Eixo:** persistencia-estado-runtime
**Tipo:** [EVOLUIR]
**Prazo sugerido:** início da Fase 2

## O que é

Separar `ExecutionStore` e repositórios para execuções, sessões, projeto ativo e onboarding sem quebrar o banco SQLite/runtime existente.

## O que fazer

- Extrair `ExecutionStore` e schema de `src/discord_openclaude_bridge.py:546`.
- Separar persistência de projeto ativo de `:767`.
- Separar persistência de thread onboarding de `:804`.
- Separar sessões `channel_id + project_slug` de `:827`.
- Preservar criação de execução com `project_slug/cwd/add_dirs_json/routing_reason` de `:870`.
- Testar leitura de registros antigos e escrita de registros novos sem migração destrutiva.

## Agente / Skill / Rotina

@bolt-executor + @grid-tester + @oath-verifier + @lens-reviewer.

## O que o usuário precisa decidir/fornecer

Decidir se adicionamos validação explícita de schema agora ou se mantemos apenas compatibilidade passiva.

## Impacto esperado

Reduz risco em histórico, sessões e continuidade. Prepara futuras features ligadas a sessões e execução sem mexer no runtime público.

## Dependências

MOD-00 e MOD-01.

## Riscos

Quebrar `/last`, perder `session_id` por projeto ou alterar propagação de `add_dirs`.

## Critérios de aceite

- Fixture de DB antigo continua legível pelo novo store.
- `/last` encontra histórico antigo com projeto/cwd/add_dirs quando existir.
- Sessão por `channel_id + project_slug` permanece intacta.
- Nenhuma migration destrutiva.
- Redaction/persistência sanitizada continuam válidas.

## Agente sugerido pra implementação

**Time:** @compass → @bolt → @grid → @oath → @lens

| Fase | Agente | Papel |
|---|---|---|
| 1. Plano curto | @compass | Fatiar store/repositories |
| 2. Build | @bolt | Extrair persistência |
| 3. Testes | @grid | Cobrir fixtures SQLite |
| 4. Verify | @oath | Validar compatibilidade com evidência |
| 5. Review | @lens | Revisar riscos de dados e regressão |

**Por quê esse time:** persistência é área crítica; precisa de build cuidadoso, fixtures e verificação independente.

## Status

- [ ] Pendente
- [ ] Em progresso
- [x] Concluído

## Evidência de conclusão

- Commit: `02a6680 refactor(discord): extract v1 execution store`
- Gate executado: `python3 -m pytest -q tests/test_discord_openclaude_bridge.py`
- Resultado: `202 passed, 1 warning`
- Escopo: extraídos `JsonlLogger`, `ExecutionStore` e helpers de persistência para `src/discord_openclaude_bridge/execution_store.py`, preservando schema SQLite, contrato legacy e sem tocar na v2.
