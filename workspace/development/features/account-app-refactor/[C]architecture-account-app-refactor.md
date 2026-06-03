---
author: claude
agent: apex-architect
type: adr
date: 2026-05-15
feature: account-app-refactor
status: proposed
prd: ./[C]prd-account-app-refactor.md
plan: ./[C]plan-account-app-refactor.md
scout: ./scout-notes.md
---

# ADR — Account App Refactor

## Status: proposed

Aguarda aprovação do Eduardo. Sem aprovação explícita, Bolt não inicia Phase 4.

---

## Contexto

O PRD pediu a substituição conceitual de "Módulos" por "Licenças" no app Account (porta 5174),
mais paridade Platform Admin para o dono da conta gerenciar papéis/permissões dentro do seu
próprio tenant. A leitura do código mostrou três fatos que **contradizem** o PRD/plano literal
e exigem decisões arquiteturais:

1. **Não existe `LicencaDetailSidebar`** — o que existe é `LicencaContratadaSidebar`
   (`frontend/apps/account/src/components/LicencaContratadaSidebar.tsx:15-80`) e ele só
   mostra **uma lista plana de módulos** da licença. Não tem usuários, não tem papéis,
   não tem árvore. Para atender US-2/US-4/US-6/US-7 do PRD, o componente precisa ser
   **reconstruído como um side panel composto**, não apenas movido.
2. **Endpoint `PATCH papel` é estruturalmente platform-only** — está sob `BackofficeBaseView`
   (`backend/apps/backoffice/base.py:76-77`) cujo default é `[IsAuthenticated, IsPlatformStaff]`.
   E **não há validação de tenant** nem para staff. Dois gaps de segurança, não um.
3. **`Empresa` tem só 8 campos no modelo** (`backend/apps/platform/models.py:504-525`).
   Não existem campos de endereço, telefone, IE, IM, regime tributário. A premissa do
   PRD §5/US-3 de "12+ campos" é falsa — não há nada a descobrir; há decisão de **escopo**
   sobre estender o modelo ou ajustar a expectativa.

Esses três pontos amarram as quatro decisões abaixo.

---

## Decisão A — Endpoint de alteração de papel para o dono da conta

### Drivers

- O dono da conta precisa alterar papéis de usuário em suas licenças (US-6, US-7).
- O endpoint atual (`PATCH /api/platform/licencas/<licenca_id>/usuarios/<pk>/`,
  `backend/apps/backoffice/platform/views.py:1565-1581`) usa `IsPlatformStaff` — o dono
  da conta **não passa** essa permissão.
- Existem **dois gaps**, não um: (i) o dono não pode chamar; (ii) mesmo staff não tem
  validação de tenant (qualquer staff edita qualquer cliente).
- `IsAccountOwner` **já existe** em `backend/apps/backoffice/account/permissions.py:14-28`,
  com helper `_get_conta_id` para resolver conta ativa. Não precisa criar permission class
  do zero — só compor.
- Toda a infra de URLs `account/...` já está montada no padrão `IsAccountOwner` (16+ views
  em `backend/apps/backoffice/account/views.py`).

### Alternativas analisadas

**Alt-A1 — Novo endpoint em `account/` paralelo ao endpoint platform**
`PATCH /api/backoffice/account/licencas/<licenca_id>/usuarios/<pk>/papel/`
- View dedicada herda `BackofficeBaseView` mas sobrescreve `permission_classes = [IsAuthenticated, IsAccountOwner]`.
- Resolve conta ativa via `_get_conta_id(request)` e valida cadeia
  `licenca.empresa.conta_id == conta_ativa.id` antes de mutar.
- Payload restrito a `{ "papel_id": "<uuid>" }` — não aceita `status` (gestão de status do
  vínculo continua sendo prerrogativa de staff).
- Reutiliza `UserLicencaUpdateSerializer` apenas para o subset `papel_id`, OU cria
  `AccountUserLicencaPapelUpdateSerializer` enxuto.

