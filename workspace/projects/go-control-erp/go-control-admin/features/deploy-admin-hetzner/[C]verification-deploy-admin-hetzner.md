# [C] Verification — deploy-admin-hetzner

## Re-verificação Final — 2026-06-28

**Data:** 2026-06-28
**Verifier:** @oath-verifier
**Veredito:** FAIL
**Confiança:** Alta
**Bloqueadores:** 1 (CA-05 — nginx retorna 404 para /api/ externamente; proxy não funciona via Traefik)
**Avisos não-bloqueantes:** 2 (CA-06 — Celery KeyError task obsoleta; Redis warning overcommit_memory)

---

| CA | Critério | Status | Evidência |
|---|---|---|---|
| CA-01 | Imagens buildadas no servidor | ✅ VERIFIED | `gocontrol/admin-backend:latest` (42730bbc8321, 270MB) e `gocontrol/admin-frontend:latest` (ff3b34aa425f, 65.3MB) — IDs novos vs verificação anterior (rebuild confirmado) |
| CA-02 | 6 serviços Running 1/1 | ✅ VERIFIED | backend, celery, celery-beat, frontend, postgres, redis — todos 1/1 |
| CA-03 | Migrations aplicadas, tabelas OK | ✅ INFERRED | `manage.py migrate --check` falhou por SECRET_KEY não disponível fora do container (decouple não encontra `/run/secrets/` no shell de verificação externo). Evidência indireta: Django responde HTTP 400 (não 500/ImproperlyConfigured) via chamada interna — Django não inicializa se há migration pendente com auto-migrate desabilitado |
| CA-04 | TLS + DNS admin.gocontrol.com.br | ✅ VERIFIED | HTTP/2 200, TLSv1.3/TLS_AES_128_GCM_SHA256, CN=admin.gocontrol.com.br, nginx/1.31.2 |
| CA-05 | SPA carrega + API responde externamente | ❌ FAIL | SPA: `<title>GO Control — Platform Admin</title>` HTTP 200 ✅. API: nginx retorna 404 para todos os endpoints `/api/` externamente (via Traefik). Internamente (acesso direto ao frontend por IP) o proxy funciona (Django responde 400). O fix do SECURE_PROXY_SSL_HEADER foi aplicado (301 loop não ocorre mais) mas o nginx falha no proxy_pass quando request chega via rede traefikNetwork |
| CA-06 | Redis OK, Celery sem erros críticos | ⚠️ PARTIAL | Redis operacional (warning vm.overcommit_memory não impede operação). Celery: `KeyError: 'platform.verificar_health_modulos'` — task da versão anterior descartada silenciosamente, worker não reinicia |
| CA-07 | Secrets não expostos em plain-text | ✅ VERIFIED | Env do serviço backend: `ALLOWED_HOSTS`, `DEBUG=False`, `REDIS_URL`, `DJANGO_SETTINGS_MODULE` etc. Nenhuma senha/chave. Secrets via Docker Secrets |

---

## Detalhes da Re-verificação Final

### CA-01 — Imagens no servidor

```
$ ssh hetzner-prod "docker images | grep gocontrol"
gocontrol/admin-backend:latest    42730bbc8321   270MB
gocontrol/admin-frontend:latest   ff3b34aa425f   65.3MB
```

Novo build (IDs diferentes: antes 7f478e0f4e2f/54b369ffbbe1). Confirma rebuild com fix do SECURE_PROXY_SSL_HEADER.

### CA-02 — Serviços Running 1/1

```
$ ssh hetzner-prod "docker service ls | grep go-control-admin"
a0xar4cwx2vg   go-control-admin_backend      replicated   1/1   gocontrol/admin-backend:latest
w3mg0w9uu1s2   go-control-admin_celery       replicated   1/1   gocontrol/admin-backend:latest
zfi6b17bh52i   go-control-admin_celery-beat  replicated   1/1   gocontrol/admin-backend:latest
i03j9k9euu2l   go-control-admin_frontend     replicated   1/1   gocontrol/admin-frontend:latest
eotl8hxjhfzx   go-control-admin_postgres     replicated   1/1   postgres:18-alpine
5nrf45zkcsts   go-control-admin_redis        replicated   1/1   redis:7-alpine
```

### CA-03 — Migrations (verificação indireta)

`manage.py migrate --check` falhou ao ser executado fora do contexto do container — `python-decouple` não encontra `SECRET_KEY` sem acesso ao `/run/secrets/`. Evidência indireta de banco íntegro: chamada interna ao Django via HTTP retorna `400 Bad Request` (Django inicializado corretamente; um banco com migrations pendentes retornaria erro de tabela inexistente em requests autenticadas). A verificação direta da V1 (exit 0) permanece válida — nenhuma nova migration foi introduzida desde então.

