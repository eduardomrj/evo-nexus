---
author: claude
agent: compass-planner
type: work-plan
date: 2026-04-25
plan-name: vigil-refactor-collect-report
status: draft
mode: direct
---

# Work Plan — Refatorar Vigil: coletar tudo na entrada, inteligência via @pulse na saída

## Context

Hoje o Vigil (`/home/evonexus/evo-projects/vigil/vigil.py`) aplica `classify()` (keyword matching) na entrada de cada mensagem (WhatsApp webhook, Discord bot, Telegram Telethon) e **descarta** o que não passa no filtro. O resultado: relatórios pobres, contexto perdido para sempre. A refatoração inverte o fluxo — salvar 100% das mensagens em JSONL por canal/dia e empurrar a inteligência para o momento da geração do relatório, delegando a interpretação semântica ao `@pulse-community` via `claude -p`.

## Objectives

- Toda mensagem de canal/grupo monitorado é salva integralmente em JSONL (`logs/{platform}-{channel_id}-YYYY-MM-DD.jsonl`), com `topics` embutido como snapshot da config no momento do recebimento.
- O endpoint `POST /vigil/api/reports/generate` passa a invocar `@pulse-community` para interpretar semanticamente as mensagens do dia e devolver totalizadores estruturados.
- A tabela `community_messages` deixa de armazenar mensagens individuais e passa a armazenar **totalizadores diários por canal** (gravados no fim da geração do relatório).
- Os 3 coletores (WhatsApp/Discord/Telegram) e a UI de configuração de grupos continuam funcionando sem mudanças visíveis.

## Guardrails

### Must Have

- Os 3 coletores existentes continuam operacionais: webhook em `/vigil/api/whatsapp/webhook` (vigil.py:811), `VigilDiscordBot.on_message` (vigil.py:705), `_telegram_message_handler` (vigil.py:754).
- UI `/vigil/groups` (vigil.py:1208) e endpoints de configuração de grupos/canais (vigil.py:957-1042) intocados.
- Botão "Gerar Relatório" continua chamando `POST /vigil/api/reports/generate` (vigil.py:1050).
- Um arquivo JSONL por canal por dia, com `topics` embutido em cada linha (snapshot da config).
- Tudo permanece no monolito `vigil.py` — sem novos arquivos Python.
- Dados em `/home/evonexus/evo-projects/vigil/logs/` (convenção de projetos customizados).

### Must NOT Have

- Reescrever o HTML do `_report_html` ou da UI de configuração.
- Chamar LLM em tempo real na entrada (no caminho do webhook/bot/handler).
- Quebrar qualquer endpoint de configuração existente.
- Criar arquivo Python separado (módulo novo) para a refatoração.
- Apagar dados históricos da `community_messages` antiga (migração preserva, schema novo coexiste via tabela nova).

## Task Flow

```
Step 1 (schema/migração) ──┐
                           ├──→ Step 4 (endpoint generate) ──→ Step 5 (invocar @pulse) ──→ Step 6 (testes E2E)
Step 2 (write JSONL/canal) ┤
Step 3 (coletores sem classify) ──┘
```

## Detailed TODOs

### Step 1 — Adicionar tabela `community_daily_totals` e helper `_jsonl_path()`

- **What:**
  - Em `db_init()` (vigil.py:104), adicionar `CREATE TABLE IF NOT EXISTS community_daily_totals` com colunas: `id`, `date TEXT`, `platform TEXT`, `channel_id TEXT`, `channel_name TEXT`, `total_messages INTEGER`, `relevant_messages INTEGER`, `alerts INTEGER`, `topics_json TEXT`, `summary TEXT`, `pulse_raw_json TEXT`, `generated_at TEXT`. Índice `UNIQUE(date, platform, channel_id)`.
  - Manter `community_messages` e `community_links` como estão (legacy/links continuam funcionando).
  - Adicionar função `_jsonl_path(platform: str, channel_id: str, date_str: str) -> Path` retornando `LOGS_DIR / f"{platform}-{channel_id}-{date_str}.jsonl"`. Sanitiza `channel_id` (substitui `/`, `@`, espaços por `_`).
- **Onde:** `vigil.py:104-142` (db_init) e nova função antes de `save_entry` (~vigil.py:200).
- **Owner agent:** @bolt-executor
- **Acceptance criteria:**
  - `sqlite3 vigil.db ".schema community_daily_totals"` mostra a nova tabela.
  - `_jsonl_path("discord", "123456", "2026-04-25")` retorna `logs/discord-123456-2026-04-25.jsonl`.
  - Schema antigo intacto (`community_messages` e `community_links` existem e indexes preservados).
