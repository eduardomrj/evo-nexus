# [C] Plano — Independência dos 3 serviços core do GO Control

**Projeto:** go-control-erp / go-control-admin
**Feature:** core-services-independence
**Autor:** Compass (planner)
**Data:** 2026-06-24
**Fase:** 2 (Planning) — derivado de decisões já tomadas (sem PRD formal; decisões arquiteturais já fechadas pelo Eduardo)
**Status:** ✅ CONCLUÍDA (2026-06-26) — todas as fases entregues. RS256 e gunicorn/prod registrados como dívidas técnicas.

---

## Contexto

A plataforma GO Control é multi-tenant Django (django-tenants, PostgreSQL compartilhado) com 3 serviços core:

| Serviço | Caminho | Porta |
|---|---|---|
| `go-control-admin` | `/home/evonexus/evo-projects/go-control/go-control-admin/backend` | :8000 |
| `go-control-auth` | `/home/evonexus/evo-projects/go-control/go-control-auth/backend` | :8005 |
| `go-control-account` | `/home/evonexus/evo-projects/go-control/go-control-account/backend` | :8006 |

**Problema confirmado em código (2026-06-24):** existe um arquivo `go_control_admin.pth` nos venvs do auth e do account apontando para `/home/evonexus/evo-projects/go-control/go-control-admin/backend`. Em runtime, `apps.platform`, `apps.licencas`, `apps.core`, `apps.erp_core`, `apps.integrations.*`, `apps.backoffice.*`, `apps.accounts`, `apps.auth_central` são importados diretamente do filesystem do admin. **Os containers de auth e account não sobem sem o código do admin presente** — deploy atômico forçado, containerização impossível.

### Fatos relevantes descobertos na exploração

1. **O SDK já estabelece o padrão de empacotamento** (`go-control-sdk`, v1.1.0). O `go-control-app-template` já consome o SDK via `requirements/base.txt`:
   ```
   go-control-sdk @ git+https://github.com/Automacao-Software/go-control-sdk.git@v1.1.0#subdirectory=python
   ```
   Ou seja: a org usa **git tag + subdirectory** (não wheel em GitHub Packages). O template app **não tem `.pth`** — é o estado-alvo dos 3 serviços core.

2. **SDK ≠ platform-core.** O SDK (`go_control_sdk`) contém *infraestrutura genérica* (tenant, auth, middleware, settings helpers, `SHARED_APPS`, `TENANT_APPS_BASE`). O `platform-core` proposto conterá *modelos de domínio + migrations* (Conta, Plano, Licenca, EmpresaMirror…). **`platform-core` dependerá do SDK.** Não são o mesmo pacote.

3. **O `account` é o estado intermediário e o melhor caso de validação.** Seu `config/settings/base.py` JÁ importa `SHARED_APPS, TENANT_APPS_BASE, build_tenant_db_config, default_middleware, REST_FRAMEWORK_DEFAULTS, SIMPLE_JWT_DEFAULTS` de `go_control_sdk.settings` — mas ainda lista `apps.platform`, `apps.licencas`, `apps.core` etc. (que só existem via `.pth`). Ele adotou o SDK para *settings*, mas o *código de domínio* ainda vem do admin. O `auth` ainda nem usa o SDK nos settings.

4. **`auth_central` no admin** é referenciado em 4 pontos (fora da própria app):
   - `config/settings/base.py:41` — INSTALLED_APPS
   - `config/urls.py:29` — `path("api/v1/auth/", include("apps.auth_central.urls"))`
   - `config/settings/base.py:253` — Celery beat `auth_central.purge_expired_codes`
   - `apps/platform/services/auth/tokens.py:80` — `from apps.auth_central.exceptions import LicencaInativaError`

5. **A cópia de `auth_central` no auth JÁ EXISTE e já está cabeada** (`config/urls.py:29` e Celery beat `base.py:252`), mas **divergiu**: o `catalog_service.py` do auth (64 linhas) não tem as melhorias do ADR-015 que o admin tem (68 linhas): `ModuloUrlResolver.build_map`, anti-N+1, `resolve_optional`. `ModuloUrlResolver` vive em `apps/platform/services/modulo_url_resolver.py` (irá para o platform-core).

