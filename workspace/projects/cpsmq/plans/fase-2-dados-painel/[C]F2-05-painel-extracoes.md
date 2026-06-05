---
author: claude
agent: oracle
type: work-plan-item
date: 2026-04-26
phase: 2
item-id: F2-05
status: pending
---

# F2-05. Painel de extrações (auditoria + reexecução)

**Fase:** Dados + Painel
**Eixo:** operação
**Tipo:** [CONSTRUIR NOVO]
**Prazo sugerido:** Sem 3

## O que é

Tela administrativa que mostra o histórico de todas as extrações do SIGES: data, status (sucesso/falha), links para download dos XLS originais, log de erro e screenshot se falhou. Permite reexecutar a extração manualmente quando a automática falhar.

## O que fazer

- Tela `/extracoes` (lista com data, status, formIDs, links pros XLS originais)
- Detalhe da extração: log completo, mensagem de erro, screenshot se falhou
- Botão "Reexecutar agora" — dispara `run.py` via endpoint protegido por API key de admin
- Upload manual: se o SIGES estiver instável, Elistênio pode baixar o XLS manualmente e fazer upload — o parser processa normalmente
- Badge no menu mostrando status da última extração (verde/amarelo/vermelho)

## Agente / Skill / Rotina

`@bolt-executor` (implementação) + `@canvas-designer` (badge de status no layout)

## O que o usuário precisa decidir/fornecer

- **Permissão de reexecução:** só Eduardo (admin) ou Elistênio também pode disparar manualmente?

## Impacto esperado

Elistênio vê que o sistema está funcionando e confia nos dados. Quando algo falhar, Eduardo tem evidências suficientes para diagnosticar sem pedir que o cliente repita os passos.

## Dependências

F2-03.

## Riscos

Baixo.

## Agente sugerido pra implementação

**Agente:** @bolt-executor

**Por quê:** tela administrativa direta — sem ambiguidade técnica, sem UI complexa.

## Status

- [x] Pendente
- [ ] Em progresso
- [ ] Concluído
