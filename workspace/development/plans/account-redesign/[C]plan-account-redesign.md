# Plano — Refatoração Completa do App Account (GO Control ERP)

**Autor:** @compass-planner
**Owner:** Eduardo
**PRD:** `[C]prd-account-redesign.md` (mesma pasta)
**Slug:** `account-redesign`
**Data:** 2026-05-15
**Status:** Draft (aguardando aprovação)

## Contexto

Refatorar todas as 5 telas do app Account (porta 5174), aplicar design system card-based aprovado em 2026-05-14, criar `components/` e `hooks/` ausentes, e adicionar Detalhe do Usuário, Convites Pendentes e Notificações. Mantendo `BackofficeLayout`, `api` shared e o backend Django REST.

## Guardrails

**Must Have:**
- Todas as páginas refatoradas seguem o design system (tokens `--evo-*`, PrimeReact overrides do `index.css`).
- `src/components/` e `src/hooks/` criados e adotados — não voltar a inline.
- Sempre usar instância `api` de `@/lib/api`.
- Backend novo entra antes do frontend que o consome (ordem dos steps respeita isso).
- pt-BR em toda UI.

**Must NOT Have:**
- `axios.create()` paralelo.
- `padding: 0 !important` em `.p-tabview-panels` ou afins.
- Mudanças no app Platform.
- Persistir notificações em tabela nova (decidir on-the-fly primeiro).
- Endpoints sem rate-limit em reset de senha.

---

## Step 1 — Fundação: estrutura de pastas + componentes base

**Complexidade:** Baixa (pastas já existem — apenas enriquecer)
**Owner sugerido:** @bolt-executor

> **Nota pós-scout:** `src/components/` já tem 6 componentes (StatCard, StatusBadge, LicencaRow, LicencaStatusBadge, PapelDropdown, PlanoStatusBadge). `src/hooks/` já tem 5 hooks (useAccount, useEmpresas, useModulos, useUsuarios, usePlatform). Step 1 é enriquecer, não criar do zero.

**O que fazer:**
- Inventariar `CardGrid.tsx` (atualmente em `apps/platform/src/components/`):
  - Se realmente reutilizável → mover para `packages/shared/src/components/CardGrid.tsx` e atualizar import do Platform (mudança mínima, atômica).
  - Se específico de Platform → duplicar versão simplificada em `apps/account/src/components/CardGrid.tsx` (decisão de Apex se OQ1 ficar ambígua).
- Criar utilitários base em `apps/account/src/components/`:
  - `PageHeader.tsx` — título + subtítulo + ações (botão CTA primário).
  - `StatusBadge.tsx` — badge de status (active/invited/suspended, ativo/inativo, etc.) com cores do tema.
  - `EmptyState.tsx` — empty state padrão com ícone, mensagem, CTA.
  - `ConfirmSidebar.tsx` — sidebar de confirmação reutilizável (extrair de `DeleteConfirmSidebar` da Platform se aplicável).

**Hooks base (`apps/account/src/hooks/`):**
- `useAccountOverview.ts`
- `useAccountUsuarios.ts` (list + invite + update + delete em um único hook com mutations).
- `useAccountEmpresas.ts`
- `useAccountModulos.ts`
- Cada um encapsula `useQuery`/`useMutation` do TanStack Query e expõe os métodos do `accountService`.

**Arquivos:**
- Criar: `apps/account/src/components/{PageHeader,StatusBadge,EmptyState,ConfirmSidebar}.tsx`
- Criar: `apps/account/src/hooks/{useAccountOverview,useAccountUsuarios,useAccountEmpresas,useAccountModulos}.ts`
- Talvez mover: `apps/platform/src/components/CardGrid.tsx` → `packages/shared/src/components/CardGrid.tsx` (+ atualizar imports da Platform)

**Backend:** nada.

**Acceptance:** componentes e hooks compilam, `npm run typecheck` passa, Platform continua funcionando idêntico.

---

## Step 2 — Backend: novos endpoints para Detalhe do Usuário, Convites e Notificações

**Complexidade:** Alta
**Owner sugerido:** @bolt-executor (com revisão de @vault-security no endpoint de reset)

**O que fazer (apenas backend Django):**

Adicionar a `apps/backoffice/account/`:

