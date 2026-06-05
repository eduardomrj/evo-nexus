---
author: claude
agent: compass-planner
type: work-plan
date: 2026-05-06
plan-name: migracao-minierp-piloto-pessoas-produtos
status: partially_superseded
superseded_by: ./[C]plan-ciclo2-redesign.md
ticket: MIG-01 (ad313e49-c22e-4d52-aaf8-713e21f3fe78)
goal: minierp-01-discovery-classificacao
prd: ./[C]prd-migracao-minierp-adianti-python-react.md
---

> ⚠️ **PARCIALMENTE SUPERSEDIDO — 2026-05-08**
>
> Steps 1-10 deste plano foram executados no Ciclo 1. A partir dos Steps relacionados a identidade,
> tenancy e backoffice, este plano foi substituído por:
> **`[C]plan-ciclo2-redesign.md`**
>
> As decisões D-R01..D-R12 (2026-05-08) afetam os Steps 6-10 originais. Consulte o plano do Ciclo 2
> para o estado atual de qualquer work relacionado a login, tenancy, backoffice ou frontend SPAs.

# Work Plan — Piloto Pessoas + Produtos (GO Control ERP)

## Context

PRD aprovado em `[C]prd-migracao-minierp-adianti-python-react.md` define o piloto end-to-end que valida a stack Django 5 + React 18 + PrimeReact com multi-tenancy, soft delete e proxy pattern para integrações. Este plano materializa a entrega em 6 passos sequenciais com TDD obrigatório.

> **Atualização 2026-05-06 (Step 1b):** O Step 1 foi executado e expandido em um Step 1b adicional que estabeleceu uma arquitetura mais robusta do que a originalmente especificada. Decisões D10-D15 e D19 introduziram **django-tenants (schema-per-Conta)** como camada primária de isolamento, **Unified User System (modelo ZOHO)** em `apps.platform`, e **JWT com claim `ctx`** para contexto de tenant. A Empresa (Matriz/Filiais) permanece como camada secundária dentro do schema da Conta. As seções abaixo foram atualizadas para refletir o estado atual.

## Objectives

- Repositório `go-control-erp/` bootstrapped com estrutura aprovada e CI verde
- Multi-tenancy com **django-tenants** (schema PostgreSQL por Conta) como camada primária de isolamento
- **Unified User System (ZOHO model)** em `apps.platform`: `User` + `Conta` (TenantMixin) + `Domain` + `Membership` + `Modulo` + `ContaModulo` + `Papel`
- JWT autenticado com claim `ctx` (`{type, conta_id, schema, permissions}`) e validação de `token_version` para revogação global/granular
- Apps independentes `apps.pessoas` e `apps.produtos` (cada um é um `Modulo` próprio no catálogo, ativável por Conta), cobrindo Pessoas (com endereços/contatos/grupos) e Produtos com `empresa_id` (Matriz/Filiais) e soft delete
- API REST DRF autenticada via JWT com isolamento de schema (django-tenants) + filtro intra-Conta por `empresa_id`
- Proxies CEP e CNPJ funcionando com fallback entre 2 providers cada e cache no banco
- Frontend React + PrimeReact com módulos `pessoas` e `produtos` (lista + form) consumindo a API
- Cobertura de testes ≥ 80% nos services dos apps `pessoas` e `produtos` e nos proxies

## Guardrails

### Must Have

- Estrutura de pastas exata: `backend/apps/{platform,core,empresas,accounts,pessoas,produtos,integrations/{cep,cnpj}}/` e `frontend/src/modules/{pessoas,produtos}/`
- `apps.pessoas` e `apps.produtos` são **apps Django completamente independentes** — não são sub-módulos de um namespace `cadastros`. Cada um tem entrada própria em `INSTALLED_APPS`, suas próprias migrations e fixtures, e seu próprio `Modulo` no catálogo (`erp.pessoas`, `erp.produtos`).
- **Multi-tenancy primária via django-tenants:** `Conta(TenantMixin)` cria schema PostgreSQL `tenant_{cnpj_14_digitos}`; `Domain(DomainMixin)` mapeia subdomain → Conta. SHARED_APPS: `apps.platform`, `apps.core`, Django contrib, DRF. TENANT_APPS: `apps.empresas`, `apps.accounts`, `apps.pessoas`, `apps.produtos`.
- **`TenantMainMiddleware` é o PRIMEIRO middleware** — roteia requests por hostname para o schema correto antes de qualquer outra lógica.
- **`EmpresaContextMiddleware` vem DEPOIS do Tenant** — injeta `request.empresa_id` (Matriz/Filial) a partir do JWT, dentro do schema já roteado.
- `AUTH_USER_MODEL = 'platform.User'` (em `apps.platform`, SHARED_APP) — User é global à plataforma; pertence a N Contas via `Membership`.
- `empresa_id` em **todas** as tabelas de domínio DENTRO do schema da Conta (distingue Matriz vs Filiais intra-Conta). Catálogos globais sem `empresa_id`: `estado`, `cidade`, `cep_cache` (em SHARED_APPS); catálogos por módulo (sem `empresa_id`, mas dentro do schema): `tipo_cliente`, `categoria_cliente`, `unidade_medida`, etc.
- JWT com claim `ctx`: `{type: "account", conta_id, schema, permissions}` + `token_version`. `TokenVersionJWTAuthentication` valida `token_version` contra `user.token_version` (default 0 para tokens legados sem a claim). Login automático em `ctx.type=account` quando user tem exatamente 1 Membership ativa.
- Manutenção dois níveis: global via `PlatformFlag` + `INCR platform:token_version` no Redis (invalida todos os tokens); por módulo via `Modulo.em_manutencao=True` (não invalida tokens, só bloqueia o módulo).
- Soft delete via Mixin (`deleted_at`) aplicado por Manager customizado — nunca via DELETE físico
- ORM `EmpresaQuerySet` filtra automaticamente todos os models que herdam de `EmpresaScopedModel` por `empresa_id` (intra-schema)
- TDD: testes escritos por @grid-tester antes da implementação por @bolt-executor
- Proxies via interface `Protocol` + lista de providers + estratégia de fallback testada com mocks
- `docs/agent-instructions.md` + `docs/coding-standards.md` versionados
- CI no GitHub Actions: lint (`ruff` + `eslint`), type check (`mypy` + `tsc`), tests (`pytest` + `vitest`), coverage gate ≥ 80%
- Linguagem pt-BR em mensagens de erro, validações e UI
- `.env.example` documentando todas as variáveis (DB, Redis, JWT secret, provider URLs)

