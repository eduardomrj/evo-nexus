---
author: claude
agent: oracle
type: work-plan-item
date: 2026-05-08
phase: 3
item-id: F3-02
status: completed
---

# F3-02. Testes automatizados e validação manual

**Fase:** Fase 3 — Robustez, testes e status avançado  
**Eixo:** qualidade  
**Tipo:** [ATIVAR]  
**Prazo sugerido:** antes de qualquer cutover

## O que é

Criar cobertura de testes e um checklist manual para garantir que a bridge não substitui o channel oficial sem evidência de estabilidade.

## O que fazer

- Testar parser de comandos e montagem de prompt.
- Testar transições de status no SQLite/JSONL.
- Testar timeout, erro e cancelamento com subprocess mockado.
- Testar integração com mock de Discord para reações e mensagens.
- Rodar validação manual em canal privado com tarefa curta, longa, erro forçado e concorrência.

## Agente / Skill / Rotina

@grid lidera testes. @oath verifica evidências. @probe pode executar QA interativo em sessão real se necessário.

## O que o usuário precisa decidir/fornecer

Checklist manual aprovado e autorização para teste em canal privado quando chegar a hora.

## Impacto esperado

Reduz o risco de trocar um problema de UX por uma instabilidade operacional. Cria confiança antes da integração.

## Dependências

F3-01.

## Riscos

- Mocks divergirem do comportamento real do Discord.
- Testes cobrirem subprocess mas não latência/erro real do OpenClaude.

## Agente sugerido pra implementação

**Time:** @grid → @probe → @oath

| Fase | Agente | Papel |
|---|---|---|
| 1. Testes | @grid | Criar testes automatizados |
| 2. QA | @probe | Rodar validação interativa se necessário |
| 3. Verify | @oath | Emitir relatório PASS/FAIL/INCOMPLETE |

**Por quê esse time:** este item é principalmente qualidade e evidência, não desenvolvimento de feature.

## Resultado reconciliado

Concluído para automação. Os testes foram criados em `tests/evo_projects/test_discord_openclaude_bridge.py` cobrindo config, allowlist, store, parser de stream, sucesso/erro, `/status`, `/cancel` stub, concorrência e token ausente. A validação manual ainda depende do teste com o novo bot.

## Validação real

Concluída em 2026-05-08 no tópico/canal de teste. Testes manuais executados com sucesso:

- `/status` respondeu corretamente.
- Tarefa mais longa respondeu corretamente.
- Duas mensagens em sequência validaram o bloqueio de concorrência por canal.

## Status

- [ ] Pendente
- [ ] Em progresso
- [x] Concluído
