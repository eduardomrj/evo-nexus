---
author: claude
agent: oath-verifier
type: verification
date: 2026-05-15
feature: account-app-refactor
verdict: HOLD
confidence: HIGH
blockers: 1
---

# Verificação — Refatoração do app Account (GO Control ERP)

## Veredito

**HOLD** | Confiança: ALTA | Bloqueadores: 1

| # | Item | Status | Evidência |
|---|------|--------|-----------|
| 1 | Menu lateral — 4 itens exatos | **PASS** | Ver §Item 1 |
| 2 | Redirect /modulos → /conta | **PASS** | Ver §Item 2 |
| 3 | Seção Licenças em /conta | **PASS** | Ver §Item 3 |
| 4 | LicencaModuloTree em packages/shared | **PASS** | Ver §Item 4 |
| 5 | Backend — endpoint PATCH papel com validação de tenant | **PASS** | Ver §Item 5 |
| 6 | empresa_pai_nome no serializer | **PASS** | Ver §Item 6 |
| 7 | UsuarioLink criado e usado | **PASS** | Ver §Item 7 |
| 8 | Zero #00FFA7 no código do Account | **PASS** | Ver §Item 8 |
| 9 | Typecheck sem erros novos | **FAIL** | 2 erros TS6133 em AccountEmpresaDetailPage.tsx:53 |
| 10 | AccountModulosPage deletado | **PASS** | Ver §Item 10 |

---

## Evidência por Item

### Item 1 — Menu lateral com exatamente 4 itens

**PASS**

Arquivo: `packages/shared/src/components/BackofficeLayout.tsx`

```ts
const BACKOFFICE_NAV: BackofficeNavItem[] = [
  { label: 'Dashboard', icon: 'pi pi-home',     to: '/' },
  { label: 'Conta',     icon: 'pi pi-id-card',  to: '/conta' },
  { label: 'Empresas',  icon: 'pi pi-building', to: '/empresas' },
  { label: 'Usuários',  icon: 'pi pi-users',    to: '/usuarios' },
];
```

Exatamente 4 itens. Sem "Módulos" nem "Licenças". O comentário na linha 8 do arquivo confirma: _"Exibe apenas: Dashboard, Conta, Empresas, Usuários."_

---

### Item 2 — Redirect /modulos → /conta

**PASS**

Arquivo: `apps/account/src/app/router.tsx`

```ts
{ path: 'modulos', element: <Navigate to="/conta" replace /> },
```

- `AccountModulosPage` não está importado no arquivo (ausente das linhas 1–45, confirmado por leitura completa do router).
- Redirect usa `replace`, conforme AC do PRD (sem 404, sem histórico de volta para /modulos).

---

### Item 3 — Seção Licenças em /conta com LicencaCard, LicencaDetailSidebar e filtro por empresa

**PASS**

Arquivo: `apps/account/src/pages/AccountContaPage.tsx`

- `LicencaCard` importado (linha 11) e usado no CardGrid (linha 171).
- `LicencaDetailSidebar` importado (linha 12) e instanciado (linha 183).
- Filtro por empresa: `Dropdown` (linha 130) com `filtroEmpresaId` controlando `licencasFiltradas` (linhas 41–43).
- Filtro condicional: aparece apenas quando `(empresas?.length ?? 0) > 1` (linha 129) — correto, sem ruído quando há uma única empresa.

---

### Item 4 — LicencaModuloTree em packages/shared

**PASS**

| Sub-item | Evidência |
|---|---|
| Arquivo existe em shared | `-rw-r--r-- ... packages/shared/src/components/LicencaModuloTree.tsx` (4948 bytes, 2026-05-16 14:17) |
| `index.ts` exporta `LicencaModuloTree` | `export { LicencaModuloTree } from './components/LicencaModuloTree';` |
| `index.ts` exporta `ArvoreNo` | `export type { ArvoreNo } from './types/licenca';` |
| Platform é apenas re-export | `export { LicencaModuloTree } from '@go-control/shared';` e `export type { ArvoreNo } from '@go-control/shared';` — duas linhas, nenhum código próprio |

---

### Item 5 — Backend: rota PATCH papel + validação de tenant

**PASS**

**URLs** (`backend/apps/backoffice/account/urls.py`, linha 69–71):

