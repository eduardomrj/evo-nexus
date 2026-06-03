# PRD — Refatoração Completa do App Account (GO Control ERP)

**Autor:** @compass-planner
**Owner do produto:** Eduardo Martins
**Data:** 2026-05-15
**Status:** Draft (aguardando aprovação)
**Slug:** `account-redesign`

---

## 1. Contexto e Problema

O app **Account** (`apps/account`, porta 5174) é o portal self-service dos **donos de conta** que adquiriram o GO Control ERP. Hoje ele cumpre o básico (5 páginas funcionais), mas:

- Toda a UI vive **inline** dentro dos `.tsx` das páginas (1.508 linhas em 5 arquivos). Não existe `src/components/` nem `src/hooks/`.
- A tela de Usuários e de Empresas usam `DataTable`, enquanto o padrão recente do app Platform (aprovado em 2026-05-14) é **card-based** com `CardGrid.tsx`.
- A tela de detalhe do usuário não existe: o dono da conta não consegue ver em quais empresas o usuário atua, ativar/desativar acesso por empresa, ver log de operações ou disparar reset de senha sem ir ao backoffice da Automação Software.
- Não há gestão de **convites pendentes** (reenviar, cancelar) — convites estão misturados na lista geral de usuários.
- Não há **notificações** de licença vencendo, usuário bloqueado, módulo desativado.
- A inconsistência visual entre Account e Platform já gerou ruído em demos.

## 2. Objetivos

- O1: Padronizar Account com o design system aprovado (dark theme, `CardGrid`, PrimeReact overrides do `index.css`).
- O2: Extrair componentes inline para `src/components/` e lógica de dados para `src/hooks/`, seguindo o padrão do app Platform.
- O3: Entregar a tela de detalhe do usuário (info, empresas+papéis, ativar/desativar por empresa, log de operações, reset de senha).
- O4: Entregar tela de detalhe da empresa (info, usuários por aplicativo, ações).
- O5: Adicionar Gestão de Convites Pendentes (alta prioridade) e Notificações/Alertas (alta prioridade).
- O6: Adicionar Visão Consolidada Usuários por Empresa (média prioridade), se não inflar a iteração.

## 3. Non-goals

- Histórico de faturamento, Auditoria geral de acessos, Suspensão temporária de empresa, Tokens de API, Painel de saúde — registrados como backlog em `[C]backlog-account.md`.
- Trocar o roteador, layout shell, ou autenticação. `BackofficeLayout` continua.
- Mudar a `api` (instância axios) ou criar `axios.create()` paralelo — ADR Decisão 4.
- Mudanças no app Platform (escopo separado).

## 4. Personas e User Stories

**Persona:** Dono de conta (cliente da Automação Software). Acessa em `:5174` com login JWT. Não é staff. Quer operar sua conta sem abrir ticket para a Automação.

- **US1 (Usuários):** Como dono de conta, quero ver meus usuários em cards e clicar em **Informações** para ver detalhes completos.
- **US2 (Usuário-detalhe):** Como dono de conta, quero ver em quais empresas cada usuário atua e qual papel tem em cada uma.
- **US3 (Bloquear/Permitir):** Como dono de conta, quero bloquear/permitir o login global de um usuário em um clique.
- **US4 (Acesso por empresa):** Como dono de conta, quero ativar/desativar o acesso de um usuário a uma empresa específica sem afetar as outras.
- **US5 (Log de operações):** Como dono de conta, quero ver o log das operações daquele usuário (login, alteração de papel, bloqueio) filtrável por data e empresa.
- **US6 (Reset de senha):** Como dono de conta, quero disparar o reset de senha do usuário sem precisar pedir ao suporte.
- **US7 (Empresas):** Como dono de conta, quero ver minhas empresas em cards e abrir detalhes para gerenciar usuários e ver dados cadastrais.
- **US8 (Convites pendentes):** Como dono de conta, quero ver os convites pendentes em uma lista separada, com ações de reenviar e cancelar.
- **US9 (Notificações):** Como dono de conta, quero ver na home alertas críticos: licença prestes a vencer, usuário recém-bloqueado, módulo desativado.
- **US10 (Cross-company users):** Como dono de conta, quero consultar a matriz "qual usuário tem qual papel em qual empresa" em uma visão única.

## 5. Acceptance Criteria (Given/When/Then)

### AC1 — Usuários (cards)

