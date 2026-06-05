# Open Questions — Plans Backlog

Perguntas abertas de planos ativos. Cada item traz: a pergunta, por que importa, e o risco.

---

## GO Payment Hub — Payment Products Matrix / PINPDV / SuperTEF — 2026-06-05

PRD: `/home/evonexus/evo-projects/go-control-erp/features/go-payment-hub/payment-products-matrix/[C]prd-payment-products-matrix.md`
Plano: `/home/evonexus/evo-projects/go-control-erp/features/go-payment-hub/payment-products-matrix/[C]plan-payment-products-matrix.md`

- [ ] **OQ-001** — Nome final das entidades: `ReceivingProduct`/`ReceivingEndpoint` ou `PaymentProduct`/`PaymentEndpoint`? — Afeta API, migrations e linguagem do domínio — Risk: med
- [ ] **OQ-002** — Migração por campos novos em `PaymentIntent` ou entidade nova `ProductIntent`? — Afeta compatibilidade e volume de refactor — Risk: high
- [ ] **OQ-003** — PINPDV callback/cancelamento/estorno: quais endpoints/status oficiais? — Evita implementar capability errada — Risk: high
- [ ] **OQ-004** — Voucher fica fora do MVP ou entra como produto desabilitado? — SuperTEF expõe voucher, mas PRD não oficializa — Risk: low/med
- [ ] **OQ-005** — SuperTEF `pos_id=null`/broadcast será permitido no MVP? — Pode causar captura no terminal errado — Risk: med
- [ ] **OQ-006** — Cartão online e cartão TEF são o mesmo produto com canais diferentes? — Afeta matriz e UX — Risk: med
- [ ] **OQ-007** — Pix Cobrança e Pix Instantâneo devem nascer separados desde a primeira migration? — Evita nova ambiguidade do `pix` legado — Risk: med
- [ ] **OQ-008** — Matriz e POS entram no Platform Admin central, no app GO Payment Hub ou ambos por perfil? — Afeta frontend e permissões — Risk: med

---

## Discord Plus — Isolamento CLI em cgroup (Fix 3 systemd-run) — Planning 2026-06-05

Plano: `/home/evonexus/evo-nexus/workspace/development/features/discord-plus-cli-process-isolation/[C]plan-discord-plus-cli-process-isolation.md`
PRD: `/home/evonexus/evo-nexus/workspace/development/features/discord-plus-cli-process-isolation/[C]prd-discord-plus-cli-process-isolation.md`

Consolida as questões do discovery (Echo). Recomendações de Planning entre colchetes; D1 é o bloqueante.

- [ ] **D1 (bloqueante)** — Spawn via `loginctl enable-linger` + `systemd-run --user --scope` [recomendado] vs `sudo systemd-run --scope`? — define segurança/herança/ciclo de vida — Risk: high — Owner: Eduardo + @custom-sysops
- [ ] **R10** — LXC unprivileged permite cgroup delegation para scopes filhos do user manager? — pré-requisito do mecanismo — Risk: med — Owner: @custom-sysops
- [ ] **D5** — `MemoryMax` por scope [sugestão 6G via env] + `maxSessions` coerente para não derrubar o LXC? — Risk: med — Owner: Eduardo
- [ ] **D6** — Re-aplicar namespaces (PrivateTmp/ProtectHome/ReadWritePaths) no scope ou aceitar FS do host/contexto do user? — Risk: med — Owner: @custom-sysops
- [ ] **D7/AC-7** — Texto exato da mensagem de OOM ao usuário do Discord — Risk: low — Owner: Eduardo/@nova-product

Resolvido em Planning (sem necessidade de decisão do usuário): classificação OOM antes da heurística max_turns [via `systemctl show Result=oom-kill`/exit 137]; env via `--setenv` por var; kill via `systemctl stop <unit>` com fallback `process.kill(-pid)`; limpeza via `--collect`; sem `RuntimeMaxSec` (mantém timeout do runner). Sudoers `NOPASSWD: ALL` → endurecer só se D1=sudo.

---

## GO Payment Hub — Cancel/Confirmar com Provider + Motivo + Timeline — 2026-06-04

Plano: `/home/evonexus/evo-projects/go-control-erp/features/go-payment-hub/[C]plan-cancel-confirm-with-provider.md`
PRD: `/home/evonexus/evo-projects/go-control-erp/features/go-payment-hub/[C]prd-cancel-confirm-with-provider.md`

