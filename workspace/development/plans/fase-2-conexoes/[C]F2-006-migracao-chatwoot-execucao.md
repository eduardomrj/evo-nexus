---
author: claude
agent: oracle
type: work-plan-item
date: 2026-04-17
phase: 2
item-id: F2-006
status: pending
---

# F2-006. Migração Chatwoot → Evo CRM + Evolution Go — Execução

**Fase:** 2 — Conexões
**Eixo:** Suporte
**Tipo:** [CONSTRUIR NOVO]
**Prazo sugerido:** Sem 5-6 (logo no início da Fase 2)

## O que é

Executar o plano de migração produzido em F1-007. Migrar contatos, histórico de conversas e pipelines do Chatwoot para o Evo CRM. Na mesma janela de manutenção, trocar o Evolution API pelo Evolution Go. Após este item, toda a comunicação com clientes passa a acontecer via Evo CRM.

## O que fazer

- Implementar script de migração com @bolt-executor baseado no plano de F1-007
- Rodar migração em ambiente de teste primeiro (cópia dos dados do Chatwoot)
- Verificar integridade com @oath-verifier: contagem de registros, campos mapeados, histórico de conversas preservado
- Executar migração em produção com rollback plan ativo (Chatwoot não desativado até validação)
- Configurar Evolution Go apontando para Evo CRM (substituindo Evolution API → Chatwoot)
- Validação manual por Eduardo e técnico antes de desativar o Chatwoot

## Agente / Skill / Rotina

`@bolt-executor` (script de migração) + `@oath-verifier` (verificação de integridade) + `@hawk-debugger` (bugs durante migração) + `int-evo-crm`

## O que o usuário precisa decidir/fornecer

- Data de cutover (quando executar a migração em produção)
- Período de operação paralela: por quanto tempo os dois sistemas ficam ativos?
- Validação manual: Eduardo e técnico precisam confirmar manualmente antes de desligar o Chatwoot
- Instância Evolution Go configurada e testada antes do cutover

## Impacto esperado

CRM unificado no Evo CRM. Stack de atendimento moderna: Evolution Go → Evo CRM. Zara e Nex passam a operar com dados reais de clientes. Chatwoot pode ser desativado.

## Dependências

- F1-007 (plano de migração concluído e aprovado)
- Instância Evo CRM provisionada
- Evolution Go configurado e testado com a instância WhatsApp

## Riscos

- **MÉDIO** — perda de dados históricos. Mitigação: backup completo do Chatwoot antes de qualquer migração
- Downtime de atendimento durante cutover — mitigação: migração fora do horário comercial (noite ou fim de semana)
- Evolution Go pode ter comportamentos diferentes do Evolution API — mitigação: testar integração com Evo CRM antes do cutover

## Agente sugerido pra implementação

| Fase | Agente | Papel |
|---|---|---|
| 1. Script | @bolt-executor | Implementar script de migração |
| 2. Teste | @oath-verifier | Verificar integridade em ambiente de teste |
| 3. Produção | @bolt-executor | Executar cutover em produção |
| 4. Debug | @hawk-debugger | Resolver problemas durante/após migração |

**Por quê:** item [CONSTRUIR NOVO] com risco em produção — verificação rigorosa antes do cutover.

## Status

- [x] Pendente
- [ ] Em progresso
- [ ] Concluído
