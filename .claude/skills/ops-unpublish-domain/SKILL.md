---
name: ops-unpublish-domain
description: Remove um domínio de myworkhome.com.br — apaga a regra do Cloudflare Tunnel, o registro DNS e o arquivo de rota do Traefik. Use quando quiser despublicar um serviço exposto anteriormente com /ops-publish-domain.
argument-hint: "[subdominio]"
---

# /ops-unpublish-domain

Remove um subdomínio de `myworkhome.com.br` despublicando o serviço interno.

## Agente

`custom-sysops` — infraestrutura, DevOps, Traefik, Cloudflare, systemd.

## Infraestrutura conhecida

| Componente | Endereço | Observação |
|---|---|---|
| Cloudflare Tunnel | `a6b50548-e82e-44cd-ae27-c8a319d787d6` (workhome) | Remotely managed — configurar via MCP Cloudflare |
| Traefik | LXC `.211`, porta `80` | Config em `/etc/traefik/conf.d/`, hot-reload ativo |
| Base domain | `myworkhome.com.br` | |

## Fluxo de execução

### Passo 1 — Coletar input

Se não foi passado como argumento, perguntar:

```
Qual subdomínio deseja remover? (ex: minha-app → remove minha-app.myworkhome.com.br)
```

Montar:
- `SUBDOMAIN` = subdomínio informado
- `FULL_DOMAIN` = `{SUBDOMAIN}.myworkhome.com.br`

**Confirmação obrigatória antes de prosseguir:**
```
⚠️  Você está prestes a remover {FULL_DOMAIN}.
    Isso vai apagar o DNS, a regra do tunnel e a rota do Traefik.
    Confirma? (s/n)
```

### Passo 2 — Tunnel: remover regra de ingress

Usar o **MCP do Cloudflare**:

1. Ler configuração atual do tunnel `a6b50548-e82e-44cd-ae27-c8a319d787d6`
2. Localizar regra com `hostname: {FULL_DOMAIN}`
3. Se encontrada → remover e salvar configuração atualizada
4. Se não encontrada → avisar e continuar
5. Reportar: "Tunnel ✓ (regra removida, versão {N})" ou "Tunnel — regra não encontrada"

### Passo 3 — DNS: remover CNAME

Usar o **MCP do Cloudflare**:

1. Listar registros DNS da zona `myworkhome.com.br`
2. Localizar CNAME com name `{SUBDOMAIN}`
3. Se encontrado → deletar
4. Se não encontrado → avisar e continuar
5. Reportar: "DNS ✓ (CNAME removido)" ou "DNS — registro não encontrado"

### Passo 4 — Traefik: remover arquivo de rota

No LXC Traefik (`.211`):

```bash
# Localizar arquivo da rota
ls /etc/traefik/conf.d/ | grep "infra-{SUBDOMAIN}"
```

Se encontrado → remover:
```bash
rm /etc/traefik/conf.d/{arquivo encontrado}
```

Aguardar hot-reload (~3s) e verificar logs:
```bash
sleep 3
journalctl -u traefik --since "10 seconds ago" --no-pager | grep -i "{SUBDOMAIN}\|error"
```

Reportar: "Traefik ✓ ({arquivo} removido)" ou "Traefik — arquivo não encontrado"

### Passo 5 — Relatório final

```
✅ Domínio removido com sucesso

  URL removida:  https://{FULL_DOMAIN}

  Tunnel:   regra removida (versão {N})
  DNS:      CNAME removido
  Traefik:  {arquivo} removido, hot-reload OK
```

Se algum item não foi encontrado, listar como `— não encontrado (já estava ausente)`.

## Tratamento de erros

| Situação | O que fazer |
|---|---|
| MCP Cloudflare não autenticado | Iniciar fluxo OAuth — gerar URL e pedir ao usuário para colar o callback |
| Arquivo Traefik não encontrado | Avisar e continuar — pode ter sido removido manualmente |
| Regra de tunnel não encontrada | Avisar e continuar |
| CNAME não encontrado | Avisar e continuar |
| Usuário responde "n" na confirmação | Abortar sem fazer nenhuma alteração |
