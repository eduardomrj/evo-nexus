# ADR F3-03 — Bot IA CPSMQ: Tool Calling com SQL Fechado

## Status
Accepted — 2026-04-26

## Contexto

O CPSMQ — Consórcio Público de Saúde da Região de Quixadá — precisa de um bot de Telegram que responda perguntas em linguagem natural sobre dados de atendimento (agendamentos, atendimentos, metas contratuais, PPI). O usuário primário é Elistênio Nóbrega, gestor que viaja com frequência e consulta dados pelo celular para reuniões com prefeitos, Ministério Público e TCE.

**Risco central:** alucinação numérica é inaceitável. Um número inventado em reunião com TCE destrói a confiança no produto e potencialmente cria responsabilização para o gestor. A regra é: **toda resposta com número precisa vir de uma query SQL determinística, com fonte e data de extração citadas**.

### Requisitos não-negociáveis
1. Zero free-text → SQL. Modelo nunca escreve SQL; só seleciona tools com parâmetros enumerados.
2. Toda resposta cita a data da última extração (`extracoes.data_extracao`).
3. Quando dados não existem, o bot diz "não há dados para o período" — nunca estima.
4. Custo controlado em $50/mês (Sonnet 4.6 ≈ $3/MTok input, $15/MTok output).
5. Fallback explícito quando há ambiguidade ou erro: "consulte o painel em <url>".

### Restrições da stack
- Python + SQLAlchemy + SQLite (`/home/evonexus/evo-projects/cpsmq/cpsmq.db`)
- Anthropic SDK (Claude Sonnet 4.6) com tool calling
- python-telegram-bot
- Modelos já definidos em `backend/models.py` (Municipio, Especialidade, ContratoMeta, PpiMensal, Agendamento, Atendimento, Extracao, BotConversa)

## Decisão

**Arquitetura:** Tool Calling com SQL fechado e parâmetros validados.

1. O modelo (Claude Sonnet 4.6) recebe a pergunta + system prompt + lista de 5 tools.
2. O modelo escolhe **uma** tool por turno, passando parâmetros normalizados (mês `YYYY-MM`, IDs ou nomes de enums).
3. O backend resolve nomes → IDs via lookup tables (não-fuzzy: match exato no nome do município/especialidade, com normalização de acentos e case). Se não encontrar, retorna erro estruturado e o modelo decide se pede esclarecimento ou cai no fallback.
4. Cada tool executa uma query SQL **parametrizada e fechada** — nenhum parâmetro entra na string SQL via interpolação; apenas via bind parameters do SQLAlchemy.
5. O resultado da tool inclui `data_extracao_iso` (da última `Extracao` com `status='success'`).
6. O modelo formata a resposta em pt-BR, **sempre citando a data de extração** ao final.
7. Loop de tool calling com **máximo 3 iterações** por mensagem do usuário (hard limit).

**Por que essa arquitetura:**
- O modelo nunca toca em SQL. Não há SQL injection nem alucinação de schema.
- Tools são funções Python testáveis isoladamente — `pytest` cobre cada uma com fixtures determinísticas.
- Custo previsível: 5 tools × ~150 tokens de descrição = ~750 tokens fixos no system prompt; respostas curtas mantêm output controlado.

## System Prompt