1. **Log de operações por usuário** (US5, AC2):
   - `GET /api/v1/account/usuarios/<uuid:pk>/operations-log/?empresa_id=&date_from=&date_to=`
   - Decisão de OQ2: se já existe Django audit log, criar view que filtra por `user_id`. Senão, criar model novo `UserOperationLog(user, empresa, event_type, payload, created_at)` + signals em login/logout/permission_change.
   - Recomendação Compass: **começar com Django simple-history ou django-auditlog se já estiver em uso**; caso contrário, criar tabela leve `UserOperationLog` e popular com signals nos pontos críticos (login, status_change, papel_change).

2. **Reset de senha por dono de conta** (US6, AC2):
   - `POST /api/v1/account/usuarios/<uuid:pk>/reset-password/`
   - Backend dispara `PasswordResetTokenGenerator` do Django, envia email via task celery/django-mail.
   - **Rate limit:** 3 requests por usuário-alvo por hora; 10 por dono-de-conta por dia. Usar `django-ratelimit` ou middleware existente.
   - Validar que o `user_id` pertence a uma empresa do dono que está chamando (permissão).

3. **Listagem de Convites Pendentes** (US8, AC4):
   - Já dá para filtrar via `GET /api/v1/account/usuarios/?status=invited`, mas o frontend precisa de campos extras: `invited_at`, `expires_at`, `is_expired`. Adicionar esses campos ao serializer de `MembershipInfo`.
   - `POST /api/v1/account/usuarios/<uuid:pk>/resend-invite/` — reenvia o convite (email + atualiza `invited_at`).
   - `DELETE /api/v1/account/usuarios/<uuid:pk>/` já existe; usar para cancelar convites (status=invited).
   - Definir `expires_at = invited_at + 7 dias` no modelo (campo computed ou property no serializer).

4. **Notificações do dashboard** (US9, AC5):
   - `GET /api/v1/account/notifications/` — endpoint on-the-fly que calcula:
     - Licenças vencendo em < 30 dias (severity: 14d=critical, 30d=warning).
     - Usuários suspendidos nas últimas 24h.
     - Módulos desativados nas últimas 24h.
   - Resposta: `[{ type, severity, title, message, link, created_at }]`.
   - Sem persistência; sempre recomputa.

5. **Toggle de acesso por empresa** (US4, AC2):
   - Endpoint já existe: `PATCH /api/v1/backoffice/platform/empresas/<id>/usuarios-aplicativo/` (via `empresaPermissoesService.updateUsuarioAplicativo`).
   - **Validar** que dono de conta também tem permissão (não só staff). Se não, abrir endpoint paralelo em `/api/v1/account/empresas/<id>/usuarios-aplicativo/<id>/`.

6. **Matriz Usuários × Empresas** (US10, AC6) — opcional fase 2 se inflar:
   - `GET /api/v1/account/usuarios-matriz/` — retorna `{ usuarios: [...], empresas: [...], matriz: { user_id: { empresa_id: papel_nome | null } } }`.

**Arquivos:**
- Modificar: `apps/backoffice/account/views.py`, `urls.py`, `serializers.py`, `permissions.py`.
- Possível novo: `apps/backoffice/account/models.py` (se criar `UserOperationLog`).
- Migration nova se houver model novo.
- Tests: `apps/backoffice/account/tests/test_views.py` cobrindo cada endpoint novo.

**Endpoints existentes vs novos:**

| Endpoint | Existe? | Ação |
|---|---|---|
| `GET /account/overview/` | ✅ | Manter |
| `GET /account/modulos/` | ✅ | Manter |
| `PATCH /account/modulos/<code>/` | ✅ | Manter |
| `GET /account/empresas/` | ✅ | Manter |
| `POST /account/empresas/` | ✅ | Manter |
| `PATCH /account/empresas/<id>/` | ✅ | Manter |
| `GET /account/usuarios/` | ✅ | **Modificar serializer** (adicionar `invited_at`, `expires_at`, `is_expired`) |
| `POST /account/usuarios/invite/` | ✅ | Manter |
| `PATCH /account/usuarios/<id>/` | ✅ | Manter |
| `DELETE /account/usuarios/<id>/` | ✅ | Manter |
| `GET /account/usuarios/<id>/operations-log/` | ❌ | **Criar** |
| `POST /account/usuarios/<id>/reset-password/` | ❌ | **Criar** + rate-limit |
| `POST /account/usuarios/<id>/resend-invite/` | ❌ | **Criar** |
| `GET /account/notifications/` | ❌ | **Criar** (on-the-fly) |
| `GET /account/usuarios-matriz/` | ❌ | **Criar** (se incluir US10) |
| `GET /backoffice/platform/empresas/<id>/papeis/` | ✅ | Manter |
| `GET /backoffice/platform/empresas/<id>/usuarios-aplicativo/` | ✅ | Manter |
| `PATCH /backoffice/platform/usuarios-aplicativo/<id>/` | ✅ | **Verificar permissão do dono de conta** |

