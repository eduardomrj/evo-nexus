---
author: claude
agent: oracle
type: work-plan-item
date: 2026-05-13
phase: 2
item-id: MOD-05
status: pending
---

# MOD-05. Extrair runner, parser de progresso e contratos async

**Fase:** Extração de Estado, Execução e Interface Discord
**Eixo:** execucao-streaming-concorrencia
**Tipo:** [EVOLUIR]
**Prazo sugerido:** após MOD-04 parcial

## O que é

Isolar `OpenClaudeRunner` e `StreamProgressParser` preservando lifecycle assíncrono, timeout, cancelamento, progress updates e contratos de concorrência.

## O que fazer

- Documentar invariantes antes de extrair: uma execução ativa por escopo, cancelamento encerra subprocess/task, timeout preserva estado útil, reset não perde race com execução terminando.
- Extrair `OpenClaudeRunner` de `src/discord_openclaude_bridge.py:1243`.
- Extrair `StreamProgressParser` de `:1486`.
- Definir contrato de eventos/progresso entre runner, store e Discord adapter.
- Testar erro, timeout, cancel e stream conhecido.
- Garantir que exceções viram resposta/followup, não silent failure.

## Agente / Skill / Rotina

@bolt-executor + @grid-tester + @trail-tracer + @oath-verifier.

## O que o usuário precisa decidir/fornecer

Decidir se a interface do runner fica mínima agora ou se deve nascer preparada para múltiplos backends futuros sem implementar esses backends.

## Impacto esperado

Melhora debug e testabilidade do núcleo de execução sem alterar UX pública.

## Dependências

MOD-00 e MOD-04 parcial.

## Riscos

Ressuscitar race de reset/cancel/status ou vazar dado sensível em progresso/logs.

## Critérios de aceite

- Uma execução ativa por canal/tópico continua garantida.
- `/cancel` encerra execução e atualiza estado.
- Timeout registra status útil e não deixa subprocess órfão.
- Parser isolado produz os mesmos milestones/status para streams conhecidos.
- Logs/progress seguem redigidos.

## Agente sugerido pra implementação

**Time:** @compass → @bolt → @grid → @trail → @oath

| Fase | Agente | Papel |
|---|---|---|
| 1. Plano curto | @compass | Quebrar runner/progress em etapas |
| 2. Build | @bolt | Extrair runner e parser |
| 3. Testes | @grid | Criar testes de stream/lifecycle |
| 4. Causal | @trail-tracer | Investigar se houver intermitência |
| 5. Verify | @oath | Confirmar evidências de não regressão |

**Por quê esse time:** async/concurrency é área de risco; Trail entra só se houver sintoma intermitente.

## Status

- [x] Pendente
- [ ] Em progresso
- [ ] Concluído
