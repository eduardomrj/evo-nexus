# PRD — Implantação Evo CRM Community na stack `evo-projects`

**Status:** pronto para aprovação  
**Data:** 2026-05-20  
**Ambiente:** Docker Swarm homelab  
**Stack alvo:** `evo-projects`  
**Frontend:** `https://crm.myworkhome.com.br`  
**API/Gateway sugerido:** `https://api-crm.myworkhome.com.br`  
**Versão Evo CRM Community:** `1.0.0-rc2`  
**Repositório:** <https://github.com/evolution-foundation/evo-crm-community>

---

## 1. Objetivo

Implantar corretamente o **Evo CRM Community** no Docker Swarm da homelab, dentro da stack `evo-projects`, com:

- frontend em `crm.myworkhome.com.br`;
- API/gateway em domínio dedicado, sugerido `api-crm.myworkhome.com.br`;
- execução apenas em workers, nunca no manager;
- Postgres existente da homelab;
- Redis interno da stack;
- MinIO existente da homelab;
- migração do serviço funcional `evo-crm_evolution-go` da stack antiga `evo-crm` para a nova stack `evo-projects`.

---

## 2. Contexto atual

### 2.1 Stack antiga

Existe hoje uma stack Swarm chamada:

```text
evo-crm
```

Ela foi considerada criada de forma errada, mas contém um serviço funcional:

```text
evo-crm_evolution-go
```

Esse serviço está correto e em uso na homelab como API WhatsApp.

### 2.2 Serviço funcional atual — `evo-crm_evolution-go`

Inventário real feito pelo SysOps:

```text
Serviço: evo-crm_evolution-go
Estado: 1/1
Nó atual: vm-docker-worker-1
Imagem: evoapicloud/evolution-go:latest
Digest: sha256:0b9b4c562f78633d7c820836e780904be3fd39c85b296b91c0622228bb61c197
Porta interna: 8080
Porta publicada direta: nenhuma
Exposição: Traefik
Domínio atual: evogo.myworkhome.com.br
Volumes/mounts: nenhum
Docker secrets: nenhum
Docker configs: nenhum
```

Labels Traefik atuais:

```text
traefik.enable=true
router: evo-crm
host: evogo.myworkhome.com.br
entrypoint: websecure
tls: true
service: evo-crm
backend port: 8080
network: traefik-homelab
priority: 110
```

Constraints atuais:

```text
node.role == worker
node.hostname == vm-docker-worker-1
```

Ponto de atenção: `vm-docker-worker-1` tem `allow_app=false`, mas o serviço está funcional lá há ~4 semanas. A migração deve preservar comportamento antes de qualquer mudança de nó.

---

## 3. Decisões já aprovadas pelo Eduardo

1. **Stack correta:** `evo-projects`.
2. **Frontend:** `crm.myworkhome.com.br`.
3. **Postgres:** usar servidor Postgres existente na homelab.
4. **Redis:** criar dentro da stack `evo-projects`.
5. **MinIO:** usar MinIO existente na homelab.
6. **Evolution Go:** migrar o serviço funcional atual para dentro da stack `evo-projects`.
7. **Manager:** nenhum workload do CRM deve rodar no manager.

---

## 4. Arquitetura alvo

```text
Stack: evo-projects

Traefik
  ├── crm.myworkhome.com.br
  │     └── evo-projects_evo-crm-frontend
  │
  ├── api-crm.myworkhome.com.br
  │     └── evo-projects_evo-crm-gateway
  │
  └── evogo.myworkhome.com.br
        └── evo-projects_evolution-go

Stack interna
  ├── evo-crm-gateway
  ├── evo-crm-auth
  ├── evo-crm-auth-sidekiq
  ├── evo-crm
  ├── evo-crm-sidekiq
  ├── evo-crm-core
  ├── evo-crm-processor
  ├── evo-crm-bot-runtime
  ├── evo-crm-frontend
  ├── evolution-go
  └── redis

Infra externa reaproveitada
  ├── PostgreSQL homelab: 192.168.88.106:5432
  └── MinIO homelab: 192.168.88.240:9000 / apiminio.myworkhome.com.br
```

