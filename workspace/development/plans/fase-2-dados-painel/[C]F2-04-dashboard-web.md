---
author: claude
agent: oracle
type: work-plan-item
date: 2026-04-26
phase: 2
item-id: F2-04
status: pending
---

# F2-04. Dashboard web — consolidado mensal

**Fase:** Dados + Painel
**Eixo:** frontend
**Tipo:** [CONSTRUIR NOVO]
**Prazo sugerido:** Sem 3 — entrega-chave para demo com Elistênio

## O que é

A tela principal do sistema. Elistênio abre, escolhe o mês e vê a visão consolidada: Contratado × PPI × Agendado × Atendido × Faltas × % Utilização, agrupado por município e especialidade. É a entrega-chave do MVP — a validação com Elistênio acontece aqui.

## O que fazer

- Endpoint `GET /api/consolidado?mes=YYYY-MM&especialidade=&municipio=` (via F1-03)
- Tela `/dashboard` com:
  - Filtros no topo: mês (default = corrente), especialidade (multi-select), município (multi-select)
  - **Tabela principal:** linhas = município × especialidade, colunas = Contratado / PPI / Agendado / Atendido / Faltas / % Utilização
  - **Alertas visuais:** célula amarela < 80%, vermelha < 50% de utilização
  - **Cards de resumo no topo:** total agendado / atendido / faltas do mês, % geral da meta
  - **Gráfico de barras:** top 5 municípios por % utilização (melhores e piores)
  - Botão "Exportar XLS" — relatório pronto para reunião
  - Indicador "Última atualização: DD/MM HH:MM" sempre visível
- Mobile-first: tabela vira cards empilhados no celular (Elistênio em viagem)
- Animação de loading enquanto dados chegam

## Agente / Skill / Rotina

`@canvas-designer` (design do dashboard) → `@bolt-executor` (implementação React) → `@probe-qa` (testes interativos) → `@nova-product` (validação com cliente)

## O que o usuário precisa decidir/fornecer

- **Limiares de alerta:** amarelo abaixo de 80% e vermelho abaixo de 50% — confirma esses percentuais? Ou configurável por especialidade?
- **Comparativo M-1:** mostrar variação mês anterior já no MVP ou deixar para depois?
- **Gráficos:** recharts, Chart.js, ou só tabela + cards no MVP (mais rápido)?

## Impacto esperado

Esta é a tela que o Elistênio mostra na reunião com os prefeitos e com o MP. Um dashboard limpo e correto aqui é o argumento de venda para os outros 20 consórcios.

## Dependências

F2-02 (dados no banco), F1-04 (layout base do frontend), F1-05 (dados-base cadastrados para a % ser calculada).

## Riscos

Sobrecarga de informação → gestor não sabe onde olhar. Mitigação: começar com tabela simples + cards, evoluir com feedback do Elistênio após a demo.

## Agente sugerido pra implementação

**Time:** @canvas-designer → @bolt-executor → @probe-qa → @nova-product

| Fase | Agente | Papel |
|---|---|---|
| 1. Design | @canvas-designer | Layout do dashboard, alertas visuais, mobile |
| 2. Build | @bolt-executor | React, integração com API, Export XLS |
| 3. QA | @probe-qa | Testes interativos com dados reais |
| 4. Validação | @nova-product | Sessão de validação com Elistênio |

**Por quê esse time:** esta é a tela mais visível do produto — Canvas garante que não é genérico, Nova garante que atende o gestor.

## Status

- [x] Pendente
- [ ] Em progresso
- [ ] Concluído