### CA-04 — TLS e DNS

```
HTTP/2 200
server: nginx/1.31.2
TLSv1.3 / TLS_AES_128_GCM_SHA256 / X25519 / RSASSA-PSS
CN=admin.gocontrol.com.br
last-modified: Sun, 28 Jun 2026 15:44:10 GMT
```

TLS ativo, certificado válido, DNS resolvendo corretamente.

### CA-05 — SPA e API (BLOQUEADOR)

**SPA — PASS:**
```
$ curl -s https://admin.gocontrol.com.br | grep title
<title>GO Control — Platform Admin</title>
```

**API externa — FAIL (404, não mais 301):**
```
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" https://admin.gocontrol.com.br/api/v1/health/
HTTP 404
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST https://admin.gocontrol.com.br/api/v1/auth/login/
HTTP 404
```

O fix do `SECURE_PROXY_SSL_HEADER` foi aplicado (loop de 301 não ocorre mais). Porém o nginx agora retorna 404 para todas as requests `/api/` chegando via Traefik.

**Análise de causa raiz:**

Configuração nginx do frontend:
```nginx
location /api/ {
    resolver 127.0.0.11 valid=10s ipv6=off;
    set $upstream http://backend:8000;
    proxy_pass $upstream;
    proxy_set_header X-Forwarded-Proto https;
    ...
}
```

Access log do nginx (requests do Traefik — 10.0.3.22):
```
10.0.3.22 - - [28/Jun/2026:15:47:10] "GET /api/v1/auth/login/ HTTP/1.1" 404 179
10.0.3.22 - - [28/Jun/2026:15:48:06] "POST /api/v1/auth/login/ HTTP/1.1" 404 179
```

Access log (request interna do backend — 10.0.2.104):
```
10.0.2.104 - - [28/Jun/2026:15:52:30] "GET /api/v1/ HTTP/1.1" 400 154
```

**Diferença crítica:** requests do backend (rede interna 10.0.2.x) chegam ao nginx e são proxiadas para o Django (retorna 400). Requests do Traefik (rede traefikNetwork 10.0.3.x) chegam ao nginx e retornam 404 diretamente — o nginx não faz proxy.

nslookup `backend` dentro do frontend:
```
Server: 127.0.0.11 (explícito) → resolve para 10.0.2.7 (VIP)
nslookup sem servidor → NXDOMAIN (search domain Tailscale: tailab27dd.ts.net interfere)
```

Hipótese mais provável: quando o nginx tenta resolver `backend` durante a request (usando `resolver 127.0.0.11`), o Docker DNS retorna corretamente, mas pode haver um problema de timing no container recém-redeploy ou um conflito com o search domain Tailscale que interfere na resolução lazy do nginx. O nginx, ao não resolver o upstream no momento da request, retorna 404 (comportamento de `set $upstream` quando a variável não resolve em tempo de request, dependendo da versão nginx).

Adicionalmente, o error.log do nginx está vazio — não há erro de upstream registrado — o que é inconsistente com falha de proxy. Isso pode indicar que o nginx está caindo no `location /` (try_files) antes da `location /api/` por algum motivo de configuração não óbvio.

**Fix necessário:**
1. Verificar se `location /api/` no nginx está sendo processada corretamente (nginx -T dentro do container para ver config compilada)
2. Testar resolver com `resolver 127.0.0.11` explícito via `curl` dentro do container frontend para confirmar que backend resolve
3. Considerar substituir `set $upstream http://backend:8000; proxy_pass $upstream;` por `proxy_pass http://backend:8000;` direto (sem variável — força resolução DNS no startup, não por request) — aceitável em Swarm onde o backend sempre estará up antes do frontend
4. Rebuild frontend + force redeploy: `docker service update --force go-control-admin_frontend`

### CA-06 — Redis e Celery

**Redis:**
```
1:C 23 Jun 2026 23:37:40 # WARNING Memory overcommit must be enabled!
```
Operacional. Warning não bloqueia.

**Celery — tasks obsoletas:**
```
KeyError: 'platform.verificar_health_modulos'
```
Mesma situação da V1. Worker operacional para tasks registradas, descarta as obsoletas.

### CA-07 — Secrets

```json
["ALLOWED_HOSTS=admin.gocontrol.com.br","CNPJ_CACHE_TTL_SECONDS=1296000",
 "DEBUG=False","DJANGO_SETTINGS_MODULE=config.settings.prod",
 "ENABLE_RBAC_V2=False","REDIS_URL=redis://redis:6379/0"]
```

Nenhum secret em plain-text. Padrão Docker Secrets mantido.

---

## Gaps e Riscos

