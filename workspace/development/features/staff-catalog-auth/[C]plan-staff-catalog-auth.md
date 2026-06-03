# Plano — Staff Catalog & AUTH como Autenticador Único (GO Control ERP)

**Slug:** `staff-catalog-auth`
**Owner do plano:** @compass-planner
**Data:** 2026-05-29 (atualizado com decisões finais Q1–Q4 do Eduardo)
**PRD pareado:** `[C]prd-staff-catalog-auth.md` (mesma pasta)
**Reformula:** `platform-access-restriction` (marcado como superseded)
**Projeto:** `/home/evonexus/evo-projects/go-control-erp/`
**Próximo agente sugerido:** @apex-architect (ADR-006 confirmando decisões) → @bolt-executor → @oath-verifier

---

## Decisões finais (Eduardo, 2026-05-29)

| Q | Decisão |
|---|---|
| **Q1** | Criar **`is_impersonation: bool`** em `AuthorizationCode` (migration). No `POST /auth/staff/launch` o code é marcado com `is_impersonation=True` **e** `ImpersonationLog` é registrado. No `redeem`, ao detectar o flag, injetar `acesso={is_owner: True, papel_code: 'owner', modulos: <módulos licenciados da empresa>}`. **Sem criar `UserLicenca` fake.** |
| **Q2** | Em modo impersonação, `acesso.modulos` contém **apenas os módulos licenciados daquela empresa**. Implementação: chamar `resolve_permissions(...)` para obter os módulos do plano contratado e **sobrescrever `is_owner=True` + `papel_code='owner'`** no resultado. Staff respeita os limites do plano contratado. |
| **Q3** | Apps `requires_staff=True` **não têm `conta_id` nem `empresa_id`**. Adicionar **segundo flag `is_staff_app: bool`** em `AuthorizationCode` (decidido por código no `staff_launch`, não inferido em runtime do `Aplicativo.requires_staff` — mais auditável). No `CodeService.redeem`, se `is_staff_app=True` → chamar `make_platform_staff_token(user)` (já existe em `tokens.py:7-19`). Caso contrário, `make_final_token(...)`. |
| **Q4** | **Staff é exclusivamente administrativo.** Não existe usuário staff com `UserEmpresaVinculo` de cliente. Toda lógica de "staff com vínculo de cliente" sai do plano. `login_catalog` para staff ignora `UserEmpresaVinculo` completamente e vai direto a `/staff/catalog`. |

---

## Contexto

AUTH passa a ser autoridade única de autenticação. Apps staff (Platform Admin e futuros backoffice) viram itens de um catálogo dedicado `/staff/catalog`. Staff que escolhe uma conta-cliente entra como **impersonador owner** — com módulos limitados ao plano contratado. Não-staff é bloqueado no AUTH.

**Estado atual confirmado em código (2026-05-29):**

- `Aplicativo.requires_staff` já existe (`backend/apps/platform/models/aplicativo.py:87`, migration 0056) — reusar como flag canônica de "app staff-only".
- `LoginService._check_staff_restriction` (`backend/apps/auth_central/services/login_service.py:167-184`) já bloqueia login direto em app `requires_staff` por não-staff.
- `make_final_token(user, conta_id, empresa_id, acesso=..., aplicativo_id=..., app_key=...)` (`backend/apps/platform/services/auth/tokens.py:69-100`) **já aceita `acesso` opcional** — base do owner override para apps de cliente.
- `make_platform_staff_token(user)` (`tokens.py:7-19`) emite token sem ctx de conta — caminho usado pelo `redeem` quando `is_staff_app=True`.
- `resolve_permissions(user, empresa_id, aplicativo_id)` (`tokens.py:32-66`) retorna `{is_owner, papel_code, modulos}`. Em impersonação, **chamamos para extrair `modulos` do plano** e sobrescrevemos `is_owner=True` + `papel_code='owner'` — mas precisa de variante que **não exija `UserLicenca`** (passa pela `Licenca` da empresa direto). Ver Step 2.
- `CatalogService.get_apps_visiveis` (`repositories.py:144-152`) precisa filtrar `requires_staff=False` para esconder apps staff do catálogo cliente.
- `AuthCallbackPage` padrão em `frontend/apps/account/src/features/auth-callback/AuthCallbackPage.tsx` — copiar para Platform Admin.
- `auth.isAuthenticated()` em `frontend/apps/platform/src/app/router.tsx:43-48` + `LoginPage` em `frontend/apps/platform/src/shared/components/LoginPage.tsx` — remover ambos quando central auth assumir.
- `PlatformLayout.tsx:54-69` faz `navigate('/login')` se `!is_platform_staff` — remover (passa a ser garantido pelo `requires_staff` do Aplicativo + bloqueio no AUTH).

---

## Objetivos

