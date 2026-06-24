---
author: claude
agent: compass-planner
type: prd
date: 2026-06-18
feature: cancelamento-watcher
project: evo-nexus
status: draft
ticket: ed442230-1bf4-4212-9cb0-ea91d74724c3
---

# PRD — Cancelamento Watcher

## Contexto

A Automação Software recebe solicitações de cancelamento de contrato por email em
`cancelamento@automacaosoftware.com.br` (Zoho Mail). Hoje essas mensagens dependem de
checagem manual da caixa, sem triagem jurídica nem rastreabilidade. Cancelamentos são
eventos de alto valor (risco de churn, implicações contratuais/LGPD, prazos) e não podem
ficar parados numa inbox.

A feature é um **heartbeat** que roda a cada 30 minutos, detecta emails novos de
cancelamento, aciona o agente `custom-legal-clients` para interpretar a solicitação,
notifica o canal Discord `1516147962391171122` e abre um ticket interno de alta prioridade.

## Problema

- Emails de cancelamento ficam invisíveis até alguém abrir a caixa manualmente.
- Não há triagem jurídica/risco estruturada nem registro persistente (ticket) do evento.
- Sem rastreabilidade: não dá pra saber se uma solicitação foi vista, classificada ou tratada.
- O Zoho Mail client disponível **não tem "mark as read"** nem filtro nativo por destinatário,
  então qualquer solução ingênua re-notificaria os mesmos emails a cada ciclo.

## Solução

Heartbeat `cancelamento-watcher-30m` que executa um **agente orquestrador**
(`custom-cancelamento-watcher`, Via B / decisão D-01). A cada ciclo o orquestrador:

1. Lê emails da caixa `cancelamento@` via Zoho Mail client (account `4128168000000008002`).
2. Aplica **dedup por arquivo JSON** de `messageId` já processados (D-02), em
   `/home/evonexus/evo-projects/cancelamento-watcher/processed.json`.
3. Para cada email novo, **delega ao `custom-legal-clients` via Agent tool** o texto do email
   (entre aspas, como dado não-confiável — R-06) para produzir resumo estruturado:
   cliente, nº de contrato, motivo, pedido, classificação de risco, próximos passos (D-04).
4. **Notifica o Discord** `1516147962391171122` com o resumo (mínimo de dados sensíveis — R-07).
5. **Cria um ticket interno** (assignee `custom-legal-clients`, priority `high`) via EvoClient (D-05).
6. **Registra o messageId** como processado e, em caso de falha (token Zoho / Discord 4xx),
   **alerta no Discord** — nunca falha silenciosamente (R-03, R-06).

**Por que Via B:** o `custom-legal-clients` tem guardrails de escopo e pode recusar Bash/escrita
de estado (R-04). Isolando — orquestrador faz I/O (Zoho, JSON, Discord, ticket), legal-clients
apenas **interpreta texto** — cada agente atua dentro do seu papel.

## Requisitos funcionais (Given/When/Then)

- **RF-01 (AC-01):** Dado um email novo em `cancelamento@`, quando o heartbeat roda, então o
  orquestrador detecta o email (via leitura da caixa + comparação com `processed.json`).
- **RF-02 (AC-02):** Dado um email cujo `messageId` já consta em `processed.json`, quando o
  heartbeat roda de novo, então **não re-notifica** e **não delega** para o legal-clients.
- **RF-03 (AC-03):** Dado um email de cancelamento, quando processado, então o `custom-legal-clients`
  produz um resumo estruturado contendo, no mínimo: cliente, nº de contrato, motivo, pedido e
  classificação de risco.
- **RF-04 (AC-04):** Dado o resumo pronto, quando a notificação é enviada, então uma mensagem
  chega no canal Discord `1516147962391171122` com o resumo completo, **sem dados sensíveis além
  do mínimo** (nome do cliente, nº de contrato, motivo, classificação de risco).
- **RF-05 (AC-05):** Dado que não há email novo, quando o heartbeat roda, então faz **skip** — sem
  notificação e **sem custo de LLM** (a delegação ao legal-clients só ocorre se há email novo).
