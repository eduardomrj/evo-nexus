---
author: claude
agent: oracle
type: work-plan-item
date: 2026-05-19
phase: 4
item-id: DCB-v2-08
status: pending
---

# DCB-v2-08. Preparar shadow rollout com v1 como fallback/checkpoint

**Fase:** Fase 4 — Prova operacional e shadow rollout
**Eixo:** operacao-rollout
**Tipo:** [EVOLUIR]
**Prazo sugerido:** após spike aprovado

## O que é

Rodar a v2 em paralelo controlado, sem assumir produção integral, comparando comportamento com a v1 e mantendo rollback simples.

## O que fazer

- Definir modo shadow: v2 recebe eventos selecionados, registra decisão/resposta e só envia quando explicitamente habilitado.
- Definir canal/categoria de teste e allowlist de usuários.
- Definir flags: `bridge_v2_enabled`, `bridge_v2_shadow_only`, `bridge_v1_fallback_enabled`, `gateway_strict_mode`.
- Definir dashboard/log operacional mínimo: mensagens recebidas, respostas entregues, chunks, falhas, dedupes, cancelamentos e policy denied.
- Rodar casos reais de baixa criticidade.
- Comparar incidentes contra v1.

## Agente / Skill / Rotina

`@bolt-executor`, `@probe-qa`, `@oath-verifier`, `@custom-sysops`, `@vault-security`.

## O que o usuário precisa decidir/fornecer

- Canal de shadow.
- Usuários permitidos.
- Data/janela de teste.
- Se v2 pode responder publicamente em shadow parcial ou só logar.

## Impacto esperado

Reduz risco de cutover e valida operação real sem desligar a v1.

## Dependências

Spike aprovado, feature flags/config equivalente e ambiente operacional seguro.

## Riscos

- Shadow duplicar respostas por erro de configuração.
- v1 e v2 competirem pelo mesmo evento.
- Logs insuficientes para comparar.

## Agente sugerido pra implementação

**Time:** @compass-planner → @bolt-executor → @custom-sysops → @probe-qa → @vault-security → @oath-verifier

| Fase | Agente | Papel |
|---|---|---|
| 1. Plano | @compass-planner | Sequenciar rollout |
| 2. Build | @bolt-executor | Flags/config/runtime |
| 3. Infra | @custom-sysops | Serviço, portas, systemd |
| 4. QA | @probe-qa | Testes interativos |
| 5. Segurança | @vault-security | Segredos e allowlist |
| 6. Verify | @oath-verifier | Evidência operacional |

**Por quê esse time:** rollout envolve código, infra, segurança e QA real.

## Status

- [x] Pendente
- [ ] Em progresso
- [ ] Concluído
