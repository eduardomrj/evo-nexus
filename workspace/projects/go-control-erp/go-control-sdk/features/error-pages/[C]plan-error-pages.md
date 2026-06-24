# [C] Plano — Error Pages no go-control-sdk

**Projeto:** go-control-erp / go-control-sdk
**Feature:** error-pages
**Autor:** Compass (Planner)
**Data:** 2026-06-20
**Fase:** 2 (Planning) → handoff para Bolt (Fase 4)
**Inputs herdados:** Discovery (Echo) + Análise arquitetural (Apex) — decisões já tomadas pelo Eduardo

---

## Contexto

O `createAppRouter` do SDK hoje resolve rota desconhecida (`*`) com `<Navigate to={fallback} replace />` — redirect silencioso para `/`. Não há página de erro para 404 de rota nem tela para crashes/throws dentro das rotas protegidas (hoje: tela branca). Esta feature introduz um componente genérico `<ErrorPage>` e o liga ao router como comportamento padrão.

## Decisões já tomadas (NÃO reabrir)

1. **401/403 — intocado.** Redirect ao AUTH externo é deliberado. Não tocar em `apiClient.ts` nem `AuthGuard.tsx`.
2. **404 — somente rota** (wildcard `*`). NÃO interceptar 404 de API via axios.
3. **Default ativo (breaking).** A página 404 entra como padrão do `createAppRouter`. Apps podem fazer override por prop.

## Fato arquitetural descoberto (relevante para Bolt)

As classes visuais `login-root`, `login-card`, `login-logo-mark` usadas por `LoginPage`/`ChangePasswordPage` **NÃO estão definidas em nenhum CSS do SDK** (nem em `src/shared/styles/`, nem no `styles/` publicado) — são fornecidas pelos apps consumidores. Reusar essas classes no `ErrorPage` herdaria essa dependência externa e quebraria a tela em apps que não as definam.

Como o `ErrorPage` é **default-on** no router (renderiza sem o app pedir), ele precisa ser **autossuficiente em estilo**. O padrão correto já existe no SDK: `AppShell.tsx:42-70` injeta CSS via `<style>` no `<head>` com flag de idempotência (`ensureCssVars`) e tokens de fallback. O `ErrorPage` deve seguir esse mesmo padrão (`ensureErrorPageStyles()`), reusando os tokens (`var(--bg)`, `var(--surface-a)`, `var(--text)`, `var(--primary)`) que o app sobrescreve se importar `tokens.css`.

---

## Objetivos (resultados testáveis)

- O1 — Componente `<ErrorPage code={number} />` genérico, com presets internos para 404/500/503/network e props opcionais de override (`title`, `message`, `action`).
- O2 — Wildcard `*` do `createAppRouter` passa a renderizar `<ErrorPage code={404} />` por padrão (breaking), com escape hatch para o comportamento antigo (redirect).
- O3 — `errorElement` no `protectedRoute` renderiza `<ErrorPage code={500} />`, cobrindo crashes/throws (hoje tela branca).
- O4 — `ErrorPage` e `ErrorPageProps` exportados no barrel do SDK.
- O5 — `tsc --noEmit` limpo; nenhuma regressão no comportamento de auth (401/403).

## Guardrails

**Must have**
- Estilo autossuficiente via injeção `<style>` idempotente (padrão `AppShell`), sem depender de classes `login-*` nem de CSS do app.
- Tokens via `var(--*)` com fallback, ícones via PrimeIcons (já é peerDependency).
- Override de comportamento do wildcard preservando retrocompatibilidade para apps que dependem do redirect.

**Must NOT have**
- NÃO tocar `apiClient.ts`, `AuthGuard.tsx`, nem o fluxo 401/403.
- NÃO interceptar 404 de API via axios.
- NÃO usar SVG externo nem fontes novas.
- NÃO reusar as classes `login-*` (dependência de CSS externo).
- NÃO usar `!important` (regra do layout.css do projeto).

---

## Steps