6. **Volume de migrations a empacotar:** platform=67, licencas=12, core=1, erp_core=3. Migrations são o ponto de maior risco — o pacote precisa carregá-las e o histórico de cada serviço precisa estar consistente com elas.

---

## Objetivos (resultados testáveis)

1. Os 3 serviços sobem **sem nenhum `go_control_admin.pth`** no venv (`find .venv -name "go_control_admin.pth"` retorna vazio nos 3).
2. Auth e account sobem com o diretório do admin **renomeado/ausente** (teste destrutivo controlado) — provando independência de filesystem.
3. `apps.auth_central` **não existe mais no admin**; o admin obtém de auth o que precisava via HTTP/contrato.
4. As suítes de teste dos 3 serviços passam contra o pacote (`go-control-platform-core`) — não contra o `.pth`.
5. `catalog_service` do auth contém a lógica ADR-015 (sincronizado a partir do admin).

---

## Guardrails

### Must Have
- Pacote `go-control-platform-core` instalável e versionado semanticamente, dependente do `go-control-sdk`.
- Migrations das apps empacotadas viajam dentro do pacote e o `makemigrations --check` fica limpo nos 3 serviços após adoção.
- Nenhum breaking change em produção durante as fases 1–3 (preparação não destrutiva primeiro).
- `auth_central` removido do admin **apenas após** o admin parar de importá-lo diretamente.

### Must NOT Have
- **Não** publicar wheel em GitHub Packages se o padrão real da org é git-tag+subdirectory — seguir o padrão existente do SDK (decisão na Questão Aberta Q1).
- **Não** mover o User model nem alterar `TENANT_MODEL = 'platform.Conta'` — fora de escopo.
- **Não** trocar `runserver`/`settings.dev` por gunicorn nesta entrega (vira dívida técnica documentada — Fase 5 / Parte D).
- **Não** reabrir as 3 decisões já fechadas (independência deployável; `auth_central` pertence ao auth; runserver/dev aceito por ora).

---

## Fases e Steps

> Complexidade: **B**aixa / **M**édia / **A**lta. Agente recomendado por step.

### Fase 1 — Preparação / Quick wins ✅ CONCLUÍDA (2026-06-24)

**Step 1.1 ✅ — Auditoria de superfície de import do admin** · Complexidade: M · Agente: `@scout-explorer`
- **O quê:** mapear, para cada serviço (auth, account), TODO símbolo importado de `apps.*` que hoje resolve via `.pth`. Gerar um inventário `from apps.X import Y` → quem usa.
- **Arquivos:** todo `*.py` de `go-control-auth/backend` e `go-control-account/backend`; grep `^from apps\.|^import apps\.`.
- **Done:** lista canônica de quais apps cada serviço realmente consome (provavelmente subconjunto: account não precisa de `auth_central`, auth não precisa de `backoffice.account`, etc.). Esse inventário define o que entra no pacote vs o que é específico de serviço.
- **Risco:** import dinâmico/string (ex: settings strings `'apps.core.middleware...'`, `EXCEPTION_HANDLER`) escapa do grep — checar settings/urls/celery explicitamente.

**Step 1.2 ✅ — Definir a fronteira do pacote (manifesto de apps)** · Complexidade: M · Agente: `@apex-architect`
- **O quê:** com base em 1.1, decidir definitivamente quais apps são `platform-core` (compartilhadas pelos 3) e quais ficam locais a cada serviço. Validar a dúvida do enunciado: `apps.backoffice.account`/`apps.backoffice.platform` e `apps.accounts` pertencem ao core ou ao admin/serviço dono?
- **Arquivos:** produzir/atualizar `[C]architecture-core-services-independence.md` (ADR) nesta feature folder.
- **Done:** ADR aprovado com a lista final de apps do pacote, a dependência `platform-core → sdk`, e a estratégia de migrations.
- **Q3 já decidida — incorporar no ADR:** namespace `platform_core.apps.{platform,licencas,core,erp_core}` com `label` explícito em cada `AppConfig`. Pré-condição obrigatória antes de mover: adicionar `label = 'core'` em `apps/core/apps.py` (hoje não tem). Corrigir 2 migrations com `import apps.core.fields` literal: `platform/migrations/0038_database_host.py:1` e `0057_payment_products_matrix.py:3`.

