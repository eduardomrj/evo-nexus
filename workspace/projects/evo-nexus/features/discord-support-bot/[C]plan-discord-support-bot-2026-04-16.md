---
author: claude
agent: compass-planner
type: work-plan
date: 2026-04-16
plan-name: discord-support-bot
status: draft
mode: direct
---

# Work Plan — Bot Discord de Suporte Multi-Agente

## Context
A Automação Software opera um servidor Discord privado (equipe + parceiros) e quer um bot que responda automaticamente a dúvidas de suporte, produtos, contratos, pagamentos em atraso e liberação de licenças. O bot deve rotear cada pergunta para o agente correto (`@zara-cs`, `@flux-finance`, `@atlas-project`, `@lex-legal`, `@nova-product`) com base no papel (role) Discord do solicitante, consumindo dados reais do Asaas (pagamentos) e do sistema proprietário de licenças.

## Objectives
- Bot Python conectado ao Discord Gateway que escuta canais específicos e invoca o agente certo via Claude Code CLI.
- Controle de acesso por role Discord, configurável em YAML sem mudanças de código.
- Respostas contextualizadas com dados reais de Asaas (pagamentos) e sistema proprietário de licenças.
- Toda interação registrada como ticket no dashboard EvoNexus para rastreabilidade e observabilidade.
- Operação como serviço gerenciável via `make discord-support` / `make discord-support-stop`, com alertas de saúde para o `@pulse`.

## Guardrails

### Must Have
- **Servidor privado apenas** — o bot recusa qualquer mensagem fora do `DISCORD_GUILD_ID` do `.env`.
- **Autorização por role** — cada pergunta é avaliada contra o mapeamento role→agente antes de invocar Claude.
- **Timeout e circuit breaker** — invocação Claude tem `max_turns` e `timeout_seconds` limitados; falhas em sequência pausam o bot.
- **Auditoria** — cada interação gera um ticket no dashboard (`/api/tickets`) com request, resposta, agente, role, custo em tokens.
- **Segredos apenas em `.env`** — nenhum token/API key em código, YAML ou logs.
- **Resposta em pt-BR** — padrão do workspace (`CLAUDE.md`).

### Must NOT Have
- **Sem acesso público** — o bot não opera em DMs externas nem em servidores não autorizados.
- **Sem bypass de role** — se o role do solicitante não mapeia para agente algum, o bot recusa educadamente (não tenta adivinhar).
- **Sem liberação automática de licenças** — Fase 2 consulta e lista; liberação efetiva exige confirmação humana via approval (Fase 3 opcional).
- **Sem mocks em produção** — integrações Asaas e licenças devem hitar APIs reais em testes de homologação.
- **Sem escrever credenciais em tickets** — sanitizar qualquer payload antes de persistir.

## Task Flow

```
Fase 1 — Fundação                 Fase 2 — Dados                    Fase 3 — Operação
────────────────                  ──────────────                    ──────────────────
Step 1: estrutura bot  ────►     Step 4: Asaas client       ────►  Step 7: roles YAML runtime
Step 2: role→agent map ────►     Step 5: Licensing client   ────►  Step 8: tickets + pulse alerts
Step 3: Claude invoker ────►     Step 6: contexto no prompt ────►  Step 9: make + systemd/screen
```

## Detailed TODOs

---

### Step 1 — Estrutura do bot Discord (Fase 1)
- **Tipo:** [CONSTRUIR NOVO]
- **What:** criar `ADWs/discord_support/bot.py` usando `discord.py` (v2.x). Conectar ao gateway com `DISCORD_BOT_TOKEN`, validar `DISCORD_GUILD_ID`, escutar eventos `on_message` em canais listados em `config/discord_support.yaml`. Responder em thread (criar uma se não existir) para não poluir o canal.
- **Sub-steps:**
  1. Adicionar `discord.py>=2.3` ao `pyproject.toml` / `uv.lock`.
  2. Criar pacote `ADWs/discord_support/` com `__init__.py`, `bot.py`, `config.py`, `roles.py`, `invoker.py`.
  3. Implementar handler `on_ready` (log de guild conectada + membros) e `on_message` (filtro guild, filtro canal, filtro bot-próprio).
  4. Criar `config/discord_support.example.yaml` com estrutura (canais monitorados, roles→agentes, limites).
  5. Bootstrap: se `config/discord_support.yaml` não existir, copiar do example (padrão EvoNexus).
