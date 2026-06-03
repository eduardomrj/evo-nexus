# Plano de Execução — Force Password Change

**Feature slug:** `force-password-change`
**Projeto:** GO Control ERP (`/home/evonexus/evo-projects/go-control-erp/`)
**Owner do plano:** Compass (Phase 2)
**PRD:** `[C]prd-force-password-change.md` (mesma pasta)
**Data:** 2026-05-24
**Status:** ENTREGUE — 2026-05-24

---

## Contexto

O backend já carrega `force_password_change` no model `User` e o devolve em `/api/v1/auth/me/`. Falta toda a parte interativa: endpoint de troca, tela compartilhada, redirect pós-login e guard de rota nos 4 apps frontend.

## Objetivos testáveis

1. Usuário com flag ligado **não consegue** chegar em `/` sem trocar a senha.
2. Após a troca, `force_password_change` vira `False` e a navegação destrava.
3. Zero regressão para usuários sem o flag.

## Guardrails

### Must Have
- Endpoint backend em **3 camadas** (view → service → repository), serializer próprio, exceção própria.
- Componente compartilhado em `packages/shared/` — **um único** `ChangePasswordPage`.
- Guard no `RequireAuth` (ou wrapper irmão) que intercepta `force_password_change = True`.
- Testes backend cobrindo happy path + 4 cenários de erro.

### Must NOT Have
- Lógica de troca de senha duplicada em qualquer app (DRY no shared).
- Chamada `axios`/`fetch` em componente React (deve passar por `lib/auth.ts` ou `features/*/api.ts`).
- `raise ValueError` ou `raise Exception` no service/view.
- Arquivo > 300 linhas ou método > 30 linhas.
- Política de senha "criativa" (sem checagem de maiúsculas/símbolos nesta entrega — só ≥8 chars + diferente da atual).

---

## Etapas (5 steps)

### Step 1 — Backend: endpoint `POST /api/v1/auth/change-password/` em camadas (ADR-001)

**Arquivos a criar / tocar:**
- `backend/apps/accounts/serializers.py` — adicionar `ChangePasswordSerializer` (campos: `new_password`, `confirm_password`).
- `backend/apps/accounts/exceptions.py` (criar se não existir) — exceções `PasswordTooShortError`, `PasswordMismatchError`, `PasswordUnchangedError` (todas com `code` enum).
- `backend/apps/accounts/services.py` — método `AccountsService.change_password(user, new_password, confirm_password)` que valida, chama repository, zera o flag.
- `backend/apps/accounts/repositories.py` — método `UserRepository.set_password_and_clear_force_flag(user, raw_password)` (única camada que toca ORM).
- `backend/apps/accounts/views.py` — adicionar `ChangePasswordView` (DRF `APIView`, `permission_classes=[IsAuthenticated]`).
- `backend/apps/accounts/urls.py` — registrar rota `change-password/` → `ChangePasswordView`.

**Acceptance criteria:**
- **Given** usuário autenticado | **When** POST com payload válido | **Then** 200, `force_password_change=False`, senha persistida.
- **Given** payload com `password_too_short` / `password_mismatch` / `password_unchanged` | **When** POST | **Then** 400 com `{ "detail": "...", "code": "..." }`.
- **Given** request sem auth | **When** POST | **Then** 401.
- View ≤ 30 linhas, sem regra de domínio. Toda regra em `services.py`. Toda query ORM em `repositories.py`.

**Complexidade:** Média (3-4h).

---

### Step 2 — Backend: testes unitários + integração

**Arquivos a tocar:**
- `backend/apps/accounts/tests/test_change_password_service.py` (novo) — testes do service isoladamente (mock do repository).
- `backend/apps/accounts/tests/test_change_password_view.py` (novo) — testes de integração via DRF `APIClient`.

**Casos mínimos:**
1. Happy path — flag vira False, senha nova autentica.
2. Senha curta → 400 com `code=password_too_short`.
3. Mismatch entre `new_password` e `confirm_password` → 400 com `code=password_mismatch`.
4. Senha igual à atual → 400 com `code=password_unchanged`.
5. Sem autenticação → 401.

**Acceptance criteria:**
- **Given** suite rodando | **When** `pytest backend/apps/accounts/tests/test_change_password_*.py` | **Then** 5/5 passam.
- Cobertura: as 4 exceções de `exceptions.py` são exercidas ao menos 1 vez.

**Complexidade:** Baixa (1-2h).

---

### Step 3 — Frontend shared: `ChangePasswordPage` + lib auth

**Arquivos a criar / tocar:**
- `frontend/packages/shared/src/components/ChangePasswordPage.tsx` (novo) — espelha estrutura do `LoginPage.tsx` (form, useState, submit, error display). PrimeReact `Password` + `Button`. Prop opcional `appName`.
- `frontend/packages/shared/src/components/ChangePasswordPage.css` (novo) — CSS irmão, mesmo padrão visual do `LoginPage.css`.
- `frontend/packages/shared/src/lib/auth.ts` — adicionar:
  - `changePassword(newPassword, confirmPassword): Promise<{ok: boolean, error?: {detail, code}}>` que chama `POST /auth/change-password/`.
  - Helper `mustChangePassword(): boolean` que lê o último `/auth/me/` em cache (ou refaz a chamada).
- `frontend/packages/shared/src/index.ts` — exportar `ChangePasswordPage`.

**Acceptance criteria:**
- **Given** componente em `packages/shared/` | **When** importado por qualquer app | **Then** renderiza form, valida client-side (≥8 chars + match) antes de enviar.
- **Given** submit com 400 do backend | **When** resposta recebida | **Then** mensagem do `detail` aparece no form.
- **Given** submit com 200 | **When** resposta recebida | **Then** `useNavigate('/')` é disparado.
- Zero `axios`/`fetch` direto no `.tsx` — toda chamada de rede via `auth.changePassword()`.

