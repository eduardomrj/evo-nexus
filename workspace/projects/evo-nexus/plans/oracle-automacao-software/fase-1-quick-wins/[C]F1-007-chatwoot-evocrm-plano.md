---
author: claude
agent: oracle
type: work-plan-item
date: 2026-04-17
phase: 1
item-id: F1-007
status: pending
---

# F1-007. Migração Chatwoot → Evo CRM — Planejamento

**Fase:** 1 — Quick Wins
**Eixo:** Suporte / Comercial
**Tipo:** [DECIDIR]
**Prazo sugerido:** Sem 3-4

## O que é

Mapear todos os dados do Chatwoot atual (contatos, conversas, histórico, tags) e produzir o plano de migração para o Evo CRM. A transição do Evolution API para o Evolution Go acontece na mesma janela. Este item é apenas o plano — a execução é o F2-006.

## O que fazer

- Levantar schema do Chatwoot: contatos, conversas, tags, atribuições, inboxes
- Mapear para o modelo do Evo CRM via `int-evo-crm`: contatos → contatos, inboxes → inboxes, pipelines, labels
- Identificar dados que não migram diretamente (gaps) e definir como lidar
- Produzir plano de migração com: script estimado, janela de execução, rollback plan, e critérios de sucesso
- Documentar em `workspace/development/features/chatwoot-to-evocrm/`

## Agente / Skill / Rotina

`@echo-analyst` (discovery dos schemas) + `@scout-explorer` (mapeamento técnico) + `int-evo-crm` + `@compass-planner` (produzir o plano)

## O que o usuário precisa decidir/fornecer

- Instância Evo CRM destino: URL e credenciais (já provisionada?)
- Quais dados são essenciais: contatos e histórico de conversas? Tags e atribuições? Arquivos?
- Prazo máximo de downtime aceitável durante a migração
- Período de operação paralela (Chatwoot + Evo CRM ao mesmo tempo)?

## Impacto esperado

Migração executada sem surpresas na Fase 2. Evo CRM ativo libera toda a automação downstream (Zara, Nex, pipeline comercial).

## Dependências

- Acesso ao Chatwoot atual (banco de dados ou API de exportação)
- Instância Evo CRM destino já provisionada (ou provisionamento como parte deste item)

## Riscos

- Dados do Chatwoot em formato não-padrão (conversas longas, mídia, webhooks customizados) — mitigação: discovery completo antes de estimar o script
- Evo CRM não provisionado ainda — bloqueante: precisa de URL e credenciais para mapear o modelo de dados

## Agente sugerido pra implementação

| Fase | Agente | Papel |
|---|---|---|
| 1. Discovery | @echo-analyst | Mapear schemas Chatwoot e Evo CRM |
| 2. Mapeamento | @scout-explorer | Buscar diferenças nos modelos |
| 3. Plano | @compass-planner | Produzir plano de migração com passos e rollback |

**Por quê:** item [DECIDIR] com discovery técnico — requer análise antes de qualquer execução.

## Status

- [x] Pendente
- [ ] Em progresso
- [ ] Concluído
