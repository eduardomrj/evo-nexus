# PRD — Staff Catalog & AUTH como Autenticador Único (GO Control ERP)

**Slug:** `staff-catalog-auth`
**Owner do PRD:** @compass-planner
**Data:** 2026-05-29
**Projeto:** `/home/evonexus/evo-projects/go-control-erp/`
**Reformula:** `platform-access-restriction` (superseded)

---

## Problema

Hoje o **Platform Admin** (`frontend/apps/platform/`) mantém seu próprio fluxo de login (`/login`, `auth.isAuthenticated()` em `app/router.tsx:43-48`). Como consequência:

1. **Há dois autenticadores** na plataforma: AUTH SPA (`frontend/apps/auth/`, central) e Platform Admin (próprio). Cada um precisa ser ajustado quando regras de auth mudam (lockout, troca de senha, 2FA — `auth-policy-2fa` já planejado).
2. **Apps staff-only não têm catálogo** — staff entra "no escuro": precisa lembrar URLs (`platform.gocontrol.com.br`, futuros apps de backoffice).
3. **Staff não tem como impersonar uma conta** para suporte de forma estruturada — hoje só via `ImpersonationLog` manual, sem UI guiada.
4. **A bloqueio de acesso negado vive no Platform Admin** (`PlatformLayout.tsx:60` chama `navigate('/login')` para não-staff). A regra deveria pertencer ao AUTH (autoridade única).

Eduardo decidiu: **AUTH é o único autenticador**. Apps staff são apenas mais um item do catálogo (com `staff_only=True`), com catálogo dedicado para staff que permite (a) entrar em apps staff-only e (b) impersonar qualquer conta como owner.

---

## Objetivos

1. AUTH é o único ponto de entrada de autenticação — Platform Admin deixa de ter `/login` próprio.
2. Após login no AUTH:
   - se `user.is_platform_staff=True` → redireciona para `/staff/catalog`;
   - caso contrário → mantém o `/catalog` atual.
3. Página `/staff/catalog` exibe:
   - **Apps marcados como staff_only** (cadastrados no `Aplicativo` com flag) — clicar leva direto ao app via SSO code com permissões de owner;
   - **Seletor de conta ativa** — lista todas as contas com `status='ativada'`.
4. Após escolher uma conta, `/staff/catalog/:contaId` exibe **licenças ativas daquela conta agrupadas por empresa**; clicar emite SSO code com permissões de **owner full** independentemente de `UserLicenca`.
5. Acesso negado a app staff-only por usuário não-staff é bloqueado **no AUTH** (não no app destino) e exibe mensagem clara.
6. Mudança não regride apps cliente atuais (account, go-message, go-cobranca, go-payment-hub seguem funcionando com `VITE_USE_CENTRAL_AUTH=true`).

## Não-objetivos

- Reescrever fluxo de redeem-code dos apps cliente — já funciona via `sessionManager.handleAuthCallback`.
- Substituir `ImpersonationLog` — continuamos gravando entrada nele quando staff entra como owner em conta de cliente (fora do escopo deste PRD; ver Open Questions).
- Implementar email de alerta para tentativa de acesso negado (planejado antes em `platform-access-restriction` — desescopado por ora).
- Renomear backend `requires_staff` → `staff_only` no banco (campo já existe e funciona — ver Open Questions Q1).

---

## Usuários e cenários

### U1 — Eduardo (platform staff)
Quer abrir o Platform Admin pela manhã, e também entrar como owner na conta de um cliente específico para diagnosticar um pedido travado.

### U2 — João (usuário cliente, não-staff)
Entra no AUTH normalmente, vê o catálogo de empresas+apps do seu vínculo (`UserEmpresaVinculo`) — comportamento atual preservado.

### U3 — Maria (atendimento, futura papel staff parcial)
Hoje só Eduardo é staff. No futuro pode haver staff segmentado — fora do escopo agora (todo staff vê tudo).

---

## Histórias de usuário

### US-01 — Login redireciona staff para `/staff/catalog`
**Como** staff da plataforma
**Quero** entrar no AUTH com email/senha e ir direto ao catálogo staff
**Para** não confundir com o catálogo de apps cliente

### US-02 — Catálogo staff lista apps staff-only
**Como** staff
**Quero** ver os apps marcados como `staff_only=True` em uma seção do catálogo staff
**Para** acessar Platform Admin (e futuros apps de backoffice) sem decorar URL