- **Owner agent:** `@bolt-executor`
- **Dependências:** nenhuma (token já no `.env`).
- **Riscos:** Gateway Intents — precisa habilitar "Message Content Intent" e "Server Members Intent" no Developer Portal do Discord (ação manual do Eduardo).
- **Acceptance criteria:** bot logado na guild, reage com ✓ (reação) a qualquer mensagem em canal monitorado sem responder ainda. Log em `workspace/ADWs/logs/discord_support/{YYYY-MM-DD}.jsonl`.
- **Estimated complexity:** MEDIUM

---

### Step 2 — Mapeamento Role → Agente (Fase 1)
- **Tipo:** [CONSTRUIR NOVO]
- **What:** implementar `roles.py` que lê `config/discord_support.yaml`, expõe `resolve_agent(member_roles, question_text) → (agent_slug, allowed: bool, reason)`. Roles Discord (ex.: `financeiro`, `suporte`, `parceiro`, `admin`) mapeiam para **conjunto de agentes permitidos** + um **classificador leve** que escolhe o agente dentro desse conjunto.
- **Sub-steps:**
  1. YAML schema: `roles: { financeiro: [flux-finance], suporte: [zara-cs, nova-product], parceiro: [atlas-project, zara-cs], admin: [all] }`.
  2. Classificador: primeira versão usa **regex/keywords** por agente (rápido, sem custo). Palavras-chave por agente ficam em `config/discord_support.yaml` (seção `routing.keywords`).
  3. Fallback: se a pergunta não bate com keyword E o role tem múltiplos agentes, pedir `@zara-cs` (triagem) como default.
  4. Se o role não mapeia para agente nenhum (ex.: role sem permissão), responder: _"Olá! Seu perfil atual não tem acesso ao suporte automatizado. Peça para um admin ajustar suas permissões."_
- **Owner agent:** `@bolt-executor`
- **Dependências:** Step 1.
- **Riscos:** usuários com múltiplos roles — definir regra de precedência (mais específico vence; explícita no YAML via `role_priority`).
- **Acceptance criteria:** testes unitários cobrindo: (a) role autorizado + keyword match → agente certo, (b) role autorizado sem keyword → fallback, (c) role não autorizado → mensagem de recusa, (d) múltiplos roles → precedência correta.
- **Estimated complexity:** MEDIUM

---

### Step 3 — Invoker do Claude Code CLI (Fase 1)
- **Tipo:** [CONSTRUIR NOVO]
- **What:** `invoker.py` chama `claude` CLI via `asyncio.create_subprocess_exec` com o agente escolhido (`/zara-cs`, `/flux-finance`, etc.), captura stdout, aplica `max_turns=6` e `timeout_seconds=90`. Retorna resposta formatada para Discord (respeitando limite de 2000 caracteres; usa embed ou thread para respostas longas).
- **Sub-steps:**
  1. Prompt montado: `identidade do solicitante + role + pergunta original + canal`.
  2. Subprocess: `claude -p "<prompt>" --agent <slug> --max-turns 6`.
  3. Capturar custo/tokens do output JSON (se disponível via `--output-format json`).
  4. Sanitização do output (remover blocos de código secretos se o agente expor algo sensível — lista negra configurável).
  5. Lidar com timeout graciosamente: postar _"Estou processando, demorou mais que o esperado. Um humano vai revisar."_ e criar ticket prioridade `high`.
- **Owner agent:** `@bolt-executor`
- **Dependências:** Steps 1 e 2.
- **Riscos:** custo descontrolado se o bot for spammado — rate limit por usuário (ex.: 5 perguntas/hora) em memória (Redis não é necessário na Fase 1).
- **Acceptance criteria:** fluxo E2E numa conta de teste: mensagem em canal monitorado → bot classifica → invoca agente certo → responde em thread em < 90s. Log da invocação no JSONL.
- **Estimated complexity:** HIGH

---

