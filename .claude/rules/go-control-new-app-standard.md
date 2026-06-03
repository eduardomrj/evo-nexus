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

---

## Checklist obrigatório — Backend (todo novo app)

- [ ] App Django em `backend/apps/<nome_app>/` seguindo ADR-001 (views → services → repositories → models)
- [ ] `manifest.json` na raiz do app declarando módulos e recursos
- [ ] `AppConfig.ready()` ou signal de startup: push do manifest ao Platform Admin
- [ ] `AplicativoContextMiddleware` wired com o URL prefix do app
- [ ] `HasLicensedPermission` nos views que requerem módulo licenciado
- [ ] Exceções de domínio em `exceptions.py` — nunca `ValueError`/`Exception` genérico

---

## Critérios de rejeição — Frontend

Qualquer entrega de frontend GO Control que apresente:
- Layout próprio sem sidebar/topbar/content do DS
- Fontes que não sejam IBM Plex
- Menus hardcoded em vez de consumir `/api/v1/erp/modules/`
- `axios`/`fetch` diretamente em componente React (deve estar em `features/*/api.ts`)
- Ausência de skeleton/empty state
- CRUD em modal centralizado em vez de side panel

…é **rejeitada** independentemente de funcionalidade.

---

## Modelo de referência

O GO Message é o app mais maduro na plataforma:
- Backend: `backend/apps/go_message/`
- Frontend: `frontend/apps/go-message/`
- Layout: `frontend/apps/go-message/src/components/layout/GoMessageLayout.tsx`
- Licença client: `backend/apps/go_message/services/licenca_client.py`

Para qualquer dúvida de padrão, ler o GO Message primeiro.