1. Backend: 3 endpoints novos em `auth_central` (`/staff/catalog`, `/staff/catalog/:contaId`, `/staff/launch`) + filtro `requires_staff=False` no catálogo cliente + redirect staff-aware pós-login + 2 flags novos (`is_impersonation`, `is_staff_app`) em `AuthorizationCode`.
2. Frontend AUTH: novo feature folder `staff-catalog` com 2 páginas, rotas protegidas e guard que redireciona não-staff para `/catalog`.
3. Frontend Platform Admin: passa a usar `VITE_USE_CENTRAL_AUTH=true`, remove `LoginPage`/legacy auth, ganha `AuthCallbackPage`.
4. Impersonação funciona via flags persistidos no code — zero `UserLicenca` fake, módulos respeitam plano contratado.
5. Todos os testes existentes continuam passando; novos testes cobrem cada AC do PRD.

---

## Guardrails

### Must Have
- ADR-001 estrito: views thin (≤ 30 linhas/método), services orquestram, repositories isolam ORM; novas exceções em `apps/auth_central/exceptions.py`.
- Impersonação implementada via flags persistentes (`is_impersonation`, `is_staff_app`) no `AuthorizationCode`; **nunca** via `UserLicenca` fake.
- Em impersonação, `acesso.modulos` vem da `Licenca` da empresa (plano contratado) — não vem vazio nem inclui módulos que o plano não comprou.
- Frontend AUTH: chamadas HTTP só em `features/staff-catalog/api.ts`.
- Platform Admin: callback usa `sessionManager.handleAuthCallback` igual aos outros apps.
- Não regredir AC-08 (staff_only invisível no catálogo cliente).
- Não regredir auto-redirect single-app/empresa no `/catalog` cliente (AC-11).
- `ImpersonationLog` gravado sempre que `is_impersonation=True`.

### Must NOT Have
- Renomear `requires_staff` → `staff_only` no banco (campo mantido).
- `UserLicenca` fake para staff em conta de cliente.
- Vincular staff a conta/empresa de cliente via `UserEmpresaVinculo` ou `Membership` (Q4).
- Inferir `is_staff_app` em runtime no `redeem` — decidir no momento de emitir o code e persistir.
- Nova `LoginPage` no Platform Admin após o switch.
- Lógica de `is_platform_staff` no `PlatformLayout` após a migração (passa para AUTH).
- Email de alerta de acesso negado (escopo do plano antigo, descontinuado).

---

## Steps

### Step 1 — Backend: redirect staff-aware no login + filtro `requires_staff` no catálogo cliente

**Complexidade:** baixa.

**O que fazer:**
1. `apps/auth_central/repositories.py:144-152` (`CatalogRepository.get_apps_visiveis`): adicionar `.filter(requires_staff=False)`.
2. `apps/auth_central/services/login_service.py:101-165` (`LoginService.login_catalog`): refatorar para tratar staff **antes** de qualquer query a `UserEmpresaVinculo` (Q4).
   - Após `authenticate` + `reset_login_failures`:
     - **Se `user.is_platform_staff=True`:** emitir `make_platform_staff_token(user)` (sem `conta_id`/`empresa_id`); retornar `{stage: 'done', redirect_to: '/staff/catalog', access_token, refresh_token, user: {id, nome, email, is_platform_staff: True}}`. **Não consultar `UserEmpresaVinculo`.**
     - **Se não-staff:** comportamento atual preservado (consulta `UserEmpresaVinculo`, ramos `no_access` / `select_empresa` / `done` → `/catalog`). Adicionar `is_platform_staff: False` ao `user` do payload.
3. Extrair `_login_catalog_staff(user)` e `_login_catalog_user(user)` para manter `login_catalog` ≤ 30 linhas (ADR-001).
4. Garantir que `is_platform_staff` é serializado no `user` de retorno (para o `StaffGuard` do frontend usar sem decodificar JWT).

**Acceptance:**
- AC-01, AC-02, AC-08 passam.
- Teste `tests/test_login_service.py` cobre:
  - staff loga sem `UserEmpresaVinculo` → `redirect_to='/staff/catalog'`, tokens emitidos.
  - staff loga **com** `UserEmpresaVinculo` (cenário anômalo) → ainda assim vai para `/staff/catalog` (Q4: vínculo é ignorado).
  - não-staff com 1 vínculo → `/catalog` (regressão).
  - não-staff sem vínculo → `no_access`.
- Teste `tests/test_catalog_service.py`: app `requires_staff=True` ausente em `/auth/catalog`.

**Arquivos tocados:**
- `backend/apps/auth_central/repositories.py` (~1 linha)
- `backend/apps/auth_central/services/login_service.py` (refactor `login_catalog`, ~30 linhas líquidas; criar 2 helpers privados)
- `backend/apps/auth_central/tests/test_login_service.py`
- `backend/apps/auth_central/tests/test_catalog_service.py`

