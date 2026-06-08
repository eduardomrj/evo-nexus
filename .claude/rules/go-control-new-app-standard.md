# GO Control ERP — Padrão de Construção de Novo Aplicativo

Applies to every agent (Bolt, Canvas, Compass, Apex, etc.) that creates or scaffolds any new application under the GO Control platform at `/home/evonexus/evo-projects/go-control-erp/`.

**NEVER treat a GO Control frontend as a scaffold.** Every app is a first-class platform citizen from day one.

---

## Documentos obrigatórios a ler antes de qualquer código

```
/home/evonexus/evo-projects/go-control-erp/docs/design-system.md
/home/evonexus/evo-projects/go-control-erp/docs/decisions/ADR-004-app-platform-contract.md
/home/evonexus/evo-projects/go-control-erp/docs/decisions/ADR-001-architecture-standards.md
```

Referência de layout implementado:
```
/home/evonexus/evo-projects/go-control-erp/frontend/apps/platform/src/components/PlatformLayout.tsx
/home/evonexus/evo-projects/go-control-erp/frontend/packages/shared/src/components/BackofficeLayout.tsx
```

---

## Checklist obrigatório — Frontend (todo novo app)

### 1. Layout Base (DS Seção 3)
- [ ] Criar `src/components/<NomeApp>Layout.tsx` baseado no `PlatformLayout.tsx`
- [ ] Estrutura: `<div class="app"> → <aside class="sidebar"> → <div class="main"> → <header class="topbar"> → <main class="content">`
- [ ] Sidebar: logo com sub-label do app, nav dinâmico (ver item 3), sidebar-footer com usuário + logout
- [ ] Topbar: breadcrumb + espaço para ações

### 2. Design System (DS Seções 2–18)
- [ ] Fonte: `IBM Plex Sans` / `IBM Plex Mono` — **nunca Inter, Roboto ou system fonts**
- [ ] Tokens de cor: `--bg`, `--surface-a/b/c`, `--text`, `--text-muted`, `--primary`, `--border`
- [ ] Toda página começa com `.page-header` (título + subtitle com contagem + `.header-actions`)
- [ ] Tabelas: `.table-wrap > table` com `<th class="t-label">`, `.badge-*` para status, `.btn-icon` para ações inline
- [ ] Botões: `.btn.btn-primary`, `.btn.btn-secondary`, `.btn.btn-danger` — altura `36px`
- [ ] CRUD via side panels (`--panel-md`), não modais centralizados
- [ ] Pipeline obrigatório: filter → sort → paginate (PAGE_SIZE=20)
- [ ] Skeleton + empty state em todo `useQuery`

### 3. Integração ADR-004 — Menu dinâmico via Platform
- [ ] No startup do backend: registrar `manifest.json` via `POST /api/v1/platform/apps/register`
- [ ] Layout consome `/api/v1/erp/modules/?aplicativo_key=<key>` para montar o nav da sidebar
- [ ] Respeitar `sem_licenca_comportamento`: `ocultar` → não renderiza; `cadeado` → renderiza com lock + `upsell_url`
- [ ] `LicencaHTTPClient` no backend com cache Redis TTL 900s (modelo: `apps/go_message/services/licenca_client.py`)
- [ ] Backend retorna HTTP 403 com `upgrade_required + modulo + upsell_url` quando módulo não licenciado

### 4. Autenticação e service token
- [ ] App registra `AplicativoServiceToken` no Platform Admin (scope `app:register` + `app:read`)
- [ ] Token armazenado como `PLATFORM_SERVICE_TOKEN` no `.env` do app

### 5. Auth central (obrigatório — sem login próprio)
- [ ] **Nenhum app tem página de login própria.** Toda autenticação passa pelo app AUTH.
- [ ] `router.tsx` usa `AuthGuard` + `/auth/callback` (sem `legacyRouter`, sem `/login`)
- [ ] `providers.tsx` usa `ShellProvider` + `AuthProvider` + `AccessDeniedProvider`
- [ ] `AuthCallbackPage` chama `sessionManager.handleAuthCallback()` e navega para `/` em sucesso e falha
- [ ] `vite.config.ts` — proxy `/api/v1/auth/` → admin backend (**porta 8000**) **antes** da entrada genérica `/api/`
  ```ts
  proxy: {
    '/api/v1/auth': { target: 'http://localhost:8000', changeOrigin: true },
    '/api/':        { target: 'http://localhost:<PORTA_DO_APP>', changeOrigin: true },
  }
  ```
  > **Motivo:** `redeem-code`, `token/refresh` e `logout` existem no admin backend (auth_central).
  > Se o proxy do app aponta para outro backend, o callback falha e o usuário fica em loop.