### US-03 — Seletor de conta no catálogo staff
**Como** staff
**Quero** ver a lista de todas as contas ativadas
**Para** escolher uma e impersonar como owner

### US-04 — Drill-down em conta seleciona licença
**Como** staff
**Quero** ao clicar em uma conta, ver as licenças ativas dela agrupadas por empresa
**Para** escolher qual licença entrar

### US-05 — Launch com owner override
**Como** staff
**Quero** clicar em uma licença e ser levado ao app com permissões de owner
**Para** ter acesso total mesmo sem `UserLicenca` registrado

### US-06 — Bloqueio de não-staff em app staff-only
**Como** usuário não-staff
**Quero** receber mensagem clara se tentar abrir um app staff-only
**Para** entender que não tenho acesso (e não cair em tela genérica de "Acesso negado")

### US-07 — Platform Admin usa central auth
**Como** staff
**Quero** que Platform Admin tenha o mesmo fluxo de auth dos apps cliente (callback via code)
**Para** mudanças futuras (2FA, lockout) propagarem automaticamente

---

## Critérios de aceitação (Given/When/Then)

### AC-01 — Redirect pós-login para staff
**Given** usuário com `is_platform_staff=True`
**When** faz login bem-sucedido no AUTH sem `?app=...&redirect=...`
**Then** a resposta de `POST /auth/login-app` retorna `stage='done'` com `redirect_to='/staff/catalog'`
**And** o frontend navega para `/staff/catalog`.

### AC-02 — Redirect pós-login para não-staff (regressão)
**Given** usuário com `is_platform_staff=False` e ao menos um `UserEmpresaVinculo` ativo
**When** faz login bem-sucedido no AUTH sem `?app=...&redirect=...`
**Then** `redirect_to='/catalog'` (comportamento atual preservado).

### AC-03 — Staff catalog backend retorna apps + contas
**Given** staff autenticado
**When** GET `/api/v1/auth/staff/catalog`
**Then** resposta = `{ apps: [...], contas: [...] }` onde:
- `apps` é a lista de Aplicativos com `staff_only=True` (campo `requires_staff` no DB) e `status='ativo'`, ordenados por nome, no mesmo shape de `AppInfo` do catálogo cliente;
- `contas` é a lista de Contas com `status='ativada'`, ordenadas por `nome`, contendo `id`, `nome`, `cnpj_matriz`, `slug`.

### AC-04 — Non-staff é bloqueado em `/auth/staff/catalog`
**Given** usuário autenticado com `is_platform_staff=False`
**When** GET `/api/v1/auth/staff/catalog`
**Then** resposta `403 { error, code: 'staff_only' }`.

### AC-05 — Drill-down de conta retorna licenças por empresa
**Given** staff autenticado, `contaId` válido e ativado
**When** GET `/api/v1/auth/staff/catalog/{contaId}`
**Then** resposta = `{ conta: {...}, empresas: [{ empresa_id, razao_social, licencas: [{aplicativo_key, aplicativo_nome, icone_url, url_login_callback, licenca_id, status}] }] }`, apenas licenças com `status='ativa'`.

### AC-06 — Launch emite code com owner override
**Given** staff autenticado, `app_key` e `empresa_id` válidos
**When** POST `/api/v1/auth/staff/launch { app_key, empresa_id }`
**Then** emite `AuthorizationCode` (TTL 60s) **and** o `redeem-code` subsequente retorna JWT com `acesso = { is_owner: True, papel_code: 'owner', modulos: [] }` independente de existir `UserLicenca` para o staff naquela licença
**And** redireciona para `aplicativo.url_login_callback?code=...`.

### AC-07 — Launch em app staff-only por não-staff é bloqueado
**Given** usuário com `is_platform_staff=False`
**When** POST `/api/v1/auth/staff/launch`
**Then** resposta `403 { error, code: 'staff_only' }`.

### AC-08 — App staff-only é invisível no catálogo cliente
**Given** Aplicativo com `requires_staff=True`
**When** GET `/api/v1/auth/catalog` (catálogo cliente)
**Then** o app **não** aparece em nenhuma `EmpresaCatalogo.apps` (mesmo que tem_licenca seria True para alguma licença anômala).

### AC-09 — Frontend AUTH: rotas staff exigem staff
**Given** usuário autenticado mas com `is_platform_staff=False`
**When** acessa `/staff/catalog` ou `/staff/catalog/:contaId`
**Then** é redirecionado para `/catalog` (sem flash de conteúdo staff).