---

### Step 2 — Backend: flags `is_impersonation` + `is_staff_app` em `AuthorizationCode` + branching no `redeem`

**Complexidade:** média (alterações no modelo + `CodeService.redeem`).

**O que fazer:**
1. **Modelo:** em `backend/apps/auth_central/models.py`, adicionar dois campos a `AuthorizationCode`:
   - `is_impersonation = models.BooleanField(default=False, db_index=False)`
   - `is_staff_app = models.BooleanField(default=False, db_index=False)`
   - Defaults `False` garantem que codes existentes continuam funcionando.
2. **Migration:** nova migration `0002_authcode_impersonation_flags.py` em `backend/apps/auth_central/migrations/`.
3. **`AuthorizationCodeRepository.create`** (`repositories.py:25-51`):
   - Aceitar `is_impersonation=False` e `is_staff_app=False` como kwargs e gravar na instância.
4. **`CodeService.emitir`** (`services/code_service.py:26-47`):
   - Aceitar `is_impersonation=False` e `is_staff_app=False` como kwargs e propagar ao repository.
5. **`CodeService._build_redeem_response`** (`code_service.py:58-76`): refatorar para escolher o token:
   - **Se `obj.is_staff_app=True`** → chamar `make_platform_staff_token(obj.user)`; retornar payload com `ctx={stage:'authenticated', type:'platform_staff', app_key}` e **sem** `acesso` (ou `acesso={'is_owner': True, 'papel_code': 'staff', 'modulos': []}` para shape consistente). Sem `conta_id`/`empresa_id`.
   - **Se `obj.is_impersonation=True`** (e `is_staff_app=False`): chamar nova função `resolve_permissions_for_impersonation(user, empresa_id, aplicativo_id)` (Step 2.7) que retorna `{is_owner: True, papel_code: 'owner', modulos: <do plano>}`. Emitir `make_final_token(obj.user, obj.conta_id, obj.empresa_id, acesso=<acima>, aplicativo_id=obj.aplicativo_id, app_key=app_key)`.
   - **Caso contrário** (fluxo normal): comportamento atual (`acesso = resolve_permissions(...)`, `make_final_token(...)`).
   - Extrair branching para `_resolve_redeem_strategy(obj, app_key)` se necessário para manter `_build_redeem_response` ≤ 30 linhas.
6. **Audit:** em `audit_log.py`, estender `log_code_redeemed` para gravar `is_impersonation` e `is_staff_app` (rastreabilidade — toda impersonação deixa rastro além do `ImpersonationLog`).
7. **Q2 — Nova função em `apps/platform/services/auth/tokens.py`:**
   ```python
   def resolve_permissions_for_impersonation(user, empresa_id, aplicativo_id) -> dict:
       """Resolve módulos do plano contratado da empresa (sem exigir UserLicenca do staff).

       Returns: {is_owner: True, papel_code: 'owner', modulos: [<módulos licenciados>]}
       """
       # Busca Licenca da empresa+aplicativo (status='ativa').
       # Resolve módulos via PlanoModulo do plano contratado.
       # NÃO consulta UserLicenca — staff não tem.
   ```
   - Reusar query do `PlanoModulo` que já existe no fluxo de licenças. **Não criar** `UserLicenca` para o staff.
   - Se não houver `Licenca` ativa para a empresa+aplicativo → levantar `LicencaInativaError` (nova exceção em `apps/auth_central/exceptions.py`) e o `staff/launch` retorna 400 antes de emitir code.

**Acceptance:**
- Teste `tests/test_code_service.py`:
  - redeem de code normal → `acesso` resolvido por `resolve_permissions` (regressão).
  - redeem de code `is_impersonation=True` → `acesso.is_owner=True`, `acesso.papel_code='owner'`, `acesso.modulos` = módulos do plano da empresa (não vazio, não excede plano).
  - redeem de code `is_staff_app=True` → token tipo `platform_staff`, sem `ctx.conta_id`/`empresa_id`.
  - migration aplica e reverte sem erro.
- Teste `tests/test_tokens.py`:
  - `resolve_permissions_for_impersonation` com licença ativa retorna módulos corretos.
  - Sem licença ativa → levanta exceção.
  - Não cria `UserLicenca`.

**Arquivos tocados:**
- `backend/apps/auth_central/models.py` (+2 campos em `AuthorizationCode`)
- `backend/apps/auth_central/migrations/0002_authcode_impersonation_flags.py` (novo)
- `backend/apps/auth_central/repositories.py` (`AuthorizationCodeRepository.create` aceita 2 kwargs)
- `backend/apps/auth_central/services/code_service.py` (branching em `_build_redeem_response`)
- `backend/apps/auth_central/audit_log.py` (log inclui flags)
- `backend/apps/auth_central/exceptions.py` (`LicencaInativaError`)
- `backend/apps/platform/services/auth/tokens.py` (`resolve_permissions_for_impersonation` — função nova, ≤ 30 linhas)
- `backend/apps/auth_central/tests/test_code_service.py`
- `backend/apps/auth_central/tests/test_tokens.py` (novo)

