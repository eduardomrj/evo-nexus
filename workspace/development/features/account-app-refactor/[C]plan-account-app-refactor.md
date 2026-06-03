---
author: claude
agent: compass-planner
type: work-plan
date: 2026-05-16
plan-name: account-app-refactor
status: draft
mode: direct
revision: 2 — sem menu/rotas de Licenças; integradas em /conta e /empresas/:id; review DS completo
prd: ./[C]prd-account-app-refactor.md
---

# Work Plan — Refatoração do app Account (GO Control ERP)

## Context

App Account (porta 5174) expõe "Módulos" como entidade do dono da conta, mas o modelo correto de negócio é **Licenças** (planos contratados). Esta refatoração substitui Módulos por Licenças, completa dados de Empresas, traz paridade Platform Admin para gestão de papéis/permissões pelo dono, e corrige inconsistências visuais. PRD irmão detalha 8 user stories com acceptance criteria.

## Objectives

- Remover item "Módulos" do menu; redirecionar `/modulos` para `/conta`
- Integrar seção de Licenças em `/conta` (todas as licenças da conta com filtro por empresa)
- Adicionar tab "Licenças" em `/empresas/:id` (apenas licenças da empresa em questão)
- Completar `AccountEmpresaDetailPage` exibindo 100% dos campos da empresa
- Habilitar dono da conta a alterar papéis de usuário em licenças (PATCH papel via side panel)
- Habilitar permissões granulares por licença (reuso `LicencaModuloTree`)
- Eliminar `#00FFA7` e hex hardcoded; review completo de DS + links em todas as telas

## Guardrails

### Must Have

- Rota `/modulos` deve redirecionar para `/conta` — não 404
- Menu lateral com exatamente 4 itens: Dashboard, Conta, Empresas, Usuários
- Toda chamada `PATCH /api/platform/licencas/*` validada contra o tenant do chamador (backend) — Apex confirma na Phase 3
- DS tokens: `var(--primary-color)` `#4F6AF5`, nunca `#00FFA7` (verde Evolution)
- `LicencaDetailSidebar` em `packages/shared/` (mover do `apps/platform/` se necessário)
- Review completo de todas as telas: links, hover, padding, DS tokens
- Smoke test manual passando nas 5 telas pré-existentes do Account

### Must NOT Have

- Item "Licenças" no menu lateral — licenças aparecem em contexto
- Novas rotas `/licencas` ou `/licencas/:id` — side panel substitui página separada
- Toggle de ativar/desativar módulo individual pelo dono da conta — quem decide é o plano
- Fluxo de contratação/cancelamento de licença no Account
- Novos endpoints de backend — todos já existem
- Alteração no app `apps/platform/` além de **extrair** componentes para `packages/shared`
- Mudanças no Dashboard `/` (fora do escopo)

## Task Flow

```
Step 1 (Scout discovery)
    │
    ▼
Step 2 (Apex architecture)
    │
    ▼
Step 3 (Backend guard) ──┐ (paralelizável com Step 4)
                          │
Step 4 (Shared extract) ──┤
                          ▼
                       Step 5 (Licenças pages + hooks)
                          │
                          ▼
                       Step 6 (Empresa Visão Geral + UI fixes)
                          │
                          ▼
                       Step 7 (Canvas DS pass + verify)
                          │
                          ▼
                       Step 8 (Oath + Lens — verify + review)
```

## Detailed TODOs

### Step 1 — Discovery e mapeamento de reuso

- **What:**
  - Confirmar localização atual de `LicencaDetailSidebar` (`apps/platform/` ou `packages/shared/`)
  - Listar tipos TS exportados/usados por `LicencaDetailSidebar` e `LicencaModuloTree`
  - Verificar se `useLicencaPapel`-equivalente já existe no Platform e se está extraível
  - Mapear todos os 12+ campos retornados por `GET /api/backoffice/account/empresas/:id/` (modelo Django + serializer)
  - Validar que `PATCH /api/platform/licencas/:id/usuarios/:uid/papel/` aceita chamadas do tenant do dono da conta hoje
- **Owner agent:** @scout-explorer
- **Acceptance criteria:**
  - Arquivo `scout-notes.md` (efêmero, descartar após Step 2) listando caminhos, exports, gaps
  - Open Questions Q2 e Q5 do PRD respondidas
- **Estimated complexity:** LOW

### Step 2 — Architecture decision record

- **What:** Produzir `[C]architecture-account-app-refactor.md` cobrindo:
  - **Decisão A:** `LicencaDetailSidebar` mora em `packages/shared/` (mover se necessário); padrão de uso em modo página vs side panel
  - **Decisão B:** `/usuarios/:id` abre como página dedicada (Q1 do PRD) — manter consistência com refatoração prévia do Account
  - **Decisão C:** Hook `useLicencaPapel` exportado de `packages/shared/src/hooks/` para uso cruzado
  - **Decisão D:** Multi-tenant guard no backend — se ausente, adicionar `IsAccountOwnerOfLicenca` permission class
  - Diagrama: como rotas + hooks + componentes se conectam
  - Pre-mortem: o que pode dar errado (acoplamento, tipos divergentes, permissão silenciosamente negada)