**Complexidade:** Média (3-4h).

---

### Step 4 — Frontend shared: guard pós-login + redirect

**Arquivos a tocar:**
- `frontend/packages/shared/src/components/LoginPage.tsx` — após `saveFinalTokens(...)`, antes de `onAfterLogin()`, chamar `/auth/me/` (ou usar valor já retornado pelo login se vier embutido). Se `force_password_change === true`, navegar para `/change-password` em vez de seguir o fluxo normal.
- `frontend/packages/shared/src/components/RequireAuth.tsx` — adicionar verificação: se rota atual ≠ `/change-password` E `force_password_change === true`, redirecionar para `/change-password`. Isso bloqueia tentativa de navegar para `/` digitando na barra de URL.
- (Opcional, decisão de OQ4) — adicionar botão "Sair" no `ChangePasswordPage` que chama `auth.logout()`.

**Acceptance criteria:**
- **Given** usuário com flag faz login | **When** `saveFinalTokens` completa | **Then** navegação vai para `/change-password`, não para `/`.
- **Given** usuário com flag tenta digitar `/empresas` na URL | **When** `RequireAuth` monta | **Then** redireciona para `/change-password`.
- **Given** usuário sem flag faz login | **When** fluxo normal | **Then** vai para `/` (zero regressão).
- **Given** usuário acabou de trocar a senha (flag agora False) | **When** navega para `/` | **Then** acessa normalmente.

**Complexidade:** Média (2-3h) — requer atenção para não criar loop de redirect.

---

### Step 5 — Frontend apps: registrar rota `/change-password` nos 4 routers

**Arquivos a tocar:**
- `frontend/apps/account/src/app/router.tsx`
- `frontend/apps/erp/src/app/router.tsx`
- `frontend/apps/go-message/src/app/router.tsx`
- `frontend/apps/platform/src/app/router.tsx`

Em cada um:
```tsx
import { ChangePasswordPage, RequireAuth } from '@go-control/shared';
// ...
{
  path: '/change-password',
  element: <RequireAuth><ChangePasswordPage appName="..." /></RequireAuth>,
}
```

**Acceptance criteria:**
- **Given** cada app em dev (`pnpm dev` em `apps/{nome}`) | **When** usuário logado com flag acessa `/change-password` | **Then** tela renderiza, sem 404.
- **Given** os 4 apps | **When** grep por `ChangePasswordPage` | **Then** **uma única definição** em `packages/shared/`, **quatro imports** (um por app).
- Smoke manual em pelo menos 1 app: account em `localhost:5175`.

**Complexidade:** Baixa (1h) — cópia/cola controlada.

---

## Success criteria checklist

- [ ] Endpoint backend implementado em 5 camadas (view, service, repository, serializer, exception).
- [ ] 5 testes backend passando.
- [ ] `ChangePasswordPage` único em `packages/shared/`, CSS dedicado.
- [ ] `lib/auth.ts` com `changePassword()` e detecção do flag.
- [ ] Guard funcional: usuário com flag não escapa para outras rotas.
- [ ] 4 apps registram a rota e importam do shared.
- [ ] Smoke manual: login com flag → tela aparece → troca → flag zera no DB → vai pra `/`.
- [ ] Sem regressão: usuário sem flag faz login normalmente.
- [ ] Symlinks `workspace/projects/go-control-erp/features/force-password-change/` criados.

## Open Questions (do PRD, ainda não resolvidas)

- OQ1 — Política mínima de senha (default: ≥8 chars + diferente da atual).
- OQ2 — Rotacionar JWT após troca? (default: não).
- OQ3 — Usuário pode pular? (default: não).
- OQ4 — Botão "Sair" visível no `ChangePasswordPage`? (default: sim).
- OQ5 — Banner explicativo? (default: sim).

> Tudo pode ser destravado com defaults na revisão deste plano.

## Riscos

| Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|
| Loop de redirect (`/change-password` → guard → `/change-password`...) | Média | Alto | Excluir explicitamente a rota `/change-password` da checagem do `RequireAuth`. Teste manual obrigatório. |
| Token JWT cacheado fica desincronizado após troca | Baixa | Médio | Após 200, chamar `/auth/me/` novamente para refrescar o cache de user. |
| Algum app frontend tem `RequireAuth` próprio, não usa o shared | Baixa | Médio | Step 0 implícito: grep por `RequireAuth` nos 4 apps antes de implementar Step 4. Se algum tiver custom, reaproveitar lógica. |
| Endpoint /auth/me/ não está sendo chamado após login em algum fluxo (ex.: refresh de token) | Média | Médio | Garantir que o helper `mustChangePassword()` força reload do `/me/` se o cache for stale. |

## Handoff

- **Aprovação:** aguardando "proceed" do Eduardo (Phase 2 → Phase 4).
- **Recomendação:** este feature **não requer Phase 3 (Architecture)** — fits cleanly nos padrões existentes do ADR-001. Ir direto para Bolt após aprovação.
- **Próximo agente:** `@bolt-executor`
- **Input para Bolt:** este plano + PRD + ADR-001 do projeto.
- **Validação final:** `@oath-verifier` mapeando AC1–AC9 do PRD a evidências.
- **Code review:** `@lens-reviewer` com foco em ADR-001 compliance (camadas + limites).

## Notas pós-execução (preencher após Build)

_(deixar em branco — Bolt/Oath preenchem)_