---

### Step 3 — Backend: `StaffCatalogService`, `StaffLaunchService` + 3 endpoints + repositórios

**Complexidade:** média.

**O que fazer:**
1. **`backend/apps/auth_central/services/staff_catalog_service.py`** (novo):
   - `listar_apps_e_contas(staff_user)`:
     - `apps` = `AplicativoRepository.list_staff_apps()` (novo método: `requires_staff=True, status='ativo'`, ordenado por nome). Shape: `{key, nome, descricao_curta, icone_url, url_login_callback, url_producao}`.
     - `contas` = `ContaRepository.list_ativadas(limit=100)` (novo método: `status='ativada'`, ordem `nome ASC`). Shape: `{id, nome, cnpj_matriz, slug}`. Retorna `total` para sinalizar paginação futura.
     - Retorna `{apps: [...], contas: [...], total_contas: N}`.
   - `licencas_da_conta(staff_user, conta_id)`:
     - Valida que `conta_id` existe e `status='ativada'`.
     - `CatalogRepository.get_licencas_agrupadas_por_empresa(conta_id)` (novo método): `Licenca.objects.filter(empresa__conta_id=conta_id, status='ativa').select_related('empresa', 'aplicativo').exclude(aplicativo__requires_staff=True)` — staff apps não aparecem aqui.
     - Agrupa por `empresa_id`. Retorna `{conta: {...}, empresas: [{empresa_id, razao_social, licencas: [{licenca_id, aplicativo_key, aplicativo_nome, icone_url, url_login_callback, status}]}]}`.

2. **`backend/apps/auth_central/services/staff_launch_service.py`** (novo):
   - `emitir_code(staff_user, app_key, empresa_id=None, ip=None)`:
     - Valida `staff_user.is_platform_staff` → senão levanta `StaffOnlyAppError`.
     - `app = AplicativoRepository.get_ativo_or_raise(app_key)`.
     - **Dois ramos de decisão (mutuamente exclusivos):**
       - **Ramo A — App staff-only (`app.requires_staff=True`):** `empresa_id` deve ser `None` (validar; se vier valor → `AuthCentralError`). Emite code com `is_staff_app=True`, `is_impersonation=False`, `conta_id=None`, `empresa_id=None`. Redirect para `app.url_login_callback`. **Não grava `ImpersonationLog`** (não há conta de cliente sendo impersonada).
       - **Ramo B — Impersonação em app cliente (`app.requires_staff=False`):** `empresa_id` obrigatório. Valida `empresa.ativo=True` e `empresa.conta.status='ativada'`. Valida licença ativa (`resolve_permissions_for_impersonation` antecipa erro se inexistente). Emite code com `is_impersonation=True`, `is_staff_app=False`, `conta_id=empresa.conta_id`, `empresa_id=empresa.id`. **Grava `ImpersonationLog(staff=staff_user, conta=empresa.conta, empresa=empresa)`**. Redirect para `app.url_login_callback`.
     - Retorna `{redirect_to: '<url>?code=<raw>'}`.

3. **Repositories** em `backend/apps/auth_central/repositories.py`:
   - `AplicativoRepository.list_staff_apps()` — novo.
   - `ContaRepository` (novo classe ou função): `list_ativadas(limit=100)`.
   - `CatalogRepository.get_licencas_agrupadas_por_empresa(conta_id)` — novo.

4. **Views** em `backend/apps/auth_central/views.py`:
   - Helper `_require_staff(request)` → levanta `StaffOnlyAppError` se `not request.user.is_platform_staff`.
   - `StaffCatalogView` — GET `/api/v1/auth/staff/catalog` — `IsAuthenticated` + `_require_staff` + delega a `StaffCatalogService.listar_apps_e_contas`.
   - `StaffContaDetailView` — GET `/api/v1/auth/staff/catalog/<uuid:conta_id>` — idem + delega a `StaffCatalogService.licencas_da_conta`.
   - `StaffLaunchView` — POST `/api/v1/auth/staff/launch` — body `{app_key, empresa_id?}` (serializer `StaffLaunchSerializer` em `serializers.py`) + delega a `StaffLaunchService.emitir_code`. Mapeia exceções (`StaffOnlyAppError`→403, `AppKeyUnknownError`→400, `LicencaInativaError`→400, `AuthCentralError`→400).