- **Given** estou logado como dono de conta e tenho 3+ usuários
  **When** abro `/usuarios`
  **Then** vejo um `CardGrid` com um card por usuário contendo nome, email, badge de status (active/invited/suspended), botão **Bloquear/Permitir** (alterna `status` entre `active` e `suspended`) e botão **Informações**.

- **Given** existem 0 usuários ativos além de mim
  **When** abro `/usuarios`
  **Then** vejo um empty state com CTA "Convidar primeiro usuário".

### AC2 — Detalhe do usuário

- **Given** estou na lista de usuários
  **When** clico em **Informações** de um usuário
  **Then** sou levado a `/usuarios/:id` com 4 blocos: (a) Info cadastral (nome, email, status, criado em, owner sim/não), (b) Empresas e papéis (lista de empresas onde o usuário tem `UsuarioAplicativo`, com papel atual, status do acesso, e toggle ativar/desativar), (c) Log de operações com filtros de data e empresa, (d) Botão "Resetar senha" no header.

- **Given** estou no detalhe do usuário
  **When** clico em "Desativar acesso" em uma empresa
  **Then** o `UsuarioAplicativo` daquela empresa muda para `status='suspended'` e o card de empresa atualiza imediatamente (optimistic update + revalidate).

- **Given** estou no detalhe do usuário
  **When** clico em **Resetar senha** e confirmo no modal
  **Then** o backend dispara o fluxo de reset (email com link) e vejo um toast "Email de reset enviado para …".

- **Given** o usuário só tem acesso a 1 empresa
  **When** abro o detalhe
  **Then** vejo só aquela empresa na lista, com toggle e papel.

### AC3 — Empresas (cards)

- **Given** tenho 2+ empresas
  **When** abro `/empresas`
  **Then** vejo `CardGrid` com card por empresa: razão social, nome fantasia, CNPJ, badge `ativa/inativa`, contagem de usuários, botão **Informações**.

- **Given** estou na lista
  **When** clico em **Informações**
  **Then** sou levado a `/empresas/:id` (a página `AccountEmpresaUsuariosPage` atual, agora chamada `AccountEmpresaDetailPage`) com tabs: Dados cadastrais, Usuários por aplicativo, Logs (opcional fase 2).

### AC4 — Convites Pendentes

- **Given** convidei 2 usuários e eles ainda não aceitaram
  **When** abro `/usuarios` aba "Convites pendentes" (ou rota `/convites`)
  **Then** vejo lista separada com email, data do convite, expira em, botões **Reenviar** e **Cancelar**.

- **Given** estou na lista de convites
  **When** clico em **Cancelar**
  **Then** confirmação por sidebar/modal, o `Membership.status='invited'` vai para `cancelled` (ou é deletado) e some da lista.

- **Given** um convite tem mais de 7 dias
  **When** abro a lista
  **Then** o card mostra badge "Expirado" e o botão é **Reenviar** (não Cancelar).

### AC5 — Dashboard com Notificações

- **Given** tenho 1 licença vencendo em < 14 dias
  **When** abro `/` (dashboard)
  **Then** vejo um banner/card de alerta vermelho/amarelo no topo: "Licença X vence em 9 dias".

- **Given** tenho 2 usuários `suspended` nas últimas 24h
  **When** abro o dashboard
  **Then** vejo um alerta informativo com link "2 usuários bloqueados recentemente".

- **Given** tenho um módulo desativado nas últimas 24h
  **When** abro o dashboard
  **Then** vejo notificação correspondente.

- **Given** não há eventos pendentes
  **When** abro o dashboard
  **Then** vejo o estado "Tudo certo" sem cards de alerta.

### AC6 — Visão consolidada usuários × empresas (média prioridade)

- **Given** tenho 2 empresas e 5 usuários
  **When** abro `/usuarios?view=matriz` (ou tab "Matriz" na página)
  **Then** vejo uma tabela densa: linhas = usuários, colunas = empresas, célula = papel atual (ou — se não tem acesso). Clique na célula abre o sidebar de detalhe do `UsuarioAplicativo`.

### AC7 — Módulos (refatorado)

- **Given** abro `/modulos`
  **When** carrega
  **Then** vejo `CardGrid` (não DataTable) com card por módulo: ícone, nome, aplicativo, badge de status (ativo/inativo/em_manutencao), toggle on/off no card.