- **Owner agent:** @apex-architect (com @raven-critic em modo adversarial leve)
- **Acceptance criteria:**
  - ADR com Decisão / Drivers / Alternativas / Consequências
  - Q1 e Q5 do PRD resolvidas
  - Aprovação explícita do Eduardo antes de Step 3
- **Estimated complexity:** MEDIUM

### Step 3 — Backend: guard multi-tenant em PATCH papel (condicional)

- **What:**
  - **Se Step 2 detectou gap:** adicionar permission class `IsAccountOwnerOfLicenca` em `apps/platform/licencas/views.py` (ou equivalente)
  - Garantir que o dono da conta só pode operar em licenças do próprio tenant
  - Adicionar teste pytest cobrindo: dono A tenta editar licença do tenant B → 403
- **Owner agent:** @bolt-executor (paralelo com Step 4)
- **Acceptance criteria:**
  - Teste de regressão verde
  - Curl manual: dono tenant A com 403 ao tentar editar tenant B
  - Se Step 2 concluiu que guard já existe, este step é skipped e isso é documentado no plan log
- **Estimated complexity:** MEDIUM

### Step 4 — Extração de componentes para `packages/shared`

- **What:**
  - Mover `LicencaDetailSidebar` para `packages/shared/src/components/` (se ainda em `apps/platform/`)
  - Mover `LicencaModuloTree` + `MODULE_TREE_TOKENS` para `packages/shared/src/components/`
  - Extrair `useLicencaPapel` para `packages/shared/src/hooks/`
  - Re-exportar de `apps/platform/` para evitar breaking change
  - Garantir tipagem TS consistente (`LicencaInfo`, `ModuloPermissao`, `UserLicencaPapel`)
- **Owner agent:** @bolt-executor (paralelo com Step 3)
- **Acceptance criteria:**
  - `apps/platform/` continua compilando e funcionando (smoke test rápido em :5175)
  - `import { LicencaDetailSidebar } from '@evo/shared'` funciona em `apps/account/`
  - Sem duplicação de tipos — fonte única em `packages/shared`
- **Estimated complexity:** MEDIUM

### Step 5 — Integrar Licenças em /conta e /empresas/:id

- **What:**
  - Criar `components/LicencaCard.tsx` (usa `CardShell`, mostra: plano, empresa, status, expiração, nº usuários)
  - Criar `components/LicencaFiltersBar.tsx` (filtro por empresa + status, reutilizado nas duas telas)
  - Criar `hooks/useLicencas.ts` (lista da conta; aceita `empresa_id` opcional para filtro por empresa)
  - **Em `pages/AccountContaPage.tsx`:** adicionar seção "Licenças" abaixo dos dados cadastrais — CardGrid com `LicencaFiltersBar`, cada card abre `LicencaDetailSidebar`
  - **Em `pages/AccountEmpresaDetailPage.tsx`:** renomear tab "Módulos" → "Licenças"; trocar conteúdo da tab por CardGrid de licenças da empresa, cada card abre `LicencaDetailSidebar`
  - Atualizar `app/router.tsx`: redirect `/modulos → /conta` (`<Navigate replace>`)
  - Atualizar `BackofficeLayout` (em `packages/shared`): remover item "Módulos" do menu; garantir exatamente 4 itens (Dashboard, Conta, Empresas, Usuários)
  - Remover `pages/AccountModulosPage.tsx` e `hooks/useModulos.ts` (se órfão pós-refatoração)
- **Owner agent:** @bolt-executor
- **Acceptance criteria:**
  - US-1, US-2 do PRD verdes
  - `/conta` mostra seção Licenças com filtro por empresa funcional
  - `/empresas/:id` tab Licenças mostra apenas licenças da empresa
  - Card mostra: nome do plano, empresa, status, expiração, nº usuários
  - Side panel abre/fecha sem reload; clique em usuário usa `UsuarioLink` → `/usuarios/:id` (US-5)
  - `/modulos` redireciona para `/conta` em <100ms
  - Menu lateral tem exatamente 4 itens
- **Estimated complexity:** HIGH

### Step 6 — Empresa Visão Geral completa + tab Licenças

- **What:**
  - Em `pages/AccountEmpresaDetailPage.tsx`:
    - Expandir tab "Visão Geral" para todos os campos do `EmpresaSerializer` (razão social, fantasia, CNPJ, IE, IM, endereço completo, telefones, e-mail, regime, status, datas, observações)
    - Campos opcionais vazios renderizam `—` (não escondem)
    - Tab "Módulos" da empresa → renomear para "Licenças" se ainda existir como tab
  - Atualizar `hooks/useEmpresas.ts` se o detalhe não estiver puxando todos os campos
  - Componente `UsuarioLink` em `components/UsuarioLink.tsx` para padronizar links de usuário (US-5)
- **Owner agent:** @bolt-executor
- **Acceptance criteria:**
  - US-3, US-4 do PRD verdes
  - Tab "Visão Geral" mostra ≥ 12 campos (incluindo placeholders `—`)
  - Toda menção a usuário usa `UsuarioLink`