**Acceptance:** todos os endpoints novos têm testes, retornam 200 em happy-path, 403 sem permissão, 429 quando rate-limit ativa.

---

## Step 3 — Refactor da tela de Usuários (lista em cards)

**Complexidade:** Média
**Owner sugerido:** @bolt-executor (UI por @canvas-designer se quiser polimento)

**O que fazer:**
- Reescrever `AccountUsuariosPage.tsx` (atual 259 linhas → alvo < 150 linhas).
- Trocar `DataTable` por `CardGrid` (do Step 1).
- Card por usuário com:
  - Avatar/inicial, nome, email.
  - `StatusBadge` (active/invited/suspended).
  - Botão **Bloquear/Permitir** (toggle `status` active↔suspended via `useAccountUsuarios().updateUsuario`).
  - Botão **Informações** → navega para `/usuarios/:id`.
- Filtro/busca por nome ou email (usar `<InputText>` no `PageHeader`).
- Tabs no topo: "Ativos" / "Convites pendentes" — quando "Convites" selecionada, lista filtrada por `status=invited` (ver Step 5).
- Sidebar de convite (componente extraído `InviteUserSidebar.tsx` em `components/`).
- Empty state com CTA.

**Arquivos:**
- Modificar: `apps/account/src/pages/AccountUsuariosPage.tsx`
- Criar: `apps/account/src/components/{UsuarioCard,InviteUserSidebar}.tsx`

**Backend:** nada novo neste step (Step 2 já cobriu).

**Acceptance:** AC1 e AC4 (tab convites pendentes) passam. `npm run dev` e validar lado a lado com Platform.

---

## Step 4 — Nova tela: Detalhe do Usuário (`/usuarios/:id`)

**Complexidade:** Alta
**Owner sugerido:** @bolt-executor

**O que fazer:**
- Criar `apps/account/src/pages/AccountUsuarioDetailPage.tsx`.
- Rota nova em `apps/account/src/app/router.tsx`: `path: '/usuarios/:id'`.
- Layout em 4 blocos:
  1. **Header** com avatar, nome, email, `StatusBadge`, botão **Resetar senha** (abre modal de confirmação → chama `POST /account/usuarios/:id/reset-password/`), botão **Bloquear/Permitir**.
  2. **Empresas e papéis** — lista de cards, um por empresa onde o usuário tem `UsuarioAplicativo`. Cada card: nome empresa, aplicativo, papel atual (com dropdown para trocar), toggle ativar/desativar (`status`), última atividade.
  3. **Log de operações** — `DataTable` com filtros (`Calendar` para período, `Dropdown` para empresa). Colunas: data, evento, empresa, papel, IP. Consome `GET /account/usuarios/:id/operations-log/`.
  4. **Sidebar lateral** (opcional) com metadados: criado em, último login, total de empresas, total de logins (se houver).
- Hook novo: `useAccountUsuarioDetail.ts` (queries: usuário + empresas+papéis + log).

**Arquivos:**
- Criar: `apps/account/src/pages/AccountUsuarioDetailPage.tsx`
- Criar: `apps/account/src/components/{UsuarioEmpresaCard,OperationsLogTable,ResetPasswordModal}.tsx`
- Criar: `apps/account/src/hooks/useAccountUsuarioDetail.ts`
- Modificar: roteador (adicionar rota)

**Backend:** consome endpoints criados no Step 2.

**Acceptance:** AC2 inteiro passa. Reset de senha emite email (testar em ambiente local com mailcatcher). Toggle de acesso por empresa é optimistic e revalida.