- **Estimated complexity:** LOW

### Step 2 — Função `save_raw_message(entry)` que escreve JSONL por canal/dia

- **What:**
  - Criar `save_raw_message(entry: dict) -> None` em vigil.py (próximo a `save_entry`, ~linha 205) que:
    - Deriva `date_str` de `entry["ts"]` em `America/Fortaleza` (rotação no fuso local, não UTC).
    - Append-only: abre `_jsonl_path(...)` em modo `"a"` e escreve `json.dumps(entry, ensure_ascii=False) + "\n"`.
    - Não toca em SQLite (banco só recebe totalizadores no Step 5).
  - Schema do `entry` exigido: `ts` (ISO8601 UTC), `platform`, `channel_id`, `channel_name`, `sender`, `text` (texto completo, **sem truncar**), `topics` (lista vinda do snapshot da config no momento do recebimento).
  - Manter `save_entry` e `save_link_entry` existentes — coexistência (links continuam indo para `community_links`).
- **Onde:** nova função em `vigil.py` próximo a vigil.py:205.
- **Owner agent:** @bolt-executor
- **Acceptance criteria:**
  - 3 mensagens consecutivas em um canal Discord no mesmo dia geram exatamente 3 linhas no mesmo JSONL.
  - Arquivos diferentes para canais diferentes ou dias diferentes.
  - Cada linha contém todos os campos do schema; `text` não truncado; `topics` é uma lista (mesmo que vazia).
  - Concorrência: 2 mensagens simultâneas (ex: WhatsApp + Discord) não corrompem o JSONL — usar `with open(...)` por chamada (writes por linha em POSIX são atômicos até PIPE_BUF=4KB; se uma linha exceder isso, usar `fcntl.flock` em modo `LOCK_EX`).
- **Estimated complexity:** LOW

### Step 3 — Substituir `classify()` nos 3 coletores: salvar tudo, sem filtro

- **What:**
  - **WhatsApp webhook** (vigil.py:811-873): remover `msg_type = classify(...)` e o early-return em vigil.py:847-849. Construir `entry` no novo schema (Step 2) e chamar `save_raw_message(entry)` em vez de `save_entry(entry)`. **Manter** o `process_links(...)` em thread (vigil.py:866-872) — links continuam coletados como hoje.
  - **Discord** (vigil.py:705-740): remover `msg_type = classify(...)` e early-return em vigil.py:716-718. Idem WhatsApp. Manter `process_links` thread.
  - **Telegram** (vigil.py:754-800): remover `classify(...)` e early-return em vigil.py:766-768. Idem.
  - Em todos os 3, `topics` no entry vem de `g.get("topics") or []` capturado no momento do recebimento (snapshot — se a config mudar depois, o JSONL preserva o que era válido).
  - **Manter** os filtros básicos de admissão: `if not text.strip(): return` (mensagens vazias seguem ignoradas), `if remote_jid not in WHATSAPP_GROUPS: return` (canal não monitorado segue ignorado), `fromMe: return`.
  - **Não remover** a função `classify()` da definição (vigil.py:179-199) — fica como dead code marcada com comentário `# DEPRECATED — kept as safety fallback, not invoked in v2 ingest path`. Permite rollback rápido se necessário.
- **Onde:** vigil.py:705-740, vigil.py:754-800, vigil.py:811-873.
- **Owner agent:** @bolt-executor
- **Acceptance criteria:**
  - Mensagem "bom dia" em canal monitorado (que hoje seria descartada por `KEYWORDS_NOISE`) aparece no JSONL.
  - Nenhum coletor chama `classify()` (verificável com grep `classify(` no fluxo de ingest).
  - Mensagem em canal NÃO monitorado continua sendo ignorada (não cria JSONL).
  - Logs no console mantêm formato `[vigil/{platform}] [{group}] {sender}: {text[:80]}`.
- **Estimated complexity:** MEDIUM

### Step 4 — Refatorar `generate_daily_report()` para ler JSONLs e chamar @pulse