- [ ] Asaas Pix dinâmico é cancelável via API (depende do status da chave)? — Define se `cancel_pix` é implementado ou fica fail-open — Risk: med
- [ ] Endpoint Asaas de cancelar boleto: `DELETE /v3/payments/{id}` vs `POST /v3/payments/{id}/cancel`? — Errar aqui pode estornar pago em vez de cancelar — Risk: med
- [ ] Operador da ação: usar `request.api_key.id` ou exigir usuário humano explícito? — Afeta o "quem" exibido na timeline — Risk: low

---

## Discord Plus modo híbrido C — 2026-05-30

Plano: `/home/evonexus/evo-nexus/workspace/development/plans/discord-plus-hybrid-cli-engine/[C]index-2026-05-30.md`
PRD: `/home/evonexus/evo-nexus/workspace/development/plans/discord-plus-hybrid-cli-engine/[C]prd-discord-plus-hybrid-cli-engine-2026-05-30.md`

- [ ] Quais flags públicas reais do `openclaude` suportam modo não interativo, agente e continuidade? — Define o contrato do runner CLI e evita depender de comportamento inventado — Risk: high
- [ ] A CLI retorna session id/continue token estável em stdout, arquivo de estado ou outro mecanismo público? — Define se haverá continuidade real cross-process por thread/canal — Risk: high
- [ ] O default de produção deve permanecer SDK até smoke real PASS, ou CLI pode ser default em ambiente controlado? — Afeta rollout e rollback operacional — Risk: med
- [ ] Qual formato mínimo de resposta CLI deve virar reply seguro quando não houver tool passiva? — Evita duplicidade ou postagem de texto indevido — Risk: med

---

## GO Control Auth (SSO Central) — 2026-05-28

Plano: `/home/evonexus/evo-projects/go-control-erp/features/go-control-auth/[C]plan-go-control-auth.md`
PRD: `/home/evonexus/evo-projects/go-control-erp/features/go-control-auth/[C]prd-go-control-auth.md`

Bloqueantes resolvidas:
- [x] Q1 — Modelo cross-domain: **code exchange** (TTL 60s, `POST /auth/redeem-code`)
- [x] Q2 — URLs do app: **reutilizar `Aplicativo.url_producao`/`url_developer`**; callback fixo `/auth/callback`; `AUTH_URL` no env
- [x] Q3 — `@gocontrol/shell` cobre **todos os 5 itens** (guard, perms, layout, api client, sessão)

Operacionais pendentes:
- [ ] Whitelist final do redirect (IDN homograph, path traversal, `data:`, `javascript:`) — Owner: Apex no ADR — Risk: high (segurança)
- [ ] UX para `is_platform_staff=True` no Auth V1: redirect simples para `platform.gocontrol.com.br` ou bloqueio? — Owner: Eduardo — Risk: low
- [ ] Catálogo exibe apps sem licença com upsell (Q4 do discovery)? — Afeta Step 5 — Risk: low
- [ ] Refresh token segue em `localStorage` no V1 (XSS blast radius preservado); migração HttpOnly cookie em V2 — Risk: aceito
- [ ] Porta do dev server do app `auth/` (sugestão: 5180) — Owner: Sysops — Risk: low
- [ ] Manifest do próprio Auth (ADR-004) — quem provisiona o `AplicativoServiceToken` do Auth? — Owner: Eduardo + Sysops — Risk: med
- [ ] `AUTH_URL` em dev: `localhost:5180` ou `auth.local.gocontrol.com.br` via /etc/hosts? — Owner: Sysops/DX — Risk: low

---

## GO Payment Hub — Platform Admin registration — 2026-05-28

Plano: `/home/evonexus/evo-projects/go-control-erp/features/go-payment-hub/[C]plan-payment-hub-platform-registration.md`