```
Você é o assistente de dados do CPSMQ — Consórcio Público de Saúde da Região de Quixadá.

Seu único trabalho é responder perguntas sobre os números do consórcio com base nas tools disponíveis. Você fala em português do Brasil, em tom direto e profissional, com Elistênio Nóbrega (gestor do consórcio).

REGRAS INVIOLÁVEIS:

1. NUNCA invente números. Todo número que você citar precisa vir de uma tool. Se não veio de uma tool nesta conversa, você não pode dizer.

2. Se a tool retornar lista vazia ou erro, diga literalmente: "Não há dados para o período/parâmetros informados." NUNCA estime, interpole ou use conhecimento prévio.

3. SEMPRE cite a data da última extração ao final da resposta, no formato: "Dados extraídos em DD/MM/AAAA."

4. NUNCA escreva SQL, código, ou explicações técnicas. Você responde números, percentuais e tendências em linguagem natural curta.

5. Se a pergunta for ambígua (mês não especificado, município ambíguo), peça esclarecimento ANTES de chamar a tool. Não chute.

6. Se uma tool falhar com erro técnico ou retornar resultado contraditório, responda: "Não consegui consultar os dados agora. Consulte o painel: https://cpsmq.local/dashboard"

7. Não responda perguntas fora do escopo (saúde pública, política, opinião, conselho médico). Se for fora de escopo, diga: "Posso te ajudar apenas com dados de atendimento do consórcio."

8. Limite cada resposta a no máximo 1000 tokens. Seja conciso. Números primeiro, contexto depois.

9. Você só sabe do que está no banco. Não comente sobre eventos atuais, decisões políticas, ou interpretações que vão além dos números.

FORMATO DE RESPOSTA:
- Comece com o número-chave em negrito (ex: **78%** de utilização).
- Em seguida, 1-2 frases de contexto.
- Termine com "Dados extraídos em DD/MM/AAAA."
```

## Tools disponíveis (tool calling Claude)

Todas as tools recebem `mes` como string `YYYY-MM` (validada com regex `^\d{4}-(0[1-9]|1[0-2])$`). Nomes de município/especialidade são resolvidos para IDs via lookup helpers `_resolve_municipio(nome)` e `_resolve_especialidade(nome)`. Toda tool retorna `{"data": [...], "data_extracao_iso": "...", "row_count": N}` ou `{"error": "..."}`.

### 1. `query_consolidado(mes, municipio=None, especialidade=None)`

**Descrição (passada ao modelo):**
> Retorna o consolidado mensal: contratado, PPI, agendado, atendido, faltas e % de utilização. Use para perguntas como "como está fevereiro?", "qual o atendimento de cardiologia em Quixadá em março?". Filtros opcionais por município e especialidade. Sem filtro, retorna a soma do consórcio inteiro.

**Parâmetros:**
- `mes` (string, obrigatório): `YYYY-MM`
- `municipio` (string, opcional): nome do município (ex: "Quixadá")
- `especialidade` (string, opcional): nome ou código da especialidade (ex: "Cardiologia")

**Query SQL (parametrizada via SQLAlchemy):**
```sql
SELECT
  m.nome AS municipio,
  e.nome AS especialidade,
  COALESCE(cm.meta_mensal, 0) AS contratado,
  ppi.quantidade_programada AS ppi,
  COALESCE(SUM(ag.quantidade), 0) AS agendado,
  COALESCE(SUM(at.quantidade_atendida), 0) AS atendido,
  COALESCE(SUM(at.quantidade_falta), 0) AS faltas
FROM ppi_mensal ppi
JOIN municipios m ON m.id = ppi.municipio_id
JOIN especialidades e ON e.id = ppi.especialidade_id
LEFT JOIN contrato_metas cm
  ON cm.especialidade_id = ppi.especialidade_id
  AND cm.vigencia_inicio <= :mes_ref
  AND (cm.vigencia_fim IS NULL OR cm.vigencia_fim >= :mes_ref)
LEFT JOIN agendamentos ag
  ON ag.municipio_id = ppi.municipio_id
  AND ag.especialidade_id = ppi.especialidade_id
  AND ag.mes_referencia = :mes_ref
LEFT JOIN atendimentos at
  ON at.municipio_id = ppi.municipio_id
  AND at.especialidade_id = ppi.especialidade_id
  AND at.mes_referencia = :mes_ref
WHERE ppi.mes_referencia = :mes_ref
  AND (:municipio_id IS NULL OR ppi.municipio_id = :municipio_id)
  AND (:especialidade_id IS NULL OR ppi.especialidade_id = :especialidade_id)
GROUP BY m.nome, e.nome, cm.meta_mensal, ppi.quantidade_programada
ORDER BY m.nome, e.nome
LIMIT 100
```

**Exemplo de output:**
```json
{
  "data": [
    {"municipio": "Quixadá", "especialidade": "Cardiologia",
     "contratado": 200, "ppi": 180, "agendado": 175, "atendido": 158,
     "faltas": 17, "percentual_utilizacao": 79.0}
  ],
  "data_extracao_iso": "2026-04-25T03:14:00",
  "row_count": 1
}
```

