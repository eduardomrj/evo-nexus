---
author: claude
agent: oracle
type: work-plan-index
date: 2026-04-17
plan-name: oracle-automacao-software
status: draft
mode: index
---

# Plano de Ativação EvoNexus — Automação Software

**Tipo:** índice. Cada item tem arquivo próprio na pasta da respectiva fase. Este arquivo não duplica o detalhamento — aponta pros arquivos-filhos.

---

## Contexto

A Automação Software é uma empresa de software para varejo (B2B) e saúde pública (B2G) com 25 anos de mercado, atualmente pivotando de desktop (Emporion Delphi) para micro-SaaS (Plataforma GO). Time de 2 pessoas: Eduardo (dono, dev principal) e 1 técnico de suporte. O plano cobre 3 eixos simultâneos: automação operacional, aceleração de desenvolvimento e construção de produtos novos.

## Objetivos

- Reduzir em 60-70% o tempo gasto com suporte repetitivo via automação (Zara + WhatsApp)
- Construir funil de marketing e captação de leads do zero (Mako + Pixel)
- Acelerar o desenvolvimento da Plataforma GO e do SERKET com Engineering Layer
- Automatizar ciclo comercial (proposta → contrato → assinatura → ativação)
- Eliminar operações manuais de cobrança e gestão de licenças

## Guardrails

**Must Have**
- Cada item ativado deve ser testado antes de ir para produção
- Decisões arquiteturais (stack GO, integração SUS) devem ter ADR documentado antes de qualquer código
- Aprovação humana obrigatória para bloqueio de licença por inadimplência (primeiros 30 dias)
- SERKET e Plataforma GO evoluem em paralelo — nenhum bloqueia o outro

**Must NOT Have**
- Não iniciar construção da Plataforma GO sem a decisão de stack (F2-004) resolvida
- Não migrar Chatwoot → Evo CRM sem plano de rollback documentado
- Não automatizar bloqueio de licença antes da nova API de licenças (F2-005) estar estável

---

## Visão geral das fases

```
Fase 1 — Quick Wins (Sem 1-4)     →    Fase 2 — Conexões (Sem 5-10)     →    Fase 3 — Ciclo Completo (Sem 11-24)
Ativar agentes existentes,              Pipelines entre eixos,                  Construção dos módulos GO,
visibilidade imediata                   decisões arquiteturais,                  SERKET avançado,
                                        migração CRM                            loops end-to-end
```

---

## Fase 1 — Quick Wins (Semanas 1-4)

Pasta: [`fase-1-quick-wins/`](fase-1-quick-wins/)

| # | Item | Tipo | Eixo |
|---|---|---|---|
| F1-001 | [Zara — Triagem Automática de Suporte via WhatsApp](fase-1-quick-wins/[C]F1-001-zara-triagem-whatsapp.md) | [ATIVAR] | Suporte |
| F1-002 | [Flux + Asaas — Visibilidade Financeira](fase-1-quick-wins/[C]F1-002-flux-asaas-financeiro.md) | [ATIVAR] | Financeiro |
| F1-003 | [Sistema de Tickets Nativo — Inbox Centralizado](fase-1-quick-wins/[C]F1-003-tickets-inbox.md) | [ATIVAR] | Organização |
| F1-004 | [Goals — Missão e Projetos Estruturados](fase-1-quick-wins/[C]F1-004-goals-missao-projetos.md) | [ATIVAR] | Organização |
| F1-005 | [Rotinas Diárias — Good Morning + EOD](fase-1-quick-wins/[C]F1-005-rotinas-diarias.md) | [ATIVAR] | Organização |
| F1-006 | [Atlas — Monitoramento GitHub Automático](fase-1-quick-wins/[C]F1-006-atlas-github.md) | [ATIVAR] | Engineering |
| F1-007 | [Migração Chatwoot → Evo CRM — Planejamento](fase-1-quick-wins/[C]F1-007-chatwoot-evocrm-plano.md) | [DECIDIR] | Suporte/Comercial |

---

## Fase 2 — Conexões (Semanas 5-10)

Pasta: [`fase-2-conexoes/`](fase-2-conexoes/)