### AC-10 — Platform Admin usa central auth
**Given** `VITE_USE_CENTRAL_AUTH=true` no Platform Admin
**When** usuário não autenticado abre qualquer rota privada
**Then** o frontend redireciona para `{authUrl}/login?redirect=...&app=platform-admin`
**And** após redeem-code, `PlatformLayout` não faz mais check de `is_platform_staff` (bloqueio passa para AUTH no `staff_only` do app).

### AC-11 — Auto-redirect single-empresa preservado
**Given** usuário não-staff com **uma única** empresa **e uma única** licença ativa
**When** abre `/catalog`
**Then** auto-redireciona para o app (comportamento atual `CatalogPage.tsx:67-76` preservado).

### AC-12 — Sem regressão de testes existentes
**Given** testes atuais de `auth_central` e `platform` no projeto
**When** rodar `make test-backend`
**Then** todos passam.

---

## Constraints

- ADR-001 obrigatório: views thin → services → repositories → models; exceptions de domínio em `apps/auth_central/exceptions.py`; ≤ 300 linhas/arquivo, ≤ 30 linhas/método.
- Frontend: chamadas HTTP só em `features/*/api.ts`.
- Owner override **não cria `UserLicenca` fake** — implementado passando `acesso={is_owner, papel_code, modulos}` para `make_final_token` que já aceita o parâmetro (`tokens.py:69-100`).
- Não renomear `Aplicativo.requires_staff` no banco — usar o campo existente; expor como `staff_only` nas serializações se quisermos vocabulário consistente.
- TTL do `AuthorizationCode` permanece 60s (`repositories.py:16`).
- Manter `enabled: False` em `requires_staff` como default (já é).

---

## Riscos e mitigações

| Risco | Severidade | Mitigação |
|---|---|---|
| Staff abrir Platform Admin sem owner override em conta cria sessão "sem ctx" e quebra views | Alta | Para Platform Admin (que não tem conta-tenant), emitir token tipo `platform_staff` (já existe em `tokens.py:7-19`) — não usar fluxo de empresa |
| Auto-redirect single-app dispara para staff que só vê apps staff-only de uma conta | Média | `/staff/catalog` não implementa auto-redirect; só `/catalog` faz |
| Catálogo cliente regrida ao filtrar `staff_only` | Média | Adicionar teste explícito (AC-08) e manter pipeline atual |
| Componente staff catalog vê todas as contas (mil+ tenants no futuro) | Baixa-Média | Paginação opcional + busca por nome/CNPJ no frontend; backend manda primeiras 100 |
| ImpersonationLog não é gravado quando staff entra como owner | Média | Open Question Q3 (escopo: gravar em `staff/launch`?) |

---

## Open questions

- **Q1** — Renomear `Aplicativo.requires_staff` → `staff_only` no banco (migration) ou manter o nome atual e expor `staff_only` apenas nas serializações? **Recomendação:** manter `requires_staff` no DB (já tem testes), expor `staff_only` no serializer do staff catalog para consistência com o vocabulário de Eduardo. **Risk:** baixo.
- **Q2** — O Platform Admin não é multi-tenant (não tem conta/empresa). Ao staff clicar no card "Platform Admin" no `/staff/catalog`, o `staff/launch` deve emitir token do tipo `platform_staff` (sem `conta_id`/`empresa_id`) ou criar um pseudo-ctx? **Recomendação:** emitir `make_platform_staff_token` (já existe), e flag no Aplicativo indica o modo (`tipo_token` ou heurística por `requires_staff && !needs_empresa_context`). **Risk:** médio — precisa decidir antes do Step 3.
- **Q3** — `ImpersonationLog` deve ser criado quando staff entra como owner numa conta-cliente via staff catalog? **Recomendação:** sim, gravar `ImpersonationLog(staff=user, conta=..., empresa=...)` dentro do `StaffLaunchService` quando `app != platform-admin`. **Risk:** baixo.
- **Q4** — Paginação/busca de contas: lazy (apenas após digitar termo) ou eager (primeiras N)? **Recomendação:** eager 100 + busca client-side para v1; revisitar quando tivermos 500+ contas.
- **Q5** — Logout do Platform Admin: ao remover o login próprio, o botão "Sair" do `PlatformLayout` deve chamar `sessionManager.logout(authUrl, apiBase)` (igual aos outros apps) e voltar para `{authUrl}/login`?  **Recomendação:** sim, idêntico ao padrão dos demais apps.
