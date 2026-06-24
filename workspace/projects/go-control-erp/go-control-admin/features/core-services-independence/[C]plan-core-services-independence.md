# [C] Plano — Independência dos 3 serviços core do GO Control

**Projeto:** go-control-erp / go-control-admin
**Feature:** core-services-independence
**Autor:** Compass (planner)
**Data:** 2026-06-24
**Fase:** 2 (Planning) — derivado de decisões já tomadas (sem PRD formal; decisões arquiteturais já fechadas pelo Eduardo)
**Status:** aguardando aprovação para handoff

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

### Fase 1 — Preparação / Quick wins (sem breaking changes)

**Step 1.1 — Auditoria de superfície de import do admin** · Complexidade: M · Agente: `@scout-explorer`
- **O quê:** mapear, para cada serviço (auth, account), TODO símbolo importado de `apps.*` que hoje resolve via `.pth`. Gerar um inventário `from apps.X import Y` → quem usa.
- **Arquivos:** todo `*.py` de `go-control-auth/backend` e `go-control-account/backend`; grep `^from apps\.|^import apps\.`.
- **Done:** lista canônica de quais apps cada serviço realmente consome (provavelmente subconjunto: account não precisa de `auth_central`, auth não precisa de `backoffice.account`, etc.). Esse inventário define o que entra no pacote vs o que é específico de serviço.
- **Risco:** import dinâmico/string (ex: settings strings `'apps.core.middleware...'`, `EXCEPTION_HANDLER`) escapa do grep — checar settings/urls/celery explicitamente.

**Step 1.2 — Definir a fronteira do pacote (manifesto de apps)** · Complexidade: M · Agente: `@apex-architect`
- **O quê:** com base em 1.1, decidir definitivamente quais apps são `platform-core` (compartilhadas pelos 3) e quais ficam locais a cada serviço. Validar a dúvida do enunciado: `apps.backoffice.account`/`apps.backoffice.platform` e `apps.accounts` pertencem ao core ou ao admin/serviço dono?
- **Arquivos:** produzir/atualizar `[C]architecture-core-services-independence.md` (ADR) nesta feature folder.
- **Done:** ADR aprovado com a lista final de apps do pacote, a dependência `platform-core → sdk`, e a estratégia de migrations (namespace de apps preservado: `apps.platform`, etc. — o pacote deve expor os mesmos `app_label` para não quebrar 67+ migrations e FKs).
- **Risco (ALTO):** mudar `app_label` quebra migrations e `ContentType`. O pacote DEVE preservar os labels atuais (`platform`, `licencas`, `core`, `erp_core`). Decidir se o pacote expõe `apps.platform` (namespace `apps`) ou `platform_core.platform` — isso afeta todos os `INSTALLED_APPS` e migrations. **Esta é a decisão de maior impacto.**

**Step 1.3 — Resolver Questão Aberta Q1 (onde mora o source) com Eduardo** · Complexidade: B · Agente: `@compass-planner` (handoff p/ decisão humana)
- **O quê:** decidir Opção A (subdir `packages/platform-core/` no repo admin) vs Opção B (repo separado). Ver §Open Questions.
- **Done:** decisão registrada no ADR. As fases 2+ dependem dela.

### Fase 2 — Criação do pacote e migração das apps

**Step 2.1 — Esqueleto do pacote `go-control-platform-core`** · Complexidade: M · Agente: `@bolt-executor`
- **O quê:** criar `pyproject.toml` espelhando o do SDK (`setuptools` + `wheel`, `requires-python >=3.12`), `name = "go-control-platform-core"`, `version = "0.1.0"`, dependência `go-control-sdk` (mesma referência git-tag do template). Configurar `packages.find` para incluir o namespace `apps*` (ou o namespace decidido em 1.2).
- **Arquivos:** novo `pyproject.toml` no local decidido em Q1; `README.md`; `__init__.py` de pacote.
- **Done:** `pip install -e .` do pacote funciona num venv limpo e `import apps.platform` resolve do pacote (não do `.pth`).
- **Risco:** descoberta de packages do setuptools com namespace `apps` — confirmar que `apps/` tem `__init__.py` e que não colide com `apps/` local de cada serviço.

