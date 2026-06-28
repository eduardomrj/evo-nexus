# Tasks — registry-integration

**Feature:** go-pessoas-ui → GoControlRegistry
**Status geral:** T-01→T-08 concluídas — exceto T-07 (verificação browser — Eduardo)

---

## T-01 — Criar `src/client.ts` no go-pessoas-ui

**Status:** [x] concluída — commit `fad214d`
**Arquivo:** `go-pessoas/frontend/packages/pessoas/src/client.ts`
**Tipo:** NOVO

Criar lazy singleton que resolve a baseURL via registry:

```ts
import { GoControlRegistry, createApiClient } from '@automacao-software/go-control-sdk';
import type { AxiosInstance } from 'axios';

let _client: AxiosInstance | null = null;

/**
 * Retorna o cliente axios do go-pessoas com baseURL resolvida pelo GoControlRegistry.
 * Lazy: criado na primeira chamada, após GoControlRegistry.load() completar no bootstrap.
 */
export function getPessoasClient(): AxiosInstance {
  if (!_client) {
    _client = createApiClient({
      baseURL: GoControlRegistry.getUrl('go-pessoas'),
    });
  }
  return _client;
}

/**
 * Invalida o cliente singleton (útil em testes ou após mudança de ambiente).
 */
export function resetPessoasClient(): void {
  _client = null;
}
```

**Critério:** arquivo existe, compila sem erros (`tsc --noEmit`).

---

## T-02 — Atualizar `src/api.ts`

**Status:** [x] concluída — commit `fad214d`
**Arquivo:** `go-pessoas/frontend/packages/pessoas/src/api.ts`
**Tipo:** EDITAR

- Remover `import { api } from '@automacao-software/go-control-sdk'`
- Adicionar `import { getPessoasClient } from './client'`
- Remover `const P = '/go-pessoas'`
- Substituir todas as ocorrências de `api.get(${P}/...` por `getPessoasClient().get('/...`

Mapeamento de paths (todas as funções):

| Antes | Depois |
|---|---|
| `api.get(\`${P}/\`)` | `getPessoasClient().get('/')` |
| `api.get(\`${P}/${id}/\`)` | `getPessoasClient().get(\`/${id}/\`)` |
| `api.post(\`${P}/\`, payload)` | `getPessoasClient().post('/', payload)` |
| `api.patch(\`${P}/${id}/\`, payload)` | `getPessoasClient().patch(\`/${id}/\`, payload)` |
| `api.delete(\`${P}/${id}/\`)` | `getPessoasClient().delete(\`/${id}/\`)` |
| `api.get(\`${P}/search/\`)` | `getPessoasClient().get('/search/')` |
| `api.get(\`${P}/${id}/documentos/\`)` | `getPessoasClient().get(\`/${id}/documentos/\`)` |
| `api.post(\`${P}/${id}/documentos/\`, p)` | `getPessoasClient().post(\`/${id}/documentos/\`, p)` |
| *(contatos, enderecos, papeis, relacionamentos, audit — mesmo padrão)* | |

**Critério:** arquivo compila, nenhuma referência a `const P` ou `api.get('/go-pessoas` restante.

---

## T-03 — Atualizar `src/config/api.ts`

**Status:** [x] concluída — commit `fad214d`
**Arquivo:** `go-pessoas/frontend/packages/pessoas/src/config/api.ts`
**Tipo:** EDITAR

Mesma troca de T-02:
- Remover `import { api }` e `const P = '/go-pessoas'`
- Adicionar `import { getPessoasClient } from '../client'`
- Substituir todos os `api.get(\`${P}/config/...` por `getPessoasClient().get('/config/...`

Funções afetadas: `getConfig`, `updateConfig`, `listTiposContato`, `createTipoContato`,
`deleteTipoContato`, `listTiposDocumento`, `createTipoDocumento`, `deleteTipoDocumento`,
`listTiposEndereco`, `createTipoEndereco`, `deleteTipoEndereco`.

