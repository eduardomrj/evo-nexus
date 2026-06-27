# Open Questions — core-services-independence

## core-services-independence — 2026-06-24
- [x] Q1 — Onde mora o source do `platform-core`: subdir no repo admin (Opção A) vs repo separado (Opção B)? — Define versionamento/CI; padrão da org (SDK) é repo separado via git-tag — Risco: med — **bloqueia Fase 2**
  - **Decisão (2026-06-24):** Opção B — repo separado `go-control-platform-core` no GitHub, publicado via GitHub Packages (PyPI privado). Segue o mesmo padrão do `go-control-sdk` TypeScript. Cada serviço declara `go-control-platform-core==X.Y` como dep normal no `pyproject.toml`.
  - **Implicações:** criar repo `go-control-platform-core` na org; `pyproject.toml` com build via `hatchling` ou `flit`; publicação por tag (`v1.0.0`) via GitHub Actions; consumidores adicionam `[[tool.uv.sources]]` ou `pip install --index-url github packages`.
- [x] Q2 — Como o admin acessa o auth após remover `auth_central`: HTTP (`PLATFORM_AUTH_URL`) ou deixa de precisar? — Define se nasce contrato HTTP novo (exige security gate) — Risco: high
  - **Decisão (2026-06-24):** Opção B — validação local via RS256 (chave pública). O admin continua validando JWT in-process via `apps.core` (que vai para `platform-core`). O que muda é a remoção dos 11 endpoints de emissão do `auth_central`. Não nasce dependência HTTP runtime.
  - **Insight crítico:** `auth_central` no admin **emite** tokens, não valida. Validação é `apps.core.authentication.TokenVersionJWTAuthentication` + `JWTDecodeMiddleware` + `JWTTenantMiddleware` — todos em `apps.core`, que vai para `platform-core`.
  - **Problema de segurança a corrigir:** hoje admin e auth compartilham `JWT_SIGNING_KEY` com HS256 (`base.py:195-198` idênticos) — admin pode forjar tokens. Migração para RS256 elimina isso: auth assina com privada, todos validam com pública.
  - **Pré-condições obrigatórias antes de remover `auth_central` do admin:**
    1. Migrar HS256 → RS256 coordenada com todos os consumidores (go-account, go-payment-hub, go-message, go-pessoas)
    2. **Login de staff do platform** (`make_platform_staff_token`): **migra para o auth service** — decisão 2026-06-25. Auth ganha endpoint `POST /api/v1/auth/staff/token`; admin consome via HTTP (call não-crítico).
    3. Mover `LicencaInativaError` de `apps.auth_central.exceptions` para `apps.core` ou `apps.platform` (único import problemático: `tokens.py:80`)
  - **Opções A (HTTP) e C (forward-auth)** descartadas: criam dependência runtime do auth a cada request — o admin hoje não tem essa dependência e não deveria ter.
- [x] Q3 — Namespace das apps no pacote: preservar `app_label` atual via namespace package `apps`, ou namespace próprio com `app_label` explícito? — Erro quebra 67+ migrations e ContentType — Risco: high — **decidir em 1.2 antes de 2.2**
  - **Decisão (2026-06-24):** Opção B — `platform_core.apps.{platform,licencas,core,erp_core}` com `label` explícito em cada AppConfig. Padrão idêntico a `django.contrib.auth`. Falha ruidosa (ModuleNotFoundError no startup) vs. colisão silenciosa da Opção A.
  - **Pré-condição obrigatória:** `apps/core/apps.py` atualmente NÃO tem `label` explícito — adicionar `label = 'core'` antes de mover.
  - **Único ponto de atenção nas migrations:** `platform/migrations/0038_database_host.py` e `0057_payment_products_matrix.py` têm `import apps.core.fields` literal — corrigir para `import platform_core.apps.core.fields` (2 linhas).
  - **O que NÃO muda:** labels (`platform`, `licencas`, `core`, `erp_core`), tabelas, django_content_type, FKs, TENANT_MODEL, Celery task names. Apenas `INSTALLED_APPS` e imports de código vivo (~1.244 refs, mecânico).
- [x] Q4 — Migrations de `auth_central` no histórico do admin ao remover: `--fake`, manter, ou squash? Bancos provisionados não podem regredir — Risco: med
  - **Decisão (2026-06-24):** Manter — não fazer `--fake`, não fazer squash, não dropar tabelas. Django ignora linhas de `django_migrations` de apps ausentes em `INSTALLED_APPS` ao rodar `migrate`. Tabelas e registros permanecem no banco compartilhado (schema `public`) para uso do auth service.
  - **Por que não `--fake zero`:** apagaria os registros de `django_migrations` do auth_central no banco compartilhado. O auth service veria as migrations como não aplicadas e tentaria reaplicá-las — corrupção de estado.
  - **Questão futura (out of scope):** se/quando auth migrar para banco separado, será necessário reproduzir o histórico de auth_central nesse banco. Documentar como dívida técnica no Step 5.3.