### 2. `query_meta_contrato(especialidade=None)`

**Descrição:**
> Retorna a meta contratual mensal vigente por especialidade. Use para perguntas tipo "qual a meta de cardiologia?", "quantos atendimentos estão contratados ao mês?". Sem filtro, retorna todas as especialidades ativas.

**Parâmetros:**
- `especialidade` (string, opcional)

**Query SQL:**
```sql
SELECT e.nome AS especialidade, cm.meta_mensal,
       cm.vigencia_inicio, cm.vigencia_fim
FROM contrato_metas cm
JOIN especialidades e ON e.id = cm.especialidade_id
WHERE e.ativo = 1
  AND cm.vigencia_inicio <= DATE('now')
  AND (cm.vigencia_fim IS NULL OR cm.vigencia_fim >= DATE('now'))
  AND (:especialidade_id IS NULL OR cm.especialidade_id = :especialidade_id)
ORDER BY e.nome
LIMIT 50
```

**Exemplo:**
```json
{"data": [{"especialidade": "Cardiologia", "meta_mensal": 200,
           "vigencia_inicio": "2026-01-01", "vigencia_fim": null}],
 "data_extracao_iso": "2026-04-25T03:14:00", "row_count": 1}
```

### 3. `query_ppi(mes, municipio=None)`

**Descrição:**
> Retorna a Programação Pactuada Integrada (PPI) — quantos atendimentos cada município tem direito por especialidade no mês. Use para "qual a cota de Banabuiú em março?", "quanto cada cidade tem programado?".

**Parâmetros:**
- `mes` (string, obrigatório): `YYYY-MM`
- `municipio` (string, opcional)

**Query SQL:**
```sql
SELECT m.nome AS municipio, e.nome AS especialidade,
       ppi.quantidade_programada
FROM ppi_mensal ppi
JOIN municipios m ON m.id = ppi.municipio_id
JOIN especialidades e ON e.id = ppi.especialidade_id
WHERE ppi.mes_referencia = :mes_ref
  AND (:municipio_id IS NULL OR ppi.municipio_id = :municipio_id)
ORDER BY m.nome, e.nome
LIMIT 200
```

### 4. `top_faltas(mes, n=3)`

**Descrição:**
> Retorna as N especialidades com maior número absoluto de faltas no mês informado, somando todos os municípios. Use para "onde estamos perdendo mais consultas?", "top 3 especialidades em falta de março".

**Parâmetros:**
- `mes` (string, obrigatório)
- `n` (int, opcional, default=3, máximo=10)

**Query SQL:**
```sql
SELECT e.nome AS especialidade,
       SUM(at.quantidade_falta) AS faltas_total,
       SUM(at.quantidade_atendida) AS atendido_total,
       ROUND(
         CAST(SUM(at.quantidade_falta) AS FLOAT) /
         NULLIF(SUM(at.quantidade_atendida + at.quantidade_falta), 0) * 100, 2
       ) AS pct_falta
FROM atendimentos at
JOIN especialidades e ON e.id = at.especialidade_id
WHERE at.mes_referencia = :mes_ref
GROUP BY e.nome
ORDER BY faltas_total DESC
LIMIT :n
```

### 5. `comparar_municipios(mes)`

**Descrição:**
> Retorna comparação entre os 12 municípios do consórcio no mês: total atendido, total faltas, % de utilização sobre PPI. Use para "qual cidade está usando mais?", "comparar municípios em fevereiro".

**Parâmetros:**
- `mes` (string, obrigatório)

**Query SQL:**
```sql
SELECT m.nome AS municipio,
       SUM(ppi.quantidade_programada) AS ppi_total,
       COALESCE(SUM(at.quantidade_atendida), 0) AS atendido_total,
       COALESCE(SUM(at.quantidade_falta), 0) AS faltas_total,
       ROUND(
         CAST(COALESCE(SUM(at.quantidade_atendida), 0) AS FLOAT) /
         NULLIF(SUM(ppi.quantidade_programada), 0) * 100, 2
       ) AS pct_uso_ppi
FROM municipios m
JOIN ppi_mensal ppi ON ppi.municipio_id = m.id AND ppi.mes_referencia = :mes_ref
LEFT JOIN atendimentos at
  ON at.municipio_id = m.id AND at.mes_referencia = :mes_ref
WHERE m.ativo = 1
GROUP BY m.nome
ORDER BY pct_uso_ppi DESC
LIMIT 20
```

