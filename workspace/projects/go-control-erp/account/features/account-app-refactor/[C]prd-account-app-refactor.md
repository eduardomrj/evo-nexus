---
author: claude
agent: compass-planner
type: prd
date: 2026-05-16
feature: account-app-refactor
status: draft
revision: 2 — sem menu Licenças; licenças integradas em /conta e /empresas/:id
---

# PRD — Refatoração do app Account (GO Control ERP)

## 1. Visão do Produto

O app **Account** (porta 5174) é o portal do **dono da conta** no GO Control ERP. Hoje ele expõe um conceito errado — Módulos — que é responsabilidade do Platform Admin (operação Evolution), não do cliente. O dono da conta não escolhe quais módulos ficam ativos; ele consome **licenças** (planos contratados) que já trazem módulos embarcados. Esta refatoração corrige o modelo mental, completa dados de Empresas e dá ao dono o controle sobre **papéis de licenças** e **permissões** — paridade funcional com o Platform Admin no escopo restrito da própria conta.

### Persona

**Dono da conta** (admin tenant)
- Tem 1+ empresas cadastradas dentro da própria conta
- Cada empresa pode ter 1+ licenças contratadas (planos)
- Cada licença vincula usuários da conta com um papel específico
- NÃO escolhe módulos individualmente — isso é decidido pelo plano da licença

### User Journey

```
Login → Dashboard (KPIs + alertas)
  │
  ├─ /conta            → dados cadastrais + seção "Licenças da Conta"
  │                       (todas as licenças, cards; clique abre side panel)
  │
  ├─ /empresas         → lista todas as empresas da conta
  │   └─ /empresas/:id → detalhe da empresa
  │       ├─ Visão Geral (dados completos, hoje incompletos)
  │       ├─ Licenças   → só licenças desta empresa; clique abre side panel
  │       └─ Usuários   → matrix de acesso; clique abre side panel
  │
  └─ /usuarios         → lista de usuários da conta
      └─ /usuarios/:id → perfil do usuário + acessos
```

**Decisão de navegação:** Não há item "Licenças" no menu lateral. Licenças são sempre
exibidas em contexto — globais em `/conta`, por empresa em `/empresas/:id`. Item
"Módulos" é removido do menu (rota `/modulos` redireciona para `/conta`).

## 2. Problema

| # | Problema observado | Impacto |
|---|---|---|
| P1 | Tela de Empresas não exibe todos os dados cadastrais | Dono não consegue auditar/atualizar empresa pelo Account |
| P2 | Menu "Módulos" induz o dono a achar que ele controla módulos | Confunde modelo de negócio; cria expectativa de toggle que não deveria existir |
| P3 | Falta visibilidade de **Licenças** — coisa que o dono realmente consome | Para saber o que contratou, hoje precisa ir ao Platform Admin (acesso Evolution-only) |
| P4 | Não há gestão de **papéis de licença** pelo dono | Toda mudança de papel precisa passar pela operação Evolution — gargalo de suporte |
| P5 | UI de Usuários e Empresas com tokens DS inconsistentes e layout quebrado | Inconsistência visual em relação ao restante do GO Control |

## 3. Goals

1. Substituir a área de "Módulos" por "Licenças" como entidade de primeira classe no Account
2. Completar a tela de Empresas exibindo 100% dos dados cadastrais persistidos no backend
3. Dar autonomia ao dono da conta para alterar papéis dos usuários em suas licenças (paridade Platform Admin no escopo da conta)
4. Reaproveitar componentes do `packages/shared` e do Platform Admin — não duplicar implementação
5. Eliminar inconsistências visuais (DS tokens, layout) em Usuários e Empresas

## 4. Non-Goals (Out of Scope)

- **NÃO** dar ao dono da conta capacidade de ativar/desativar módulos individualmente — isso continua sendo decisão do plano contratado
- **NÃO** permitir contratar/cancelar licenças pelo Account — fluxo de cobrança fica no Platform Admin / wizard de nova licença
- **NÃO** redesenhar o Dashboard (`/`) — fica como está
- **NÃO** alterar endpoints do backend (já estão prontos no Platform Admin e reutilizáveis)
- **NÃO** alterar o app `apps/platform/` (somente reaproveitar componentes de `packages/shared`)
- **NÃO** introduzir nova autenticação ou middleware — segue o modelo multi-tenant atual

