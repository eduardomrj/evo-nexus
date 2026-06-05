---
author: claude
agent: oracle
type: work-plan-item
date: 2026-04-17
phase: 2
item-id: F2-009
status: pending
---

# F2-009. Cobranças Semi-Automáticas — Escalonamento + Bloqueio

**Fase:** 2 — Conexões
**Eixo:** Financeiro
**Tipo:** [EVOLUIR]
**Prazo sugerido:** Sem 9-10

## O que é

Evoluir o monitoramento do F1-002 para ação concreta: envio automático de 2a via, escalonamento de notificações de inadimplência, e bloqueio de licença vinculado ao status de pagamento no Asaas. Depende da nova API de licenças (F2-005) para o bloqueio funcionar de forma confiável.

## O que fazer

- Criar workflow de cobrança escalonada: D+5 (lembrete), D+15 (2a via automática), D+30 (notificação de bloqueio iminente), D+45 (bloqueio — com aprovação humana no início)
- Implementar envio de 2a via via `int-asaas` (gerar novo boleto ou Pix)
- Integrar com nova API de licenças (F2-005) para bloqueio/desbloqueio
- Configurar aprovação humana obrigatória para bloqueio via Telegram — Eduardo aprova antes de bloquear
- Após 30 dias sem erros: avaliar automatizar o bloqueio completamente

## Agente / Skill / Rotina

`@flux-finance` + `int-asaas` + `int-telegram` (aprovação de bloqueio) + nova API de licenças (F2-005)

## O que o usuário precisa decidir/fornecer

- Política de cobrança escalonada: confirmar os dias (D+5, D+15, D+30, D+45) ou ajustar
- Bloqueio automático ou sempre com aprovação humana? (recomendado: aprovação humana por 30 dias)
- Exceções: clientes VIP, órgãos públicos (SERKET) têm regras diferentes de prazo?
- Canal de aprovação de bloqueio: Telegram ou dashboard?

## Impacto esperado

Inadimplência reduzida. Zero trabalho manual de 2a via de boleto ou Pix. Bloqueio de licença consistente e auditável. Eduardo só entra quando há exceções.

## Dependências

- F1-002 (Flux + Asaas ativo)
- F2-005 (nova API de licenças estável e em produção)

## Riscos

- **MÉDIO** — bloqueio indevido de cliente adimplente por erro de integração. Mitigação: aprovação humana obrigatória por 30 dias antes de automatizar completamente.
- API de licenças instável (especialmente no período pós-migração) — mitigação: retry com backoff + alerta imediato de falha

## Agente sugerido pra implementação

| Fase | Agente | Papel |
|---|---|---|
| 1. Spec | @compass-planner | Plano do workflow de escalonamento |
| 2. Build | @flux-finance + @bolt-executor | Implementar regras no heartbeat + integração |
| 3. Verify | @oath-verifier | Testar fluxo D+5 → D+45 completo |

**Por quê:** item [EVOLUIR] com baseline existente — Flux já monitora, agora precisa agir.

## Status

- [x] Pendente
- [ ] Em progresso
- [ ] Concluído