## Fluxo de execução

```
[Telegram message in] chat_id=X, text="como está fevereiro?"
        │
        ▼
[Rate limit check] — 50 msgs/dia/chat_id (SQLite count em BotConversa)
   ├── excedeu → resposta "Limite diário atingido. Tente amanhã." [STOP]
        │
        ▼
[Load history] — últimas 6 mensagens (3 turnos) de BotConversa para chat_id
        │
        ▼
[Anthropic call #1] system + history + new_message + tools=[5 tools]
        │
        ▼
[Response.stop_reason]
   ├── "end_turn" sem tool_use → resposta direta (raro, geralmente saudação)
   ├── "tool_use" → executa tool localmente
   │       │
   │       ▼
   │    [Tool router] valida params (mes regex, n ≤ 10, etc.)
   │       ├── inválido → tool_result com {"error": "..."} → loop
   │       └── válido → resolve nomes → IDs (lookup) → executa SQL
   │              │
   │              ▼
   │       [SQL execute via SQLAlchemy] timeout 5s
   │              ├── erro/timeout → tool_result {"error": "db_error"}
   │              ├── 0 rows → tool_result {"data": [], "row_count": 0, ...}
   │              └── ok → tool_result {"data": [...], "data_extracao_iso": "..."}
   │       │
   │       ▼
   │    [Anthropic call #2] com tool_result anexado
   │       │
   │       ▼
   │    [Itera até stop_reason="end_turn" OU 3 iterações OU 1000 tokens output]
        │
        ▼
[Persist BotConversa] — pergunta, resposta, tokens, custo, latência
        │
        ▼
[Telegram reply] texto formatado
```

## Fallback strategy

A resposta de fallback **canônica** é:

> "Não consegui consultar os dados agora. Consulte o painel: https://cpsmq.local/dashboard"

Acionada quando:
1. Tool retorna `{"error": ...}` (erro de DB, timeout, parâmetro irresolúvel após 1 retry).
2. Loop de tool calling atinge 3 iterações sem `end_turn`.
3. Resposta excede 1000 tokens output (truncada e substituída).
4. Exceção não tratada no handler (capturada no `try/except` raiz).
5. `BotConversa.count_today(chat_id)` ≥ 50 (rate limit) — mensagem ligeiramente diferente: "Limite diário atingido. Tente amanhã."

Quando o modelo **hesita** (perguntas ambíguas), ele é instruído pelo system prompt a **pedir esclarecimento** em vez de cair no fallback. Fallback é para falha técnica, não para ambiguidade.

## Hard limits

| Limite | Valor | Enforcement |
|---|---|---|
| Tokens input/chamada | 4000 | `max_tokens` no SDK + truncar histórico |
| Tokens output/resposta | 1000 | `max_tokens=1000` + verificação pós-resposta |
| Iterações de tool calling | 3 | Contador no loop; ao atingir, força fallback |
| Mensagens/dia/chat_id | 50 | `SELECT COUNT(*) FROM bot_conversas WHERE telegram_chat_id=? AND date(created_at)=date('now')` |
| Timeout SQL | 5s | `connect_args={"timeout": 5}` no engine SQLAlchemy |
| Timeout Anthropic | 30s | `client.with_options(timeout=30.0)` |
| Custo diário projetado | <$1.70/dia | Monitor: alertar Telegram admin se BotConversa.SUM(custo_usd) > $40 mês |

**Proteção contra loop:** o handler mantém `iteration_count = 0`; cada `tool_use` incrementa; ao chegar em 3, o próximo turno **não envia** tools, força `end_turn` e, se ainda assim tiver tool_use, retorna fallback.

## Multi-turn

Histórico mantido nas últimas **3 trocas (6 mensagens)** por `telegram_chat_id`, lidas de `BotConversa` ordenadas `created_at DESC LIMIT 6` e injetadas como mensagens user/assistant alternadas antes da pergunta atual.

