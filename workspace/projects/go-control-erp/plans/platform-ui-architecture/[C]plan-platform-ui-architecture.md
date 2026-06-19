---
title: "Plano — Arquitetura de Reutilização de UI na Plataforma GO Control"
date: 2026-06-18
author: Oracle + Eduardo
status: approved
version: "1.0"
prd_ref: "[C]prd-platform-ui-architecture.md"
---

# Plano de Implementação — Arquitetura de UI da Plataforma

## Ordem de execução

```
Fase 1 — Service Registry (D3)         ← base para tudo
Fase 2 — go-pessoas-ui (D1, primeiro módulo)
Fase 3 — Manifest endpoint (D2)
Fase 4 — Padrão replicado (D1 para novos módulos)
```

---

## Fase 1 — Service Registry de URLs [CONSTRUIR NOVO]

**Objetivo:** admin vira fonte da verdade de URLs por ambiente. Apps consultam no bootstrap.

### Step 1.1 — Admin: modelo e CRUD de app registry

**Repo:** go-control-erp (admin backend)
**Agente:** Bolt

- Criar modelo `AppRegistry` (slug, label, ativo)
- Criar modelo `AppEnvironmentUrl` (app FK, environment: dev|staging|prod, api_url)
- Migration + admin Django
- Endpoint `GET /api/v1/admin/apps/{slug}/urls?env={env}` → `{ api_url: "..." }`
- Endpoint `GET /api/v1/admin/apps/` → lista todos os apps registrados

**Aceita quando:**
- [ ] Models e migrations aplicadas
- [ ] CRUD funcional no Django admin
- [ ] Endpoint de consulta retorna URL correta por env
- [ ] go-pessoas, go-cobranca, go-payment-hub pré-cadastrados com URLs dev

---

### Step 1.2 — Frontend admin: tela de gerenciamento de apps

**Repo:** go-control-admin frontend
**Agente:** Bolt + Canvas

- Tela `/apps` no admin com listagem de apps registrados
- Form de edição: URLs por ambiente (dev / staging / prod)
- Validação de URL antes de salvar

**Aceita quando:**
- [ ] Tela acessível no menu do admin
- [ ] CRUD de URLs por app funcional
- [ ] Validação de formato de URL

---

### Step 1.3 — SDK: GoControlRegistry helper

**Repo:** go-control-sdk
**Agente:** Bolt

- Criar `GoControlRegistry` em `src/registry/`
- Método `load(apps: string[], opts: { env: string, adminUrl: string })`
- Hierarquia de resolução:
  1. Consulta `GET {adminUrl}/api/v1/admin/apps/{slug}/urls?env={env}`
  2. Em caso de sucesso: salva em localStorage com TTL (chave: `go_ctrl_reg_{slug}_{env}`)
  3. Em caso de falha: lê localStorage
  4. Se localStorage vazio: usa `import.meta.env.VITE_{SLUG_UPPER}_API_URL ?? '/api/v1'`
- Método `getUrl(slug: string): string`
- TTL configurável (default: 3600s dev, 86400s prod)
- Publicar como `@automacao-software/go-control-sdk@1.2.0`

**Aceita quando:**
- [ ] `GoControlRegistry.load()` e `.getUrl()` exportados pelo SDK
- [ ] Hierarquia de resolução testada (admin up, admin down + cache, admin down sem cache)
- [ ] TTL respeitado — nova consulta ao admin após expirar
- [ ] TypeCheck sem erros

---

## Fase 2 — go-pessoas-ui (primeiro módulo) [CONSTRUIR NOVO]

**Objetivo:** `@automacao-software/go-pessoas-ui` publicado e go-cobranca consumindo.

### Step 2.1 — Extrair e corrigir packages/pessoas

**Repo:** go-pessoas
**Agente:** Bolt

- Mover `apps/go-pessoas/src/features/pessoas/{api,hooks,types,utils}/` para dentro de
  `packages/pessoas/src/`
- Substituir todos os imports `@go-pessoas/*` por imports relativos
- Remover `PessoasMountProvider` (redundante — auth vem do SDK do app hospedeiro)
- Configurar `api.ts` para usar `GoControlRegistry.getUrl('go-pessoas')`
  com fallback para `import.meta.env.VITE_GO_PESSOAS_API_URL ?? '/api/v1'`
- Refatorar `PessoasListPage` para receber `onNavigate: (path: string) => void` por prop
  (remover `useNavigate()` interno)
- Adicionar `vite.config.ts` com `build.lib` configurado
- Atualizar `package.json`: `main: dist/index.js`, `types: dist/index.d.ts`,
  `peerDependencies` idênticas ao SDK

**Aceita quando:**
- [ ] `pnpm build` dentro de `packages/pessoas/` gera `dist/` sem erros
- [ ] `dist/index.js` e `dist/index.d.ts` presentes
- [ ] Nenhum import `@go-pessoas/*` no código da lib
- [ ] TypeCheck sem erros

---

### Step 2.2 — Publicar @automacao-software/go-pessoas-ui

**Agente:** Bolt + Flow

- Atualizar `package.json` com nome `@automacao-software/go-pessoas-ui`
- Adicionar `.npmrc` com `@automacao-software:registry=https://npm.pkg.github.com`
- Publicar `npm publish` via GitHub Actions ou manualmente
- Versão inicial: `0.1.0`

