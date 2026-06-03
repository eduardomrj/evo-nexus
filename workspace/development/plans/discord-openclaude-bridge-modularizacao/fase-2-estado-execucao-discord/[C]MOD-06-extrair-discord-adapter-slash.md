---
author: claude
agent: oracle
type: work-plan-item
date: 2026-05-13
phase: 2
item-id: MOD-06
status: pending
---

# MOD-06. Extrair Discord adapter puro e slash registration

**Fase:** Extração de Estado, Execução e Interface Discord
**Eixo:** interface-discord-adaptacao-externa
**Tipo:** [CONSTRUIR NOVO]
**Prazo sugerido:** após MOD-05

## O que é

Separar helpers Discord e registro slash antes de mover comandos sensíveis. A meta é isolar adaptação externa sem mudar a slash tree pública.

## O que fazer

- Extrair helpers Discord de `src/discord_openclaude_bridge.py:1810`: chunking, send_response, fallback system message e reactions.
- Separar slash registration de `build_discord_client` em `:3136` sem mudar slash tree pública.
- Congelar contrato `defer/followup` em comandos lentos.
- Rodar import smoke e testes de adapter com fakes.

## Agente / Skill / Rotina

@bolt-executor + @grid-tester + @probe-qa + @lens-reviewer.

## O que o usuário precisa decidir/fornecer

Decidir se haverá smoke Discord manual após esta etapa ou apenas após MOD-08.

## Impacto esperado

Reduz acoplamento com Discord e prepara command handlers sem mexer nas regras de negócio.

## Dependências

MOD-00, MOD-01 e MOD-05.

## Riscos

Quebrar registro slash, fallback de resposta ou defer/followup de comandos lentos.

## Critérios de aceite

- Slash tree pública permanece igual.
- `/start` e `/reset-session` continuam deferindo/followup quando lentos.
- Chunking/fallback/reactions mantêm comportamento semântico.

## Agente sugerido pra implementação

**Time:** @compass → @bolt → @grid → @probe → @lens

| Fase | Agente | Papel |
|---|---|---|
| 1. Plano curto | @compass | Definir extração adapter/slash |
| 2. Build | @bolt | Implementar adapter |
| 3. Testes | @grid | Validar fakes e slash registration |
| 4. QA | @probe-qa | Smoke manual quando autorizado |
| 5. Review | @lens | Revisar regressões de UX |

**Por quê esse time:** adapter Discord toca integração externa; Probe só entra com autorização para validação manual.

## Status

- [x] Pendente
- [ ] Em progresso
- [ ] Concluído