**Alt-A2 — Compor permissões na view existente**
Trocar `permission_classes` da `UserLicencaDetailView` para
`[IsAuthenticated, (IsPlatformStaff | IsAccountOwnerOfLicenca)]` + injetar tenant guard inline.
- Acopla domínios de account e platform na mesma view.
- Risco de regressão em qualquer fluxo que dependa do contrato atual.
- Mistura responsabilidades: a view passa a falar dois "idiomas" de autorização.

**Alt-A3 — Adiar US-6/US-7**
Refactor entrega só visualização; alteração de papel fica para v2.
- Trava metade do valor do PRD (Goals 3 e 5).
- Eduardo explicitou no PRD §3.3 que paridade Platform Admin é objetivo central.

### Decisão

**Adotar Alt-A1.** Criar novo endpoint sob `apps/backoffice/account/` com:

```
PATCH /api/backoffice/account/licencas/<licenca_id>/usuarios/<vinculo_id>/papel/
permission_classes = [IsAuthenticated, IsAccountOwner]
payload: { "papel_id": "<uuid>" }
response: serializer reduzido de UserLicenca (papel atualizado)
```

Tenant guard explícito no `patch()`:

```
conta_id = _get_conta_id(request)
vinculo = UserLicenca.objects.select_related('licenca__empresa').filter(
    id=vinculo_id, licenca_id=licenca_id, licenca__empresa__conta_id=conta_id
).first()
if not vinculo:
    return 404   # não vaza existência cross-tenant
```

**Decisão paralela sobre o gap em staff:** corrigir a `UserLicencaDetailView` original
para validar tenant via `conta_id` resolvido do request ou da licença, mantendo
`IsPlatformStaff` — mas isso fica como **follow-up separado** (ticket próprio), não no
escopo desta refatoração. Citar na seção "Pontos de atenção".

### Consequências

- **Positivas:**
  - Separação clara de domínios: account expõe só o que o dono pode fazer.
  - 404 em cross-tenant evita oracle de existência (boa prática de segurança).
  - Reuso de `IsAccountOwner` reduz superfície a auditar.
  - Não toca `UserLicencaDetailView`, então `apps/platform/` segue intocado.
- **Negativas:**
  - Duplicação leve de lógica de atualização de papel (resolvida com helper de domínio
    `update_user_licenca_papel(vinculo, papel)` se desejado).
  - Frontend precisa de hook novo apontando para a URL `account/` em vez da `platform/`
    que o plano original mencionava.
- **Trade-off explícito:** ganha-se isolamento e segurança ao custo de uma view + URL
  adicional. Aceitável e canônico para multi-tenant.

---

## Decisão B — Localização do side panel de licença

### Drivers

- `LicencaContratadaSidebar` está em `apps/account/src/components/` (Scout §1).
- O componente atual é **mínimo** (só lista módulos). O PRD pede um side panel que
  mostre módulos + usuários + papéis + ação "editar papel" — escopo bem maior.
- O `apps/platform/` tem outra UI de gestão de licença (não um side panel idêntico),
  então **hoje não há reuso natural** com platform.
- `packages/shared/components/` existe (Scout §8) e contém apenas `CardGrid`,
  `RequireStaff`, etc. — nenhum componente de domínio "licença".

### Alternativas analisadas

**Alt-B1 — Manter em `apps/account/src/components/`**
- Renomear de `LicencaContratadaSidebar` para `LicencaDetailSidebar` (alinhar nomenclatura
  do PRD) e **expandir o conteúdo** (módulos + usuários + papéis + edit role).
- Reuso futuro pelo platform fica condicionado a extração posterior (YAGNI agora).

**Alt-B2 — Mover para `packages/shared/`**
- Custo de mover hooks (`useEmpresaLicencaModulos`), types (`EmpresaLicencaModuloInfo`)
  e service (`empresaDetailService.listLicencaModulos`) juntos.
- Plataforma **não consome** este componente hoje. Mover agora é YAGNI duplo: o trabalho
  de extração + manutenção de API estável para um único consumidor.
- O hook `useLicencaPapel` (novo) usa endpoint **`account/`**, não platform — então
  colocá-lo em shared força o shared a depender de URL específica de tenant, ou
  parametrizar URL no hook (over-engineering para um consumidor).

### Decisão