**Step 2.2 — Mover as apps de domínio para o pacote** · Complexidade: A · Agente: `@bolt-executor` + `@grid-tester`
- **O quê:** mover fisicamente `apps.platform`, `apps.licencas`, `apps.core`, `apps.erp_core`, `apps.integrations.cep`, `apps.integrations.cnpj` (e o que 1.2 confirmar) **com suas migrations** para dentro do pacote. `ModuloUrlResolver` (`apps/platform/services/modulo_url_resolver.py`) vai junto.
- **Arquivos:** árvore `apps/` do admin → pacote; ajustar imports internos se o namespace mudar.
- **Done:** suíte de testes do **admin** roda verde com o pacote instalado (editable) e SEM as apps no path local do admin. `makemigrations --check` limpo.
- **Risco (ALTO):** migrations com `import` de código de app (data migrations, `RunPython`) podem quebrar se o caminho de import mudar. Rodar `migrate --plan` e a suíte completa. Este é o step de maior esforço — candidato a circuit breaker (3 tentativas → escalar `@apex-architect`).

**Step 2.3 — Publicar v0.1.0 do pacote** · Complexidade: B · Agente: `@flow-git`
- **O quê:** commitar + criar tag git (`v0.1.0`) no repo decidido em Q1, no padrão do SDK (tag consumível via `git+...@v0.1.0#subdirectory=...`).
- **Done:** a referência git instala num venv limpo de fora do projeto.

### Fase 3 — Atualizar os 3 serviços para consumir o pacote

**Step 3.1 — Account consome o pacote (caso piloto)** · Complexidade: M · Agente: `@bolt-executor`
- **O quê:** account é o melhor piloto (já usa SDK nos settings). Adicionar `go-control-platform-core==0.1.0` (ou ref git) ao `requirements/base.txt`; remover `go_control_admin.pth` do venv; reinstalar.
- **Arquivos:** `go-control-account/backend/requirements/base.txt`; venv.
- **Done:** suíte do account (referência de memória: 77/77) passa; serviço sobe; teste destrutivo — renomear o dir do admin e o account ainda sobe.
- **Risco:** colisão entre `apps/` local do account (`apps.accounts`, `apps.backoffice`) e `apps/` do pacote — namespace `apps` precisa fundir os dois (pacote + local). Confirmar que Python resolve namespace package corretamente (ambos `apps/` sem conflito de submódulos). **Validar isto aqui antes de propagar.**

**Step 3.2 — Auth consome o pacote** · Complexidade: M · Agente: `@bolt-executor`
- **O quê:** migrar `auth/config/settings/base.py` para importar de `go_control_sdk.settings` (como o account já faz) e consumir o pacote; remover `.pth`.
- **Arquivos:** `go-control-auth/backend/config/settings/base.py`, `requirements/base.txt`, venv.
- **Done:** suíte do auth verde; sobe sem o admin no filesystem.

**Step 3.3 — Admin consome o próprio pacote** · Complexidade: M · Agente: `@bolt-executor`
- **O quê:** admin instala `platform-core` (editable durante dev, ou ref git). Remover as apps do path local (já movidas em 2.2) — o admin passa a ter só apps específicas dele (`backoffice`, `internal`, e o que 1.2 disser).
- **Done:** suíte do admin verde consumindo o pacote; `makemigrations --check` limpo.

### Fase 4 — Remoção do `auth_central` do admin + sincronização

**Step 4.1 — Sincronizar `catalog_service` (ADR-015) admin → auth** · Complexidade: M · Agente: `@bolt-executor`
- **O quê:** portar para o `auth_central` do auth as melhorias do admin: `ModuloUrlResolver.build_map`, anti-N+1, `resolve_optional`. `ModuloUrlResolver` virá via pacote (Fase 2), então o import resolve.
- **Arquivos:** `go-control-auth/backend/apps/auth_central/services/catalog_service.py` (64→~68 linhas, alinhar ao admin).
- **Done:** diff entre os dois `catalog_service.py` mostra paridade funcional; teste do endpoint de catálogo no auth cobre `url_producao`.
- **Risco:** outras divergências além do `catalog_service` — diff completo de `apps/auth_central/` entre admin e auth antes de assumir que só o catalog divergiu.

**Step 4.2 — Quebrar a dependência do admin em `auth_central`** · Complexidade: A · Agente: `@apex-architect` (decisão) + `@bolt-executor`
- **O quê:** resolver os 4 pontos de uso no admin (ver Contexto §4):
  - `config/urls.py:29` — o admin ainda precisa servir `api/v1/auth/`? Se auth é o dono, o admin remove a rota ou faz proxy/redirect.
  - Celery beat `purge_expired_codes` — passa a rodar SÓ no auth (remover do beat do admin).
  - `platform/services/auth/tokens.py:80` `LicencaInativaError` — substituir por exceção do SDK/local, ou expor o erro via contrato HTTP (resolve Questão Aberta Q2).
