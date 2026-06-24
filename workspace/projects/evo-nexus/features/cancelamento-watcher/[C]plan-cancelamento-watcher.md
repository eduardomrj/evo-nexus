---
author: claude
agent: compass-planner
type: work-plan
date: 2026-06-18
plan-name: cancelamento-watcher
project: evo-nexus
status: draft
mode: direct
ticket: ed442230-1bf4-4212-9cb0-ea91d74724c3
---

# Work Plan — Cancelamento Watcher

## Context

Heartbeat de 30 min que monitora a caixa `cancelamento@automacaosoftware.com.br` (Zoho),
delega a triagem ao `custom-legal-clients` (Via B), notifica o Discord `1516147962391171122`
e abre ticket interno de alta prioridade. Deriva do PRD `[C]prd-cancelamento-watcher.md` e da
gap analysis do Echo (R-01..R-07). Decisões D-01..D-06 já fechadas por Eduardo.

## Objectives

- Detectar e triar automaticamente cada email novo de cancelamento, sem re-notificar antigos.
- Resumo jurídico/risco no Discord + ticket interno por cancelamento.
- Custo zero de LLM quando não há nada novo; nunca falhar silenciosamente.

## Guardrails

### Must Have
- Dedup por `processed.json` no MVP (R-01/R-02); marca o messageId **apenas após sucesso**.
- Orquestrador faz todo o I/O; `custom-legal-clients` **só interpreta texto** (Via B, R-04).
- Corpo do email tratado como **dado entre delimitadores**, nunca como instrução (R-06).
- Skip sem custo de LLM quando não há email novo (AC-05/D-06).
- Falha (Zoho/Discord/I-O) → alerta no Discord, não silenciosa (R-03/R-06).
- Notificação limitada a: cliente, nº contrato, motivo, classificação de risco (R-07).
- Convenção de projetos: dados em `/home/evonexus/evo-projects/cancelamento-watcher/`,
  código em `ADWs/routines/evo-projects/cancelamento-watcher.py`.

### Must NOT Have
- Sem "mark as read" no Zoho (não suportado — dedup é por JSON).
- Sem resposta automática ao cliente; sem ação contratual/retenção automatizada.
- Sem anexos/PDF na notificação; sem corpo completo do email em Discord/ticket.
- Sem alteração no runtime/plugin oficial do Discord (escopo protegido — CLAUDE.md).

## Task Flow

```
Step 1 (pré-req manual: alias Zoho + pasta + PATH)
        ↓
Step 2 (criar agente orquestrador custom-cancelamento-watcher)
        ↓
Step 3 (script: poll Zoho + dedup JSON + delegação legal-clients)
        ↓
Step 4 (notificação Discord + criação de ticket + alerta de falha)
        ↓
Step 5 (registrar heartbeat em heartbeats.yaml + smoke test)
```

## Detailed TODOs

### Step 1 — Pré-requisitos (alias Zoho + pasta de projeto + PATH do scheduler)
- **What:**
  - Criar o alias `cancelamento@automacaosoftware.com.br` no Zoho Mail (account `4128168000000008002`) — **manual, Eduardo** (D-03).
  - Criar `/home/evonexus/evo-projects/cancelamento-watcher/{logs,reports,src}` e `processed.json` inicial (`{"processed": []}`).
  - Verificar `which claude` no ambiente do scheduler (R-05); se ausente, registrar caminho absoluto a usar no runner/PATH.
  - Confirmar `DISCORD_BOT_TOKEN` no `.env` (já confirmado) e que `from dashboard.backend.sdk_client import evo` resolve.
- **Owner agent:** manual (Eduardo) para o alias Zoho; @bolt-executor para pasta/verificações.
- **Acceptance criteria:** alias recebe emails de teste; pasta + `processed.json` existem; `which claude` retorna um path; EvoClient importável.
- **Dependências:** nenhuma.
- **Riscos:** R-03 (alias inexistente bloqueia smoke real), R-05 (PATH).
- **Estimated complexity:** LOW

### Step 2 — Criar agente orquestrador `custom-cancelamento-watcher`
- **What:** criar `.claude/agents/custom-cancelamento-watcher.md` com frontmatter
  `tools: Bash, Read, Write, Glob, Grep, Agent, Skill` (verificado: `heartbeat_runner.py:264-266`
  passa essa linha como `--allowedTools`; sem ela, o default não inclui Agent/Skill e a Via B quebra).
  Persona: lê Zoho, aplica dedup, delega ao `custom-legal-clients` via Agent tool, dispara o script de
  notificação/ticket. Inclui o **schema de saída** que o legal-clients deve produzir (cliente, nº contrato,
  motivo, pedido, risco, próximos passos) e a regra de tratar o corpo como dado (R-06).
  Criar também `.claude/commands/custom-cancelamento-watcher.md`.
- **Owner agent:** @bolt-executor.
- **Acceptance criteria:** `_parse_agent_tools("custom-cancelamento-watcher")` retorna os 7 tools;
  invocar o agente manualmente faz uma delegação válida ao legal-clients.
- **Dependências:** Step 1.
- **Riscos:** R-04 (se o frontmatter de tools estiver errado, Agent tool indisponível).
- **Estimated complexity:** MEDIUM

