# TASKS — Deploy go-control-admin no Hetzner Production

**Feature:** `deploy-admin-hetzner`  
**Data:** 2026-06-22

---

## Grafo de dependências

```
T1 ──┐
T2 ──┼── T3 ── T5 ── T6 ── T7
T4 ──┘
```

---

## Tasks

### T1 — Dockerfile backend (Django)
**Agente:** @bolt-executor  
**Deps:** —  
**Critério:** `docker build -t go-control-admin-backend .` conclui sem erro; imagem roda `python manage.py check` sem erro

**Escopo:**
- Multi-stage `python:3.12-slim`
- Instala `requirements.txt`
- `collectstatic` no build
- Entrypoint: `gunicorn go_control_admin.wsgi:application --bind 0.0.0.0:8000`
- Expõe porta 8000

---

### T2 — Dockerfile frontend (React/Nginx)
**Agente:** @bolt-executor  
**Deps:** —  
**Critério:** `docker build -t go-control-admin-frontend .` conclui; `curl localhost:80` retorna HTML da SPA

**Escopo:**
- Stage build: `node:20-alpine`, `npm ci && npm run build`
- Stage final: `nginx:alpine`, copia `/dist`
- `nginx.conf`: SPA fallback + proxy `/api/` → `http://backend:8000`

---

### T3 — Build das imagens no Hetzner
**Agente:** @custom-sysops  
**Deps:** T1, T2  
**Critério:** `docker images | grep gocontrol` mostra `admin-backend:latest` e `admin-frontend:latest` no servidor 37.27.202.125

**Escopo:**
- SSH no Hetzner (37.27.202.125)
- Sync/clone do código go-control-admin para `/opt/go-control-admin/`
- `docker build -t gocontrol/admin-backend:latest backend/`
- `docker build -t gocontrol/admin-frontend:latest -f frontend/Dockerfile /opt/go-control/`
- Sem Docker Hub — imagens locais no servidor

---

### T4 — DNS Cloudflare + Docker Secrets (4 secrets)
**Agente:** @custom-sysops  
**Deps:** —  
**Critério:** `dig admin.gocontrol.com.br` retorna `37.27.202.125`; `docker secret ls` lista 4 secrets go_control_*

**Escopo (DNS):**
- A record `admin.gocontrol.com.br → 37.27.202.125`
- Proxy Cloudflare: OFF (para cloudflareresolver do Traefik)

**Escopo (Secrets — gerados automaticamente):**
```bash
openssl rand -base64 32 | docker secret create go_control_postgres_password -
python3 -c "import secrets; print(secrets.token_urlsafe(50))" | docker secret create go_control_django_secret_key -
openssl rand -base64 48 | docker secret create go_control_jwt_signing_key -
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" | docker secret create go_control_fernet_key -
```

---

### T5 — Stack Swarm `stack-go-control-admin.yml`
**Agente:** @bolt-executor  
**Deps:** T3, T4  
**Critério:** `docker-compose -f stack-go-control-admin.yml config` valida sem erros

**Escopo:**
- 6 serviços: `postgres`, `redis`, `backend`, `celery`, `celery-beat`, `frontend`
- Placement `node.hostname == ServerServices` em todos
- Healthchecks em postgres e redis
- Secrets montados no backend e celery
- Labels Traefik no frontend: host `admin.gocontrol.com.br`, TLS letsencrypt
- Volumes nomeados: `go_control_postgres_data`, `go_control_redis_data`

---

### T6 — Deploy + Migrations
**Agente:** @bolt-executor  
**Deps:** T5  
**Critério:** `docker service ls` mostra todos os serviços em `Running`; migrations concluem sem erro; superuser criado

**Escopo:**
```bash
docker stack deploy -c stack-go-control-admin.yml go-control-admin
# aguardar serviços healthy
docker exec $(docker ps -q -f name=go-control-admin_backend) \
  python manage.py migrate
docker exec $(docker ps -q -f name=go-control-admin_backend) \
  python manage.py createsuperuser --noinput \
  --username admin --email admin@gocontrol.com.br
```

---

### T7 — Smoke Test & Verificação final
**Agente:** @oath-verifier  
**Deps:** T6  
**Critério:** todos os 7 CAs do PRD verificados com evidência real

**Checklist:**
- [ ] CA-01: imagens no Docker Hub confirmadas
- [ ] CA-02: `docker service ls` — 6/6 Running
- [ ] CA-03: migrations OK, tabelas existem no banco
- [ ] CA-04: `curl -I https://admin.gocontrol.com.br` → 200, TLS válido
- [ ] CA-05: SPA carrega, chamada `/api/` retorna dados
- [ ] CA-06: logs Celery sem erros Redis
- [ ] CA-07: `docker service inspect` — sem senha em plain-text

**Output:** `[C]verification-deploy-admin-hetzner.md`