| # | Item | Tipo | Eixo |
|---|---|---|---|
| F2-001 | [DocuSign Self-Hosted — Implantação no Proxmox](fase-2-conexoes/[C]F2-001-docusign-proxmox.md) | [DECIDIR] | Comercial |
| F2-002 | [Pipeline Comercial — Nex + Lex + Assinatura](fase-2-conexoes/[C]F2-002-pipeline-comercial.md) | [CONSTRUIR NOVO] | Comercial |
| F2-003 | [Marketing e Captação de Leads — Mako + Pixel](fase-2-conexoes/[C]F2-003-marketing-leads.md) | [CONSTRUIR NOVO] | Marketing |
| F2-004 | [Stack da Plataforma GO — Madbuilder vs Laravel/Filament](fase-2-conexoes/[C]F2-004-stack-plataforma-go.md) | [DECIDIR] | Engineering |
| F2-005 | [API de Licenças do Emporion — Rebuild do Zero](fase-2-conexoes/[C]F2-005-api-licencas-rebuild.md) | [CONSTRUIR NOVO] | Engineering |
| F2-006 | [Migração Chatwoot → Evo CRM + Evolution Go — Execução](fase-2-conexoes/[C]F2-006-migracao-chatwoot-execucao.md) | [CONSTRUIR NOVO] | Suporte |
| F2-007 | [SERKET — Discovery Hub InovaAF (RNDS, BNAFAR, CADSUS)](fase-2-conexoes/[C]F2-007-serket-inovaaf-discovery.md) | [DECIDIR] | Produto/Engineering |
| F2-008 | [Workflow de Engenharia — Feature Folders + 6 Fases](fase-2-conexoes/[C]F2-008-workflow-engenharia.md) | [ATIVAR] | Engineering |
| F2-009 | [Cobranças Semi-Automáticas — Escalonamento + Bloqueio](fase-2-conexoes/[C]F2-009-cobrancas-escalonamento.md) | [EVOLUIR] | Financeiro |

---

## Fase 3 — Ciclo Completo (Semanas 11-24)

Pasta: [`fase-3-ciclo-completo/`](fase-3-ciclo-completo/)

| # | Item | Tipo | Eixo |
|---|---|---|---|
| F3-001 | [GO Platform — Primeiro Módulo (Contas a Pagar/Receber)](fase-3-ciclo-completo/[C]F3-001-go-contas-pagar-receber.md) | [CONSTRUIR NOVO] | Produto/Engineering |
| F3-002 | [GO Platform — PDV Web](fase-3-ciclo-completo/[C]F3-002-go-pdv-web.md) | [CONSTRUIR NOVO] | Produto/Engineering |
| F3-003 | [PDV Integrado ao WhatsApp — Discovery + Protótipo](fase-3-ciclo-completo/[C]F3-003-pdv-whatsapp.md) | [CONSTRUIR NOVO] | Produto/Engineering |
| F3-004 | [SERKET — Implementação Hub InovaAF](fase-3-ciclo-completo/[C]F3-004-serket-inovaaf-implementacao.md) | [CONSTRUIR NOVO] | Produto/Engineering |
| F3-005 | [Loop End-to-End: Lead → Cliente → Suporte → Cobrança](fase-3-ciclo-completo/[C]F3-005-loop-end-to-end.md) | [EVOLUIR] | Comercial/Suporte/Financeiro |
| F3-006 | [Sistema Próprio de Cobranças — Discovery](fase-3-ciclo-completo/[C]F3-006-cobrancas-proprias-discovery.md) | [DECIDIR] | Financeiro/Produto |

---

## Decisões críticas pendentes

1. **Instância Evo CRM** (F1-007) — URL e credenciais — desbloqueia toda a automação de CRM
2. **Stack da Plataforma GO** (F2-004) — Madbuilder/Adianti vs Laravel/Filament — **bloqueante para toda a Fase 3**
3. **DocuSign vs alternativa self-hosted** (F2-001) — implantação no Proxmox — desbloqueia pipeline comercial
4. **Certificado ICP-Brasil** (F2-007 / F3-004) — processo administrativo DATASUS precisa iniciar AGORA
5. **Primeiro módulo da GO Platform** (F3-001) — Contas a Pagar/Receber confirmado? ou outro?
6. **Política de bloqueio de licença** (F2-009) — automático ou com aprovação humana?

---

## Histórico de mudanças

- **v1 (2026-04-17):** versão inicial — onboarding completo realizado por Oracle. 22 itens em 3 fases.