---

## 5. Serviços da stack `evo-projects`

### 5.1 `evo-crm-gateway`

**Imagem:**

```text
evoapicloud/evo-crm-gateway:1.0.0-rc2
```

**Função:** gateway Nginx/API de entrada para os serviços internos.

**Domínio sugerido:**

```text
api-crm.myworkhome.com.br
```

**Porta interna oficial:** `3030`.

### 5.2 `evo-crm-auth`

**Imagem:**

```text
evoapicloud/evo-auth-service-community:1.0.0-rc2
```

**Função:** autenticação/autorização.

**Porta interna:** `3001`.

**Dependências:** Postgres homelab, Redis interno, secrets Rails/JWT/Doorkeeper.

### 5.3 `evo-crm-auth-sidekiq`

**Imagem:**

```text
evoapicloud/evo-auth-service-community:1.0.0-rc2
```

**Função:** jobs assíncronos do Auth.

**Healthcheck HTTP:** deve ficar desabilitado, conforme compose Swarm oficial, porque Sidekiq não expõe HTTP.

### 5.4 `evo-crm`

**Imagem:**

```text
evoapicloud/evo-ai-crm-community:1.0.0-rc2
```

**Função:** backend Rails principal do CRM.

**Porta interna:** `3000`.

**Dependências:** Postgres homelab, Redis interno, MinIO via S3-compatible, Auth, Core, Bot Runtime e Processor.

### 5.5 `evo-crm-sidekiq`

**Imagem:**

```text
evoapicloud/evo-ai-crm-community:1.0.0-rc2
```

**Função:** jobs assíncronos do CRM.

**Healthcheck HTTP:** desabilitado.

### 5.6 `evo-crm-core`

**Imagem:**

```text
evoapicloud/evo-ai-core-service-community:1.0.0-rc2
```

**Função:** core service Go da suíte Evo CRM Community.

**Porta interna:** `5555`.

### 5.7 `evo-crm-processor`

**Imagem:**

```text
evoapicloud/evo-ai-processor-community:1.0.0-rc2
```

**Função:** processor Python/FastAPI.

**Porta interna:** `8000`.

**Startup oficial:** roda Alembic + seeders:

```bash
alembic upgrade head && python -m scripts.run_seeders
```

### 5.8 `evo-crm-bot-runtime`

**Imagem:**

```text
evoapicloud/evo-bot-runtime:1.0.0-rc2
```

**Função:** runtime de bots.

**Porta interna:** `8080`.

### 5.9 `evo-crm-frontend`

**Imagem:**

```text
evoapicloud/evo-ai-frontend-community:1.0.0-rc2
```

**Função:** frontend React/Vite/Nginx.

**Domínio aprovado:**

```text
crm.myworkhome.com.br
```

**Porta interna:** `80`.

### 5.10 `evolution-go`

**Imagem atual preservada inicialmente:**

```text
evoapicloud/evolution-go@sha256:0b9b4c562f78633d7c820836e780904be3fd39c85b296b91c0622228bb61c197
```

ou, se preferirmos manter tag:

```text
evoapicloud/evolution-go:latest
```

**Recomendação:** usar digest observado para preservar exatamente o serviço funcional atual durante a migração.

**Função:** API WhatsApp já usada na homelab.

**Domínio atual a preservar inicialmente:**

```text
evogo.myworkhome.com.br
```

**Porta interna:** `8080`.

### 5.11 `redis`

**Imagem sugerida:**

```text
redis:7.4-alpine
```

**Função:** cache/fila interna da stack.

**Exposição pública:** nenhuma.

**Rede:** apenas interna da stack.

**Persistência:** usar volume persistente, mesmo sendo cache, para reduzir perda de jobs em restart.

---

## 6. Infraestrutura existente

### 6.1 PostgreSQL

Servidor identificado:

```text
Host: 192.168.88.106
Hostname: db-postgres-home
Porta: 5432
Serviço: postgresql active
Listener: 0.0.0.0:5432
```

