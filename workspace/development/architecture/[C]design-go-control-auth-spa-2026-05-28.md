# Design Implementation — GO Control Auth SPA (Step 2)

## Aesthetic Direction

- **Purpose:** App de autenticação central (SSO-like) para toda a plataforma GO Control. Ponto de entrada de todos os usuários antes de qualquer app.
- **Tone:** Profissional, confiável, limpo. Inspiração Zoho One. Nenhum elemento decorativo supérfluo — o formulário de login é o único protagonista.
- **Constraints:** Sem sidebar, sem topbar pesada. Layout centrado. Card max-width 420px (login), 560px (empresa), 900px (catálogo). Dark theme obrigatório.
- **Differentiation:** Grid pattern sutil no fundo (linhas azuis com 3% opacidade), logo-mark com glow de `--primary`, transições de 100ms nos cards de empresa e app. Tipografia IBM Plex Sans — sem Inter, sem system fonts.

## Framework

- Detected: React 18 + Vite 5 + TypeScript strict
- Patterns matched: GoMessageLayout (sidebar/nav pattern), shared LoginPage (form pattern), packages/shared/lib/auth.ts (API call pattern)
- Feature folder structure: `features/{domain}/api.ts + components/`

## Components Created/Modified

- `frontend/apps/auth/src/shared/components/AuthLayout.tsx` — wrapper centrado com logo, card e footer. Props: `appSub`, `wide` (900px), `md` (560px), `noCard`.
- `frontend/apps/auth/src/shared/lib/api.ts` — axios instance para `VITE_AUTH_API_URL`. Sem interceptor de refresh (Auth é emissor, não consumidor).
- `frontend/apps/auth/src/shared/lib/session.ts` — sessionStorage manager para `auth_user` e `auth_token_hint`. Usado pela CatalogPage.
- `frontend/apps/auth/src/features/login/api.ts` — `loginApp()`, `validateRedirect()`, `selectEmpresaAndEmitCode()`
- `frontend/apps/auth/src/features/login/components/LoginPage.tsx` — validação anti open-redirect no boot, todos os stages do backend (done/select_empresa/no_access/force_password_change)
- `frontend/apps/auth/src/features/empresa-select/components/SelectEmpresaPage.tsx` — grid 2 colunas de cards de empresa
- `frontend/apps/auth/src/features/catalog/components/CatalogPage.tsx` — auto-redirect B11, agrupamento por empresa, skeleton, empty state
- `frontend/apps/auth/src/features/catalog/components/AppCard.tsx` — card 180×140px, overlay de cadeado com botão "Adquirir"
- `frontend/apps/auth/src/features/lockout/components/LockoutPage.tsx` — 4 variantes configuradas (no_app_license, account_locked, user_inactive, force_password_change_required)
- `frontend/apps/auth/src/features/password/components/ForgotPasswordPage.tsx` — sem app_key (C12)
- `frontend/apps/auth/src/features/password/components/ResetPasswordPage.tsx` — token via ?token querystring
- `frontend/apps/auth/src/features/password/components/ChangePasswordPage.tsx` — token provisional de force_password_change
- `frontend/apps/auth/src/features/redirect-error/components/RedirectErrorPage.tsx` — URL rejeitada com motivo

## Design Choices

- **Typography:** IBM Plex Sans (400/500/600/700) + IBM Plex Mono para CNPJ e códigos. Importado via Google Fonts em index.html.
- **Color:** `--bg: #0F1117`, `--surface-a: #1A1D26`, `--surface-b: #22263A`, `--primary: #4F6AF5`, `--border: #2E3347`. Paleta herdada do DS GO Control via `@go-control/shared/styles/tokens.css`.
- **Motion:** hover nos app-cards (`translateY(-1px)` em 100ms), transição de cor em botões/links (100ms), spinner PrimeIcons durante loading.
- **Layout:** centrado vertical + horizontal, auth-root com grid pattern sutil (`3%` opacidade azul), card com `border-radius: 12px` (mais arredondado que o padrão 4px do DS para dar sensação de "janela de entrada").

## Rotas

| Path | Componente |
|---|---|
| `/login?redirect=&app=` | LoginPage (valida redirect antes de renderizar) |
| `/select-empresa` | SelectEmpresaPage (recebe state do loginApp) |
| `/catalog` | CatalogPage (requer auth_token_hint em sessionStorage) |
| `/lockout/:variant` | LockoutPage (4 variantes) |
| `/forgot` | ForgotPasswordPage |
| `/reset?token=` | ResetPasswordPage |
| `/change-password` | ChangePasswordPage (usa sessionStorage force_change_token) |
| `/redirect-error` | RedirectErrorPage |
| `*` | redirect /login |

## Porta

- Dev: **5182** (5180=go-message, 5181=go-cobranca já ocupadas)
- Build: `pnpm --filter @go-control/auth-app build`
- Dev:   `pnpm run dev:auth` (script adicionado ao frontend/package.json)

## Verificação

- ✅ `tsc` sem erros (strict mode)
- ✅ `vite build` em 4.16s — 206 módulos transformados, sem erros
- ✅ IBM Plex Sans/Mono — nunca Inter/Roboto
- ✅ Dark theme com tokens canônicos do DS
- ✅ `axios`/`fetch` jamais direto em componente — sempre via `features/*/api.ts`
- ✅ Skeleton + empty state em CatalogPage
- ✅ 4 variantes de LockoutPage implementadas
- ✅ Anti open-redirect: validateRedirect() chamado no boot do LoginPage antes de exibir form
- ✅ ADR-004 compatível: app standalone, sem dependência de login embarcado
- ✅ Padrão de feature folder: `api.ts` + `components/` por feature

## Pendências para Steps seguintes

- Step 3 (`@gocontrol/shell`): CatalogPage ainda usa sessionStorage próprio — o shell vai substituir por seu sessionManager
- Step 5: Manifest `auth/manifest.json` para registro via ADR-004 (Step 5 cuida de healthz + manifest)
- Step 6: E2E Playwright para `/login → redirect → lockout` e anti open-redirect
