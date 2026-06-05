# Fluxo de Convite de Usuário — GO Control ERP

**Data:** 2026-05-15  
**Escopo:** Mapeamento READ-ONLY do fluxo atual para planejamento de componente shared `InviteUsuarioSidebar`

---

## 1. Endpoint de Convite — Account (Conta Owner)

| Item | Achado |
|------|--------|
| **View** | `AccountUsuariosInviteView` |
| **Localização** | `/home/evonexus/evo-projects/go-control-erp/backend/apps/backoffice/account/views.py:191-222` |
| **Método HTTP** | `POST /api/v1/account/usuarios/invite/` |
| **Permission** | `IsAuthenticated, IsAccountOwner` |
| **Status** | ✅ FOUND |

### Serializer
- **Classe**: `InviteUsuarioSerializer` 
- **Localização**: `/home/evonexus/evo-projects/go-control-erp/backend/apps/backoffice/account/serializers.py:104-107`
- **Campos aceitos**:
  - `email` — obrigatório, EmailField
  - `nome` — opcional, CharField, max 150 chars, default ''

### Fluxo Backend
1. Busca ou cria `User` por email (com nome padrão = parte antes de @)
2. Cria ou reativa `Membership` com `status='invited'`
3. Retorna `MembershipSerializer` (id, email, nome, is_account_owner, status, created_at, expires_at, is_expired)

---

## 2. Endpoint de Convite — Platform (Staff)

| Item | Achado |
|------|--------|
| **View** | `StaffUsuarioInviteView` |
| **Localização** | `/home/evonexus/evo-projects/go-control-erp/backend/apps/backoffice/platform/views.py` |
| **Método HTTP** | `POST /api/v1/platform/usuarios/invite/` |
| **Permission** | `IsAuthenticated, IsPlatformStaff` |
| **Status** | ✅ FOUND |

### Serializer
- **Classe**: `StaffInviteSerializer`
- **Localização**: `/home/evonexus/evo-projects/go-control-erp/backend/apps/backoffice/platform/serializers.py`
- **Campos aceitos**:
  - `email` — obrigatório, EmailField

### Fluxo Backend
1. Se email não existe: cria `User` com senha temporária (12 chars aleatória)
2. Define `is_platform_staff=True` e `is_active=True`
3. Retorna `UserStaffSerializer` + `created: bool` + `temp_password` (se criado)

---

## 3. Model Membership

| Campo | Tipo | Obrigatório | Default |
|-------|------|-------------|---------|
| **id** | UUID (auto) | ✅ | uuid4 |
| **user** | FK(User) | ✅ | — |
| **conta** | FK(Conta) | ✅ | — |
| **is_account_owner** | Boolean | ✅ | False |
| **status** | CharField (20) | ✅ | 'active' |
| **created_at** | DateTime | ✅ | auto_now_add |

**Choices status**: `[('active', 'Ativo'), ('invited', 'Convidado'), ('suspended', 'Suspenso')]`

**Localização**: `/home/evonexus/evo-projects/go-control-erp/backend/apps/platform/models.py:214-226`

**Unique Constraint**: `(user, conta)` — um usuário só aparece uma vez por conta

---

## 4. Relação Membership → UserLicenca

| Fluxo | Implementação | Status |
|-------|---------------|--------|
| **Auto-create ao convidar** | NÃO — Membership é apenas "entrada" na Conta | ⚠️ GAP |
| **Create ao usuário aceitar invite** | Não mapeado — fluxo de aceitação não localizado | ⚠️ GAP |
| **Create ao admin vincular user a licença** | Via endpoint `AccountEmpresaUsuariosAplicativoView` ou manual | ⚠️ GAP |

**Achado**: Convite (Membership) é separado de acesso à licença (UserLicenca). Usuário pode estar `invited` a uma Conta mas não ter acesso a nenhuma Licença.

---

## 5. Model UserLicenca

| Campo | Tipo | Obrigatório | Notes |
|-------|------|-------------|-------|
| **id** | UUID | ✅ | uuid4 |
| **licenca** | FK(Licenca) | ✅ | on_delete=CASCADE |
| **user** | FK(User) | ✅ | on_delete=CASCADE |
| **papel** | FK(PapelLicenca) | ❌ | null=True, on_delete=PROTECT |
| **status** | CharField (20) | ✅ | default='active' |
| **created_at** | DateTime | ✅ | TimestampMixin |
| **updated_at** | DateTime | ✅ | TimestampMixin |

**Choices status**: `[('invited', 'Convidado'), ('active', 'Ativo'), ('suspended', 'Suspenso')]`

**Localização**: `/home/evonexus/evo-projects/go-control-erp/backend/apps/platform/models.py:719-757`

**Unique Constraint**: `(licenca, user)` — usuário vinculado uma única vez por licença

