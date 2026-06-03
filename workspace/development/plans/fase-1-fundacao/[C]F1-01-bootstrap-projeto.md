---
author: claude
agent: oracle
type: work-plan-item
date: 2026-04-26
phase: 1
item-id: F1-01
status: pending
---

# F1-01. Bootstrap do projeto e estrutura de diretórios

**Fase:** Fundação
**Eixo:** infraestrutura
**Tipo:** [CONSTRUIR NOVO]
**Prazo sugerido:** Sem 1 — Dia 1

## O que é

Criação do esqueleto completo do projeto seguindo a convenção EvoNexus: código em `ADWs/routines/custom/cpsmq/`, dados persistentes em `/home/evonexus/evo-projects/cpsmq/`. Define a estrutura onde todos os outros componentes serão construídos, o ambiente Python com uv, as variáveis de ambiente e o repositório Git separado.

## O que fazer

- Criar `ADWs/routines/custom/cpsmq/` com subpastas: `backend/`, `frontend/`, `extractor/`, `notifier/`, `bot/`, `migrations/`, `tests/`
- Criar `/home/evonexus/evo-projects/cpsmq/` com subpastas: `logs/`, `reports/raw/`, `reports/consolidated/`, `backups/`
- Criar `pyproject.toml` (uv) com deps: fastapi, uvicorn, sqlalchemy, alembic, playwright, openpyxl, pandas, anthropic, httpx, pydantic, python-dotenv
- Criar `.env.example` com: `CPSMQ_DATA_DIR`, `SIGES_USER`, `SIGES_PASS`, `EVOLUTION_API_URL`, `EVOLUTION_API_KEY`, `WHATSAPP_TARGET`, `ANTHROPIC_API_KEY`, `API_TOKEN`
- Criar `.gitignore` (ignorar `.env`, `*.db`, `reports/`, `logs/`)
- Inicializar repositório Git separado + `README.md` mínimo

## Agente / Skill / Rotina

`@bolt-executor` (estrutura e arquivos base) + `@custom-sysops` (paths e permissões no host LXC)

## O que o usuário precisa decidir/fornecer

- **Repositório Git:** privado da Automação Software no GitHub ou repositório do CPSMQ?
- **Banco de dados:** SQLite no MVP (recomendado) ou PostgreSQL desde o início pensando na escala dos 21 consórcios?

## Impacto esperado

Desbloqueia todos os outros itens da Fase 1. Sem essa base, nada mais pode começar.

## Dependências

Nenhuma.

## Riscos

Estrutura errada de pastas ou convenção violada gera retrabalho nas próximas fases — custo baixo de corrigir agora, alto depois.

## Agente sugerido pra implementação

**Agente:** @bolt-executor + @custom-sysops

| Fase | Agente | Papel |
|---|---|---|
| 1. Build | @bolt-executor | Criar estrutura, pyproject.toml, .env.example, .gitignore |
| 2. Infra | @custom-sysops | Criar paths no host, ajustar permissões, inicializar Git |

**Por quê esse time:** item de bootstrap sem ambiguidade técnica — Bolt executa diretamente, Sysops cuida do host.

## Status

- [x] Pendente
- [ ] Em progresso
- [ ] Concluído
