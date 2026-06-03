# Scout Notes — Account App Refactor Mapping

**Data:** 2026-05-15  
**Projeto:** GO Control ERP  
**Base:** `/home/evonexus/evo-projects/go-control-erp/`

---

## 1. LicencaDetailSidebar

**Status:** NOT_FOUND — Componente não existe com este nome.

**O que existe em seu lugar:**
- **`LicencaContratadaSidebar`** — `/home/evonexus/evo-projects/go-control-erp/frontend/apps/account/src/components/LicencaContratadaSidebar.tsx:1-80`
  - **Props interface (linhas 8-13):**
    ```typescript
    interface LicencaContratadaSidebarProps {
      visible: boolean;
      onHide: () => void;
      empresaId: string;
      licencaId: string | null;
    }
    ```
  - **Hook utilizado (linha 21):** `useEmpresaLicencaModulos(empresaId, licencaId)`
  - **Localização:** Atualmente em `apps/account/src/components/` — NÃO em `packages/shared/`
  - **Tipo de importação (AccountEmpresaDetailPage linha 14):** `import { LicencaContratadaSidebar } from '@/components/LicencaContratadaSidebar'`

**Recomendação para refatoração:**
Se mover para `packages/shared/`, trazer junto:
- `useEmpresaLicencaModulos` hook (atualmente em `apps/account/src/hooks/useEmpresas.ts:47-55`)
- `EmpresaLicencaModuloInfo` type (definido em `apps/account/src/services/account.ts:191-196`)
- `empresaDetailService.listLicencaModulos` (definido em `apps/account/src/services/account.ts:235-242`)

---

## 2. LicencaModuloTree

**Status:** FOUND ✓

**Localização:** `/home/evonexus/evo-projects/go-control-erp/frontend/apps/platform/src/components/LicencaModuloTree.tsx:1-173`

**Props interface (linhas 8-11):**
```typescript
interface LicencaModuloTreeProps {
  tree: ArvoreNo[];
  compact?: boolean; // se true, omite recursos
}
```

**Tipo base utilizado (linha 2):**
```typescript
import type { ArvoreNo } from '../services/permissoes';
```

**Localização atual:** `apps/platform/src/components/` — NÃO em `packages/shared/`

**Dependências para mover junto:**
- `ArvoreNo` type (definido em `apps/platform/src/services/permissoes.ts`) — **VERIFICAR se existe este arquivo**
- Nenhuma chamada HTTP interna; apenas renderização da árvore

**Uso atual:** Não encontrado em `apps/account/` — exclusivo de `apps/platform/`

---

## 3. useLicencaPapel (Hook para PATCH papel)

**Status:** NOT_FOUND — Hook não existe com este nome.

**O que existe:**
- **Rota backend para atualizar papel:** `/home/evonexus/evo-projects/go-control-erp/backend/apps/backoffice/platform/views.py:1565-1581`
  - **View:** `UserLicencaDetailView`
  - **Endpoint:** `PATCH /api/platform/licencas/<licenca_id>/usuarios/<pk>/`
  - **Permissões (linha 77):** `permission_classes = [IsAuthenticated, IsPlatformStaff]`
  - **Serializer usado (linha 1572):** `UserLicencaUpdateSerializer` (em `apps/backoffice/platform/serializers.py`)

**Gap detectado:**
- NÃO existe hook no frontend (`apps/account/`) para chamar `PATCH /api/platform/licencas/:id/usuarios/:uid/papel/`
- O endpoint existe no backend mas **sem hook correspondente no account app**
- Será necessário criar ou expor via `empresaPermissoesService`

**Verificação de permissão (segurança):**
- **Verificação tenant:** A view filtra por `licenca_id` e `pk`, mas **NÃO há validação explícita de que o caller pertence ao mesmo tenant** — apenas `IsPlatformStaff` (acesso global)
- **GAP DETECTADO:** Falta guard multi-tenant; staff pode modificar papel de qualquer licença em qualquer tenant

---

## 4. Campos da Empresa no Backend

**Model:** `/home/evonexus/evo-projects/go-control-erp/backend/apps/platform/models.py:504-533`

