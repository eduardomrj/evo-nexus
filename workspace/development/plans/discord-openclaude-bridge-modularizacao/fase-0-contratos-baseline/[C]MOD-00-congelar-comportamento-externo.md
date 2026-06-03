---
author: claude
agent: oracle
type: work-plan-item
date: 2026-05-13
phase: 0
item-id: MOD-00
status: pending
---

# MOD-00. Congelar comportamento externo do bridge

**Fase:** Contratos e Segurança de Baseline
**Eixo:** segurança-regressao-contrato-externo
**Tipo:** [ATIVAR]
**Prazo sugerido:** antes de qualquer extração

## O que é

Transformar o comportamento validado do bridge em contrato verificável antes de mover código. O objetivo é impedir falso verde em testes fake-based e preservar a experiência real no Discord.

## O que fazer

- Criar matriz black-box dos comandos `/start`, `/reset-session`, `/status`, `/context`, `/last` e `/project`.
- Criar matriz canal/tópico/allowlist: canal permitido direto, tópico com parent permitido, canal negado, novo thread com onboarding e múltiplos canais permitidos.
- Congelar contratos slash `defer/followup` para comandos lentos, especialmente `/start` e `/reset-session`.
- Definir snapshots semânticos para `/status` current-only, `/context` current-only e `/last` histórico.
- Definir invariantes de redaction/logging e não vazamento de dados sensíveis.
- Criar fixtures realistas de SQLite/runtime para histórico, sessão por `channel_id + project_slug`, `project/cwd/add_dirs` e onboarding.

## Agente / Skill / Rotina

@grid-tester + @oath-verifier + @lens-reviewer + skill `dev-verify`.

## O que o usuário precisa decidir/fornecer

Definir se o smoke Discord manual será exigido ao final de cada fase ou apenas no baseline/final. Recomendação: baseline e final obrigatórios; por fase quando mexer em comandos Discord.

## Impacto esperado

Reduz o risco de regressão silenciosa em comandos já validados. Cria uma linha de base objetiva para todo refactor posterior.

## Dependências

Baseline atual validado por Eduardo.

## Riscos

Snapshots byte-a-byte podem tornar o refactor lento. Preferir equivalência semântica onde a copy exata não for crítica.

## Critérios de aceite

- Cada comando crítico tem critério black-box antes/depois.
- Slash commands lentos têm contrato explícito de `defer/followup`.
- Fixtures DB cobrem histórico antigo, sessão ativa, `add_dirs` e onboarding.
- Redaction/logging entram como invariantes obrigatórias.

## Agente sugerido pra implementação

**Time:** @grid → @oath → @lens

| Fase | Agente | Papel |
|---|---|---|
| 1. Contratos | @grid-tester | Definir matriz de testes e fixtures |
| 2. Evidência | @oath-verifier | Verificar baseline com saída concreta |
| 3. Revisão | @lens-reviewer | Checar gaps de regressão e segurança |

**Por quê esse time:** este item é safety rail; precisa de testes, evidência e revisão antes de qualquer build.

## Status

- [x] Pendente
- [ ] Em progresso
- [ ] Concluído

## Evidência parcial registrada em 2026-05-20

- Gate v1 validado antes de novas extrações: `python3 -m pytest -q tests/test_discord_openclaude_bridge.py`.
- Resultado observado: `202 passed, 1 warning`.
- Observação: a suíte completa não é baseline válido neste momento porque inclui `tests/v2/*`, e a v2 está congelada.
- Pendente para concluir MOD-00: matriz black-box formal dos comandos críticos e decisão sobre smoke Discord baseline/final.