**Auto-link**: Ao criar uma Licença, o `dono da conta` (Membership owner) é auto-vinculado com papel `owner`

---

## 6. Model PapelLicenca

| Campo | Tipo | Notas |
|-------|------|-------|
| **id** | UUID | — |
| **licenca** | FK(Licenca) | on_delete=CASCADE |
| **code** | SlugField (60) | ex: 'owner', 'manager', 'operator', 'readonly' |
| **nome** | CharField (120) | ex: 'Owner', 'Gerente' |
| **is_owner** | Boolean | default=False, unique por licença |
| **created_at** | DateTime | TimestampMixin |
| **updated_at** | DateTime | TimestampMixin |

**Localização**: `/home/evonexus/evo-projects/go-control-erp/backend/apps/platform/models.py:661-688`

**Seeding**: Ao criar uma Licença, papéis são criados automaticamente a partir de `PapelTemplate` do aplicativo

**Unique Constraint**: `(licenca, code)` — papel é único por licença e código

---

## 7. Model PapelModulo

| Campo | Tipo | Notas |
|-------|------|-------|
| **papel** | FK(PapelLicenca) | on_delete=CASCADE |
| **modulo_code** | CharField (100) | Referência ao módulo (não é FK) |

**Localização**: `/home/evonexus/evo-projects/go-control-erp/backend/apps/platform/models.py:690-702`

**Uso**: Define quais módulos um papel não-owner pode acessar

---

## 8. Endpoints para Listar Licenças Disponíveis

| Endpoint | Método | Localização | Retorna |
|----------|--------|-------------|---------|
| `/api/v1/account/empresas/{id}/licencas/` | GET | `AccountEmpresaLicencasView` | Lista Licenças da Empresa |
| `/api/v1/platform/licencas/` | GET | Platform (global) | Todas as Licenças (staff) |

**Importante**: Não existe endpoint "todas as licenças da conta". Só funciona por empresa.

**Localização AccountEmpresaLicencasView**: `/home/evonexus/evo-projects/go-control-erp/backend/apps/backoffice/account/views.py:424-457`

---

## 9. Endpoints para Listar Papéis de uma Licença

| Endpoint | Método | Localização | Retorna |
|----------|--------|-------------|---------|
| `/api/v1/platform/licencas/{licenca_id}/papeis/` | GET | `LicencaPapeisListView` | Papéis (Staff) |
| `/api/v1/account/licencas/{licenca_id}/usuarios/{userlicenca_id}/papel/` | PATCH | `AccountUserLicencaPapelView` | Altera papel de um usuário |

**Status**: ⚠️ Gap — não existe endpoint account-level para GET papéis de uma licença

**Localização LicencaPapeisListView**: `/home/evonexus/evo-projects/go-control-erp/backend/apps/backoffice/platform/views.py`

---

## 10. Frontend — Componente Atual

| Item | Achado |
|------|--------|
| **Componente** | `InviteUserSidebar` |
| **Localização** | `/home/evonexus/evo-projects/go-control-erp/frontend/apps/account/src/components/InviteUserSidebar.tsx` |
| **Hook** | `useInviteUsuario()` → `accountService.inviteUsuario()` |
| **Status** | ✅ FOUND |

### Campos do Form
- `email` — InputText, obrigatório, type="email"
- `nome` — InputText, opcional

### Comportamento
- Sidebar direita, width 400px
- Valida email não vazio antes de enviar
- Desabilita campos/botão enquanto loading
- Chama `onSuccess()` e limpa form ao sucesso
- Chama `onError()` ao falhar
- Rejeita fechamento enquanto loading (via `inviteMutation.isPending`)

**Página que usa**: `/home/evonexus/evo-projects/go-control-erp/frontend/apps/account/src/pages/AccountUsuariosPage.tsx`

---

## 11. Hook useInviteUsuario

| Item | Achado |
|------|--------|
| **Hook** | `useInviteUsuario()` |
| **Localização** | `/home/evonexus/evo-projects/go-control-erp/frontend/apps/account/src/hooks/useUsuarios.ts:17-26` |
| **Status** | ✅ FOUND |

### Implementação
```typescript
export function useInviteUsuario() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: accountService.inviteUsuario,
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: USUARIOS_KEY });
      void qc.invalidateQueries({ queryKey: ACCOUNT_KEY });
    },
  });
}
```

---

## 12. Service API Frontend

| Item | Achado |
|------|--------|
| **Service** | `accountService.inviteUsuario()` |
| **Localização** | `/home/evonexus/evo-projects/go-control-erp/frontend/apps/account/src/services/account.ts` |
| **Tipo Retorno** | `Promise<MembershipInfo>` |
| **Status** | ✅ FOUND |

### Implementação
```typescript
async inviteUsuario(payload: { email: string; nome?: string }): Promise<MembershipInfo> {
  const { data } = await api.post<MembershipInfo>('/account/usuarios/invite/', payload);
  return data;
}
```