**Por quê 3 trocas:**
- Suficiente para "e em março?" depois de "como foi fevereiro?"
- Limita crescimento de contexto: ~600 tokens extra max
- Histórico mais antigo é descartado — não há "memória" de longo prazo no bot (gestor não precisa)

**Limpeza:** sem retenção infinita. Janitor noturno (rotina diária separada) deleta `bot_conversas` com mais de 30 dias para controle de tamanho do DB e LGPD-compliance.

## Confidence threshold

Claude não tem confidence score nativo. Substituímos por **regras heurísticas** aplicadas ao output e enforced pelo system prompt:

1. **Pergunta ambígua** (sem mês explícito e contexto histórico não resolve) → modelo é instruído a perguntar "Qual mês?" antes de chamar tool.
2. **Tool retorna `row_count = 0`** → resposta obrigatória "Não há dados para o período/parâmetros informados." (não pode haver criatividade).
3. **Modelo tenta responder número sem ter chamado tool no turno** → Não há enforcement programático possível (modelo é livre para gerar texto). **Mitigação:** system prompt regra #1 + auditoria periódica via `BotConversa.resposta` (Bolt cria script de spot-check semanal que sample 20 conversas e marca suspeitas para review humana).
4. **Resposta sem "Dados extraídos em"** → post-processor regex valida a presença da string `Dados extraídos em \d{2}/\d{2}/\d{4}` no final. Se ausente, anexa automaticamente usando a `data_extracao_iso` da última tool chamada no turno. Se nenhuma tool foi chamada, substitui resposta inteira por fallback.

## O que NÃO fazer

1. ❌ **NÃO** permitir que o modelo gere SQL — nem mesmo SQL "de exemplo" em respostas. O system prompt proíbe explicitamente.
2. ❌ **NÃO** usar embeddings/RAG sobre os dados numéricos. Tool calling é deterministicamente correto; embedding introduz aproximação.
3. ❌ **NÃO** usar string formatting (f-strings, %, .format) para montar SQL com parâmetros do usuário. Apenas bind parameters via SQLAlchemy `text(...).bindparams(...)` ou ORM.
4. ❌ **NÃO** responder números sem citar `data_extracao`. Sem fonte = bot vira boato.
5. ❌ **NÃO** deixar o modelo "completar lacunas" quando tool retorna vazio. Resposta vazia = "não há dados", literal.
6. ❌ **NÃO** estimar tendências fora do que veio da tool. "Provavelmente em abril..." é proibido.
7. ❌ **NÃO** dar conselho clínico, político ou jurídico. Só números do consórcio.
8. ❌ **NÃO** confiar em fuzzy matching de nomes. Match exato (com normalização de acentos/case) → se falha, modelo pergunta de volta.
9. ❌ **NÃO** logar a chave da Anthropic ou o token do Telegram em `BotConversa` ou logs.
10. ❌ **NÃO** fazer streaming de resposta. Resposta bloqueante simplifica o post-processing (validação da assinatura "Dados extraídos em").

## Consequências

### Positivas
- Determinismo: mesma pergunta → mesma SQL → mesmo número.
- Auditável: `BotConversa` registra pergunta, resposta, tokens, custo. Spot-check semanal viável.
- Custo previsível: ~$0.005-0.02 por interação típica → ~$30-45/mês a 50 chats/dia.
- Sem SQL injection: parâmetros do usuário nunca tocam string SQL.
- Fácil expandir: adicionar tool = adicionar função Python + entrada no array de tools. System prompt não muda.

### Negativas / Riscos residuais
- **Risco 1: modelo alucina texto não-numérico.** Mitigação: system prompt + validação de assinatura "Dados extraídos em" + spot-check semanal.
- **Risco 2: ambiguidade de nome de município/especialidade.** Mitigação: lookup exato com normalização; se falha, modelo pergunta. Ainda assim, "Quixadá" vs "Quixeramobim" pode confundir o modelo na escolha do parâmetro — mitigado por descrição clara da tool.
- **Risco 3: consultas que combinam dados de tools diferentes** (ex: "compare meta com PPI"). Modelo terá que fazer tool calling encadeado dentro do limite de 3 iterações. Se exceder, fallback. Aceito como tradeoff.
- **Risco 4: rate limit por chat_id permite spam de outros usuários se conta Telegram for compartilhada.** Mitigação fora do escopo desta ADR — controle de acesso ao bot via allowlist de `chat_id` é responsabilidade do handler de autenticação (F3-02).
- **Risco 5: latência alta em tool calling (2 chamadas Anthropic + SQL).** Esperado: 3-6s por resposta. Aceitável para uso em celular em reuniões.

