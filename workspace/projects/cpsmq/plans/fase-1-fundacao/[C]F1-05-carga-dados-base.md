---
author: claude
agent: oracle
type: work-plan-item
date: 2026-04-26
phase: 1
item-id: F1-05
status: pending
---

# F1-05. Carga inicial dos dados-base (contrato, PPI, municípios)

**Fase:** Fundação
**Eixo:** dados
**Tipo:** [DECIDIR]
**Prazo sugerido:** Sem 2 — após F1-04 estar funcional

## O que é

Sessão de trabalho para popular os cadastros com os dados reais do CPSMQ: 10 municípios, especialidades, metas do Contrato de Programa (Anexos 1/2/3) e PPI mensal. Os dados já existem nos arquivos do Google Drive — a decisão é como fazer a carga: parser automatizado (Claude API lendo PDFs) ou cadastro manual no frontend.

## O que fazer

- Mapear cada arquivo do Drive → tabela destino:
  - Contrato de Programa PDF (Anexos 1/2/3) → `contrato_metas` por especialidade
  - PPI mensal (Word/XLS) → `ppi_mensal` por município e procedimento
  - Planilha de coeficiente populacional → `municipios`
- **Decisão:** parser automatizado ou cadastro manual? (recomendação: manual no MVP — o contrato muda só 1x/ano)
- Executar carga inicial do mês corrente + 2-3 meses anteriores para histórico imediato
- Validar com Elistênio: "Esses números batem com o que você tem na cabeça?"
- Documentar mapeamento de colunas dos XLS para reuso na próxima renovação do contrato

## Agente / Skill / Rotina

`@echo-analyst` (estruturar formato real dos dados do Drive) → cadastro manual via frontend (F1-04) ou `@bolt-executor` (script de ETL se opção automatizada)

## O que o usuário precisa decidir/fornecer

- **Estratégia de carga:** manual (mais rápido pra validar MVP) ou parser automatizado via Claude API (mais lento mas reusável)?
- **Recomendação Oracle:** manual no MVP. Contrato muda 1x/ano — o tempo de desenvolver o parser não vale agora.
- Fornecer: acesso ao Drive com os arquivos e clareza sobre quais números do contrato são os vigentes para 2026.

## Impacto esperado

Sem isso, a Fase 2 (extração + dashboard) gera números sem contexto — sabe-se o que foi atendido mas não se atingiu a meta. Este item transforma o sistema de "contador de atendimentos" em "monitor de desempenho".

## Dependências

F1-04 (telas de cadastro funcionais).

## Riscos

**CRÍTICO:** dados errados aqui → relatório incorreto → Elistênio leva número errado para o MP → perda de credibilidade imediata. Mitigação: validação cruzada obrigatória com Elistênio antes de "abrir" o painel para uso real.

## Agente sugerido pra implementação

**Agente:** @oracle (conduz a decisão) + @echo-analyst (extrai e mapeia dados do Drive)

**Por quê:** item [DECIDIR] — a escolha de estratégia de carga precisa de alinhamento com Eduardo antes de qualquer execução. @echo-analyst lê os arquivos do Drive e estrutura o mapeamento.

## Status

- [x] Pendente
- [ ] Em progresso
- [ ] Concluído
