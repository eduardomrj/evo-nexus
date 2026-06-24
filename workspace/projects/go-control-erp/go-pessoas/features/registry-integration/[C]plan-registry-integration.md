# Plan — go-pessoas-ui: GoControlRegistry Integration

**Feature:** `registry-integration`
**Projeto:** go-control-erp / go-pessoas
**Data:** 2026-06-20
**Status:** ready-to-implement

---

## Contexto

A arquitetura do GO Control define que apps externos (go-cobrança, go-message, etc.) descobrem a
URL do go-pessoas via `GoControlRegistry`:

```
main.tsx
  └─ GoControlRegistry.load(['go-pessoas'], { adminUrl, env })
       └─ GET {adminUrl}/platform/apps/go-pessoas/urls/?env={env}
            └─ plataforma retorna { api_url: 'http://localhost:8004/api/v1', ttl_seconds: 3600 }
                 └─ salvo em localStorage com TTL

go-pessoas-ui/api.ts
  └─ pessoasClient = createApiClient({ baseURL: GoControlRegistry.getUrl('go-pessoas') })
       └─ requests diretos ao serviço com auth Bearer
```

O `go-pessoas-ui@0.1.0` foi implementado hardcodando `const P = '/go-pessoas'` e usando o `api`
compartilhado do SDK (baseURL `/api/v1`). Isso:
- Ignora o registry (a chamada ao Admin é feita mas o resultado nunca é consumido)
- Depende do nginx rotear `/api/v1/go-pessoas/` → porta 8004 (frágil)
- Quebra em qualquer ambiente onde o nginx não existe ou a rota muda

## Objetivo

Fazer o `go-pessoas-ui` usar `GoControlRegistry.getUrl('go-pessoas')` como baseURL do seu cliente
axios, respeitando a arquitetura projetada.

## Escopo dos arquivos

| Arquivo | Ação |
|---|---|
| `go-pessoas/frontend/packages/pessoas/src/api.ts` | Trocar `api` por `pessoasClient`, remover prefixo `/go-pessoas` dos paths |
| `go-pessoas/frontend/packages/pessoas/src/config/api.ts` | Mesma troca |
| `go-pessoas/frontend/packages/pessoas/src/client.ts` | **NOVO** — lazy singleton via `createApiClient` |
| `go-cobrança/frontend/apps/go-cobranca/.env.production` | Adicionar `VITE_GO_PESSOAS_API_URL` (fallback nginx) |
| `go-cobrança/frontend/apps/go-cobranca/.env.development` | Mesma adição |

## Padrão do cliente lazy

```ts
// src/client.ts (NOVO)
import { GoControlRegistry, createApiClient } from '@automacao-software/go-control-sdk';
import type { AxiosInstance } from 'axios';

let _client: AxiosInstance | null = null;

export function getPessoasClient(): AxiosInstance {
  if (!_client) {
    _client = createApiClient({
      baseURL: GoControlRegistry.getUrl('go-pessoas'),
      // authUrl omitido: 401 rejeita sem redirect (o app consumer trata)
    });
  }
  return _client;
}
```

## Fallback do GoControlRegistry

`GoControlRegistry.getUrl('go-pessoas')` — cadeia de resolução:
1. Memory cache (resolvido pelo `load()` no bootstrap)
2. localStorage (cache expirado)
3. `VITE_GO_PESSOAS_API_URL` env var → fallback para o path nginx
4. `/api/v1` (último recurso — errado para go-pessoas, mas evita crash)

O env var de fallback em go-cobrança:
```
VITE_GO_PESSOAS_API_URL=/api/v1/go-pessoas   # roteado pelo nginx → porta 8004
```

## Mudança de paths

Antes (api.ts com `P = '/go-pessoas'`):
```ts
api.get(`/go-pessoas/`)           // baseURL /api/v1 → /api/v1/go-pessoas/
api.get(`/go-pessoas/${id}/`)
api.get(`/go-pessoas/${id}/documentos/`)
```

Depois (client.ts com baseURL resolvida):
```ts
pessoasClient.get('/')            // baseURL http://localhost:8004/api/v1 → diretamente no serviço
pessoasClient.get(`/${id}/`)
pessoasClient.get(`/${id}/documentos/`)
```

## Dependências

- `go-pessoas-ui` deve ter `@automacao-software/go-control-sdk` como peerDependency (já tem)
- `GoControlRegistry.getUrl()` deve ser chamado após `load()` completar — o lazy singleton
  garante isso (primeira chamada de API acontece após render, o load é feito no bootstrap)

## Tasks

Ver `[C]tasks-registry-integration.md`.