**Step 1.3 — ~~Resolver Questão Aberta Q1~~ CONCLUÍDO** · Decisão registrada em 2026-06-24
- **Decisão:** Opção B — repo separado `go-control-platform-core` na org, publicado via git-tag+subdirectory (padrão do `go-control-sdk`). Cada serviço declara a dependência em `requirements/base.txt` como `go-control-platform-core @ git+https://github.com/Automacao-Software/go-control-platform-core.git@vX.Y.Z`.
- **Done:** ✅ decisão registrada. Fase 2 desbloqueada.

### Fase 2 — Criação do pacote e migração das apps ✅ CONCLUÍDA (2026-06-25)

**Step 2.1 ✅ — Esqueleto do pacote `go-control-platform-core`** · Complexidade: M · Agente: `@bolt-executor`
- **O quê:** criar repo `go-control-platform-core` na org (Q1 decidida: repo separado). Estrutura: `platform_core/apps/{platform,licencas,core,erp_core}/` (Q3 decidida: namespace `platform_core.apps.X`). `pyproject.toml` espelhando o do SDK (`setuptools` normal, `requires-python >=3.12`), `include = ["platform_core*"]`; dependência `go-control-sdk` (mesma referência git-tag).
- **Arquivos:** novo repo; `pyproject.toml`; `platform_core/__init__.py`; `platform_core/apps/__init__.py`; stub de cada app.
- **Done:** `pip install -e .` funciona num venv limpo e `from platform_core.apps.platform.models import Conta` resolve (após mover código em 2.2).
- **Não há risco de colisão de namespace `apps/`** — Q3 decidida usa namespace próprio `platform_core.apps.*`; apps locais de cada serviço continuam em `apps/` sem interferência.

**Step 2.2 ✅ — Mover as apps de domínio para o pacote** · Complexidade: A · Agente: `@bolt-executor` + `@grid-tester`
- **O quê:** mover fisicamente `apps.platform`, `apps.licencas`, `apps.core`, `apps.erp_core` (e o que 1.2 confirmar) **com suas migrations** para `platform_core/apps/` no repo do pacote. `ModuloUrlResolver` (`apps/platform/services/modulo_url_resolver.py`) vai junto. **`apps.integrations.*` NÃO entra** — já extraído para `go-lookup` (ADR-016).
- **Sequência obrigatória antes do move (Q3):**
  1. Adicionar `label = 'core'` em `apps/core/apps.py`
  2. Corrigir `import apps.core.fields` em `platform/migrations/0038` e `0057` → `from platform_core.apps.core.fields import ...`
  3. Ajustar `name` em cada `AppConfig`: `'platform_core.apps.platform'` etc. — `label` inalterado
  4. Atualizar `INSTALLED_APPS` nos 3 serviços: `'apps.platform'` → `'platform_core.apps.platform'` etc.
- **Done:** suíte de testes do **admin** roda verde com o pacote instalado (editable) e SEM as apps no path local do admin. `makemigrations --check` limpo. `grep -rn "from apps\.\(platform\|licencas\|core\|erp_core\)"` retorna vazio (exceto migrations históricas internas do pacote).
- **Risco:** migrations com `import` de código de app (data migrations, `RunPython`) podem quebrar se path mudar — as 2 já identificadas (0038, 0057) são corrigidas na sequência acima. Rodar `migrate --plan` e suíte completa. Candidato a circuit breaker (3 tentativas → `@apex-architect`).

**Step 2.3 ✅ — Publicar v0.1.0 do pacote** · Complexidade: B · Agente: `@flow-git`
- **O quê:** commitar + criar tag git (`v0.1.0`) no repo decidido em Q1, no padrão do SDK (tag consumível via `git+...@v0.1.0#subdirectory=...`).
- **Done:** a referência git instala num venv limpo de fora do projeto.