5. **URLs** em `backend/apps/auth_central/urls.py`:
   ```python
   path('staff/catalog',                  StaffCatalogView.as_view(),     name='auth-central-staff-catalog'),
   path('staff/catalog/<uuid:conta_id>',  StaffContaDetailView.as_view(), name='auth-central-staff-catalog-detail'),
   path('staff/launch',                   StaffLaunchView.as_view(),      name='auth-central-staff-launch'),
   ```

**Acceptance:**
- AC-03, AC-04, AC-05, AC-06, AC-07 do PRD passam (revisitar AC-06 para confirmar que `acesso.modulos` reflete o plano contratado, não array vazio).
- Teste `tests/test_staff_catalog_service.py`:
  - staff lista apps `requires_staff=True` + contas `ativada`.
  - non-staff levanta `StaffOnlyAppError`.
- Teste `tests/test_staff_launch_service.py`:
  - Ramo A (Platform Admin): code emitido com `is_staff_app=True`, sem `empresa_id`. Sem `ImpersonationLog`.
  - Ramo A com `empresa_id` enviado → erro.
  - Ramo B (conta-cliente): code com `is_impersonation=True`, `ImpersonationLog` gravado.
  - Ramo B sem licença ativa → `LicencaInativaError`, code não emitido.
  - Non-staff → `StaffOnlyAppError`.
- Teste E2E: emitir code (ramo B) → redeem → JWT contém `acesso.is_owner=True` e `modulos` do plano.

**Arquivos tocados:**
- `backend/apps/auth_central/services/staff_catalog_service.py` (novo, ~80 linhas)
- `backend/apps/auth_central/services/staff_launch_service.py` (novo, ~90 linhas; cada método ≤ 30 linhas)
- `backend/apps/auth_central/repositories.py` (3 métodos novos)
- `backend/apps/auth_central/views.py` (3 views novas)
- `backend/apps/auth_central/serializers.py` (`StaffLaunchSerializer`)
- `backend/apps/auth_central/urls.py` (3 paths)
- `backend/apps/auth_central/exceptions.py` (confirmar `StaffOnlyAppError`, adicionar `LicencaInativaError` se Step 2 ainda não fez)
- `backend/apps/auth_central/tests/test_staff_catalog_service.py` (novo)
- `backend/apps/auth_central/tests/test_staff_launch_service.py` (novo)

---

### Step 4 — Frontend AUTH: feature `staff-catalog` (api, types, hooks, 2 páginas, guard) + rotas

**Complexidade:** média.

**O que fazer:**
1. Novo feature folder `frontend/apps/auth/src/features/staff-catalog/`:
   - **`types.ts`:** `StaffApp`, `StaffConta`, `StaffCatalogResponse`, `StaffEmpresaLicencas`, `StaffLicenca`, `StaffContaDetailResponse`, `StaffLaunchRequest`.
   - **`api.ts`** (única camada com HTTP):
     - `fetchStaffCatalog(token) → StaffCatalogResponse`
     - `fetchStaffConta(token, contaId) → StaffContaDetailResponse`
     - `launchStaff(token, app_key, empresa_id?) → { redirect_to }`
   - **`hooks.ts`:** `useStaffCatalog()`, `useStaffConta(contaId)` com TanStack Query (staleTime 60s).
   - **`components/StaffCatalogPage.tsx`:** 2 seções:
     - "Apps de plataforma" — grid de cards (reusa estilo de `AppCard`, mas componente próprio `StaffAppCard` que chama `launchStaff(token, app.key)` sem `empresa_id`).
     - "Contas ativas" — lista (busca client-side por nome/CNPJ, top 100 + indicador `total_contas` para futura paginação). Cada item navega a `/staff/catalog/:contaId`.
   - **`components/StaffAccountPage.tsx`:** header com nome da conta + breadcrumb voltar; lista de empresas; para cada empresa, grid de `StaffAppCard` com `empresa_id` (chama `launchStaff(token, app.key, empresa_id)`).
   - **`components/StaffGuard.tsx`:** lê `session.getUser()`, redireciona para `/catalog` se `user.is_platform_staff !== true`. Retorna `null` (sem flash) enquanto valida. **Não decodifica JWT** — usa `is_platform_staff` salvo no `session.save()` (Step 1 do backend já retorna esse campo).
2. Atualizar `frontend/apps/auth/src/app/router.tsx`:
   - `{ path: '/staff/catalog', element: <StaffGuard><StaffCatalogPage /></StaffGuard> }`
   - `{ path: '/staff/catalog/:contaId', element: <StaffGuard><StaffAccountPage /></StaffGuard> }`
3. Atualizar `frontend/apps/auth/src/shared/lib/session.ts`:
   - `AuthSession` ganha campo `is_platform_staff: boolean`.
   - `session.save(user, token)` mantém assinatura (user já vem com o campo).
