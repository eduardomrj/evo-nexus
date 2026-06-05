---
author: claude
agent: oracle
type: work-plan-index
date: 2026-04-26
plan-name: cpsmq-mvp
status: draft
mode: index
---

# CPSMQ MVP — Dashboard de Gestão do Consórcio de Saúde

**Tipo:** índice. Cada item tem arquivo próprio na pasta da respectiva fase. Este arquivo não duplica o detalhamento — aponta pros arquivos-filhos.

---

## Contexto

Sistema de gestão para o Consórcio Público de Saúde da Região de Quixadá (CE). Resolve o problema de 1-2 dias de trabalho manual para consolidar dados de atendimentos do SIGES. O gestor (Elistênio Nóbrega) viaja constantemente e precisa de dados atualizados em reuniões com municípios, MP e TCE. A extração do SIGES está resolvida via Playwright (fluxo validado). O produto cobre: painel web de monitoramento de metas (Contratado × PPI × Agendado × Atendido × Faltas por município e especialidade), extração automatizada diária às 17:30, notificação Telegram às 19h e bot de IA especializado para consultas em linguagem natural.

## Objetivos

- Eliminar os 1-2 dias de trabalho manual de consolidação de dados do SIGES
- Dar ao gestor visibilidade em tempo real do cumprimento das metas do Contrato de Programa
- Entregar acesso 24/7 via web + WhatsApp (painel, resumo diário e bot de IA)
- Criar produto replicável para os outros 20 consórcios de saúde do Ceará

## Guardrails

**Must Have**
- Extração automatizada do SIGES via Playwright (fluxo já validado)
- Painel web responsivo (acesso mobile obrigatório)
- Bot IA via Telegram com respostas baseadas exclusivamente nos dados do banco (zero alucinação)
- Projeto standalone: código e dados em `/home/evonexus/evo-projects/cpsmq/`, git próprio — independente do EvoNexus

**Must NOT Have**
- Dependência de API do Fest Médico ou SIGES (extração via automação web, não API)
- Integração com sistemas de terceiros sem validação de existência de API
- Bot respondendo com dados não fundamentados em SQL (sem "free text" sobre números)
- Módulo de assistência farmacêutica (CAF) — fora do escopo

---

## Visão geral das fases

```
Fase 1 — Fundação (Sem 1-2)      →    Fase 2 — Dados + Painel (Sem 2-3)    →    Fase 3 — IA + WhatsApp (Sem 4-5)
Estrutura, banco, cadastros            Extração SIGES, carga, dashboard           Bot IA, notificações, validação
```

---

## Fase 1 — Fundação (Sem 1–2)

Pasta: [`fase-1-fundacao/`](fase-1-fundacao/)

| # | Item | Tipo |
|---|---|---|
| F1-01 | [Bootstrap do projeto e estrutura de diretórios](fase-1-fundacao/[C]F1-01-bootstrap-projeto.md) | [CONSTRUIR NOVO] |
| F1-02 | [Schema do banco de dados (SQLite + Alembic)](fase-1-fundacao/[C]F1-02-schema-banco.md) | [CONSTRUIR NOVO] |
| F1-03 | [Backend FastAPI — esqueleto + CRUDs de cadastro](fase-1-fundacao/[C]F1-03-backend-fastapi.md) | [CONSTRUIR NOVO] |
| F1-04 | [Frontend base + telas de cadastro](fase-1-fundacao/[C]F1-04-frontend-cadastros.md) | [CONSTRUIR NOVO] |
| F1-05 | [Carga inicial dos dados-base (contrato, PPI, municípios)](fase-1-fundacao/[C]F1-05-carga-dados-base.md) | [DECIDIR] |

---

## Fase 2 — Dados + Painel (Sem 2–3)

Pasta: [`fase-2-dados-painel/`](fase-2-dados-painel/)

| # | Item | Tipo |
|---|---|---|
| F2-01 | [Extrator Playwright do SIGES](fase-2-dados-painel/[C]F2-01-extrator-siges.md) | [CONSTRUIR NOVO] |
| F2-02 | [Parser dos XLS + carga no banco](fase-2-dados-painel/[C]F2-02-parser-xls-carga.md) | [CONSTRUIR NOVO] |
| F2-03 | [Agendamento da rotina diária 17:30](fase-2-dados-painel/[C]F2-03-rotina-extracao.md) | [ATIVAR] |
| F2-04 | [Dashboard web — consolidado mensal](fase-2-dados-painel/[C]F2-04-dashboard-web.md) | [CONSTRUIR NOVO] |
| F2-05 | [Painel de extrações (auditoria + reexecução)](fase-2-dados-painel/[C]F2-05-painel-extracoes.md) | [CONSTRUIR NOVO] |

---

## Fase 3 — IA + Telegram (Sem 4–5)

Pasta: [`fase-3-ia-whatsapp/`](fase-3-ia-whatsapp/)

| # | Item | Tipo |
|---|---|---|
| F3-01 | [Integração Telegram Bot API](fase-3-ia-whatsapp/[C]F3-01-evolution-api.md) | [ATIVAR] |
| F3-02 | [Notificação diária 19h via Telegram](fase-3-ia-whatsapp/[C]F3-02-notificacao-diaria.md) | [CONSTRUIR NOVO] |
| F3-03 | [Bot IA Telegram para consultas em linguagem natural](fase-3-ia-whatsapp/[C]F3-03-bot-ia-whatsapp.md) | [CONSTRUIR NOVO] |
| F3-04 | [Onboarding e validação com Elistênio](fase-3-ia-whatsapp/[C]F3-04-onboarding-validacao.md) | [DECIDIR] |

---

## Decisões — TODAS RESOLVIDAS (2026-04-26)

| # | Decisão | Resolução |
|---|---|---|
| 1 | **Repositório Git** | GitHub da Automação Software — token já existe no EvoNexus |
| 2 | **Banco de dados** | SQLite no MVP; PostgreSQL só se escalar para outros consórcios |
| 3 | **Domínio** | `policlinica.myworkhome.com.br` (Traefik, porta 32360) |
| 4 | **Credenciais SIGES** | User `92441238353` / Pass `saude123` — somente em `.env`, nunca em git |
| 5 | **Carga dados-base** | Usar documentos do Drive já extraídos — scripts de seed automatizados |
| 6 | **Canal de mensagens** | **Telegram** (MVP sem número WhatsApp disponível) |
| 7 | **Modelo Claude** | Claude Sonnet 4.6 (custo-benefício) |
| 8 | **Orçamento Claude** | $50/mês |
| 9 | **Design system** | Canvas designer define antes do Bolt implementar a UI |
| 10 | **Isolamento** | Projeto standalone — `/home/evonexus/evo-projects/cpsmq/`, git próprio, sem acoplamento ao EvoNexus |

---

## Histórico de mudanças

- **v1 (2026-04-26):** versão inicial. Plano criado após discovery completo com Eduardo Martins — 10 reuniões lidas (mai/2025–abr/2026), documentos do Drive extraídos, fluxo SIGES validado.
- **v2 (2026-04-26):** todas as 10 decisões críticas resolvidas. Telegram substitui WhatsApp no MVP. Projeto marcado como standalone. Canvas acionado para design system antes da implementação da UI.