### Must NOT Have

- Migração de dados do legado (qualquer tipo)
- Outros módulos (financeiro, vendas, estoque, produção, expedição, CRM, etc.)
- Workflow data-driven (estados/transições) — nenhuma entidade do piloto precisa
- Notificações (Telegram, e-mail, WhatsApp)
- Multi-banco por CNPJ (piloto roda em banco único)
- Audit log universal (entra em MIG-02 com accounts)
- Endpoints públicos sem autenticação (exceto `POST /api/v1/auth/token/`)
- Hard-coded secrets no código ou no `agent-instructions.md`
- Chamada direta a APIs externas fora do proxy
- Lógica de negócio em `views.py` (deve ficar em `services/`)

## Task Flow

```
Step 1: Bootstrap repo + CI + auth + EmpresaScopedModel ✅ CONCLUÍDO
   ↓
Step 1b: django-tenants + Unified User System + JWT ctx ✅ CONCLUÍDO
   ↓
Step 2: apps.pessoas + apps.produtos (apps independentes — schemas, models, fixtures)
   ↓
Step 3: Proxies CEP + CNPJ (interfaces + providers + fallback + cache)  ──┐
   ↓                                                                       │
Step 4: API REST (services + selectors + serializers + views + tests)  ◄──┘
   ↓
Step 5: Frontend React (módulos pessoas + produtos com PrimeReact)
   ↓
Step 6: Smoke test manual + docs + CI verde + handoff Oath
```

## Detailed TODOs

### Step 1 — Bootstrap do repositório `go-control-erp` + accounts + multi-empresa ✅ CONCLUÍDO

> **Status: CONCLUÍDO** (com divergências da spec original — ver Step 1b abaixo). O bootstrap inicial foi feito conforme planejado, mas durante a execução ficou claro que o modelo de tenant precisava ser mais robusto. Decisões D10-D15 e D19 foram tomadas em conjunto e materializadas no Step 1b: o User foi movido de `apps.accounts.User` para `apps.platform.User`, `empresa_atual_id` foi removido do User (sua função foi assumida pelo claim `ctx` do JWT + django-tenants), e `threading.local()` deixou de ser usado para roteamento de tenant — `TenantMainMiddleware` (django-tenants) faz o roteamento por schema PostgreSQL.

- **What (executado):**
  - Repo `go-control-erp/` em `/home/evonexus/evo-projects/go-control-erp/` com `backend/` (Django 5) e `frontend/` (Vite + React 18 + TS) ✅
  - `docker-compose.yml` com PostgreSQL 16 + Redis 7 ✅
  - `.env.example` com `DATABASE_URL`, `REDIS_URL`, `JWT_SIGNING_KEY`, `VIACEP_BASE_URL`, `BRASILAPI_BASE_URL`, `RECEITAWS_BASE_URL` ✅
  - `apps.empresas.Empresa` permanece como TENANT_APP — distingue Matriz vs Filiais DENTRO do schema da Conta ✅
  - `apps.core`: `TimestampMixin`, `SoftDeleteMixin` (com `SoftDeleteManager`), `EmpresaScopedModel` (com `EmpresaQuerySet` que injeta filtro por `empresa_id`) ✅
  - `apps.core.middleware`: `EmpresaContextMiddleware` (intra-schema; injeta `empresa_id` por contexto após o `TenantMainMiddleware`) ✅
  - JWT auth via `djangorestframework-simplejwt` (depois substituído/estendido por `TokenVersionJWTAuthentication` em Step 1b) ✅
  - GitHub Actions: workflow `ci.yml` com lint/typecheck/tests + coverage gate ≥ 80% ✅
  - `docs/agent-instructions.md` + `docs/coding-standards.md` (esqueletos) ✅
  - README com `make setup`, `make backend`, `make frontend`, `make test` ✅
- **Divergências da spec original:**
  - **Custom user model NÃO ficou em `apps.accounts.User`** — foi movido para `apps.platform.User` (SHARED_APP) durante o Step 1b. Justificativa: `User` é global à plataforma, não pertence a uma Conta única.
  - **`empresa_atual_id` foi removido do User** — sua função foi substituída pelo claim `ctx.conta_id` do JWT, que é resolvido a cada request pelo `TenantMainMiddleware`.
  - **`threading.local()` deixou de ser usado para roteamento de tenant** — `django-tenants` faz isso de forma nativa via schema PostgreSQL. Permanece apenas o uso intra-schema para `empresa_id` (Matriz/Filiais), via `EmpresaContextMiddleware`.