- **What:**
  - Reescrever `generate_daily_report(date_str)` em vigil.py:644-678. Novo fluxo:
    1. Determinar `date_str` (mantém lógica atual com `America/Fortaleza`).
    2. Coletar lista de canais monitorados de `WHATSAPP_GROUPS`, `DISCORD_CHANNELS`, `TELEGRAM_GROUPS`.
    3. Para cada canal, montar caminho via `_jsonl_path(platform, channel_id, date_str)`. **Skip silencioso** se o arquivo não existir (canal sem mensagens no dia — comportamento confirmado).
    4. Ler todos os JSONLs existentes, agregar em `messages_by_channel: dict[str, list[dict]]` (chave = `f"{platform}:{channel_id}"`).
    5. Chamar `_invoke_pulse(messages_by_channel, date_str)` (Step 5) → retorna `dict` estruturado: `{"channels": [{platform, channel_id, channel_name, total, relevant, alerts, topics, summary}], "global_summary": str, "global_alerts": [...]}`.
    6. Persistir um row em `community_daily_totals` por canal (UPSERT por `(date, platform, channel_id)`).
    7. Reusar `_report_html(...)` existente (ou adaptar minimamente para receber a estrutura nova). Para preservar a UI atual com mínimo retrabalho: montar `by_cat`, `alerts`, `groups` no formato esperado por `_report_html` a partir do retorno do Pulse. **Não reescrever o HTML.**
  - Manter `community_links` (vigil.py:657) — os links continuam vindo da tabela legacy populada pelo `process_links`.
- **Onde:** vigil.py:644-678.
- **Owner agent:** @bolt-executor
- **Acceptance criteria:**
  - Chamar `POST /vigil/api/reports/generate` lê os JSONLs do dia (sem tocar em `community_messages` legacy).
  - Canais sem JSONL no dia são silenciosamente pulados (sem erro, sem log de warning ruidoso — só log debug).
  - `community_daily_totals` recebe 1 linha por canal com mensagens no dia.
  - HTML gerado tem o mesmo layout visual da versão atual.
- **Estimated complexity:** HIGH

### Step 5 — Invocar `@pulse-community` via `claude -p` subprocess

- **What:**
  - Implementar `_invoke_pulse(messages_by_channel: dict, date_str: str) -> dict` em vigil.py.
  - Padrão de invocação (alinhado com `ADWs/runner.py:130-154`):
    ```python
    cmd = ["claude", "--print", "--dangerously-skip-permissions",
           "--output-format", "json", "--agent", "pulse-community", prompt]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600,
                            cwd="/home/evonexus/evo-nexus",
                            env={**os.environ, "TERM": "dumb"})
    ```
  - **PATH do `claude`:** ver memory `project_adw_scheduler_cli_path_issue.md` — em ambientes não-interativos o `claude` pode não estar no PATH. Resolver via `shutil.which("claude")` e fallback para `/home/evonexus/.local/bin/claude` (ou caminho derivado de `os.environ["HOME"]`). Se não encontrado, levantar erro claro com instrução de configurar `VIGIL_CLAUDE_BIN`.
  - **Prompt** (system instruction embutida no `prompt` arg):
    - Cabeçalho explicando: "Você é Pulse. Recebeu mensagens cruas de canais monitorados do dia {date_str}. Para cada canal, filtre semanticamente (não keyword) por `topics`, identifique alertas, resuma e devolva JSON estrito."
    - Schema de saída obrigatório (validar com `json.loads` + checagem de chaves):
      ```json
      {
        "channels": [
          {"platform": "...", "channel_id": "...", "channel_name": "...",
           "total": int, "relevant": int, "alerts": int,
           "topics_found": ["..."],
           "summary": "...",
           "alert_messages": [{"sender": "...", "text": "...", "ts": "..."}]}
        ],
        "global_summary": "...",
        "global_alerts": [...]
      }
      ```
    - Payload do prompt: serializar `messages_by_channel` como JSON (com `topics` por canal vindos do primeiro item — ou da config corrente em `WHATSAPP_GROUPS` etc. para canais sem mensagens — porém canais sem mensagens já foram pulados no Step 4).
  - **Limites de payload:** se total > 50k caracteres, dividir por canal (uma chamada por canal grande). Estratégia inicial simples: 1 chamada agregada; mover para chunking se exceder 200k chars.
  - **Tratamento de erro:** timeout/erro de parse → registrar `pulse_raw_json` com o stderr/stdout bruto, marcar `summary = "[Pulse falhou — ver pulse_raw_json]"`, ainda gravar row em `community_daily_totals` com `total_messages` (contagem do JSONL) preenchido, `relevant_messages = total_messages`, `alerts = 0`. Nunca abortar o relatório por falha do LLM.
