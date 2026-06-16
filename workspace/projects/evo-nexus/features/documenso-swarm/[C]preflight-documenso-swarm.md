# Preflight read-only — Documenso Swarm

**Projeto:** evo-nexus / infraestrutura operacional  
**Feature:** documenso-swarm  
**Data local:** 2026-06-11/12 (America/Fortaleza)  
**Escopo:** somente leitura; nenhuma criação/alteração executada

---

## Veredito

**PARTIAL PASS — preflight suficiente para planejar execução, mas com ajustes obrigatórios antes de criar recursos.**

Não foram criados banco, bucket, secrets, stack ou rota. Nenhum deploy foi executado.

---

## Decisões aplicadas ao preflight

- Domínio: `signature.myworkhome.com.br`.
- Exposição: pública controlada.
- Tunnel: Cloudflare Tunnel existente.
- Entrada interna: `http://192.168.88.73:80`.
- Traefik alvo: `homelab_traefik-manager` no Swarm principal.
- Placement desejado: apenas workers da homelab.
- Banco: PostgreSQL existente, DB `documenso`, user `documenso_app`.
- Storage: MinIO principal, bucket `documenso`.
- SMTP: Zoho, remetente originalmente planejado `signature@automacaosoftware.com.br`; substituído em 2026-06-12 por `gocontrol@automacaosoftware.com.br` após validação da app password existente.
- Stack: `documenso`.

---

## Achados — Swarm principal

### Acesso

- Acesso SSH aos nós Swarm funciona com usuário `emrj`, não `root`.
- Hosts validados:
  - `192.168.88.73` → `vm-docker-manager`
  - `192.168.88.77` → `vm-docker-worker-1`
  - `192.168.88.78` → `vm-docker-worker-2`

### Nós

| Hostname | Papel | Labels relevantes | Observação |
|---|---|---|---|
| `vm-docker-manager` | manager/Leader | `provider=local`, `zone=lan`, `host=vm-docker-manager` | SPOF do cluster; Traefik Swarm roda aqui |
| `vm-docker-worker-1` | worker | `provider=local`, `zone=lan`, `host=vm-docker-worker-1`, `allow_app=false` | Worker local, mas `allow_app=false` |
| `vm-docker-worker-2` | worker | `provider=local`, `zone=lan`, `host=vm-docker-worker-2`, `allow_app=true` | Melhor alvo atual para Documenso |
| `hetzner-aivoo` | worker | `provider=hetzner`, `zone=cloud`, `allow_app=true` | Deve ser explicitamente excluído |

### Implicação de placement

A decisão do Eduardo foi “apenas workers da homelab”. Pelas labels atuais, a constraint segura recomendada para o POC é:

```text
node.labels.host == vm-docker-worker-2
```

Alternativa mais flexível exigiria alterar labels do `vm-docker-worker-1` para permitir apps, mas isso é mudança operacional separada e não foi autorizada nesta etapa.

---

## Achados — Traefik Swarm

Serviço alvo encontrado:

```text
homelab_traefik-manager
```

Detalhes:

- Imagem: `traefik:v3.5.3` pinada com digest.
- Roda no `vm-docker-manager`.
- Constraint atual: `node.role == manager`.
- EntryPoints:
  - `web=:80`
  - `websecure=:443`
- Provider:
  - `providers.swarm=true`
  - `providers.swarm.exposedbydefault=false`
  - `providers.swarm.network=traefik-homelab`
- Portas publicadas em host mode:
  - `80:80/tcp`
  - `443:443/tcp`
- Rede Traefik:
  - `traefik-homelab`
  - overlay, attachable, subnet `10.0.1.0/24`

Teste HTTP interno:

- `http://192.168.88.73/` com Host `signature.myworkhome.com.br` retorna 404.
- Isso é esperado enquanto não houver router/labels Documenso.
- Confirma que há algo escutando na porta 80 do manager.

### Implicação para stack Documenso

A stack Documenso deve:

- conectar o serviço à rede `traefik-homelab`;
- definir labels Traefik explícitas;
- usar `traefik.enable=true`;
- usar `traefik.swarm.network=traefik-homelab`;
- definir router para `Host(`signature.myworkhome.com.br`)`;
- definir porta interna do container Documenso no service label.

---

## Achados — Cloudflare Tunnel

LXC 210 `cloudflared-ct`:

- Serviço `cloudflared` ativo.
- Unidade systemd usa `cloudflared --no-autoupdate tunnel run --token ...`.
- Não há `/etc/cloudflared/config.yml` nem `/etc/cloudflared/config.yaml` local.

### Risco/hardening