```python
path('licencas/<uuid:licenca_id>/usuarios/<uuid:userlicenca_id>/papel/',
     AccountUserLicencaPapelView.as_view(),
     name='account-userlicenca-papel'),
```

**Validação de tenant** (`AccountUserLicencaPapelView.patch`):

```python
conta_id = _get_conta_id(request)

# Valida que a licença existe e pertence ao tenant do caller
licenca = Licenca.objects.get(id=licenca_id)

empresa = Empresa.objects.filter(id=licenca.empresa_id, conta_id=conta_id).first()
if not empresa:
    return Response({'detail': 'Não encontrado.'}, status=status.HTTP_404_NOT_FOUND)
```

Guard explícito: se `empresa.conta_id != conta_do_caller`, retorna 404 (não vaza existência). Classe tem `permission_classes = [IsAuthenticated, IsAccountOwner]`.

---

### Item 6 — empresa_pai_nome no EmpresaSerializer

**PASS**

Arquivo: `backend/apps/backoffice/account/serializers.py`

```python
class EmpresaSerializer(serializers.ModelSerializer):
    empresa_pai_nome = serializers.SerializerMethodField()

    class Meta:
        model  = Empresa
        fields = ['id', 'razao_social', 'nome_fantasia', 'cnpj', 'tipo', 'ativo', 'created_at', 'empresa_pai_nome']
        read_only_fields = ['id', 'created_at', 'empresa_pai_nome']

    def get_empresa_pai_nome(self, obj):
        if obj.empresa_pai:
            return obj.empresa_pai.razao_social
        return None
```

`SerializerMethodField` confirmado, retorna `None` quando empresa não tem pai (campo opcional seguro).

---

### Item 7 — UsuarioLink criado e usado

**PASS**

| Sub-item | Evidência |
|---|---|
| Arquivo existe | `-rw-r--r-- ... apps/account/src/components/UsuarioLink.tsx` (1076 bytes) |
| Importado em `LicencaDetailSidebar.tsx` | linha 14: `import { UsuarioLink } from '@/components/UsuarioLink';` — usado na linha 240 |
| Importado em `AccountEmpresaDetailPage.tsx` | linha 22: `import { UsuarioLink } from '@/components/UsuarioLink';` — usado na linha 331 |

---

### Item 8 — Zero #00FFA7 no código do Account

**PASS**

A única ocorrência encontrada foi:

```
apps/account/src/components/LicencaCard.tsx:4
 * DS tokens: var(--primary-color) indigo. Nunca #00FFA7.
```

Trata-se de um **comentário JSDoc** (`/** ... */`), não de uso real de cor. Nenhuma ocorrência de `rgba(0, 255, 167` ou `rgba(0,255,167` foi encontrada. Zero hardcoded em código ativo.

---

### Item 9 — Typecheck sem erros novos

**FAIL — BLOQUEADOR**

Comando: `cd apps/account && npx tsc --noEmit`

Saída:
```
src/pages/AccountEmpresaDetailPage.tsx(53,10): error TS6133: 'tipoSeverity' is declared but its value is never read.
src/pages/AccountEmpresaDetailPage.tsx(53,23): error TS6133: 'tipo' is declared but its value is never read.
```

Exit code 2. Dois erros TS6133 (unused variable) em `AccountEmpresaDetailPage.tsx` linha 53. A variável `tipoSeverity` foi declarada via destructuring de `tipo` e nenhuma das duas é utilizada no corpo do componente. Isso indica dead code deixado após refatoração — provavelmente um destructure que deveria ter sido removido junto com o uso.

Impacto: build de produção falha com `noUnusedLocals: true` (padrão no tsconfig deste monorepo). Bloqueia o Step 8 do plano.

---

### Item 10 — AccountModulosPage deletado

**PASS**

- `apps/account/src/pages/AccountModulosPage.tsx`: arquivo não existe (confirmado).
- A única menção residual foi em `apps/account/src/components/StatusBadge.tsx` linha 36:

```ts
/** Módulos (AccountModulosPage) */
export const moduloStatusMap: StatusMap = {
```

Trata-se de um **comentário JSDoc** que documentava a origem histórica do map — não é uma importação nem referência funcional. O `moduloStatusMap` ainda pode ser útil para outros usos. Não é um bloqueador, mas vale limpar o comentário.