4. `frontend/apps/auth/src/features/login/components/LoginPage.tsx:140-148`: já usa `result.redirect_to || '/catalog'` — comentar confirmando que `/staff/catalog` é tratado pelo backend. **Tipar `result.user.is_platform_staff` no `login/types.ts`.**
5. `frontend/apps/auth/src/features/login/types.ts`: incluir `is_platform_staff` em `LoginUserPayload`.

**Acceptance:**
- AC-09 passa (guard, sem flash).
- Playwright manual:
  - staff loga → cai direto em `/staff/catalog` com 2 seções visíveis.
  - clica em uma conta → `/staff/catalog/:contaId` mostra empresas + licenças.
  - clica numa licença → AUTH chama `/staff/launch` → redireciona para o app cliente; app cliente faz redeem; JWT chega com `acesso.is_owner=true`.
  - clica em Platform Admin → `/staff/launch` (sem `empresa_id`) → redireciona para callback do Platform Admin.
- Usuário não-staff que digita `/staff/catalog` direto na URL é redirecionado para `/catalog`.

**Arquivos tocados:**
- `frontend/apps/auth/src/features/staff-catalog/{types.ts,api.ts,hooks.ts}` (novos)
- `frontend/apps/auth/src/features/staff-catalog/components/{StaffCatalogPage,StaffAccountPage,StaffGuard,StaffAppCard}.tsx` (novos)
- `frontend/apps/auth/src/app/router.tsx` (+2 rotas)
- `frontend/apps/auth/src/shared/lib/session.ts` (+ campo `is_platform_staff`)
- `frontend/apps/auth/src/features/login/types.ts` (+ campo)
- `frontend/apps/auth/src/features/login/components/LoginPage.tsx` (apenas comentário/tipos)

---

### Step 5 — Platform Admin: switch para central auth (env, AuthCallbackPage, remoção do legacy login)

**Complexidade:** média-alta (toca rotas, layout e logout).

**O que fazer:**
1. **Env files**: criar `frontend/apps/platform/.env.development` e `.env.production`:
   ```
   VITE_API_BASE_URL=/api/v1
   VITE_AUTH_URL=http://localhost:5174   # dev (ajustar p/ prod: https://auth.gocontrol.com.br)
   VITE_APP_KEY=platform-admin
   VITE_USE_CENTRAL_AUTH=true
   ```
2. **Type**: adicionar `VITE_USE_CENTRAL_AUTH`, `VITE_AUTH_URL`, `VITE_APP_KEY` em `frontend/apps/platform/src/vite-env.d.ts`.
3. **AuthCallbackPage**: criar `frontend/apps/platform/src/features/auth-callback/AuthCallbackPage.tsx` copiando do `frontend/apps/account/src/features/auth-callback/AuthCallbackPage.tsx`. Trocar `APP_KEY='platform-admin'`.
4. **Router** (`frontend/apps/platform/src/app/router.tsx`):
   - Adicionar rota `/auth/callback` → `<AuthCallbackPage />`.
   - `PrivateRoute`: se `!auth.isAuthenticated()`:
     - Se `VITE_USE_CENTRAL_AUTH=true` → `window.location.href = \`${VITE_AUTH_URL}/login?redirect=${encodeURIComponent(window.location.href)}&app=platform-admin\``. Retorna `null` enquanto redireciona.
     - Caso contrário → `<Navigate to="/login" replace />` (fallback legado).
   - Esconder rotas `/login`, `/forgot-password`, `/reset-password`, `/change-password` atrás de `if (!useCentralAuth)`.
5. **PlatformLayout** (`frontend/apps/platform/src/components/PlatformLayout.tsx:54-69`):
   - **Remover** o check `if (!u.is_platform_staff) navigate('/login')` — autoridade passa para AUTH (Aplicativo `platform-admin` com `requires_staff=True`).
   - Manter fetch de `auth.me()` apenas para exibir nome/email no `sidebar-footer`.
6. **Logout**: substituir handler por `sessionManager.logout(VITE_AUTH_URL, VITE_API_BASE_URL)` (mesmo pattern dos outros apps).
7. **Lib `auth.ts`** (`frontend/apps/platform/src/lib/auth.ts`): delegar `getAccess`/`save`/`clear` para `@gocontrol/shell` (sessionManager). `isAuthenticated()` agora lê do session manager.
8. **Seed/data migration do Aplicativo `platform-admin`** (backend, mas necessário para Step 5 funcionar end-to-end):
   - Garantir `Aplicativo.objects.update_or_create(key='platform-admin', defaults={requires_staff=True, status='ativo', visivel_no_catalogo=False, url_login_callback='<URL>/auth/callback'})`.
   - Data migration ou comando `manage.py register_platform_admin`. Documentar como rodar em dev/prod.

**Acceptance:**
- AC-10 passa.
- Smoke E2E staff:
  - Abre `http://platform.gocontrol.local` (não autenticado) → AUTH redireciona com `?redirect=...&app=platform-admin` → login → callback faz redeem → entra no Platform Admin sem `/login` local.
  - Logout volta para `{authUrl}/login`.
