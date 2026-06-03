---
author: claude
agent: oracle
type: work-plan-item
date: 2026-04-17
phase: 3
item-id: F3-005
status: pending
---

# F3-005. Loop End-to-End: Lead → Cliente → Suporte → Cobrança

**Fase:** 3 — Ciclo Completo
**Eixo:** Comercial / Suporte / Financeiro
**Tipo:** [EVOLUIR]
**Prazo sugerido:** Sem 21-24

## O que é

Conectar todos os eixos da operação em um loop automatizado: lead captado pelo marketing → qualificado pelo Nex → contrato via Lex → assinatura digital → ativação de licença → suporte por Zara → cobrança por Flux. A "operação autônoma" que libera Eduardo para focar em desenvolvimento de produto.

## O que fazer

- Mapear o fluxo completo com triggers entre cada etapa (onde começa, onde termina, o que aciona o próximo passo)
- Implementar webhooks e triggers: contrato assinado → ticket de ativação → Zara onboarding → Flux inicia cobrança
- Testar fluxo completo com cliente fictício: desde o lead até a primeira cobrança automática
- Criar dashboard de funil com `data-build-dashboard`: conversão por etapa, tempo por etapa, gargalos
- Retrospectiva com @mirror-retro: o que funciona, o que precisa de humano, o que otimizar

## Agente / Skill / Rotina

`@nex-sales` + `@lex-legal` + `@zara-cs` + `@flux-finance` + `@mako-marketing` + `@helm-conductor` (orquestração) + `data-build-dashboard` + `@mirror-retro`

## O que o usuário precisa decidir/fornecer

- Quais etapas podem ser 100% automáticas vs quais precisam de aprovação humana obrigatória
- SLA de cada etapa: proposta em X horas, contrato em Y horas, ativação em Z horas
- Aceita cliente entrar em produção sem onboarding humano? Ou sempre quer 1 contato manual?
- Integração entre Evo CRM (dados) e o sistema de licenças do Emporion/GO

## Impacto esperado

Eduardo e técnico focam em desenvolvimento de produto e suporte P1 apenas. Toda a operação comercial e financeira roda no automático com pontos de aprovação estratégicos.

## Dependências

- F2-002 (pipeline comercial ativo)
- F2-006 (Evo CRM com dados reais de clientes)
- F2-009 (cobranças automáticas funcionando)
- F1-001 (Zara ativa em produção)
- F2-005 (nova API de licenças estável)

## Riscos

- **MÉDIO** — excesso de automação gera experiência impessoal. Mitigação: pontos de contato humano obrigatórios (onboarding, renovação anual)
- Falha em cascata: se um agente falha, o pipeline para. Mitigação: circuit breakers + alerta imediato via Telegram

## Agente sugerido pra implementação

| Fase | Agente | Papel |
|---|---|---|
| 1. Mapeamento | @helm-conductor | Mapear triggers entre eixos |
| 2. Build | @bolt-executor | Implementar webhooks e triggers |
| 3. Dashboard | @dex-data | Dashboard de funil |
| 4. Teste | @probe-qa | Testar com cliente fictício |
| 5. Retro | @mirror-retro | Capturar aprendizados e otimizações |

**Por quê:** item [EVOLUIR] que conecta todos os outros — Helm orquestra, cada agente dono executa sua parte.

## Status

- [x] Pendente
- [ ] Em progresso
- [ ] Concluído
