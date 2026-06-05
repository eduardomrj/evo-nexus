# SERKET — Extrator de Abastecimento

**Projeto:** SERKET (id=3, missão: Automação Software — Plataforma micro-SaaS)
**Status:** Em desenvolvimento ativo
**Código:** `/home/evonexus/evo-projects/serket-extract-abastecimento/src/`
**Dados:** `/home/evonexus/evo-projects/serket-extract-abastecimento/`
**URL local:** `http://localhost:8083/serket-extract/`
**URL produção:** `http://nexus.myworkhome.com.br/serket-extract/`

---

## O que é

Módulo standalone do SERKET para análise de risco de desabastecimento de medicamentos do Componente Especializado da Assistência Farmacêutica (CEAF/CE).

Extrai dados de duas fontes, cruza via fuzzy matching e disponibiliza dashboards de análise:
- **Horus CAF** — sistema federal de distribuição (extração via Playwright, paginação JSF)
- **COPAF** — relatório mensal de abastecimento da SESA-CE (Excel)

---

## Stack

- **Flask** — padrão "Vigil" (UI embutida em strings Python, sem React/npm)
- **SQLite** — banco local em `/home/evonexus/evo-projects/serket-extract-abastecimento/`
- **Playwright** — automação Chromium para extração do Horus
- **rapidfuzz** — fuzzy matching de nomes de medicamentos (token_set_ratio, threshold 80)
- **Chart.js** — gráficos via CDN

---

## Arquitetura do banco (SQLite)

| Tabela | Conteúdo |
|---|---|
| `distributions` | Distribuições brutas do Horus por produto/mês |
| `products` | Produtos únicos (deduplicados) |
| `copaf_abastecimento` | Dados mensais do relatório COPAF/SESA-CE |
| `caf_abastecimento_mensal` | Cruzamento Horus × COPAF (view materializada, upsert mensal) |
| `extraction_runs` | Histórico de execuções com status e timestamps |

---

## Classificação de situação (campo `situacao`)

```sql
CASE
  WHEN pct_abastecimento_copaf >= 80  THEN 'FALHA_OPERACIONAL'  -- estado tinha, Horus não entregou
  WHEN status_copaf = 'DESABASTECIDO' THEN 'DESABASTECIDO'
  WHEN status_copaf IS NOT NULL       THEN 'INSATISFATÓRIO'
  ELSE                                     'SEM_COPAF'
END
```

---

## Dashboards — estado atual

| # | Tela | Rota | Status |
|---|---|---|---|
| 1 | Risco de Desabastecimento | `/serket-extract/analise/risco` | ✅ Entregue |
| 2 | Gap Scatter (% COPAF vs % Horus) | `/serket-extract/analise/gap-scatter` | 🔲 Ticket #87e09d51 |
| 3 | Evolução Mensal por Medicamento | `/serket-extract/analise/evolucao` | 🔲 Ticket #7c1af496 |
| 4 | Ranking de Medicamentos Críticos | `/serket-extract/analise/ranking` | 🔲 Ticket #4cf29444 |
| 5 | Performance por Estabelecimento | `/serket-extract/analise/estabelecimento` | 🔲 Ticket #fd2130d9 |
| 6 | Alertas COPAF vs Demanda Real | `/serket-extract/analise/alertas` | 🔲 Ticket #92882c7b |
| 7 | Resumo Executivo Mensal | `/serket-extract/analise/resumo` | 🔲 Ticket #e611a1ce |

Dashboards sempre disponíveis:
- Dashboard anual: `/serket-extract/`
- COPAF CEAF: `/serket-extract/copaf`
- CAF Mensal: `/serket-extract/caf-mensal`
- Extrações: `/serket-extract/extractions`

---

## Goals ativos (plataforma)

| id | Goal | Métrica | Progresso |
|---|---|---|---|
| 8 | 7 dashboards de análise entregues | count | 1/7 |
| 9 | Extrator estável em produção | boolean | 0/1 |
| 5 | Discovery Hub InovaAF concluído | boolean | 0/1 |
| 6 | Processo credenciamento DATASUS iniciado | boolean | 0/1 |

---

## Decisões técnicas relevantes

- **Sem React/npm** — padrão Vigil para manter o projeto como código Python puro sem pipeline de build. A pasta `src/frontend/` é legado e não está em uso.
- **sessionStorage por tela** — chaves `sk_dashboard`, `sk_copaf`, `sk_caf_mensal`, `sk_risco`. Restore dos filtros ocorre APÓS popular os selects dinâmicos (evita assignment silencioso em select vazio).
- **Paginação Horus** — race condition corrigida: aguarda `td.rich-datascr-act` com novo número de página antes de ler DOM (JSF AJAX é assíncrono).
- **Fuzzy matching** — `token_set_ratio` threshold 80 para tolerar variações de apresentação nos nomes de medicamentos entre Horus e COPAF.
- **upsert mensal** — `INSERT OR REPLACE` na `caf_abastecimento_mensal` para re-população idempotente.

---

## Infraestrutura

- **Porta:** 8083
- **PID file:** `/home/evonexus/evo-projects/serket-extract-abastecimento/.serket-extract.pid`
- **Start/stop:** `./start.sh` / `./stop.sh` no diretório do projeto
- **Integração systemd:** pendente — ticket #a643fa66 (@custom-sysops)

---

## Agentes envolvidos

| Agente | Papel |
|---|---|
| `@bolt-executor` | Implementação dos dashboards (tickets abertos) |
| `@custom-sysops` | Integração systemd permanente |
| `@atlas-project` | Monitoramento de progresso e blockers |
| `@hawk-debugger` | Debugging de extração e regressões |
| `@lens-reviewer` | Review de código antes de merge |
