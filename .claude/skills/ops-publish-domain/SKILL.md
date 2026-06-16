---
name: ops-publish-domain
description: Publica um novo domínio em myworkhome.com.br — cria regra no Cloudflare Tunnel, registro DNS e rota no Traefik apontando para o serviço desejado. Use quando quiser expor um serviço da homelab para a internet via tunnel sem precisar acessar o dashboard do Cloudflare.
argument-hint: "[subdominio] [http://ip:porta]"
---

# /ops-publish-domain

Publica um subdomínio de `myworkhome.com.br` expondo um serviço interno via Cloudflare Tunnel + Traefik.

## Agente

`custom-sysops` — infraestrutura, DevOps, Traefik, Cloudflare, systemd.

## Infraestrutura conhecida

| Componente | Endereço | Observação |
|---|---|---|
| Cloudflare Tunnel | `a6b50548-e82e-44cd-ae27-c8a319d787d6` (workhome) | Remotely managed — configurar via MCP Cloudflare |
| Traefik | LXC `.211`, porta `80` | Config em `/etc/traefik/conf.d/`, hot-reload ativo |
| Base domain | `myworkhome.com.br` | CNAME deve apontar para `<tunnel-id>.cfargotunnel.com` |
| Stack completa | `Browser → Cloudflare CDN → Tunnel (.210) → Traefik (.211:80) → serviço destino` | |

## Fluxo de execução

### Passo 1 — Coletar inputs

Se não foram passados como argumento, perguntar:

```
1. Subdomínio: qual o subdomínio desejado? (ex: minha-app → minha-app.myworkhome.com.br)
2. Serviço destino: para qual endereço interno direcionar? (ex: http://192.168.88.250:8080)
3. BasicAuth: quer proteger com usuário/senha? (s/n) — se sim, qual usuário?
```

Montar as variáveis:
- `SUBDOMAIN` = subdomínio informado (sem o domínio base)
- `FULL_DOMAIN` = `{SUBDOMAIN}.myworkhome.com.br`
- `TARGET_SERVICE` = URL do serviço destino
- `USE_AUTH` = true/false
- `TRAEFIK_FILE` = `/etc/traefik/conf.d/{numero}-infra-{SUBDOMAIN}.yaml` — numerar incrementalmente (verificar maior número existente em `/etc/traefik/conf.d/` e somar 1)

### Passo 2 — DNS: verificar e criar CNAME

Usar o **MCP do Cloudflare** (`mcp__cloudflare__*`):

1. Listar registros DNS da zona `myworkhome.com.br`
2. Verificar se já existe CNAME para `{SUBDOMAIN}`
3. Se não existir → criar:
   - **Type:** `CNAME`
   - **Name:** `{SUBDOMAIN}`
   - **Content:** `a6b50548-e82e-44cd-ae27-c8a319d787d6.cfargotunnel.com`
   - **Proxied:** `true`
   - **TTL:** Auto
4. Reportar: "DNS ✓ (criado)" ou "DNS ✓ (já existia)"

### Passo 3 — Tunnel: adicionar regra de ingress

Usar o **MCP do Cloudflare**:

1. Ler configuração atual do tunnel `a6b50548-e82e-44cd-ae27-c8a319d787d6`
2. Verificar se já existe regra para `{FULL_DOMAIN}`
3. Se não existir → adicionar **antes** do catch-all (`http_status:404`):
   ```json
   {
     "hostname": "{FULL_DOMAIN}",
     "service": "http://192.168.88.211:80"
   }
   ```
4. Salvar a configuração atualizada
5. Reportar versão salva: "Tunnel ✓ (versão {N})"

### Passo 4 — Traefik: criar arquivo de rota

No LXC Traefik (`.211`), criar o arquivo `{TRAEFIK_FILE}`:

**Sem BasicAuth:**
```yaml
http:
  routers:
    {SUBDOMAIN}-http:
      rule: "Host(`{FULL_DOMAIN}`)"
      entryPoints:
        - web
      service: {SUBDOMAIN}-svc

  services:
    {SUBDOMAIN}-svc:
      loadBalancer:
        servers:
          - url: "{TARGET_SERVICE}"
```

**Com BasicAuth** (gerar hash via `htpasswd -nb {usuario} {senha}`):
```yaml
http:
  routers:
    {SUBDOMAIN}-http:
      rule: "Host(`{FULL_DOMAIN}`)"
      entryPoints:
        - web
      middlewares:
        - auth@file
      service: {SUBDOMAIN}-svc

  services:
    {SUBDOMAIN}-svc:
      loadBalancer:
        servers:
          - url: "{TARGET_SERVICE}"
```

> Se `auth@file` não existir no Traefik, criar middleware BasicAuth inline no próprio arquivo com o hash gerado.

### Passo 5 — Verificar hot-reload do Traefik

```bash
# Verificar se Traefik detectou o novo arquivo (aguardar ~3s)
sleep 3
# Checar logs do Traefik por erros de parse no novo arquivo
journalctl -u traefik --since "30 seconds ago" --no-pager | grep -i "{SUBDOMAIN}\|error\|warn"
```

Se aparecer erro de parse → reportar e corrigir antes de continuar.

### Passo 6 — Smoke test

```bash
# Testar se o domínio responde (aguardar propagação DNS ~5s)
sleep 5
curl -sI "https://{FULL_DOMAIN}" | head -5
```

Resultados esperados:
- `HTTP/2 200` ou `301`/`302` → ✅ sucesso
- `HTTP/2 404` do Cloudflare → regra de tunnel não aplicou ainda (aguardar mais 10s e tentar novamente)
- `curl: (6) Could not resolve host` → DNS ainda propagando (normal nos primeiros segundos)
- `HTTP/2 502` ou `503` → serviço destino não está respondendo

### Passo 7 — Relatório final

```
✅ Domínio publicado com sucesso

  URL:        https://{FULL_DOMAIN}
  Serviço:    {TARGET_SERVICE}
  BasicAuth:  {sim (usuário: X) / não}

  DNS:        CNAME criado/já existia → a6b50548...cfargotunnel.com (proxied)
  Tunnel:     regra adicionada → versão {N}
  Traefik:    {TRAEFIK_FILE} criado, hot-reload OK

Para remover depois: /ops-unpublish-domain {SUBDOMAIN}
```

## Tratamento de erros comuns

| Situação | O que fazer |
|---|---|
| MCP Cloudflare não autenticado | Iniciar fluxo OAuth — gerar URL e pedir ao usuário para colar o callback |
| CNAME já existe apontando para outro lugar | Alertar e perguntar se quer sobrescrever |
| Regra de tunnel já existe | Alertar e perguntar se quer atualizar o serviço destino |
| Arquivo Traefik já existe | Alertar e perguntar se quer sobrescrever |
| Serviço destino não responde no smoke test | Avisar que publicação foi feita mas serviço parece offline — verificar se o IP/porta estão corretos |
| Número do arquivo Traefik incerto | Usar `ls /etc/traefik/conf.d/ | sort | tail -1` para pegar o maior e incrementar |

## Notas

- O Cloudflare sempre roteia para `http://192.168.88.211:80` (Traefik) — o Traefik é quem faz o roteamento final para o serviço destino. Nunca apontar o tunnel diretamente para o serviço.
- TLS é gerenciado pelo Cloudflare (full/flexible) — não configurar certificados no Traefik para rotas expostas via tunnel.
- Para serviços com WebSocket (ex: terminais, Discord bots), adicionar ao router Traefik: `middlewares: ["ws-headers@file"]` se disponível, ou headers manuais.