**Aceita quando:**
- [ ] Pacote visível em `https://github.com/orgs/Automacao-Software/packages`
- [ ] Instalável via `npm install @automacao-software/go-pessoas-ui` com `NODE_AUTH_TOKEN`

---

### Step 2.3 — Migrar go-cobranca para usar a lib

**Repo:** go-cobranca
**Agente:** Bolt

- Adicionar `@automacao-software/go-pessoas-ui` como dependência
- Adicionar `.npmrc` (se não existir)
- Substituir `features/pagadores/PagadoresPage.tsx` por uso de `PessoasListPage`
  com `onNavigate` configurado para as rotas do go-cobranca
- Remover reimplementação local: `features/pagadores/{api,hooks,types}.ts`
- Bootstrap: chamar `GoControlRegistry.load(['go-pessoas'])` na inicialização do app

**Aceita quando:**
- [ ] PagadoresPage usa `PessoasListPage` da lib
- [ ] Arquivos de reimplementação local removidos
- [ ] TypeCheck sem erros no go-cobranca
- [ ] Funcional em dev (com `VITE_GO_PESSOAS_API_URL` ou registry)

---

## Fase 3 — Manifest endpoint [CONSTRUIR NOVO]

**Objetivo:** cada app expõe sua estrutura. Admin sincroniza com um clique.

### Step 3.1 — Contrato e implementação no go-pessoas

**Repo:** go-pessoas (backend)
**Agente:** Bolt

- Definir schema JSON do manifest (baseado no PRD)
- Implementar `GET /api/v1/manifest` no go-pessoas como implementação de referência
- Endpoint público (sem auth) ou com auth de serviço (a decidir)
- Retorna: app slug, version, label, menus com telas aninhadas

**Aceita quando:**
- [ ] `GET /api/v1/manifest` retorna JSON válido conforme schema do PRD
- [ ] Menus e telas refletem a estrutura real do app
- [ ] Schema documentado para replicar nos demais apps

---

### Step 3.2 — Admin: botão sincronizar + lógica de upsert

**Repo:** go-control-admin (backend + frontend)
**Agente:** Bolt

- Admin backend: endpoint `POST /api/v1/admin/apps/{slug}/sync-manifest`
  - Chama `GET {app_url}/api/v1/manifest`
  - Faz upsert de menus e telas no banco
  - Telas removidas marcadas como `ativo=False` (não deletadas)
  - Preserva associações existentes com Planos
- Admin frontend: botão "Sincronizar módulo" na tela de cadastro do app
  - Mostra diff do que vai mudar antes de confirmar
  - Feedback de sucesso/erro

**Aceita quando:**
- [ ] Sincronização cria/atualiza menus e telas corretamente
- [ ] Telas removidas do app ficam `ativo=False` no admin (não deletadas)
- [ ] Associações com Planos preservadas após sync
- [ ] Frontend mostra resultado da sync com contador de alterações

---

### Step 3.3 — Replicar manifest nos demais apps

**Repos:** go-cobranca, go-payment-hub, go-message
**Agente:** Bolt (por app)

- Implementar `GET /api/v1/manifest` seguindo o schema de referência do go-pessoas
- Sincronizar no admin após cada implementação

**Aceita quando:**
- [ ] Cada app tem endpoint de manifest funcional
- [ ] Admin sincronizado com estrutura atualizada de cada app

---

## Fase 4 — Padrão replicado para novos módulos [DOCUMENTAR]

**Objetivo:** qualquer novo módulo segue o padrão sem ter que descobrir do zero.

### Step 4.1 — Documentação do padrão de feature-lib

**Agente:** Quill

- `docs/platform/feature-libs-pattern.md` no go-control-sdk ou repo de docs
- Passo a passo: como criar uma nova `@automacao-software/{modulo}-ui`
- Checklist de publicação
- Exemplo de bootstrap com `GoControlRegistry`

### Step 4.2 — go-produtos-ui (quando go-produtos estiver pronto)

- Replicar exatamente o padrão da go-pessoas-ui
- `@automacao-software/go-produtos-ui` com `ProdutoPicker`, `ProdutoForm`, `ProdutosListPage`

---

## Resumo de dependências

```
Step 1.1 (admin backend registry)
  → Step 1.2 (admin frontend)
  → Step 1.3 (SDK registry helper)
      → Step 2.1 (extrair go-pessoas-ui)
          → Step 2.2 (publicar)
              → Step 2.3 (migrar go-cobranca)

Step 3.1 (manifest go-pessoas) — paralelo à Fase 2
  → Step 3.2 (admin sync)
      → Step 3.3 (demais apps)

Step 4.1 — após Fase 2 completa
Step 4.2 — quando go-produtos estiver pronto
```

---

## Agentes sugeridos por step

| Step | Agente principal | Suporte |
|------|-----------------|---------|
| 1.1 | Bolt | Apex (review modelo) |
| 1.2 | Bolt + Canvas | — |
| 1.3 | Bolt | Grid (testes hierarquia de resolução) |
| 2.1 | Bolt | Lens (review antes de publicar) |
| 2.2 | Bolt + Flow | — |
| 2.3 | Bolt | Oath (verificação) |
| 3.1 | Bolt | Apex (review contrato JSON) |
| 3.2 | Bolt + Canvas | Lens |
| 3.3 | Bolt | — |
| 4.1 | Quill | — |