- **Done:** `grep -rn auth_central` no admin (fora de migrations históricas) retorna vazio.
- **Risco (ALTO):** se o admin gera tokens (login-app) e isso dependia de `auth_central`, mover/remover quebra o fluxo de login cross-domain. Mapear o fluxo end-to-end antes (handoff a `@apex-architect`). Decidir Q2 (admin via HTTP vs admin não precisa mais).

**Step 4.3 — Remover `apps.auth_central` do admin** · Complexidade: B · Agente: `@bolt-executor`
- **O quê:** seguir o checklist de extração de serviço (memória `feedback_go_control_app_extraction_checklist`): remover de INSTALLED_APPS + urls.py órfão + Celery beat + env vars do consumer; apagar a pasta `apps/auth_central/` do admin.
- **Done:** admin sobe; suíte verde; nenhuma referência residual.
- **Risco:** migrations de `auth_central` no histórico do admin — decidir se ficam como "fake" no histórico ou se há `swappable`. Não apagar migrations já aplicadas em bancos existentes sem plano de `--fake`.

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

- [ ] `find .venv -name "go_control_admin.pth"` vazio em auth, account E admin.
- [ ] Auth e account sobem com o dir do admin ausente (teste destrutivo PASS).
- [ ] `grep -rn auth_central` no admin (exceto migrations históricas) = vazio.
- [ ] Pacote `go-control-platform-core` versionado e instalável via o padrão da org (git-tag ou wheel — Q1).
- [ ] 3 suítes de teste verdes contra o pacote.
- [ ] `catalog_service` do auth com paridade ADR-015.
- [ ] `makemigrations --check` limpo nos 3 serviços.
- [ ] Security gate (Lens + Vault) sem CRITICAL/HIGH.
- [ ] Dívida técnica gunicorn/prod registrada com deadline.

---

## Open Questions

- [ ] **Q1 — Onde mora o source do `platform-core`?** Opção A (subdir `packages/platform-core/` no repo admin, mesmo histórico git) vs Opção B (repo separado `go-control-platform-core`). — Importa: define o fluxo de versionamento/CI e o quanto o admin permanece "dono" do core. O padrão atual da org (SDK) é repo separado consumido via git-tag+subdirectory; Opção B é mais consistente, Opção A é mais simples no curto prazo. — Risco: médio. **Bloqueia Fase 2.**
- [ ] **Q2 — Como o admin acessa o auth após remover `auth_central`?** Via HTTP (`PLATFORM_AUTH_URL`) ou o admin simplesmente deixa de precisar do `auth_central` (ex: `LicencaInativaError` vira exceção local/SDK e a geração de token de login migra inteiramente para o auth)? — Importa: define se nasce um novo contrato HTTP admin→auth (que exige security gate) ou se a dependência some por completo. — Risco: alto (toca fluxo de login cross-domain).
- [ ] **Q3 — Namespace das apps no pacote.** Preservar `app_label` atual (`platform`, `licencas`, `core`, `erp_core`) é obrigatório para não quebrar 67+ migrations e ContentType. O pacote expõe namespace `apps` (namespace package fundindo pacote + local de cada serviço) ou um namespace próprio com `app_label` explícito em cada `AppConfig`? — Importa: decisão de maior impacto técnico; erro aqui quebra migrations em bancos existentes. — Risco: alto. **Decidir em 1.2, antes de 2.2.**
- [ ] **Q4 — Migrations de `auth_central` no histórico do admin.** Como tratar ao remover a app: `--fake`, manter histórico, ou squash? Bancos já provisionados não podem regredir. — Risco: médio.

(Estas questões também são anexadas a `[C]open-questions.md` desta feature folder.)

---

## Handoff

- **Próximo passo:** decidir Q1 e Q3 com Eduardo (Fase 1, Steps 1.2–1.3) **antes** de qualquer código.
- **Owner Fase 3 (Solutioning):** `@apex-architect` — produzir `[C]architecture-core-services-independence.md` (ADR) cobrindo namespace de apps (Q3), estratégia de migrations e contrato admin↔auth (Q2). Recomendo `@raven-critic` no ADR por ser alto risco (toca 67 migrations + fluxo de login).
- **Owner Fase 4 (Build):** `@bolt-executor`, com `@grid-tester` no Step 2.2 (migrations) e circuit breaker → `@apex-architect`.
- **Gate Fase 5:** `@oath-verifier` + `@lens-reviewer` + `@vault-security`.
- **Sequenciamento:** Fase 1 → Fase 2 → Fase 3 → Fase 4 → Fase 5, estritamente ordenadas (cada fase depende da anterior). Account é piloto de 3.1; só propagar para auth/admin após 3.1 PASS.