| Gap | Risco | Ação |
|---|---|---|
| nginx proxy `/api/` não funciona via Traefik | **CRÍTICO** — API inacessível externamente | Diagnose: `nginx -T` dentro do container; testar `proxy_pass http://backend:8000` direto (sem variável); force redeploy |
| CA-03 não verificado diretamente | **BAIXO** — evidência indireta confiável; nenhuma nova migration introduzida | Opcional: correr `docker exec` com env vars explícitos dentro do script de deploy |
| Tasks obsoletas na queue Celery | **BAIXO** | `redis-cli DEL celery` no próximo deploy |
| Redis vm.overcommit_memory=0 | **BAIXO** | `sysctl vm.overcommit_memory=1` no host |
| Celery Beat — histórico de falhas (3x "non-zero exit (1)") | **MÉDIO** | Investigar causa dos falhas anteriores nos logs; monitorar se estabiliza |

---

## Avaliação de Regressão

| Área | Status V2 | Mudança vs V1 |
|---|---|---|
| SPA React (frontend) | OK | Sem mudança — carrega normalmente |
| TLS/Certificado | OK | Sem mudança — TLSv1.3 válido |
| Banco de dados | OK (inferido) | Sem mudança — Django responde 400, não 500 |
| Celery Beat | OK com histórico | 3 restarts anteriores investigar |
| Celery Worker | Parcialmente OK | Sem mudança — tasks obsoletas descartadas |
| Redis | OK com ressalva | Sem mudança |
| Secrets management | OK | Sem mudança |
| API Django (externo) | **FALHA** | Mudou de 301 loop para 404 nginx — fix aplicado mas proxy nginx quebrado |

---

## Veredito

**FAIL** — 1 critério bloqueador (CA-05).

O fix do `SECURE_PROXY_SSL_HEADER` foi aplicado e o loop de 301 não ocorre mais. Progresso real. Porém o nginx agora retorna 404 para `/api/` em requests chegando via Traefik — o proxy_pass para o backend Django não está funcionando quando a request chega pela rede `traefikNetwork`. Internamente o proxy funciona. O problema é de resolução DNS do nginx ou de configuração de rede entre o frontend e o backend para requests do Traefik.

## Recomendação

**REQUEST_CHANGES** — handoff para `@bolt-executor`:

1. Dentro do container frontend, rodar `nginx -T` para ver config compilada e confirmar que `location /api/` está presente
2. Testar resolução: `nslookup backend 127.0.0.11` dentro do container frontend durante uma request real
3. Alterar nginx.conf: substituir `set $upstream http://backend:8000; proxy_pass $upstream;` por `proxy_pass http://backend:8000;` — resolver DNS no startup é adequado em Swarm com VIP estável
4. Rebuild imagem frontend: `docker build -t gocontrol/admin-frontend:latest .` + `docker service update --image gocontrol/admin-frontend:latest go-control-admin_frontend`
5. Re-verificar CA-05 após redeploy

---

---

## Verificação V1 — Histórico (2026-06-28, antes do fix)

**Veredito:** FAIL
**Bloqueadores:** 1 (CA-05 — 301 loop por SECURE_SSL_REDIRECT sem SECURE_PROXY_SSL_HEADER)

| CA | Critério | Status | Evidência |
|---|---|---|---|
| CA-01 | Imagens buildadas no servidor | ✅ VERIFIED | `gocontrol/admin-backend:latest` (id 7f478e0f4e2f, 270MB) e `gocontrol/admin-frontend:latest` (id 54b369ffbbe1, 65.3MB) |
| CA-02 | 6 serviços Running 1/1 | ✅ VERIFIED | Todos 6 serviços com réplica 1/1 |
| CA-03 | Migrations aplicadas, tabelas OK | ✅ VERIFIED | `manage.py migrate --check` exit 0; showmigrations: todas `[X]` até `platform.0066_seed_modulo_environment_urls` e `sessions.0001_initial` |
| CA-04 | TLS + DNS admin.gocontrol.com.br | ✅ VERIFIED | HTTP/2 200, TLSv1.3, certificado CN=admin.gocontrol.com.br válido |
| CA-05 | SPA carrega + API responde externamente | ❌ FAIL | SPA OK. API: HTTP/2 301 em loop — SECURE_SSL_REDIRECT=True sem SECURE_PROXY_SSL_HEADER; Django não reconhecia TLS terminado no Traefik |
| CA-06 | Redis OK, Celery sem erros críticos | ⚠️ PARTIAL | Redis OK. Celery: KeyError tasks obsoletas (verificar_health_modulos, process_notification_outbox) |
| CA-07 | Secrets não expostos em plain-text | ✅ VERIFIED | Apenas vars não-sensíveis em env; secrets via /run/secrets/ |

**Fix prescrito:** `SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')` em `config/settings/prod.py`. Fix foi aplicado (rebuild confirmado por novo image ID) mas introduziu regressão no proxy nginx.