### Step 4 — Cliente Asaas para dados reais (Fase 2)
- **Tipo:** [ATIVAR]
- **What:** reutilizar a skill `int-asaas` já existente. Criar helper `ADWs/discord_support/integrations/asaas.py` que encapsula consultas que o bot usa com frequência: `get_payment_status(customer_email | cpf | asaas_id)`, `list_overdue_payments(customer_id)`, `get_next_invoice(customer_id)`.
- **Sub-steps:**
  1. Verificar se `int-asaas` expõe SDK Python utilizável via import (senão, criar wrapper HTTP fino direto com `requests` + `ASAAS_API_KEY`).
  2. Implementar 3 funções acima com cache em memória (TTL 60s) para reduzir custo e latência.
  3. Mapear identidade Discord → cliente Asaas: a opção mais simples é o solicitante mencionar o CPF/CNPJ/email na pergunta; alternativa é tabela `discord_customers` no dashboard DB (linka `discord_user_id` → `asaas_customer_id`). **[DECIDIR]** qual abordagem adotar.
  4. Retornar estrutura padronizada (`dict` com `status`, `valor`, `vencimento`, `link_pagamento`).
- **Owner agent:** `@bolt-executor` (com consulta a `@scout-explorer` para localizar código Asaas existente).
- **Dependências:** `ASAAS_API_KEY` no `.env` (já está).
- **Riscos:** LGPD — dados de pagamento expostos em canal visível a múltiplos membros. Mitigação: responder sempre em **thread privada** (membros não-mencionados não veem) OU via DM, configurável por role.
- **Acceptance criteria:** `@flux-finance` invocado pelo bot consegue responder "Qual o status do meu pagamento de abril?" com valor e vencimento reais do Asaas.
- **Estimated complexity:** MEDIUM

---

### Step 5 — Cliente do sistema de licenças (Fase 2)
- **Tipo:** [CONSTRUIR NOVO]
- **What:** criar `ADWs/discord_support/integrations/licensing.py` que conversa com a API REST proprietária de licenças. **[DECIDIR]** endpoint base, auth method (Bearer? API key? OAuth?), schema do recurso licença.
- **Sub-steps:**
  1. Entrevistar o time para obter OpenAPI/Postman/docs da API de licenças. Se não houver docs, invocar `@scroll-docs` para inspecionar via `WebFetch`/reverse engineering.
  2. Implementar funções: `get_license_status(customer_id)`, `list_licenses(customer_id)`, `request_license_release(customer_id, license_id, reason)` — **esta última apenas cria pedido; liberação real é humana (ver Fase 3)**.
  3. Tratamento de erros: timeout, 401/403, 404 (cliente não existe), 429 (rate limit).
  4. Adicionar variáveis ao `.env.example`: `LICENSING_API_URL`, `LICENSING_API_KEY`.
- **Owner agent:** `@bolt-executor` (com `@scroll-docs` para docs externos).
- **Dependências:** credenciais + URL da API de licenças (depende de decisão Eduardo).
- **Riscos:** API proprietária pode mudar sem aviso; adicionar testes de contrato executáveis manualmente (`make test-licensing-contract`).
- **Acceptance criteria:** `@atlas-project` consegue responder "Minha licença está ativa?" com dados reais (tipo, validade, features habilitadas).
- **Estimated complexity:** HIGH

---

### Step 6 — Injeção de contexto no prompt do agente (Fase 2)
- **Tipo:** [CONSTRUIR NOVO]
- **What:** antes de invocar Claude (Step 3), enriquecer o prompt com dados relevantes buscados em Asaas/Licensing. Implementar `context_builder.py` que decide **quais dados trazer** com base no agente escolhido (evita overfetching).
- **Sub-steps:**
  1. Regras por agente: `flux-finance` → puxa últimos 3 pagamentos do cliente; `atlas-project` → puxa licenças ativas; `zara-cs` → puxa ambos (triagem); `nova-product`, `lex-legal` → sem fetch (puro texto).
  2. Montagem do prompt: `## Contexto do Cliente\n{dados_json}\n\n## Pergunta do Membro\n{role}: {texto}`.
  3. Cache: chave `{customer_id}:{agent}:{data}`, TTL 60s, em memória (`functools.lru_cache` + TTL via `cachetools`).
  4. Se cliente não identificado, prompt fica sem contexto estruturado — Claude pede para o membro fornecer identificação.
- **Owner agent:** `@bolt-executor`
- **Dependências:** Steps 4 e 5.
- **Riscos:** vazamento de dados de cliente X ao membro Y se identificação falhar. Mitigação: validar que `discord_user_id` tem permissão de ver `customer_id` solicitado (checar tabela de mapeamento ou consentimento explícito).
- **Acceptance criteria:** resposta do bot para "Estou com pagamento em atraso?" inclui valor real e vencimento do Asaas, sem Claude ter inventado.
- **Estimated complexity:** MEDIUM

---