O `evolution-go` atual já usa Postgres nesse host.

DB inferido para Evolution Go:

```text
evogo_users
```

Também existe variável `POSTGRES_AUTH_DB`, mas o valor contém credencial/URL sensível e foi redigido.

### Requisitos para implantação

SysOps deve preparar no Postgres:

```text
DB/usuário para Auth
DB/usuário para CRM
DB/usuário para Processor, se necessário
Permissões mínimas
Backup lógico antes das migrations
```

**Importante:** a senha/DSN atual do `evolution-go` está em env plano. O PRD recomenda rotação e migração para Docker Secret ou arquivo montado seguro.

### 6.2 MinIO

MinIO principal identificado:

```text
Host: 192.168.88.240
API S3 interna: http://192.168.88.240:9000
Console: http://192.168.88.240:9001
```

Traefik:

```text
Console: https://minio.myworkhome.com.br
API S3: https://apiminio.myworkhome.com.br
```

Bucket esperado pelo Evolution Go atual:

```text
evolution-media
```

Estado atual no `evolution-go`:

```text
MINIO_ENABLED=false
MINIO_BUCKET=evolution-media
MINIO_ENDPOINT=
```

### Requisitos para implantação

SysOps deve:

- validar/criar bucket para CRM;
- preferencialmente usar bucket dedicado, exemplo:

```text
evo-crm-community
```

- criar access key dedicada;
- aplicar policy limitada ao bucket;
- não expor access key/secret no stack file;
- usar endpoint LAN para serviços internos, preferencialmente:

```text
http://192.168.88.240:9000
```

---

## 7. Redes

### 7.1 Rede pública Traefik

Rede existente:

```text
traefik-homelab
```

Usada por serviços expostos via Traefik.

### 7.2 Rede interna da nova stack

Criar rede:

```text
evo-projects-internal
```

Uso:

- comunicação entre gateway, auth, CRM, processor, bot-runtime, core, Redis e evolution-go;
- não expor Redis nessa rede pública.

---

## 8. Placement / constraints

Cluster atual:

```text
vm-docker-manager     manager, provider=local
vm-docker-worker-1    worker, provider=local, allow_app=false
vm-docker-worker-2    worker, provider=local, allow_app=true
hetzner-aivoo         worker, provider=hetzner, allow_app=true
```

### Regra obrigatória

Nenhum serviço da stack `evo-projects` deve rodar no manager:

```yaml
placement:
  constraints:
    - node.role == worker
```

### Recomendação para serviços novos do CRM

Usar worker local com `allow_app=true`:

```yaml
placement:
  constraints:
    - node.role == worker
    - node.labels.provider == local
    - node.labels.allow_app == true
```

Isso direciona os novos serviços para:

```text
vm-docker-worker-2
```

### Recomendação específica para `evolution-go`

Como o serviço funcional atual roda em:

```text
vm-docker-worker-1
```

e está operacional há ~4 semanas, a migração deve ser conservadora:

**Fase inicial:**

```yaml
placement:
  constraints:
    - node.role == worker
    - node.hostname == vm-docker-worker-1
```

Depois de validar, pode-se planejar migração futura para `vm-docker-worker-2`.

---

## 9. Domínios e Traefik

### 9.1 Frontend CRM

```text
crm.myworkhome.com.br
→ evo-projects_evo-crm-frontend:80
```

### 9.2 Gateway/API

Sugestão a aprovar:

```text
api-crm.myworkhome.com.br
→ evo-projects_evo-crm-gateway:3030
```

### 9.3 Evolution Go

Preservar inicialmente:

```text
evogo.myworkhome.com.br
→ evo-projects_evolution-go:8080
```

### 9.4 Labels Traefik

Usar nomes únicos para evitar colisão com a stack antiga:

```text
evo-projects-evo-crm-frontend
evo-projects-evo-crm-api
evo-projects-evolution-go
```

Não reutilizar router/service Traefik chamado apenas `evo-crm`.

---