### AC8 — Estrutura de pastas

- **Given** o app foi refatorado
  **When** inspeciono `apps/account/src/`
  **Then** existe `components/` com componentes reutilizáveis e `hooks/` com `useAccountUsuarios`, `useAccountEmpresas`, `useAccountModulos`, `useAccountOverview` (TanStack Query encapsulado).

### AC9 — Design system

- **Given** qualquer tela do Account
  **When** comparada lado a lado com a equivalente do Platform
  **Then** segue exatamente os tokens (`--evo-bg`, `--evo-surface`, `--evo-accent` etc.) e overrides do `index.css`. Validado via DevTools.

### AC10 — Sem regressão funcional

- **Given** as features atuais (convidar usuário, criar empresa, toggle de módulo)
  **When** executadas na versão refatorada
  **Then** funcionam idênticas ou melhor — backend não muda comportamento para fluxos existentes.

## 6. Constraints

- **Stack travado:** React + Vite + PrimeReact + TanStack Query + axios via `@/lib/api`.
- **Não criar** axios.create() paralelo (ADR Decisão 4).
- **Não zerar padding** de `.p-tabview-panels` no CSS — controlar no TSX (memory `feedback_canvas_primereact_padding`).
- Manter `BackofficeLayout` do shared.
- Componentes reutilizáveis entre Account e Platform devem ir para `packages/shared/src/components/` quando houver claro reuso (ex: `CardGrid` já está lá? confirmar; senão promover).
- Idioma: pt-BR em todos os labels.

## 7. Risks

| Risco | Severidade | Mitigação |
|---|---|---|
| Endpoints de log/reset/notificações não existem no backend → escopo expande | Alta | Listar explicitamente os novos endpoints no plano (Step 2) e implementar backend antes do frontend |
| Componente `CardGrid` está em `apps/platform/src/components/` (não em shared) | Média | Step 1 promove para `packages/shared/src/components/` se reuso confirmado; senão duplica |
| Migrar de DataTable para Cards pode quebrar UX para listas grandes (>50 usuários) | Média | Manter fallback de busca + paginação no `CardGrid`; se necessário, oferecer toggle "ver como tabela" só para Usuários |
| Reset de senha via portal — risco de segurança se não tiver rate limit | Alta | Validar com @vault-security antes do merge; backend deve aplicar throttle e gerar token expirável |
| Quebrar uso atual em produção durante refactor | Média | Trabalhar em branch dedicada, testes via Probe antes do merge |

## 8. Open Questions

- OQ1: `CardGrid.tsx` já está em `packages/shared/` ou ainda em `apps/platform/src/components/`? Promover ou duplicar?
- OQ2: Log de operações vai vir de um model novo (`UserOperationLog`) ou reutilizar `Membership.history` / Django audit log existente?
- OQ3: Reset de senha — vamos disparar email via Django (`PasswordResetView`) ou gerar um link de senha temporária?
- OQ4: Convites têm expiração configurada? (modelo `Membership.invited_at` existe; campo `expires_at` precisa ser adicionado?)
- OQ5: Notificações são calculadas on-the-fly no `/overview/` ou existe model `Notification` separado? Recomendação: começar on-the-fly (sem persistência) para evitar criar feature pesada.
- OQ6: Matriz cross-company entra nesta iteração ou fica para v2?

Essas perguntas vão para `workspace/development/plans/[C]open-questions.md` também.

## 9. Success Metrics

- 100% dos `AccountAlgumaCoisaPage.tsx` < 200 linhas após refactor (atual: maior é 431).
- 0 componentes inline duplicados em mais de uma página.
- 100% das telas validadas no DevTools usando tokens do design system (`--evo-*`).
- Tempo de carga `/usuarios` < 800ms em rede local com 50 usuários.
- 0 regressões reportadas pelo Eduardo no smoke test pós-merge.

## 10. Handoff esperado

- **Compass → Apex (opcional):** se OQ2/OQ3 abrirem decisões arquiteturais (modelo de log, mecânica de reset). Para o resto, ir direto para Bolt.
- **Compass → Bolt:** com o plano (`[C]plan-account-redesign.md`) após Eduardo aprovar.
- **Bolt → Oath:** verificação final contra os ACs deste PRD.

---

**Próximo passo:** Eduardo revisa este PRD + plano e responde com "proceed" para liberar Bolt.