**Campos declarados (Python):**
```python
id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
conta       = models.ForeignKey(Conta, on_delete=models.PROTECT, related_name='empresas')
cnpj        = models.CharField(max_length=14, verbose_name='CNPJ')
razao_social = models.CharField(max_length=150, verbose_name='razão social')
nome_fantasia = models.CharField(max_length=150, blank=True, verbose_name='nome fantasia')
tipo        = models.CharField(max_length=20, choices=TIPO_CHOICES, default='independente', verbose_name='tipo')
empresa_pai = models.ForeignKey('self', null=True, blank=True, ...)
ativo       = models.BooleanField(default=True, verbose_name='ativo')
```

**Serializer para detail:** `/home/evonexus/evo-projects/go-control-erp/backend/apps/backoffice/account/serializers.py:109-113`

```python
class EmpresaSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Empresa
        fields = ['id', 'razao_social', 'nome_fantasia', 'cnpj', 'tipo', 'ativo', 'created_at']
        read_only_fields = ['id', 'created_at']
```

**Observação:** `empresa_pai` NÃO é retornado pelo serializer (não está em `fields`)

**Frontend — tipos correspondentes:** `/home/evonexus/evo-projects/go-control-erp/frontend/apps/account/src/services/account.ts:37-45`

```typescript
export interface EmpresaInfo {
  id: string;
  razao_social: string;
  nome_fantasia: string;
  cnpj: string;
  tipo: string;          // <-- mapeado
  ativo: boolean;
  created_at: string;
}
```

**Exibição em AccountEmpresaDetailPage:** Linhas 179, 153
- Campo `tipo` está sendo exibido (linha 179)
- `ativo` está sendo exibido (linha 153)
- Todos os campos principais já estão sincronizados

---

## 5. Guard Multi-tenant em PATCH papel

**Arquivo:** `/home/evonexus/evo-projects/go-control-erp/backend/apps/backoffice/platform/views.py:1565-1581`

```python
class UserLicencaDetailView(BackofficeBaseView):
    """PATCH /api/platform/licencas/<licenca_id>/usuarios/<pk>/"""

    def patch(self, request: Request, licenca_id: str, pk: str) -> Response:
        vinculo = UserLicenca.objects.filter(id=pk, licenca_id=licenca_id).select_related('user', 'papel').first()
        if not vinculo:
            return Response({'detail': 'Usuário não encontrado nesta licença.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = UserLicencaUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if 'papel' in data:
            vinculo.papel = data['papel']
        if 'status' in data:
            vinculo.status = data['status']
        vinculo.save()
        vinculo.refresh_from_db()
        return Response(UserLicencaSerializer(vinculo).data)
```

**Permission classes (linha 77):** `[IsAuthenticated, IsPlatformStaff]`

**Verificação de tenant:** 
- Nenhuma verificação de que o caller é owner/admin da conta/empresa associada à licença
- Apenas `IsPlatformStaff` (staff global)

**GAP DETECTADO:** ❌ Sem validação de que o caller pertence ao tenant da licença — qualquer staff pode editar qualquer licença de qualquer cliente.

---

## 6. AccountEmpresaDetailPage — Tab Módulos

**Arquivo:** `/home/evonexus/evo-projects/go-control-erp/frontend/apps/account/src/pages/AccountEmpresaDetailPage.tsx`

**Tab de "Licenças" (linhas 195-250):**
- Exibe lista de licenças contratadas com status badge
- **Componente exibido:** `LicencaStatusBadge` (linha 235)
- **Sidebar:** `LicencaContratadaSidebar` (linhas 359-365) — mostra módulos contratados ao clicar "Ver contratado"
- **Não há tab separado "Módulos"** — módulos aparecem **dentro** da tab Licenças

**Tab "Dados cadastrais" (linhas 162-192):**
- Exibe `tipo` (linha 179)
- Exibe `ativo` (linhas 152-155, 182-189)
- Todos os campos do serializer estão sendo renderizados

**Tab "Usuários" (linhas 252-344):**
- Lista usuários vinculados à empresa
- Botão "Permissões" (linha 325) abre `UsuarioPermissoesSidebar` (linhas 369-375)

**Observação:** NÃO existe tab "Módulos" separada — precisa esclarecer se refatoração quer criar uma.

---

## 7. AccountModulosPage e useModulos

**Arquivo:** `/home/evonexus/evo-projects/go-control-erp/frontend/apps/account/src/pages/AccountModulosPage.tsx:1-353`