- [ ] URL prefix `/api/v1/go-payment-hub/` já está em `apps/core/middleware.py:APP_URL_MAP`? — Sem isso, `HasLicensedPermission` não consegue resolver `request.aplicativo_id` no Payment Hub — Risk: high
- [ ] O seed deve criar `Plano`s comerciais (starter/pro) ou deixar para staff cadastrar no Platform Admin? — Define se o app fica "vendável" no boot ou só visível para staff — Risk: med
- [ ] Defaults de cotas (`quota_pagamentos_mes=5000`, `quota_contas_bancarias=3`) batem com a expectativa comercial do MVP? — Afeta enforcement quando snapshot de licença começar — Risk: med
- [ ] `AppConfig.ready()` em produção: detecção `sys.argv[0]` cobre gunicorn/uwsgi sem disparar em `migrate`/`shell`? — Risco de push duplicado ou de não acontecer em prod — Risk: med
- [ ] Adicionar tela "Visão Geral" (`go-payment-hub.visao-geral`) agora ou em feature posterior? — Hoje `/` redireciona para `/bank-accounts`; seguir padrão do GO Message exigiria uma tela `/` real — Risk: low

---

## evonexus-discord-plus refactor sem perfis — 2026-05-26

Plano: `/home/evonexus/evo-nexus/workspace/development/plans/evonexus-discord-plus/[C]plan-refactor-sem-perfis-2026-05-26.md`

- [x] O runtime MCP fornece hoje um `user_id` real e confiável para cada tool-call, ou só temos `chat_id`? — **DECIDIDO:** sem `user_id` real confiável, deny-by-default. Não usar last-inbound actor/TTL no v2 inicial. — Risk: high
- [x] Operações sensíveis devem ser controladas por lista explícita por usuário/recurso (`allowedOperations`) ou por separação de listas (`allowedUserIds`, `allowedToolUserIds`, `permissionApproverUserIds` sem perfis)? — **DECIDIDO:** operações explícitas por usuário/recurso. — Risk: med
- [x] DMs continuam permitidas para usuários explicitamente allowlisted ou serão bloqueadas por padrão após remover perfis? — **DECIDIDO:** DMs bloqueadas por padrão, exceto usuários explicitamente listados em `dm.users`. — Risk: med

---

## Platform Notifications (Platform Admin + GO Account → GO Message) — 2026-05-25

Plano: `/home/evonexus/evo-projects/go-control-erp/features/platform-notifications/[C]plan-platform-notifications.md`
PRD: `/home/evonexus/evo-projects/go-control-erp/features/platform-notifications/[C]prd-platform-notifications.md`

- [ ] OQ1 — `user.invited`: gerar `temp_password` (8 chars random) ou usar `setup_link` único (token + escolher senha)? — Impacta segurança e UX do primeiro acesso — Risco: med
- [ ] OQ2 — `/forgot-password` precisa de captcha ou rate-limit 1/min por e-mail é suficiente? — Impacta abuso/anti-bot — Risco: low
- [ ] OQ3 — Se o operador desativa mapeamento de `auth.password_reset_requested`, o fluxo deve falhar 503 ou seguir silenciosamente? — Impacta usuário trancado fora — Risco: med
- [ ] OQ4 — `account.welcome` dispara para todos os usuários ou só owner? — Default proposto: só owner — Risco: low
- [ ] OQ5 — Onde armazenar `notifications.api_base_url` por ambiente? Hardcode ou ENV `NOTIFICATIONS_API_BASE`? — Impacta deploy multi-ambiente — Risco: low
- [ ] OQ6 — P1 (`licenca.expiring_7d`, `account.suspended`) entra nesta entrega ou vira PRD-2? — Impacta escopo Step 5 — Risco: low

---

## Discord OpenClaude Bridge v1.5 — 2026-05-22

Plano: `/home/evonexus/evo-nexus/workspace/development/plans/discord-openclaude-bridge-v1-5/[C]index-2026-05-22.md`

- [ ] A implementação de `bridge_reply` deve ser feature-flagada por env/config no primeiro deploy ou ativada diretamente na v1.5? — Impacta rollback operacional — Risco: med
- [ ] O `/last` deve mostrar apenas “entregue via bridge_reply” ou armazenar um resumo curto gerado pelo modelo? — Impacta utilidade de histórico sem reintroduzir payload longo — Risco: med
- [ ] O smoke live aprovado deve usar o projeto `cpsmq` e um prompt semelhante ao caso `487f6588-8a38-4622-820c-5090bddd0b3a`, ou um projeto sandbox? — Impacta segurança do teste em produção — Risco: med

---

## Plano Wizard (Platform Admin / GO Control) — 2026-05-22

Plano: `workspace/development/features/plano-wizard/[C]plan-plano-wizard.md`

