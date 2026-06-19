---
feature: template-correcao-base
status: approved
created: 2026-06-17
author: oracle
---

# PRD — Correção da base do go-control-app-template

## Contexto

O `go-control-app-template` é a fonte da verdade para todos os apps SaaS da plataforma GO Control (go-cobrança, go-payment-hub, go-message, etc.). Qualquer app gerado a partir dele deve funcionar após seguir o `SETUP.md` — sem configurações ocultas, sem bugs de arranque.

Na integração piloto do go-cobrança (2026-06-17), descobrimos que o template tem **3 bugs de código** e **2 lacunas de documentação** que causam falha em cascata em qualquer app novo. O go-payment-hub tem os mesmos bugs herdados.

---

## Bugs identificados

### B1 — `JWTAuthentication` incompatível com JWT do admin
**Arquivo:** `backend/config/settings/base.py:158`
```python
# Template atual (errado):
"rest_framework_simplejwt.authentication.JWTAuthentication"
```
O admin emite JWT com `user_id` como UUID. O `JWTAuthentication` padrão tenta `User.objects.get(id=uuid)` num modelo com PK int → **500 garantido**.

### B2 — `AuthProvider` causa redirect loop
**Arquivo:** `frontend/apps/my-app/src/app/providers.tsx`
O `AuthProvider` dispara `auth.me()` → bate no admin → `JWTTenantMiddleware` retorna 403 GC-A003 se o contexto não estiver completo → interceptor do SDK limpa `localStorage` e redireciona → **loop infinito**.

### B3 — `HasLicensedPermission` chama endpoint inexistente no admin
**Arquivo:** `backend/apps/my_app/permissions.py` + qualquer view que use `HasLicensedPermission`
O SDK chama `GET /api/v1/platform/licencas/check/` mas esse endpoint **nunca foi implementado** no go-control-admin → resposta 404 → `check_licenca()` retorna `False` → **403 permanente** em toda view com essa permission.

### D1 — `.env.example` com `GO_CONTROL_ADMIN_URL` errado
**Arquivo:** `.env.example` (raiz)
```bash
GO_CONTROL_ADMIN_URL=http://localhost:8001  # errado — porta do app, não do admin
```
Admin roda em `:8000`. Com a porta errada, `HasLicensedPermission` e `PlatformAPIClient` chamam o próprio app em vez do admin.

### D2 — `SETUP.md` não documenta criação do `ContaLocal`
`ContaLocal` é o registro de tenant que o `JWTTenantMiddleware` usa para resolver o schema. Sem ele, qualquer request JWT válido falha com GC-A003. O `SETUP.md` atual não tem nenhum passo sobre `ContaLocal`.

---

## Objetivo

O template deve ser a fonte da verdade: qualquer dev que siga o `SETUP.md` do zero tem um app funcionando — login, dashboard autenticado, sem bugs de arranque.

---

## Escopo

**In:** template + propagação para go-payment-hub (mesmo bug B1 e B2 herdados).
**Out:** implementar o endpoint `licencas/check/` no admin (ticket separado F2).

---

## Acceptance Criteria

**AC-1 — StatelessJWTAuthentication**
- Dado um JWT assinado com `JWT_SIGNING_KEY` correta
- Quando o request chega ao app gerado a partir do template
- Então a autenticação passa sem consultar `User` no DB do app

**AC-2 — Sem redirect loop no login**
- Dado um usuário que fez login no admin
- Quando acessa o app pela primeira vez
- Então o dashboard carrega sem ciclo de redirect

**AC-3 — HasLicensedPermission não bloqueia quando endpoint inexiste**
- Dado que o admin ainda não implementou `GET /api/v1/platform/licencas/check/`
- Quando uma view com `HasLicensedPermission` é acessada
- Então o SDK retorna `True` (permissivo) em vez de 403 — comportamento idêntico ao `get_modulo_status` que já faz isso

**AC-4 — `.env.example` correto**
- Dado um dev que copia `.env.example` para `.env` sem alterar nada
- Quando roda o app localmente
- Então `GO_CONTROL_ADMIN_URL` aponta para `:8000` (admin), não `:8001`

**AC-5 — SETUP.md completo**
- Dado um dev que segue o `SETUP.md` do zero
- Quando chega ao passo de migrations
- Então encontra instrução explícita para criar o registro `ContaLocal` via Django shell com `id`, `schema_name` e `nome` da conta

**AC-6 — go-payment-hub corrigido**
- Dado que go-payment-hub foi gerado do mesmo template
- Quando os fixes são aplicados
- Então go-payment-hub também passa AC-1 e AC-2

---

## Fora do escopo

- Implementar `GET /api/v1/platform/licencas/check/` no admin (ticket separado)
- Alterar o SDK além do `check_licenca` (AC-3 é mudança cirúrgica)
- go-message e outros apps gerados do template (verificar separadamente)
