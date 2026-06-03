---
author: claude
agent: oracle
type: work-plan-item
date: 2026-05-13
phase: 3
item-id: MOD-08
status: pending
---

# MOD-08. Reduzir BridgeHandler a facade fina

**Fase:** Facade Fina e Prontidão para Próximas Features
**Eixo:** arquitetura-manutenibilidade
**Tipo:** [EVOLUIR]
**Prazo sugerido:** após extrações da Fase 2

## O que é

Remover lógica residual do `BridgeHandler` e deixá-lo como composição/coordenação de dependências. O handler deve orquestrar, não conter SQL, montagem CLI, parsing de stream ou formatação longa.

## O que fazer

- Remover parsing, persistência, runner, formatação longa e detalhes Discord residuais do handler.
- Manter apenas allowlist orchestration, fluxo alto nível de mensagem normal e delegação para handlers.
- Definir interfaces explícitas entre registry, store, runner, adapter e command handlers.
- Atualizar `docs/ARCHITECTURE.md` por responsabilidade final.
- Rodar verificação final com suíte, fixture DB e import smoke.

## Agente / Skill / Rotina

@apex-architect + @bolt-executor + @lens-reviewer + @oath-verifier.

## O que o usuário precisa decidir/fornecer

Decidir se a meta de sucesso será por responsabilidade ou por alvo numérico aproximado de linhas. Recomendação: responsabilidade primeiro; número de linhas apenas indicador.

## Impacto esperado

Reduz risco de novas features virarem remendos no monólito e torna o bridge mais fácil de manter.

## Dependências

MOD-04, MOD-05, MOD-06 e MOD-07.

## Riscos

Criar um framework interno complexo demais. O objetivo é simplicidade operacional, não abstração por abstração.

## Critérios de aceite

- `BridgeHandler` não contém SQL, montagem CLI, parsing de stream ou formatação longa de comando.
- Handler coordena dependências e delega para módulos.
- Comportamentos críticos continuam verdes.
- Docs refletem a arquitetura modular.

## Agente sugerido pra implementação

**Time:** @apex → @bolt → @lens → @oath

| Fase | Agente | Papel |
|---|---|---|
| 1. Arquitetura | @apex | Validar facade e boundaries finais |
| 2. Build | @bolt | Reduzir handler e ajustar composição |
| 3. Review | @lens | Revisar simplicidade e SOLID |
| 4. Verify | @oath | Verificar não regressão com evidência |

**Por quê esse time:** é o fechamento arquitetural do refactor; precisa de design, execução e verificação independente.

## Status

- [x] Pendente
- [ ] Em progresso
- [ ] Concluído