- [ ] **Endpoint atômico (A) vs orquestração client (B) para criação de plano completo** — bloqueante para Step 3. Recomendação Compass: A. **Risco: MEDIUM**.
- [ ] **Storage do `valor` em `PlanoRecurso.params_default`** — chave `"valor"` no JSON existente vs novo campo. Recomendação: chave `"valor"`. **Risco: LOW**.
- [ ] **`ValueInput` polimórfico vs inputs inline por step** — Recomendação: wrapper. **Risco: LOW**.
- [ ] **Aplicar `editavel_na_criacao` no wizard de licença existente** — fora de escopo? Confirmar. **Risco: LOW** (feature paralela).
- [ ] **Remover `NovoPlanoSidebar` antigo neste ciclo?** — Recomendação Compass: manter como deprecated. **Risco: LOW**.

---

## Discord Support Bot — 2026-04-16

Plano: `workspace/development/plans/[C]plan-discord-support-bot-2026-04-16.md`

- [ ] **Mapeamento Discord → Cliente Asaas/Licensing** — (a) usuário digita CPF/email na pergunta vs (b) tabela `discord_customers` no DB. Importa para Steps 4, 5, 6. **Risco: LOW** (começar com (a), migrar depois).
- [ ] **API de licenças — endpoint base, auth method, schema** — bloqueante para Step 5. **Risco: HIGH**.
- [ ] **Privacidade em respostas financeiras** — thread pública no canal ou DM sempre? LGPD sensível. **Risco: MEDIUM**.
- [ ] **Gerenciamento do serviço** — `screen` (padrão Telegram) vs `systemd` (robusto). **Risco: LOW**.
- [ ] **Liberação de licença via bot** — só consulta/pedido (Fase 2) ou fluxo de approval no dashboard com execução real (Fase 3 estendida)? **Risco: MEDIUM**.
- [ ] **Rate limit por usuário** — 5 perguntas/hora é adequado? Ajustar após primeira semana. **Risco: LOW**.

---

## Migração MiniERP Adianti → Python+React (MIG-01) — 2026-05-06
**Origem:** `workspace/development/features/migracao-minierp-adianti-python-react/[C]discovery-migracao-minierp-adianti-python-react.md` (@echo-analyst)
**Endereçada para:** Eduardo (decisão) → @compass-planner / @apex-architect

### Bloqueio crítico (responder em 24h)
- [ ] **Escopo funcional do GO** — Quais módulos do legado o GO precisa replicar (Pessoas/Produtos/Vendas/Financeiro/Estoque/Produção/Expedição/CRM/SAC/Comunicação/Portal-cliente)?
- [ ] **Stack Python** — FastAPI / Django / Litestar? ORM? Auth (próprio, OIDC, Authlib)?
- [ ] **Stack React** — Vite puro / Next.js / Remix? UI lib (Mantine, MUI, Chakra, shadcn)? Forms (RHF+Zod)?
- [ ] **Multi-tenant?** Legado tem `system_unit` — GO mantém? Define `tenant_id` em quase toda tabela.

### Bloqueio alto (responder em 48h)
- [ ] **Migração de dados reais ou só estrutura?** GO arranca do zero ou importa dados existentes?
- [ ] **Integrações externas decididas** (Stripe? Asaas? Bling? Omie? Telegram? SMTP/SendGrid)?
- [ ] **Workflow de pedido** — replica matriz_estado_pedido_venda do legado ou redesenha?
- [ ] **Workflow de produção** — replica `is_start/is_work/is_paused/is_waiting/is_end`?
- [ ] **Notificações** — mantém design declarativo (template+channel+rule) ou event bus em código?

### Bloqueio médio (pode ser diferido para depois do piloto)
- [ ] Portal cliente público (`control/public/`+`publico/`) faz parte do GO?
- [ ] Mensageria interna + documentos (`control/communication/`) faz parte?
- [ ] Ouvidoria (`control/sac/`) faz parte?
- [ ] Logs do legado — replicar `system_change_log/access_log/sql_log` ou audit-log via SQLAlchemy events?
- [ ] 2FA — escopo do GO ou v2?
- [ ] Internacionalização — só pt-BR?
- [ ] Soft delete em todas as tabelas — manter `deleted_at`?

### Riscos não-funcionais
- [ ] Banco do GO já existe — conflito com 68 tabelas do legado? Schema separado, prefixo, rename?
- [ ] Volume de pedidos/contas/dia — define se denormalizações (`valor_total` em pedido) fazem sentido.
- [ ] LGPD — pessoa tem CPF/CNPJ + endereço; precisa campo de consentimento + exclusão sob demanda?
- [ ] Cobertura de testes — GO arranca com TDD? Legado não tem testes visíveis.