## 10. Secrets obrigatórios

Não devem ser salvos em texto puro no compose.

### 10.1 Secrets do Evo CRM

A criar/preencher:

```text
SECRET_KEY_BASE
JWT_SECRET_KEY
DOORKEEPER_JWT_SECRET_KEY
EVOAI_CRM_API_TOKEN
BOT_RUNTIME_SECRET
ENCRYPTION_KEY
SMTP_PASSWORD
```

### 10.2 Secrets do Postgres

```text
POSTGRES_PASSWORD_AUTH
POSTGRES_PASSWORD_CRM
POSTGRES_PASSWORD_PROCESSOR
POSTGRES_DSN_EVOLUTION_GO
```

### 10.3 Secrets do MinIO

```text
MINIO_ACCESS_KEY_ID_EVO_CRM
MINIO_SECRET_ACCESS_KEY_EVO_CRM
```

### 10.4 Observação de segurança

O serviço atual `evo-crm_evolution-go` tem credenciais sensíveis em env plano. Durante a migração, a recomendação é:

1. preservar funcionamento primeiro;
2. migrar para secret;
3. rotacionar senha depois que o novo serviço estiver validado.

---

## 11. Variáveis principais

### 11.1 URLs públicas

```env
FRONTEND_DOMAIN=crm.myworkhome.com.br
API_DOMAIN=api-crm.myworkhome.com.br

FRONTEND_URL=https://crm.myworkhome.com.br
BACKEND_URL=https://api-crm.myworkhome.com.br
CORS_ORIGINS=https://crm.myworkhome.com.br,https://api-crm.myworkhome.com.br
```

### 11.2 Postgres

```env
POSTGRES_HOST=192.168.88.106
POSTGRES_PORT=5432
POSTGRES_SSLMODE=<confirmar>
POSTGRES_DATABASE=<definir>
POSTGRES_USERNAME=<definir>
POSTGRES_PASSWORD_FILE=/run/secrets/...
```

### 11.3 Redis

```env
REDIS_URL=redis://evo-crm-redis:6379/0
PROCESSOR_REDIS_HOST=evo-crm-redis
PROCESSOR_REDIS_PORT=6379
PROCESSOR_REDIS_DB=0
```

Se Redis tiver senha:

```env
REDIS_URL=redis://:<senha>@evo-crm-redis:6379/0
```

### 11.4 MinIO / S3-compatible

```env
ACTIVE_STORAGE_SERVICE=s3_compatible
STORAGE_BUCKET_NAME=evo-crm-community
STORAGE_REGION=us-east-1
STORAGE_ENDPOINT=http://192.168.88.240:9000
STORAGE_FORCE_PATH_STYLE=true
```

---

## 12. Migrations e seed

A documentação oficial informa:

- Auth roda `bundle exec rails db:migrate`;
- CRM roda `bundle exec rails db:migrate`;
- Processor roda `alembic upgrade head` e `python -m scripts.run_seeders`;
- Auth precisa ser seedado antes do CRM em setup inicial.

### Estratégia recomendada

Não depender cegamente do startup automático para primeiro deploy.

Fazer rollout em etapas:

1. criar DBs/usuários;
2. backup/snapshot;
3. subir Redis;
4. executar migrations Auth;
5. executar seed Auth;
6. executar migrations CRM;
7. executar seed CRM, se aplicável;
8. executar migrations/seeders Processor;
9. subir serviços web/background;
10. liberar Traefik.

---

## 13. Plano de migração do `evolution-go`

### Fase A — Inventário e congelamento

- Capturar spec atual do serviço `evo-crm_evolution-go`.
- Preservar:
  - imagem/digest;
  - envs não sensíveis;
  - secrets/DSNs redigidos;
  - labels Traefik;
  - constraints;
  - update/rollback policy.

### Fase B — Criar serviço equivalente na nova stack

Criar `evo-projects_evolution-go` com:

```text
imagem: digest atual observado
porta interna: 8080
rede: traefik-homelab + evo-projects-internal
constraint inicial: node.hostname == vm-docker-worker-1
domínio: evogo.myworkhome.com.br
```