**Adotar Alt-B1.** Manter em `apps/account/src/components/`, renomear para
`LicencaDetailSidebar` (alinhar PRD), e expandir conteúdo em três seções verticais:

```
LicencaDetailSidebar
├── Cabeçalho      ← plano, empresa, status badge, expiração
├── Seção Módulos  ← reuso do conteúdo atual (lista plana)
├── Seção Usuários ← lista de vínculos com papel editável (UserLicencaPapelRow)
└── Footer         ← ação "Ver permissões granulares" (abre tela ou modal — ver Decisão C)
```

A re-localização para `packages/shared/` é registrada como **follow-up condicional**:
mover apenas quando platform tiver um consumidor concreto. Hoje, mover é dívida sem ROI.

### Consequências

- **Positivas:**
  - Zero risco de quebrar `apps/platform/`.
  - Iteração rápida: o componente cresce dentro de account até estabilizar API.
  - Tipos podem ficar locais a account (`EmpresaLicencaModuloInfo` já está em
    `services/account.ts:191-196`).
- **Negativas:**
  - Se Eduardo decidir no futuro que platform precisa do mesmo side panel, haverá um
    custo de extração maior (componente terá amadurecido com dependências account-specific).
- **Trade-off explícito:** ganha-se velocidade hoje, paga-se possível extração futura.
  Aceitável dado que não há consumidor platform hoje.

---

## Decisão C — `LicencaModuloTree` (árvore de permissões granulares)

### Drivers

- `LicencaModuloTree` existe em `apps/platform/src/components/LicencaModuloTree.tsx:1-173`,
  é **read-only** (renderiza `tree: ArvoreNo[]`), depende do tipo `ArvoreNo` em
  `apps/platform/src/services/permissoes.ts:39`.
- PRD US-7 pede **checkbox + save** (escrita de permissões individuais). O componente atual
  **não tem** essa capacidade — seria reconstrução grande.
- A escrita de permissões individuais requer: (i) endpoint backend de PATCH granular,
  (ii) modelo de dados que aceite override por licença, (iii) UI de checkbox tri-state com
  herança modulo→tela→recurso, (iv) lógica de save com diff. Nenhum desses 4 pontos foi
  endereçado no PRD/plano.
- A US-7 atual no PRD (linhas 167-178) mistura "ver árvore" (cheap) com "salvar permissões"
  (caro) sem distinguir. Isso é escopo creep silencioso.

### Alternativas analisadas

**Alt-C1 — Incluir `LicencaModuloTree` read-only nesta refatoração**
- Mover para `packages/shared/` (custo: leva `ArvoreNo` junto) OU re-importar de
  `@/platform/components` (cross-app import — anti-padrão em monorepo).
- Renderiza no side panel a árvore de módulos incluídos no plano da licença.
- Sem checkboxes interativos, sem save.

**Alt-C2 — Excluir `LicencaModuloTree` do escopo desta refatoração**
- Manter o que `LicencaContratadaSidebar` já faz: lista plana de módulos.
- Não cria expectativa que não vai ser cumprida agora.

**Alt-C3 — Read-only agora, write em iteração separada**
- Inclui árvore visual nesta refatoração (mostra hierarquia modulo→tela→recurso).
- Não inclui edição. US-7 do PRD é cortada em duas partes; a parte de "ver" é entregue,
  a parte de "salvar" vira ticket separado com escopo backend + frontend.

### Decisão

**Adotar Alt-C3 com condição.** Incluir `LicencaModuloTree` em **modo read-only**, mas:

1. **Localização:** mover para `packages/shared/src/components/` **junto com o tipo
   `ArvoreNo`** (movê-lo para `packages/shared/src/types/`). Razão: o tree é genuinamente
   reutilizável entre account e platform — diferente de `LicencaDetailSidebar`, aqui há
   consumidor atual em platform.
2. **Re-exportar** de `apps/platform/src/components/` para evitar breaking change.
3. **Escopo de exibição:** mostrar apenas módulos do **plano contratado pela licença**
   — backend já filtra (Scout não detalhou, mas é a expectativa do PRD §9 Risk 4).