---

## Migração MiniERP — Piloto Pessoas+Produtos (MIG-01) — 2026-05-06
**Origem:** `workspace/development/features/migracao-minierp-adianti-python-react/[C]plan-migracao-minierp-adianti-python-react.md` (@compass-planner)
**Endereçada para:** Eduardo (decisão) → @apex-architect

### Bloqueante para Step 1 (RESOLVIDO em 2026-05-06 por Eduardo)
- [x] **OQ7** — Caminho do repo `go-control-erp/`. **DECIDIDO:** `/home/evonexus/evo-projects/go-control-erp/` (local na máquina, segue convenção CLAUDE.md de projetos customizados). Sem GitHub remoto definido neste momento.
- [x] **OQ1** — Tipo de PK: UUID v4 vs autoincremento. **DECIDIDO:** UUID v4 em todas as tabelas (catálogos globais, catálogos por empresa, domínio e cache). Alinhado com a recomendação Compass.
- [x] **OQ2** — Custom user model em `apps.accounts.User` desde o Step 1? **DECIDIDO:** SIM — `apps.accounts.User` configurado como `AUTH_USER_MODEL` desde o bootstrap, antes da primeira migration. Alinhado com a recomendação Compass.

### Não-bloqueantes (decidir antes do final do Step 2)
- [ ] **OQ3** — `tipo_cliente.sigla` (char(2)) — manter ou descartar? Recomendação Compass: descartar. — **Risco: LOW**.
- [ ] **OQ4** — Catálogos globais (`estado`, `cidade`, `unidade_medida`) recebem `created_at`/`updated_at`? Recomendação Compass: SIM. — **Risco: LOW**.
- [ ] **OQ5** — Geração de código de barras: EAN-13? Recomendação Compass: SIM. — **Risco: LOW**.
- [ ] **OQ6** — Hash de senha: argon2 (vs pbkdf2 default)? Recomendação Compass: argon2. — **Risco: LOW**.
- [ ] **OQ8** — Persistência dos dados em dev: volume Docker (recomendado) vs `/home/evonexus/evo-projects/go-control-erp/`. Decisão de produção fica para o deploy. — **Risco: LOW**.

---

## Account Redesign (GO Control ERP) — 2026-05-15
**Origem:** `workspace/development/plans/account-redesign/[C]plan-account-redesign.md` (@compass-planner)
**Endereçada para:** Eduardo (decisão) → @apex-architect (se decisões arquiteturais) → @bolt-executor

- [ ] **CardGrid em shared** — `CardGrid.tsx` esta em `apps/platform/src/components/`. Promover para `packages/shared/src/components/` ou duplicar no app account? Importa para Step 1. **Risco: LOW**.
- [ ] **Log de operacoes por usuario** — model novo `UserOperationLog` ou usar Django audit log existente (django-auditlog/simple-history)? Bloqueante para Step 2/4. **Risco: MEDIUM**.
- [ ] **Reset de senha pelo dono de conta** — `PasswordResetView` padrao do Django (envia email) ou link temporario proprio? Rate-limit obrigatorio. Bloqueante para Step 2/4. **Risco: HIGH** (seguranca).
- [ ] **Convites — `expires_at`** — adicionar campo no `Membership` ou calcular on-the-fly (`invited_at + 7d`)? Importa para Step 2/5. **Risco: LOW**.
- [ ] **Notificacoes** — on-the-fly via `/notifications/` (sem persistencia) ou criar model `Notification` com read/unread? Decisao de produto. **Risco: MEDIUM**.
- [ ] **Matriz cross-company (US10/AC6/Step 8)** — inclui nesta iteracao ou backlog v2? Decisao de escopo. **Risco: LOW**.
- [ ] **Toggle de acesso por empresa** — abrir endpoint em `/account/` ou ajustar permissoes no `/backoffice/platform/usuarios-aplicativo/` existente? Importa para Step 2/4. **Risco: MEDIUM**.


---

## Mensageria API (GO Control ERP) — Fase 1 — 2026-05-19
**Origem:** `/home/evonexus/evo-projects/go-control-erp/workspace/development/features/mensageria-api/[C]plan-mensageria-api.md` (@compass-planner)
**Endereçada para:** @apex-architect (Solutioning) → Eduardo (sign-off no ADR)

