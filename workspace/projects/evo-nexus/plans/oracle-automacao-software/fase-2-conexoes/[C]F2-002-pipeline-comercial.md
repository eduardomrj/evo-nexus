---
author: claude
agent: oracle
type: work-plan-item
date: 2026-04-17
phase: 2
item-id: F2-002
status: pending
---

# F2-002. Pipeline Comercial — Nex + Lex + Assinatura

**Fase:** 2 — Conexões
**Eixo:** Comercial
**Tipo:** [CONSTRUIR NOVO]
**Prazo sugerido:** Sem 7-9

## O que é

Construir o ciclo comercial completo: lead → qualificação → proposta → contrato → assinatura digital → ativação de licença. Nex gerencia o pipeline, Lex revisa e gera contratos, a plataforma de assinatura (F2-001) fecha o ciclo. Elimina toda a operação manual de contratos no Google Docs.

## O que fazer

- Configurar Nex com pipeline Evo CRM: etapas Lead → Qualificação → Proposta Enviada → Negociação → Fechamento → Ativação
- Criar templates de proposta comercial para Emporion e SERKET com @lex-legal (preços, condições, SLA)
- Integrar plataforma de assinatura digital (resultado de F2-001) via skill `legal-signature-request`
- Criar ticket automático de ativação de licença quando contrato for assinado
- Habilitar heartbeat de Nex para alerta de cold leads > 7 dias sem resposta

## Agente / Skill / Rotina

`@nex-sales` (pipeline) + `@lex-legal` + skills `legal-review-contract`, `legal-signature-request` + `int-evo-crm` + heartbeat para cold leads

## O que o usuário precisa decidir/fornecer

- Etapas do pipeline comercial (confirmar ou ajustar as sugeridas)
- Templates de proposta: tabela de preços, condições de pagamento, SLA de suporte, cláusulas padrão
- Conta na plataforma de assinatura (resultado de F2-001)
- Critérios de qualificação de leads (o que é um lead quente para a Automação Software?)

## Impacto esperado

Ciclo proposta → assinatura → ativação de dias para horas. Contratos assinados digitalmente com auditoria. Zero Google Docs manual. Nex monitora pipeline proativamente.

## Dependências

- F2-001 (plataforma de assinatura implantada)
- F2-006 (Evo CRM ativo com contatos migrados do Chatwoot)

## Riscos

- Templates de contrato precisam revisão antes do go-live — mitigação: Lex gera draft, Eduardo (e advogado se necessário) revisa
- Integração com assinatura pode ter delay de webhook — mitigação: polling de backup além de webhook

## Agente sugerido pra implementação

| Fase | Agente | Papel |
|---|---|---|
| 1. Spec | @compass-planner | Plano de 5-6 passos |
| 2. Pipeline | @nex-sales | Configurar etapas no Evo CRM |
| 3. Contratos | @lex-legal | Templates de proposta e contrato |
| 4. Integração | @bolt-executor | Webhook assinatura → ticket ativação |
| 5. Verify | @oath-verifier | Testar fluxo end-to-end |

**Por quê:** item [CONSTRUIR NOVO] de médio porte com múltiplos agentes especializados.

## Status

- [x] Pendente
- [ ] Em progresso
- [ ] Concluído