### Step 7 — Configuração de roles em runtime via YAML (Fase 3)
- **Tipo:** [CONSTRUIR NOVO]
- **What:** hot-reload do `config/discord_support.yaml` sem reiniciar o bot. Comando admin no Discord: `!reload-config` (restrito a role `admin`).
- **Sub-steps:**
  1. Usar `watchdog` para detectar mudança no arquivo OU comando slash `/reload-config` do Discord.
  2. Validar schema (via `pydantic` ou `jsonschema`) antes de aplicar; manter config anterior em memória em caso de erro.
  3. Logar diff aplicado (roles adicionados/removidos/alterados).
  4. Documentar no `CLAUDE.md` como adicionar novo role sem código.
- **Owner agent:** `@bolt-executor`
- **Dependências:** Step 2.
- **Riscos:** YAML malformado derruba o bot — por isso a validação antes de aplicar é obrigatória.
- **Acceptance criteria:** editar YAML, adicionar role novo "revenda" → `@flux-finance`, executar reload, membro com esse role consegue perguntar sobre pagamentos sem reiniciar o serviço.
- **Estimated complexity:** MEDIUM

---

### Step 8 — Tickets, observabilidade e alertas (Fase 3)
- **Tipo:** [ATIVAR]
- **What:** cada interação do bot cria/atualiza ticket no dashboard via `EvoClient` SDK. Alerta para `@pulse` em condições de saúde degradada.
- **Sub-steps:**
  1. `POST /api/tickets` ao receber mensagem: `title="Discord: {primeiros 60 chars}"`, `description`=pergunta completa, `assignee_agent=<resolvido>`, `priority=medium`, custom field `source=discord`.
  2. `POST /api/tickets/{id}/comments` com a resposta do bot (autor `agent:{slug}`) e um segundo comment com metadados (tokens, custo, latência).
  3. Status do ticket: `resolved` se Claude respondeu com sucesso, `review` se timeout/erro (humano precisa revisar), `blocked` se role não autorizado.
  4. Heartbeat health check: criar heartbeat `discord-support-health-15min` que lê os últimos 15min de `heartbeat_runs` / ticket activity e, se taxa de erro > 20%, gera ticket urgente para `@pulse-community`.
  5. Métricas expostas: total de perguntas/dia, por agente, por role, custo médio (consulta SQL simples em view `v_discord_support_daily`).
- **Owner agent:** `@bolt-executor` (código) + `@atlas-project` (definir KPIs).
- **Dependências:** `DASHBOARD_API_TOKEN` no `.env` (já está).
- **Riscos:** explosão de tickets — adicionar flag `auto_close_resolved_after: 7d` para não entupir o inbox.
- **Acceptance criteria:** rodar 5 perguntas de teste → 5 tickets no `/issues` do dashboard, cada um com timeline completa (pergunta, resposta, metadados).
- **Estimated complexity:** MEDIUM

---

### Step 9 — Make commands e gerenciamento de serviço (Fase 3)
- **Tipo:** [CONSTRUIR NOVO]
- **What:** adicionar ao `Makefile`:
  - `make discord-support` — inicia bot em `screen` ou `systemd` (consistente com `make telegram`).
  - `make discord-support-stop` — para o serviço.
  - `make discord-support-logs` — segue o JSONL + stderr.
  - `make discord-support-status` — health check (PID vivo + última interação no último 5min).
- **Sub-steps:**
  1. Escolher entre `screen` (simples, padrão Telegram) e `systemd` (mais robusto). **[DECIDIR]** — recomendação: iniciar com `screen` espelhando `make telegram` e migrar para `systemd` depois.
  2. Script wrapper: `scripts/discord_support_start.sh`, `scripts/discord_support_stop.sh`.
  3. PID lock file em `/tmp/discord_support.pid` com fluxo atômico (lição do `scheduler`: commit `0b051af`).
  4. Documentar em `.claude/rules/integrations.md` sob a seção "Servers e Infrastructure".
- **Owner agent:** `@bolt-executor` (com referência a `make telegram` como padrão).
- **Dependências:** Steps 1–8 todos funcionando em desenvolvimento.
- **Riscos:** processo zumbi após crash — PID lock atômico resolve (padrão já aplicado no scheduler).
- **Acceptance criteria:** `make discord-support` inicia, `make discord-support-status` retorna OK, `make discord-support-stop` encerra limpo; `ps aux` confirma processo único.
- **Estimated complexity:** LOW

---

## Success Criteria

