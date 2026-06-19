---
title: "PRD — Arquitetura de Reutilização de UI na Plataforma GO Control"
date: 2026-06-18
author: Oracle + Eduardo (sessão de arquitetura)
status: approved
version: "1.0"
feature_slug: platform-ui-architecture
---

# PRD — Arquitetura de Reutilização de UI na Plataforma GO Control

## Contexto e motivação

O GO Control ERP é uma plataforma composta por apps independentes (go-pessoas, go-cobranca,
go-payment-hub, go-message, go-produtos, go-control-admin). Cada app tem backend Django REST
e frontend React+Vite próprios.

O problema atual: componentes de UI de um módulo (ex: seletor de pessoa no go-cobranca)
precisam ser reutilizados em outros apps, mas não há mecanismo funcional para isso.
A tentativa anterior (`@go-control/pessoas`) falhou por ausência de build step e path aliases
presos ao workspace de origem. O go-cobranca reimplementou do zero a listagem de pagadores —
duplicação que se repetirá a cada novo módulo que precisar de UI de outro.

Três decisões arquiteturais foram tomadas em sessão de 2026-06-18 para resolver isso de forma
sustentável.

---

## Decisão 1 — Feature-libs npm compiladas por módulo

### O que é

Uma lib npm compilada por módulo de domínio, publicada no GitHub Packages (mesmo registry
do `@automacao-software/go-control-sdk`), seguindo exatamente o mesmo pipeline de build e
publicação já validado pelo SDK.

### Nomenclatura

```
@automacao-software/go-pessoas-ui
@automacao-software/go-produtos-ui
@automacao-software/go-message-ui
...
```

Uma lib por módulo — versionamento independente. Não existe lib guarda-chuva.

### Estrutura de cada lib

```
packages/{modulo}/
  src/
    api.ts          ← client de API do módulo (usa URL do registry — ver Decisão 3)
    hooks.ts        ← hooks de dados (usePessoas, usePessoa, etc.)
    types.ts        ← tipos TypeScript exportados
    utils/          ← utilitários do domínio
    components/
      {Modulo}Picker.tsx      ← picker para usar em forms de outros apps
      {Modulo}Form.tsx        ← form de cadastro rápido (sidebar)
      {Modulo}ListPage.tsx    ← página completa (recebe onNavigate por prop)
  dist/             ← build tsc (gerado, não commitado)
  package.json      ← main: dist/index.js, types: dist/index.d.ts
```

### Contratos de design

- **Build:** `tsc → dist/`. Nunca TypeScript cru como `main`.
- **Sem path aliases externos:** todos os imports internos à lib são relativos. Nenhum
  `@go-pessoas/*` ou similar.
- **peerDependencies obrigatórias:** `react`, `react-dom`, `react-router-dom`, `primereact`,
  `@tanstack/react-query` — idênticas ao SDK. Nunca duplicar instâncias.
- **Camada UI:** componentes prontos (`Picker`, `Form`, `ListPage`).
- **Camada headless:** hooks + api + types exportados separadamente para quem quiser UI própria.
- **Navegação:** componentes-page recebem `onNavigate: (path: string) => void` por prop.
  Nunca `useNavigate()` interno — rotas do módulo não existem no app hospedeiro.
- **Auth:** não resolvida pela lib. O SDK já inicializa o singleton `api` com Bearer token
  no app hospedeiro. A lib herda esse contexto.
- **URL de API:** configurada via Service Registry (Decisão 3). Fallback para
  `import.meta.env.VITE_{MODULO}_API_URL ?? '/api/v1'`.

### Primeiro módulo a implementar

`@automacao-software/go-pessoas-ui` — extraído de
`go-pessoas/frontend/packages/pessoas/` com as correções necessárias.
go-cobranca remove reimplementação local e passa a consumir a lib.

### Critérios de aceitação

- [ ] `@automacao-software/go-pessoas-ui` publicado no GitHub Packages com `dist/` gerado
- [ ] `PessoaPicker`, `PessoaForm` e `PessoasListPage` exportados e tipados
- [ ] go-cobranca consome a lib e remove `features/pagadores/` reimplementada
- [ ] PagadoresPage no go-cobranca usa `PessoasListPage` com `onNavigate` configurado
- [ ] `peerDependencies` idênticas ao SDK — sem instâncias duplicadas de React/PrimeReact
- [ ] TypeCheck sem erros nos dois repos após a migração
- [ ] Padrão documentado para replicar em go-produtos-ui e futuros módulos

---

## Decisão 2 — Manifest endpoint por módulo

### O que é

Cada app backend expõe `GET /manifest` que retorna sua estrutura de menus e telas em formato
padronizado. O admin usa esse endpoint para sincronizar automaticamente o catálogo de
módulos e telas — eliminando cadastro manual e garantindo que o admin sempre reflita
a estrutura real de cada app.

### Motivação

Hoje o admin tem módulos e telas cadastrados manualmente (`PlanoModulo`, tipo='modulo'|'tela').
Quando um app adiciona uma tela nova, alguém precisa cadastrar manualmente no admin.
Com o manifest, o app é a **fonte da verdade** da sua própria estrutura.

### Contrato do manifest (formato)

```json
GET /api/v1/manifest

{
  "app": "go-pessoas",
  "version": "1.3.0",
  "label": "GO Pessoas",
  "menus": [
    {
      "code": "pessoas",
      "label": "Pessoas",
      "icon": "pi pi-users",
      "order": 1,
      "telas": [
        {
          "code": "pessoas.lista",
          "label": "Lista de Pessoas",
          "route": "/pessoas",
          "publico": false
        },
        {
          "code": "pessoas.detalhe",
          "label": "Detalhe de Pessoa",
          "route": "/pessoas/:id",
          "publico": false,
          "pai": "pessoas.lista"
        },
        {
          "code": "pessoas.config",
          "label": "Configurações",
          "route": "/config",
          "publico": false
        }
      ]
    }
  ]
}
```