- [ ] **OQ2 — SMTP genérico para MVP de teste** — qual SMTP usar em dev/staging (Mailpit local vs Mailtrap vs SMTP real)? — Bloqueia Step 1 (Solutioning) — **Risco: LOW**
- [ ] **OQ4 — Recursos de permissão por papel** — confirmar slugs `mensageria.dispatch`, `mensageria.manage_templates`, `mensageria.manage_credenciais`, `mensageria.manage_api_keys`, `mensageria.view_mensagens` e mapear para papéis existentes — Bloqueia Step 4 — **Risco: MEDIUM**
- [ ] **OQ6 — Review LGPD pelo @lex-legal** — necessário antes do go-live de produção (não bloqueia Fases de dev) — **Risco: HIGH** se omitido
- [ ] **OQ1 — Billing report** — contagem de mensagens por tenant para futura cobrança/cap — adiado para Fase 2 — **Risco: LOW**
- [ ] **OQ3 — Storage de anexos S3-compatible** — Fase 1 usa filesystem local em `/var/lib/go-control/mensageria/{schema}/`; backup precisa cobrir esse path — adiado para Fase 2 — **Risco: MEDIUM** (sem backup, perda em crash)
- [ ] **OQ5 — Validação DKIM/SPF do `from_email`** — adiado para Fase 3 (white-label sender) — **Risco: LOW**


---

## Module Tree (GO Control ERP) — 2026-05-19

Plano: `workspace/projects/go-control-erp/features/module-tree/[C]plan-module-tree.md` (symlink) → repo do projeto

- [ ] **Duplicação `frontend/src/lib/modules-manifest.ts` vs. `frontend/packages/shared/src/lib/modules-manifest.ts`** — confirmar se pode unificar nesta feature ou fica fora de escopo — **Risco: LOW**
- [ ] **Validar `Modulo.route`** (startswith('/'), sem espaços) antes da migração para evitar links quebrados na sidebar — **Risco: MEDIUM**
- [ ] **RBAC por tela** — endpoint hoje filtra só por licença/módulo; quando houver RBAC por tela, tree precisa filtrar — fora de escopo, registrar como Follow-up no ADR — **Risco: LOW agora, HIGH depois**
- [ ] **Ícone do submenu/tela** — confirmar se seed atual de submenus/telas no banco tem `icone` preenchido; se não, popular como parte do Step 5 — **Risco: LOW**
- [ ] **Cache invalidation** — `useModules` tem `staleTime: 5min`; aceitar latência ou expor botão "recarregar módulos"? Sugestão: aceitar e registrar como melhoria futura — **Risco: LOW**

---

## GO Message — Credential Config por Provedor — 2026-05-19

Plano: `workspace/projects/go-control-erp/features/go-message-credential-config/[C]plan-go-message-credential-config.md`