- Smoke E2E não-staff:
  - Tenta abrir Platform Admin → AUTH bloqueia com `StaffOnlyAppError` (AC-07, backend).
- Build de produção do Platform Admin com `VITE_USE_CENTRAL_AUTH=true` passa.

**Arquivos tocados:**
- `frontend/apps/platform/.env.development`, `.env.production` (novos)
- `frontend/apps/platform/src/vite-env.d.ts`
- `frontend/apps/platform/src/features/auth-callback/AuthCallbackPage.tsx` (novo)
- `frontend/apps/platform/src/app/router.tsx`
- `frontend/apps/platform/src/components/PlatformLayout.tsx`
- `frontend/apps/platform/src/lib/auth.ts`
- Seed/data migration de `platform-admin` (em `backend/apps/platform/migrations/`)

---

### Step 6 — Backoffice admin: expor campos críticos do Aplicativo (serializer + UI)

**Complexidade:** baixa-média.

**Contexto:** o `AplicativoSerializer` do backoffice (`backend/apps/backoffice/platform/serializers.py`) e o formulário `PlatformAplicativosPage.tsx` (990 linhas) expõem apenas `url_producao` dos campos SSO-críticos. Os seguintes campos existem no modelo mas estão ausentes do serializer **e** da UI:

| Campo no Model | Impacto |
|---|---|
| `url_login_callback` | **Crítico** — redirect SSO; sem ele, nenhum app funciona no catálogo |
| `requires_staff` | **Crítico** — flag canônica do staff catalog; precisa ser editável na UI |
| `visivel_no_catalogo` | Controla visibilidade no catálogo de clientes |
| `url_upsell` | Link de upgrade quando licença inexistente |
| `descricao_curta` | Texto do card no catálogo |
| `icone_url` | URL do ícone (o serializer atual usa `icone` — imagem file upload) |

**O que fazer:**

1. **Backend — `backend/apps/backoffice/platform/serializers.py`**: adicionar ao `AplicativoSerializer.Meta.fields`:
   - `'url_login_callback'`, `'requires_staff'`, `'visivel_no_catalogo'`, `'url_upsell'`, `'descricao_curta'`, `'icone_url'`
   - Adicionar `read_only_fields` adequados (somente `id`, `key`, `created_at`, `updated_at`).
   - Manter `icone` (file upload) existente — `icone_url` é o campo complementar de URL externa.

2. **Frontend — `frontend/apps/platform/src/pages/PlatformAplicativosPage.tsx`**: adicionar os campos no formulário de edição/criação:
   - **Seção "SSO & Catálogo"** (nova seção no formulário, agrupada):
     - `url_login_callback` — campo de texto obrigatório, label "URL de Callback (SSO)"
     - `visivel_no_catalogo` — toggle/checkbox, label "Visível no catálogo de clientes"
     - `url_upsell` — campo de texto opcional, label "URL de Upsell"
     - `descricao_curta` — campo de texto opcional, label "Descrição Curta"
     - `icone_url` — campo de texto opcional, label "URL do Ícone"
   - **Campo `requires_staff`** — toggle/checkbox com destaque visual (tag badge "Staff Only"), label "App exclusivo de staff — oculto para clientes"
   - Seguir DS: toggle padrão (`.toggle-field`), labels em `.t-label`.

3. **Tipagem frontend** — atualizar a interface `Aplicativo` em `src/features/aplicativos/types.ts` (ou onde for declarada) para incluir os novos campos.

**Acceptance:**
- Admin consegue editar `url_login_callback` e `requires_staff` pelo Platform Admin sem tocar no Django shell.
- `GET /api/v1/backoffice/aplicativos/<id>/` retorna os 6 novos campos no JSON.
- `PATCH /api/v1/backoffice/aplicativos/<id>/` aceita alteração de `requires_staff` e persiste.
- Teste de regressão: campos existentes (`url_producao`, `status`, `modulos_count`, etc.) continuam funcionando.

**Arquivos tocados:**
- `backend/apps/backoffice/platform/serializers.py` (+6 campos em `AplicativoSerializer`)
- `frontend/apps/platform/src/pages/PlatformAplicativosPage.tsx` (+seção SSO & Catálogo + campo `requires_staff`)
- `frontend/apps/platform/src/features/aplicativos/types.ts` (ou equivalente)

---

### Step 7 — ADR-006 + symlinks + verificação + QA + retro

**Complexidade:** baixa.