## 5. User Stories e Acceptance Criteria (Given/When/Then)

### US-1 — Remover "Módulos" do menu; licenças em contexto

**Como** dono da conta
**Quero** que o menu não mostre "Módulos" nem "Licenças" como item isolado
**Para** ter uma navegação limpa onde licenças aparecem em contexto (conta / empresa)

**Acceptance Criteria:**
- **Given** estou logado no Account
  **When** o `BackofficeLayout` renderiza o sidebar
  **Then** vejo exatamente 4 itens: Dashboard, Conta, Empresas, Usuários — **sem** Módulos nem Licenças
- **Given** acesso a rota legada `/modulos`
  **When** o router resolve
  **Then** sou redirecionado para `/conta` sem 404

### US-2 — Licenças da conta consolidadas em /conta

**Como** dono da conta
**Quero** ver todas as licenças da conta diretamente na página /conta
**Para** ter visão consolidada do que contratei sem sair da tela de conta

**Acceptance Criteria:**
- **Given** minha conta tem M licenças no total
  **When** acesso `/conta` e rolo para a seção "Licenças"
  **Then** vejo um `CardGrid` com M cards, cada card mostrando: nome do plano, empresa vinculada, status (ativa/expirada/trial), data de expiração, contagem de usuários
- **Given** clico em um card de licença
  **When** o side panel abre
  **Then** vejo `LicencaDetailSidebar` com módulos incluídos, usuários vinculados e papéis
- **Given** filtro por empresa
  **When** seleciono uma empresa no filtro
  **Then** o CardGrid filtra sem reload

### US-3 — Empresa com dados completos

**Como** dono da conta
**Quero** ver todos os dados cadastrais de cada empresa
**Para** auditar e manter informação consistente

**Acceptance Criteria:**
- **Given** acesso `/empresas/:id` na tab "Visão Geral"
  **When** a página carrega
  **Then** vejo TODOS os campos retornados por `GET /api/backoffice/account/empresas/:id/` (razão social, fantasia, CNPJ, IE, IM, endereço completo, telefones, e-mail, regime tributário, status, datas de criação/atualização, observações)
- **Given** algum campo opcional está vazio no backend
  **When** a UI renderiza
  **Then** mostra placeholder `—` (não esconde o campo)

### US-4 — Licenças por empresa com side panel

**Como** dono da conta
**Quero** clicar em uma licença na tab "Licenças" da empresa
**Para** ver detalhes da licença e módulos incluídos sem sair da página

**Acceptance Criteria:**
- **Given** estou em `/empresas/:id` aba "Licenças"
  **When** clico em um card de licença
  **Then** o `LicencaDetailSidebar` abre à direita com: nome do plano, módulos incluídos (árvore), usuários vinculados com papéis, data de expiração, ações (Editar papéis)
- **Given** o sidebar está aberto
  **When** clico fora ou no botão fechar
  **Then** o sidebar fecha sem reload da página

### US-5 — Link de usuário sempre clicável

**Como** dono da conta
**Quero** que toda menção a um usuário seja um link
**Para** acessar rapidamente o perfil dele

**Acceptance Criteria:**
- **Given** vejo um usuário em qualquer tela (licença, empresa, dashboard)
  **When** clico no nome ou e-mail
  **Then** sou levado para `/usuarios/:id` OU um side panel `UsuarioDetailSidebar` abre (escolha de implementação documentada na arquitetura)
- **Given** o usuário não existe mais (foi removido)
  **When** o link é renderizado
  **Then** o nome aparece com estilo `muted` e o link é desabilitado

### US-6 — Alterar papel de usuário em uma licença

**Como** dono da conta
**Quero** alterar o papel de um usuário em uma licença específica
**Para** ajustar permissões sem precisar pedir suporte à Evolution

**Acceptance Criteria:**
- **Given** sou dono da conta e estou no detalhe de uma licença
  **When** clico em "Editar papel" para um usuário
  **Then** vejo dropdown com papéis disponíveis (mesmo conjunto do Platform Admin)
