---
author: claude
agent: compass-planner
type: work-plan
date: 2026-04-25
plan-name: vigil-executive-report
status: draft
mode: direct
---

# Work Plan — Vigil Executive Report

## Context
O Vigil hoje gera um relatório diário com contagens simples (mensagens, alertas, links) por canal. Eduardo quer um **relatório executivo com inteligência real**: análise por categoria, hot topics, perguntas frequentes, sentimento, trends e oportunidades — agregando todos os canais num único resumo do dia. Toda mudança fica em `/home/evonexus/evo-projects/vigil/vigil.py` (gitignored, padrão de projetos customizados).

## Objectives
- `_invoke_pulse()` retorna o JSON estruturado completo (categorias, hot_topics, frequent_questions, spam_check, trends, sentiment, opportunities, announcements, important_links, etc.) com fallback gracioso preservado.
- `generate_daily_report()` agrega resultados de todos os canais num único resumo executivo do dia (não soma trivial — merge inteligente de listas + soma de contadores) e usa esse resumo para gerar o HTML.
- Novo HTML (substitui o gerado por `_report_html`) entrega a estrutura executiva pedida (Resumo → Avisos → Discussões → Dúvidas/Respostas → Trends → Sentimento → Oportunidades → Links) com tema escuro Vigil (`#0a0a0a` / `#00FFA7`) e cards por seção.
- Nada quebra: endpoints de configuração intactos, persistência em `community_daily_totals` continua válida, fallback se Pulse falhar.

## Guardrails

### Must Have
- Todas as alterações em `vigil.py` — nenhum arquivo Python novo.
- Truncagem de 150 mensagens por canal (75+75) preservada antes do prompt.
- Fallback gracioso: se Pulse falhar para um canal, retornar estrutura vazia válida com todas as chaves do novo schema (não derrubar o relatório).
- HTML continua sendo gravado em `REPORTS_DIR / vigil-report-{date}.html` com mesmo nome.
- Persistência em `community_daily_totals` mantida (campo `pulse_raw_json` agora carrega o JSON novo — schema mais rico, mas mesma coluna).
- Tema escuro Vigil mantido (`#0a0a0a` background, `#00FFA7` accent, Inter font, cards com `border-radius:12px`).
- Resposta e documento em pt-BR.

### Must NOT Have
- Não criar arquivos novos (templates, módulos, schemas).
- Não alterar a estrutura da tabela `community_daily_totals` (ALTER TABLE) — o JSON novo mora em `pulse_raw_json` que já existe.
- Não mexer nos coletores (Discord/Telegram/WhatsApp webhooks) nem em `save_raw_message`.
- Não mexer nos endpoints de configuração (`/vigil/api/whatsapp/...`, `/vigil/api/discord/...`, `/vigil/api/telegram/...`).
- Não remover o `_report_html` antigo de cara — substituir por uma nova função (mesmo nome ok) que produz o novo layout, mantendo a assinatura compatível ou adaptando o único call-site.

## Task Flow

```
Step 1 (novo prompt + parse) ──► Step 2 (agregação executiva)
                                          │
                                          ▼
                              Step 3 (novo HTML executivo)
                                          │
                                          ▼
                              Step 4 (smoke test + verify)
```

## Detailed TODOs

### Step 1 — Reescrever `_invoke_pulse()` com prompt e schema executivo
- **What:**
  - Em `vigil.py` linha ~722, substituir o prompt atual pelo prompt executivo que pede o JSON completo (total_messages, active_members, categories, hot_topics, frequent_questions, spam_check, trends, sentiment, opportunities, alerts, announcements, important_links, open_questions_count).
  - O prompt deve listar explicitamente cada categoria (`geral`, `duvidas_suporte`, `apresentacoes`, `avisos`, `outros`) e pedir para que a soma das categorias seja igual a `total_messages`.
  - Adicionar instrução para extrair `important_links` e contar `open_questions_count` dos tópicos de suporte.
  - Manter truncagem 150 (75+75) e o `_extract_json()` existente.
  - Reescrever o bloco de parsing pós-resposta (linhas ~780-789): em vez de extrair só 4 campos, mapear todas as chaves do novo schema com defaults seguros (int/list/dict vazios) por chave.
  - Atualizar o `print` de log para imprimir, ex.: `[vigil/pulse] [{canal}] msgs={n} hot={k} questions={q} alerts={a}`.
  - **Atualizar o fallback final** (linha ~798) para retornar um dict com **todas** as chaves do novo schema vazias/zeradas — isso é o que blinda os call-sites quando o Pulse falha.
- **Owner agent:** @bolt-executor
- **Acceptance criteria:**
  - `_invoke_pulse()` chamado com mensagens reais de um canal retorna dict com todas as 13 chaves listadas no schema.
  - Forçando timeout/erro do subprocess (ex.: matando o claude bin), a função retorna o dict-fallback completo sem exceção.
  - `total_messages` no retorno do Pulse é igual ao `len(messages)` truncado, e a soma de `categories.values()` é validada (se divergir, log de warning, mas não falha).
