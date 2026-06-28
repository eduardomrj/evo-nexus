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
| 2 | Gap Scatter (% COPAF vs % Horus) | `/serket-extract/analise/gap-scatter` | 🔴 goal_task id=1 (bolt-executor, **BLOQUEADO ~50 dias** desde 2026-04-26) |
| 3 | Evolução Mensal por Medicamento | `/serket-extract/analise/evolucao` | 🔴 goal_task id=2 (bolt-executor, **BLOQUEADO ~50 dias** desde 2026-04-26) |
| 4 | Ranking de Medicamentos Críticos | `/serket-extract/analise/ranking` | 🔴 goal_task id=3 (bolt-executor, **BLOQUEADO ~50 dias** desde 2026-04-26) |
| 5 | Performance por Estabelecimento | `/serket-extract/analise/estabelecimento` | 🔴 goal_task id=4 (bolt-executor, **BLOQUEADO ~50 dias** desde 2026-04-26) |
| 6 | Alertas COPAF vs Demanda Real | `/serket-extract/analise/alertas` | 🔴 goal_task id=5 (bolt-executor, **BLOQUEADO ~50 dias** desde 2026-04-26) |
| 7 | Resumo Executivo Mensal | `/serket-extract/analise/resumo` | 🔴 goal_task id=6 (bolt-executor, **BLOQUEADO ~50 dias** desde 2026-04-26) |

> 🚨 **ESCALAÇÃO ATLAS — 2026-06-28 (5ª notificação consecutiva sem resposta):** 6/7 dashboards estagnados há **~63 dias** (desde 2026-04-26). Deadline goal_id=8: 2026-07-31 → **33 dias restantes**. Ritmo atual: 0 entregas/mês. Cinco escalações consecutivas sem movimento (2026-06-23, 2026-06-24, 2026-06-25, 2026-06-26, 2026-06-27). **META EM RISCO CRÍTICO — janela técnica se fechando.** Ação urgente: abrir sessão `/bolt` com escopo SERKET (goal_task ids 1–6). Cada dashboard é independente; 6 sessões de ~1h. 33 dias ainda permitem entrega, mas não há margem para mais inação.
>
> 🔴🔴 **ALERTA MÁXIMO — Goal 9 (systemd) vence AMANHÃ (2026-06-30 = em 2 dias):** status=`achieved` mas `current_value=0.0` e task id=7 (@custom-sysops) ainda `open`. Inconsistência crítica: systemd provavelmente não está configurado. **Ação imediata necessária HOJE:** verificar `systemctl status serket-extract`. Se não existir, abrir sessão `/sysops` agora — prazo expira em menos de 48h.

Dashboards sempre disponíveis:
- Dashboard anual: `/serket-extract/`
- COPAF CEAF: `/serket-extract/copaf`
- CAF Mensal: `/serket-extract/caf-mensal`
- Extrações: `/serket-extract/extractions`

---

## Goals ativos (plataforma)

| id | Goal | Métrica | Progresso |
|---|---|---|---|
| 8 | 7 dashboards de análise entregues | count | 1/7 (🚨 6 tasks abertas 63+ dias — 33 dias p/ prazo) |
| 9 | Extrator estável em produção | boolean | 🔴🔴 status=achieved mas current_value=0/1; task systemd id=7 open; **prazo 2026-06-30 em 2 dias** |
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
