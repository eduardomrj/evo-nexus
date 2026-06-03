---
author: claude
agent: oracle
type: work-plan-item
date: 2026-05-08
phase: 1
item-id: F1-02
status: completed
---

# F1-02. Definir estratégia de bot/canal de teste

**Fase:** Fase 1 — Discovery técnico e arquitetura mínima  
**Eixo:** seguranca-operacao-discord  
**Tipo:** [DECIDIR]  
**Prazo sugerido:** antes da POC

## O que é

Decidir como a POC vai escutar o Discord sem competir com o channel oficial atual. A decisão principal é usar bot separado ou o mesmo bot, e qual canal ficará isolado para testes.

## O que fazer

- Confirmar se a POC usará bot Discord separado ou o mesmo bot atual.
- Definir canal de teste e IDs permitidos de usuário/canal.
- Definir política de rollback e de não interferência com `make discord-channel`.
- Definir onde tokens serão guardados: `.env`/Vaultwarden, nunca hardcoded.
- Registrar permissões mínimas: ler mensagens, enviar mensagens, adicionar reações.

## Agente / Skill / Rotina

Oracle conduz a decisão. `@custom-sysops` deve ser chamado se envolver serviço, systemd, portas, LXC, Proxmox ou alteração operacional persistente.

## O que o usuário precisa decidir/fornecer

- Bot separado ou mesmo bot.
- Canal de teste.
- IDs de usuário/canal permitidos.
- Forma de fornecer token com segurança.

## Impacto esperado

Reduz o risco de respostas duplicadas e permite testar a bridge sem afetar o Discord Channel atual.

## Dependências

Acesso ao Discord Developer Portal ou ao token já provisionado, além de canal/servidor de teste.

## Riscos

- Duplicidade de respostas se a POC escutar o mesmo canal principal.
- Token exposto por erro de configuração.
- Permissões insuficientes para reações/status.

## Agente sugerido pra implementação

**Time:** @oracle → @custom-sysops

| Fase | Agente | Papel |
|---|---|---|
| 1. Decisão | @oracle | Conduzir escolha com o usuário |
| 2. Operação | @custom-sysops | Validar impacto em serviço/infra quando necessário |

**Por quê esse time:** decisão operacional com risco de interferir no serviço atual precisa de coordenação e cuidado de infra.

## Resultado reconciliado

Concluído. A POC usa bot separado, canal de teste `1502371179858755584`, usuário permitido `783488179000442891`, e token guardado no Vaultwarden como `DISCORD_OPENCLAUDE_BRIDGE_TOKEN`. O fluxo oficial `make discord-channel` continua preservado até cutover explícito.

## Status

- [ ] Pendente
- [ ] Em progresso
- [x] Concluído