### Fase C — Corte Traefik

Atualizar router/service Traefik para apontar para o novo serviço, sem mudar o domínio.

### Fase D — Validação

Validar:

- health/endpoint básico;
- autenticação via API key;
- conexão com Postgres;
- fluxo WhatsApp em uso;
- logs sem erro;
- ausência de task no manager.

### Fase E — Remoção da stack antiga

Só depois da validação:

- remover ou escalar para zero `evo-crm_evolution-go`;
- remover stack antiga `evo-crm` se ela não tiver mais nada útil.

---

## 14. Plano de rollout completo

### Etapa 1 — Preparação SysOps

- Criar pasta da stack:

```text
/home/emrj/platforms/docker/stacks/evo-projects/
```

- Criar compose/env seguindo padrão homelab.
- Criar rede interna `evo-projects-internal`.
- Confirmar `traefik-homelab`.
- Confirmar DNS/TLS:
  - `crm.myworkhome.com.br`;
  - `api-crm.myworkhome.com.br`;
  - preservar `evogo.myworkhome.com.br`.

### Etapa 2 — Postgres

- Criar DBs/usuários necessários no `192.168.88.106`.
- Confirmar SSL mode.
- Criar backup antes das migrations.
- Testar conexão a partir do worker alvo.

### Etapa 3 — MinIO

- Criar bucket:

```text
evo-crm-community
```

- Criar credencial dedicada.
- Aplicar policy mínima.
- Testar upload/download a partir do worker alvo.

### Etapa 4 — Redis

- Subir Redis interno.
- Validar DNS interno:

```text
evo-crm-redis:6379
```

### Etapa 5 — Deploy dos serviços Evo CRM

Subir, em ordem controlada:

1. `evo-crm-auth`
2. `evo-crm-auth-sidekiq`
3. `evo-crm`
4. `evo-crm-sidekiq`
5. `evo-crm-core`
6. `evo-crm-processor`
7. `evo-crm-bot-runtime`
8. `evo-crm-gateway`
9. `evo-crm-frontend`

### Etapa 6 — Migrar `evolution-go`

- Criar equivalente em `evo-projects`.
- Redirecionar Traefik.
- Validar.
- Remover stack antiga depois.

---

## 15. Critérios de aceite

### 15.1 Frontend

**Given** a stack `evo-projects` implantada  
**When** acesso `https://crm.myworkhome.com.br`  
**Then** o frontend carrega via HTTPS com certificado válido.

### 15.2 Gateway/API

**Given** o domínio `api-crm.myworkhome.com.br` aprovado  
**When** acesso endpoint de health/API  
**Then** o gateway responde sem 502/503.

### 15.3 Worker-only

**Given** os serviços implantados  
**When** executo `docker service ps`  
**Then** nenhum serviço roda em `vm-docker-manager`.

### 15.4 Postgres externo

**Given** Auth/CRM iniciados  
**When** verifico os serviços  
**Then** não existe Postgres dentro da stack `evo-projects`; todos usam `192.168.88.106:5432`.

### 15.5 Redis interno

**Given** a stack implantada  
**When** verifico serviços  
**Then** existe Redis dentro de `evo-projects` e sem porta publicada externamente.

### 15.6 MinIO

**Given** upload/anexo/ActiveStorage usado  
**When** arquivo é salvo  
**Then** objeto aparece no bucket MinIO dedicado.

### 15.7 Evolution Go migrado

**Given** `evogo.myworkhome.com.br` funcional antes da migração  
**When** o router passa a apontar para `evo-projects_evolution-go`  
**Then** a API continua respondendo e mantendo comportamento esperado.

### 15.8 Stack antiga removível

**Given** todos os serviços novos validados  
**When** nenhum tráfego depende da stack antiga `evo-crm`  
**Then** a stack antiga pode ser removida em operação posterior aprovada.

---

## 16. Rollback

### 16.1 Antes de cortar `evolution-go`

Se a nova stack falhar:

