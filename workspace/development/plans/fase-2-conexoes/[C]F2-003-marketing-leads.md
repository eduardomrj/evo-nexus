---
author: claude
agent: oracle
type: work-plan-item
date: 2026-04-17
phase: 2
item-id: F2-003
status: pending
---

# F2-003. Marketing e Captação de Leads — Mako + Pixel

**Fase:** 2 — Conexões
**Eixo:** Marketing
**Tipo:** [CONSTRUIR NOVO]
**Prazo sugerido:** Sem 5-7

## O que é

Construir o funil de marketing do zero: estratégia de conteúdo, calendário editorial, sequências de email, e auditoria SEO dos sites. Mako cuida da estratégia e campanhas, Pixel produz o conteúdo para redes sociais. Resolve o problema de zero captação de leads ativa.

## O que fazer

- Definir personas e pilares de conteúdo com `social-context` + `social-content-strategy`: cliente ideal do Emporion (pequeno comerciante), cliente do SERKET (gestor de saúde pública municipal)
- Criar calendário de conteúdo mensal com `social-content-calendar` para LinkedIn e Instagram
- Gerar primeiros 10 posts com `social-post-writer` e `social-carousel-writer`
- Criar sequência de email nurturing para leads de Emporion: onboarding → educação → conversão com `mkt-email-sequence`
- Rodar auditoria SEO em sysautomacao.com.br e automacaosoftware.com.br com `mkt-seo-audit`

## Agente / Skill / Rotina

`@mako-marketing` + `@pixel-social-media` + skills: `mkt-campaign-plan`, `mkt-email-sequence`, `mkt-seo-audit`, `mkt-competitive-brief`, `social-content-strategy`, `social-content-calendar`, `social-post-writer`, `social-carousel-writer`

## O que o usuário precisa decidir/fornecer

- Redes sociais prioritárias (LinkedIn, Instagram, YouTube — qual foca primeiro?)
- Tom de voz da marca (técnico e confiável? acessível? ambos dependendo da rede?)
- Personas confirmadas: quem é o cliente ideal do Emporion? Gestor de TI? Dono do mercado? Contador?
- Budget para ads (se houver) ou apenas orgânico?
- Acesso às contas das redes sociais

## Impacto esperado

Presença digital ativa e consistente. Pipeline de leads orgânicos começando a ser alimentado. Sequência de email automatizada nutre leads sem intervenção manual.

## Dependências

- Perfis criados nas redes sociais prioritárias
- Sites acessíveis para auditoria SEO (sysautomacao.com.br / automacaosoftware.com.br)

## Riscos

- Conteúdo genérico sem diferencial — mitigação: usar `mkt-competitive-brief` para mapeamento competitivo antes de criar conteúdo
- Inconsistência de publicação — mitigação: calendário + rotina semanal `social-analytics-report` para monitorar

## Agente sugerido pra implementação

| Fase | Agente | Papel |
|---|---|---|
| 1. Estratégia | @mako-marketing | Personas, pilares, calendário |
| 2. Conteúdo | @pixel-social-media | Posts, carousels, calendário editorial |
| 3. Email | @mako-marketing | Sequência de nurturing |
| 4. SEO | @mako-marketing | Auditoria e recomendações |

**Por quê:** dois agentes especializados com domínios distintos (estratégia vs criação).

## Status

- [x] Pendente
- [ ] Em progresso
- [ ] Concluído