- **Owner agent:** @bolt-executor (implementação) + @grid-tester (testes) + @apex-architect (decisões D10-D15)
- **Acceptance criteria atendidos:**
  - `docker-compose up` sobe PostgreSQL + Redis sem erro ✅
  - `python manage.py migrate_schemas` aplica migrations no schema `public` (SHARED_APPS) ✅
  - JWT funcional: token + refresh + endpoint protegido recusa sem token ✅
  - CI passou no primeiro push ✅
- **Estimated complexity:** HIGH (decisões fundamentais; o escopo cresceu para o Step 1b)

### Step 1b — django-tenants + Unified User System + JWT com claim `ctx` ✅ CONCLUÍDO

> **Status: CONCLUÍDO** — 45 testes passando, 3 marcados como `xfail` (isolamento cross-schema, requerem ambiente PostgreSQL com tenant_test settings).

- **Contexto:** durante o Step 1, ficou claro que o modelo single-database com `empresa_atual_id` era insuficiente para garantir isolamento forte de dados entre clientes-empresa. As decisões D10-D15 e D19 foram tomadas em conjunto e introduziram **django-tenants (schema-per-Conta)** como camada primária + **Unified User System (modelo ZOHO)** + **JWT com claim `ctx`** + **manutenção em dois níveis (global/módulo)**.
- **What (executado):**
  - **`apps.platform`** (SHARED_APP, schema `public`):
    - `User`: id (UUID), email, nome, is_active, is_platform_staff, **token_version** (sem `empresa_atual` FK)
    - `Conta(TenantMixin)`: id (UUID), nome, **cnpj_matriz** (14 dígitos), slug, **schema_name** (`tenant_{cnpj_14}`), ativo
    - `Domain(DomainMixin)`: mapeia subdomain → Conta
    - `Membership(User ↔ Conta)`: status (`active`/`invited`/`suspended`), `is_account_owner`
    - `Modulo`: catálogo de módulos; `code` (ex: `erp.pessoas`), `surface`, `em_manutencao`, `nome`
    - `ContaModulo`: módulos ativos por Conta; `params_overrides` (JSONField validado por Pydantic v2)
    - `Papel`: bundle de permissões por módulo
    - `MembershipPapel`: papéis do usuário dentro de uma Conta
    - `MigrationRun`: auditoria de migrations por schema
    - `PlatformFlag`: flags globais (e.g., manutenção global)
  - **`apps.core.authentication.TokenVersionJWTAuthentication`**: valida `token_version` contra `user.token_version` (default 0 para tokens legados sem a claim).
  - **JWT com claim `ctx`**:
    ```json
    {
      "sub": "uuid",
      "ctx": {"type": "account", "conta_id": "uuid", "schema": "tenant_12345678000195", "permissions": []},
      "token_version": 0
    }
    ```
    Login automático em `ctx.type=account` quando user tem exatamente 1 Membership ativa.
  - **`config/settings/base.py`**:
    - `SHARED_APPS = ['django_tenants', 'apps.platform', 'apps.core', 'django.contrib.*', 'rest_framework', ...]`
    - `TENANT_APPS = ['apps.empresas', 'apps.accounts', ...]` (futuramente: `apps.pessoas`, `apps.produtos`)
    - `MIDDLEWARE` começa com `django_tenants.middleware.main.TenantMainMiddleware`, seguido por `EmpresaContextMiddleware`
    - `AUTH_USER_MODEL = 'platform.User'`
    - `DATABASE_ROUTERS = ['django_tenants.routers.TenantSyncRouter']`
  - **Manutenção dois níveis**:
    - Global: `PlatformFlag` + `INCR platform:token_version` no Redis → invalida todos os tokens
    - Por módulo: `Modulo.em_manutencao=True` → bloqueia acesso ao módulo (não invalida tokens)
  - **Testes** em `tests/platform/`: 45 pass cobrindo model, JWT, membership, módulo, conta. 3 `xfail` para isolamento cross-schema.
- **Acceptance criteria atendidos:**
  - `python manage.py migrate_schemas --shared` aplica migrations dos SHARED_APPS no `public` ✅
  - Criar Conta → cria schema `tenant_{cnpj}` automaticamente via signal ✅
  - JWT emitido com claim `ctx` quando user tem 1 Membership ativa ✅
  - `INCR platform:token_version` invalida todos os tokens (próxima request retorna 401) ✅
  - `Modulo.em_manutencao=True` bloqueia o módulo sem invalidar tokens ✅
  - Cobertura ≥ 80% no `apps.platform` ✅
- **Divergências do plano original:**
  - Escopo bem maior do que o esperado para um "passo de bootstrap": o Unified User System + django-tenants + JWT ctx + token_version são decisões arquiteturais profundas (registradas como D10-D15 e D19).
  - `apps.accounts` foi reduzido a um TENANT_APP que hospeda apenas tabelas de relacionamento usuário↔conta dentro do schema (papéis intra-Conta, etc.). O `User` global vive em `apps.platform`.
  - 3 testes de isolamento cross-schema marcados como `xfail` — requerem ambiente PostgreSQL com `tenant_test` settings; serão reabilitados quando o pipeline de CI rodar com Postgres dedicado para tenant tests.
- **Owner agent:** @apex-architect (decisões D10-D15, D19) + @bolt-executor (implementação) + @grid-tester (45 testes) + @raven-critic (challenge da spec antes da execução)
- **Estimated complexity:** VERY HIGH (multi-tenancy + auth + manutenção em dois níveis em um único bloco)

### Step 2 — `apps.pessoas` + `apps.produtos` (apps independentes — schemas, models, fixtures)