- [ ] `.env.development` — sem `VITE_USE_CENTRAL_AUTH` (flag removida); variáveis mínimas:
  ```
  VITE_APP_KEY=<app-key>
  VITE_API_BASE_URL=/api/v1
  VITE_AUTH_URL=https://auth.myworkhome.com.br
  ```

---

## Checklist obrigatório — Backend (todo novo app)

- [ ] App Django em `backend/apps/<nome_app>/` seguindo ADR-001 (views → services → repositories → models)
- [ ] `manifest.json` na raiz do app declarando módulos e recursos
- [ ] `AppConfig.ready()` ou signal de startup: push do manifest ao Platform Admin
- [ ] `AplicativoContextMiddleware` wired com o URL prefix do app
- [ ] `HasLicensedPermission` nos views que requerem módulo licenciado
- [ ] Exceções de domínio em `exceptions.py` — nunca `ValueError`/`Exception` genérico

### JWT — chave de assinatura compartilhada (CRÍTICO)

> **Todo backend GO Control valida tokens emitidos pelo auth central.**
> A chave de assinatura (`JWT_SIGNING_KEY`) deve ser **idêntica** em todos os backends.
> Sem ela, o backend cai no fallback `SECRET_KEY` → tokens do auth são rejeitados → 401 em tudo.

- [ ] `.env` contém `JWT_SIGNING_KEY=<valor compartilhado>` — **mesma chave** do auth e admin backends
- [ ] `SIMPLE_JWT["SIGNING_KEY"]` no `settings/base.py` lê `config("JWT_SIGNING_KEY", default=SECRET_KEY)`
- [ ] Verificar: `grep JWT_SIGNING_KEY /home/evonexus/evo-projects/go-control/go-control-admin/backend/.env` e usar o mesmo valor

Backends de referência que já têm a chave correta:
```
go-control-admin/backend/.env   → JWT_SIGNING_KEY=...
go-control-auth/backend/.env    → JWT_SIGNING_KEY=...  (mesmo valor)
go-control-account/backend/.env → JWT_SIGNING_KEY=...  (mesmo valor)
```

---

## Critérios de rejeição — Frontend

Qualquer entrega de frontend GO Control que apresente:
- Layout próprio sem sidebar/topbar/content do DS
- Fontes que não sejam IBM Plex
- Menus hardcoded em vez de consumir `/api/v1/erp/modules/`
- `axios`/`fetch` diretamente em componente React (deve estar em `features/*/api.ts`)
- Ausência de skeleton/empty state
- CRUD em modal centralizado em vez de side panel
- Página `/login` própria (qualquer `LoginPage`, `RequireAuth`, `legacyRouter`)
- `VITE_USE_CENTRAL_AUTH` no código ou nos arquivos `.env`
- Proxy Vite sem entrada `/api/v1/auth/` → porta 8000 antes da entrada genérica

…é **rejeitada** independentemente de funcionalidade.

## Critérios de rejeição — Backend

Qualquer entrega de backend GO Control que apresente:
- `.env` sem `JWT_SIGNING_KEY` (ou com valor diferente dos outros backends)
- `SIMPLE_JWT["SIGNING_KEY"]` hardcoded em vez de `config("JWT_SIGNING_KEY", default=SECRET_KEY)`

…é **rejeitada** independentemente de funcionalidade.

---

## Modelo de referência

O GO Message é o app mais maduro na plataforma:
- Backend: `backend/apps/go_message/`
- Frontend: `frontend/apps/go-message/`
- Layout: `frontend/apps/go-message/src/components/layout/GoMessageLayout.tsx`
- Licença client: `backend/apps/go_message/services/licenca_client.py`

Para qualquer dúvida de padrão, ler o GO Message primeiro.
