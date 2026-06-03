---
author: claude
agent: oracle
type: work-plan-item
date: 2026-04-26
phase: 2
item-id: F2-02
status: pending
---

# F2-02. Parser dos XLS + carga no banco

**Fase:** Dados + Painel
**Eixo:** extração
**Tipo:** [CONSTRUIR NOVO]
**Prazo sugerido:** Sem 2 — Dias 8-9

## O que é

Leitura dos 2 XLS baixados pelo extrator, normalização de colunas, mapeamento para as tabelas `agendamentos` e `atendimentos`, e persistência transacional no banco. Transforma XLS brutos em dados consultáveis pelo dashboard e pelo bot.

## O que fazer

- Criar `extractor/parser.py` com pandas/openpyxl
- Mapeamento do XLS de agendamento (formID 464568178): profissional, especialidade → `especialidade_id`, município → `municipio_id`, qtd_agendada, mes_ref
- Mapeamento do XLS de atendimento (formID 464568165): mesmo + procedimento, qtd_atendida, qtd_falta
- Normalização de nomes: tabela de aliases para tratar variações de grafia (acento, capitalização, abreviação)
- Inserção transacional ligada ao `extracao_id` — se o parse falhar, nada é persistido parcialmente
- Tratar especialidade desconhecida: criar como "pendente" + logar alerta para Eduardo
- Salvar consolidado mensal em `${CPSMQ_DATA_DIR}/reports/consolidated/{YYYY-MM}.xlsx` (auditoria)
- Atualizar VIEW `consolidado_mensal` após cada carga

## Agente / Skill / Rotina

`@bolt-executor` (implementação) + `@grid-tester` (validação cruzada dos dados)

## O que o usuário precisa decidir/fornecer

- **Especialidade desconhecida:** criar como "pendente" (recomendado) ou bloquear a carga e avisar?
- **Profissional não cadastrado:** criar dinamicamente ou exigir cadastro prévio?

## Impacto esperado

Transforma XLS brutos em conhecimento consultável. Sem o parser, o extrator baixa arquivos que ninguém consegue usar.

## Dependências

F2-01 (XLS disponíveis), F1-02 (schema das tabelas), F1-05 (municípios e especialidades cadastrados para o mapeamento funcionar).

## Riscos

Layout do XLS muda entre versões do SIGES → parser quebra silenciosamente (insere zeros). Mitigação: validação de schema estrito no parser + alerta se contagem extraída for zero ou muito diferente do esperado.

## Agente sugerido pra implementação

**Time:** @bolt-executor → @grid-tester

| Fase | Agente | Papel |
|---|---|---|
| 1. Build | @bolt-executor | Parser pandas, normalização, inserção transacional |
| 2. Verify | @grid-tester | Validação cruzada: total XLS == total banco, sem duplicatas |

**Por quê esse time:** parser com dados críticos para tomada de decisão — Grid valida que os números que entram são os números que saem.

## Status

- [x] Pendente
- [ ] Em progresso
- [ ] Concluído