---

## Step 5 — Convites Pendentes (lista + ações)

**Complexidade:** Média
**Owner sugerido:** @bolt-executor

**O que fazer:**
- Pode ser tab dentro de `/usuarios` (preferido, menos rotas) ou rota dedicada `/convites`. Decisão Compass: **tab** (menor superfície de roteamento).
- Quando tab "Convites pendentes" ativa:
  - Lista filtrada `status=invited`.
  - Card por convite: email, nome, convidado em, expira em, badge "Pendente" ou "Expirado".
  - Botão **Reenviar** → `POST /account/usuarios/:id/resend-invite/`.
  - Botão **Cancelar** → confirmação por `ConfirmSidebar` → `DELETE /account/usuarios/:id/`.
- Indicador no header da tab com contagem ("Convites pendentes (3)").

**Arquivos:**
- Modificar: `AccountUsuariosPage.tsx` (tabs)
- Criar: `apps/account/src/components/ConviteCard.tsx`
- Estender `useAccountUsuarios` com `resendInvite` mutation.

**Backend:** Step 2 já criou `resend-invite/`.

**Acceptance:** AC4 passa.

---

## Step 6 — Refactor de Empresas (cards) + Detalhe da Empresa (nova página)

**Complexidade:** Alta (nova página densa)
**Owner sugerido:** @bolt-executor

**O que fazer:**

**Lista de empresas (`/empresas`):**
- Reescrever `AccountEmpresasPage.tsx` (atual 425 linhas → alvo < 200 linhas).
- Substituir DataTable por `CardGrid`.
- Card por empresa: razão social, nome fantasia, CNPJ formatado, badge ativa/inativa, contagem de usuários, contagem de licenças, botão **Informações**.
- Sidebar de criação de empresa (extrair para `EmpresaSidebarForm.tsx`).

**Detalhe da empresa (nova rota `/empresas/:id`):**
- Nova página `AccountEmpresaDetailPage.tsx` (substituindo `AccountEmpresaUsuariosPage`).
- **Cards de indicadores no topo:** usuários ativos, licenças ativas, módulos contratados, último acesso.
- `TabView` com 3 tabs:
  - **Tab 1: Dados cadastrais** — razão social, nome fantasia, CNPJ, tipo, datas, toggle ativo/inativo, edição inline via sidebar.
  - **Tab 2: Licenças** — lista de licenças vinculadas à empresa. Cada licença: nome do aplicativo, status badge (ativa/pendente/suspensa), período de vigência. Botão **Ver contratado** → abre sidebar/modal com módulos contratados na licença (plano, módulos, limites). Botão para gerenciar se staff.
  - **Tab 3: Usuários** — usuários vinculados à empresa por licença. Cada linha: nome, email, aplicativo, papel, status. Botão **Permissões** → abre sidebar mostrando o detalhamento de permissões (módulos/recursos que o papel permite nessa licença).
- **NÃO** zerar padding de `.p-tabview-panels` no CSS — usar prop ou wrapper interno.

**Arquivos:**
- Modificar: `apps/account/src/pages/AccountEmpresasPage.tsx`
- Renomear+refatorar: `AccountEmpresaUsuariosPage.tsx` → `AccountEmpresaDetailPage.tsx`
- Criar: `apps/account/src/components/{EmpresaCard,EmpresaSidebarForm,EmpresaKpiCards,LicencaContratadaSidebar,UsuarioPermissoesSidebar}.tsx`
- Atualizar roteador: rota nova `/empresas/:id`.

**Backend — novos endpoints necessários:**
- `GET /account/empresas/<id>/licencas/` — lista de licenças vinculadas à empresa com status e vigência.
- `GET /account/empresas/<id>/licencas/<licenca_id>/modulos/` — módulos/recursos contratados nessa licença (o que foi comprado).
- `GET /account/empresas/<id>/usuarios-aplicativo/` — usuários por licença com papel e status (alternativa ao `/backoffice/platform/` que tem permissão ambígua).
- `GET /account/empresas/<id>/usuarios-aplicativo/<usuario_id>/permissoes/` — detalhamento de permissões do usuário nessa licença.