### Tradeoffs explícitos
| Escolha | Sacrifica | Por quê vale |
|---|---|---|
| Tool calling fechado vs SQL livre | Flexibilidade — perguntas exóticas caem no fallback | Risco numérico é maior que custo de cobertura imperfeita |
| Sonnet 4.6 vs Haiku | Custo (~5x mais caro) | Tool selection mais confiável; orçamento de $50/mês comporta |
| 3 iterações max | Perguntas multi-step sofisticadas | Proteção contra loops e blowup de custo |
| Sem streaming | UX (~2s a mais de espera percebida) | Validação de assinatura "Dados extraídos em" precisa do output completo |
| Histórico de 6 msgs | Contexto longo | Tokens previsíveis; gestor faz perguntas curtas e independentes |

## Implementação (para o Bolt)

**Arquivo a criar:** `/home/evonexus/evo-projects/cpsmq/backend/bot/ai_handler.py`

**Assinatura pública:**
```python
class AIHandler:
    def __init__(self, db_session_factory, anthropic_client, model="claude-sonnet-4-6"):
        ...

    async def handle_message(self, chat_id: str, user_text: str) -> str:
        """
        Returns: resposta formatada em pt-BR pronta pra enviar ao Telegram.
        Side effects: persiste 1 row em BotConversa.
        Raises: nunca — todo erro vira string de fallback.
        """
        ...
```

**Estrutura interna:**
```
backend/bot/
├── ai_handler.py          # AIHandler class (orquestra)
├── tools/
│   ├── __init__.py        # TOOLS = [...] lista para Anthropic
│   ├── base.py            # ToolResult dataclass; helpers comuns
│   ├── consolidado.py     # query_consolidado()
│   ├── meta_contrato.py   # query_meta_contrato()
│   ├── ppi.py             # query_ppi()
│   ├── top_faltas.py      # top_faltas()
│   └── comparar.py        # comparar_municipios()
├── lookups.py             # _resolve_municipio, _resolve_especialidade (com normalização)
├── prompts.py             # SYSTEM_PROMPT constante
├── limits.py              # rate_limit_check, count_today
└── post_process.py        # validate_extraction_signature, append_signature_if_missing
```

**Tests obrigatórios** (Grid escreve, Bolt implementa):
- `test_query_consolidado_zero_rows_returns_empty_with_signature`
- `test_query_consolidado_with_municipio_filter`
- `test_resolve_municipio_normalizes_accents` (Quixada == Quixadá)
- `test_rate_limit_enforces_50_per_chat_per_day`
- `test_loop_breaks_at_3_iterations`
- `test_response_without_signature_gets_signature_appended`
- `test_response_without_tool_call_falls_back`
- `test_sql_injection_attempt_in_municipio_param_does_not_execute` (param: `'; DROP TABLE atendimentos;--`)

**Handoff:**
- Após esta ADR, **@compass-planner** decompõe em plano de 5-7 steps (criar tools dir, criar lookups, criar handler, escrever testes, integrar no telegram_bot.py existente, smoke test, documentar no README do projeto).
- **@grid-tester** escreve a suite de testes com fixtures determinísticas antes de **@bolt-executor** implementar.
- **@oath-verifier** valida no final: roda testes, verifica que system prompt no código é exatamente o desta ADR, confere hard limits configurados, executa 5 perguntas-canário e revisa BotConversa.

## Referências
- `backend/models.py:23-150` — schema das tabelas usadas pelas tools
- `backend/routers/consolidado.py:25-129` — query SQLAlchemy do consolidado (base para `query_consolidado`)
- `backend/models.py:153-165` — BotConversa (auditoria + rate limit)
- `backend/models.py:92-105` — Extracao (fonte do `data_extracao_iso`)