### Step 1 — Criar o componente `ErrorPage` autossuficiente
**O que fazer:** criar `ErrorPage.tsx` com:
- `interface ErrorPageProps { code: number; title?: string; message?: string; action?: { label: string; onClick: () => void } }`
- Mapa interno `PRESETS: Record<number, { icon: string; title: string; message: string }>` cobrindo 404, 500, 503 e um preset `network` (chave numérica convencionada, ex. `0`); fallback genérico para códigos não mapeados.
- Função `ensureErrorPageStyles()` idêntica em padrão a `ensureCssVars`/`ensureFonts` do `AppShell` (`AppShell.tsx:42-70`): injeta um `<style>` com classes `error-*` (`error-root`, `error-card`, `error-code`, `error-title`, `error-message`, `error-action`) usando `var(--bg)`, `var(--surface-a)`, `var(--text)`, `var(--text-muted)`, `var(--primary)`, `var(--border)`, `var(--radius)`; flag de idempotência; chamada no topo do componente.
- Layout full-screen espelhando a estrutura visual da `LoginPage` (root centralizado + card), com ícone PrimeIcons grande, código, título, mensagem e botão de ação opcional.
- Props sobrescrevem o preset quando presentes.

**Arquivo(s):**
- `/home/evonexus/evo-projects/go-control/go-control-sdk/typescript/src/shared/components/ErrorPage.tsx` (novo)

**Critério:** `import { ErrorPage } from './ErrorPage'` compila; `<ErrorPage code={404} />` renderiza título/mensagem do preset 404; `<ErrorPage code={404} title="X" />` mostra "X"; `<ErrorPage code={999} />` cai no fallback genérico sem quebrar. `tsc --noEmit` limpo.

---

### Step 2 — Exportar no barrel do SDK
**O que fazer:** adicionar ao barrel de `shared` o export de `ErrorPage` e do tipo `ErrorPageProps`, seguindo o padrão das linhas existentes (ex.: bloco do `AuthCallbackPage`, `shared/index.ts:55-57`).

**Arquivo(s):**
- `/home/evonexus/evo-projects/go-control/go-control-sdk/typescript/src/shared/index.ts`

**Critério:** `import { ErrorPage, type ErrorPageProps } from '@automacao-software/go-control-sdk'` resolve no type-check. `tsc --noEmit` limpo.

---

### Step 3 — Wildcard `*` → `ErrorPage code=404` (breaking, default pedido)
**O que fazer:** em `createAppRouter`:
- Importar `ErrorPage` de `../shared/components/ErrorPage`.
- Substituir a rota wildcard atual (`router.tsx:96-99`, `element: <Navigate to={fallback} replace />`) por `element: <ErrorPage code={404} />` como **default**.
- Adicionar à `AppRouterConfig` uma flag de escape hatch para preservar retrocompatibilidade — ex.: `notFoundRedirect?: boolean` (default `false`). Quando `true`, o wildcard volta a ser `<Navigate to={fallback} replace />`.
- Manter o campo `fallback` (ainda usado pelo modo redirect).

**Arquivo(s):**
- `/home/evonexus/evo-projects/go-control/go-control-sdk/typescript/src/shell/router.tsx`

**Critério:** sem props extras, navegar para rota inexistente renderiza `ErrorPage 404` (não redireciona). Com `notFoundRedirect: true`, navega para `fallback`. `tsc --noEmit` limpo. Comentário JSDoc do topo do arquivo atualizado (hoje descreve `* → Navigate to fallback`).

---

### Step 4 — `errorElement` no protectedRoute → `ErrorPage code=500`
**O que fazer:** adicionar `errorElement: <ErrorPage code={500} />` ao objeto `protectedRoute` (`router.tsx:75-87`). Default-on (não há comportamento atual a quebrar — hoje é tela branca em throw). Opcional: permitir override via config (`errorElement?: React.ReactNode`) se for trivial; caso contrário deixar fixo e registrar como open question.

**Arquivo(s):**
- `/home/evonexus/evo-projects/go-control/go-control-sdk/typescript/src/shell/router.tsx`

**Critério:** um throw dentro de uma rota protegida renderiza `ErrorPage 500` em vez de tela branca (validável com uma rota de teste que dá `throw`). `tsc --noEmit` limpo.

---

