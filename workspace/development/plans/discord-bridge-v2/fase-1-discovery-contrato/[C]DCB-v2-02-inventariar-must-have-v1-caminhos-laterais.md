---
author: claude
agent: oracle
type: work-plan-item
date: 2026-05-19
phase: 1
item-id: DCB-v2-02
status: pending
---

# DCB-v2-02. Inventariar must-have da v1 e caminhos laterais de outbound

**Fase:** Fase 1 — Discovery/Contrato oficial e inventário must-have
**Eixo:** discovery-confiabilidade-operacional
**Tipo:** [ATIVAR]
**Prazo sugerido:** início da fase 1

## O que é

Identificar quais capacidades da v1 precisam sobreviver e quais caminhos laterais podem vazar texto para Discord fora do controle central.

## O que fazer

- Mapear responsabilidades em `/home/evonexus/evo-projects/discord-openclaude-bridge/src/discord_openclaude_bridge.py`.
- Mapear `/home/evonexus/evo-projects/discord-openclaude-bridge/src/bridge_reply_mcp_server.py`.
- Mapear testes em `/home/evonexus/evo-projects/discord-openclaude-bridge/tests/test_discord_openclaude_bridge.py`.
- Separar bot Discord, subprocess OpenClaude, stdout/stream/result, chunking, sessão, metrics, policy, comandos e MCP reply.
- Listar todos os caminhos que podem produzir texto visível.
- Classificar cada feature como must-have v2, nice-to-have, remover ou fallback via v1.

## Agente / Skill / Rotina

`@scout-explorer` para inventário, `@echo-analyst` para gaps/requisitos ocultos, `@raven-critic` para procurar caminhos de vazamento ignorados.

## O que o usuário precisa decidir/fornecer

- Lista final de must-have para cutover.
- Quais features podem ficar fora da primeira v2.

## Impacto esperado

Evita migrar o monólito inteiro por inércia. Preserva só o que sustenta operação real.

## Dependências

Código v1 e histórico dos bugs de chunk-limit, duplicate notifications e slash defer.

## Riscos

- Subestimar features operacionais usadas em produção.
- Deixar caminho lateral fora do inventário.

## Agente sugerido pra implementação

**Time:** @echo-analyst → @scout-explorer → @raven-critic

| Fase | Agente | Papel |
|---|---|---|
| 1. Discovery | @echo-analyst | Organizar requisitos e gaps |
| 2. Evidência | @scout-explorer | Mapear arquivos e caminhos |
| 3. Crítica | @raven-critic | Procurar vazamentos esquecidos |

**Por quê esse time:** item [ATIVAR] de discovery técnico-operacional; precisa inventário e crítica.

## Status

- [x] Pendente
- [ ] Em progresso
- [ ] Concluído