**Critério:** arquivo compila, sem referência a `P`.

---

## T-04 — Adicionar `VITE_GO_PESSOAS_API_URL` nos env files do go-cobrança

**Status:** [x] concluída — commit `c76b775`
**Arquivos:**
- `go-cobranca/frontend/apps/go-cobranca/.env.production`
- `go-cobranca/frontend/apps/go-cobranca/.env.development`
**Tipo:** EDITAR

Adicionar em ambos:
```
VITE_GO_PESSOAS_API_URL=/api/v1/go-pessoas
```

Este valor é o fallback usado pelo `GoControlRegistry._envFallback('go-pessoas')` caso o
Platform Admin não responda. Com baseURL `/api/v1/go-pessoas` e paths `'/'`, `'/${id}/'` etc.,
as requests vão para `/api/v1/go-pessoas/` que o nginx do go-cobrança já roteia para porta 8004.

**Critério:** variável presente nos dois arquivos.

---

## T-05 — Rebuild do go-pessoas-ui

**Status:** [x] concluída
**Diretório:** `go-pessoas/frontend/packages/pessoas/`
**Comando:** `tsc`

**Critério:** `dist/` atualizado sem erros de compilação.

---

## T-06 — Atualizar go-pessoas-ui no go-cobrança e rebuild

**Status:** [x] concluída — commit `c76b775` (build do go-cobrança inclui nova versão do go-pessoas-ui)
**Tipo:** EDITAR + BUILD

O go-cobrança usa `go-pessoas-ui` via workspace pnpm. Verificar se o link está apontando para
a versão local (workspace) ou para um snapshot no registry.

```bash
# Verificar fonte do pacote
cat go-cobranca/frontend/node_modules/@automacao-software/go-pessoas-ui/dist/api.js | head -5
```

Se for workspace link → o rebuild do T-05 já é suficiente (pnpm resolve na hora).
Se for snapshot → `pnpm update @automacao-software/go-pessoas-ui` no go-cobrança.

Depois rebuild do go-cobrança:
```bash
cd go-cobranca/frontend/apps/go-cobranca && pnpm build
```

**Critério:** build do go-cobrança sem erros; `dist/assets/index-*.js` não contém `/go-pessoas` como path hardcoded de API.

---

## T-07 — Verificação funcional

**Status:** [ ] pendente — Eduardo verifica no browser

1. Acessar `https://go-cobranca.myworkhome.com.br` e fazer login
2. No Network tab, confirmar que após o login o bootstrap chama:
   `GET https://auth.myworkhome.com.br/api/v1/platform/apps/go-pessoas/urls/?env=prod`
   e recebe `{ api_url: '...' }` com status 200
3. Navegar para a página que usa go-pessoas (ex: seleção de pagador em novo contrato)
4. Confirmar que os requests de API vão para a URL retornada pelo Admin (ex: `http://localhost:8004/api/v1/...`)
   e NÃO para `/api/v1/go-pessoas/...`

**Critério:** requests de pessoas batem direto no serviço (sem passar pelo nginx path trick).

---

## T-08 — Commits

**Status:** [x] concluída — `fad214d` (go-pessoas) · `c76b775` (go-cobrança)

Dois commits atômicos:

```
feat(go-pessoas-ui): usar GoControlRegistry para resolução de URL do serviço

Substitui o path hardcoded /go-pessoas + api singleton compartilhado por
lazy createApiClient com baseURL resolvida pelo GoControlRegistry. Adiciona
resetPessoasClient() para testes.
```

```
feat(go-cobranca): VITE_GO_PESSOAS_API_URL como fallback do registry

Adiciona variável nos env files de dev e prod — usada pelo GoControlRegistry
quando o Platform Admin não responde.
```

---

## Dependências entre tasks

```
T-01 → T-02 → T-05 → T-06 → T-07
T-01 → T-03 → T-05
T-04 ──────────────→ T-06
                      T-07 → T-08
```