- **Onde:** nova função em vigil.py (próximo a `generate_daily_report`).
- **Owner agent:** @bolt-executor
- **Acceptance criteria:**
  - Em ambiente onde `claude` está no PATH: chamada retorna JSON válido com a estrutura esperada.
  - Em ambiente sem `claude`: erro claro indicando como configurar (não trava o servidor).
  - Erro de parse do retorno do Pulse não impede que o HTML seja gerado (degrada com summary placeholder).
  - Row em `community_daily_totals` sempre é criado por canal com mensagens no dia, mesmo em falha.
- **Estimated complexity:** HIGH

### Step 6 — Testes manuais E2E + smoke do fluxo completo

- **What:**
  - Subir o Vigil em dev, configurar 1 canal Discord + 1 grupo WhatsApp + 1 chat Telegram para teste.
  - Enviar 3 mensagens em cada canal (mistura de "bom dia", uma com tópico configurado, uma alerta clara). Verificar:
    - 3 JSONLs criados em `logs/` (um por canal+dia).
    - Cada JSONL tem 3 linhas. Nenhuma `community_messages` legacy nova.
  - Acionar `POST /vigil/api/reports/generate` (ou botão da UI).
  - Verificar:
    - Pulse foi invocado (log com prompt e response).
    - 3 rows em `community_daily_totals` com `total=3`, `relevant >= 1`, `alerts >= 1` no canal com alerta.
    - HTML gerado em `reports/` abre sem erro e mostra os totais.
  - Edge case: canal monitorado sem mensagens no dia — relatório roda sem erro, canal não aparece nos totais.
  - Edge case: matar `claude` (renomear binário) — relatório ainda gera HTML degradado.
- **Owner agent:** @oath-verifier
- **Acceptance criteria:**
  - Todos os 6 cenários acima passam.
  - `[C]verification-vigil-refactor.md` produzido com evidências (paths dos JSONLs, output do Pulse, screenshot do HTML).
- **Estimated complexity:** MEDIUM

## Success Criteria

- [ ] Mensagem "bom dia" em canal monitorado é preservada no JSONL (hoje é descartada).
- [ ] Nenhuma chamada a `classify()` no caminho de ingest (grep limpo nos 3 coletores).
- [ ] `community_daily_totals` populada após cada `generate_daily_report`.
- [ ] HTML do relatório continua abrindo no mesmo layout, com totais agora vindos do Pulse.
- [ ] Falha do `claude -p` não derruba o servidor nem bloqueia geração do HTML.
- [ ] 3 coletores e UI de configuração funcionam sem regressão visível.
- [ ] Dados continuam em `/home/evonexus/evo-projects/vigil/` (logs e db).

## Open Questions

- [ ] **Retenção dos JSONLs:** manter o padrão atual de `KEEP_DAYS` (janela deslizante) também para os JSONLs por canal? O design atual (`save_entry`) reescreve o arquivo a cada chamada — caro com volume alto. Proposta: cron diário separado (ou função em `db_init` na primeira chamada do dia) que apaga JSONLs com `mtime > KEEP_DAYS`. **Risco: médio.** Decisão necessária antes do Step 2.
- [ ] **`@pulse-community` aceita prompt longo?** Hoje o pulse-daily lê de `community_messages` direto. Vamos passar JSON cru como argumento. Vale validar se o agente tem skill ou prompt-handling adequado para esse formato, ou se precisa criar variante `@pulse-vigil-report`. **Risco: baixo** (Pulse é genérico, mas vale 1 teste antes do Step 5).
- [ ] **Migração de `community_messages` legacy:** apagamos a tabela depois de N dias rodando o novo fluxo, ou deixamos para sempre? Proposta: deixar para sempre como auditoria histórica (não custa nada). **Risco: baixo.**
- [ ] **`channel_name` em WhatsApp/Telegram:** o nome pode mudar (rename de grupo). Hoje gravamos snapshot a cada mensagem — mantém consistência. Confirmar que isso é aceitável (sim, é o comportamento já existente em `save_entry`). **Risco: baixo.**

## Handoff

- **Próximo agent:** @bolt-executor (executar Steps 1-5)
- **Verifier:** @oath-verifier (Step 6)
- **Source artifact:** este plano em `workspace/development/plans/[C]plan-vigil-refactor-collect-report-2026-04-25.md`
- **What's open:** 4 questões em aberto acima — recomendado responder à questão de retenção (#1) e validar Pulse (#2) antes de Bolt iniciar.
- **Expected output:** vigil.py refatorado com tabela nova, JSONL por canal/dia, classify removido do fluxo de ingest, generate_daily_report invocando @pulse, evidência E2E.