4. **US-7 do PRD é cortada:** entregar visualização agora; abrir ticket `EVO-XXX —
   Permissões granulares por licença (write)` como follow-up com seu próprio PRD,
   pois envolve modelagem de override + endpoint PATCH + lógica de save.

### Consequências

- **Positivas:**
  - Entrega valor visível para US-7 (dono vê o que está incluído na licença em árvore).
  - Trabalho de write fica isolado, com escopo dimensionado em iteração própria.
  - Movimento para shared resolve duplicação real (tree já é usado em platform).
- **Negativas:**
  - O PRD precisa ser atualizado para refletir o corte de US-7 — Compass deve
    re-revisar o PRD após este ADR.
  - Se Eduardo entender US-7 como bloqueante para a refatoração, esta decisão precisa
    voltar a debate.
- **Trade-off explícito:** entrega visualização e adia escrita. Aceitável se Eduardo
  confirmar; caso contrário, US-7 vira PRD próprio antes de Phase 4.

---

## Decisão D — Campos da Empresa (qual a verdade?)

### Drivers

- Eduardo reportou "não está mostrando todos os dados" da empresa (PRD §2, P1).
- O modelo `Empresa` (`backend/apps/platform/models.py:504-525`) tem **8 campos totais**:
  `id`, `conta`, `cnpj`, `razao_social`, `nome_fantasia`, `tipo`, `empresa_pai`, `ativo`
  (+ `created_at`/`updated_at` de `TimestampMixin`).
- `EmpresaSerializer` (`backend/apps/backoffice/account/serializers.py:109-113`) retorna
  **7 campos** — falta apenas `empresa_pai`.
- O PRD §5/US-3 lista 12+ campos que **não existem no modelo**: IE, IM, endereço, telefones,
  e-mail, regime tributário, observações. Isso é uma **premissa errada do PRD**, não
  gap de implementação.

### Alternativas analisadas

**Alt-D1 — Adicionar `empresa_pai` (nome da matriz) ao serializer e parar aí**
- Mudança mínima: 1 campo no serializer + 1 no tipo TS.
- Honra o gap real (campo existe, não está exposto).
- Não cria expectativa do que o modelo não suporta.

**Alt-D2 — Estender o modelo `Empresa` com campos cadastrais (IE, IM, endereço, telefone, e-mail, regime)**
- Migration grande (~6-8 colunas).
- Precisa decidir: dados vêm de onde? Receita Federal lookup automático? CRUD manual?
- Cada campo opcional? Validação por tipo (matriz vs filial)?
- Fora do escopo de uma **refatoração frontend** — vira projeto próprio de "Cadastro
  completo de empresa" com PRD, integração possível com Receita.
- Quebra o non-goal do PRD §4 ("NÃO alterar endpoints do backend" — quebrar essa regra
  exige decisão consciente).

**Alt-D3 — Layout-only fix**
- Premissa: a percepção do Eduardo é sobre **layout** (campos espremidos, mal hierarquizados),
  não sobre campos faltando.
- Não toca backend; apenas redesigna a tab "Visão Geral" para deixar os 7 campos atuais
  mais legíveis com seções, ícones e tipografia.
- Combina com Canvas DS pass (Step 7 do plano).

### Decisão

**Adotar Alt-D1 + Alt-D3 (combinação).** Concretamente:

1. **Backend:** estender `EmpresaSerializer` para incluir `empresa_pai` (com nome resolvido
   via SerializerMethodField: `empresa_pai_nome`). Sem migration de modelo.
2. **Frontend:** atualizar `EmpresaInfo` (services/account.ts:37-45) para incluir
   `empresa_pai_id` e `empresa_pai_nome`.
3. **UI:** Canvas redesign da tab "Visão Geral" para mostrar os 7 campos atuais + matriz
   com hierarquia visual clara (seção "Dados cadastrais", seção "Vínculo", seção "Status").
   Sem placeholder de campos que não existem.
4. **PRD update:** Compass corrige US-3 do PRD para refletir "exibir 100% dos campos do
   serializer" (que agora são 8 com `empresa_pai_nome`), não "≥ 12 campos".
