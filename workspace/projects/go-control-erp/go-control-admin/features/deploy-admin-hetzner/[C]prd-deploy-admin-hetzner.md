# PRD — Deploy go-control-admin no Hetzner Production

**Feature:** `deploy-admin-hetzner`  
**Projeto:** go-control-erp / go-control-admin  
**Data:** 2026-06-22  
**Status:** Aprovado para implementação

---

## Objetivo

Publicar o go-control-admin (Django backend + React frontend) em produção no Docker Swarm Hetzner, acessível via `https://admin.gocontrol.com.br`, com PostgreSQL 18 e Redis 7 próprios na stack.

---

## Escopo

**Inclui:**
- Dockerfiles para backend (Django) e frontend (Vite → Nginx)
- Stack Swarm com 4 serviços: backend, frontend, postgres, redis
- Configuração Traefik + DNS Cloudflare
- Docker Secrets para variáveis sensíveis
- Migrations e superuser inicial

**Não inclui:**
- CI/CD pipeline (follow-up)
- Backup automatizado do Postgres (follow-up)
- Workers Celery adicionais (apenas o worker principal)

---

## Critérios de Aceite

### CA-01 — Imagens buildadas e publicadas
**Given** o código-fonte do backend Django e frontend React  
**When** `docker build` é executado para cada Dockerfile  
**Then** as imagens `gocontrol/admin-backend:latest` e `gocontrol/admin-frontend:latest` estão publicadas no Docker Hub sem erros

### CA-02 — Stack deployada no Swarm
**Given** o arquivo `stack-go-control-admin.yml` e os Docker Secrets criados  
**When** `docker stack deploy -c stack-go-control-admin.yml go-control-admin` é executado  
**Then** todos os 4 serviços (backend, frontend, postgres, redis) estão no estado `Running` com réplicas healthy

### CA-03 — PostgreSQL acessível pelo backend
**Given** a stack deployada com o serviço `postgres` healthy  
**When** o backend Django sobe  
**Then** `manage.py migrate` executa sem erros e as tabelas são criadas no banco `go_control_admin`

### CA-04 — Roteamento e TLS funcionando
**Given** o DNS Cloudflare com A record `admin.gocontrol.com.br → 37.27.202.125`  
**When** o navegador acessa `https://admin.gocontrol.com.br`  
**Then** a resposta é 200 OK com certificado TLS válido emitido via Let's Encrypt

### CA-05 — Frontend servindo a SPA corretamente
**Given** a stack deployada e o DNS configurado  
**When** o usuário acessa `https://admin.gocontrol.com.br`  
**Then** a interface React carrega, chamadas `/api/` chegam ao backend Django e retornam dados reais

### CA-06 — Redis operacional para Celery
**Given** a stack deployada com Redis healthy  
**When** o Celery worker inicia  
**Then** o worker conecta ao Redis e fica em estado `OK` (sem erros de conexão no log)

### CA-07 — Secrets não expostos
**Given** os Docker Secrets criados para POSTGRES_PASSWORD e DJANGO_SECRET_KEY  
**When** `docker service inspect go-control-admin_backend` é executado  
**Then** nenhuma senha ou chave aparece em plain-text nas variáveis de ambiente

---

## Restrições Técnicas

- Placement obrigatório: `node.hostname == ServerServices`
- Versão PostgreSQL: 18-alpine
- Versão Redis: 7-alpine
- Registry: Docker Hub (`evolutions/`)
- Domínio: `admin.gocontrol.com.br` (Cloudflare DNS)
- Traefik entrypoint: `websecure` (HTTPS), TLS resolver `letsencrypt`
