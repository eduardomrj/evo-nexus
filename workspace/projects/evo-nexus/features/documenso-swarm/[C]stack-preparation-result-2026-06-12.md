# Documenso Swarm — Preparação da stack segura

**Data:** 2026-06-12  
**Responsável:** SysOps  
**Status:** preparado, não publicado, não aplicado

## Escopo executado

- Validado CORS efetivo do MinIO para o domínio aprovado.
- Revisadas fontes oficiais do Documenso via repositório GitHub oficial.
- Pinada imagem Documenso em versão e digest.
- Criada stack preparada sem segredos reais no YAML.
- Criada variante pós-bootstrap com signup fechado.
- Adicionados middlewares Traefik básicos de headers/rate limit.
- Criado secret adicional exigido pela release: `documenso_encryption_secondary_key_v1`.

## Artefatos criados/atualizados

- `workspace/projects/evo-nexus/features/documenso-swarm/stack-prepared-documenso.yml`
- `workspace/projects/evo-nexus/features/documenso-swarm/stack-prepared-documenso-signup-closed.yml`
- `workspace/projects/evo-nexus/features/documenso-swarm/stack-draft-documenso.yml`
- `workspace/projects/evo-nexus/features/documenso-swarm/[C]preparation-result-2026-06-12.md`
- `workspace/infra/runbooks/documenso-swarm-preparacao-2026-06-11.md`
- `.claude/agent-memory/custom-sysops/documenso-swarm.md`

## Imagem Documenso

Imagem preparada:

```text
documenso/documenso:v2.11.0@sha256:d9b9a21841e28ebf08d747706e15319a485aa19afea09ab1c926b025c2ce4a18
```

Fonte de versão: release oficial GitHub `documenso/documenso` v2.11.0.

## Variáveis oficiais confirmadas

Confirmadas nas fontes oficiais do Documenso (`.env.example`, `docker/production/compose.yml`, docs self-hosting e código):

- `NEXT_PRIVATE_DATABASE_URL`
- `NEXT_PRIVATE_DIRECT_DATABASE_URL`
- `NEXT_PUBLIC_WEBAPP_URL`
- `NEXT_PRIVATE_INTERNAL_WEBAPP_URL`
- `NEXTAUTH_SECRET`
- `NEXT_PRIVATE_ENCRYPTION_KEY`
- `NEXT_PRIVATE_ENCRYPTION_SECONDARY_KEY`
- `NEXT_PUBLIC_UPLOAD_TRANSPORT=s3`
- `NEXT_PRIVATE_UPLOAD_ENDPOINT`
- `NEXT_PRIVATE_UPLOAD_FORCE_PATH_STYLE`
- `NEXT_PRIVATE_UPLOAD_REGION`
- `NEXT_PRIVATE_UPLOAD_BUCKET`
- `NEXT_PRIVATE_UPLOAD_ACCESS_KEY_ID`
- `NEXT_PRIVATE_UPLOAD_SECRET_ACCESS_KEY`
- `NEXT_PRIVATE_SMTP_TRANSPORT=smtp-auth`
- `NEXT_PRIVATE_SMTP_HOST`
- `NEXT_PRIVATE_SMTP_PORT`
- `NEXT_PRIVATE_SMTP_SECURE`
- `NEXT_PRIVATE_SMTP_USERNAME`
- `NEXT_PRIVATE_SMTP_PASSWORD`
- `NEXT_PRIVATE_SMTP_FROM_NAME`
- `NEXT_PRIVATE_SMTP_FROM_ADDRESS`
- `NEXT_PRIVATE_SIGNING_TRANSPORT=local`
- `NEXT_PRIVATE_SIGNING_LOCAL_FILE_PATH`
- `NEXT_PRIVATE_SIGNING_PASSPHRASE`
- `NEXT_PRIVATE_JOBS_PROVIDER=local`
- `NEXT_PUBLIC_DISABLE_SIGNUP`
- `NEXT_PRIVATE_ALLOWED_SIGNUP_DOMAINS`
- `DOCUMENSO_DISABLE_TELEMETRY`

## Secrets Swarm

Confirmados existentes:

```text
documenso_postgres_password_v1=true
documenso_s3_access_key_v1=true
documenso_s3_secret_key_v1=true
documenso_nextauth_secret_v1=true
documenso_encryption_key_v1=true
documenso_encryption_secondary_key_v1=true
documenso_cert_p12_pass_v1=true
documenso_cert_p12_v1=true
documenso_smtp_password_v1=true
```

Pendente:

```text
nenhum secret técnico pendente para stack preparada
```

## Validação Zoho App Password

Foi encontrado no Vaultwarden o item candidato `email-evonexus`.

Resultado da validação SMTP, sem imprimir segredo:

```text
zoho_login_signature=false
error_type=SMTPAuthenticationError
zoho_login_saved_user=true
username=gocontrol@automacaosoftware.com.br
smtp_code=235
```