5. **Follow-up ticket:** abrir `EVO-XXX — Cadastro fiscal de empresa (IE, IM, endereço,
   regime)` como projeto separado com PRD próprio. Decisão fica com Eduardo se isso é
   roadmap ou não.

### Consequências

- **Positivas:**
  - Resolve o problema real do Eduardo (layout + empresa_pai oculto).
  - Não infla escopo da refatoração com modelagem fiscal.
  - PRD fica alinhado à realidade do banco.
- **Negativas:**
  - Se a expectativa do Eduardo for **mesmo** sobre campos fiscais, esta decisão exige
    confronto explícito com ele antes de Bolt iniciar.
- **Trade-off explícito:** entrega o gap real mas pode não satisfazer expectativa
  implícita. **Bolt deve confirmar com Eduardo** antes de Phase 4 se "todos os dados"
  significa "todos do serializer" ou "campos fiscais novos".

---

## Pre-mortem — o que pode dar errado

| # | Falha potencial | Mitigação |
|---|---|---|
| PM1 | Frontend chama o endpoint `account/` mas em produção a tenant resolution falha e dá 404 silencioso, fazendo o usuário achar que "não tem permissão" | Hook `useLicencaPapel` distingue 404 (cross-tenant) de 403 (não-owner) e mostra mensagens distintas; teste integrado com dois tenants |
| PM2 | Mover `LicencaModuloTree` para shared quebra import em platform porque `ArvoreNo` viaja junto e platform tem outros lugares que importam de `services/permissoes` | Re-exportar `ArvoreNo` do path antigo no platform após mover; rodar `pnpm typecheck` em ambos os apps |
| PM3 | `LicencaDetailSidebar` cresce demais e vira god-component (módulos + usuários + papéis + permissões em um arquivo) | Split em sub-componentes desde o início: `LicencaSidebarHeader`, `LicencaModulosSection`, `LicencaUsuariosSection`, `UserLicencaPapelRow` |
| PM4 | Eduardo pediu "12+ campos" mas concorda em ver só 8 — depois reclama em produção que "faltava endereço" | Bolt confirma escopo de Empresa **antes** de começar Phase 4; se Eduardo quer fiscal, esta refatoração é bloqueada por novo PRD |
| PM5 | Endpoint novo de papel não tem teste de cross-tenant; um bug futuro libera edição cross-tenant silenciosa | Teste pytest obrigatório no Step 3 do plano: dono A → 404 ao tentar editar licença do tenant B (não 403, para não vazar existência) |
| PM6 | `IsAccountOwner` resolve conta ativa via header/JWT; se o frontend não envia header correto, todas as chamadas dão 403 | Documentar header esperado no ADR follow-up; smoke test manual antes de mergear |
| PM7 | Side panel modifica papel mas a lista de licenças não atualiza (cache react-query stale) | Hook `useLicencaPapel` invalida queries `['empresa-licencas']` e `['conta-licencas']` no `onSuccess` |
| PM8 | Corte de US-7 (write de permissões) gera frustração — Eduardo achou que estava no escopo | Apex anota explicitamente no handoff para Compass: PRD precisa de revisão pós-ADR |

---

## Diagrama de componentes / fluxo

