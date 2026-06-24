# [C] Tasks — Error Pages no go-control-sdk

**Feature:** error-pages · **Projeto:** go-control-erp / go-control-sdk
**Plano:** `[C]plan-error-pages.md` · **Owner execução:** @bolt-executor

> **Status: IMPLEMENTADO — 2026-06-20** (parte do ADR-015 STEP-3; Oath PASS 2026-06-23)

Dependências: T-02 e T-03 dependem de T-01 · T-04 depende de T-01 · T-05 depende de T-01..T-04 · T-06 depende de T-05.

---

## T-01 — Componente `ErrorPage` autossuficiente
Status: [x] **CONCLUÍDO** — commit `179e772`
Arquivo(s): `/home/evonexus/evo-projects/go-control/go-control-sdk/typescript/src/shared/components/ErrorPage.tsx`
Evidência: arquivo criado com `PRESETS` (404/500/503/0-network + fallback genérico), `ensureErrorPageStyles()` via injeção `<style>` idempotente com tokens `var(--bg/surface-a/text/primary/border/radius)`, layout full-screen com ícone PrimeIcons. Props sobrescrevem preset. Sem dependência de classes `login-*`.

---

## T-02 — Exportar `ErrorPage` no barrel
Status: [x] **CONCLUÍDO** — commit `179e772`
Arquivo(s): `/home/evonexus/evo-projects/go-control/go-control-sdk/typescript/src/shared/index.ts`
Evidência: linhas 52-53 — `export { ErrorPage }` + `export type { ErrorPageProps }`.

---

## T-03 — Wildcard `*` → `ErrorPage code=404` (breaking, default)
Status: [x] **CONCLUÍDO** — commit `179e772`
Arquivo(s): `/home/evonexus/evo-projects/go-control/go-control-sdk/typescript/src/shell/router.tsx`
Evidência: `notFoundRedirect?: boolean` adicionado a `AppRouterConfig` (default `false`); wildcard usa `<ErrorPage code={404} />` por padrão; com `notFoundRedirect: true` volta a `<Navigate to={fallback} replace />`. JSDoc atualizado.
Nota: além do plano original, também foi adicionada rota pública `/app-error` (`AppErrorPage`) para navegação programática com query params `?code=&title=&message=` — usada pelos apps para redirecionar erros de resolução de URL (ADR-015 STEP-3).

---

## T-04 — `errorElement` no protectedRoute → `ErrorPage code=500`
Status: [x] **CONCLUÍDO** — commit `179e772`
Arquivo(s): `/home/evonexus/evo-projects/go-control/go-control-sdk/typescript/src/shell/router.tsx`
Evidência: linha 116 — `errorElement: <ErrorPage code={500} />` no `protectedRoute`. Throw em rota protegida renderiza ErrorPage 500 em vez de tela branca.

---

## T-05 — Typecheck + build do SDK
Status: [x] **CONCLUÍDO**
Arquivo(s): `/home/evonexus/evo-projects/go-control/go-control-sdk/typescript/`
Evidência: `tsc --noEmit` limpo (0 erros). Versão bumped para `1.3.0` (minor — breaking com escape hatch). `dist/` atualizado com `ErrorPage` e `ErrorPageProps` expostos.

---

## T-06 — Não-regressão + comunicação do breaking change
Status: [x] **CONCLUÍDO**
Evidência:
- `apiClient.ts` e `AuthGuard.tsx` não foram tocados (escopo restrito ao STEP-3 do ADR-015)
- Versão bumped para `1.3.0` (minor, dado que breaking tem escape hatch `notFoundRedirect`)
- Breaking change: wildcard `*` agora renderiza `ErrorPage 404` por padrão em vez de `<Navigate to={fallback} replace />`. Apps que dependem do redirect silencioso devem passar `notFoundRedirect: true`.
- OQ3 (minor vs major): resolvido como minor — escape hatch `notFoundRedirect` preserva retrocompatibilidade para quem precisar.