- **RF-06 (AC-06):** Dada uma falha (token Zoho expirado, Discord 4xx, erro de I/O), quando ocorre,
  então o evento é **registrado e alertado no Discord** — nunca falha silenciosamente; o messageId
  **não** é marcado como processado se a notificação/ticket não foi concluída.
- **RF-07 (AC-07):** Dado um email processado com sucesso, quando concluído, então um ticket é
  criado no sistema interno do EvoNexus com `priority: high` e `assignee_agent: custom-legal-clients`.

## Não-escopo

- Criar o alias `cancelamento@automacaosoftware.com.br` no Zoho (pré-requisito manual — D-03).
- "Mark as read" no Zoho (o client não suporta; dedup é por JSON).
- Resposta automática ao cliente que pediu o cancelamento (apenas triagem interna).
- Retenção/contra-oferta automatizada ou qualquer ação contratual — só notifica e abre ticket.
- Anexar PDFs/contratos do email à notificação (somente texto/resumo no MVP).
- Persistir o corpo completo do email em ticket/Discord (R-07 — mínimo de dados sensíveis).
- Atualização automática de status do ticket após criação.

## Riscos

| # | Sev | Risco | Mitigação no plano |
|---|-----|-------|--------------------|
| R-01 | Alto | Sem dedup, cada ciclo re-notifica emails antigos | `processed.json` é parte do MVP (Step 3); só marca após sucesso |
| R-02 | Alto | Depender de `unread` como única fonte é frágil | Fonte da verdade é a lista de `messageId` em JSON, não o flag unread |
| R-03 | Médio | Token Zoho expira silenciosamente no scheduler | Try/except em torno da leitura Zoho → alerta no Discord (RF-06) |
| R-04 | Médio | `custom-legal-clients` pode recusar Bash/escrita | Via B: legal-clients só interpreta texto; orquestrador faz todo I/O |
| R-05 | Médio | `claude` pode não estar no PATH do scheduler | Step 1 verifica `which claude` no ambiente do scheduler |
| R-06 | Médio | Corpo do email é conteúdo não-confiável (prompt injection) | Texto passado entre delimitadores/aspas como **dado**, nunca instrução |
| R-07 | Médio | Notificação Discord pode vazar dados sensíveis | Resumo limitado a: cliente, nº contrato, motivo, classificação de risco |

## Decisões de design

| # | Decisão | Implicação |
|---|---------|------------|
| D-01 | Arquitetura Via B (orquestrador delega ao legal-clients via Agent tool) | Orquestrador declara `tools: [Bash, Read, Write, Glob, Grep, Agent, Skill]` no frontmatter — o runner passa isso como `--allowedTools` (verificado em `heartbeat_runner.py:264-266`) |
| D-02 | Dedup via JSON em `/home/evonexus/evo-projects/cancelamento-watcher/processed.json` | Estrutura: `{ "processed": [{"id": "<messageId>", "ts": "<iso>"}] }`; escrita atômica (tmp+rename) |
| D-03 | Criar alias `cancelamento@` no Zoho (account `4128168000000008002`) | Pré-requisito **manual** — bloqueia smoke test real (Step 5) |
| D-04 | Notificação completa: resumo + risco + próximos passos | Schema de saída do legal-clients fixado no prompt do orquestrador |
| D-05 | Criar ticket automaticamente por cancelamento | `evo.post("/api/tickets", {priority: high, assignee_agent: custom-legal-clients, ...})` |
| D-06 | Custo zero quando não há email novo (AC-05) | Orquestrador faz a checagem Zoho+dedup **antes** de qualquer chamada de LLM; se nada novo, retorna `{"action":"skip"}` |

## Acceptance criteria — rastreabilidade

| AC | RF | Verificado em |
|----|----|--------------|
| AC-01 | RF-01 | Step 3 + smoke test (Step 5) |
| AC-02 | RF-02 | Step 3 (dedup) |
| AC-03 | RF-03 | Step 3 (delegação) |
| AC-04 | RF-04 | Step 4 (Discord) |
| AC-05 | RF-05 | Step 2 (decision_prompt) + Step 3 |
| AC-06 | RF-06 | Step 3/4 (try/except + alerta) |
| AC-07 | RF-07 | Step 4 (ticket) |
