# Resultado da preparação de dependências — Documenso Swarm

**Data local:** 2026-06-12  
**Escopo:** preparação sem publicação  
**Status:** concluído sem alterar DNS/tunnel/rota e sem deploy

---

## Recursos criados/atualizados

- Vaultwarden secure note `documenso-swarm-poc-secrets-v1`
- PostgreSQL DB `documenso` e role `documenso_app`
- MinIO bucket `documenso`, user `documenso_app` e policy `documenso-rw`
- Docker Swarm secrets versionados `documenso_*_v1`, incluindo `documenso_encryption_secondary_key_v1`
- Stack preparada para revisão: `stack-prepared-documenso.yml`
- Stack pós-bootstrap com signup fechado: `stack-prepared-documenso-signup-closed.yml`

---

## Verificação sem segredos

### PostgreSQL

```text
db=true
role=true
```

### MinIO

```text
bucket=true
user=true
policy=true
```

### Docker secrets

```text
documenso_postgres_password_v1=true
documenso_s3_access_key_v1=true
documenso_s3_secret_key_v1=true
documenso_nextauth_secret_v1=true
documenso_encryption_key_v1=true
documenso_cert_p12_pass_v1=true
documenso_cert_p12_v1=true
```

---

## Não alterado

- DNS `signature.myworkhome.com.br`
- Cloudflare Tunnel
- Traefik routers/labels em serviço ativo
- Deploy da stack Documenso
- Migrations da aplicação

---

## Warning conhecido atualizado — CORS MinIO

- O comando de aplicação de CORS por bucket (`mc cors set local/documenso ...`) falhou com `NotImplemented` e o bucket continua sem CORS específico (`No bucket CORS configuration found`).
- Porém, o CORS efetivo no endpoint MinIO foi validado via `OPTIONS` para `GET`, `HEAD`, `PUT`, `POST` e `DELETE` usando origem `https://signature.myworkhome.com.br`; todos retornaram `204` com `Access-Control-Allow-Origin`.
- Achado de segurança: a configuração global atual do MinIO é permissiva (`api cors_allow_origin=*`) e reflete origem arbitrária. Teste com `https://evil.example` também retornou `204` e `Access-Control-Allow-Origin: https://evil.example`.
- Para o POC sem exposição direta pública do MinIO, isso não bloqueia o deploy interno. Antes de exposição pública direta/presigned upload via navegador, recomenda-se hardening global do MinIO com janela operacional e rollback.
- Não houve restart do MinIO, alteração de DNS, tunnel, Traefik ou deploy.

---

## Próximo passo

Escolher/pinar imagem Documenso, revisar variáveis exatas da release e preparar stack final para deploy interno controlado.