- **Estimated complexity:** MEDIUM

### Step 7 — DS pass + review completo de todas as telas

- **What:**
  - Abrir cada rota do Account no browser (Playwright) e auditar:
    - **DS tokens:** `getComputedStyle` por `#00FFA7`, `rgba(0,255,167,*)`, hex hardcoded — substituir por `var(--primary-color)` / `var(--info)` / `var(--success)`
    - **Links e botões:** cada link/botão navega para a rota correta; hover state visível; disabled states corretos
    - **CardGrid:** padding 16px, gap 16px, hover glow indigo, quebra responsiva 3→2→1 colunas
    - **Side panels:** abrem e fecham sem reload; overlay escuro; botão fechar funciona
    - **Formulários e dropdowns:** validação, loading state, toast de erro/sucesso
    - **Dados ausentes:** campos vazios mostram `—`, não ficam em branco
  - Telas a revisar: `/`, `/conta`, `/empresas`, `/empresas/:id` (todas as tabs), `/usuarios`, `/usuarios/:id`
- **Owner agent:** @canvas-designer
- **Acceptance criteria:**
  - US-8 do PRD verde
  - Zero ocorrências de hex hardcoded ou verde Evolution no CSS computado
  - Checklist de review preenchido para cada tela (link, DS, responsivo, side panels)
  - Screenshots evidenciando estado final de cada tela
- **Estimated complexity:** MEDIUM-HIGH

### Step 8 — Verify + Code Review

- **What:**
  - @lens-reviewer: code review 2-estágios (spec compliance vs PRD/AC + qualidade SOLID)
  - @oath-verifier: evidência por AC — output em `[C]verification-account-app-refactor.md`
  - @probe-qa: smoke test manual end-to-end nas 7 rotas
  - Verificar performance: redirect, hooks com retry, loading states
- **Owner agent:** @oath-verifier (lead) + @lens-reviewer + @probe-qa
- **Acceptance criteria:**
  - Todas as 8 user stories mapeadas a evidência (PASS / FAIL / INCOMPLETE)
  - Build de produção (`turbo build`) verde
  - Tests verdes (frontend + backend regressão)
- **Estimated complexity:** MEDIUM

## Success Criteria

- [ ] Menu lateral com exatamente 4 itens: Dashboard, Conta, Empresas, Usuários — sem Módulos
- [ ] Rota `/modulos` redireciona para `/conta` sem 404
- [ ] `/conta` exibe seção "Licenças" com CardGrid + filtro por empresa
- [ ] `LicencaDetailSidebar` abre ao clicar em licença em `/conta`
- [ ] `/empresas/:id` tem tab "Licenças" com licenças da empresa e side panel
- [ ] Dono da conta consegue trocar papel de usuário em uma licença (4 cliques)
- [ ] Permissões granulares por licença (árvore com checkboxes) operacional
- [ ] Tab "Visão Geral" de empresa exibe ≥ 12 campos cadastrais
- [ ] Toda menção a usuário em todas as telas usa `UsuarioLink` com navegação para `/usuarios/:id`
- [ ] `LicencaDetailSidebar`, `LicencaModuloTree`, `useLicencaPapel` em `packages/shared`
- [ ] Backend valida tenant em `PATCH /api/platform/licencas/:id/usuarios/:uid/papel/`
- [ ] Zero `#00FFA7` ou hex hardcoded no CSS computado do Account
- [ ] Review completo de todas as 6 rotas: links, DS, responsivo, side panels
- [ ] Smoke test manual passa nas 5 telas pré-existentes (sem regressão)
- [ ] Build de produção verde
- [ ] Todas as 8 user stories do PRD com evidência PASS no `[C]verification-*.md`

## Open Questions

- [ ] **Q1 (PRD):** `/usuarios/:id` página vs side panel quando acessado de licença? — Apex decide na Phase 3 (Step 2). Default deste plano: **página**.
- [ ] **Q2 (PRD):** `LicencaDetailSidebar` está em `packages/shared` ou ainda em `apps/platform`? — Scout responde no Step 1.
- [ ] **Q3 (PRD):** Logs de auditoria de mudança de papel/permissão pelo dono? — Out of scope nesta refatoração; registrar como follow-up se necessário.
- [ ] **Q4 (PRD):** `/licencas` permite renovar licença? — Decisão atual: **NÃO** (somente visualizar). Renovar fica no Platform / wizard.
- [ ] **Q5 (PRD):** Backend já tem guard multi-tenant em `PATCH papel`? — Scout responde no Step 1; Step 3 condicional.
- [ ] **Q6:** Algum dos hooks atuais (`useEmpresas`, `useUsuarios`) precisa virar shared também? Default: **não mover** salvo se houver duplicação evidente.

## Handoff

- **Next agent:** @apex-architect (Phase 3 — Solutioning) começa pelo Step 2 após Scout (Step 1)
- **Next skill:** dev-deep-dive opcional se Apex precisar refinar trade-offs no Step 2
- **Bloqueio para Build (Phase 4 / Bolt):** aprovação explícita do Eduardo sobre o ADR do Step 2