- **Given** seleciono um papel diferente
  **When** confirmo
  **Then** `PATCH /api/platform/licencas/:id/usuarios/:uid/papel/` é chamado, e ao sucesso a UI atualiza o papel sem reload
- **Given** falta de permissão ou erro 4xx/5xx
  **When** a chamada retorna erro
  **Then** vejo toast de erro e o papel anterior é mantido na UI

### US-7 — Visualizar permissões granulares por licença

**Como** dono da conta
**Quero** ter o mesmo módulo de "Permissões de Licença" que existe no Platform Admin
**Para** configurar acesso fino dos meus usuários

**Acceptance Criteria:**
- **Given** estou no detalhe de uma licença
  **When** clico em "Permissões"
  **Then** vejo a árvore de módulos/telas/recursos com checkboxes igual ao Platform Admin (componente `LicencaModuloTree`)
- **Given** marco/desmarco itens
  **When** clico em "Salvar"
  **Then** as permissões são persistidas via endpoint do Platform reaproveitado, e a UI dá feedback de sucesso

### US-8 — UI consistente com DS tokens

**Como** dono da conta
**Quero** que o app pareça parte do mesmo produto que o Platform Admin
**Para** ter uma experiência coesa

**Acceptance Criteria:**
- **Given** inspeciono qualquer tela do Account via DevTools
  **When** verifico cores
  **Then** **não há** uso de `#00FFA7` (verde Evolution) nem hex hardcoded; só tokens DS (`var(--primary-color)` `#4F6AF5`, `var(--info)`, `var(--success)`)
- **Given** comparo o layout de Empresas e Usuários
  **When** olho padding, gaps, hover de cards
  **Then** segue regras de `CardGrid` documentadas em `MODULE_TREE_TOKENS.md` e DS Patterns
- **Given** abro o app em mobile (sm)
  **When** o grid quebra
  **Then** quebra para 1 coluna sem layout quebrado

## 6. Mapeamento de Rotas — Nova Estrutura

### Rotas (sem mudança de quantidade)

| Rota | Página | Status pós-refatoração |
|---|---|---|
| `/` | AccountDashboardPage | **mantida** |
| `/conta` | AccountContaPage | **expandida — seção de Licenças da Conta adicionada** |
| `/empresas` | AccountEmpresasPage | **mantida (UI revisada)** |
| `/empresas/:id` | AccountEmpresaDetailPage | **atualizada — Visão Geral completa + tab Licenças** |
| `/modulos` | AccountModulosPage | **REMOVIDA — redireciona para `/conta`** |
| `/usuarios` | AccountUsuariosPage | **mantida (UI revisada)** |
| `/usuarios/:id` | AccountUsuarioDetailPage | **mantida** |

### Redirects

- `/modulos` → `/conta` (replace, sem 404)
- Sem novas rotas — licenças aparecem via side panel dentro das páginas existentes

### Menu lateral (BackofficeLayout)

```
Dashboard   /
Conta       /conta       ← inclui seção de licenças
Empresas    /empresas    ← detalhe tem tab Licenças por empresa
Usuários    /usuarios
```

Removidos: Módulos (era item incorreto), Licenças (desnecessário como item isolado)

## 7. Componentes — Criar vs Reutilizar

### Reutilizar de `packages/shared`

- `BackofficeLayout` — atualizar item de menu de "Módulos" para "Licenças"
- `CardGrid`, `CardShell`, `CardBody`, `CardFooter`, `SkeletonCard` — já existem
- `StatusBadge` — para status de licença (ativa/expirada/trial)
- `LicencaDetailSidebar` — **mover de `apps/platform/` para `packages/shared/`** se ainda não estiver lá; reusar no Account

### Reutilizar do Platform Admin (mover para `packages/shared` se necessário)

- `LicencaModuloTree` — árvore de módulos/telas com checkboxes
- `UserLicencaPapelDropdown` — dropdown de seleção de papel (se existir, senão criar minimal)
- Lógica de gestão de UserLicenca → extrair hook compartilhado `useLicencaPapel`

### Criar novos no `apps/account/`