Conclusão:

- A app password existente é válida para `gocontrol@automacaosoftware.com.br`.
- A mesma senha **não autentica** para `signature@automacaosoftware.com.br`.
- Eduardo autorizou trocar o remetente/SMTP para `gocontrol@automacaosoftware.com.br` em 2026-06-12.
- As stacks preparadas foram atualizadas para usar `gocontrol@automacaosoftware.com.br` em `NEXT_PRIVATE_SMTP_USERNAME` e `NEXT_PRIVATE_SMTP_FROM_ADDRESS`.
- O secret `documenso_smtp_password_v1` foi criado no Swarm a partir do Vaultwarden sem imprimir o valor.
- Validação do secret: `smtp_secret=created`, `smtp_secret_inspect=true`.

## Segurança aplicada na stack preparada

- Nenhum segredo real hardcoded no YAML.
- Docker Swarm secrets usados para DB password, S3 keys, auth/encryption secrets, certificado/passphrase e SMTP password.
- Como não há suporte documentado a `*_FILE`, a stack usa wrapper shell para ler `/run/secrets/*` e exportar as variáveis antes de `sh start.sh`.
- Imagem pinada com tag + digest.
- Placement fixado em worker homelab: `node.labels.host == vm-docker-worker-2`.
- Traefik com middlewares:
  - `contentTypeNosniff=true`
  - `browserXssFilter=true`
  - `frameDeny=true`
  - rate limit `average=30`, `burst=60`
- Stack pós-bootstrap com `NEXT_PUBLIC_DISABLE_SIGNUP=true` preparada.

## CORS MinIO

Resultado real:

- `mc cors set local/documenso` falha com `NotImplemented`; bucket não aceita CORS específico por esse caminho.
- CORS efetivo funciona por configuração global do MinIO (`api cors_allow_origin=*`).
- `OPTIONS` para `https://signature.myworkhome.com.br` retornou `204` para GET/HEAD/PUT/POST/DELETE.
- Origem arbitrária também é refletida; risco conhecido.

Decisão operacional:

- Não bloquear POC interno por isso.
- Não expor MinIO publicamente.
- Hardening global de CORS no MinIO fica como mudança separada, com janela, rollback e possível restart.

## Não alterado

- DNS `signature.myworkhome.com.br`.
- Cloudflare Tunnel.
- Traefik service ativo.
- Stack Documenso.
- Migrations em produção.
- SMTP Zoho.
- Restart de MinIO.

## Validação pós-correção de interpolation e troca de remetente

A verificação independente identificou inicialmente um blocker de YAML/Compose: o script inline em `command` usava variáveis shell com `$`, e o Docker Compose/Swarm tentava interpolar esses valores antes de entregar ao container.

Correções aplicadas:

- Escapados `$` shell como `$$` nas duas stacks preparadas.
- SMTP username/remetente trocado para `gocontrol@automacaosoftware.com.br` após autorização do Eduardo.
- Revalidado localmente:
  - `docker stack config -c stack-prepared-documenso.yml` → `local_bootstrap_config=true`
  - `docker stack config -c stack-prepared-documenso-signup-closed.yml` → `local_closed_config=true`
- Revalidado no manager Swarm via stdin, sem deploy:
  - stack bootstrap → `manager_bootstrap_config=true`
  - stack pós-bootstrap → `manager_closed_config=true`

## Blockers antes de deploy interno

1. Backup mínimo pré-migration concluído em `workspace/infra/backups/documenso/2026-06-12-predeploy/`:
   - dump PostgreSQL dedicado `documenso` em formato custom;
   - validação do dump com `pg_restore --list` remoto no PostgreSQL 18;
   - manifesto do bucket MinIO `documenso` — bucket vazio no momento do backup;
   - metadados dos 9 secrets Swarm por nome/ID/data, sem valores;
   - registro do digest da imagem nas stacks efetivas preservadas.
2. Confirmar caminho Cloudflare Tunnel planejado:
   - se `Tunnel -> http://IP_MANAGER_SWARM:80`, manter router `web`.
   - se `Tunnel -> https://IP_MANAGER_SWARM:443`, trocar para `websecure` + TLS.
3. Confirmar rollback mapeado e autorizar explicitamente deploy interno.

## Gate pós-deploy interno

- `docker stack services documenso`
- `docker service ps documenso_app`
- logs sem segredos e sem migration failure
- health HTTP local
- login/admin bootstrap
- criar admin `eduardo@automacaosoftware.com.br`
- aplicar stack pós-bootstrap com signup fechado
- provar signup fechado

## Gate antes de publicação externa

- DNS/tunnel apontados corretamente.
- Rota Traefik ativa só pelo caminho desejado.
- Smoke com `eduardo@sysautomacao.com.br`:
  - upload PDF;
  - envio SMTP Zoho;
  - assinatura externa;
  - PDF final baixável;
  - objeto no MinIO;
  - signup fechado.
