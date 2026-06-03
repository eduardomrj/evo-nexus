---
author: claude
agent: oracle
type: work-plan-item
date: 2026-05-19
phase: 3
item-id: DCB-v2-06
status: pending
---

# DCB-v2-06. Criar spike mínimo channel-compatible com gateway único

**Fase:** Fase 3 — Spike isolado channel-compatible
**Eixo:** spike-prova-tecnica
**Tipo:** [CONSTRUIR NOVO]
**Prazo sugerido:** 1 dia útil

## O que é

Construir uma prova isolada, timeboxed em 1 dia útil, com inbound Discord → OpenClaude → `OutboundGateway.reply()` → Discord, sem carregar todo o legado da v1.

## O que fazer

- Criar spike isolado dentro do repo custom, sem substituir produção.
- Implementar fluxo mínimo: receber mensagem, resolver policy mínima, iniciar sessão, chamar OpenClaude, capturar eventos/resultados e responder exclusivamente via gateway.
- Bloquear ou omitir features não essenciais.
- Instrumentar logs de auditoria.
- Rodar os testes obrigatórios do Gate G3 em ambiente controlado.
- Registrar resultado: PASS, FAIL recuperável ou FAIL arquitetural.

## Agente / Skill / Rotina

`@bolt-executor` para implementação do spike, `@grid-tester` para testes, `@hawk-debugger` se falhar, `@oath-verifier` para evidência e `@apex-architect` para decisão pós-spike.

## O que o usuário precisa decidir/fornecer

- Aprovar janela de 1 dia útil.
- Definir canal/servidor Discord de teste.
- Definir se o spike pode usar credenciais reais ou sandbox.

## Impacto esperado

Valida a arquitetura antes de migração e evita mais semanas remendando a v1.

## Dependências

Fase 2 aprovada, ambiente Discord de teste e tokens/credenciais disponíveis sem expor segredos.

## Riscos

- Spike tentar migrar features demais.
- Falha de ambiente/credencial ser confundida com falha arquitetural.
- Caminho lateral passar despercebido se os testes forem fracos.

## Agente sugerido pra implementação

**Time:** @compass-planner → @apex-architect → @bolt-executor → @grid-tester → @hawk-debugger → @oath-verifier

| Fase | Agente | Papel |
|---|---|---|
| 1. Plano | @compass-planner | Escopo 1 dia e passos |
| 2. Arquitetura | @apex-architect | Validar fronteiras do spike |
| 3. Build | @bolt-executor | Implementação mínima |
| 4. Testes | @grid-tester | Testes obrigatórios |
| 5. Debug | @hawk-debugger | Falhas de execução |
| 6. Verify | @oath-verifier | Evidência final |

**Por quê esse time:** construção crítica e timeboxed; precisa build mínimo, testes fortes e evidência.

## Status

- [x] Pendente
- [ ] Em progresso
- [ ] Concluído
