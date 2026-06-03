---
author: claude
agent: oracle
type: work-plan-item
date: 2026-05-08
phase: 1
item-id: F1-01
status: completed
---

# F1-01. Confirmar capacidades do OpenClaude CLI

**Fase:** Fase 1 — Discovery técnico e arquitetura mínima  
**Eixo:** engenharia-integracao-discord  
**Tipo:** [DECIDIR]  
**Prazo sugerido:** início do discovery

## O que é

Verificar exatamente o que o `openclaude` local suporta antes de construir a bridge. O foco é validar chamadas `-p`, formatos de saída, streaming, sessão/resume, stdout/stderr e comportamento em timeout.

## O que fazer

- Rodar `openclaude --version` e `openclaude --help` para capturar flags disponíveis.
- Testar prompt simples com `openclaude -p` e timeout controlado.
- Testar `--output-format stream-json`, se a flag existir, e registrar se é compatível com parsing incremental.
- Verificar suporte a sessão/resume ou alternativa para contexto por canal.
- Documentar limitações que impactam status fino de ferramenta.

## Agente / Skill / Rotina

Oracle conduz o discovery. Scout/Apex podem ser usados para mapear padrões no repo se necessário. Oath deve validar evidências antes de declarar compatibilidade.

## O que o usuário precisa decidir/fornecer

Nada além da aprovação para aceitar fallback sem streaming fino caso o OpenClaude não exponha eventos de ferramenta.

## Impacto esperado

Evita construir a bridge em cima de uma flag inexistente ou comportamento incompatível. Define se o MVP terá apenas status por ciclo de processo ou status fino por evento.

## Dependências

OpenClaude instalado e acessível no PATH.

## Riscos

- OpenClaude não expor eventos de ferramenta.
- Formato de saída não ser estável para parsing.
- Chamadas de teste consumirem tokens/créditos.

## Agente sugerido pra implementação

**Time:** @oracle → @scout → @oath

| Fase | Agente | Papel |
|---|---|---|
| 1. Discovery | @oracle | Conduzir testes mínimos e decisões com o usuário |
| 2. Busca | @scout | Localizar padrões e limitações documentadas, se necessário |
| 3. Verify | @oath | Confirmar evidências reais das flags e saídas |

**Por quê esse time:** item [DECIDIR] precisa de framing interativo e evidência objetiva antes da POC.

## Resultado reconciliado

Concluído. OpenClaude local não substitui diretamente o channel oficial via `--channels`; a decisão foi usar uma bridge própria chamando `openclaude -p` com saída `stream-json`, MCP vazio isolado e timeout controlado.

## Status

- [ ] Pendente
- [ ] Em progresso
- [x] Concluído
