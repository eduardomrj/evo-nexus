# Port Registry — GO Control Platform (dev)

Registro canônico de portas para desenvolvimento local.
**Atualizado em:** 2026-06-23

---

## Backend (Django — `runserver PORT`)

| Porta | Serviço | Tipo |
|-------|---------|------|
| **8000** | go-control-admin | core |
| **8001** | go-cobranca | satélite |
| **8002** | go-payment-hub | satélite |
| **8003** | go-message | satélite |
| **8004** | go-pessoas | satélite |
| **8005** | go-control-auth | core |
| **8006** | go-control-account | core |
| **8007** | go-produtos | satélite |
| **8008** | go-lookup | utilitário |

## Frontend (Vite dev server)

| Porta | Serviço |
|-------|---------|
| **5174** | go-control-account |
| **5175** | go-control-admin |
| **5180** | go-message |
| **5181** | go-cobranca |
| **5182** | go-payment-hub |
| **5183** | go-control-auth |
| **5184** | go-pessoas |
| **5185** | go-produtos |

> go-produtos: porta 5185 reservada — frontend ainda não criado.

---

## URLs de API dev (para uso em `.env` e seeds)

| Serviço | `api_url` dev |
|---------|--------------|
| go-control-admin | `http://localhost:8000/api/v1` |
| go-cobranca | `http://localhost:8001/api/v1` |
| go-payment-hub | `http://localhost:8002/api/v1` |
| go-message | `http://localhost:8003/api/v1` |
| go-pessoas | `http://localhost:8004/api/v1` |
| go-control-auth | `http://localhost:8005/api/v1` |
| go-control-account | `http://localhost:8006/api/v1` |
| go-produtos | `http://localhost:8007/api/v1` |
| go-lookup | `http://localhost:8008/api/v1` |

---

## Variáveis de ambiente (core → satélites)

Cada app satélite configura o admin via env var — não via `ModuloEnvironmentUrl`:

```env
GO_CONTROL_ADMIN_URL=http://localhost:8000
AUTH_URL=http://localhost:8005
```

`ModuloEnvironmentUrl` é para resolução de URL entre satélites (via `ModuloUrlResolver`).
Admin, auth e account são configurados via env var diretamente em cada app.

---

## Como subir todos os backends em dev

```bash
# Cada serviço no próprio terminal (ou tmux)
cd go-control-admin  && make backend   # :8000
cd go-cobranca       && make backend   # :8001
cd go-payment-hub    && make backend   # :8002
cd go-message        && make backend   # :8003
cd go-pessoas        && make backend   # :8004
cd go-control-auth   && make backend   # :8005
cd go-control-account && make backend  # :8006
cd go-produtos        && make backend  # :8007
cd go-lookup          && make backend  # :8008
```

> Os Makefiles já usam `runserver PORT` explícito — sem conflito de porta.
