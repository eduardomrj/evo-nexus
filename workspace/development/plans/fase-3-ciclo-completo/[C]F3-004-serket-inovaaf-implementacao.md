---
author: claude
agent: oracle
type: work-plan-item
date: 2026-04-17
phase: 3
item-id: F3-004
status: pending
---

# F3-004. SERKET — Implementação Hub InovaAF

**Fase:** 3 — Ciclo Completo
**Eixo:** Produto / Engineering
**Tipo:** [CONSTRUIR NOVO]
**Prazo sugerido:** Sem 13-22 (em paralelo com GO Platform)

## O que é

Implementar a integração do SERKET com o Hub InovaAF do SUS baseada no discovery de F2-007. Prioridade sugerida: CADSUS (cadastro de pacientes) → BNAFAR (dispensação) → RNDS (notificações clínicas). Dados de saúde pública exigem auditoria de segurança reforçada.

## O que fazer

- Plano de implementação com @compass-planner baseado no discovery de F2-007
- Arquitetura com @apex-architect: camada de integração FHIR R4, autenticação com certificado ICP-Brasil, retry e resiliência
- Build por prioridade com @bolt-executor: CADSUS → BNAFAR → RNDS
- Testes com @grid-tester: mocks do ambiente de homologação DATASUS (APIs instáveis)
- Auditoria de segurança obrigatória com @vault-security: dados sensíveis de saúde (LGPD + normas SUS)
- Verificação com @oath-verifier contra requisitos regulatórios
- Homologação no ambiente DATASUS

## Agente / Skill / Rotina

`@compass-planner` + `@apex-architect` + `@bolt-executor` + `@grid-tester` + `@vault-security` + `@oath-verifier`

## O que o usuário precisa decidir/fornecer

- Ordem de integração: confirmar CADSUS → BNAFAR → RNDS ou outra?
- Município de piloto para homologação (o atual já em uso)
- Certificado digital ICP-Brasil: município já possui? Precisa adquirir? Custo estimado?
- Credenciamento DATASUS: processo administrativo iniciado? (precisa iniciar em F2-007)

## Impacto esperado

SERKET em conformidade com exigências federais do SUS. Diferencial competitivo para vender o produto a outros municípios. Potencial de expansão nacional via Hub InovaAF.

## Dependências

- F2-007 (discovery concluído com requisitos claros)
- Certificado digital ICP-Brasil emitido
- Credenciamento no DATASUS aprovado
- Ambiente de homologação do SUS acessível

## Riscos

- **ALTO** — ambiente de homologação do SUS tem histórico de indisponibilidade. Mocks robustos obrigatórios para não travar o desenvolvimento
- **ALTO** — mudanças regulatórias durante a implementação. Monitorar portarias do Ministério da Saúde
- **ALTO** — processo de credenciamento DATASUS pode atrasar toda a fase. Se não foi iniciado em F2-007, este item não pode ser concluído

## Agente sugerido pra implementação

| Fase | Agente | Papel |
|---|---|---|
| 1. Plano | @compass-planner | Plano detalhado por integração |
| 2. Arquitetura | @apex-architect | ADR FHIR R4 + ICP-Brasil |
| 3. Build | @bolt-executor | Implementação por prioridade |
| 4. Testes | @grid-tester | Mocks + testes de resiliência |
| 5. Segurança | @vault-security | Auditoria LGPD + normas SUS |
| 6. Verify | @oath-verifier | Validação regulatória |

**Por quê:** item [CONSTRUIR NOVO] de alto risco regulatório — processo completo com segurança reforçada.

## Status

- [x] Pendente
- [ ] Em progresso
- [ ] Concluído