> **Correção fundamental do plano original:** o plano descrevia `apps.cadastros` com sub-módulos `pessoas/` e `produtos/`. Decisão tomada (e confirmada pelo usuário): `apps.pessoas` e `apps.produtos` são **apps Django completamente independentes**, registrados separadamente em `INSTALLED_APPS`/`TENANT_APPS`. Cada um é um `Modulo` próprio no catálogo (`erp.pessoas`, `erp.produtos`), com sua entrada em `ContaModulo`, podendo ter maintenance mode independente e ser ativado/desativado por Conta.

- **What:**
  - **Criar `apps.pessoas`** como Django app independente, registrado em `TENANT_APPS`:
    - Models (herdam de `EmpresaScopedModel + SoftDeleteMixin + AuditMixin`):
      - `Pessoa` (empresa_id, tipo_cliente_id, categoria_cliente_id?, nome, documento, fone, email, obs, responsavel_finan_id?)
      - `PessoaContato` (pessoa_id, nome, email, telefone, obs)
      - `PessoaEndereco` (pessoa_id, cidade_id, nome, principal, cep, rua, numero, bairro, complemento)
      - `PessoaGrupo` (pessoa_id, grupo_pessoa_id) — M2M associativo
    - **Catálogos do módulo Pessoas** (dentro do schema da Conta, herdam de `TimestampMixin` apenas):
      - `TipoCliente` (id, nome) — descartar `sigla` (OQ3)
      - `CategoriaCliente` (id, nome)
      - `GrupoPessoa` (id, nome) — usuário-criável; pode ter `empresa_id` se vier necessidade futura, mas inicialmente sem
    - Fixtures em `apps/pessoas/fixtures/`:
      - `tipos_cliente.json` — Cliente PF, Cliente PJ, Fornecedor, Transportadora, Cliente+Fornecedor
      - `categorias_cliente.json` — PF, PJ, MEI

  - **Criar `apps.produtos`** como Django app independente, registrado em `TENANT_APPS`:
    - Models (herdam de `EmpresaScopedModel + SoftDeleteMixin + AuditMixin`):
      - `Produto` (empresa_id, tipo_produto_id, familia_produto_id, fornecedor_id?→`apps.pessoas.Pessoa`, unidade_medida_id, fabricante_id?, nome, cod_barras, preco_venda, preco_custo, peso_liquido, peso_bruto, largura, altura, volume, ativo, foto, data_ultimo_reajuste_preco, obs)
        - Removidos vs legado: `qtde_estoque`, `estoque_minimo`, `estoque_maximo` (vão para módulo `estoque` em MIG-04)
    - **Catálogos do módulo Produtos** (dentro do schema, herdam só de `TimestampMixin`):
      - `UnidadeMedida` (id, nome, sigla, fraciona)
      - `FamiliaProduto` (id, nome)
      - `Fabricante` (id, nome)
      - `TipoProduto` (id, nome)
    - Fixtures em `apps/produtos/fixtures/`:
      - `unidades_medida.json` — UN, KG, L, M, M2, M3, CX, PCT

  - **Catálogos globais** (em `apps.platform.catalogs` ou `apps.core` — **SHARED_APP, schema `public`**):
    - `Estado` (id, nome, sigla, codigo_ibge) — herdam de `TimestampMixin`
    - `Cidade` (id, estado_id FK, nome, codigo_ibge)
    - `CepCache` (cep, rua, bairro, cidade_id?, estado_id?, codigo_ibge, uf, created_at)
    - Fixtures em `apps/platform/fixtures/` (ou `apps/core/fixtures/`):
      - `estados.json` — 27 UFs com IBGE
      - `cidades_top200.json` — 200 maiores cidades brasileiras (carga inicial)

  - **Registro em `INSTALLED_APPS`/`TENANT_APPS`** (`config/settings/base.py`):
    ```python
    SHARED_APPS = [
        'django_tenants',
        'apps.platform',   # User, Conta, Domain, Modulo, Papel, catalogs (Estado, Cidade, CepCache)
        'apps.core',       # Mixins, EmpresaScopedModel, middleware
        'django.contrib.*', 'rest_framework', ...
    ]
    TENANT_APPS = [
        'apps.empresas',   # Matriz/Filiais (intra-Conta)
        'apps.accounts',   # Papéis intra-Conta
        'apps.pessoas',    # entrada própria — Modulo erp.pessoas
        'apps.produtos',   # entrada própria — Modulo erp.produtos
    ]
    INSTALLED_APPS = SHARED_APPS + [app for app in TENANT_APPS if app not in SHARED_APPS]
    ```

  - **Seed do catálogo `Modulo`** (em SHARED, no schema `public`) via data migration ou comando `seed_modulos`:
    - `Modulo(code='erp.pessoas', nome='Pessoas', surface='erp', em_manutencao=False)` — **ativo por padrão** (toda nova Conta recebe `ContaModulo` para `erp.pessoas` automaticamente)
    - `Modulo(code='erp.produtos', nome='Produtos', surface='erp', em_manutencao=False)` — **opt-in** (Conta precisa explicitamente ativar via `ContaModulo`)

  - **Constraints e indexes:**
    - `Pessoa.documento` único por empresa dentro do schema da Conta (`UniqueConstraint(fields=['empresa', 'documento'], condition=Q(documento__isnull=False))`)
    - `Produto.cod_barras` único por empresa dentro do schema (`UniqueConstraint(fields=['empresa', 'cod_barras'], condition=Q(cod_barras__isnull=False))`)
    - Index em `(empresa_id, deleted_at)` em todos os models de domínio
    - Index em `(cep, created_at)` em `CepCache` (schema `public`)

  - **Migrations**:
    - Geradas separadamente: `python manage.py makemigrations pessoas` e `python manage.py makemigrations produtos`
    - Aplicadas via `python manage.py migrate_schemas` (django-tenants — aplica em todos os schemas tenant ou no `public` conforme o app)