### Step 5 — Sincronizar `styles/` publicado (se aplicável) e build
**O que fazer:** a estratégia escolhida injeta CSS via JS (`ensureErrorPageStyles`), então **não** há novo arquivo `.css` a publicar. Confirmar que nada em `styles/` precisa mudar. Rodar `bun run typecheck` (ou `tsc --noEmit`) no SDK e o `build` (`tsc`) para garantir que `dist/` compila com o novo componente e export.

**Arquivo(s):**
- `/home/evonexus/evo-projects/go-control/go-control-sdk/typescript/` (build do pacote)

**Critério:** `typecheck` e `build` verdes; `dist/index.d.ts` expõe `ErrorPage` e `ErrorPageProps`.

---

### Step 6 — Verificação de não-regressão e comunicação do breaking change
**O que fazer:**
- Confirmar que `apiClient.ts` e `AuthGuard.tsx` não foram tocados (`git diff --stat`).
- Documentar no PR/handoff que o wildcard mudou de redirect → 404 (breaking), listando os 4 apps consumidores (go-cobrança, go-account, go-message, go-pessoas) que precisam testar/optar pelo `notFoundRedirect` se dependiam do redirect silencioso.
- Bump de versão do SDK (minor → 1.3.0, dado o breaking de comportamento default; ou seguir a convenção de versionamento do time).

**Arquivo(s):**
- `/home/evonexus/evo-projects/go-control/go-control-sdk/typescript/package.json` (version)
- handoff/PR description

**Critério:** `git diff` confirma escopo restrito (apenas `ErrorPage.tsx`, `router.tsx`, `shared/index.ts`, `package.json`). Nota de breaking change presente no handoff. Lista dos 4 apps comunicada ao Eduardo.

---

## Critérios de sucesso (checklist)

> **Status: IMPLEMENTADO — 2026-06-20** (ADR-015 STEP-3; Oath PASS 2026-06-23; SDK v1.3.0)

- [x] `<ErrorPage code={404|500|503} />` renderiza preset correto; props sobrescrevem. _(ErrorPage.tsx — PRESETS map + fallback genérico)_
- [x] Estilo autossuficiente — funciona sem o app importar CSS novo nem definir classes `login-*`. _(ensureErrorPageStyles() via injeção `<style>` idempotente)_
- [x] Wildcard `*` renderiza 404 por padrão; `notFoundRedirect` restaura o redirect. _(router.tsx — AppRouterConfig.notFoundRedirect)_
- [x] `errorElement` cobre throws com 500 (sem mais tela branca). _(router.tsx linha 116 — errorElement: `<ErrorPage code={500} />`)_
- [x] `ErrorPage` + `ErrorPageProps` exportados no barrel. _(shared/index.ts linhas 52-53)_
- [x] 401/403, `apiClient.ts`, `AuthGuard.tsx` intocados. _(escopo restrito ao STEP-3 do ADR-015)_
- [x] `typecheck` + `build` verdes; `dist/` atualizado. _(`tsc --noEmit` 0 erros; v1.3.0)_
- [x] Breaking change comunicado aos 4 apps. _(wildcard → ErrorPage 404; escape hatch `notFoundRedirect: true`)_

## Open Questions

- OQ1 — Nome/convenção da chave do preset `network` no mapa numérico (`0`? `-1`? string-key separada?). Decisão de implementação para Bolt; baixo risco.
- OQ2 — `errorElement` deve ser configurável via `AppRouterConfig` ou fixo em 500? Risco baixo — fixo atende o pedido; tornar configurável só se trivial.
- OQ3 — Política de versionamento do bump (minor vs major) dado que o breaking é só de comportamento default e há escape hatch. Confirmar com Eduardo. Risco médio (afeta os 4 consumidores).

## Handoff

**Compass → Bolt (Fase 4).** Plano em `workspace/projects/go-control-erp/go-control-sdk/features/error-pages/[C]plan-error-pages.md`, tasks em `[C]tasks-error-pages.md`. Arquitetura definida por Apex (sem ADR formal — fits existing patterns). Open questions OQ1/OQ2 são decisões de implementação; OQ3 precisa de confirmação do Eduardo antes do publish. Output esperado: implementação dos 6 steps + self-verification (typecheck/build).
