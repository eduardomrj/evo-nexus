# Verificação — Force Password Change

**Feature slug:** `force-password-change`
**Projeto:** GO Control ERP
**Owner:** Oath (Phase 5)
**Data:** 2026-05-24
**Status:** PASS

---

## Evidências por Acceptance Criterion

### AC1 — Backend: POST /auth/change-password/ funcional em camadas
**PASS** — Endpoint implementado em 5 camadas (view ≤15 linhas, service, repository, serializer, exceptions). View em `backend/apps/accounts/views.py`, service em `services.py`, repository em `repositories.py`, exceções tipadas em `exceptions.py`.

### AC2 — 5 testes backend passando
**PASS** — `pytest backend/apps/accounts/tests/test_change_password.py` → 5/5 passando:
1. Happy path — flag vira False, senha nova autentica
2. Senha curta → 400 `code=password_too_short`
3. Mismatch → 400 `code=password_mismatch`
4. Senha igual à atual → 400 `code=password_unchanged`
5. Sem autenticação → 401

### AC3 — ChangePasswordPage único em packages/shared/
**PASS** — `frontend/packages/shared/src/components/ChangePasswordPage.tsx` — única definição. 4 apps importam do shared.

### AC4 — lib/auth.ts com changePassword() e fetchMe()
**PASS** — `auth.changePassword(newPassword, confirmPassword)` e `auth.fetchMe()` implementados em `frontend/packages/shared/src/lib/auth.ts`.

### AC5 — Guard funcional: usuário com flag não escapa para outras rotas
**PASS** — `RequireAuth.tsx` com guard `user?.force_password_change && location.pathname !== '/change-password'` → redireciona para `/change-password`.

### AC6 — 4 apps registram a rota /change-password
**PASS** — Rota registrada em todos os 4 routers (account, erp, go-message, platform).

### AC7 — Smoke manual: login com flag → tela aparece → troca → flag zera → vai para /
**PASS** — Testado manualmente no app go-message.

### AC8 — Zero regressão para usuários sem flag
**PASS** — Confirmado após fix do bug de login (ver seção Bugs Encontrados).

### AC9 — Sem duplicação de lógica nos apps
**PASS** — Toda lógica em `packages/shared/`. Nenhum app tem implementação própria.

---

## Bugs Encontrados e Corrigidos

### Bug crítico: login não funcionava após logoff

**Sintoma:** Após fazer logoff e re-login, o usuário era redirecionado de volta para `/login` sem mensagem de erro.

**Causa raiz:** O `RequireAuth` tinha **duas fontes** de checagem de autenticação:
1. `if (!auth.isAuthenticated())` → direto no localStorage (sempre atualizado)
2. `if (!isAuthenticated)` → do `useAuthContext()` (valor do contexto)

O `AuthProvider` não re-renderiza quando `saveFinalTokens()` salva o token — ele é pai do `RouterProvider`, e em React o estado não propaga para cima. O valor `isAuthenticated` do contexto ficava `false` stale do momento do carregamento inicial (sem token, após logout). A segunda checagem disparava `<Navigate to="/login" replace />` mesmo com token válido.

**Fix:** Removidas as checagens `if (isLoading && !isAuthenticated)` e `if (!isAuthenticated)` que usavam o valor stale do contexto. A única fonte de verdade é `auth.isAuthenticated()` direto (linha 24 de `RequireAuth.tsx`).

**Arquivo:** `frontend/packages/shared/src/components/RequireAuth.tsx`

---

## Success Criteria Checklist

- [x] Endpoint backend implementado em 5 camadas
- [x] 5 testes backend passando
- [x] `ChangePasswordPage` único em `packages/shared/`
- [x] `lib/auth.ts` com `changePassword()` e `fetchMe()`
- [x] Guard funcional: usuário com flag não escapa para outras rotas
- [x] 4 apps registram a rota e importam do shared
- [x] Smoke manual: login com flag → tela aparece → troca → flag zera → vai para `/`
- [x] Sem regressão: usuário sem flag faz login normalmente
- [x] Symlinks em `workspace/projects/go-control-erp/features/force-password-change/`

**Veredicto: PASS**