- **Owner agent:** @grid-tester (testes de model: validações, constraints, soft delete, isolamento cross-schema) → @bolt-executor (implementação dos models + migrations + fixtures + seeds de Modulo)

- **Acceptance criteria:**
  - `python manage.py migrate_schemas` aplica todas as migrations sem erro em banco vazio (SHARED no `public`, TENANT_APPS em cada schema tenant)
  - `python manage.py loaddata estados cidades_top200` popula catálogos globais no `public`
  - `python manage.py loaddata --schema=tenant_X tipos_cliente categorias_cliente unidades_medida` popula catálogos do módulo dentro do schema da Conta
  - `python manage.py seed_modulos` cria entradas `erp.pessoas` (ativa por padrão) e `erp.produtos` (opt-in) no catálogo `Modulo`
  - Testes de model passam:
    - Criar Pessoa em Conta1 (schema A) com documento X, criar Pessoa em Conta2 (schema B) com documento X → ambas convivem (schemas isolados) ✓
    - Dentro do mesmo schema: criar Pessoa na Empresa-Matriz com documento X e em Filial1 com documento X → ambas convivem (constraint é por `empresa_id` intra-schema) ✓
    - Criar duas Pessoas com mesmo documento na mesma empresa do mesmo schema → IntegrityError ✓
  - Soft delete: `pessoa.delete()` seta `deleted_at` e a query padrão não retorna mais a pessoa, mas `Pessoa.all_objects.filter(deleted_at__isnull=False)` ainda mostra
  - `erp.produtos` desativado em uma Conta → middleware/serviço de catálogo bloqueia acesso ao app
  - Cobertura ≥ 80% nos testes de model

- **Estimated complexity:** MEDIUM-HIGH (dois apps independentes + catálogos em SHARED + seed de Modulo + isolamento cross-schema)

### Step 3 — Proxies CEP + CNPJ com fallback e cache

- **What:**
  - `apps/integrations/cep/`:
    - `interface.py` — `CepProvider(Protocol)` com `lookup(cep: str) -> CepResult | None`
    - `providers/viacep.py` — implementa contra https://viacep.com.br/ws/{cep}/json/
    - `providers/brasilapi.py` — implementa contra https://brasilapi.com.br/api/cep/v2/{cep}
    - `proxy.py` — `CepProxy` com lista ordenada de providers, estratégia "tenta sequencial; primeiro que retornar resultado válido vence; persiste no `CepCache`"
    - `services.py` — `lookup_cep(cep)` consulta `CepCache` primeiro (TTL 30 dias), depois proxy se miss
    - `views.py` — `GET /api/v1/integrations/cep/{cep}/` (autenticado)
  - `apps/integrations/cnpj/`:
    - `interface.py` — `CnpjProvider(Protocol)` com `lookup(cnpj: str) -> CnpjResult | None`
    - `providers/receitaws.py` — implementa contra https://receitaws.com.br/v1/cnpj/{cnpj}
    - `providers/brasilapi.py` — implementa contra https://brasilapi.com.br/api/cnpj/v1/{cnpj}
    - `proxy.py` — fallback sequencial; respeita rate-limit do ReceitaWS (token bucket simples em Redis)
    - `services.py` — `lookup_cnpj(cnpj)` (sem cache em DB no piloto; cache em Redis com TTL 7 dias)
    - `views.py` — `GET /api/v1/integrations/cnpj/{cnpj}/` (autenticado)
  - Validação: `cep` e `cnpj` normalizados (remove pontuação) antes de buscar
  - Timeouts: 5s por provider; circuit breaker simples (3 falhas seguidas → ignora provider por 5 min)
  - Logs estruturados (provider, cep/cnpj, status, latência) via `structlog`
- **Owner agent:** @grid-tester (testes com mocks de provider — sucesso, timeout, 5xx, 429, fallback, cache hit) → @bolt-executor (implementação)
- **Acceptance criteria:**
  - Teste unitário: ViaCEP retorna 5xx → BrasilAPI é chamado → resultado retornado
  - Teste unitário: cache hit → nenhum provider é chamado
  - Teste unitário: ReceitaWS retorna 429 → BrasilAPI é chamado
  - Teste de integração (com `responses` mockando HTTP): endpoint `GET /api/v1/integrations/cep/01310-100/` autenticado retorna 200 com payload válido
  - Cobertura ≥ 90% nos proxies (são pequenos e críticos)
  - Nenhuma chamada real a APIs externas nos testes (tudo mockado)
- **Estimated complexity:** MEDIUM

### Step 4 — API REST de Pessoas e Produtos (DRF)

> **Decisão de URL:** os endpoints ficam sob `/api/v1/pessoas/` e `/api/v1/produtos/` (refletindo a separação em apps independentes — `erp.pessoas` e `erp.produtos` são módulos distintos no catálogo). Não usar mais o prefixo `/api/v1/cadastros/`.