**Acceptance:** AC3 passa. Padding e visual idênticos ao Platform. Botão "Ver contratado" abre sidebar com lista de módulos. Botão "Permissões" abre detalhamento do papel.

---

## Step 7 — Refactor de Módulos (cards) + Dashboard com Notificações

**Complexidade:** Média
**Owner sugerido:** @bolt-executor

**O que fazer:**

**Módulos (AC7):**
- Reescrever `AccountModulosPage.tsx` (atual 431 linhas → alvo < 200 linhas).
- `CardGrid` com card por módulo: ícone, nome, aplicativo, badge de status, switch on/off (chama `toggleModulo`).
- Filtro por aplicativo (Dropdown).
- Empty state quando filtrado sem resultados.

**Dashboard (AC5):**
- Reescrever `AccountDashboardPage.tsx` (atual 78 linhas → expandir para incluir notificações).
- Bloco superior: cards de KPI (total empresas, total usuários, módulos ativos) — já existe, manter.
- **Novo bloco:** "Alertas" — consome `GET /account/notifications/`.
  - Banner crítico (vermelho) para licenças vencendo < 14d.
  - Cards amarelos para vencimento 14-30d.
  - Cards informativos para usuários bloqueados/módulos desativados nas últimas 24h.
  - Estado vazio: card neutro "Tudo certo" com checkmark.
- Bloco final (opcional): atalhos rápidos (Convidar usuário, Nova empresa).

**Arquivos:**
- Modificar: `AccountModulosPage.tsx`, `AccountDashboardPage.tsx`
- Criar: `apps/account/src/components/{ModuloCard,NotificationCard,DashboardKpiCard}.tsx`
- Criar: `apps/account/src/hooks/useAccountNotifications.ts`

**Backend:** consome `/account/notifications/` (criado no Step 2).

**Acceptance:** AC5, AC7 passam.

---

## Step 8 — Visão Consolidada Usuários × Empresas (média prioridade)

**Complexidade:** Média
**Owner sugerido:** @bolt-executor
**Condicional:** só se Eduardo aprovar incluir nesta iteração (OQ6).

**O que fazer:**
- Adicionar tab "Matriz" em `/usuarios` (ou rota dedicada `/usuarios/matriz`).
- Tabela densa: linhas = usuários, colunas = empresas, célula = papel ou "—".
- Filtros: empresa, papel, status.
- Click em célula → sidebar com detalhes do `UsuarioAplicativo` daquele cruzamento.
- Exportar CSV (futuro — não obrigatório).

**Arquivos:**
- Criar: `apps/account/src/components/UsuariosMatrizTable.tsx`
- Estender `AccountUsuariosPage.tsx` com tab nova.
- Criar hook `useUsuariosMatriz.ts`.

**Backend:** consome `/account/usuarios-matriz/` (criado no Step 2 se decidido incluir).

**Acceptance:** AC6 passa.

---

## Step 9 — Limpeza, extração para shared, verificação

**Complexidade:** Baixa
**Owner sugerido:** @bolt-executor + @zen-simplifier + @oath-verifier

**O que fazer:**
- Revisar todos os componentes em `apps/account/src/components/` — qualquer um usado também por Platform vai para `packages/shared/src/components/`.
- Rodar `@zen-simplifier` na pasta `apps/account/src/` para remover slop/duplicações.
- `npm run lint`, `npm run typecheck`, `npm run build`.
- Validação visual via Playwright + DevTools (`getComputedStyle`) comparando Account vs Platform: tokens, spacing, colors devem bater.
- Smoke test manual (Probe-style):
  - Convidar, reenviar, cancelar, bloquear, desbloquear usuário.
  - Criar, editar, ativar/desativar empresa.
  - Toggle módulo.
  - Reset senha.
  - Toggle acesso por empresa no detalhe de usuário.
  - Notificações aparecem quando há eventos disparadores; somem quando não há.
- Atualizar memory pattern `project_go_control_account_app.md` com novo mapeamento.

**Arquivos:**
- Possíveis movimentações para `packages/shared/`.
- `[C]verification-account-redesign.md` em `workspace/development/features/account-redesign/` (se promover para feature folder) ou na pasta deste plano.

**Backend:** nada.

**Acceptance:** AC8, AC9, AC10 passam. Build verde. Smoke test ok.

---