```
Frontend (apps/account)
────────────────────────────────────────────────────────────────────
/conta page
  └─ <LicencasSection>
       ├─ <LicencaFiltersBar empresaFilter=... />
       ├─ <CardGrid>
       │    └─ <LicencaCard onClick=openSidebar />
       └─ <LicencaDetailSidebar  (renderiza condicionalmente)
            ├─ <LicencaSidebarHeader />
            ├─ <LicencaModulosSection>
            │    └─ <LicencaModuloTree compact />     ← shared (read-only)
            ├─ <LicencaUsuariosSection>
            │    └─ <UserLicencaPapelRow              ← novo, account-local
            │         (usa <UsuarioLink /> e
            │          dropdown de papel via useLicencaPapel)
            └─ footer

/empresas/:id page (tab "Licenças")
  └─ mesma estrutura, com empresaId pré-fixado nos filtros e hooks

Hooks
────────────────────────────────────────────────────────────────────
useLicencas(empresaId?)              ← novo, account
  GET /api/backoffice/account/licencas?empresa_id=...

useEmpresaLicencaModulos(...)        ← já existe, account

useLicencaPapel()                    ← novo, account
  PATCH /api/backoffice/account/licencas/:lid/usuarios/:uid/papel/
  payload: { papel_id }
  permissions: IsAccountOwner
  tenant guard: licenca.empresa.conta_id == _get_conta_id(request)

Backend (apps/backoffice/account)
────────────────────────────────────────────────────────────────────
NOVO: AccountUserLicencaPapelUpdateView
  PATCH /api/backoffice/account/licencas/<lid>/usuarios/<vid>/papel/
  permission_classes = [IsAuthenticated, IsAccountOwner]

AJUSTE: EmpresaSerializer
  + empresa_pai (id)
  + empresa_pai_nome (SerializerMethodField)

MOVE (com re-export): LicencaModuloTree + ArvoreNo
  apps/platform/src/components/  →  packages/shared/src/components/
  apps/platform/src/services/permissoes.ts (ArvoreNo type) → packages/shared/src/types/
  re-export no path antigo para zero-breaking-change

INALTERADO: UserLicencaDetailView (platform) — tenant guard fica como ticket follow-up
```

---

## Impacto em outros apps e packages

### `apps/platform/`
- **`LicencaModuloTree.tsx`:** arquivo migra para `packages/shared/`; um shim
  `export { LicencaModuloTree } from '@evo/shared'` fica em
  `apps/platform/src/components/LicencaModuloTree.tsx` para evitar refactor de imports.
- **`services/permissoes.ts`:** type `ArvoreNo` migra para `packages/shared/src/types/`;
  shim `export type { ArvoreNo } from '@evo/shared'` fica no path antigo.
- **`UserLicencaDetailView`:** **inalterada** nesta refatoração. Tenant guard para staff
  fica como ticket separado (PM5 do pre-mortem reforça urgência).
- **Risco regressão:** baixíssimo; turbo build + typecheck cobrem.

### `packages/shared/`
- Recebe `LicencaModuloTree` + `ArvoreNo`.
- **Não recebe** `LicencaDetailSidebar` (decisão B).
- **Não recebe** `useLicencaPapel` (acoplado a endpoint account-specific).
- Atualizar `packages/shared/src/index.ts` com novos exports.

### `apps/account/`
- Maior superfície de mudança (esperado — é o foco da refatoração).
- Novos: `LicencaCard`, `LicencaFiltersBar`, `LicencaDetailSidebar` (renomeado),
  `UserLicencaPapelRow`, `UsuarioLink`, `useLicencas`, `useLicencaPapel`.
- Removidos pós-merge: `AccountModulosPage.tsx`, `useModulos.ts`.
- Renomeado: `LicencaContratadaSidebar` → `LicencaDetailSidebar` (expandindo conteúdo).
- Roteamento: `/modulos` → `<Navigate replace to="/conta" />`.

### Backend
- Sem migration de banco.
- Novo: 1 view + 1 URL em `apps/backoffice/account/`.
- Ajuste: 1 campo no `EmpresaSerializer`.
- Sem alteração em `apps/backoffice/platform/`.

---

## Pontos de atenção para o @bolt-executor

1. **Confirmar escopo de Empresa com Eduardo antes de começar (Decisão D)**
   — se ele esperava campos fiscais, esta refatoração está bloqueada por um PRD novo.
   Pergunta exata: *"Quando você diz 'não está mostrando todos os dados' da empresa,
   você se refere aos campos que existem no banco (que são poucos) ou está esperando
   IE/IM/endereço/telefone? Esses últimos não existem no modelo hoje."*

2. **Confirmar corte de US-7 com Eduardo antes de começar (Decisão C)**
   — Entrega visualização (árvore read-only) agora; escrita (checkbox + save) vira
   ticket próprio. Pergunta exata: *"US-7 do PRD originalmente pedia checkbox + save
   de permissões granulares. Estou propondo entregar só a visualização agora, e
   transformar a parte de salvar em um projeto separado. OK?"*

3. **Endpoint novo retorna 404 (não 403) em cross-tenant** — não vazar existência de
   licenças/vínculos de outros tenants. Esse padrão deve ser replicado em qualquer
   endpoint multi-tenant futuro.