### Fase 1 — Fundação
- [ ] Bot conectado ao Discord Gateway usando `DISCORD_BOT_TOKEN` do `.env`.
- [ ] Responde a mensagens em canais monitorados com o agente correto baseado no role do solicitante.
- [ ] YAML de mapeamento role→agente existe em `config/discord_support.yaml` com example rastreado em git.
- [ ] Logs JSONL em `workspace/ADWs/logs/discord_support/`.

### Fase 2 — Integrações
- [ ] `@flux-finance` invocado pelo bot responde status de pagamento real do Asaas.
- [ ] `@atlas-project` invocado pelo bot responde status real de licença via API proprietária.
- [ ] Contexto do cliente (pagamento/licença) é injetado no prompt apenas quando relevante ao agente.

### Fase 3 — Operação
- [ ] Toda interação vira ticket no dashboard com timeline completa.
- [ ] Reload de config sem restart do bot funciona.
- [ ] `make discord-support` / `make discord-support-stop` gerenciam o serviço com PID lock atômico.
- [ ] Heartbeat de saúde alerta `@pulse-community` quando taxa de erro > 20%.

---

## Open Questions

- [ ] **[DECIDIR] Mapeamento Discord → Cliente Asaas/Licensing** — usar (a) identificação explícita na pergunta (simples, exige usuário digitar CPF/email) ou (b) tabela `discord_customers` no DB (vincula `discord_user_id` → `asaas_customer_id` + `licensing_customer_id`, UX melhor mas exige cadastro prévio). Risco: LOW (começar com (a), migrar para (b) se volume justificar).
- [ ] **[DECIDIR] API de licenças** — endpoint base, método de auth, schema. Sem isso a Fase 2 não termina. Risco: HIGH (bloqueante para Step 5).
- [ ] **[DECIDIR] Privacidade das respostas financeiras** — thread pública no canal (visível a outros membros) ou DM sempre que dados sensíveis aparecerem? Risco: MEDIUM (LGPD).
- [ ] **[DECIDIR] Gerenciamento de serviço** — `screen` (padrão Telegram, simples) ou `systemd` (robusto, auto-restart)? Risco: LOW.
- [ ] **[DECIDIR] Liberação de licença via bot** — parar no "consultar e criar pedido" (Fase 2) ou incluir fluxo de approval no dashboard EvoNexus que dispara liberação real (Fase 3 estendida)? Risco: MEDIUM (controle financeiro/fraude).
- [ ] **[DECIDIR] Rate limit por usuário** — 5 perguntas/hora é apropriado? Ajustar conforme volume real observado na primeira semana. Risco: LOW.

Todas as perguntas acima serão anexadas ao `workspace/development/plans/[C]open-questions.md`.

---

## Handoff

### Sequência recomendada (fase-por-fase, não big-bang)

1. **Phase 3 — Solutioning** (antes de codar a Fase 1 do bot): `@apex-architect` produz ADR cobrindo:
   - Discord.py v2 vs alternativas (ex.: Pycord, Nextcord) — decisão.
   - Sync vs async em `on_message` (asyncio nativo, mas subprocess Claude é bloqueante → usar `asyncio.subprocess`).
   - Onde mora o mapeamento Discord→Customer (pergunta explícita ou tabela).

2. **Phase 3 — Review** pelo `@raven-critic`: risco LGPD (dados financeiros em canal), superfície de ataque (role escalation, command injection no prompt).

3. **Phase 4 — Build** com `@bolt-executor` executando Steps 1→3 (Fase 1), verificando E2E, depois Steps 4→6 (Fase 2), depois Steps 7→9 (Fase 3). Entre fases, **parar e validar com Eduardo**.

4. **Phase 5 — Verify** com `@oath-verifier`: evidência fresh de cada critério de sucesso por fase, especialmente teste de role escalation (membro sem role tenta perguntar sobre finanças).

5. **Phase 5 — Security** com `@vault-security`: audit OWASP focado em prompt injection, rate limiting, data leakage, token handling.

### Próximo passo imediato
- **Resolver as Open Questions marcadas [DECIDIR] acima** (em especial a API de licenças e privacidade LGPD).
- Com isso resolvido, `@apex-architect` produz ADR (Phase 3) e o plano avança para Build.

### Handoff target
- **Next agent:** `@apex-architect` (Phase 3 — Solutioning)
- **Next skill:** `dev-plan` (este plano) → `dev-plan` review → ADR
