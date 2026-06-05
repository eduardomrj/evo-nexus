---
author: claude
agent: oracle
type: work-plan-item
date: 2026-04-26
phase: 1
item-id: F1-03
status: pending
---

# F1-03. Backend FastAPI — esqueleto + CRUDs de cadastro

**Fase:** Fundação
**Eixo:** backend
**Tipo:** [CONSTRUIR NOVO]
**Prazo sugerido:** Sem 1 — Dias 2-3

## O que é

API REST com CRUDs para os 4 cadastros-base (municípios, especialidades, contrato, PPI) e endpoint do consolidado. Auth simples via bearer token. Serve tanto o frontend web quanto o bot e o notificador.

## O que fazer

- Criar estrutura FastAPI: `backend/main.py`, `routers/`, `models/`, `schemas/`, `db.py`, `auth.py`
- Endpoints CRUD: `/api/municipios`, `/api/especialidades`, `/api/contrato-metas`, `/api/ppi` (com filtro por mês)
- Endpoint de consulta: `GET /api/consolidado?mes=YYYY-MM&especialidade=&municipio=`
- Endpoint de saúde: `GET /api/health`
- Auth via `Authorization: Bearer <token>` — token único em `.env`; API key separada para serviços internos (extrator, bot)
- CORS liberado para o domínio do frontend
- OpenAPI docs em `/docs`
- Logging JSONL em `${CPSMQ_DATA_DIR}/logs/api-{date}.jsonl`
- Serviço systemd `cpsmq-api.service` rodando uvicorn na porta interna (sugestão: 32360)

## Agente / Skill / Rotina

`@bolt-executor` (implementação) + `@grid-tester` (testes de endpoint) + `@custom-sysops` (systemd + Traefik)

## O que o usuário precisa decidir/fornecer

- **Subdomínio:** `cpsmq.sysautomacao.com.br` (no EvoNexus) ou domínio próprio do CPSMQ?
- **Porta interna:** 32360 ou outra do range da Automação Software?
- **Auth:** token único no MVP — confirma que é suficiente para o Elistênio sozinho agora?

## Impacto esperado

Expõe todos os dados via API para o frontend, o bot e o notificador. Sem o backend, nenhum dos outros componentes funciona.

## Dependências

F1-02.

## Riscos

Token único hardcoded — se vazar, acesso total ao sistema. Mitigação: rotação fácil via `.env` + IP whitelist se possível.

## Agente sugerido pra implementação

**Time:** @bolt-executor → @grid-tester → @custom-sysops

| Fase | Agente | Papel |
|---|---|---|
| 1. Build | @bolt-executor | FastAPI, CRUDs, auth, logging |
| 2. Verify | @grid-tester | Testes de cada endpoint (happy path + edge cases) |
| 3. Infra | @custom-sysops | systemd service, Traefik route, subdomínio |

**Por quê esse time:** backend direto com testes obrigatórios — Bolt implementa, Grid garante que os CRUDs não quebram nos dados reais.

## Status

- [x] Pendente
- [ ] Em progresso
- [ ] Concluído
