---
author: claude
agent: oracle
type: work-plan-item
date: 2026-04-26
phase: 3
item-id: F3-02
status: pending
---

# F3-02. Notificação diária 19h via WhatsApp

**Fase:** IA + WhatsApp
**Eixo:** automação
**Tipo:** [CONSTRUIR NOVO]
**Prazo sugerido:** Sem 4 — Dias 2-3 da Fase 3

## O que é

Job diário que roda às 19h, calcula o resumo do mês até o dia e envia ao Elistênio via WhatsApp. Elistênio recebe o estado do consórcio no celular sem precisar abrir nenhum sistema — essencial para quem passa a maior parte do tempo em reuniões e viagens.

## O que fazer

- Criar `notifier/daily_summary.py` que calcula:
  - Total de atendimentos no mês até o dia corrente
  - % de atingimento da meta geral do contrato
  - Top 3 municípios abaixo do percentual esperado (alertas)
  - Top 3 especialidades com maior volume de faltas
- Template de mensagem em pt-BR, tom executivo:
  ```
  📊 CPSMQ — 26/abr
  Atendimentos: 4.231 (68% da meta de abril)
  ⚠️ Abaixo do esperado: Quixeramobim (54%), Banabuiú (61%)
  Maior falta: Cardiologia (12%)
  Ver painel: [link]
  ```
- Rotina em `config/routines.yaml`: `0 19 * * *` (America/Fortaleza)
- Envio via `whatsapp_client.py` (F3-01)
- Logging em `notificacoes_log`

## Agente / Skill / Rotina

`@bolt-executor` (implementação) + skill `create-routine` + `@custom-sysops` (agendamento)

## O que o usuário precisa decidir/fornecer

- **Fins de semana e feriados:** pular ou enviar mesmo assim?
- **Tom:** mais executivo (números secos, recomendado) ou mais conversacional?
- **Anexo XLS:** enviar o consolidado do dia junto da mensagem ou só link pro painel?

## Impacto esperado

Elistênio "recebe" o consórcio todo dia às 19h sem abrir nada. Transforma dado passivo em informação ativa — o gestor age antes que o problema apareça na reunião.

## Dependências

F2-02 (dados no banco), F3-01 (canal WhatsApp).

## Riscos

Mensagem virar ruído e ser silenciada. Mitigação: começar minimalista (5-6 linhas), ajustar tom e conteúdo com feedback do Elistênio na primeira semana.

## Agente sugerido pra implementação

**Agente:** @bolt-executor

**Por quê:** implementação direta sem ambiguidade — lê banco, formata texto, envia via cliente já pronto (F3-01).

## Status

- [x] Pendente
- [ ] Em progresso
- [ ] Concluído