**O que fazer:**
1. **ADR-006** em `/home/evonexus/evo-projects/go-control-erp/docs/decisions/ADR-006-staff-catalog-auth.md` (formato Decision/Drivers/Alternatives/Consequences/Follow-ups). Registrar:
   - AUTH = autenticador único da plataforma.
   - `Aplicativo.requires_staff` é a flag canônica de "app staff-only".
   - Impersonação implementada via flags `is_impersonation` e `is_staff_app` em `AuthorizationCode` (decisão por código no emit, não inferência no redeem).
   - Em modo impersonação, `acesso.modulos` reflete plano contratado da empresa (`resolve_permissions_for_impersonation`).
   - Staff é exclusivamente administrativo — sem vínculo de cliente (Q4).
   - `ImpersonationLog` gravado em todo launch ramo B.
2. **Symlinks** em `evo-nexus/workspace/projects/go-control-erp/` (regra `feedback_go_control_workspace_symlinks`):
   - Symlink já criado para a pasta `staff-catalog-auth/`. Garantir que o ADR-006 também apareça (symlink direto ou referência).
3. **Verificação (@oath-verifier):**
   - `make test-backend` + `make test-frontend` verdes.
   - Cada AC do PRD (AC-01 a AC-12) mapeado com evidência (output de teste, screenshot Playwright).
4. **QA exploratório (@probe-qa):**
   - Staff inicia sessão impersonando empresa X; admin altera plano da empresa X (remove módulo). Próximo refresh respeita o novo plano?
   - Staff abre Platform Admin e simultaneamente impersona em GO Message — JWT do GO Message tem `is_owner=true`; JWT do Platform Admin é `platform_staff`. Não há vazamento entre eles.
   - Code expira (60s) → redeem retorna 410 (regressão).
5. **Retro (@mirror-retro)**: `[C]retro-staff-catalog-auth.md` na mesma feature folder; propor memory updates (ex.: pattern de flags persistentes em `AuthorizationCode` para variantes de redeem).

**Acceptance:**
- 12 ACs do PRD com evidência PASS.
- ADR-006 commitado.
- Retro arquivado.

**Arquivos tocados:**
- `docs/decisions/ADR-006-staff-catalog-auth.md` (novo)
- `workspace/development/features/staff-catalog-auth/[C]verification-staff-catalog-auth.md` (Oath)
- `workspace/development/features/staff-catalog-auth/[C]retro-staff-catalog-auth.md` (Mirror)

---

## Success criteria checklist

- [ ] AC-01 a AC-12 do PRD: PASS.
- [ ] `make test-backend` verde.
- [ ] `make test-frontend` verde.
- [ ] Bundle production de `frontend/apps/platform` com `VITE_USE_CENTRAL_AUTH=true`.
- [ ] Bundle production de `frontend/apps/auth` com novas rotas `/staff/*`.
- [ ] ADR-001 não violado (arquivo ≤ 300 linhas, método ≤ 30 linhas).
- [ ] Nenhum `axios.get`/`fetch(` dentro de componente React.
- [ ] Nenhum `Aplicativo` legítimo do catálogo cliente sumiu (AC-08).
- [ ] `AuthorizationCode` com `is_impersonation=True` sempre tem `ImpersonationLog` correspondente (cross-check via teste).
- [ ] `acesso.modulos` em impersonação **reflete plano contratado** (não vazio, não inclui módulos fora do plano).
- [ ] Zero `UserLicenca` criado para staff em qualquer caminho do código (assert em teste).
- [ ] Apex assinou ADR-006 antes do Step 5 implementar.
- [ ] Admin consegue editar `url_login_callback` e `requires_staff` pelo Platform Admin (Step 6).
- [ ] `GET /api/v1/backoffice/aplicativos/<id>/` retorna todos os 6 campos novos (Step 6).

---

## Open questions

Todas as 4 perguntas críticas foram fechadas por Eduardo em 2026-05-29. Restam apenas defaults Compass (ver `workspace/development/plans/[C]open-questions.md` para registro):

- **Q5 (default)** — Logout do Platform Admin via `sessionManager.logout(...)` ✓ aceito.
- **Paginação de contas** — 100 + busca client-side; backend retorna `total_contas` ✓ aceito.
- **Apelido `staff_only` em serializers** — Sim, expor como `staff_only` no JSON do staff catalog, mantendo `requires_staff` no DB ✓ aceito.

---

## Handoff

**Compass → Apex:** plano atualizado com Q1–Q4 fechadas. Próxima entrada: `[C]architecture-staff-catalog-auth.md` (ADR-006). Apex confirma o desenho dos 2 flags em `AuthorizationCode` e a função `resolve_permissions_for_impersonation`; refina shape do payload se necessário.

**Apex → Bolt:** após ADR-006, Bolt implementa Step 1 → 2 → 3 → 4 → 5 em PRs separados (um por step), com testes em cada PR. Step 5 depende do Step 2 (flags) e Step 3 (endpoint launch).

**Bolt → Oath:** ao final do Step 5 (+ Step 6), @oath-verifier roda verificação completa antes do Step 7.