- [ ] **Fallback `settings.EMAIL_*` em dev** — manter (com warning) ou forçar credencial sempre? Recomendação Compass: manter com warning. **Risco: LOW**.
- [ ] **Comportamento em produção com credencial inválida** — cair para settings (mascara bug) ou falhar (`CredencialFaltandoError`)? Recomendação Compass: falhar. **Risco: MEDIUM**.
- [ ] **Dry-run de conexão no POST /credenciais/** — validar contra provedor real ou só schema? Recomendação Compass: só schema; dry-run em backlog. **Risco: LOW**.
- [ ] **Migration destrutiva** — credenciais antigas (só dev hoje) são zeradas; ok ou preservar? Recomendação Compass: zerar com log explícito. **Risco: LOW**.
- [ ] **Roteamento entre múltiplas credenciais ativas** — quando há 2+ credenciais ativas para o mesmo (canal, provider) graças ao novo campo `nome`, qual o algoritmo? Recomendação Compass: pegar a mais antiga + warning agora; roteamento sofisticado em Fase 2. **Risco: MEDIUM**.
- [ ] **`nome` editável após criação?** — permitir renomear credencial existente ou ficar imutável? Recomendação Compass: editável (UI já cobre). **Risco: LOW**.

---

## Force Password Change (GO Control ERP) — 2026-05-24

Plano: `workspace/development/features/force-password-change/[C]plan-force-password-change.md`
PRD: `workspace/development/features/force-password-change/[C]prd-force-password-change.md`

- [ ] **OQ1 — Política mínima de senha** — apenas ≥8 chars + diferente da atual, ou exigir maiúscula/número/símbolo? Recomendação Compass: ≥8 chars + diferente, reforço em fase posterior. **Risco: LOW**.
- [ ] **OQ2 — Rotacionar JWT após troca?** — invalidar tokens existentes ou manter sessão atual válida? Recomendação Compass: manter (só zera o flag). **Risco: MEDIUM**.
- [ ] **OQ3 — Usuário pode "pular" a troca?** — Recomendação Compass: não, bloqueio rígido. **Risco: LOW**.
- [ ] **OQ4 — Botão "Sair" visível no ChangePasswordPage?** — Recomendação Compass: sim. **Risco: LOW**.
- [ ] **OQ5 — Banner explicativo "Sua senha foi resetada pelo administrador..."?** — Recomendação Compass: sim. **Risco: nenhum**.

---

## GO Payment Hub — MVP — 2026-05-26

Plano: `/home/evonexus/evo-projects/go-control-erp/features/go-payment-hub/[C]plan-go-payment-hub.md`
PRD: `/home/evonexus/evo-projects/go-control-erp/features/go-payment-hub/[C]prd-go-payment-hub.md`

Bloqueadores antes de Phase 3 (Apex/ADR):

- [ ] **Q1 — Pagador como FK em `pessoas.Pessoa` ou payload livre?** — Define schema de `PaymentIntent` no Step 1 e acoplamento com Módulo Pessoas. Default Compass: híbrido (FK opcional + snapshot sempre). **Risk: med**
- [ ] **Q2 — Conciliação Bradesco no MVP: webhook ou CNAB 240?** — Define escopo do Step 3. Default Compass: CNAB upload no MVP; webhook fica para V2 se contratado. **Risk: med**
- [ ] **Q4 — Subdomínio dedicado para webhooks inbound (`hooks.go-control.com.br`)?** — Bloqueia config DNS/Traefik na Fase 0. Default Compass: sim. **Risk: low**
- [ ] **Q5 — API interna GO Cobrança ↔ Hub: HTTP com API key ou chamada in-process via service?** — Define integração no Step 2. Default Compass: in-process via service layer; API HTTP só para externos. **Risk: med**

Defaults Compass aceitos (sem necessidade de decisão explícita, mas registrados):

- [ ] **Q3 — Frontend admin: app separado (porta 5182).** **Risk: low**
- [ ] **Q6 — Conectores habilitados por agreement aprovado, não global.** **Risk: low**
- [ ] **Q7 — Webhook outbound: payload completo no MVP.** **Risk: low**
- [ ] **Q8 — Outbox eventually consistent.** **Risk: low**
- [ ] **Q9 — Sandbox por agreement (não tenant dedicado).** **Risk: low**
- [ ] **Q10 — Manter `/v1/` ao adicionar Pix Automático/cartão na V2.** **Risk: low**

## Staff Catalog & AUTH como autenticador único — 2026-05-29

Plano: `/home/evonexus/evo-nexus/workspace/development/features/staff-catalog-auth/[C]plan-staff-catalog-auth.md`
PRD: `/home/evonexus/evo-nexus/workspace/development/features/staff-catalog-auth/[C]prd-staff-catalog-auth.md`

**TODAS as 4 perguntas críticas foram fechadas por Eduardo em 2026-05-29:**

- [x] **Q1 — Owner override via `is_impersonation: bool` em `AuthorizationCode`** (não `acesso_override` JSON). Marcar code no `staff/launch`, registrar `ImpersonationLog`, injetar `acesso` no `redeem`.
- [x] **Q2 — `acesso.modulos` em impersonação = módulos licenciados do plano contratado da empresa.** Reusa `resolve_permissions` com override `is_owner=True`. Staff respeita limites do plano.
- [x] **Q3 — Apps staff não têm `conta_id`/`empresa_id`.** Segundo flag `is_staff_app: bool` em `AuthorizationCode` (decidido por código no emit, não inferência runtime). No `redeem` → `make_platform_staff_token`.
- [x] **Q4 — Staff é exclusivamente administrativo, sem vínculo de cliente.** `login_catalog` para staff ignora `UserEmpresaVinculo` e vai direto a `/staff/catalog`.

Defaults Compass aceitos (sem necessidade de decisão explícita):

- [ ] **Q5 — Logout do Platform Admin via `sessionManager.logout(...)`.** **Risk: low**
- [ ] **Paginação de contas: 100 + busca client-side, backend retorna `total_contas`.** **Risk: low**
- [ ] **Apelido `staff_only` no serializer staff catalog (mantém `requires_staff` no DB).** **Risk: low**

Bloqueadores: nenhum. Pronto para @apex-architect → @bolt-executor.

---

## GO Payment Hub — Emissão Assíncrona — 2026-06-02

PRD: `/home/evonexus/evo-projects/go-control-erp/features/go-payment-hub/[C]prd-async-emission.md`
Plano: `/home/evonexus/evo-projects/go-control-erp/features/go-payment-hub/[C]plan-async-emission.md`
ADR: `/home/evonexus/evo-projects/go-control-erp/features/go-payment-hub/[C]ADR-008-async-emission.md`

- [ ] **Q1 — TTL do Idempotency-Key:** 24h sugerido pelo ADR; algum cliente faz retry > 24h depois? — Define cache eviction e janela de proteção contra dupla emissão — Risk: low
- [ ] **Q2 — Alerta de fila grande:** F2 do ADR (alerta Telegram para `payment_issuance > 50`) — entra junto com o feature ou fica para próxima fase? — Sem alerta, degradação só vira visível pelo dashboard manual — Risk: med
- [ ] **Q3 — `payer_address` validation:** novo `EmitRequestSerializer` específico (preferido pelo Compass) ou estender o `PaymentIntentSerializer` atual? — Separa concerns vs minimiza superfície de mudança — Risk: low
- [ ] **Q4 — UI consumer no GO Control web:** sub-escopo deste plano ou ticket separado para Canvas (sugerido)? — Define se Step 5 cobre só admin ou também consumer — Risk: low
- [ ] **Q5 — Métricas SLO:** Prometheus/Grafana já existe no Payment Hub? Se não, SQL agregado no dashboard (Step 5) serve como MVP. — Define se entra observabilidade externa — Risk: low

Bloqueadores: nenhum. Pronto para @bolt-executor após aprovação do Eduardo.

## discord-plus-renew-confirm — 2026-06-03
- [ ] /model set e /agent set durante pending devem re-exibir o summary atualizado? — PRD pede (AC-3), handlers atuais só confirmam o ajuste — Risk: low (recomendado Opção A: anexar summary)
- [ ] /session confirm (subcomando) vs /confirm (top-level) — plano adota subcomando conforme PRD §4 — Risk: low

---

## Discord Plus — Isolamento de processo CLI (Fix 3: systemd-run --scope) — 2026-06-05

Discovery: `/home/evonexus/evo-nexus/workspace/development/features/discord-plus-cli-process-isolation/[C]discovery-discord-plus-cli-process-isolation.md`

- [ ] Mecanismo: `sudo systemd-run --scope` (system) vs `enable-linger` + `--user`? `--scope` puro dá "Access denied"; `--user` não tem bus (sem linger). — Bloqueia o plano inteiro — Risk: high
- [ ] Detectar/classificar OOM-kill do scope vs `max_turns` vs falha normal? Heurística atual (cli-session-runner.ts:408-411) classifica OOM como max_turns. — Usuário recebe causa errada — Risk: high
- [ ] Re-aplicar namespaces (PrivateTmp/ProtectHome/ReadWritePaths) no scope ou aceitar FS do host? Scope no system manager perde as proteções do serviço. — Comportamento de FS muda — Risk: med
- [ ] Repassar env (minimalCliEnv) para dentro do scope via `--setenv` por var? systemd-run não herda env do chamador. — claude falha no startup pós-deploy — Risk: high
- [ ] Encerramento: matar wrapper basta ou precisa `systemctl stop <unit>`? child.pid passa a ser o systemd-run/sudo, não o claude. — cancel/timeout não matam pytest neto — Risk: med
- [ ] Endurecer sudoers de `NOPASSWD: ALL` para só o comando systemd-run? — Superfície de root ampla — Risk: high
- [ ] Teto de memória por scope + teto agregado para não derrubar o LXC? — Troca "derruba serviço" por "derruba container" — Risk: med
- [ ] Notificar usuário do Discord em OOM-kill? Qual mensagem? — UX/observabilidade — Risk: low
