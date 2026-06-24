# ADR-DEPLOY-001 — Deploy go-control-admin no Hetzner Production (Docker Swarm)

**Status:** Proposta  
**Data:** 2026-06-22  
**Autor:** Eduardo Martins

---

## Contexto

O go-control-admin (backend Django + frontend React/Vite) roda atualmente em desenvolvimento local via systemd + Nginx no LXC 250. O objetivo é publicar o app em produção no Swarm Hetzner (`ServerServices`), seguindo o padrão já estabelecido pelo Documenso.

Infraestrutura disponível no Swarm Hetzner:
- Traefik já operacional com TLS via Let's Encrypt
- DNS Cloudflare apontando para `37.27.202.125`
- Padrão de placement: `node.hostname == ServerServices`

Infraestrutura ausente (precisa ser criada):
- PostgreSQL (existente via Tailscale é dedicado ao Documenso)
- Redis (não existe no cluster Hetzner)

---

## Decisão

Deployar go-control-admin como Docker Swarm stack standalone com:

1. **Stack self-contained**: backend, frontend, postgres:18, redis:7 — sem dependências externas além do Traefik já existente
2. **Build local no servidor**: imagens buildadas diretamente no Hetzner via SSH — sem Docker Hub
3. **PostgreSQL 18 local na stack**: instância dedicada ao go-control-admin, volume persistente
4. **Redis 7 na stack**: broker Celery + cache Django
5. **Secrets via Docker Swarm Secrets**: 4 secrets gerados automaticamente (postgres_password, django_secret_key, jwt_signing_key, fernet_key)
6. **Roteamento via Traefik**: host rule `admin.gocontrol.com.br`, HTTPS via cloudflareresolver

---

## Drivers

- Isolamento: banco dedicado evita conflito com Documenso
- Portabilidade: stack portável para outro nó sem dependências Tailscale
- Segurança: secrets nunca em variáveis de ambiente plain-text
- Consistência: mesmo padrão do Documenso já validado no cluster
- Reversibilidade: `docker stack rm` desfaz tudo sem afetar outros serviços

---

## Alternativas Descartadas

| Alternativa | Motivo de descarte |
|---|---|
| Usar PostgreSQL do LXC 106 via Tailscale | Banco dedicado ao Documenso; acoplamento indesejado e latência extra |
| Deploy direto via SSH + systemd no Hetzner | Não usa o Swarm; perde orchestration, rolling update e secrets |
| Kubernetes | Over-engineering para cluster single-node |

---

## Consequências

**Positivas:**
- Deploy reproduzível via um único `docker stack deploy`
- Rollback simples por versão de imagem
- TLS automático via Traefik
- Isolamento total de dados

**Negativas / Riscos:**
- Volume Postgres sem backup automatizado (mitigar: pg_dump cron ou Swarm config)
- Primeira vez containerizando o Django do go-control-admin (risco de config omissa)
- Celery worker depende do Redis estar healthy antes de iniciar (mitigar: `healthcheck` no Redis)

---

## Follow-ups

- [ ] Definir política de backup do Postgres 18 (pg_dump + rclone/S3)
- [ ] Criar pipeline CI/CD para build automático das imagens no Docker Hub
- [ ] Avaliar migração de outros apps go-control para o mesmo Swarm no futuro