| Componente | Localização | Propósito |
|---|---|---|
| `LicencaCard` | `components/` | Card individual de licença (usa `CardShell`) |
| `LicencaFiltersBar` | `components/` | Filtros inline: empresa, status, busca — usado em /conta e /empresas/:id |
| `UsuarioLink` | `components/` | Link/anchor padronizado para usuário (US-5) |
| `useLicencas` | `hooks/` | Lista de licenças da conta (com filtro opcional por empresa_id) |
| `useLicencaPapel` | `hooks/` (ou shared) | Mutação de papel via `PATCH /api/platform/licencas/:id/usuarios/:uid/papel/` |

Sem novas páginas — licenças integradas nas páginas existentes via seção e side panel.

### Backend — sem novos endpoints

Todos os endpoints já existem (listados na entrada). Confirmar permissão multi-tenant para `PATCH /api/platform/licencas/:id/usuarios/:uid/papel/` quando chamado pelo dono da conta no contexto do tenant correto.

## 8. Constraints

- **Stack:** React + TS + PrimeReact, monorepo Turborepo
- **DS tokens:** `var(--primary-color)` = `#4F6AF5` (indigo), NUNCA `#00FFA7`
- **Backend:** Django REST + django-tenants — toda chamada precisa respeitar o tenant do usuário logado
- **Não duplicar** componentes — preferir `packages/shared` quando o uso é compartilhado com Platform Admin
- **Multi-tenant:** o dono da conta só pode editar papéis/permissões de licenças que pertençam à sua própria conta (validação no backend obrigatória)

## 9. Risks

| Risco | Mitigação |
|---|---|
| `PATCH /api/platform/licencas/:id/usuarios/:uid/papel/` não valida tenant do chamador | Validar no Apex (Phase 3) — pode exigir guard adicional no backend |
| `LicencaDetailSidebar` está acoplado a tipos do Platform Admin | Apex avalia interface; se acoplado, extrair tipos para `packages/shared` |
| Redirect `/modulos → /licencas` pode confundir usuários acostumados | Adicionar toast/banner explicativo no primeiro acesso pós-deploy |
| Permissões granulares na licença podem expor árvore de módulos não autorizados | Backend deve retornar somente módulos do plano da licença em questão |

## 10. Open Questions

- [ ] **Q1:** `/usuarios/:id` deve abrir como página ou side panel quando acessado de dentro de uma licença? (Apex decide UX trade-off na Phase 3)
- [ ] **Q2:** `LicencaDetailSidebar` já está em `packages/shared` ou ainda em `apps/platform/`? Scout precisa confirmar.
- [ ] **Q3:** O dono da conta deve poder ver **logs de auditoria** das mudanças de papel/permissão? (Out of scope nesta refatoração, mas vale registrar para v2)
- [ ] **Q4:** A tela `/licencas` deve permitir **renovar** uma licença próxima do vencimento ou só visualizar? (Atual escopo = só visualizar; ação de renovar é Platform Admin)
- [ ] **Q5:** Validar com o backend se há permissão multi-tenant explícita em `/api/platform/licencas/*` quando o chamador é dono da conta. Se não, abrir ticket adicional para o backend.

## 11. Success Metrics

- Dono da conta consegue trocar papel de um usuário em uma licença em ≤ 4 cliques sem suporte
- Zero ocorrências de `#00FFA7` no CSS computado do Account em validação DevTools
- Tab "Visão Geral" de Empresa exibe ≥ 12 campos cadastrais (vs ~5 atuais)
- Redirect de `/modulos` para `/licencas` ≤ 100ms
- Zero regressões nas 5 telas pré-existentes do Account (smoke test manual)

## 12. Handoff

- **Phase 3 — Solutioning (@apex-architect):** validar reuso de `LicencaDetailSidebar`, decidir Q1 (página vs side panel), confirmar multi-tenant guard no `PATCH papel`. Output: `[C]architecture-account-app-refactor.md`.
- **Phase 4 — Build (@bolt-executor):** executar plano (`[C]plan-account-app-refactor.md`) em ordem, com @canvas-designer para UI/DS e @grid-tester para regression
- **Phase 5 — Verify (@oath-verifier + @lens-reviewer):** mapear cada US/AC a evidência
