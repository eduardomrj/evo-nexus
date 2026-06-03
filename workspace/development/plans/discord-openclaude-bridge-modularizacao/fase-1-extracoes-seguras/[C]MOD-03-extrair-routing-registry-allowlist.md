---
author: claude
agent: oracle
type: work-plan-item
date: 2026-05-13
phase: 1
item-id: MOD-03
status: completed
---

# MOD-03. Extrair routing, registry e allowlist

**Fase:** Extrações Seguras de Baixo Risco
**Eixo:** roteamento-autorizacao-configuracao
**Tipo:** [EVOLUIR]
**Prazo sugerido:** após MOD-02

## O que é

Separar `ProjectRoute`, `ProjectRegistry` e allowlist mantendo `/project` e autorização por canal/tópico compatíveis com o baseline.

## O que fazer

- Extrair `ProjectRoute` de `src/discord_openclaude_bridge.py:173`.
- Extrair `ProjectRegistry` de `:188` e leitura de `config/projects.yaml:1`.
- Encapsular validação de `repo_path` e `add_dirs` sem ampliar permissões.
- Separar allowlist multi-channel e autorização por parent thread.
- Testar `project select/current/clear`, canal permitido, tópico permitido via parent e canal negado.

## Agente / Skill / Rotina

@bolt-executor + @grid-tester + @lens-reviewer.

## O que o usuário precisa decidir/fornecer

Decidir se erros de configuração continuam permissivos como hoje ou se um modo strict futuro deve ser planejado sem ativar agora.

## Impacto esperado

Remove do handler uma área crítica e prepara `/project new` futuro sem alterar comportamento nesta onda.

## Dependências

MOD-00, MOD-01 e MOD-02.

## Riscos

Regressão em autorização por canal/tópico, resolução de alias ou bloqueio de paths sensíveis.

## Critérios de aceite

- `config/projects.yaml` atual resolve igual ao baseline.
- Allowlist singular e plural continuam funcionando em união sem duplicatas.
- Tópicos com parent permitido continuam autorizados.
- Paths sensíveis continuam bloqueados/redigidos conforme contrato atual.

## Agente sugerido pra implementação

**Time:** @compass → @bolt → @grid → @lens

| Fase | Agente | Papel |
|---|---|---|
| 1. Plano curto | @compass | Definir ordem de extração |
| 2. Build | @bolt | Extrair routing/registry/allowlist |
| 3. Testes | @grid | Validar autorização e project routing |
| 4. Review | @lens | Revisar segurança e boundaries |

**Por quê esse time:** routing e allowlist são sensíveis; precisam de implementação pequena e revisão de segurança lógica.

## Status

- [ ] Pendente
- [ ] Em progresso
- [x] Concluído

## Evidência de conclusão

- Commit: `fcbf1be refactor(discord): extract v1 registry modules`
- Gate executado: `python3 -m pytest -q tests/test_discord_openclaude_bridge.py`
- Resultado: `202 passed, 1 warning`
- Escopo: extraídos `ProjectRoute`, `AccessRole`, `AccessUser`, `ResolvedAccess`, `AccessRegistry` e `ProjectRegistry` para `src/discord_openclaude_bridge/registry.py`, preservando contrato legacy e sem tocar na v2.
