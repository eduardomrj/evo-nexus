# TASKS — Deploy go-control-admin no Hetzner Production

**Feature:** `deploy-admin-hetzner`  
**Data:** 2026-06-22  
**Status:** ✅ CONCLUÍDA (2026-06-28)

---

## Grafo de dependências

```
T1 ──┐
T2 ──┼── T3 ── T5 ── T6 ── T7
T4 ──┘
```

---

## Tasks

### T1 — Dockerfile backend (Django) ✅
Existia. Ajustado: adicionado `git` ao builder (necessário para pip instalar `go-control-platform-core` via git+https).
Commit: `c04c43f`

### T2 — Dockerfile frontend (React/Nginx) ✅
Existia (reescrito em m3b-sdk-migration). Ajustado: token GitHub Packages escrito no `~/.npmrc` do builder antes do `pnpm install`.
Commit: `c04c43f`

### T3 — Build das imagens no Hetzner ✅
`gocontrol/admin-backend:latest` (270MB) e `gocontrol/admin-frontend:latest` (65.3MB) buildadas em 37.27.202.125.

### T4 — DNS Cloudflare + Docker Secrets ✅
DNS `admin.gocontrol.com.br → 37.27.202.125` e 4 secrets já existiam de sessão anterior.

### T5 — Stack Swarm ✅
`go-control-admin/infra/swarm/stack-go-control-admin.yml` existia e validou sem erros.

### T6 — Deploy + Migrations ✅
`docker stack deploy` concluído. 6/6 serviços Running 1/1. 1 migration aplicada (`platform.0066`).

### T7 — Smoke Test & Verificação final ✅

- [x] CA-01: imagens no servidor confirmadas
- [x] CA-02: `docker service ls` — 6/6 Running 1/1
- [x] CA-03: migrations OK (`migrate --check` exit 0)
- [x] CA-04: `curl -I https://admin.gocontrol.com.br` → HTTP/2 200, TLS válido
- [x] CA-05: SPA carrega (`<title>GO Control — Platform Admin</title>`), API proxiada corretamente
- [x] CA-06: Redis operacional, Celery sem erros críticos
- [x] CA-07: secrets via `/run/secrets/` — nenhum valor sensível em plain-text

**Output:** `[C]verification-deploy-admin-hetzner.md`

---

### Fixes aplicados durante o deploy

| Fix | Commit | Motivo |
|---|---|---|
| `backend/Dockerfile`: adicionar `git` | `c04c43f` | pip install de repo privado via git+https |
| `frontend/Dockerfile`: token no `~/.npmrc` do builder | `c04c43f` | pnpm não expande vars em `.npmrc` de projeto |
| `backend/config/settings/prod.py`: `SECURE_PROXY_SSL_HEADER` | `29ca4fe` | loop 301 — Traefik termina TLS, Django não reconhecia como HTTPS |
| `frontend/nginx.conf`: `proxy_pass` direto (sem resolver lazy) | `aef6daa` | 404 na rede traefikNetwork com `set $upstream` |