---

## Critérios de Aceitação — Mapeamento Completo (PRD)

| US | Acceptance Criterion | Status | Evidência |
|---|---|---|---|
| US-1 | Menu: 4 itens exatos, sem Módulos/Licenças | VERIFIED | Item 1 |
| US-1 | Redirect /modulos → /conta sem 404 | VERIFIED | Item 2 |
| US-2 | CardGrid com licenças em /conta | VERIFIED | Item 3 |
| US-2 | LicencaDetailSidebar ao clicar no card | VERIFIED | Item 3 |
| US-2 | Filtro por empresa funcional | VERIFIED | Item 3 |
| US-3 | Tab Visão Geral com 100% dos campos (≥12) | PARTIAL | Não verificado aqui — requer inspeção de AccountEmpresaDetailPage completo e smoke test |
| US-4 | Tab Licenças em /empresas/:id com side panel | PARTIAL | Não verificado aqui — requer inspeção de AccountEmpresaDetailPage tabs |
| US-5 | UsuarioLink em todos os contextos | VERIFIED | Item 7 (LicencaDetailSidebar + AccountEmpresaDetailPage) |
| US-6 | PATCH papel com guard tenant no backend | VERIFIED | Item 5 |
| US-7 | LicencaModuloTree reutilizável de packages/shared | VERIFIED | Item 4 |
| US-8 | Zero #00FFA7, apenas DS tokens | VERIFIED | Item 8 |
| US-8 | Typecheck sem erros | FAIL | Item 9 — 2 erros TS6133 |

---

## Lacunas e Riscos

| Gap | Risco | Observação |
|---|---|---|
| TS6133 em AccountEmpresaDetailPage.tsx:53 | **ALTO** — bloqueia build de produção | Remover destructure `{ tipo, tipoSeverity }` não utilizado |
| US-3 / US-4 não inspecionadas por leitura de arquivo | MÉDIO | AccountEmpresaDetailPage.tsx não foi lida na íntegra; aceitar como PARTIAL até smoke test ou leitura completa |
| Comentário legado em StatusBadge.tsx linha 36 | BAIXO | `/** Módulos (AccountModulosPage) */` — não funcional, mas polui o histórico |
| EmpresaSerializer: apenas 8 campos no Meta.fields | MÉDIO | PRD exige ≥12 campos (razão social, fantasia, CNPJ, IE, IM, endereço completo, telefones, e-mail, regime, status, datas, observações). Os campos extras podem vir de outro serializer/endpoint — requer validação |

---

## Avaliação de Risco de Regressão

| Área | Status | Base |
|---|---|---|
| apps/platform — reuso de shared | Sem evidência de regressão | re-export confirmado em LicencaModuloTree |
| packages/shared — BackofficeLayout | Sem regressão esperada | apenas remoção de item do nav, não quebra API |
| Backend — endpoints existentes | Sem alteração nos existentes | novo endpoint adicionado, nenhum modificado |
| apps/account — telas não refatoradas | Risco baixo | router e layout preservados |

---

## Recomendação

**REQUEST_CHANGES** — 1 bloqueador obrigatório, 1 verificação pendente.

### Para @bolt-executor

**Bloqueador obrigatório:**
- Corrigir `AccountEmpresaDetailPage.tsx` linha 53: remover o destructure de `tipo` e `tipoSeverity` que não são utilizados. Dois erros `TS6133` impedem build de produção.

**Ação recomendada (não bloqueadora):**
- Remover o comentário `/** Módulos (AccountModulosPage) */` da linha 36 de `StatusBadge.tsx`.

**Verificação pendente (PARTIAL):**
- Confirmar que a tab "Visão Geral" de `AccountEmpresaDetailPage` exibe ≥ 12 campos com placeholder `—` para vazios (US-3). A leitura completa do arquivo não foi realizada nesta verificação.

---

## Follow-ups

1. Após Bolt corrigir o TS6133, reexecutar `tsc --noEmit` e confirmar exit code 0.
2. Verificação de US-3 e US-4 (AccountEmpresaDetailPage) pendente — pode ser feita por Probe-QA em smoke test, ou por Oath em nova rodada após o fix.
3. Validar que o EmpresaSerializer retorna todos os 12+ campos via endpoint real (pode haver serializer estendido para detail view).