- **Estimated complexity:** MEDIUM

### Step 2 — Agregar resultados de todos os canais num resumo executivo do dia
- **What:**
  - Em `generate_daily_report()` (linha ~801), depois do loop `for platform, channel_id, cfg in channels` (que termina ~linha 887), introduzir uma função interna `_aggregate_executive_summary(channel_messages: list[dict]) -> dict` que recebe os dicts por canal (cada um já contém o `pulse_result` completo — guardar `pulse_result` inteiro em `channel_messages` em vez de só os 4 campos antigos) e retorna o resumo agregado do dia:
    - Soma: `total_messages`, `alerts`, `open_questions_count`, `categories.*`, `spam_check.duplicates`.
    - Set/dedupe: `active_members` (união de senders únicos por canal — recalcular do JSONL ao invés de somar para evitar dupla contagem; basta `len({m['sender'] for ch in channel_messages for m in ch['messages']})`).
    - Concat + dedup: `announcements`, `important_links`, `spam_check.suspicious_patterns`.
    - Merge ordenado por `count` desc: `hot_topics` (top 8), `frequent_questions` (top 6), `trends` (top 5), `opportunities` (top 5) — preservar `channel_name` em cada item para mostrar origem.
    - Sentimento agregado: média ponderada de `sentiment.score` por `total_messages`, `overall` = label do score médio (mapa simples: `<-0.3` frustrado / `[-0.3,0.3]` neutro / `>0.3` positivo / `mixed` se desvio padrão alto), `highlights` = concat top 3 de cada canal.
  - Persistir o JSON agregado também em uma linha extra de `community_daily_totals` com `platform='_aggregate'`, `channel_id='_day'` (ou usar uma nova coluna `is_aggregate` — mas como guardrail veta ALTER, usar a convenção de chave especial). Fica disponível para queries históricas sem schema novo.
  - Modificar a chamada `_report_html(...)` para passar o `executive_summary` em vez (ou além) das listas antigas — o Step 3 redefine essa assinatura.
- **Owner agent:** @bolt-executor
- **Acceptance criteria:**
  - Rodar `generate_daily_report("2026-04-24")` (data com dados reais) e inspecionar `executive_summary` no debugger / log: contadores batem com soma manual, `active_members` ≤ soma dos `active_members` por canal, listas estão deduplicadas e ordenadas.
  - Linha agregada gravada em `community_daily_totals` com `platform='_aggregate'` e `pulse_raw_json` parseável.
  - Se um canal retornar fallback vazio, agregação não quebra (zeros somam zero, listas vazias concat).
- **Estimated complexity:** MEDIUM

### Step 3 — Novo `_report_html` executivo (substitui layout atual)
- **What:**
  - Reescrever `_report_html` (linha ~502) com nova assinatura: `_report_html(date_str, executive_summary, link_rows, generated_at, prev_total) -> str`. Atualizar o único call-site em `generate_daily_report`.
  - Estrutura do HTML (em ordem, todas como `.section` com tema atual):
    1. **Header** — `Vigil — Resumo Executivo {data}` + botão Exportar PDF (manter).
    2. **Cards de topo** (grid 4 cols) — `total_messages`, `active_members`, `important_links` count, `alerts` (mantém vermelho).
    3. **Categorias** — barra horizontal compacta com 5 segmentos (geral / dúvidas-suporte / apresentações / avisos / outros), cada um com cor + número.
    4. **📢 Avisos** (`announcements`) — lista com bullets (ocultar a seção se vazia).
    5. **💬 Discussões do dia** (`hot_topics`) — cards com título 🔥, `count` e `summary`. Mostrar até 8.
    6. **❓ Dúvidas & Respostas** — duas colunas: ✅ `frequent_questions` com `answered=true` (mostrar `question` + `answer_summary`) | ⏳ "X dúvidas em aberto" (= `open_questions_count`) com link/explicação.
    7. **📈 Trends** (`trends`) — cards com `topic` + `reason`.
    8. **😊 Sentimento** — badge grande do `overall` (cor por label: positivo verde, neutro cinza, frustrado vermelho, misto amarelo) + `score` numérico + lista de `highlights`.
    9. **💡 Oportunidades** (`opportunities`) — agrupar por `type` (conteudo / feature / acao) com ícone.
    10. **🔗 Links Importantes** (`important_links` + `link_rows` da tabela `community_links`) — tabela compacta com domínio + título.
    11. **Spam check** (rodapé pequeno, só se `duplicates>0` ou padrões suspeitos) — `X duplicadas detectadas` + lista de padrões.
    12. Footer atual (`Vigil · Automação Software · {data}`).
  - Manter CSS existente (Inter, `#0a0a0a`, `#00FFA7`, cards `#111`, etc.) e `@media print`.
  - Função `esc()` reaproveitada. Sem JS além do `window.print()`.
  - Esconder seções vazias (sem renderizar `<div class="section">` se a lista correspondente estiver vazia) para o relatório não ficar com "buracos" em dias quietos.
