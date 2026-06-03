---
author: claude
agent: oracle
type: work-plan-item
date: 2026-04-26
phase: 1
item-id: F1-02
status: pending
---

# F1-02. Schema do banco de dados (SQLite + Alembic)

**Fase:** Fundação
**Eixo:** dados
**Tipo:** [CONSTRUIR NOVO]
**Prazo sugerido:** Sem 1 — Dias 1-2

## O que é

Modelagem completa do banco de dados cobrindo cadastros (municípios, especialidades, contrato, PPI) e dados extraídos (agendamentos, atendimentos, consolidado). Migrations versionadas com Alembic. É o núcleo de tudo — sem schema correto, os dados extraídos do SIGES não têm onde persistir.

## O que fazer

- Modelar tabelas:
  - `municipios` (id, nome, ibge_code, coef_populacional, ativo, created_at)
  - `especialidades` (id, nome, codigo_siges, ativo)
  - `contrato_metas` (id, especialidade_id, meta_mensal, anexo_ref, vigencia_inicio, vigencia_fim)
  - `ppi_mensal` (id, municipio_id, especialidade_id, mes_ref [YYYY-MM], qtd_programada, criado_em)
  - `extracoes` (id, executada_em, status, raw_path_agend, raw_path_atend, mensagem_erro)
  - `agendamentos` (id, extracao_id, mes_ref, municipio_id, especialidade_id, profissional, qtd_agendada)
  - `atendimentos` (id, extracao_id, mes_ref, municipio_id, especialidade_id, profissional, procedimento, qtd_atendida, qtd_falta)
  - `bot_conversas` (id, telefone, pergunta, resposta, custo_tokens, created_at)
  - `notificacoes_log` (id, tipo, payload, enviado_em, status)
- Criar VIEW `consolidado_mensal`: mes, municipio, especialidade, contratado, ppi, agendado, atendido, faltas, pct_util
- Criar índices em `mes_ref`, `municipio_id`, `especialidade_id`
- Configurar Alembic apontando para `${CPSMQ_DATA_DIR}/cpsmq.db`
- Migration inicial + seed com os 10 municípios pré-cadastrados

## Agente / Skill / Rotina

`@apex-architect` (revisão do schema e decisões de modelagem) → `@bolt-executor` (implementação SQLAlchemy + Alembic)

## O que o usuário precisa decidir/fornecer

- **Versionamento de PPI:** PPI muda por mês — manter histórico completo (snapshot mensal, recomendado) ou apenas o vigente?
- **Comparativo histórico:** vamos comparar abr/2026 vs abr/2025? Se sim, confirmar que o campo `mes_ref` é suficiente para partição anual.

## Impacto esperado

Todos os outros componentes dependem do schema. Um schema bem modelado agora evita migrations destrutivas nas fases 2 e 3.

## Dependências

F1-01.

## Riscos

Modelagem fraca de PPI ou `contrato_metas` → retrabalho quando os dados reais do Drive chegarem. Mitigação: validar com Elistênio o formato exato dos anexos antes de fechar.

## Agente sugerido pra implementação

**Time:** @apex-architect → @bolt-executor → @grid-tester

| Fase | Agente | Papel |
|---|---|---|
| 1. Solutioning | @apex-architect | ADR do schema — decisões de modelagem, índices, VIEW |
| 2. Build | @bolt-executor | SQLAlchemy models, Alembic migrations, seed |
| 3. Verify | @grid-tester | Testes de integridade do schema e da VIEW |

**Por quê esse time:** schema é a decisão de maior alavancagem do projeto — Apex garante que não virá retrabalho caro depois.

## Status

- [x] Pendente
- [ ] Em progresso
- [ ] Concluído
