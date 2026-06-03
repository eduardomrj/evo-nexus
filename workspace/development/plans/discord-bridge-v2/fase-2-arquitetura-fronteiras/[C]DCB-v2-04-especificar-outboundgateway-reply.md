---
author: claude
agent: oracle
type: work-plan-item
date: 2026-05-19
phase: 2
item-id: DCB-v2-04
status: pending
---

# DCB-v2-04. Especificar OutboundGateway.reply() como única saída visível

**Fase:** Fase 2 — Arquitetura v2 e interfaces de fronteira
**Eixo:** messaging-confiabilidade-auditoria
**Tipo:** [CONSTRUIR NOVO]
**Prazo sugerido:** antes do spike

## O que é

Definir o contrato do gateway único de outbound que centraliza chunking, confirmação de entrega, deduplicação, auditoria e falhas.

## O que fazer

- Definir assinatura conceitual de `reply()` com contexto, conteúdo, tipo de resposta, correlation id, policy context e metadata de agente/skill/MCP.
- Definir estados: `created`, `chunked`, `send_attempted`, `delivered`, `failed`, `deduped`, `cancelled`.
- Definir idempotência por sessão + request id + sequence.
- Definir chunking seguro para Discord com ordem preservada e fail-fast.
- Definir confirmação real apenas após retorno bem-sucedido da API Discord.
- Definir auditoria segura e teste que bloqueia envio direto pelo Discord client fora do gateway.

## Agente / Skill / Rotina

`@apex-architect`, `@grid-tester`, `@vault-security`, `dev-verify`.

## O que o usuário precisa decidir/fornecer

- Se auditoria guarda conteúdo completo, hash, preview ou conteúdo redigido.
- Tolerância para mensagem parcial: permitir parcial com aviso ou rollback lógico.

## Impacto esperado

Ataca diretamente a causa-raiz dos vazamentos e cria rastreabilidade real entre “foi produzido?” e “foi entregue?”.

## Dependências

Contrato oficial Channel e inventário dos caminhos laterais da v1.

## Riscos

- Auditoria guardar conteúdo sensível demais.
- Deduplicação agressiva bloquear resposta legítima.
- Confirmação da API Discord ser interpretada incorretamente.

## Agente sugerido pra implementação

**Time:** @oracle → @compass-planner → @apex-architect → @vault-security → @grid-tester → @bolt-executor → @oath-verifier

| Fase | Agente | Papel |
|---|---|---|
| 1. Framing | @oracle | Decisões de auditoria e risco |
| 2. Plano | @compass-planner | Quebrar em 3-6 passos executáveis |
| 3. Arquitetura | @apex-architect | Contrato do gateway |
| 4. Segurança | @vault-security | Auditoria e redaction |
| 5. Testes | @grid-tester | Testes de bloqueio e chunking |
| 6. Build | @bolt-executor | Implementação futura |
| 7. Verify | @oath-verifier | Evidência de entrega |

**Por quê esse time:** item crítico de construção com impacto de segurança e confiabilidade.

## Status

- [x] Pendente
- [ ] Em progresso
- [ ] Concluído