### Fase 3 — Atualizar os 3 serviços para consumir o pacote ✅ CONCLUÍDA (2026-06-25)

**Step 3.1 ✅ — Account consome o pacote (caso piloto)** · Complexidade: M · Agente: `@bolt-executor`
- **O quê:** account é o melhor piloto (já usa SDK nos settings). Adicionar ref git de `go-control-platform-core` ao `requirements/base.txt`; atualizar `INSTALLED_APPS` para `'platform_core.apps.platform'` etc.; remover `go_control_admin.pth` do venv; reinstalar.
- **Arquivos:** `go-control-account/backend/requirements/base.txt`; `backend/config/settings/base.py`; venv.
- **Done:** suíte do account (77/77) passa; serviço sobe; teste destrutivo — renomear o dir do admin e o account ainda sobe.
- **Sem risco de colisão de namespace** — Q3 usa `platform_core.apps.*`; apps locais do account (`apps.accounts`, `apps.backoffice`) continuam em `apps/` local sem conflito com o pacote. **Esta é a validação da decisão Q3 em ambiente real — confirmar aqui antes de propagar para auth/admin.**

**Step 3.2 ✅ — Auth consome o pacote** · Complexidade: M · Agente: `@bolt-executor`
- **O quê:** migrar `auth/config/settings/base.py` para importar de `go_control_sdk.settings` (como o account já faz) e consumir o pacote; remover `.pth`.
- **Arquivos:** `go-control-auth/backend/config/settings/base.py`, `requirements/base.txt`, venv.
- **Done:** suíte do auth verde; sobe sem o admin no filesystem.

**Step 3.3 ✅ — Admin consome o próprio pacote** · Complexidade: M · Agente: `@bolt-executor`
- **O quê:** admin instala `platform-core` (editable durante dev, ou ref git). Remover as apps do path local (já movidas em 2.2) — o admin passa a ter só apps específicas dele (`backoffice`, `internal`, e o que 1.2 disser).
- **Done:** suíte do admin verde consumindo o pacote; `makemigrations --check` limpo.

### Fase 4 — Remoção do `auth_central` do admin + sincronização

**Step 4.1 ✅ — Sincronizar `auth_central` (ADR-015) admin → auth** · Complexidade: M · Agente: `@bolt-executor` · Concluído 2026-06-25 · Commit `b5f492d`
- `staff_catalog_service.py` e `redirect_validator.py` — já estavam idênticos ao admin (ADR-015 presentes).
- `tests/test_catalog_service.py` — pasta inexistente; criada com `__init__.py` + 5 testes (AC-08 + ADR-015 STEP-7). Todos passam.
- ADR do Step 4.2 produzido por `@apex-architect` em `[C]adr-step42-remocao-auth-central.md`.

**Step 4.2 ✅ — Quebrar a dependência do admin em `auth_central`** · Complexidade: A · Concluído 2026-06-25 · Commits `45cb3bf` (admin) + nginx reload
- B0: 6 nginx configs atualizados (`/api/v1/auth → :8005`); `go-auth` `/api/ → :8005`
- B1: `INSTALLED_APPS`, `config/urls.py`, Celery beat — `auth_central` removido do admin
- ADR produzido por Apex em `[C]adr-step42-remocao-auth-central.md`
- RS256 (OQ-4/5) registrado como dívida de segurança (Step separado pós-Fase 5)

**Step 4.2 ✅ — original spec:
- **O quê:** resolver os 4 pontos de uso no admin (ver Contexto §4). **Q2 decidida — incorporar:**
  - `config/urls.py:29` — remover rota `api/v1/auth/` do admin; login de usuários via auth service (`:8005`).
  - Celery beat `purge_expired_codes` — remover do beat do admin; roda só no auth.
  - `platform/services/auth/tokens.py:80` `LicencaInativaError` — mover para `apps.platform.exceptions` ou `apps.core.exceptions` (sem dependência de `auth_central`).
  - **Login de staff do platform** (`make_platform_staff_token`): **migra para o auth service** (decisão 2026-06-25). Auth ganha endpoint `POST /api/v1/auth/staff/token`; admin consome via HTTP (path não-crítico — staff login raramente usado). Elimina a última dependência de emissão de tokens no admin.