- escalar serviços novos para zero;
- manter `evo-crm_evolution-go` antigo ativo;
- preservar DBs/buckets para análise;
- não remover stack antiga.

### 16.2 Após cortar `evolution-go`

Se o novo `evolution-go` falhar:

- reverter Traefik para o serviço antigo `evo-crm_evolution-go`;
- escalar `evo-projects_evolution-go` para zero;
- analisar logs;
- manter dados intactos.

### 16.3 Migrations

Antes das migrations:

- backup lógico do Postgres;
- registrar versão/tag;
- preservar logs.

Rollback de migration pode exigir restore; não assumir reversibilidade automática.

---

## 17. Riscos e mitigação

| Risco | Impacto | Mitigação |
|---|---:|---|
| Quebrar `evolution-go` funcional | Alto | Migrar preservando digest, envs, constraint e domínio; manter antigo como fallback |
| Secrets atuais em env plano | Alto | Preservar primeiro, depois migrar para Docker Secrets e rotacionar |
| Postgres externo sem backup | Alto | Backup antes de migrations |
| MinIO bucket/policy incorretos | Médio | Criar credencial dedicada e testar upload/download |
| Redis sem persistência | Médio | Usar volume persistente |
| Serviços caírem no manager | Alto | Constraints obrigatórias |
| Conflito Traefik com `evo-crm` antigo | Alto | Usar routers únicos `evo-projects-*` |
| `crm.myworkhome.com.br` sem rota atual | Médio | Criar router dedicado no deploy |
| Tag `1.0.0-rc2` é release candidate | Médio | Rollout gradual e rollback pronto |

---

## 18. Decisões pendentes para aprovação

Para transformar este PRD em plano técnico/deploy, validar estes pontos:

1. **API domain:** aprovar `api-crm.myworkhome.com.br`.
2. **Evolution Go:** preservar `evogo.myworkhome.com.br` durante a migração.
3. **Imagem Evolution Go:** usar digest atual para preservar exatamente o runtime funcional.
4. **Placement do Evolution Go:** manter inicialmente em `vm-docker-worker-1`.
5. **Serviços novos:** colocar em `vm-docker-worker-2` com `allow_app=true`.
6. **Bucket MinIO:** aprovar criar `evo-crm-community`.
7. **Redis:** aprovar Redis com volume persistente.
8. **Postgres:** aprovar criar DBs/usuários dedicados para Auth/CRM/Processor no `192.168.88.106`.
9. **Stack antiga:** manter como fallback até validação final, e só remover depois.

---

## 19. Checklist de aprovação

- [ ] Stack `evo-projects` aprovada.
- [ ] Frontend `crm.myworkhome.com.br` aprovado.
- [ ] API `api-crm.myworkhome.com.br` aprovada.
- [ ] Preservar `evogo.myworkhome.com.br` aprovado.
- [ ] Usar Postgres homelab `192.168.88.106:5432` aprovado.
- [ ] Criar Redis interno com volume aprovado.
- [ ] Usar MinIO homelab `192.168.88.240:9000` aprovado.
- [ ] Criar bucket `evo-crm-community` aprovado.
- [ ] Migrar `evolution-go` para `evo-projects` aprovado.
- [ ] Manter stack antiga `evo-crm` como fallback até validação aprovado.
- [ ] Executar migrations apenas após backup aprovado.
- [ ] Nenhum workload no manager aprovado.

---

## 20. Recomendação final

Aprovar o PRD com estes defaults:

```text
API domain: api-crm.myworkhome.com.br
Frontend: crm.myworkhome.com.br
Evolution Go domain: evogo.myworkhome.com.br preservado
Evolution Go: migrar com digest atual
Evolution Go placement inicial: vm-docker-worker-1
Serviços novos: vm-docker-worker-2
Postgres: 192.168.88.106:5432 com DBs/usuários dedicados
Redis: interno na stack com volume
MinIO: 192.168.88.240:9000 com bucket evo-crm-community
Stack antiga evo-crm: manter como fallback até validação final
```