**Hook utilizado:** `/home/evonexus/evo-projects/go-control-erp/frontend/apps/account/src/hooks/useModulos.ts:1-27`

```typescript
export function useModulos() {
  return useQuery({
    queryKey: MODULOS_KEY,
    queryFn: accountService.listModulos,
  });
}

export function useToggleModulo() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ code, ativo }: { code: string; ativo: boolean }) =>
      accountService.toggleModulo(code, ativo),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: MODULOS_KEY });
      void qc.invalidateQueries({ queryKey: ACCOUNT_KEY });
    },
  });
}
```

**Uso em AccountModulosPage (linhas 266-343):**
- `useModulos()` para carregar lista com filtro de busca
- `useToggleModulo()` para ativar/desativar módulo
- **NÃO é reutilizado em outra página** — exclusivo de AccountModulosPage

**Conclusão:** ✓ `useModulos.ts` e `AccountModulosPage.tsx` podem ser deletados após refatoração (são específicos de account).

---

## 8. Rotas Frontend — Estrutura Atual

```
/home/evonexus/evo-projects/go-control-erp/frontend/
├── apps/
│   ├── account/
│   │   └── src/
│   │       ├── pages/
│   │       │   ├── AccountEmpresaDetailPage.tsx          ← Detail empresa + 3 tabs
│   │       │   ├── AccountEmpresasPage.tsx
│   │       │   ├── AccountModulosPage.tsx                ← Lista módulos (deletável pós-refactor)
│   │       │   ├── AccountUsuariosPage.tsx
│   │       │   ├── AccountContaPage.tsx
│   │       │   └── AccountDashboardPage.tsx
│   │       ├── components/
│   │       │   ├── LicencaContratadaSidebar.tsx          ← Sidebar módulos contratados
│   │       │   ├── LicencaRow.tsx
│   │       │   ├── LicencaStatusBadge.tsx
│   │       │   └── ...
│   │       ├── hooks/
│   │       │   ├── useEmpresas.ts
│   │       │   ├── useModulos.ts                          ← Deletável pós-refactor
│   │       │   ├── usePlatform.ts
│   │       │   └── ...
│   │       └── services/
│   │           └── account.ts                             ← API calls
│   │
│   └── platform/
│       └── src/
│           ├── components/
│           │   ├── LicencaModuloTree.tsx                 ← Tree hierárquica
│           │   └── ...
│           └── pages/
│               ├── PlatformLicencasPage.tsx
│               └── ...
│
└── packages/shared/
    └── src/
        ├── components/
        │   ├── CardGrid.tsx
        │   ├── RequireStaff.tsx
        │   └── ...
        └── hooks/
            ├── useAuth.ts
            └── ...
```

---

## 9. Checklist de Achados para ADR

- [ ] **LicencaDetailSidebar** — não existe; é `LicencaContratadaSidebar`
- [ ] **LicencaModuloTree** — existe em `apps/platform/`; depende de `ArvoreNo` type
- [ ] **useLicencaPapel** — não existe; endpoint backend em `UserLicencaDetailView` (requires new hook)
- [ ] **Campos Empresa** — sincronizados between backend/frontend (8 fields total)
- [ ] **Guard multi-tenant** — **GAP:** sem validação; staff pode editar qualquer licença
- [ ] **AccountEmpresaDetailPage** — sem tab "Módulos" separada (só dentro Licenças)
- [ ] **AccountModulosPage** — deletável; não reutilizado em outra página
- [ ] **useModulos** — deletável; exclusivo de AccountModulosPage
- [ ] **Estrutura atual** — app/platform e app/account bem separados; shared vazio de componentes

---

## Recomendações para @apex-architect

1. **Esclarecer escopo:** A refatoração quer mover `LicencaContratadaSidebar` + tree para `packages/shared`?
2. **Criar hook:** Será necessário novo hook `useLicencaPapel` no account app ou expor em `empresaPermissoesService`.
3. **Multi-tenant fix:** Adicionar guard na view `UserLicencaDetailView` para validar tenant (ANTES de implementação).
4. **Cleanup:** `AccountModulosPage.tsx` + `useModulos.ts` marcados para deleção.
5. **Service consolidation:** Considerar unificar `accountService` + `empresaPermissoesService` (dupla responsabilidade).