### Step 3 — Script de polling: leitura Zoho + dedup JSON + delegação
- **What:** criar `ADWs/routines/evo-projects/cancelamento-watcher.py` com:
  - leitura via Zoho Mail client (`zoho_mail_client.py`, comandos `inbox`/`search`, account `4128168000000008002`);
  - filtro por destinatário `cancelamento@` (no código, já que não há filtro nativo) e dedup contra `processed.json`;
  - se nada novo → retorna estrutura de `skip` **sem** chamar LLM (D-06/AC-05);
  - para cada email novo, expõe o texto (entre delimitadores) para o orquestrador delegar ao legal-clients;
  - escrita atômica do `processed.json` (tmp+rename) **somente após** notificação+ticket OK (R-01/R-02/R-06).
- **Owner agent:** @bolt-executor.
- **Acceptance criteria (AC-01/02/03/05):** email novo é detectado; email repetido é ignorado;
  delegação produz resumo estruturado; sem email novo não há custo de LLM.
- **Dependências:** Steps 1, 2.
- **Riscos:** R-01, R-02, R-06; parsing frágil do `read` do Zoho.
- **Estimated complexity:** HIGH

### Step 4 — Notificação Discord + criação de ticket + alerta de falha
- **What:** no script (ou módulo `src/`):
  - enviar resumo ao Discord `1516147962391171122` (skill `discord-send-message` ou curl API v10 com `DISCORD_BOT_TOKEN`), limitado aos campos de R-07;
  - criar ticket via `evo.post("/api/tickets", {title, description, priority:"high", assignee_agent:"custom-legal-clients"})` (D-05/AC-07);
  - envelopar Zoho/Discord/ticket em try/except: em falha → mensagem de alerta no mesmo canal e **não** marcar o messageId como processado (RF-06/AC-06).
- **Owner agent:** @bolt-executor.
- **Acceptance criteria (AC-04/06/07):** mensagem chega no canal com os 4 campos mínimos;
  ticket criado com priority high + assignee correto; falha forçada (token inválido) gera alerta no Discord.
- **Dependências:** Step 3.
- **Riscos:** R-03, R-07; ordem de operações (marcar processado só no fim).
- **Estimated complexity:** MEDIUM

### Step 5 — Registrar heartbeat + smoke test
- **What:** adicionar entrada em `config/heartbeats.yaml`:
  `id: cancelamento-watcher-30m`, `agent: custom-cancelamento-watcher`, `interval_seconds: 1800`,
  `wake_triggers: [interval, manual]`, `required_secrets: [DISCORD_BOT_TOKEN]`, `enabled: false` (ligar só após smoke),
  `decision_prompt` que instrui: checar Zoho+dedup; se nada novo `{"action":"skip"}`; se há novo, processar e responder `{"action":"work", ...}`.
  Smoke: enviar email de teste ao alias, rodar `POST /api/heartbeats/{id}/run` (ou `make`), verificar Discord+ticket+`processed.json`; rodar de novo e confirmar dedup (sem re-notificar).
- **Owner agent:** @bolt-executor (+ @oath-verifier para a verificação).
- **Acceptance criteria:** smoke cobre AC-01..AC-07; segundo run confirma AC-02 e AC-05; após PASS, `enabled: true`.
- **Dependências:** Steps 1-4 (alias Zoho do Step 1 é bloqueante para smoke real).
- **Riscos:** R-05 (PATH no scheduler), R-03 (alias).
- **Estimated complexity:** LOW

## Success Criteria
- [ ] Email novo no alias → Discord + ticket high/legal-clients (AC-01, AC-03, AC-04, AC-07)
- [ ] Segundo ciclo não re-notifica o mesmo email (AC-02)
- [ ] Ciclo sem email novo faz skip sem custo de LLM (AC-05)
- [ ] Falha de Zoho/Discord gera alerta no Discord; messageId não marcado (AC-06)
- [ ] Notificação contém só cliente, nº contrato, motivo, risco (R-07)
- [ ] Orquestrador delega; legal-clients não executa Bash/escrita (Via B, R-04)

## Open Questions
- [ ] OQ-1 — Filtro por destinatário: o alias entrega na mesma INBOX da conta? Se sim, o filtro
  `to == cancelamento@` precisa ser confiável no payload do `read`. Validar no smoke (Step 5). — Risk: med
- [ ] OQ-2 — `claude` no PATH do scheduler (R-05): confirmar no Step 1 se precisa de caminho absoluto
  no runner. — Risk: med
- [ ] OQ-3 — Política de retenção do `processed.json`: cresce indefinidamente? Definir poda (ex: manter
  90 dias) — não bloqueia MVP. — Risk: low

## Handoff
- **Next agent:** @apex-architect (Fase 3 — ADR curto sobre Via B vs handler in-process e contrato
  orquestrador↔legal-clients), depois @bolt-executor (Fase 4).
- **Atalho:** se Eduardo dispensar o ADR, handoff direto @bolt-executor a partir do Step 1.
- **Next skill:** dev-verify (definir evidências do smoke no Step 5).
