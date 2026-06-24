# PLAN — Deploy go-control-admin no Hetzner Production

**Feature:** `deploy-admin-hetzner`  
**Agente executor:** @bolt-executor  
**Data:** 2026-06-22 (atualizado 2026-06-23)  
**ADR:** `[C]architecture-deploy-admin-hetzner.md`  
**PRD:** `[C]prd-deploy-admin-hetzner.md`

---

## Step 1 — Dockerfiles

**Responsável:** Bolt  
**Output:** `go-control-admin/backend/Dockerfile` + `go-control-admin/frontend/Dockerfile`

### Backend (Django)
- Multi-stage build: `python:3.12-slim` como base
- Stage build: instala dependências com `pip install -r requirements/base.txt`
- Stage final: copia app, collectstatic, expõe porta 8000
- Entrypoint: `gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 2`

### Frontend (React/Vite)
- Stage build: `node:22-alpine`, `pnpm install --frozen-lockfile=false && pnpm run build`
- Build context: `go-control/` (raiz do monorepo, necessário pelo SDK local)
- Stage final: `nginx:alpine`, copia `/dist` para `/usr/share/nginx/html`
- Nginx config: serve SPA (`try_files $uri /index.html`), proxy `/api/` → `backend:8000`

**Exit criterion:** `docker build` bem-sucedido para ambas as imagens

---

## Step 2 — Build das imagens no Hetzner

**Responsável:** SysOps (via SSH)  
**Output:** Imagens `gocontrol/admin-backend:latest` e `gocontrol/admin-frontend:latest` disponíveis localmente no servidor

```bash
# No servidor 37.27.202.125
mkdir -p /opt/go-control-admin
cd /opt/go-control-admin
# sync/clone do código go-control-admin

# Build backend
docker build -t gocontrol/admin-backend:latest backend/

# Build frontend (contexto = raiz go-control/ por causa do SDK local)
docker build -t gocontrol/admin-frontend:latest -f frontend/Dockerfile /opt/go-control/
```

**Exit criterion:** `docker images | grep gocontrol` mostra ambas as imagens

---

## Step 3 — Stack Swarm (`stack-go-control-admin.yml`)

**Responsável:** Bolt  
**Output:** `/infra/swarm/stack-go-control-admin.yml` ✅ Entregue

Serviços:
```
postgres    → postgres:18-alpine, volume go_control_postgres_data
redis       → redis:7-alpine, volume go_control_redis_data
backend     → gocontrol/admin-backend:latest
              secrets: django_secret_key, postgres_password, jwt_key, fernet_key
celery      → mesma imagem do backend, cmd: celery worker
celery-beat → mesma imagem do backend, cmd: celery beat
frontend    → gocontrol/admin-frontend:latest
              Traefik labels: host=admin.gocontrol.com.br, TLS cloudflareresolver
```

**Exit criterion:** arquivo validado com `docker compose config` ✅

---

## Step 4 — DNS Cloudflare + Docker Secrets

**Responsável:** SysOps  
**Output:** A record criado + 4 secrets configurados no Swarm

### DNS
- A record: `admin.gocontrol.com.br → 37.27.202.125`
- Proxy Cloudflare: OFF (para emissão do certificado via cloudflareresolver)

### Docker Secrets (4 secrets — executar no Hetzner)
```bash
openssl rand -base64 32 | docker secret create go_control_postgres_password -
python3 -c "import secrets; print(secrets.token_urlsafe(50))" | docker secret create go_control_django_secret_key -
openssl rand -base64 48 | docker secret create go_control_jwt_signing_key -
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" | docker secret create go_control_fernet_key -
```

**Exit criterion:** `docker secret ls` mostra 4 secrets; DNS propagado (`dig admin.gocontrol.com.br`)

---

## Step 5 — Deploy, Migrations e Smoke Test

**Responsável:** SysOps  
**Output:** Stack running + CAs verificados

```bash
docker stack deploy -c stack-go-control-admin.yml go-control-admin

# aguardar serviços healthy (~60s)
docker service ls

# Migrations
docker exec $(docker ps -q -f name=go-control-admin_backend) \
  python manage.py migrate

# Superuser inicial
docker exec -it $(docker ps -q -f name=go-control-admin_backend) \
  python manage.py createsuperuser
```

Smoke test:
- `docker service ls` → 6/6 Running
- `curl -I https://admin.gocontrol.com.br` → 200 OK com TLS
- Login na interface admin → autenticação funcional
- `docker service logs go-control-admin_celery` → sem erros Redis

**Exit criterion:** todos os critérios de aceite do PRD verificados

---

## Decisões fechadas

- **Build local no servidor:** sem Docker Hub — imagens buildadas diretamente no Hetzner via SSH
- **PLATFORM_REGISTER_TOKEN / PLATFORM_SERVICE_TOKEN:** opcionais, omitidos (código falha silenciosamente sem eles)
- **Celery beat:** incluído na stack (2 serviços Celery: worker + beat)
- **4 secrets apenas:** django_secret_key, postgres_password, jwt_signing_key, fernet_key