---

## 13. Endpoint Resend Invite

| Item | Achado |
|------|--------|
| **View** | `AccountUsuarioResendInviteView` |
| **Localização** | `/home/evonexus/evo-projects/go-control-erp/backend/apps/backoffice/account/views.py:343-356` |
| **Método HTTP** | `POST /api/v1/account/usuarios/{id}/resend-invite/` |
| **Status** | ✅ FOUND |

---

## 14. Endpoint para Alterar Papel de UserLicenca

| Item | Achado |
|------|--------|
| **View** | `AccountUserLicencaPapelView` |
| **Localização** | `/home/evonexus/evo-projects/go-control-erp/backend/apps/backoffice/account/views.py:617-672` |
| **Método HTTP** | `PATCH /api/v1/account/licencas/{licenca_id}/usuarios/{userlicenca_id}/papel/` |
| **Serializer** | `AccountUserLicencaPapelSerializer` |
| **Permission** | `IsAuthenticated, IsAccountOwner` |
| **Status** | ✅ FOUND |

### Campos Validados
- `papel_code` — obrigatório, deve existir na licença

---

## 15. URLs Registradas

**Account**:
```
POST   /api/v1/account/usuarios/invite/              → AccountUsuariosInviteView
PATCH  /api/v1/account/licencas/{id}/usuarios/{uid}/papel/  → AccountUserLicencaPapelView
```

**Platform**:
```
POST   /api/v1/platform/usuarios/invite/             → StaffUsuarioInviteView
GET    /api/v1/platform/licencas/{id}/papeis/        → LicencaPapeisListView
```

**Localização URLs**:
- Account: `/home/evonexus/evo-projects/go-control-erp/backend/apps/backoffice/account/urls.py`
- Platform: `/home/evonexus/evo-projects/go-control-erp/backend/apps/backoffice/platform/urls.py`

---

## Gaps e Questões Abertas

| Gap | Descrição | Impacto |
|-----|-----------|--------|
| **1. Auto-create UserLicenca** | Convite (Membership) NÃO cria UserLicenca automaticamente. Quando/como usuário ganha acesso à licença? | ALTO — Bloqueia fluxo de UX |
| **2. GET papéis (account)** | Não existe endpoint account-level para listar papéis de uma licença. Só GET via platform. | MÉDIO — Sidebar precisa saber papéis disponíveis |
| **3. Fluxo "convidar para licença"** | Endpoint account/invite cria Membership apenas. Não há fluxo "convidar usuário E já vinculá-lo a uma licença com papel". | ALTO — UX esperada: "convidar + papel" em 1 clique |
| **4. Telefone em User** | Model User tem `phone` (CharField 20). Serializer InviteUsuario não aceita. Falta campo? | BAIXO — Pode ser preenchido depois |

---

## Recomendação para InviteUsuarioSidebar Shared

### Escopo Atual (Account-only)
O componente atual é **suficiente para account-level**, pois:
- Fluxo: convida usuário → Membership status=invited
- Sidebar genérica com email + nome
- Reutilizável entre account e platform com props diferentes

### Faltaria para "invite + atribua licença/papel"
1. Adicionar dropdown de `Licenças disponíveis` — requer novo endpoint account GET /licencas para a conta
2. Adicionar dropdown de `Papéis` — requer novo endpoint account GET /licencas/:id/papeis
3. Modificar backend para criar **UserLicenca** junto com Membership em um POST único
4. UI para gerenciar multi-licença-assign (complexity ↑)

---

## Arquivos-Chave Resumidos

### Backend
| Arquivo | Função |
|---------|--------|
| `apps/backoffice/account/views.py:191-222` | AccountUsuariosInviteView |
| `apps/backoffice/account/serializers.py:104-107` | InviteUsuarioSerializer |
| `apps/platform/models.py:214-226` | Membership model |
| `apps/platform/models.py:719-757` | UserLicenca model |
| `apps/platform/models.py:661-688` | PapelLicenca model |

### Frontend
| Arquivo | Função |
|---------|--------|
| `frontend/apps/account/src/components/InviteUserSidebar.tsx` | Sidebar component |
| `frontend/apps/account/src/hooks/useUsuarios.ts:17-26` | useInviteUsuario hook |
| `frontend/apps/account/src/services/account.ts` | accountService.inviteUsuario |
| `frontend/apps/account/src/pages/AccountUsuariosPage.tsx:318-320` | Uso do Sidebar |

---

## Status Geral

✅ **PRONTO**: Fluxo account-level "convidar usuário" (Membership)  
⚠️ **INCOMPLETO**: Fluxo "convidar + atribuir licença/papel"  
❌ **NÃO ENCONTRADO**: Endpoint GET papéis em account-level

