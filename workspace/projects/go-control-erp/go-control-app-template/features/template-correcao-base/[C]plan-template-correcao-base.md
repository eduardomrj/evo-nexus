---
feature: template-correcao-base
status: approved
created: 2026-06-17
owner: bolt-executor
refs:
  - prd: "[C]prd-template-correcao-base.md"
---

# Plano — Correção da base do go-control-app-template

## Visão geral

6 passos. Passos 1-3 são no template. Passo 4 é no SDK Python. Passo 5 é documentação. Passo 6 propaga para go-payment-hub.

Cada passo é independente e pode ser executado por Bolt. Nenhum passo requer migration de banco.

---

## Step 1 — Fix B1: trocar `JWTAuthentication` por `StatelessJWTAuthentication`

**Arquivo:** `go-control-app-template/backend/config/settings/base.py`

```python
# ANTES (linha ~158):
"DEFAULT_AUTHENTICATION_CLASSES": [
    "rest_framework_simplejwt.authentication.JWTAuthentication",
],

# DEPOIS:
"DEFAULT_AUTHENTICATION_CLASSES": [
    "go_control_sdk.auth.authentication.StatelessJWTAuthentication",
],
```

**Critério de conclusão:** `grep StatelessJWTAuthentication backend/config/settings/base.py` retorna resultado.

---

## Step 2 — Fix B2: remover `AuthProvider` do `providers.tsx`

**Arquivo:** `go-control-app-template/frontend/apps/my-app/src/app/providers.tsx`

```tsx
// ANTES:
import { ShellProvider, AuthProvider } from '@go-control/sdk';
// ...
<ShellProvider ...>
  <AuthProvider>
    {children}
  </AuthProvider>
</ShellProvider>

// DEPOIS:
import { ShellProvider } from '@go-control/sdk';
// ...
<ShellProvider ...>
  {children}
</ShellProvider>
```

Remover também o `PrimeReactProvider` se não houver componentes PrimeReact no template base (verificar se há uso antes de remover).

**Critério de conclusão:** `grep AuthProvider frontend/apps/my-app/src/app/providers.tsx` retorna vazio.

---

## Step 3 — Fix D1: corrigir `GO_CONTROL_ADMIN_URL` no `.env.example`

**Arquivo:** `go-control-app-template/.env.example`

```bash
# ANTES:
GO_CONTROL_ADMIN_URL=http://localhost:8001

# DEPOIS:
GO_CONTROL_ADMIN_URL=http://localhost:8000  # go-control-admin — não confundir com porta do app (8001+)
```

Adicionar comentário inline para não repetir o erro.

**Critério de conclusão:** `grep GO_CONTROL_ADMIN_URL .env.example` mostra `:8000`.

---

## Step 4 — Fix B3: tornar `check_licenca` permissivo em 404

**Arquivo:** `go-control-sdk/python/go_control_sdk/platform/client.py`

```python
# ANTES:
def check_licenca(self, *, conta_id: str, app_key: str, modulo_key: str) -> bool:
    url = f"{self.base_url}/api/v1/platform/licencas/check/"
    r = httpx.get(url, headers=self._headers(),
                  params={"conta_id": conta_id, "app_key": app_key, "modulo_key": modulo_key},
                  timeout=5)
    return r.status_code == 200

# DEPOIS:
def check_licenca(self, *, conta_id: str, app_key: str, modulo_key: str) -> bool:
    """Verifica licença via admin. Retorna True se 200.
    Retorna True em 404 (endpoint ainda não implementado no admin — fail-open
    até implementação de GET /api/v1/platform/licencas/check/).
    """
    url = f"{self.base_url}/api/v1/platform/licencas/check/"
    try:
        r = httpx.get(url, headers=self._headers(),
                      params={"conta_id": conta_id, "app_key": app_key, "modulo_key": modulo_key},
                      timeout=5)
        if r.status_code == 404:
            return True  # endpoint não implementado → fail-open
        return r.status_code == 200
    except Exception:
        return False  # falha de conexão → fail-closed (comportamento existente via HasLicensedPermission)
```

> **Nota:** o SDK está em `go-control-sdk/python/`. Após editar, republicar o pacote (ou garantir que go-cobrança e go-payment-hub referenciam o source local via `pip install -e .`).

**Critério de conclusão:** `check_licenca` com admin retornando 404 retorna `True`.

---

## Step 5 — Fix D2: completar `SETUP.md` com criação de `ContaLocal`

**Arquivo:** `go-control-app-template/SETUP.md`

Adicionar novo passo entre o Step 4 (migrations) e Step 5 (manifest.json) atual:

```markdown
## 4b. Criar registro ContaLocal (tenant local)

O `JWTTenantMiddleware` usa `ContaLocal` para resolver o schema do tenant a partir do JWT.
Sem esse registro, todos os requests retornam 403 GC-A003.

```bash
cd backend && source .venv/bin/activate
python manage.py shell
```

```python
from go_control_sdk.django_app.models import ContaLocal
ContaLocal.objects.create(
    id='<uuid-da-conta-no-admin>',     # UUID da Conta no go-control-admin
    schema_name='<slug-do-schema>',    # ex: 'minha-empresa' (sem espaços, lowercase)
    nome='<Nome da Empresa>',
)
exit()
```

Em seguida, criar o schema no banco:
```bash
python manage.py migrate_schemas --schema=<slug-do-schema>
```

> O `uuid-da-conta-no-admin` está disponível no Platform Admin → Contas → detalhe da conta.
```

**Critério de conclusão:** SETUP.md tem seção `4b` com código de criação de `ContaLocal` e `migrate_schemas --schema`.

---

## Step 6 — Propagar fixes para go-payment-hub

Aplicar Steps 1 e 2 no go-payment-hub (mesmo bug herdado do template):

- `go-payment-hub/backend/config/settings/base.py` → Step 1
- `go-payment-hub/frontend/apps/go-payment-hub/src/app/providers.tsx` → Step 2

Verificar se go-payment-hub tem `.env` com `GO_CONTROL_ADMIN_URL` e corrigir se necessário (Step 3 equivalente).

**Critério de conclusão:** `grep StatelessJWTAuthentication go-payment-hub/backend/config/settings/base.py` retorna resultado.

---

## Ordem de execução recomendada

```
Step 4 (SDK) → Step 1 → Step 2 → Step 3 → Step 5 → Step 6
```

Step 4 primeiro porque os outros dependem do comportamento correto do SDK.

---

## Open Questions

- [ ] `PrimeReactProvider` no template: há uso real de PrimeReact no scaffold base? Se não, remover junto com `AuthProvider` no Step 2.
- [ ] go-message: foi gerado do mesmo template? Verificar e criar ticket se necessário.
- [ ] SDK: go-cobrança e go-payment-hub usam `pip install -e .` (source local) ou versão publicada? Determina se Step 4 precisa de release do SDK.

---

## Tickets a criar após execução

| ID | Título | Responsável |
|----|--------|-------------|
| F2 | Implementar `GET /api/v1/platform/licencas/check/` no go-control-admin | apex + bolt |
| F3 | Smoke test do template: criar app from scratch e validar SETUP.md end-to-end | grid + oath |