- **What:**
  - Para cada entidade de domínio (Pessoa, Produto) e cada catálogo, seguir o padrão de módulo Django **dentro do app correspondente** (`apps/pessoas/` e `apps/produtos/`, cada um auto-contido):
    - `services/<entidade>_service.py` — operações de escrita com regra de negócio (criar, atualizar, soft-delete, gerar cod_barras, etc.)
    - `selectors/<entidade>_selectors.py` — operações de leitura (listagens com filtros, busca por id)
    - `serializers/<entidade>_serializer.py` — DRF serializers com validação (CPF/CNPJ format, CEP format, etc.)
    - `views/<entidade>_view.py` — DRF `ModelViewSet` ou `APIView` que delega para services/selectors (zero lógica)
    - `permissions.py` — `IsAuthenticated` + `HasContaCtx` (garante claim `ctx.conta_id` válido) + `IsInEmpresa` (intra-schema; `obj.empresa_id == request.empresa_id`) + `HasModuloAtivo` (verifica `ContaModulo` do módulo correspondente)
    - `urls.py` — rotas REST padrão
  - Endpoints do módulo Pessoas (sob `/api/v1/pessoas/`):
    - `GET/POST /pessoas/`
    - `GET/PATCH/DELETE /pessoas/{id}/`
    - `GET /pessoas/{id}/contatos/`, `POST /pessoas/{id}/contatos/`
    - `GET /pessoas/{id}/enderecos/`, `POST /pessoas/{id}/enderecos/`
    - `GET /catalogos/tipos-cliente/`, `GET /catalogos/categorias-cliente/`, `GET /catalogos/grupos-pessoa/`
  - Endpoints do módulo Produtos (sob `/api/v1/produtos/`):
    - `GET/POST /produtos/`
    - `GET/PATCH/DELETE /produtos/{id}/`
    - `POST /produtos/{id}/gerar-codigo-barras/` — gera EAN-13 único na empresa via `python-barcode`
    - `GET /catalogos/unidades-medida/`, `GET /catalogos/familias-produto/`, `GET /catalogos/fabricantes/`, `GET /catalogos/tipos-produto/`
  - Endpoints de catálogos globais (sob `/api/v1/platform/` ou `/api/v1/core/` — SHARED, schema `public`):
    - `GET /catalogos/estados/`
    - `GET /catalogos/cidades/?estado_id=X`
  - Validações no serializer:
    - CPF: validador Python Brasil (`validate_cpf`)
    - CNPJ: validador (`validate_cnpj`)
    - CEP: regex `^\d{5}-?\d{3}$`
    - Telefone: regex tolerante (10-11 dígitos)
  - Filtros e busca via `django-filter`:
    - Pessoa: search por `nome` e `documento`; filter por `tipo_cliente_id`
    - Produto: search por `nome` e `cod_barras`; filter por `tipo_produto_id`, `familia_produto_id`, `fabricante_id`
  - Paginação DRF padrão: 25 por página
  - OpenAPI spec via `drf-spectacular`: `GET /api/v1/schema/` + Swagger UI em `/api/v1/docs/`
- **Owner agent:** @grid-tester (testes da API: CRUD, isolamento cross-schema via django-tenants, isolamento intra-schema por `empresa_id`, soft delete, validações, filtros, bloqueio quando módulo desativado) → @bolt-executor (implementação)
- **Acceptance criteria:**
  - Todos os critérios de aceitação CA-02, CA-03, CA-04, CA-05, CA-06, CA-07, CA-08, CA-09 do PRD passam em testes de integração
  - Cobertura ≥ 80% nos services e selectors de cada app
  - Swagger UI lista todos os endpoints
  - `pytest apps/pessoas apps/produtos` verde
  - Request a `/api/v1/produtos/` por uma Conta sem `ContaModulo(modulo='erp.produtos', ativo=True)` retorna 403/409 com mensagem em pt-BR
- **Estimated complexity:** HIGH (mais entidades, mais testes, mais endpoints, mais camadas de permissão)

### Step 5 — Frontend React: módulos pessoas + produtos

- **What:**
  - Bootstrap do `frontend/`:
    - Vite + React 18 + TypeScript + PrimeReact + Tailwind + TanStack Query + React Hook Form + Zod
    - `src/lib/api.ts` — cliente Axios com interceptor que injeta JWT do localStorage
    - `src/lib/auth.ts` — login, logout, refresh token, contexto de usuário/empresa
    - `src/components/Layout.tsx` — sidebar (PrimeReact `PanelMenu`), topbar com seletor de empresa
    - Tema PrimeReact (lara-light-blue) + Tailwind preset documentado em `coding-standards.md`
  - Padrão de módulo (`src/modules/{pessoas,produtos}/` — cada um é um módulo independente, espelhando os apps do backend):
    - `pages/<Entidade>ListPage.tsx` — lista com PrimeReact `DataTable`, filtros, paginação server-side, botões "Novo", "Editar", "Excluir"
    - `pages/<Entidade>FormPage.tsx` — form com React Hook Form + Zod
    - `components/<Entidade>FormFields.tsx` — fields reutilizáveis
    - `services/<entidade>.service.ts` — funções tipadas que chamam a API (`listPessoas`, `createPessoa`, etc.)
    - `hooks/use<Entidade>.ts` — hooks TanStack Query (`usePessoasList`, `usePessoaCreate`, etc.)
    - `types/<entidade>.types.ts` — interfaces TS
    - `routes.tsx` — rotas do módulo
  - Telas de Pessoa:
    - `PessoaListPage` com filtros (tipo_cliente, busca por nome/documento)
    - `PessoaFormPage` com:
      - Aba "Dados gerais": nome, documento (CPF/CNPJ com máscara), fone, email, tipo_cliente, categoria_cliente
      - Botão "Buscar dados (CNPJ)" quando tipo é PJ → chama `GET /api/v1/integrations/cnpj/{cnpj}/` → autopreenche
      - Aba "Endereços": lista + modal de cadastro com CEP autopreenchimento ao blur
      - Aba "Contatos": lista + modal de cadastro
  - Telas de Produto:
    - `ProdutoListPage` com filtros (tipo_produto, familia_produto, fabricante, busca)
    - `ProdutoFormPage` com:
      - Dados gerais: nome, tipo_produto, familia_produto, fabricante (autocomplete), unidade_medida, fornecedor (autocomplete em Pessoa do tipo Fornecedor)
      - Preços: preco_venda, preco_custo
      - Dimensões: peso_liquido, peso_bruto, largura, altura, volume
      - Código de barras: campo + botão "Gerar" → POST endpoint
      - Foto: upload simples (multipart)
  - Validação client-side com Zod alinhada com a do backend (CPF/CNPJ/CEP)
  - Mensagens de erro em pt-BR
  - Testes (`vitest` + `@testing-library/react`):
    - Form de Pessoa: digita CNPJ válido → mock chamada CNPJ → campos preenchidos
    - Form de Pessoa: digita CEP → mock chamada CEP → endereço preenchido
    - Lista de Produto: filtros funcionam
