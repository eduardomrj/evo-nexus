---
author: claude
agent: oracle
type: work-plan-item
date: 2026-04-26
phase: 3
item-id: F3-01
status: pending
---

# F3-01. Integração Evolution API (WhatsApp)

**Fase:** IA + WhatsApp
**Eixo:** canais
**Tipo:** [ATIVAR]
**Prazo sugerido:** Sem 4 — Dia 1 da Fase 3

## O que é

Conectar o sistema ao número WhatsApp do CPSMQ via Evolution API — tecnologia já dominada pela Automação Software. Provisiona o canal de saída (notificações) e entrada (bot IA) que Elistênio usará em viagem.

## O que fazer

- Provisionar instância Evolution API dedicada: `cpsmq`
- Conectar número WhatsApp Business do consórcio (QR code)
- Configurar webhook → endpoint `POST /api/whatsapp/webhook` no backend
- Implementar `bot/whatsapp_client.py`: `send_message(to, text)`, `receive_event(payload)`
- Whitelist no MVP: apenas o número do Elistênio envia e recebe respostas do bot
- Logging de todas as mensagens em `notificacoes_log`
- Testar envio e recebimento antes de prosseguir para F3-02

## Agente / Skill / Rotina

`@custom-sysops` (instância Evolution API) + skill `int-evolution-api` + `@bolt-executor` (webhook handler)

## O que o usuário precisa decidir/fornecer

- **Número WhatsApp:** linha dedicada do CPSMQ (recomendado — separação institucional) ou pessoal do Elistênio?
- **Instância Evolution:** dedicada `cpsmq` ou compartilhada com outros projetos da Automação Software?
- **Whitelist:** só Elistênio no MVP, ou já abrir para mais números da equipe?

## Impacto esperado

Habilita o canal de comunicação bidirecional. Sem isso, F3-02 e F3-03 não têm onde funcionar.

## Dependências

F1-03 (backend com endpoint de webhook).

## Riscos

WhatsApp pode banir número se usado de forma agressiva (muitas mensagens, conteúdo não-transacional). Mitigação: rate limit, conteúdo só transacional, número Business verificado.

## Agente sugerido pra implementação

**Agente:** @custom-sysops + @bolt-executor

| Fase | Agente | Papel |
|---|---|---|
| 1. Infra | @custom-sysops | Instância Evolution API, conexão do número |
| 2. Build | @bolt-executor | Webhook handler, whatsapp_client.py, whitelist |

**Por quê:** item [ATIVAR] — Evolution API já é parte do stack da Automação Software, Sysops provisiona, Bolt integra ao backend.

## Status

- [x] Pendente
- [ ] Em progresso
- [ ] Concluído