### Fluxo de sincronização

1. Desenvolvedor atualiza estrutura de menus/telas no app
2. No admin, acessa o cadastro do módulo e clica **"Sincronizar módulo"**
3. Admin chama `GET {app_url}/api/v1/manifest`
4. Admin faz upsert dos menus e telas (não deleta — marca como `ativo=False` o que sumiu)
5. Estrutura atualizada alimenta automaticamente Planos e Licenças

### Critérios de aceitação

- [ ] Endpoint `GET /api/v1/manifest` implementado em cada app (go-pessoas primeiro)
- [ ] Contrato JSON padronizado e validado (schema compartilhado)
- [ ] Admin: botão "Sincronizar módulo" no cadastro de módulo
- [ ] Admin: lógica de upsert que preserva associações existentes com Planos
- [ ] Telas novas aparecem no catálogo após sincronização; telas removidas marcadas como inativas
- [ ] go-pessoas como implementação de referência

---

## Decisão 3 — Service Registry de URLs no admin

### O que é

O admin centraliza as URLs de cada app por ambiente (dev, staging, prod). Apps consultam
o admin no bootstrap para obter a URL correta dos módulos que vão consumir. A URL é
cacheada localmente para suportar indisponibilidade do admin.

### Motivação

Sem registry centralizado, cada app consumidor precisaria configurar manualmente
`VITE_GO_PESSOAS_API_URL` em cada ambiente — configuração frágil, descentralizada,
propensa a erro. Com o registry, muda no admin e propaga para todos sem redeploy.

### Hierarquia de resolução de URL (ordem de prioridade)

```
1. Admin (runtime) — consulta no bootstrap do app
      GET /api/v1/admin/apps/{slug}/urls?env={env}
      → { api_url: "https://pessoas.myworkhome.com.br/api/v1" }

2. localStorage (cache do último fetch bem-sucedido)
      Chave: go_control_registry_{slug}_{env}
      TTL: configurável por ambiente (default: 1h dev / 24h prod)
      Usado quando admin está indisponível

3. .env / default hardcoded (emergência / primeiro boot sem cache)
      import.meta.env.VITE_{MODULO}_API_URL ?? '/api/v1'
      Garante funcionamento mesmo sem admin e sem cache
```

### Dados mantidos no admin por app

```
App: go-pessoas
  dev:     api_url = http://localhost:8003/api/v1
  staging: api_url = https://staging-pessoas.myworkhome.com.br/api/v1
  prod:    api_url = https://pessoas.myworkhome.com.br/api/v1
```

### Bootstrap do app consumidor

```ts
// Executado uma vez no startup, antes de montar componentes que usam módulos externos
await GoControlRegistry.load(['go-pessoas', 'go-produtos'], { env: 'prod' });

// A partir daí, go-pessoas-ui usa automaticamente a URL correta
import { PessoaPicker } from '@automacao-software/go-pessoas-ui';
```

### Integração com Traefik (produção)

Com Traefik configurado para rotear por path prefix (`/go-pessoas/*` → backend go-pessoas),
o valor de `api_url` pode ser simplesmente `/api/v1` em produção — relativo ao domínio
do gateway. O registry continua válido para ambientes onde cada app tem URL própria.

### Critérios de aceitação

- [ ] Admin: CRUD de apps com URLs por ambiente
- [ ] Admin: endpoint `GET /api/v1/admin/apps/{slug}/urls?env={env}`
- [ ] SDK ou helper `GoControlRegistry.load()` com hierarquia de resolução implementada
- [ ] Cache em localStorage com TTL configurável
- [ ] Fallback para `.env` / default quando admin e cache indisponíveis
- [ ] go-cobranca usa o registry para resolver URL do go-pessoas (não .env hardcoded)
- [ ] Documentado como padrão de infra — Traefik por path como configuração recomendada

---

## Dependências entre decisões

```
Decisão 1 (feature-libs)
  └── depende de Decisão 3 (registry) para resolver URL de API em runtime

Decisão 2 (manifest)
  └── independente — pode ser implementada em paralelo com D1 e D3

Decisão 3 (registry)
  └── pré-requisito para D1 funcionar sem .env manual
  └── usa D2 (manifest) como complemento — manifest sincroniza estrutura, registry sincroniza URLs
```

Ordem recomendada: **D3 → D1 → D2** (registry primeiro garante que as libs já nascem corretas;
manifest pode ser implementado em paralelo).

---

## Must NOT

- Não criar lib guarda-chuva — uma lib por módulo, sempre
- Não exportar TypeScript cru sem build step
- Não usar `useNavigate()` interno em componentes exportados pelas libs
- Não duplicar instâncias de React/PrimeReact (peerDeps obrigatórias)
- Não deletar entradas do admin na sincronização de manifest — marcar como inativo
- Não depender exclusivamente do admin para funcionar (sempre ter fallback)
- Não armazenar secrets no registry (só URLs, não tokens)

---

## Referências

- ADR-004: contrato app ↔ platform admin (manifest push — este PRD especifica o pull)
- `go-control-sdk/typescript/` — pipeline de build a replicar nas feature-libs
- `go-pessoas/frontend/packages/pessoas/` — lib atual a ser corrigida (D1)
- `workspace/projects/go-control-erp/go-control-admin/features/modulos-go-cobranca-go-pessoas/` — módulos no admin
- Sessão de arquitetura: 2026-06-18 (Oracle + Eduardo)