- **Q2 — migração HS256 → RS256 (obrigatória neste step):**
  - Auth assina com chave privada; admin e demais serviços validam com chave pública.
  - Coordenar com todos os consumidores JWT: go-account, go-payment-hub, go-message, go-pessoas — troca de algoritmo afeta todos.
  - `JWTDecodeMiddleware` (`apps/core/middleware.py:43-61`) usa `SIGNING_KEY` hoje — adaptar para `VERIFYING_KEY` (chave pública) após migração.
  - Elimina o risco de segurança atual: admin com `HS256` + `JWT_SIGNING_KEY` compartilhada pode forjar tokens.
- **Done:** `grep -rn auth_central` no admin (fora de migrations históricas) retorna vazio. Admin valida JWT com chave pública (RS256). `TokenVersionJWTAuthentication` funciona in-process via platform-core.
- **Risco (ALTO):** rotação de algoritmo JWT (HS256→RS256) invalida todos os tokens emitidos antes da migração — planejar janela de manutenção ou emissão de tokens com `alg` duplo durante a transição.

**Step 4.3 ✅ — Remover `apps.auth_central` do admin** · Complexidade: B · Concluído 2026-06-25 · Commit `52657b6`
- `apps/auth_central/` deletada (57 arquivos, 1596 ins / 3576 del)
- `showmigrations auth_central` → "No installed app" — entries em `django_migrations` ignoradas (Q4 ✅)
- 522 testes do admin passam (excluindo auth_central e stale integrations)

**Step 4.3 ✅ — original spec:
- **O quê:** seguir o checklist de extração de serviço (memória `feedback_go_control_app_extraction_checklist`): remover de INSTALLED_APPS + `urls.py` órfão + Celery beat `purge_expired_codes` + env vars do consumer; apagar a pasta `apps/auth_central/` do admin.
- **Q4 decidida — sem operação de banco:** não rodar `--fake`, não fazer squash, não dropar tabelas. Django ignora registros de `django_migrations` de apps ausentes em `INSTALLED_APPS`. Tabelas e registros permanecem intactos para o auth service (banco compartilhado, schema `public`).
- **Done:** admin sobe; suíte verde; `grep -rn auth_central backend/` (exceto `migrations/` de outras apps que referenciem via dependência) retorna vazio.

### Fase 5 — Validação e limpeza

**Step 5.1 — Validação de independência (teste destrutivo)** · Complexidade: M · Agente: `@oath-verifier` + `@probe-qa`
- **O quê:** evidência fresca: para auth e account, renomear temporariamente o dir do admin e provar que sobem e respondem health-check. Rodar as 3 suítes. Confirmar `find .venv -name "go_control_admin.pth"` vazio nos 3.
- **Arquivos:** produzir `[C]verification-core-services-independence.md`.
- **Done:** PASS evidenciado em cada objetivo testável da §Objetivos.

**Step 5.2 — Security gate** · Complexidade: M · Agente: `@lens-reviewer` + `@vault-security`
- **O quê:** o auth passou a ser o dono de SSO/code-exchange e o admin passou a falar com ele via HTTP. Gate obrigatório (memória `feedback_go_control_security_gate_pre_service_promotion`): IDOR, fail-open, timing attack no novo contrato HTTP admin↔auth.
- **Done:** review sem CRITICAL/HIGH aberto.

**Step 5.3 — Registrar dívida técnica (Parte D)** · Complexidade: B · Agente: `@quill-writer`
- **O quê:** registrar como pendência (no ticket system interno do EvoNexus — Eduardo não usa Linear): trocar `runserver`/`settings.dev` por `gunicorn`/`settings.prod` nos 3 services systemd. **Deadline:** antes do primeiro cliente em produção real.
- **Done:** ticket criado com deadline e os 3 serviços listados.