O token do tunnel aparece na linha de comando do processo/systemd. O valor foi redigido nos relatórios e não deve ser repetido.

**Achado:** isso é um risco de exposição local via `systemctl status`/process list. Não foi alterado porque a etapa é read-only.

### Implicação

Para adicionar `signature.myworkhome.com.br`, provavelmente será necessário alterar a configuração do tunnel via painel/API Cloudflare ou trocar o modo de configuração atual. Antes de mexer:

- registrar config atual do tunnel;
- mapear se o tunnel é gerenciado por token remoto;
- evitar imprimir token;
- ter rollback claro.

---

## Achados — DNS

Resolução atual:

- `signature.myworkhome.com.br` → não resolve.
- `apiminio.myworkhome.com.br` → resolve via Cloudflare.
- `minio.myworkhome.com.br` → resolve via Cloudflare.
- `myworkhome.com.br` sem registro A/AAAA direto no ambiente testado.

### Implicação

Será necessário criar DNS/rota Cloudflare para `signature.myworkhome.com.br`.

---

## Achados — PostgreSQL

Host validado:

```text
192.168.88.106 — db-postgres-home
```

Resultado:

- PostgreSQL: `18.3 (Debian 18.3-1.pgdg12+1)`.
- `pg_isready`: aceitando conexões em `127.0.0.1:5432`.
- DB `documenso`: não existe.
- role `documenso_app`: não existe.

### Implicação

OK para criar DB/user dedicados numa próxima etapa, após aprovação. PostgreSQL atende requisito 14+.

---

## Achados — MinIO

MinIO principal identificado pela rota Traefik LXC 211:

```text
192.168.88.240 — minio-240
```

Rota atual no Traefik LXC 211:

- Console: `minio.myworkhome.com.br` → `http://192.168.88.240:9001`
- API S3: `apiminio.myworkhome.com.br` → `http://192.168.88.240:9000`

Estado:

- `minio-240` ativo.
- Porta 9000 ativa.
- Porta 9001 ativa.
- Data dir: `/opt/minio/data`.
- Bucket `documenso`: não apareceu na listagem inicial de diretórios.

Também existe `minio-235` ativo, mas a rota pública atual aponta para `minio-240`, então `minio-240` é o melhor candidato a MinIO principal.

### Implicação

OK para criar bucket `documenso` e credenciais dedicadas em etapa posterior, após aprovação.

---

## Achados — conflitos de nomes no Swarm

Não há conflitos encontrados para:

- stack/service `documenso` / `documenso_*`;
- secrets contendo `documenso`;
- configs contendo `documenso`;
- networks contendo `documenso`.

---

## Riscos ativos antes da execução

1. **Cloudflare Tunnel token em systemd/process args** — risco de exposição local; não mexer sem plano.
2. **Swarm tem único manager** — `vm-docker-manager` é SPOF e também roda Traefik Swarm.
3. **Placement desejado vs labels atuais** — apenas `vm-docker-worker-2` cumpre `worker + local + allow_app=true`.
4. **Hetzner tem `allow_app=true`** — deve ser excluído explicitamente por constraint de host/local.
5. **DNS `signature.myworkhome.com.br` ainda inexistente**.
6. **DB/bucket/secrets ainda inexistentes** — esperado, pois etapa foi read-only.
7. **Traefik LXC 211 ainda roteia MinIO principal** — coexistirá com Traefik Swarm; documentar limites para evitar confusão.

---

## Recomendações para próxima etapa

Antes de criar recursos, apresentar e aprovar:

1. Rollback específico da preparação:
   - remover DB/user `documenso`/`documenso_app` se criação falhar antes de uso;
   - remover bucket/credenciais se criação falhar antes de objetos reais;
   - remover secrets versionados se stack não for aplicada;
   - não alterar tunnel sem backup/registro da configuração atual.
2. Constraint inicial recomendada:

```yaml
placement:
  constraints:
    - node.labels.host == vm-docker-worker-2
```

3. Stack deve usar rede externa existente:

```yaml
networks:
  traefik-homelab:
    external: true
```

4. Labels Traefik devem usar provider swarm e rede `traefik-homelab`.
5. Antes de publicar rota real, criar stack draft sem segredos inline.

---

## Próximo passo sugerido

Solicitar confirmação humana para executar **preparação de dependências sem publicar**, com rollback mapeado:

- criar DB `documenso` e role `documenso_app`;
- criar bucket `documenso` no MinIO principal;
- gerar secrets técnicos e salvar em Vaultwarden + Swarm secrets;
- gerar `.p12` self-signed de teste;
- montar stack draft sem aplicar rota pública.

Nenhuma dessas ações deve iniciar sem confirmação explícita após apresentação do rollback.