- **Owner agent:** @canvas-designer (UI) com handoff para @bolt-executor (integração)
- **Acceptance criteria:**
  - Abrir o HTML gerado num browser: tema escuro, 11 seções na ordem certa, cards de topo lendo dados reais.
  - Em um dia com dados reais, conferir visualmente: `hot_topics` aparecem como cards 🔥, `frequent_questions` separadas em respondidas/em aberto, sentimento com badge colorido, oportunidades agrupadas por tipo.
  - Em um dia "quieto" (poucas msgs), seções vazias somem; layout não quebra.
  - `window.print()` ainda gera PDF legível (CSS `@media print` aplicado).
- **Estimated complexity:** HIGH

### Step 4 — Smoke test e self-verification
- **What:**
  - Rodar `python -c "from vigil import generate_daily_report; print(generate_daily_report('2026-04-24'))"` (data anterior com dados reais).
  - Verificar:
    1. Geração concluída sem stack trace.
    2. Arquivo `vigil-report-2026-04-24.html` criado em `REPORTS_DIR`.
    3. Linha agregada em `community_daily_totals` (SELECT WHERE platform='_aggregate' AND date='2026-04-24').
    4. Abrir HTML — checagem visual rápida das 11 seções.
    5. Forçar fallback: temporariamente apontar `claude_bin` para `/bin/false`, rodar de novo — relatório deve gerar com seções vazias mas sem erro 500.
  - Se algo falhar no path do `claude` no env do scheduler (issue conhecida em `project_adw_scheduler_cli_path_issue`), confirmar que o fallback está funcionando mesmo no ambiente do scheduler.
- **Owner agent:** @oath-verifier
- **Acceptance criteria:**
  - HTML gerado abre sem JS errors.
  - DB tem 1 linha por canal + 1 linha agregada para a data.
  - Teste de fallback (Pulse indisponível) gera relatório com mensagem "Pulse indisponível" no lugar do conteúdo executivo, sem 500.
  - Tempo total de execução de `generate_daily_report` para 5-10 canais ≤ ~10min (cada chamada Pulse pode levar 1-2min — N canais sequenciais).
- **Estimated complexity:** LOW

## Success Criteria
- [ ] `_invoke_pulse()` retorna o schema executivo completo de 13 chaves (com fallback igualmente completo).
- [ ] `generate_daily_report()` produz um `executive_summary` agregado com merge correto (sums + dedupes + top-N) e o persiste em `community_daily_totals` (linha `_aggregate`).
- [ ] HTML gerado tem as 11 seções na ordem pedida, tema escuro Vigil preservado, sem layouts quebrados em dias quietos.
- [ ] Endpoints de configuração e coletores (Discord/Telegram/WhatsApp) não foram tocados — `make vigil-test` ou equivalente passa.
- [ ] Fallback gracioso verificado: rodar com Pulse indisponível não derruba o relatório.
- [ ] Truncagem 150 msgs/canal preservada.

## Open Questions
- [ ] **Paralelizar chamadas do Pulse?** Hoje é sequencial (loop no Step 2 do `generate_daily_report`); com novo prompt mais pesado, 10 canais × 2min = 20min. Vale paralelizar com `ThreadPoolExecutor(max_workers=3)`? — risco: rate-limit no claude CLI. **Risco: médio** — se rodar dentro do horário do scheduler, sequencial pode estourar timeout. **Decisão sugerida:** começar sequencial, medir, paralelizar depois se necessário.
- [ ] **Schema da linha agregada em `community_daily_totals`** — usar `platform='_aggregate', channel_id='_day'` (convenção) ou criar coluna `is_aggregate`? Guardrail diz "não ALTER TABLE", então convenção. **Risco: baixo.** Confirmar com Eduardo se OK.
- [ ] **Tradução das categorias no HTML** — schema usa `duvidas_suporte` (snake_case sem acento). UI deve mostrar "Dúvidas/Suporte" — fazer mapa de tradução em Python ou no template? **Risco: baixo** — mapa em Python no `_report_html`.

## Handoff
- **Next agent:** @bolt-executor (após aprovação explícita do Eduardo).
- **Next skill:** `dev-verify` antes do handoff a @oath-verifier no Step 4.
- **Source artifact:** este plano em `workspace/development/plans/[C]plan-vigil-executive-report-2026-04-25.md`.
- **Arquivo único alvo:** `/home/evonexus/evo-projects/vigil/vigil.py` (gitignored — código vive em repo do projeto Vigil; dados em `/home/evonexus/evo-projects/vigil/`).