- **Owner agent:** @canvas-designer (componentes UI + tema) + @grid-tester (testes vitest) → @bolt-executor (implementação)
- **Acceptance criteria:**
  - `npm run dev` sobe frontend em :5173 sem erro
  - Login funcional → redirect para `/pessoas` (módulo padrão; `/produtos` só aparece no menu se `ContaModulo` estiver ativo)
  - CA-02, CA-03, CA-06, CA-07 do PRD passam manualmente
  - `npm run test` verde com cobertura ≥ 70% (frontend tem barra mais baixa que backend)
  - `npm run typecheck` verde (zero erros TS)
  - `npm run lint` verde
- **Estimated complexity:** HIGH (volume de telas + integração ponta a ponta)

### Step 6 — Smoke test, docs finais, CI verde, handoff

- **What:**
  - Atualizar `docs/agent-instructions.md` com:
    - Arquitetura multi-tenancy (django-tenants schema-per-Conta + intra-schema empresa_id)
    - Unified User System (modelo ZOHO): User global + Conta + Membership + Modulo + Papel
    - JWT com claim `ctx` e `token_version` (revogação global e granular)
    - Manutenção em dois níveis (PlatformFlag global vs. `Modulo.em_manutencao` por módulo)
    - Padrão de app Django independente consolidado (com exemplos `pessoas` e `produtos`)
    - Padrão de módulo React consolidado
    - Como criar um novo módulo de domínio (checklist: app independente + Modulo seed + ContaModulo + frontend module)
    - Como criar um novo proxy de integração (checklist)
    - Como rodar testes localmente (incluindo `tenant_test` settings para isolamento cross-schema)
    - Convenções: pt-BR, soft delete, multi-tenancy + multi-empresa intra-Conta, sem secrets em código
  - Atualizar `docs/coding-standards.md` com:
    - Lint config (ruff/eslint), formatter (black/prettier), type check (mypy/tsc)
    - Convenção de commits (Conventional Commits)
    - Estrutura de imports
    - Padrão de logs (structlog backend, console.log proibido em produção frontend)
    - Tema PrimeReact + variáveis Tailwind base
  - Smoke test manual adaptado à nova arquitetura (CA-13 do PRD):
    1. `docker-compose up`
    2. `python manage.py migrate_schemas --shared` (SHARED no `public`)
    3. `python manage.py loaddata estados cidades_top200` (catálogos globais)
    4. `python manage.py seed_modulos` (cria `erp.pessoas` ativo por padrão e `erp.produtos` opt-in)
    5. `python manage.py create_superuser_platform` (cria User global em `apps.platform.User`)
    6. `python manage.py create_demo_conta --cnpj 33000167000101 --slug demo` (cria Conta + Domain + schema `tenant_33000167000101`; ativa `erp.pessoas` automaticamente; ativa `erp.produtos` para o demo)
    7. Frontend: login (com host `demo.localhost`) → token contém `ctx.conta_id` + `schema=tenant_33000167000101` → redirect para `/pessoas`
    8. Cadastrar Cliente PJ "Empresa Demo" com CNPJ válido (autopreenche)
    9. Cadastrar endereço com CEP "01310-100" (autopreenche)
    10. Cadastrar Produto "Saco de ração 60kg" com código de barras gerado
    11. Verificar no PostgreSQL: `\dt tenant_33000167000101.*` lista tabelas no schema da Conta; `SELECT empresa_id FROM tenant_33000167000101.pessoas_pessoa` mostra a Empresa-Matriz correta
  - Garantir CI verde: lint + typecheck + tests + coverage ≥ 80% backend, ≥ 70% frontend
  - Reabilitar os 3 testes `xfail` do Step 1b (isolamento cross-schema) com Postgres dedicado em CI
  - Tag `v0.1.0-pilot` no git
  - Abrir tickets sucessores no EvoNexus:
    - MIG-02 (Financeiro)
    - MIG-03 (Vendas + Workflow data-driven)
    - MIG-04 (Estoque)
  - Handoff para @oath-verifier com checklist de critérios de aceitação
