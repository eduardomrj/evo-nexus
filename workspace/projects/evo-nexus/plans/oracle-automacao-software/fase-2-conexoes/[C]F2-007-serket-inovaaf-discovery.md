---
author: claude
agent: oracle
type: work-plan-item
date: 2026-04-17
phase: 2
item-id: F2-007
status: pending
---

# F2-007. SERKET — Discovery Integração Hub InovaAF (RNDS, BNAFAR, CADSUS)

**Fase:** 2 — Conexões
**Eixo:** Produto / Engineering
**Tipo:** [DECIDIR]
**Prazo sugerido:** Sem 5-8

## O que é

Discovery técnico completo para integrar o SERKET com o Hub InovaAF do Ministério da Saúde: RNDS (Rede Nacional de Dados em Saúde), BNAFAR (Base Nacional de Dados de Ações da Assistência Farmacêutica) e CADSUS (Cadastro Nacional de Usuários do SUS). Além do discovery, iniciar o processo administrativo de credenciamento DATASUS — que leva meses e precisa começar agora.

## O que fazer

- Research com @scroll-docs: documentação oficial do RNDS (FHIR R4), BNAFAR, CADSUS — portarias, APIs, formatos, certificados digitais exigidos
- Discovery com @echo-analyst: requisitos funcionais da integração (o que o município precisa enviar/receber?), fluxos de dados, formatos de mensagem
- Mapear dependências obrigatórias: certificado digital ICP-Brasil, credenciamento no DATASUS, ambiente de homologação
- Produzir `[C]discovery-serket-inovaaf.md` com: requisitos, gaps, estimativa de esforço, dependências administrativas, e open questions
- **Ação imediata:** iniciar processo de credenciamento DATASUS em paralelo (processo burocrático de meses)

## Agente / Skill / Rotina

`@echo-analyst` (discovery funcional) + `@scroll-docs` (documentação técnica) + `@apex-architect` (avaliação de viabilidade técnica)

## O que o usuário precisa decidir/fornecer

- Escopo: integrar os 3 (RNDS + BNAFAR + CADSUS) ou priorizar um?
- Município de piloto para homologação (o atual ou outro?)
- O município já tem certificado digital ICP-Brasil? Já tem credenciamento DATASUS?
- Alguém do lado do município pode acompanhar o processo de credenciamento?

## Impacto esperado

Roadmap regulatório claro para o SERKET. Sem surpresas de compliance na Fase 3. Processo administrativo DATASUS em andamento antes de começar a implementar.

## Dependências

- Acesso à documentação pública do Hub InovaAF (pública no portal do DATASUS)
- Contato com o município para iniciar o processo administrativo

## Riscos

- **ALTO** — processo de credenciamento DATASUS é burocrático e pode levar 3-6 meses. **Iniciar o processo administrativo AGORA, paralelamente ao discovery técnico.**
- APIs do SUS instáveis ou mal documentadas — mitigação: priorizar ambiente de homologação desde o início
- Certificado ICP-Brasil pode ter custo e tempo de emissão — mitigação: verificar se o município já possui ou precisa adquirir

## Agente sugerido pra implementação

| Fase | Agente | Papel |
|---|---|---|
| 1. Research técnico | @scroll-docs | Documentação RNDS/BNAFAR/CADSUS |
| 2. Discovery funcional | @echo-analyst | Requisitos + fluxos de dados |
| 3. Viabilidade | @apex-architect | Avaliação técnica + ADR preliminar |

**Por quê:** item [DECIDIR] com alta complexidade regulatória — discovery rigoroso antes de qualquer implementação.

## Status

- [x] Pendente
- [ ] Em progresso
- [ ] Concluído
