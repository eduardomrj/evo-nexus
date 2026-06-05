---
author: claude
agent: oracle
type: work-plan-item
date: 2026-04-17
phase: 2
item-id: F2-005
status: pending
---

# F2-005. API de Licenças do Emporion — Rebuild do Zero

**Fase:** 2 — Conexões
**Eixo:** Engineering
**Tipo:** [CONSTRUIR NOVO]
**Prazo sugerido:** Sem 6-10

## O que é

A API de licenças do Emporion existe mas está cheia de bugs. Rebuild completo com arquitetura limpa, integrada ao Asaas para ativação/bloqueio automático por status de pagamento. Esta nova API é pré-requisito para automatizar cobranças e licenças (F2-009).

## O que fazer

- Discovery com @echo-analyst: requisitos funcionais da nova API (ativar, bloquear, renovar, auditar, multi-produto, multi-cliente)
- Arquitetura com @apex-architect: modelo de dados limpo, autenticação segura, integração Asaas, versionamento de API
- Build com @bolt-executor: implementação incremental (CRUD → integração Asaas → auditoria)
- Testes com @grid-tester: cobertura de casos de borda (expiração, renovação, conflito de licença)
- Verify com @oath-verifier + @lens-reviewer: validação contra requisitos
- Plano de migração: período de convivência antiga API (buggy) → nova API

## Agente / Skill / Rotina

`@echo-analyst` + `@apex-architect` + `@bolt-executor` + `@grid-tester` + `@oath-verifier` + `@lens-reviewer` + `@vault-security` (autenticação de licenças é sensível) + `int-asaas`

## O que o usuário precisa decidir/fornecer

- Requisitos funcionais: quais operações a nova API precisa suportar além de ativar/bloquear?
- Como funciona hoje: qual o endpoint atual (buggy) e quais são os principais bugs?
- Integração: a nova API precisa falar com o sistema Emporion Desktop (Delphi)? Como?
- Período de convivência: por quanto tempo as duas APIs precisam funcionar em paralelo?
- Autenticação: token por cliente, certificado, ou outro mecanismo?

## Impacto esperado

Desbloqueio do bloqueio/desbloqueio automático por inadimplência (F2-009). Licenças controladas sem trabalho manual. Fundação para o módulo de Licenças da Plataforma GO.

## Dependências

- F1-002 (Flux + Asaas ativo — para integração de status de pagamento)
- Acesso à API atual (para entender o modelo existente e os bugs)

## Riscos

- **MÉDIO** — migração de API em produção com clientes ativos. Período de convivência obrigatório.
- API Delphi ↔ API nova pode ter incompatibilidades — mitigação: discovery completo do sistema Emporion Desktop antes de projetar a nova API

## Agente sugerido pra implementação

| Fase | Agente | Papel |
|---|---|---|
| 1. Discovery | @echo-analyst | Requisitos + análise da API atual |
| 2. Arquitetura | @apex-architect | ADR + modelo de dados + integração Asaas |
| 3. Build | @bolt-executor | Implementação incremental |
| 4. Testes | @grid-tester | TDD para regras de licença |
| 5. Segurança | @vault-security | Auditoria de autenticação |
| 6. Verify | @oath-verifier | Validação contra requisitos |

**Por quê:** item [CONSTRUIR NOVO] crítico com impacto em produção — pipeline completo de 6 fases obrigatório.

## Status

- [x] Pendente
- [ ] Em progresso
- [ ] Concluído