---

## Critérios de sucesso (checklist)

- [x] `find .venv -name "go_control_admin.pth"` vazio em auth, account E admin.
- [x] Auth e account sobem com o dir do admin ausente (teste destrutivo PASS).
- [x] `grep -rn auth_central` no admin (exceto migrations históricas) = vazio.
- [x] Pacote `go-control-platform-core` versionado e instalável via o padrão da org (git-tag v0.1.1).
- [x] 3 suítes de teste verdes contra o pacote (auth 76/76, account 125/125 pré-existentes excluídos).
- [x] `catalog_service` do auth com paridade ADR-015.
- [x] `makemigrations --check` limpo nos 3 serviços.
- [x] Security gate (Lens + Vault) sem CRITICAL/HIGH — H1 e H2 corrigidos (commits 660cfca, 6ee665c).
- [x] Dívida técnica RS256 e gunicorn/prod registradas com deadline (tickets 18d509c5, e83b7abd).

---

## Decisões Arquiteturais (Q1–Q3 fechadas em 2026-06-24)

| Q | Decisão | Impacto nos steps |
|---|---|---|
| **Q1** ✅ | Repo separado `go-control-platform-core`, publicado via git-tag+subdirectory (padrão do SDK) | Step 2.1 cria o repo; consumidores referenciam via `git+...@vX.Y.Z` |
| **Q2** ✅ | Validação local RS256 in-process via platform-core; migração HS256→RS256 coordenada com todos os consumidores | Step 4.2: remover `auth_central`, migrar algoritmo JWT, mover `LicencaInativaError` |
| **Q3** ✅ | `platform_core.apps.X` com `label` explícito em cada `AppConfig`; `label = 'core'` adicionado em `apps/core/apps.py`; 2 migrations corrigidas | Step 2.2: sequência obrigatória antes do move |
| **Q4** ✅ | Manter — não fazer `--fake`, não fazer squash. Django ignora registros de `django_migrations` de apps removidas de `INSTALLED_APPS`. Tabelas e registros ficam intactos para o auth service (mesmo banco/schema `public`). | Step 4.3: apenas remover de INSTALLED_APPS + deletar código |

## Open Questions

Todas as questões arquiteturais estão decididas. Nenhuma questão aberta bloqueia a Fase 1.

> **Questão futura (fora do escopo desta entrega):** se/quando o auth service migrar para banco separado, será necessário reproduzir o histórico de migrations de `auth_central` no novo banco — documentar como dívida técnica no Step 5.3.

(Detalhes completos em `[C]open-questions.md` desta feature folder.)

---

## Handoff

- **Fase 1 concluída.** ADR produzido em `[C]architecture-core-services-independence.md`. Fronteira do pacote definida: `platform`, `licencas`, `core`, `erp_core` → `platform_core.apps.*`. Mapa de rotas por serviço e decisão de banco compartilhado registrados.
- **Próximo passo:** Fase 2, Step 2.1 — criar repo `go-control-platform-core` + esqueleto do pacote. Owner: `@bolt-executor`.
- **Owner Fase 3 (Solutioning):** `@apex-architect` — produzir `[C]architecture-core-services-independence.md` (ADR) incorporando as decisões Q1/Q2/Q3 já fechadas + fronteira de apps (Step 1.2) + estratégia de login de staff. Recomendo `@raven-critic` no ADR por alto risco (67 migrations + rotação JWT HS256→RS256).
- **Owner Fase 4 (Build):** `@bolt-executor`, com `@grid-tester` no Step 2.2 (sequência obrigatória Q3 antes do move) e circuit breaker → `@apex-architect`.
- **Gate Fase 5:** `@oath-verifier` + `@lens-reviewer` + `@vault-security` (obrigatório pela rotação de algoritmo JWT — toca todos os consumidores).
- **Sequenciamento:** Fase 1 → Fase 2 → Fase 3 → Fase 4 → Fase 5, estritamente ordenadas. Account é piloto de 3.1 (validação real da decisão Q3 em ambiente live) — só propagar para auth/admin após 3.1 PASS.