- **Owner agent:** @bolt-executor (docs + tag) + @oath-verifier (verificação) + @compass-planner (abrir tickets sucessores)
- **Acceptance criteria:**
  - Eduardo executa o smoke test sem encontrar bug bloqueante
  - CI verde em main, incluindo os 3 testes de isolamento cross-schema reabilitados
  - `agent-instructions.md` e `coding-standards.md` revisados e aprovados (cobrindo django-tenants + Unified User System)
  - Tag `v0.1.0-pilot` criada
  - Tickets MIG-02, MIG-03, MIG-04 abertos com link para o feature folder
  - @oath-verifier produz `[C]verification-migracao-minierp-adianti-python-react.md` com PASS em todos os CA do PRD
- **Estimated complexity:** MEDIUM-HIGH (smoke test agora atravessa múltiplas camadas: SHARED → schema tenant → empresa intra-schema)

## Success Criteria

- [x] Repositório `go-control-erp/` inicializado, com CI verde em main ✅ (Step 1)
- [x] Multi-tenancy com django-tenants + Unified User System + JWT `ctx` ✅ (Step 1b — 45 pass, 3 xfail)
- [x] Apps independentes `apps.pessoas` e `apps.produtos` com models, migrations, fixtures e seeds ✅ (Step 2)
- [x] Proxies CEP e CNPJ funcionando com fallback e cache — 36/36 testes GREEN ✅ (Step 3)
- [ ] API REST de Pessoas e Produtos com CRUD, permissões, filtros e validações (Step 4)
- [ ] Frontend React + PrimeReact com módulos `pessoas` e `produtos` (lista + form) consumindo a API
- [ ] CA-01 a CA-13 do PRD todos verdes
- [ ] Cobertura ≥ 80% backend, ≥ 70% frontend
- [ ] `agent-instructions.md` + `coding-standards.md` aprovados (cobrindo django-tenants + Unified User System)
- [ ] Smoke test manual aprovado por Eduardo
- [ ] Tag `v0.1.0-pilot`
- [ ] Tickets MIG-02..04 abertos
- [ ] Verificação @oath-verifier: PASS

## Open Questions

Todas as OQs originais foram resolvidas durante a execução dos Steps 1 e 1b. Mantidas aqui para histórico:

- [x] **OQ1** — Modelo de tenant: `Empresa.id` UUID v4 ou autoincremento? ✅ **Resolvido: UUID v4** (aplicado a `User`, `Conta`, `Empresa`, `Pessoa`, `Produto` e demais entidades de domínio).
- [x] **OQ2** — Custom user model: `apps.accounts.User` desde Step 1? ✅ **Resolvido: SIM, mas o User foi reposicionado em `apps.platform.User`** (SHARED_APP) durante Step 1b. `AUTH_USER_MODEL = 'platform.User'`.
- [x] **OQ3** — `tipo_cliente.sigla` (char(2)): manter ou descartar? ✅ **Resolvido: descartar** (não está nos models do Step 2).
- [x] **OQ4** — Catálogos globais (`estado`, `cidade`, `unidade_medida`): adicionar `created_at`/`updated_at`? ✅ **Resolvido: SIM** (todos os catálogos herdam de `TimestampMixin`).
- [x] **OQ5** — Geração de código de barras: EAN-13? ✅ **Resolvido: EAN-13** via `python-barcode` no endpoint `POST /api/v1/produtos/{id}/gerar-codigo-barras/`.
- [x] **OQ6** — Hash de senha: `argon2`? ✅ **Resolvido: Argon2** em produção; MD5 só em testes via `PASSWORD_HASHERS` específico para `tests`.
- [x] **OQ7** — Repo `go-control-erp/` será criado em qual diretório? ✅ **Resolvido: `/home/evonexus/evo-projects/go-control-erp/`** (seguindo a convenção do CLAUDE.md para projetos custom).
- [x] **OQ8** — Convenção de projeto custom: dados persistentes em `/home/evonexus/evo-projects/go-control-erp/` ou volume Docker? ✅ **Resolvido: volume Docker em dev**; em produção, decisão posterior no momento do deploy.

### Open Questions emergentes (Step 1b → Step 2)

- [x] **OQ9** — Catálogo `GrupoPessoa` deve ter `empresa_id` ou ser global ao schema da Conta? ✅ **Resolvido: global ao schema da Conta** — sem `empresa_id`. Grupos de pessoas são compartilhados entre todas as filiais dentro da Conta.
- [ ] **OQ10** — Reabilitação dos 3 testes `xfail` de isolamento cross-schema: feita no Step 6 ou em ticket separado de infra de CI? — Recomendação Compass: Step 6, junto com o smoke test que já depende de Postgres dedicado.

Estas questões serão consolidadas em `workspace/development/plans/[C]open-questions.md`.

## Handoff

- **Status atual:** Steps 1 e 1b ✅ concluídos. Próximo passo é o Step 2 (apps independentes `pessoas` e `produtos`).
- **Próximo passo imediato → @grid-tester + @bolt-executor:** iniciar o Step 2. Grid escreve testes de model/constraint/isolamento; Bolt implementa os models, fixtures e seed do `Modulo`.
- **Pendência arquitetural → @apex-architect:** atualizar `[C]architecture-migracao-minierp-adianti-python-react.md` (ADR) consolidando D10-D15 e D19 (django-tenants schema-per-Conta, Unified User System, JWT `ctx`, manutenção dois níveis, apps independentes).
- **Após Step 6 → @oath-verifier:** verificar contra os 13 critérios de aceitação do PRD.
- **PRD:** [./[C]prd-migracao-minierp-adianti-python-react.md](./[C]prd-migracao-minierp-adianti-python-react.md)
- **Discovery:** [./[C]discovery-migracao-minierp-adianti-python-react.md](./[C]discovery-migracao-minierp-adianti-python-react.md)
