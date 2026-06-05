---
author: claude
agent: oracle
type: work-plan-item
date: 2026-04-26
phase: 1
item-id: F1-04
status: pending
---

# F1-04. Frontend base + telas de cadastro

**Fase:** Fundação
**Eixo:** frontend
**Tipo:** [CONSTRUIR NOVO]
**Prazo sugerido:** Sem 1-2 — Dias 3-5

## O que é

Frontend web responsivo (Vite + React + TypeScript + TailwindCSS + shadcn/ui) com login simples e telas de cadastro para Municípios, Especialidades, Contrato de Programa e PPI mensal. É a interface onde Elistênio popula os dados-base antes de o sistema começar a monitorar.

## O que fazer

- Criar `frontend/` com Vite + React + TypeScript + TailwindCSS + shadcn/ui
- Layout: sidebar (Dashboard, Municípios, Especialidades, Contrato, PPI, Extrações, Configurações) + topbar com nome do consórcio
- Tela de login simples: input de token → guarda em localStorage
- **Tela Municípios:** tabela editável (nome, IBGE, coeficiente populacional)
- **Tela Especialidades:** lista + form (nome, código SIGES)
- **Tela Contrato de Programa:** form para metas mensais por especialidade (Anexos 1/2/3) + visualização tabular por mês
- **Tela PPI mensal:** seletor de mês + grid editável (município × especialidade = qtd programada) + importação via upload XLS/CSV
- Build deployado via Traefik no subdomínio escolhido
- Mobile-first: sidebar vira hamburger no celular

## Agente / Skill / Rotina

`@canvas-designer` (design e identidade visual) → `@bolt-executor` (implementação React) → `@probe-qa` (testes interativos)

## O que o usuário precisa decidir/fornecer

- **Identidade visual:** cores e logo do CPSMQ (verde institucional?) ou tema padrão da Automação Software?
- **PPI no MVP:** upload XLS com auto-mapeamento de colunas ou cadastro manual célula a célula?

## Impacto esperado

Sem os cadastros preenchidos, o consolidado da Fase 2 não tem âncora — o sistema não consegue calcular % de meta sem conhecer o que foi contratado e programado. Esta tela é o pré-requisito humano do sistema.

## Dependências

F1-03.

## Riscos

UX ruim para cadastrar dezenas de linhas de PPI manualmente → Elistênio abandona o cadastro. Mitigação: entregar importação XLS no MVP mesmo que básica.

## Agente sugerido pra implementação

**Time:** @canvas-designer → @bolt-executor → @probe-qa

| Fase | Agente | Papel |
|---|---|---|
| 1. Design | @canvas-designer | Identidade visual, layout, componentes |
| 2. Build | @bolt-executor | Implementação React, integração com API |
| 3. QA | @probe-qa | Testes interativos das telas de cadastro |

**Por quê esse time:** frontend com UI/UX importante para o gestor — Canvas garante que não fica "AI-slop", Probe valida o fluxo real.

## Status

- [x] Pendente
- [ ] Em progresso
- [ ] Concluído
