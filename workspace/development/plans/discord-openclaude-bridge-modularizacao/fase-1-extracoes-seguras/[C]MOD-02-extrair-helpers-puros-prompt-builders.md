---
author: claude
agent: oracle
type: work-plan-item
date: 2026-05-13
phase: 1
item-id: MOD-02
status: completed
---

# MOD-02. Extrair helpers puros e prompt builders

**Fase:** Extrações Seguras de Baixo Risco
**Eixo:** modularidade-incremental
**Tipo:** [EVOLUIR]
**Prazo sugerido:** após MOD-00 e MOD-01

## O que é

Mover defaults/config auxiliares, parsing puro, formatação e prompt builders para módulos dedicados sem alterar fluxo async, runtime Discord ou comportamento público.

## O que fazer

- Extrair defaults/constants e helpers puros de config de `src/discord_openclaude_bridge.py:43`.
- Extrair parsing de allowlist multi-channel de `:286`, preservando compatibilidade `CHANNEL_ID` e `CHANNEL_IDS`.
- Extrair helpers de formatação onboarding/projeto de `:1950`.
- Extrair prompt builders de `:3081`.
- Usar shims temporários se aprovados em MOD-01.
- Rodar `py_compile`, import smoke, testes focados e suíte completa.

## Agente / Skill / Rotina

@bolt-executor + @grid-tester + @lens-reviewer + @oath-verifier.

## O que o usuário precisa decidir/fornecer

Confirmar se aceita shims transitórios para reduzir diff e risco de quebra.

## Impacto esperado

Primeira redução concreta do monólito com baixo risco operacional. Ajuda a validar a estratégia de pacote antes das extrações sensíveis.

## Dependências

MOD-00 e MOD-01.

## Riscos

Import circular ou mudança sutil em texto de prompt. O prompt bootstrap precisa manter a regra de não analisar, não usar ferramentas e apenas confirmar prontidão.

## Critérios de aceite

- Outputs dos helpers permanecem equivalentes ao baseline.
- Prompt bootstrap mantém a regra de Oracle apenas confirmar prontidão.
- Testes focados e suíte completa verdes.

## Agente sugerido pra implementação

**Time:** @compass → @bolt → @grid → @lens → @oath

| Fase | Agente | Papel |
|---|---|---|
| 1. Plano curto | @compass | Quebrar a extração em passos pequenos |
| 2. Build | @bolt | Implementar movimentação de código |
| 3. Testes | @grid | Ajustar/rodar testes focados |
| 4. Review | @lens | Revisar acoplamento/imports |
| 5. Verify | @oath | Produzir evidência de não regressão |

**Por quê esse time:** é uma evolução estrutural de baixo risco, mas ainda exige verificação forte.

## Status

- [ ] Pendente
- [ ] Em progresso
- [x] Concluído

## Evidência de conclusão

- Commit: `7d64c20 refactor(discord): extract v1 formatting and prompt helpers`
- Hardening pós-Lens: `5633ee5 test(discord): cover prompt attachment formatting contract`
- Gate executado: `python3 -m pytest -q tests/test_discord_openclaude_bridge.py`
- Resultado: `204 passed, 1 warning`
- Import normal validado: `PYTHONPATH=src python3 -c "import discord_openclaude_bridge"`.
- Escopo: extraídos helpers puros de formatação/parsing para `src/discord_openclaude_bridge/formatting.py`, helpers de projeto para `src/discord_openclaude_bridge/helpers.py` e prompt builders para `src/discord_openclaude_bridge/prompts.py`, preservando shims/reexports legacy e sem tocar em v2, runner, delivery, attachments runtime, command handlers ou SQLite.