4. **Sem alteração em `UserLicencaDetailView`** — o gap de tenant guard em staff existe
   e é grave (qualquer staff edita qualquer cliente), mas vira ticket separado para
   não inflar esta refatoração. Bolt deve **abrir o ticket** ao iniciar Phase 4 (já com
   contexto pronto neste ADR).

5. **Manter shim de re-export para `LicencaModuloTree` e `ArvoreNo` no path antigo do
   platform** — zero-breaking-change para platform. Validar com `pnpm typecheck` no
   apps/platform após mover.

6. **`LicencaDetailSidebar` deve nascer modular** — sub-componentes desde o primeiro
   commit, não em refactor posterior. Mitigação do PM3.

7. **Hook `useLicencaPapel` deve invalidar tanto `['conta-licencas']` quanto
   `['empresa-licencas']`** em `onSuccess` (PM7). Caso contrário, side panel mostra
   papel novo mas card grid mostra antigo.

8. **Teste pytest obrigatório no Step 3 do plano:**
   - Caso 1: dono do tenant A tenta editar vínculo de licença do tenant B → 404
   - Caso 2: dono do tenant A edita vínculo da sua própria licença → 200
   - Caso 3: usuário comum (não-owner) do tenant A tenta editar → 403
   - Caso 4: payload com `papel_id` inválido → 400

9. **Compass deve revisar o PRD após este ADR** — três premissas mudaram (Empresa,
   US-7, side panel) e o plano também (Steps 3/4/5 ficam mais simples sem mover
   `LicencaDetailSidebar` para shared, mais complexos com tenant guard explícito no
   account).

---

## Open Questions resolvidas

- **Q2 (PRD):** `LicencaDetailSidebar` (na verdade `LicencaContratadaSidebar`) está em
  `apps/account/`. **Resposta:** fica em `apps/account/` (Decisão B).
- **Q5 (PRD):** Backend tem guard multi-tenant em `PATCH papel`? **Resposta:** Não, e
  além disso a view nem aceita o dono da conta hoje. Esta refatoração resolve para
  account via novo endpoint (Decisão A); guard para staff fica como ticket follow-up.

## Open Questions remanescentes

- **Q-A1:** Eduardo aceita o corte de US-7 (visualização agora, write como projeto
  separado)? — Bloqueia início de Phase 4.
- **Q-A2:** Eduardo aceita a interpretação de Empresa (campos atuais + matriz; sem
  cadastro fiscal)? — Bloqueia início de Phase 4.
- **Q-A3:** Abrir ticket separado para o gap de tenant guard em `UserLicencaDetailView`
  agora ou depois desta refatoração? — Recomendação Apex: **agora**, ao iniciar Phase 4,
  para não esquecer.

---

## References

- `frontend/apps/account/src/components/LicencaContratadaSidebar.tsx:1-80` — sidebar atual mínima
- `frontend/apps/platform/src/components/LicencaModuloTree.tsx:1-173` — tree a mover para shared
- `frontend/apps/platform/src/services/permissoes.ts:39` — tipo `ArvoreNo`
- `backend/apps/platform/models.py:504-525` — modelo Empresa (8 campos)
- `backend/apps/backoffice/account/serializers.py:109-113` — EmpresaSerializer (7 campos)
- `backend/apps/backoffice/account/permissions.py:14-28` — IsAccountOwner existente
- `backend/apps/backoffice/account/views.py:11,44` — uso canônico de IsAccountOwner + _get_conta_id
- `backend/apps/backoffice/base.py:76-77` — BackofficeBaseView default platform-staff
- `backend/apps/backoffice/platform/views.py:1565-1581` — UserLicencaDetailView (gap)
- `backend/apps/backoffice/platform/serializers.py:588-590` — UserLicencaUpdateSerializer
- PRD: `workspace/development/features/account-app-refactor/[C]prd-account-app-refactor.md`
- Plan: `workspace/development/features/account-app-refactor/[C]plan-account-app-refactor.md`
- Scout: `workspace/development/features/account-app-refactor/scout-notes.md`