## Resumo dos endpoints a criar no backend (Step 2 + Step 6)

| Endpoint | Método | Propósito | Step |
|---|---|---|---|
| `/account/usuarios/<id>/operations-log/` | GET | Log de operações (US5/AC2) | 2 |
| `/account/usuarios/<id>/reset-password/` | POST | Reset de senha com rate-limit (US6/AC2) | 2 |
| `/account/usuarios/<id>/resend-invite/` | POST | Reenviar convite (US8/AC4) | 2 |
| `/account/notifications/` | GET | Notificações on-the-fly (US9/AC5) | 2 |
| `/account/usuarios-matriz/` | GET | Matriz cross-company (US10/AC6, condicional) | 2 |
| `/account/empresas/<id>/licencas/` | GET | Licenças vinculadas à empresa | 6 |
| `/account/empresas/<id>/licencas/<lid>/modulos/` | GET | Módulos contratados na licença | 6 |
| `/account/empresas/<id>/usuarios-aplicativo/` | GET | Usuários por licença com papel/status | 6 |
| `/account/empresas/<id>/usuarios-aplicativo/<uid>/permissoes/` | GET | Permissões detalhadas do usuário na licença | 6 |

**Modificações em endpoints existentes:**
- `GET /account/usuarios/` — serializer ganha `invited_at`, `expires_at`, `is_expired`.

---

## Ordem de execução

```
Step 1 (fundação)
   ↓
Step 2 (backend) ──── pode rodar em paralelo com Step 3 se backend já tem testes ─┐
                                                                                   │
Step 3 (Usuários cards)                                                            │
   ↓                                                                               │
Step 4 (Detalhe usuário) ←─ depende de Step 2 endpoints ───────────────────────────┤
   ↓                                                                               │
Step 5 (Convites pendentes) ←─ depende de Step 2 (resend-invite, serializer) ──────┤
   ↓                                                                               │
Step 6 (Empresas refactor + detalhe)                                               │
   ↓                                                                               │
Step 7 (Módulos refactor + Dashboard notif) ←─ depende de Step 2 (notifications) ──┘
   ↓
Step 8 (Matriz — condicional)
   ↓
Step 9 (limpeza + verify)
```

## Success Criteria (checklist)

- [ ] `apps/account/src/components/` e `hooks/` criados e populados
- [ ] 5 páginas refatoradas (todas < 200 linhas, exceto detalhe do usuário que pode ir até 300)
- [ ] Tela `AccountUsuarioDetailPage` entregue com 4 blocos funcionando
- [ ] Tab "Convites pendentes" entregue com reenviar/cancelar
- [ ] Dashboard com bloco de notificações (3 tipos)
- [ ] Endpoints backend novos: 4 (5 se incluir matriz), todos com testes
- [ ] Rate-limit no reset de senha validado
- [ ] Design system validado via DevTools (tokens batem com Platform)
- [ ] `npm run typecheck && npm run lint && npm run build` verdes
- [ ] Smoke test manual ok
- [ ] Memory `project_go_control_account_app.md` atualizada

## Open Questions

(Veem do PRD — preciso de resposta antes do Step 2)

- OQ1: `CardGrid` mover para shared ou duplicar?
- OQ2: Log de operações — model novo `UserOperationLog` ou audit log existente?
- OQ3: Reset de senha — flow do Django (`PasswordResetView`) ou link temporário próprio?
- OQ4: Convites — adicionar `expires_at` no model `Membership`?
- OQ5: Notificações on-the-fly ok ou Eduardo quer persistência (read/unread state)?
- OQ6: Matriz cross-company (Step 8) entra nesta iteração?
- OQ7: Endpoint de toggle de acesso por empresa — abrir em `/account/` ou usar o `/backoffice/platform/` ajustando permissões?

## Handoff

- **Próximo agente esperado:** @apex-architect (se OQ1-OQ7 abrirem decisões arquiteturais, especialmente OQ2 e OQ3) **OU** direto para @bolt-executor após Eduardo responder as Open Questions.
- **Caminho do PRD:** `workspace/development/plans/account-redesign/[C]prd-account-redesign.md`
- **Caminho do plano:** este arquivo.
- **Verificação final:** @oath-verifier consome este plano + PRD e produz `[C]verification-account-redesign.md` no Step 9.
