---
author: claude
agent: apex-architect
type: architecture-decision
date: 2026-05-06
topic: stack-go-control-erp-piloto
status: deprecated
superseded_by: ./[C]architecture-v2-go-control-erp.md
ticket: MIG-01 (ad313e49-c22e-4d52-aaf8-713e21f3fe78)
goal: minierp-01-discovery-classificacao
feature: migracao-minierp-adianti-python-react
prd: ./[C]prd-migracao-minierp-adianti-python-react.md
plan: ./[C]plan-migracao-minierp-adianti-python-react.md
discovery: ./[C]discovery-migracao-minierp-adianti-python-react.md
---

> ⚠️ **DEPRECATED — 2026-05-08**
>
> Este ADR v1 foi **parcialmente supersedido** pelo ADR v2 aprovado em 2026-05-08:
> **`[C]architecture-v2-go-control-erp.md`**
>
> Decisões de **identidade e tenancy** (D10-D19 deste documento, mais D-R01..D-R12 do Redesign)
> foram revisadas. As decisões de **stack foundacional** (D1-D9: Django, DRF, React, UUID PK,
> `EmpresaScopedModel`, soft delete, proxy pattern) permanecem válidas.
>
> **Não use este documento para decisões sobre:**
> - Subdomínio por Conta — `{conta}.gocontrol.com.br` **não existe** (D-R01)
> - Roteamento de schema — use `JWTTenantMiddleware`, não hostname (D-R02)
> - `Conta` como container operacional — é entidade de billing apenas (D-R03)
> - `Membership` como vínculo operacional — use `UserEmpresaVinculo` (D-R06)
> - Frontend monolítico como destino final — alvo são 3 SPAs (D-R10)
> - Login flow — use o fluxo de 3 etapas (D-R09)

# Architecture Decision — Stack do GO Control ERP (Piloto Pessoas + Produtos)

## Summary

O GO Control ERP nasce como repositório novo (`/home/evonexus/evo-projects/go-control-erp/`) sobre Django 5 + DRF + PostgreSQL + Redis no backend e React 18 + TypeScript + Vite + PrimeReact no frontend, com decisões fundacionais bloqueadas no bootstrap: **custom user model em UUID v4 desde a primeira migration**, **middleware `EmpresaContextMiddleware` + `EmpresaScopedModel` mixin** para isolamento multi-empresa automático, **soft delete universal** via `SoftDeleteMixin`, **proxy pattern (Strategy + Fallback)** para integrações externas e **TDD obrigatório** com cobertura mínima ≥ 80% nos services. Estas decisões vinculam todos os módulos sucessores (MIG-02..N) — voltar atrás em qualquer uma delas custa migration de schema e refactor cross-app.

**Emenda v2 (2026-05-06):** Sessão de alinhamento arquitetural adicionou as Decisões 10-15: multi-tenant Alternativa B (schema por Conta, django-tenants), Unified User System no modelo ZOHO (1 User global + Membership + Papel), PgBouncer em session mode, Maintenance Mode em dois níveis, Deploy policy com gate manual via Celery, e validação de `ContaModulo.params_overrides` com Pydantic v2. **A Decisão 11 substitui parcialmente a Decisão 1** — o modelo User não tem mais `empresa_atual` FK; a identity layer migrou para o schema `public` com 6 modelos independentes.

## Context

O legado Adianti/PHP em `/home/evonexus/go_mini_erp_src` é fonte de verdade **funcional** (regras já validadas em produção), não estrutural — os controllers Adianti (223 arquivos) constroem UI server-side e serão descartados. As decisões de stack documentadas no discovery (Q2-Q8) e no PRD (CA-01..CA-13) precisam ser destiladas em **guardrails arquiteturais** que os agentes (Bolt, Grid, Canvas) sigam sem ambiguidade — a alternativa é cada agente interpretar o PRD do seu jeito e produzir N variações de "padrão de módulo".

Decisões transversais que este ADR consolida:

1. Custom User Model + UUID v4 antes da primeira `migrate` *(parcialmente substituído por D11)*
2. Middleware empresa_id + ORM mixin com filtro automático
3. Padrão de módulo Django (`models/serializers/services/selectors/views/urls/permissions/tests`)
4. Padrão de módulo React (`pages/components/services/hooks/types/routes.tsx`)
5. UUID v4 como PK universal
6. Proxy pattern para integrações
7. Soft delete universal com manager filtrado
8. Workflow data-driven cross-módulo
9. `ordem_producao` desacoplada de pedido (mudança de schema vs legado)
10. Multi-tenant Alternativa B: schema por Conta (django-tenants)
11. Unified User System: 1 User global + Membership + Papel (modelo ZOHO)
12. PgBouncer em session mode (incompatibilidade com transaction mode)
13. Maintenance Mode: dois níveis (global + por módulo)
14. Deploy policy: gate manual com Celery migration por schema
15. Validação de `ContaModulo.params_overrides` com Pydantic v2

Sem este ADR, qualquer alternativa (escolher entre `apps.users` ou `apps.accounts`, decidir filtro empresa em cada view, gerar UUID no banco vs. Python, etc.) é um vetor de inconsistência.

---

## Options Considered (consolidação macro)

| Opção macro | Pros | Cons | Notas |
|---|---|---|---|
| **A.** Stack escolhida (Django 5 + DRF + React 18 + PrimeReact + Postgres + Redis) com guardrails rígidos | Estrutura previsível por módulo, custom user trivial, ORM com manager customizável, ecosistema maduro de DRF + simplejwt + django-filter, PrimeReact cobre ~80% das telas de ERP | Acoplamento a Django ORM, risco de "magic" no middleware empresa_id (`threading.local()`), PrimeReact + Tailwind exigem cuidado de tema | Decidida no discovery Q2/Q3. Foco deste ADR é detalhar guardrails. |
| B. FastAPI + SQLAlchemy + repositório explícito por módulo | Mais flexibilidade, async first-class, sem "magic" de Manager | Custom user, auth, permissões, admin precisam ser construídos do zero — alto custo inicial, mais decisões por módulo (cada agente decide diferente) | Rejeitada (Q2). Para um ERP com agentes generativos, "menos liberdade" é virtude. |
| C. Spring Boot / NestJS / Laravel | Ecosistema robusto | Fora do skillset do time, sem ganho proporcional | Rejeitada antes do discovery. |

A escolha macro está fechada. As **decisões individuais abaixo** detalham _como_ a stack é aplicada — cada decisão é um ADR-filho.

---

# Decisão 1 — Custom User Model em `apps.accounts.User` desde o bootstrap

## Decision

Criar o app `apps.accounts` no **Step 1 do plano**, com `User(AbstractBaseUser, PermissionsMixin)` configurado em `AUTH_USER_MODEL='accounts.User'` **antes** da primeira execução de `migrate`. Campos mínimos:

```
id              UUIDField  primary_key=True default=uuid.uuid4 editable=False
email           EmailField unique=True  (USERNAME_FIELD)
nome            CharField(150)
empresa_atual   FK→empresas.Empresa null=True on_delete=PROTECT
is_active       BooleanField default=True
is_staff        BooleanField default=False
is_superuser    (vem de PermissionsMixin)
created_at      auto_now_add
updated_at      auto_now
```

Manager: `UserManager` com `create_user(email, password, **extra)` e `create_superuser(...)`.
Tabela associativa `accounts_user_empresas` (M2M via `empresas.UserEmpresa`) — usuário pertence a N empresas; `empresa_atual_id` é o tenant ativo da sessão.

Hash de senha: **argon2** (`PASSWORD_HASHERS = ['django.contrib.auth.hashers.Argon2PasswordHasher', ...]`) — OQ6 do plano, decidido aqui.

Integração com `djangorestframework-simplejwt`:
- `SIMPLE_JWT['USER_ID_FIELD'] = 'id'` e `USER_ID_CLAIM = 'user_id'`
- Custom serializer `MyTokenObtainPairSerializer` injeta `empresa_atual_id` no payload do access token (claim `empresa_id`)
- `MyTokenObtainPairView` exposta em `POST /api/v1/auth/token/`
- Endpoint `POST /api/v1/auth/me/empresa/` troca `empresa_atual_id` no DB **e** retorna novo par de tokens com claim atualizada (não basta atualizar DB — o token antigo continua válido até expirar)

## Drivers

- Discovery Q4: multi-empresa exige FK direta de `User` para tenant ativo
- Django impõe restrição técnica: trocar `AUTH_USER_MODEL` depois da primeira `migrate` exige `--fake` + reset do banco — inviável após qualquer dado real
- UUID em `User.id` evita enumeração (`/api/v1/users/123/` vaza contagem; UUID não)
- `email` como `USERNAME_FIELD` casa com a realidade: o operador loga com e-mail, não com username separado
- `auth_user.id` BIGINT do default Django criaria FK heterogênea (BIGINT vs UUID) em `created_by`/`updated_by` quando todas as outras tabelas usarem UUID — degrada índices e força casts
- Argon2 é o único hasher recomendado pela OWASP em 2026; pbkdf2 (default Django) é aceitável mas inferior em memory-hardness

## Alternatives Considered

| Opção | Por quê não |
|---|---|
| Usar `django.contrib.auth.User` (default) | Bloqueia troca futura para UUID; força migration cara depois |
| `AbstractUser` (mantém `username`) | Adiciona campo `username` redundante quando `email` já é único |
| User table sem FK direta para empresa (só M2M) | Toda request precisaria ler M2M para descobrir tenant ativo — caro e propenso a "qual é o tenant atual?" virar bug |
| pbkdf2 (default) | Ainda aceitável, mas Argon2 é o estado da arte e Django 5 suporta nativo |

## Consequences

- **Positiva:** todas as FKs `created_by`/`updated_by` em todas as tabelas de domínio podem usar `UUIDField` consistente
- **Positiva:** payload JWT carrega `user_id` + `empresa_id` — middleware extrai sem hit no banco
- **Positiva:** `empresa_atual_id` no User é fonte de verdade do tenant ativo da sessão
- **Negativa:** trocar `empresa_atual_id` exige **emitir novo token JWT** (claim antiga continua válida até expirar) — fluxo de UX precisa renovar token automaticamente após `POST /me/empresa/`
- **Negativa:** Argon2 exige `pip install argon2-cffi` (dependência nativa) — pode complicar build em alpine images; usar `python:3.12-slim`
- **Neutra:** `apps.accounts.User` significa que o admin Django padrão precisa de `UserAdmin` customizado para listar `nome`/`email`/`empresa_atual`

## What agents MUST do

- **TODO model novo:** se o model precisa de FK para o usuário criador, importar `from django.conf import settings` e usar `settings.AUTH_USER_MODEL` na FK — **nunca** importar `accounts.User` diretamente em outros apps (cria circular import quando `accounts` ainda não foi configurado)
- **TODO** o agent que altera campo do User: criar migration explícita e validar com Grid antes de aplicar
- **TODO** criar superuser inicial via `python manage.py createsuperuser` no Step 6 do bootstrap

## What agents MUST NEVER do

- **NUNCA** usar `django.contrib.auth.get_user_model().objects.create()` em código de domínio sem hashear a senha — usar **sempre** `UserManager.create_user()` ou `User.objects.create_user()`
- **NUNCA** referenciar `auth.User` em FK ou em `authenticate()` — `AUTH_USER_MODEL` aponta para `accounts.User`
- **NUNCA** confiar em `request.user.empresa_atual_id` lido do DB para autorização — use o claim `empresa_id` do JWT (validado pelo middleware) — leitura DB é fallback e custa hit por request
- **NUNCA** alterar a senha de outro usuário sem passar por endpoint dedicado com auditoria

## References

- `/home/evonexus/go_mini_erp_src/app/model/Pessoa.php:36-38` — legado mistura `login`/`senha` na tabela `pessoa` (anti-padrão); GO separa em `accounts.User`
- `/home/evonexus/go_mini_erp_src/app/database/minierp-pgsql.sql:124` — tabela `entrega` referencia `created_by integer` apontando para `system_users(id)` BIGSERIAL — GO troca para UUID
- PRD §6.1 — coluna "Notas de redesenho" para `pessoa` afirma "Remover `login`/`senha` (autenticação fica em `accounts`)"

---

# Decisão 2 — `EmpresaContextMiddleware` + `EmpresaScopedModel` Mixin

## Decision

Implementar duas camadas que cooperam para isolamento multi-empresa **automático**:

### 2.1. `EmpresaContextMiddleware` (DRF middleware classe)

```
# core/middleware.py — pseudocódigo
class EmpresaContextMiddleware:
    def __call__(self, request):
        empresa_id = None
        # Prioridade 1: claim do JWT (já validado por simplejwt antes deste middleware na chain)
        if hasattr(request, 'auth') and request.auth and 'empresa_id' in request.auth.payload:
            empresa_id = request.auth.payload['empresa_id']
        # Prioridade 2: header X-Empresa-ID (apenas para superusers + endpoints administrativos marcados)
        elif request.headers.get('X-Empresa-ID') and request.user.is_superuser:
            empresa_id = request.headers['X-Empresa-ID']
        # Prioridade 3: empresa_atual do user (fallback no boot da sessão)
        elif request.user.is_authenticated:
            empresa_id = str(request.user.empresa_atual_id) if request.user.empresa_atual_id else None
        
        # Set em context-var (asyncio-safe; superior a threading.local em workers async)
        token = empresa_context.set(empresa_id)
        try:
            response = self.get_response(request)
        finally:
            empresa_context.reset(token)
        return response
```

**Decisão crítica:** usar `contextvars.ContextVar` ao invés de `threading.local()`.
- `threading.local` quebra silenciosamente em workers `gunicorn --worker-class gevent`/`uvicorn`/Celery prefork eventlet — task pode reusar local de outra request
- `ContextVar` é o padrão Python 3.7+ recomendado para contexto por-request, async-safe

### 2.2. `EmpresaScopedModel` (Mixin abstrato)

```
class EmpresaScopedModel(models.Model):
    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.PROTECT, related_name='+')
    objects = EmpresaScopedManager()         # filtra por empresa_context.get() automaticamente
    all_empresas = models.Manager()          # bypass: usar só em jobs cross-tenant
    class Meta:
        abstract = True
        indexes = [models.Index(fields=['empresa', 'deleted_at'])]
```

`EmpresaScopedManager.get_queryset()` aplica `.filter(empresa_id=empresa_context.get())` se contexto presente; **levanta `EmpresaContextoMissing`** se contexto vazio e código não estiver em `all_empresas`. Isso é importante: **falhar ruidosamente** quando alguém esquece o middleware é melhor que retornar tudo silenciosamente (hipótese de vazamento cross-tenant).

### 2.3. Auto-injeção de `empresa_id` no `save()`

```
class EmpresaScopedModel(models.Model):
    def save(self, *args, **kwargs):
        if not self.empresa_id:
            empresa_id = empresa_context.get(None)
            if not empresa_id:
                raise EmpresaContextoMissing(f"Cannot save {self.__class__.__name__} without empresa")
            self.empresa_id = empresa_id
        super().save(*args, **kwargs)
```

Agentes não precisam lembrar de setar `empresa_id` em `Service.create_pessoa(...)` — o save garante.

## Drivers

- Discovery Q4: `empresa_id` em todas as tabelas de domínio
- PRD CA-08: isolamento multi-empresa testado (E1 não vê E2)
- Erro humano comum em multi-tenancy: esquecer `WHERE empresa_id = X` em uma query — Mixin elimina a categoria inteira de bug
- `contextvars` é a forma correta em 2026; `threading.local` é cilada em async/Celery
- Falhar ruidosamente (`EmpresaContextoMissing`) é melhor que vazar dados

## Alternatives Considered

| Opção | Por quê não |
|---|---|
| Filtro manual em cada queryset (`Pessoa.objects.filter(empresa_id=request.empresa_id)`) | Toda view repete o filtro; primeira que esquecer vaza dados de outras empresas. Inviável com agentes generativos. |
| Schema-per-tenant (PostgreSQL schemas) | Migra-se mal para "banco compartilhado quando mesma natureza" (Q4); add tenant exige `CREATE SCHEMA` runtime |
| Middleware injeta `empresa_id` em `request` apenas, sem ContextVar | Manager precisa do `request` para filtrar — passar request até o ORM exige bagagem em todo método de service |
| `threading.local()` (proposta original do plano Step 1) | Quebra em async workers; Django 5 já tem `request.async_capable = True` |
| Row-Level Security (RLS) no PostgreSQL via `SET app.empresa_id = X` | Robusto, mas opaco — debugging de "por que essa query não retorna nada?" exige conhecer RLS policies; alto custo cognitivo para os agentes |

## Consequences

- **Positiva:** zero código de filtro empresa em views/services do domínio — bug de vazamento cross-tenant tem peso baixo
- **Positiva:** save() preenche `empresa_id` automaticamente → service `create_pessoa(data)` não precisa saber qual empresa é
- **Positiva:** `EmpresaContextoMissing` em queries fora de request (e.g., shell, jobs) força código a ser explícito (`Pessoa.all_empresas.filter(empresa=X).all()`)
- **Negativa:** cargo de magia — desenvolvedor novo demora ~1 dia para entender por que `Pessoa.objects.all()` retorna conjuntos diferentes em requests diferentes
- **Negativa:** `EmpresaScopedManager` tem que ser cuidadoso com `prefetch_related`/`select_related` — relacionamentos atravessam para models que também são `EmpresaScopedModel` e o filtro empresa pode duplicar / conflitar
- **Negativa:** management commands (`python manage.py shell`, `loaddata`, `migrate`) rodam sem contexto — todo seed/fixture precisa usar `Model.all_empresas` ou setar contexto manualmente
- **Negativa:** custom Manager rompe alguns querysets do admin — `EmpresaScopedModelAdmin` precisa override para usar `all_empresas` quando admin é superuser

## What agents MUST do

- **TODO model de domínio:** herdar de `EmpresaScopedModel + SoftDeleteMixin + AuditMixin` (nessa ordem)
- **TODO** seed de dados/fixtures que cruza empresas: usar `Model.all_empresas.create(empresa=..., ...)` explicitamente
- **TODO** Celery task que processa todas as empresas: setar `empresa_context.set(empresa_id)` no início do task wrapper (ou rodar via `for empresa in Empresa.objects.all(): with empresa_context_scope(empresa.id): ...`)
- **TODO** test fixture: `pytest.fixture` chamada `set_empresa_context` que aceita `empresa_id` e seta/limpa o contexto em torno do teste
- **TODO** `apps.empresas.models.Empresa` herda de `TimestampMixin + SoftDeleteMixin` mas **não** de `EmpresaScopedModel` (a Empresa não pertence a uma Empresa — é um catálogo do tenant)

## What agents MUST NEVER do

- **NUNCA** usar `Model.all_empresas` em código de view/service de domínio — só em management commands, seeds, jobs cross-tenant
- **NUNCA** passar `request.empresa_id` como argumento para um service como atalho para "burlar" o ContextVar — o middleware é a fonte; service deve confiar nele
- **NUNCA** popular `empresa_id` à mão em `Model.save()` ou `Model.objects.create(empresa=outra)` em código de domínio — auto-injeção do mixin é a regra
- **NUNCA** definir um catálogo global (Estado, Cidade, UnidadeMedida, TipoCliente, CategoriaCliente, CepCache) como `EmpresaScopedModel` — esses são compartilhados; herdam apenas `TimestampMixin`
- **NUNCA** usar `threading.local()` para dados de request — sempre `contextvars`

## References

- `/home/evonexus/go_mini_erp_src/app/database/minierp-pgsql.sql:55-83` — tabela `conta` no legado **não** tem `empresa_id` (single-tenant) — GO adiciona
- Plano §Step 1 — propunha `threading.local()`; este ADR substitui por `contextvars.ContextVar`
- PRD §C4 — catálogos globais sem `empresa_id` listados explicitamente

---

# Decisão 3 — Padrão de módulo Django (`models / serializers / services / selectors / views / urls / permissions / tests`)

## Decision

Cada app Django no GO segue **rigorosamente** este layout:

```
backend/apps/<app_name>/
├── __init__.py
├── apps.py
├── admin.py                    # Django admin (catalogos + debug)
├── models/                     # 1 arquivo por entidade ou aggregate
│   ├── __init__.py             # re-exporta as classes
│   ├── pessoa.py
│   ├── pessoa_endereco.py
│   └── ...
├── serializers/                # DRF serializers — só validação de shape + format
│   ├── __init__.py
│   ├── pessoa_serializer.py
│   └── ...
├── services/                   # Regra de negócio — toda escrita
│   ├── __init__.py
│   ├── pessoa_service.py       # create_pessoa, update_pessoa, soft_delete_pessoa, etc.
│   └── ...
├── selectors/                  # Queries de leitura — toda listagem/get-by-id
│   ├── __init__.py
│   ├── pessoa_selectors.py     # list_pessoas(filters), get_pessoa(id), etc.
│   └── ...
├── views/                      # DRF views — THIN: parse → service/selector → serialize
│   ├── __init__.py
│   ├── pessoa_view.py
│   └── ...
├── permissions.py              # Permission classes do app
├── urls.py                     # Roteamento DRF (router.register)
├── filters.py                  # django-filter FilterSets
├── fixtures/                   # JSON seeds versionados
│   └── *.json
├── migrations/
└── tests/
    ├── __init__.py
    ├── factories.py            # factory_boy
    ├── conftest.py             # fixtures (set_empresa_context, etc.)
    ├── test_models_*.py        # validações, constraints, soft delete
    ├── test_services_*.py      # regra de negócio
    ├── test_selectors_*.py     # queries com filtros
    ├── test_views_*.py         # API integration
    └── test_permissions_*.py
```

### Regra de camadas (importações)

```
views.py    →  importa de  services, selectors, serializers, permissions
serializers →  importa de  models, services (apenas para validation cross-record)
services    →  importa de  models, selectors (para checagens), outros services do MESMO app
selectors   →  importa de  models
models      →  importa de  models de outros apps (FK), core mixins
```

**Proibido:** `services` importar `views` ou `serializers` (inversão de dependência); `selectors` ter side effects (escrever, enviar e-mail, chamar API externa).

### Regra de responsabilidades

| Camada | Pode | Não pode |
|---|---|---|
| `models` | Validação de campo (`validators=[...]`), constraints, properties calculadas, manager queryset | Side effects (signals OK só para audit_log), regra de negócio cross-entidade |
| `serializers` | Validar formato (CPF/CNPJ regex, range), `validate_<field>`, `validate()` cross-field, montar shape de resposta | Persistir, chamar API externa, criar objetos relacionados (delegar para service em `create()`/`update()` que **só chama** `service.create_pessoa(data)`) |
| `services` | Operações de **escrita** (`create_pessoa`, `update_pessoa`, `soft_delete_pessoa`, `gerar_codigo_barras`), invariantes de domínio, transações (`@transaction.atomic`), publicar eventos | Renderizar HTTP, conhecer DRF, conhecer `request` (recebe argumentos puros) |
| `selectors` | Operações de **leitura** (`list_pessoas`, `get_pessoa`, `count_pessoas_ativas`), `select_related`/`prefetch_related`, agregações | Escrever, side effects |
| `views` | Parse input → chamar service/selector → serialize output → status code; aplicar permissions | Conter regra de negócio, fazer queries diretas no model, tocar em `request.user.empresa_atual_id` (use `empresa_context.get()`) |
| `permissions` | Decidir se a request tem direito a passar | Buscar dados de domínio (delegar para selector se necessário) |

## Drivers

- Plano Step 4 lista exatamente este layout — ADR formaliza como **lei**, não sugestão
- Discovery §4.3 mostrou que controllers Adianti misturam UI + regra de negócio (anti-padrão); `services/` previne reincidência
- A separação `services/selectors` é a "Two Scoops of Django" / HackSoftware Style Guide — cada agente que toca o repo entra com referência pública conhecida
- Imports unidirecionais (`views → services → models`) eliminam ciclos e tornam grep + leitura previsíveis para agentes
- DRF default empurra lógica para `ViewSet` → vira "fat view" rapidamente; padrão de "thin view" obriga delegação

## Alternatives Considered

| Opção | Por quê não |
|---|---|
| `apps/<x>/models.py` + `views.py` + `serializers.py` (default Django) | Em ERP com 20+ entidades por app, vira arquivo de 3000 linhas — Bolt+Lens perdem foco |
| Domain-Driven Design pleno (entities, value objects, repositories, application services em pacotes) | Overkill para ERP transacional; agentes generativos performam pior em camadas demais |
| Combinar service + selector em "service" só (sem distinção leitura/escrita) | Perde clareza CQRS; views ficam com mistura de "criar pedido" e "listar pedidos" no mesmo método |
| Repository pattern com SQLAlchemy estilo (sem ORM Django) | Decisão Q2 já fechou em Django ORM |

## Consequences

- **Positiva:** abrir um app desconhecido — em 30s sabe onde está cada coisa
- **Positiva:** `grep -r "service\." backend/` revela todos os pontos de regra de negócio sendo chamados
- **Positiva:** test layout espelha código layout (1 test_file por camada) — cobertura por camada visível
- **Positiva:** Lens-reviewer + Oath-verifier têm checklist objetivo ("é regra de negócio? está em `services/`?")
- **Negativa:** mais arquivos pequenos (15-25 por app) — agente novato pode confundir-se com a hierarquia
- **Negativa:** retorno de service não é serializer — agentes podem tentar retornar dict raw em view (passar pelo serializer mesmo em `Response(serializer(obj).data)` é a regra)
- **Negativa:** padrão exige disciplina — Lens **deve** rejeitar PR que coloca lógica em `view.py`

## What agents MUST do

- **TODO** Bolt ao criar nova entidade: criar **todos** os arquivos do layout (mesmo que `selectors/<entidade>_selectors.py` comece com 3 funções simples) — não amontoar tudo em `views.py` "porque é simples"
- **TODO** Service retorna a instância do Model (ou DTO Pydantic se cross-aggregate) — view serializa
- **TODO** Selector retorna `QuerySet` (preguiçoso) ou `list[Model]`/`Iterator[Model]` — nunca `dict`
- **TODO** View que precisa transação: marcar **service** com `@transaction.atomic`, não a view
- **TODO** Bolt: ao herdar `ModelViewSet`, override `perform_create`/`perform_update`/`perform_destroy` para chamar service — nunca confiar em `serializer.save()` direto se há regra
- **TODO** Grid escreve teste **antes** do código em todo step (TDD obrigatório do PRD §3)

## What agents MUST NEVER do

- **NUNCA** colocar `if request.user.is_superuser:` em service — autorização é responsabilidade de `permissions.py`/view
- **NUNCA** colocar `validate_cpf(documento)` em view — validação de formato vai no `serializers/`; validação de regra (ex: CPF único na empresa) vai no service
- **NUNCA** chamar `requests.get(...)` direto em service — toda chamada externa passa por `apps.integrations.<area>.proxy` (ver Decisão 6)
- **NUNCA** importar `serializers` em `services` (acopla regra a representação HTTP)
- **NUNCA** misturar leitura e escrita no mesmo arquivo `services/x.py` — leitura vai em `selectors/`
- **NUNCA** definir model em `models.py` único quando o app tem 5+ entidades — quebrar em `models/` package
- **NUNCA** retornar `Response()` de uma função de service — serviço não conhece HTTP

## References

- `/home/evonexus/go_mini_erp_src/app/control/comercial/PedidoVendaForm.php:1-654` — exemplo do anti-padrão Adianti: form constrói UI **e** valida campo **e** chama service no submit, tudo em 654 linhas
- `/home/evonexus/go_mini_erp_src/app/service/grafix/vendas/PedidoVendaService.php:52-86` — exemplo de service grafix bom (validações + transação) — padrão a portar
- `/home/evonexus/go_mini_erp_src/app/service/grafix/vendas/WorkflowService.php:40-103` — exemplo de selector-like com side effect (abre transação) — em GO seria split entre selector (sem transação) e service (com)
- Plano Step 4 — listou o layout; ADR formaliza

---

# Decisão 4 — Padrão de módulo React (`pages / components / services / hooks / types / routes.tsx`)

## Decision

Cada módulo de domínio em `frontend/src/modules/<area>/<entidade>/` segue este layout:

```
frontend/src/modules/<area>/<entidade>/
├── pages/
│   ├── <Entidade>ListPage.tsx       # PrimeReact DataTable + filtros + paginação server-side
│   ├── <Entidade>FormPage.tsx       # React Hook Form + Zod
│   └── <Entidade>DetailPage.tsx     # leitura
├── components/
│   ├── <Entidade>FormFields.tsx     # campos reutilizáveis (form de criação E edição usam o mesmo)
│   ├── <Entidade>StatusBadge.tsx
│   └── <Entidade>FilterBar.tsx
├── services/
│   └── <entidade>.service.ts        # API client tipado: list/get/create/update/delete
├── hooks/
│   └── use<Entidade>.ts             # TanStack Query hooks: usePessoasList, usePessoaCreate, etc.
├── types/
│   └── <entidade>.types.ts          # interfaces TS espelham serializer DRF
├── schemas/
│   └── <entidade>.schema.ts         # Zod schemas (cliente) alinhados com validators backend
└── routes.tsx                       # rotas do módulo (export default)
```

### Camadas e regras

| Camada | Responsabilidade | Não faz |
|---|---|---|
| `pages/` | Compor layout + chamar hooks + roteamento | Conter lógica de transformação de dados, montar payload manualmente |
| `components/` | UI reutilizável, props tipadas, sem fetch | `useQuery`/`useMutation` (vai em `hooks/`); knowledge de roteamento |
| `services/` | Funções tipadas que chamam Axios; **uma função = um endpoint** | TanStack Query (vai em `hooks/`); state management; toasts |
| `hooks/` | TanStack Query: `useQuery` + `useMutation` envolvendo `services/`; invalidação de cache; toast de sucesso/erro | Lógica de UI, montagem de payload complexo |
| `types/` | `interface Pessoa { ... }` espelhando o serializer DRF do backend | Lógica, defaults |
| `schemas/` | Zod schemas para validação de form (alinhado com `serializers/` do backend) | Tipos puros (esses ficam em `types/`) |
| `routes.tsx` | `<Route path="..." element={...}>` exportado | Lógica |

### Cliente HTTP único

`src/lib/api.ts` exporta `api` (Axios instance) com:
- `baseURL = import.meta.env.VITE_API_BASE_URL` (default `/api/v1`)
- Interceptor de request: anexa `Authorization: Bearer <access>` do localStorage
- Interceptor de response: 401 → tenta refresh com `/auth/token/refresh/`; se refresh falha → redireciona para login
- Interceptor de erro: extrai `{detail: "..."}` ou `{<field>: ["..."]}` do DRF e propaga em formato uniforme

Todos os `services/<entidade>.service.ts` consomem `api` — **proibido** usar `fetch()` direto ou criar Axios instance própria por módulo.

### Estado server vs cliente

- **Server state:** TanStack Query (cache + invalidação) — `usePessoasList()`, `usePessoaCreate()`
- **Form state:** React Hook Form + Zod via `zodResolver`
- **Auth/empresa state global:** Context API (`AuthProvider`, `EmpresaProvider`) — não Redux, não Zustand (decisão Q3 não menciona, ADR fixa: Context é suficiente até precisarmos de mais)
- **UI state local:** `useState`/`useReducer`

### PrimeReact + Tailwind

- Tema PrimeReact: **`lara-light-blue`** importado em `main.tsx`; tokens documentados em `coding-standards.md`
- Tailwind preset: cores aliasadas para tokens PrimeReact (`primary` = `var(--primary-color)`)
- Regra: layout/spacing → **Tailwind**; componentes complexos (DataTable, Calendar, AutoComplete, Dialog) → **PrimeReact**; nunca reimplementar componente que PrimeReact tem
- z-index: PrimeReact usa `1101+` para overlays; Tailwind ficar abaixo de 1100 — documentar

## Drivers

- Discovery Q3 + PRD §6/§7
- Mesmo princípio do padrão Django: agente generativo precisa de hierarquia previsível
- TanStack Query elimina classe inteira de bug (cache stale, refetch após mutation) que cada agente resolve diferente
- Zod no frontend + DRF Validator no backend pode redundar — **isso é desejado**: validação dupla evita ida ao servidor para erros triviais
- Axios instance única + interceptor 401 evita "cada hook trata refresh do seu jeito"

## Alternatives Considered

| Opção | Por quê não |
|---|---|
| Next.js + App Router (SSR) | Overkill para ERP intranet; SPA Vite é mais simples |
| Material UI / Ant Design (em vez de PrimeReact) | PrimeReact tem DataTable mais maduro para ERP brasileiro; Ant tem peso similar mas menor cobertura de componentes ERP-specific (Calendar PT-BR, Editor) |
| Redux Toolkit + RTK Query | TanStack Query é mais ergonômico para 80% dos casos; Redux só compensa em fluxos complexos cross-page |
| Atomic Design (atoms/molecules/organisms) | Categorização excessiva; agentes têm dificuldade em decidir nível |
| 1 arquivo por componente em qualquer pasta | Sem hierarquia → repositório vira flat de 200 .tsx |

## Consequences

- **Positiva:** novo módulo (e.g., `cadastros/produtos`) é cópia + ajuste de `cadastros/pessoas` — produtividade alta para Bolt
- **Positiva:** invalidação de cache centralizada (hooks chamam `queryClient.invalidateQueries(['pessoas'])` após mutation)
- **Positiva:** type-safety end-to-end: backend `serializers/PessoaSerializer` ↔ `types/pessoa.types.ts` ↔ form Zod
- **Negativa:** boilerplate alto — entidade simples com 4 endpoints gera 8 arquivos
- **Negativa:** PrimeReact + Tailwind exige cuidado de tema; brigas de CSS específicas do PrimeReact (z-index, classes utilitárias) precisam de sobrescritas pontuais
- **Negativa:** dois sistemas de validação (Zod + DRF) — quando divergirem, frontend pode "passar" e backend recusar; mensagens precisam ser consistentes (centralizar em arquivo de strings i18n-ready, mesmo que GO seja só pt-BR por agora)

## What agents MUST do

- **TODO** Canvas/Bolt ao criar nova tela: copiar estrutura de `modules/cadastros/pessoas/` e adaptar
- **TODO** todo serviço Axios usa `import { api } from '@/lib/api'`; **nunca** `axios.get(...)` direto
- **TODO** todo hook TanStack Query passa `queryKey` array tipado: `['pessoas', 'list', filters]` — não strings concatenadas
- **TODO** após `useMutation` de criar/atualizar/deletar: invalidar a query list correspondente
- **TODO** Zod schemas espelham regras dos serializers DRF — comentário em cada schema linkando o arquivo backend correspondente
- **TODO** mensagens de erro/UI em pt-BR — chave em arquivo central (`src/i18n/messages.ts`) facilita revisão

## What agents MUST NEVER do

- **NUNCA** chamar `fetch` ou criar `axios.create({...})` paralelo — sempre `api` em `lib/api.ts`
- **NUNCA** misturar `useState` para "dados do servidor" com TanStack Query — duplica fonte de verdade
- **NUNCA** colocar lógica de transformação em `pages/` — extrair para hook ou helper
- **NUNCA** importar componente de outro módulo "vizinho" (`modules/cadastros/produtos` em `modules/cadastros/pessoas`) — extrair para `src/components/shared/`
- **NUNCA** reimplementar DataTable, Dialog, Calendar — PrimeReact resolve
- **NUNCA** usar `console.log` em código merged — `src/lib/logger.ts` (delegando para console em dev, no-op em prod)

## References

- PRD §6.1 e §6.2 — telas Pessoa e Produto descritas
- Plano Step 5 — layout listado; ADR formaliza
- (Não há referência ao legado: a UI Adianti é descartada; React não tem espelho)

---

# Decisão 5 — UUID v4 como PK universal

## Decision

**Toda** PK no GO é `UUIDField(primary_key=True, default=uuid.uuid4, editable=False)`. Isso inclui `accounts.User`, `empresas.Empresa`, todas as entidades de domínio e todos os catálogos por-empresa. Catálogos globais (Estado, Cidade, UnidadeMedida, TipoCliente, CategoriaCliente, CepCache) **também** usam UUID — coerência supera economia marginal.

UUID é gerado em **Python** (`uuid.uuid4()`), não no banco — o objeto já tem ID antes do INSERT (útil para logs, idempotência, retornar 201 antes do commit).

FKs: `models.UUIDField` (no related field) implícito quando `models.ForeignKey('app.Model')` é declarado e o target tem PK UUID.

Paginação: **cursor-based** com `created_at + id` (UUIDField como tiebreaker estável) — DRF `CursorPagination(ordering='-created_at,-id')`. **Não** usar `LimitOffsetPagination` em listas grandes (degrada com offset alto).

Indexes:
- BTREE no PK (default)
- BTREE composto `(empresa, deleted_at)` em todo `EmpresaScopedModel`
- BTREE em `(created_at, id)` para cursor pagination
- Para campos de busca textual frequente (`pessoa.nome`, `pessoa.documento`, `produto.nome`, `produto.cod_barras`): GIN trigram (`pg_trgm`) — index dedicado, criado em RunSQL migration

## Drivers

- Discovery Q5 (sem migração de dados) → liberdade para escolher UUID sem custo
- Multi-tenant: integer auto-incremento vaza informação ("já temos 50.000 pedidos") via enumeração; UUID não
- UUID gerado client-side viabiliza upsert idempotente e geração de código antes do salvamento
- BIGSERIAL é mais compacto (8 bytes vs 16) e mais rápido em INSERT, mas o ganho é < 5% para volumetria ERP típica — não justifica perder UUID
- UUIDv4 é random; não tem hot-spot de inserção (UUIDv1 timestamp criaria contention em B-tree em workloads write-heavy — não é o caso aqui)

## Alternatives Considered

| Opção | Por quê não |
|---|---|
| BIGSERIAL (autoincrement) | Vaza contagem; FK heterogênea com User UUID |
| UUIDv7 (timestamp prefixado) | Tem benefícios em índice (locality), mas suporte ainda incipiente em libs Python — UUIDv4 é o conservador correto em 2026; revisitar em 1 ano |
| ULID | Excelente, mas não tem suporte first-class no Django ORM — usar como string CharField perde tipo nativo |
| Hash do conteúdo como ID | Apropriado para idempotência, não para ID natural |

## Consequences

- **Positiva:** sem enumeração — atacante não consegue iterar IDs em URL
- **Positiva:** UUID gerado em Python → idempotência client-side (cliente pode mandar o mesmo POST 2x se sabe o ID)
- **Positiva:** consistência de tipo em todas as FKs
- **Negativa:** PK 16 bytes vs 8 (BIGSERIAL) → +5-15% no tamanho do índice, +1-3% no tempo de range scan
- **Negativa:** UUIDs em URLs são feios (`/pessoas/3f4a5b6c-...`); mitigação: `slug` field separado para URLs amigáveis quando necessário (ex: produtos com `slug` = `nome-kebab-cased + sufixo curto`)
- **Negativa:** `LimitOffsetPagination` com UUID no `ORDER BY id` é menos previsível visualmente (UUID não tem ordem cronológica) — daí cursor-based em `created_at`
- **Negativa:** debugging "qual pessoa é a 1?" — só por nome/documento; não há atalho mental

## What agents MUST do

- **TODO** todo model novo: PK UUID via mixin `BaseModel` que já carrega `id`, `created_at`, `updated_at`, `deleted_at`
- **TODO** listas grandes (>500 itens potenciais): `CursorPagination(ordering='-created_at,-id')`
- **TODO** busca textual: criar migration RunSQL com `CREATE INDEX ... USING GIN (campo gin_trgm_ops);` (e habilitar extensão `pg_trgm` no `0001_initial`)
- **TODO** ao expor URL de detalhe pública: avaliar se faz sentido `slug` adicional (Produto sim; Pessoa não — interna)

## What agents MUST NEVER do

- **NUNCA** criar PK BIGSERIAL/`AutoField` — quebra padrão e cria FK heterogênea
- **NUNCA** gerar UUID no banco (`gen_random_uuid()` em DEFAULT) — Python deve ter o UUID antes do save (auditoria, logs)
- **NUNCA** assumir ordenação cronológica de UUID v4 — sempre ordenar por `created_at` (com `id` como tiebreaker)
- **NUNCA** expor UUID interno em recibos/relatórios para usuário final — mostrar `numero`/`codigo` legível (ex: pedido tem `numero` curto separado da PK)

## References

- `/home/evonexus/go_mini_erp_src/app/database/minierp-pgsql.sql:55-83` — legado usa `SERIAL` em `conta` (e em todas as tabelas) — GO troca para UUID
- PRD OQ1 — recomendação Compass UUID v4; este ADR fixa
- Plano Step 1 — `id (UUID v4)` em accounts e empresas

---

# Decisão 6 — Proxy Pattern para integrações externas (Strategy + Fallback + Rate-limit Router)

## Decision

Cada categoria de integração externa (Fiscal, Bancário, CEP, CNPJ) tem um app dedicado em `apps.integrations.<area>` com este layout:

```
apps/integrations/<area>/
├── __init__.py
├── interface.py        # Protocol/ABC: contrato comum
├── exceptions.py       # ProviderError, ProviderTimeout, RateLimitExceeded
├── proxy.py            # Roteador: aplica estratégia (fallback / round-robin / por config)
├── providers/
│   ├── __init__.py
│   ├── <provider1>.py  # implementa interface
│   └── <provider2>.py
├── services.py         # camada que cacheia + chama proxy + persiste log
├── views.py            # endpoint REST (se aplicável)
├── urls.py
└── tests/
    ├── test_proxy.py        # mocka providers, valida fallback
    ├── test_<provider>.py   # mocka HTTP layer (via `responses` lib)
    └── test_services.py
```

### Contrato comum (`interface.py`)

```
class CepProvider(Protocol):
    name: str   # 'viacep', 'brasilapi', etc.
    def lookup(self, cep: str) -> CepResult | None: ...

@dataclass(frozen=True)
class CepResult:
    cep: str
    rua: str | None
    bairro: str | None
    cidade: str | None
    uf: str | None
    codigo_ibge: str | None
    fonte: str   # qual provider produziu este resultado
```

Resultado com tipo `frozen dataclass`, não dict — type-checking salva regressões.

### Estratégias por categoria

| Proxy | Estratégia primária | Cache | Notas |
|---|---|---|---|
| **CEP** | Sequencial com fallback: provider 1 → 2 → 3 | Tabela `cep_cache` (TTL 30 dias) | CEP é estável; cache agressivo é seguro |
| **CNPJ** | Sequencial com fallback + circuit breaker (ReceitaWS rate-limita 3 req/min free) | Redis (TTL 7 dias) | Dado muda; cache moderado; rate-limit awareness em Redis (token bucket por provider) |
| **Fiscal (NF-e)** | Por configuração da empresa: `Empresa.proxy_fiscal_provider = 'focus_nfe'` (sem fallback automático — fiscal é sensível, falha pede ação humana) | Sem cache (NF-e é write) | Configuração explícita; falha emite alerta para responsável fiscal, não tenta outro provider |
| **Bancário** | Sequencial por método: para PIX tenta Inter, depois Asaas (cada um com sua API). Fallback é por funcionalidade, não cego | TTL curto em consulta de extrato (15min) | Webhooks de cada provider apontam para `/api/v1/integrations/banking/webhook/<provider>/` |

### Circuit breaker simples

```
class ProviderCircuitBreaker:
    def __init__(self, provider_name, failure_threshold=3, cooldown_seconds=300):
        self.key = f"cb:{provider_name}"
    def is_open(self) -> bool:
        return redis.get(self.key + ":until") is not None
    def record_failure(self):
        count = redis.incr(self.key + ":count")
        redis.expire(self.key + ":count", 60)
        if count >= self.failure_threshold:
            redis.set(self.key + ":until", "1", ex=self.cooldown_seconds)
    def record_success(self):
        redis.delete(self.key + ":count")
```

Proxy ignora providers com circuit aberto.

### Cache de CEP

`apps.integrations.cep.services.lookup_cep(cep)`:
1. Normaliza (`re.sub(r'[^0-9]', '', cep)`)
2. Consulta `CepCache.objects.filter(cep=cep, created_at__gte=now()-30d).first()` (model está em `apps.integrations.cep.models.CepCache`, **não** em `apps.cadastros.pessoas` — a entidade é da área de integrações)
3. Hit → retorna
4. Miss → chama `cep_proxy.lookup(cep)` → persiste em `cep_cache` → retorna

CepCache **não** é EmpresaScopedModel (cache global, sem `empresa_id`).

### Logs estruturados

Toda chamada de proxy/provider emite log via `structlog` com:
- `provider`, `area`, `input` (cep/cnpj normalizado), `status`, `latency_ms`, `circuit_state`, `fallback_chain`
- Persistido em `provider_call_log` table para auditoria/debug (write-only, retenção 90 dias)

## Drivers

- Discovery Q6: arquitetura proxy com múltiplos providers
- Cada API externa tem rate-limit / SLA / contratos diferentes — abstrair em `Protocol` deixa providers intercambiáveis
- Fallback automático em CEP/CNPJ (consulta) faz sentido (custo zero de tentar segundo); fallback automático em Fiscal **não** (idempotência fiscal é frágil; emitir mesma NF-e em 2 providers cria duplicidade)
- Cache de CEP economiza chamadas (CEP é estável); cache de CNPJ menos agressivo (dado muda)
- Circuit breaker evita estampedida quando provider está fora — degrada graceful em vez de timeout em todo request

## Alternatives Considered

| Opção | Por quê não |
|---|---|
| Chamada direta `requests.get(...)` em service de domínio | Acopla domínio à URL/contrato do provider; trocar provider exige tocar em N services |
| Service único `IntegrationsService` com if/elif por área | Vira god-object; testes ficam emaranhados |
| Cliente externo via library de cada provider (e.g., `viacep` pkg) | Cada lib tem qualidade variável; muitas abandonadas; melhor implementar adapter explícito por provider |
| Proxy com fallback automático em Fiscal | Risco de duplicidade; fiscal **deve** ser explícito |
| Sem cache (todas as chamadas batem nos providers) | ViaCEP/ReceitaWS rate-limitam; cache é defesa básica |

## Consequences

- **Positiva:** trocar provider de CEP de ViaCEP para BrasilAPI = config (ordem da lista), zero código de domínio
- **Positiva:** testes mockam `Protocol` — não há HTTP real em CI
- **Positiva:** circuit breaker contém falha em provider sem derrubar request principal
- **Negativa:** mais arquivos por integração (interface + N providers + proxy + service + views + tests = ~7 arquivos por área)
- **Negativa:** abstração tem custo de reflexão — agente precisa entender o contrato `Protocol` antes de adicionar novo provider
- **Negativa:** Redis vira ponto de dependência para circuit breaker (já é, para rate-limit/cache CNPJ — mas confirma); failure de Redis degrada para "sem circuit breaker" (escolha consciente: melhor que falhar)

## What agents MUST do

- **TODO** novo provider em área existente: criar `providers/<name>.py` implementando o `Protocol`; **adicionar à lista no `proxy.py`**; criar `tests/test_<name>.py` com mock HTTP via `responses`
- **TODO** nova área de integração: copiar estrutura de `apps/integrations/cep/` como template
- **TODO** chamadas externas em código de domínio: **sempre** via `apps.integrations.<area>.services.<funcao>(...)` — nunca `requests.get`, `httpx.get`, etc.
- **TODO** todo provider tem timeout (5s default); 429/5xx incrementam circuit breaker; 4xx (exceto 429) são erros do input, não falha do provider
- **TODO** novo proxy emite log estruturado com `fallback_chain` (lista de providers tentados na ordem) — debug futuro depende disso

## What agents MUST NEVER do

- **NUNCA** `requests.get()` em service ou view de domínio — chamada externa **sempre** via `apps.integrations.<area>.proxy`
- **NUNCA** colocar credenciais hard-coded em `providers/*.py` — sempre `settings.<PROVIDER>_API_KEY` (via `.env`)
- **NUNCA** habilitar fallback automático em proxy fiscal (idempotência) — falha emite alerta, **não** tenta outro
- **NUNCA** consultar cache CEP "manualmente" via ORM em código de domínio — passar pela função `services.lookup_cep(cep)` (centraliza TTL, normalização, log)
- **NUNCA** misturar `CepCache` no app `cadastros` — pertence a `apps.integrations.cep` (boundary de área)

## References

- Discovery Q6 + §4.2 + tabela em §3 — arquitetura proxy descrita
- `/home/evonexus/go_mini_erp_src/app/service/CEPService.php` — referência funcional do legado (PHP, simples; GO substitui por arquitetura)
- PRD §7 + CA-11 + CA-12 — comportamento esperado dos proxies CEP e CNPJ
- Plano Step 3 — interfaces + providers + fallback + cache

---

# Decisão 7 — Soft delete universal (`SoftDeleteMixin` + `SoftDeleteManager`)

## Decision

Toda tabela de **domínio** (não catálogos globais como Estado/Cidade/UnidadeMedida) e tabelas que têm vínculos referenciais (catálogos por empresa: Fabricante, FamiliaProduto) usam **soft delete** via `deleted_at TIMESTAMPTZ NULL`. Hard delete é exceção, requer ação explícita.

```
class SoftDeleteMixin(models.Model):
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)
    deleted_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                    on_delete=models.SET_NULL, related_name='+')
    class Meta:
        abstract = True
    
    def delete(self, using=None, keep_parents=False, hard=False):
        if hard:
            return super().delete(using=using, keep_parents=keep_parents)
        self.deleted_at = timezone.now()
        # deleted_by populado pelo service via empresa_context se disponível
        self.save(update_fields=['deleted_at', 'deleted_by'])

class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)

# em cada model que combina os dois:
class Pessoa(EmpresaScopedModel, SoftDeleteMixin, AuditMixin):
    objects = EmpresaScopedSoftDeleteManager()  # combina ambos os filtros
    all_records = models.Manager()  # bypass total
    ...
```

### Comportamento

- `pessoa.delete()` → seta `deleted_at` (default soft)
- `pessoa.delete(hard=True)` → DELETE físico (uso reservado: GDPR/LGPD direito ao esquecimento, dado de teste)
- `Pessoa.objects.all()` → não retorna soft-deleted (filtro automático)
- `Pessoa.all_records.filter(deleted_at__isnull=False)` → recupera deletadas (admin / restore)
- `Pessoa.objects.get(id=X)` para id soft-deletado → `DoesNotExist` (consistente com filter)

### Restore

`PessoaService.restore_pessoa(pessoa_id)` → encontra via `all_records`, valida que o `deleted_at` não excede política de retenção (ex: 90 dias), seta `deleted_at = None`, registra `audit_log`.

### Constraints únicas com soft delete

PostgreSQL `UNIQUE` não considera `NULL`. Para "documento único por empresa **dentre** os ativos":

```
class Meta:
    constraints = [
        models.UniqueConstraint(
            fields=['empresa', 'documento'],
            condition=models.Q(deleted_at__isnull=True) & models.Q(documento__isnull=False),
            name='uq_pessoa_documento_por_empresa_ativa',
        ),
    ]
```

→ permite re-cadastrar uma pessoa cujo documento estava em uso por outra **soft-deletada**.

### DRF e soft delete

DRF `ModelViewSet.destroy()` chama `instance.delete()` → padrão é soft (correto).
Endpoint de hard delete é separado: `POST /api/v1/cadastros/pessoas/{id}/hard-delete/` (apenas superuser, com motivo obrigatório no body, escreve em `audit_log`).

### Cascade vs SET NULL

Quando entidade A é soft-deletada e B tem FK A:
- **Default GO:** `on_delete=PROTECT` — não deixa soft-deletar A se há B ativos referenciando (regra de domínio explícita; consistência com legado em `Conta::onBeforeDelete`)
- Service de delete deve checar dependências e levantar `DomainException` com mensagem útil ("Não é possível excluir esta pessoa: existem 3 pedidos vinculados.")

## Drivers

- Discovery §4.4 + tabela §6: legado usa `deleted_at` em quase tudo — manter padrão
- Multi-tenant: hard delete cria buracos em FKs (relatórios históricos quebram); soft delete preserva integridade referencial
- LGPD: direito ao esquecimento existe — hard delete sob demanda (justificável e auditado) atende sem violar default
- Auditoria/forense: poder reconstruir histórico depois é valioso

## Alternatives Considered

| Opção | Por quê não |
|---|---|
| Hard delete sempre | Quebra relatórios; perde histórico; LGPD ainda exige logs auditáveis (ironicamente, soft + audit é melhor) |
| Sem manager filtrado (filtra na hand toda vez) | Primeira que esquecer mostra dado deletado |
| `is_deleted` boolean (em vez de timestamp) | Perde "quando foi deletado" — útil para retenção/restore |
| Tabela espelho `pessoa_deleted` (move on delete) | Complexidade desnecessária; FKs ficam inconsistentes |
| `django-safedelete` lib pronta | Decentemente mantida, mas adiciona dep externa para algo que cabe em 30 linhas; rolar próprio (10 linhas em mixin) é mais didático |

## Consequences

- **Positiva:** "deletei errado" é recuperável (até a política de retenção)
- **Positiva:** integridade referencial preservada (FKs apontam sempre para algo)
- **Positiva:** relatórios históricos não somem
- **Negativa:** queries naïve sem `objects` (manager) podem retornar soft-deleted — importância do `objects` ser **default** que filtra
- **Negativa:** `UNIQUE` precisa de `condition` em todo unique constraint (CPF, cod_barras, etc.) — esquecer cria falso positivo de duplicidade
- **Negativa:** retenção de dados cresce — política precisa existir (ex: hard-delete soft-deletados >5 anos via job — fora de escopo do piloto, mas acordar agora)
- **Negativa:** `select_related/prefetch_related` para FK em soft-deletado pode trazer NULL surpresa quando a relação foi deletada (pessoa endereço deletada mas pessoa ativa)

## What agents MUST do

- **TODO** novo model de domínio: herdar `SoftDeleteMixin`
- **TODO** unique constraint em campo opcional: `condition=Q(deleted_at__isnull=True) & Q(<campo>__isnull=False)` — sempre
- **TODO** service de delete: validar dependências (queries explícitas) → levantar `DomainException` se há blockers ativos → chamar `obj.delete()` (soft)
- **TODO** restore via service dedicado, com audit log
- **TODO** Grid escreve teste: criar → soft delete → assert não aparece em `objects.all()` → assert aparece em `all_records.filter(...)` → criar outra com mesmo documento na mesma empresa (deve passar) → restaurar a primeira (deve falhar com IntegrityError pelo constraint)

## What agents MUST NEVER do

- **NUNCA** chamar `Model.objects.delete()` (queryset bulk delete) em código de domínio — bypassa o mixin (Django bulk delete não chama `instance.delete()`); usar `for x in qs: x.delete()` ou implementar bulk soft delete custom (`qs.update(deleted_at=now())`) explicitamente
- **NUNCA** usar `all_records` em endpoint exposto sem checar superuser
- **NUNCA** comparar `deleted_at` com `==` em SQL — sempre `IS NULL`/`IS NOT NULL` (Django ORM `__isnull=True/False`)
- **NUNCA** definir `UNIQUE(documento)` em model com soft delete sem `condition`

## References

- `/home/evonexus/go_mini_erp_src/app/model/Pessoa.php:9` — `const DELETEDAT = 'deleted_at';` — padrão legado
- `/home/evonexus/go_mini_erp_src/app/model/Conta.php:525-546` — `onBeforeDelete` checa dependências antes de deletar — GO porta como check em service
- `/home/evonexus/go_mini_erp_src/app/database/minierp-pgsql.sql:81,111,290,349,391,413,463,527` — `deleted_at` presente em múltiplas tabelas no schema legado
- PRD §C5 + CA-05 — soft delete obrigatório

---

# Decisão 8 — Workflow data-driven cross-módulo (tabelas `estado_*` + `matriz_transicao_*`)

## Decision

Workflows de máquina de estado (Pedido de Venda, Ordem de Produção, Entrega/Expedição, e qualquer futuro como Cobrança, Compra) seguem **um padrão único**:

### Schema base por workflow

Para cada entidade `<X>` com workflow:

```
tabela: estado_<X>
  id              UUID PK
  nome            VARCHAR(60) UNIQUE-by-empresa-or-global
  cor             VARCHAR(20)         (hex / token)
  ordem           INT
  is_initial      BOOLEAN
  is_final        BOOLEAN
  permite_edicao  BOOLEAN
  permite_exclusao BOOLEAN
  setor           VARCHAR(60) NULL    (gatekeeper opcional)
  active          BOOLEAN
  created_at, updated_at, deleted_at
  empresa_id      UUID NULL           (NULL = global; NOT NULL = customizado)

tabela: matriz_transicao_<X>
  id                          UUID PK
  estado_origem_id            FK → estado_<X>
  estado_destino_id           FK → estado_<X>
  nome_acao                   VARCHAR(100)    (ex: "APROVAR", "CANCELAR")
  action_method               VARCHAR(200)    (callable do service: "PedidoService.aprovar")
  finaliza_etapa              BOOLEAN
  empresa_id                  UUID NULL
  
tabela: estado_<X>_aprovador (opcional)
  id, estado_<X>_id, aprovador_id (FK system_user_role)
```

### `WorkflowService` base genérico

`apps/core/workflows/service.py`:

```
class WorkflowService(ABC, Generic[T]):
    """T = entidade do workflow (Pedido, OrdemProducao, Entrega)"""
    
    @abstractmethod
    def get_estado_table(self) -> Type[Model]: ...   # ex: EstadoPedidoVenda
    @abstractmethod
    def get_matriz_table(self) -> Type[Model]: ...
    @abstractmethod
    def get_action_resolver(self) -> Callable[[str], Callable]: ...  # mapa "PedidoService.aprovar" → método
    
    def get_acoes_disponiveis(self, entidade: T, user: User) -> list[Acao]:
        # 1. validação setor (gatekeeper)
        # 2. validação aprovador
        # 3. busca matriz onde estado_origem == entidade.estado_atual
        # 4. retorna lista de ações
    
    def transicionar(self, entidade: T, acao_id: UUID, user: User, payload: dict) -> T:
        # 1. validar acao está em get_acoes_disponiveis
        # 2. dispatch action_method do action_resolver
        # 3. atualizar entidade.estado_id ← estado_destino
        # 4. registrar histórico (tabela <X>_historico)
        # 5. emitir signal `workflow_transitioned` (audit + notificações)
```

Implementações concretas (em cada módulo):
- `apps.vendas.services.PedidoWorkflowService(WorkflowService)`
- `apps.producao.services.OrdemProducaoWorkflowService(WorkflowService)`
- `apps.expedicao.services.EntregaWorkflowService(WorkflowService)`

### Notificações declarativas

Tabela `workflow_notification_rule` cross-workflow:
```
id, workflow_type ('pedido' | 'ordem_producao' | 'entrega'),
estado_id, evento ('on_enter' | 'on_exit'),
notification_template_id, notification_channel_id, empresa_id
```

`workflow_transitioned` signal → handler busca regras matching → enfileira em Celery task `send_workflow_notification.delay(rule_id, entidade_id)`.

### Configuração via fixture e UI admin

- **Seeds iniciais** por workflow em `fixtures/workflow_<X>.json` — estados padrão, transições padrão
- **UI admin** (em fase posterior, não no piloto): operador edita estados/transições por empresa via tela; mudanças geram nova versão (`workflow_version` opcional, decisão diferida)

## Drivers

- Discovery §4.1: workflow data-driven do legado é **excelente** — preservar
- Discovery Q7 + Q8: redesenhar mantendo conceito (não copiar estados literais)
- DRY: 3 workflows (Pedido, Produção, Entrega) compartilham 90% da estrutura — padrão único elimina triplicação
- Configurável por empresa: empresa A pode ter um estado custom (ex: "AGUARDANDO RESPONSÁVEL FISCAL") sem mudança de código

## Alternatives Considered

| Opção | Por quê não |
|---|---|
| Workflow hard-coded em código (enum + if-elif) | Cada empresa que pede etapa custom = release; legado evitou isso por bom motivo |
| Lib pronta (`django-fsm`, `viewflow`) | Ótimas, mas decisões opacas (especialmente `viewflow` que é pesado); rolar próprio em ~200 linhas é viável e didático |
| BPMN engine (Camunda, etc.) | Massive overkill; ERP não é orquestrador de processos formais |
| Estados em código + transições em tabela | Inconsistência: se um pode ser configurado, ambos devem |

## Consequences

- **Positiva:** novo workflow (e.g., Compra) é "criar `EstadoCompra` + `MatrizTransicaoCompra` + concretar `WorkflowService`" — talvez 100 linhas
- **Positiva:** empresa customiza fluxo via configuração, não via release
- **Positiva:** notificações declarativas — operador adiciona "notificar fiscal quando entrar em FATURADO" sem código
- **Negativa:** debug é mais difícil — "por que o pedido travou?" exige consultar matriz + aprovador (não basta ler código)
- **Negativa:** `action_method = "PedidoService.aprovar"` é string-as-callable — vulnerável a refactor (renomear método quebra o seed); mitigação: registry explícito (`workflow_actions.register('pedido.aprovar', PedidoService.aprovar)`)
- **Negativa:** primeira implementação tem custo de generalização — se só Pedido tivesse workflow, seria mais simples não generalizar; a estimativa de 3 workflows justifica
- **Negativa:** versionamento de workflow não está no escopo — alterar matriz depois de pedidos em curso pode quebrar fluxos (mitigação: migrar pedidos abertos manualmente; em fase posterior, considerar `workflow_version_id` em cada entidade)

## What agents MUST do

- **TODO** novo módulo com workflow: herdar `WorkflowService`, **não** criar lógica solta no service do módulo
- **TODO** todo `action_method` é registrado em `apps/<modulo>/workflow_actions.py` via decorator `@workflow_action('pedido.aprovar')` — registry explícito
- **TODO** seed inicial em `fixtures/workflow_<X>_default.json`
- **TODO** transição de estado **sempre** via `service.transicionar(...)` — nunca `pedido.estado_id = X; pedido.save()` direto (bypassa validação + histórico + notificação)
- **TODO** todo workflow tem tabela `<X>_historico` (entidade_id, estado_de, estado_para, acao, user_id, timestamp, payload)

## What agents MUST NEVER do

- **NUNCA** hard-codear estado em código (`if pedido.estado.nome == 'FINALIZADO': ...`) — usar `is_final` ou comparar via constante de seed (`EstadoPedido.FINALIZADO_ID` setado no seed e fixado por convenção)
- **NUNCA** alterar `pedido.estado_id` fora de `WorkflowService.transicionar(...)`
- **NUNCA** registrar histórico manualmente — `transicionar()` faz
- **NUNCA** omitir signal `workflow_transitioned` ao adicionar workflow novo — notificações dependem dele

## References

- `/home/evonexus/go_mini_erp_src/app/database/minierp-pgsql.sql:156-178` — schema `estado_pedido_venda` + `estado_pedido_venda_aprovador` legado
- `/home/evonexus/go_mini_erp_src/app/database/minierp-pgsql.sql:252-261` — schema `matriz_estado_pedido_venda` legado
- `/home/evonexus/go_mini_erp_src/app/service/grafix/vendas/WorkflowService.php:40-103` — algoritmo `getAcoesDisponiveis` (gatekeeper setor + aprovador) — porta para `WorkflowService.get_acoes_disponiveis`
- `/home/evonexus/go_mini_erp_src/app/database/minierp-pgsql.sql:180-194` — `estado_producao_item` com `is_start/is_work/is_paused/is_waiting/is_end` — padrão de "flags semânticas" em estados; GO substitui por `is_initial/is_final` simples + flags específicas em estado_<X> quando necessário
- Discovery §4.1 + Q7 + Q8

---

# Decisão 9 — `ordem_producao` desacoplada do pedido (mudança de schema vs legado)

## Decision

A **Ordem de Produção** (OP) passa a ser uma entidade **independente**, não um campo em `pedido_venda_item`. Isso é **a maior mudança de schema vs legado** e tem efeitos cascata em estoque, expedição e relatórios.

### Schema GO

```
tabela: ordem_producao
  id                  UUID PK
  empresa_id          UUID FK
  numero              VARCHAR (numero curto legível, único por empresa)
  origem              ENUM ('PEDIDO', 'ESTOQUE', 'MANUAL')
  pedido_venda_id     UUID FK NULLABLE  (preenchido só quando origem=PEDIDO)
  estado_id           UUID FK estado_ordem_producao
  motivo_origem       TEXT NULL          (ex: "ruptura abaixo do mínimo", "decisão manual do gestor X")
  data_planejada      DATE NULL
  data_inicio         TIMESTAMP NULL
  data_conclusao      TIMESTAMP NULL
  observacao          TEXT NULL
  created_by, updated_by, created_at, updated_at, deleted_at

tabela: ordem_producao_item
  id                       UUID PK
  ordem_producao_id        UUID FK
  produto_id               UUID FK produto      (produto a ser fabricado)
  quantidade               DECIMAL
  quantidade_produzida     DECIMAL DEFAULT 0
  estado_item_id           UUID FK estado_producao_item
  pedido_venda_item_id     UUID FK NULLABLE     (vínculo opcional ao item de venda original)

tabela: ordem_producao_item_mp     (BoM — bill of materials)
  id                       UUID PK
  ordem_producao_item_id   UUID FK
  produto_id               UUID FK produto      (matéria-prima)
  quantidade_necessaria    DECIMAL
  quantidade_consumida     DECIMAL DEFAULT 0

tabela: ordem_producao_historico
  id, ordem_producao_id, evento, payload, user_id, created_at
```

### Triggers de criação automática (em service)

```
class OrdemProducaoService:
    def gerar_a_partir_de_pedido(self, pedido_id) -> OrdemProducao | None:
        """Chamado em PedidoVendaService quando pedido entra em estado APROVADO.
           Lê itens do pedido + BoM dos produtos + estoque atual; gera OP só
           para itens cuja produção é necessária (se há estoque suficiente, não gera)."""
    
    def gerar_a_partir_de_ruptura(self, produto_id, quantidade) -> OrdemProducao:
        """Chamado por job que detecta produto abaixo do estoque mínimo
           OU por endpoint manual."""
    
    def concluir(self, ordem_id) -> None:
        """1. Validar todos os itens em estado is_end
           2. Para cada item: registrar movimento_estoque ENTRADA (qtde_produzida)
           3. Para cada MP de cada item: registrar movimento_estoque SAIDA (qtde_consumida)
           4. Se origem=PEDIDO: notificar PedidoWorkflowService que a produção concluiu
              (signal `producao_concluida` → PedidoWorkflowService transiciona se aplicável)
           5. Atualizar OP estado para FINALIZADA"""
```

### Conexão com estoque

`movimento_estoque` agora referencia `ordem_producao_item_id` (FK opcional) **e** `pedido_venda_item_id` (FK opcional, mantido para vendas diretas sem produção). Concluir uma OP gera N movimentos:
- 1 movimento ENTRADA por `ordem_producao_item` (produto acabado)
- N movimentos SAIDA por `ordem_producao_item_mp` (matérias-primas consumidas)

### Conexão com pedido (quando `origem=PEDIDO`)

Pedido **não tem mais** campo `estado_producao_item_id` em `pedido_venda_item`. Em vez disso:
- `OrdemProducaoItem.pedido_venda_item_id` aponta de volta (1 PVI → 0..1 OPI)
- Status visível "este item está em produção" deriva da existência de OPI ativa: `pvi.ordem_producao_item.exists() and not finalized`
- View do pedido faz `prefetch_related('itens__ordens_producao_itens')` para mostrar status

## Drivers

- Discovery Q8: maior mudança arquitetural; legado acopla produção a `pedido_venda_item.estado_producao_item_id`
- Modelo 2 (reposição de estoque) **não cabe** no design legado — exige OP sem pedido
- Empresas com produção contínua (sacos de ração 60kg) precisam produzir antes de pedir; pedido apenas dispara expedição
- Empresas com produção sob encomenda também ficam servidas (origem=PEDIDO mantém o fluxo)
- Desacoplar permite agrupar produção: 1 OP pode atender N pedidos (otimização futura — design já comporta)

## Alternatives Considered

| Opção | Por quê não |
|---|---|
| Manter modelo legado (`pedido_venda_item.estado_producao_item_id`) | Não atende reposição de estoque (Modelo 2); funciona só para sob-demanda |
| OP **só** para reposição; pedido sob-demanda mantém legado | Dois modelos paralelos = dupla manutenção; falha em "OP atende múltiplos pedidos" |
| OP herda de Pedido (polimorfismo) | Hierarquia ruim; pedido tem cliente, OP não tem; relações forçadas |
| OP via tabela genérica `tarefa_producao` | Perde shape específico de produção (BoM, qtde_produzida, MP); over-generalization |

## Consequences

- **Positiva:** suporta reposição contínua + sob demanda no mesmo módulo
- **Positiva:** OP pode agrupar pedidos (otimização produtiva — fora de escopo do piloto, design comporta)
- **Positiva:** estoque tem fonte clara (OP concluída gera movimento) — relatório de produtividade direto
- **Negativa:** **schema diferente do legado** — agentes que conheçam o legado não podem copiar 1:1
- **Negativa:** migração de dados do legado para GO (mesmo decidido como out-of-scope no Q5) ficou impossível mecanicamente — mas Q5 já decidiu sem dados
- **Negativa:** mais tabelas, mais relações — queries de "status do pedido" agora atravessam item → ordem_producao_item → ordem_producao
- **Negativa:** trigger de criação automática de OP a partir de pedido aprovado é regra explícita — esquecer de chamar `OrdemProducaoService.gerar_a_partir_de_pedido` em `PedidoWorkflowService.aprovar` deixa pedido pendurado sem produção
- **Negativa:** BoM (`ordem_producao_item_mp`) implica modelar matérias-primas por produto — schema da Decisão 9 menciona, mas o **schema-fonte** do BoM (`produto.composicao`?) não está definido aqui — fica como follow-up de MIG-04 (Estoque) ou MIG-05 (Produção)

## What agents MUST do

- **TODO** PedidoWorkflowService.aprovar: chamar `OrdemProducaoService.gerar_a_partir_de_pedido(pedido_id)` (ou equivalente trigger via signal)
- **TODO** Job/heartbeat futuro: detectar produto abaixo do mínimo → criar OP por reposição
- **TODO** Endpoint manual: `POST /api/v1/producao/ordens-producao/` aceita `origem='MANUAL'` para criação direta
- **TODO** Concluir OP: **uma transação** que cria todos os `movimento_estoque` + atualiza estados + dispara signals
- **TODO** Em telas de pedido: mostrar status produção via prefetch — não query N+1

## What agents MUST NEVER do

- **NUNCA** mexer em `produto.qtde_estoque` direto — sempre via `movimento_estoque` (a quantidade é derivada do somatório); pedido aprovado não baixa nada por si só, OP concluída sim
- **NUNCA** confundir `OrdemProducaoItem` com `PedidoVendaItem` — são entidades diferentes em apps diferentes (`apps.producao` vs `apps.vendas`)
- **NUNCA** soft-deletar OP em estado `EM EXECUÇÃO` — service valida (DomainException)
- **NUNCA** criar OP sem `origem` (campo NOT NULL); valor default é responsabilidade da camada de service, não do model

## References

- `/home/evonexus/go_mini_erp_src/app/model/PedidoVendaItem.php:21` — `parent::addAttribute('estado_producao_item_id');` — campo legado a ser removido em GO
- `/home/evonexus/go_mini_erp_src/app/database/minierp-pgsql.sql:263-273` — `movimento_estoque` legado tem `pedido_venda_item_id`; GO adiciona `ordem_producao_item_id`
- `/home/evonexus/go_mini_erp_src/app/service/grafix/EstoqueService.php:37-63` — TODOs do legado para `registrarSaidaMateriaPrima`/`registrarEntradaProdutoAcabado` — GO **implementa** isso na conclusão da OP, não em iniciar/concluir item de pedido
- `/home/evonexus/go_mini_erp_src/app/service/grafix/producao/ProducaoService.php:78-86` — legado: `iniciarOuRetomarProducao` chama `registrarSaidaMateriaPrima` no item de pedido — GO move essa responsabilidade para conclusão da OP, com baixa em batch
- Discovery Q8 — descreve o redesenho

---

# Decisão 10 — Multi-tenant Alternativa B: schema por Conta (django-tenants)

## Decision

Um único banco de dados PostgreSQL (`go_control_db`) com dois níveis de schema:

- **`public`** — schema da plataforma: identidade (`User`, `Membership`, `Modulo`, `ContaModulo`, `Papel`, `MembershipPapel`, `MigrationRun`, `Conta`, `PlatformFlag`). Usado por `SHARED_APPS`.
- **`tenant_{cnpj_14_digitos}`** — um schema por Conta (ex: `tenant_12345678000195`). Contém todas as tabelas de domínio ERP. Usado por `TENANT_APPS`.

### Hierarquia dentro do schema de Conta

```
Conta (1)
└── Empresa Matriz (1)
    └── Empresas Filiais (0..N)
```

Todas as empresas de uma Conta compartilham o mesmo schema. O `empresa_id` (FK local) distingue registros entre empresas dentro do schema.

### Roteamento de schema (obrigatório por subdomínio)

Todo acesso ao ERP é via subdomínio: `{conta_slug}.gocontrol.com.br`. O middleware django-tenants resolve o schema pelo hostname. Acesso sem subdomínio válido → 404.

O JWT inclui `ctx.schema = "tenant_12345678000195"` e o middleware valida que `connection.tenant.schema_name == claim['ctx']['schema']` em toda request autenticada.

### SHARED_APPS vs TENANT_APPS

```python
SHARED_APPS = [
    'django_tenants',
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'apps.platform',     # User, Membership, Modulo, ContaModulo, Papel, MigrationRun
    'apps.accounts',     # Conta (TenantMixin)
]

TENANT_APPS = [
    'apps.cadastros',
    'apps.vendas',
    'apps.estoque',
    'apps.producao',
    'apps.financeiro',
    # todos os módulos ERP...
]
```

### Modelo Conta (TenantMixin obrigatório)

```python
from django_tenants.models import TenantMixin, DomainMixin

class Conta(TenantMixin):
    id           = UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nome         = CharField(max_length=200)
    cnpj_matriz  = CharField(max_length=14, unique=True)  # 14 dígitos sem máscara
    slug         = SlugField(unique=True)                 # para subdomínio
    plano        = CharField(max_length=50)
    ativo        = BooleanField(default=True)
    auto_create_schema = True
    created_at   = DateTimeField(auto_now_add=True)

class Domain(DomainMixin):
    pass  # slug.gocontrol.com.br → schema
```

Schema name derivado: `schema_name = f"tenant_{cnpj_matriz_14_digitos}"`.

### Backup por Conta

```bash
pg_dump -n tenant_12345678000195 go_control_db > backup_conta_X.sql
```

## Drivers

- D11 (sessão 2): Alternativa B escolhida explicitamente após análise Apex + Raven que rejeitou Alternativa A (banco separado por módulo)
- JOINs entre tabelas da mesma Conta são nativos (mesmo schema) — sem necessidade de API cross-service
- Backup granular por `pg_dump -n schema` sem reconfigurar conexões
- django-tenants é a lib mais madura para PostgreSQL schema-per-tenant no ecossistema Django 5

## Alternatives Considered

| Opção | Por quê não |
|---|---|
| Banco separado por módulo por cliente (Alternativa A) | Rejeitado: JOINs cruzados impossíveis em ERP, explosão de conexões, migration inviável (250+ bancos com 50 clientes) |
| Row-level isolation (mesmo schema, `conta_id` em toda tabela) | Sem isolamento real — bug de filtro vaza todos os clientes |
| Schema + RLS sem django-tenants | RLS como safety net OK, mas roteamento primário é por schema gerenciado pelo django-tenants |

## Consequences

- **Positiva:** isolamento real por Conta — bug em query não vaza dados de outro cliente
- **Positiva:** JOINs nativos entre tabelas ERP do mesmo cliente
- **Positiva:** backup por `pg_dump -n schema` simples e granular
- **Negativa:** migrations tenant exigem loop por Conta (mitigado por Celery, Decisão 14)
- **Negativa:** django-tenants + PgBouncer exigem session mode (ver Decisão 12)
- **Negativa:** queries cross-Conta (agregações de plataforma) não são SQL nativo

## What agents MUST do

- **TODO** todo app de domínio ERP deve estar em `TENANT_APPS`, nunca em `SHARED_APPS`
- **TODO** modelos de plataforma (User, Membership, etc.) sempre em `SHARED_APPS`
- **TODO** middleware chain: `TenantMiddleware` antes de qualquer middleware de auth
- **TODO** criar Conta via Celery task (schema creation é síncrona no django-tenants — descarregar do request cycle)
- **TODO** RLS como safety net em produção (detect bugs de config)

## What agents MUST NEVER do

- **NUNCA** declarar FK cross-schema (tabela tenant → User da public) — usar UUID lógico
- **NUNCA** usar `django.db.connection.set_schema(...)` manualmente fora do middleware
- **NUNCA** colocar model de domínio ERP em `SHARED_APPS`
- **NUNCA** criar Conta sem `schema_name = f"tenant_{cnpj_14_digitos}"`

## References

- Requisitos D11, D12 (sessão 2) — decisão e hierarquia Conta→Empresa
- Apex + Raven (sessão 2) — análise formal Alternativa B vs Alternativa A

---

# Decisão 11 — Unified User System: 1 User global + Membership + Papel (modelo ZOHO)

> **Substitui parcialmente a Decisão 1.** A Decisão 1 ainda é válida em: UUID PK, email como USERNAME_FIELD, argon2, padrão de manager. Os campos `empresa_atual` e M2M `accounts_user_empresas` são **removidos** — substituídos pelos modelos abaixo.

## Decision

### 6 modelos no schema `public`

```python
class User(AbstractBaseUser):
    id                = UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email             = EmailField(unique=True)            # USERNAME_FIELD
    nome              = CharField(max_length=150)
    is_active         = BooleanField(default=True)
    is_platform_staff = BooleanField(default=False)        # acesso ao backoffice da plataforma
    token_version     = PositiveIntegerField(default=0)    # incrementado para revogar tokens do user

class Membership(TimestampMixin):
    user             = ForeignKey(User, on_delete=CASCADE)
    conta            = ForeignKey(Conta, on_delete=CASCADE)
    is_account_owner = BooleanField(default=False)
    status           = CharField(choices=['active','invited','suspended'])
    class Meta:
        unique_together = [('user', 'conta')]

class Modulo(TimestampMixin):
    code          = CharField(unique=True)  # 'erp.financeiro', 'backoffice.account', 'platform.admin'
    surface       = CharField(choices=['platform','account','erp'])
    em_manutencao = BooleanField(default=False)    # maintenance mode por módulo (Decisão 13)
    nome          = CharField(max_length=100)

class ContaModulo(TimestampMixin):
    conta            = ForeignKey(Conta, on_delete=CASCADE)
    modulo           = ForeignKey(Modulo, on_delete=PROTECT)
    ativo            = BooleanField(default=True)
    params_overrides = JSONField(default=dict)     # validado via Pydantic v2 (Decisão 15)
    schema_version   = CharField(max_length=20, blank=True)
    class Meta:
        unique_together = [('conta', 'modulo')]

class Papel(TimestampMixin):
    modulo      = ForeignKey(Modulo, on_delete=CASCADE)
    code        = CharField()      # 'viewer', 'editor', 'admin'
    permissions = JSONField()      # lista de permissões granulares

class MembershipPapel(TimestampMixin):
    membership = ForeignKey(Membership, on_delete=CASCADE)
    papel      = ForeignKey(Papel, on_delete=CASCADE)

class MigrationRun(TimestampMixin):
    conta        = ForeignKey(Conta, on_delete=CASCADE)
    modulo       = ForeignKey(Modulo, on_delete=CASCADE)
    deploy_id    = CharField(max_length=50)
    status       = CharField(choices=['pending','running','success','failed','skipped'])
    error_detail = TextField(blank=True)
    started_at   = DateTimeField(null=True)
    finished_at  = DateTimeField(null=True)
```

### JWT structure (substitui o JWT da Decisão 1)

```json
{
  "sub": "user-uuid",
  "ctx": {
    "type": "account",
    "conta_id": "uuid",
    "schema": "tenant_12345678000195",
    "permissions": ["erp.financeiro.editor", "erp.pessoas.viewer"]
  },
  "token_version": 7,
  "iat": 1746000000,
  "exp": 1746003600
}
```

`ctx.type = "platform"` → acesso ao backoffice. `ctx.type = "account"` → acesso ao ERP de uma Conta.

### Troca de contexto

User com acesso a múltiplas Contas faz `POST /api/v1/auth/switch-conta/` com `conta_id` → recebe novo par de tokens com `ctx.conta_id` e `ctx.schema` atualizados. `token_version` não muda nessa operação.

### Regra de acesso ao backoffice

1. `is_platform_staff = True` → módulos `surface='platform'` (gerenciar Contas, Modulos, billing)
2. `ctx.type = 'account'` + `is_account_owner = True` → módulos `surface='account'` (configurar a própria Conta)

### 9 Guardrails

| # | Guardrail |
|---|---|
| G1 | Subdomínio obrigatório: `{slug}.gocontrol.com.br`. Acesso sem subdomínio válido → 404. |
| G2 | `SHARED_APPS` contém apenas plataforma e identidade. Todo app ERP em `TENANT_APPS`. |
| G3 | Sem FK cross-schema: tabelas tenant usam `criado_por_user_id = UUIDField(db_index=True)` + `criado_por_nome = CharField` denormalizado. Nunca ForeignKey para User. |
| G4 | RLS como safety net em produção em toda tabela tenant. |
| G5 | Token versioning: middleware valida `claim['token_version'] == user.token_version`. Mismatch → 401. |
| G6 | `acted_as_role` claim: quando platform_staff atua sobre Conta de cliente, JWT inclui `"acted_as_role": "platform_support"`. |
| G7 | Platform staff policy: `is_platform_staff=True` não dá acesso a schemas tenant automaticamente. Impersonation via endpoint dedicado (auditado, TTL 2h). |
| G8 | Custom manager: `User.objects` retorna apenas `is_active=True`. `User.all_objects` faz bypass. |
| G9 | Isolation test suite: testes com 2 Contas em schemas reais — user da Conta A nunca vê dados da Conta B. |

## Drivers

- D8 (sessão 2): sistema unificado aprovado — uma conta de usuário por pessoa, múltiplos contextos
- Sistema split (3 modelos separados) rejeitado: sync bugs, múltiplas senhas, incompatibilidade com django-tenants
- `token_version` por User: revogação imediata sem blocklist
- `platform_token_version` no Redis: invalida todos os tokens simultaneamente em manutenção global

## Alternatives Considered

| Opção | Por quê não |
|---|---|
| 3 modelos separados (PlatformAdmin, AccountManager, ERPUser) | Sync bugs, múltiplas senhas, complexidade de migração entre papéis |
| User replicado por schema de Conta | Inviável: gerenciar permissões cross-conta exige acesso centralizado |
| RBAC com roles hard-coded | Não suporta customização por empresa |

## Consequences

- **Positiva:** uma conta de usuário por pessoa — sem confusão de "qual senha?"
- **Positiva:** revogação imediata via `token_version` sem overhead de Redis por token individual
- **Positiva:** permissões granulares por módulo por Conta
- **Negativa:** Decisão 1 (User com `empresa_atual`) parcialmente invalidada — código escrito com base em D1 precisa ser revisto
- **Negativa:** JWT mais rico — claims precisam ser extraídos corretamente em middleware
- **Negativa:** Membership + MembershipPapel = 2 JOINs para "quais permissões?" — mitigado por denormalizar `permissions` no JWT

## What agents MUST do

- **TODO** Bolt no Step 1b: criar os 6 modelos no schema `public` (SHARED_APP `apps.platform`)
- **TODO** middleware de auth: extrair `ctx.schema` do JWT e validar contra `connection.tenant.schema_name`
- **TODO** permissões: verificar em `ctx['permissions']` do JWT — **não** vai ao banco em cada request
- **TODO** impersonation: `POST /api/v1/auth/impersonate/` requer `is_platform_staff=True`, TTL máximo 2h, registra em audit_log
- **TODO** revogação: `user.token_version = F('token_version') + 1; user.save(update_fields=['token_version'])`

## What agents MUST NEVER do

- **NUNCA** declarar ForeignKey de tabela tenant para User — guardrail G3 é inegociável
- **NUNCA** interpretar `is_platform_staff=True` como permissão para acessar schemas tenant diretamente
- **NUNCA** comparar permissões indo ao banco em cada request — usar `ctx.permissions` no JWT
- **NUNCA** criar novo modelo de usuário paralelo (ex: `ERPUser`) — extensão de contexto é via Membership

## References

- Requisitos D8 (sessão 2) — aprovação do modelo unificado
- Requisitos §9 — 9 guardrails formais do Unified User System
- Decisão 1 (este ADR) — User base (UUID, email, argon2) ainda válido; `empresa_atual` removido

---

# Decisão 12 — PgBouncer em session mode (não transaction)

## Decision

O PgBouncer que serve o GO Control ERP deve ser configurado com **`pool_mode = session`**.

O django-tenants usa `SET search_path = tenant_schema, public` para rotear queries ao schema correto. Esse comando é **session-scoped** no PostgreSQL — não sobrevive à troca de conexão que ocorre em `transaction mode` do PgBouncer.

Em `transaction mode`, cada transação pode receber uma conexão diferente do pool, perdendo o `search_path` setado anteriormente. O resultado é queries roteadas para o schema errado silenciosamente.

**Configuração mínima:**

```ini
[databases]
go_control_db = host=localhost dbname=go_control_db

[pgbouncer]
pool_mode = session          ; OBRIGATÓRIO
max_client_conn = 1000
default_pool_size = 20
server_idle_timeout = 600
```

## Drivers

- D2 (sessão 2): escolha explícita após análise de compatibilidade django-tenants + PgBouncer
- django-tenants docs: "PgBouncer in transaction mode is NOT compatible with django-tenants"
- session mode preserva `search_path` durante toda a sessão do cliente

## Alternatives Considered

| Opção | Por quê não |
|---|---|
| PgBouncer em transaction mode | Incompatível com django-tenants (perde search_path entre transações) |
| Sem PgBouncer (conexão direta) | Cada request Django abre conexão PostgreSQL — insustentável em produção com N tenants |

## Consequences

- **Positiva:** django-tenants funciona corretamente
- **Negativa:** session mode tem multiplexação menor que transaction mode — requer `server_idle_timeout` bem configurado

## What agents MUST do

- **TODO** `docker-compose.yml`: incluir serviço PgBouncer com `pool_mode = session`
- **TODO** `.env`: `DATABASE_URL` aponta para PgBouncer, não para PostgreSQL diretamente

## What agents MUST NEVER do

- **NUNCA** configurar PgBouncer em `transaction mode` neste projeto
- **NUNCA** conectar Django diretamente ao PostgreSQL em produção

## References

- Requisito D2 (sessão 2)
- django-tenants documentation — seção "Limitations" sobre PgBouncer

---

# Decisão 13 — Maintenance Mode: dois níveis (global + por módulo)

## Decision

O sistema suporta dois níveis independentes de manutenção:

### Nível 1 — Manutenção Global

**Aciona:** operador marca `PlatformFlag(key='maintenance_mode', value='true')` **E** executa `INCR platform:token_version` no Redis.

**Efeito:** qualquer request com `platform_token_version` do token diferente do valor atual no Redis → 503. Operadores com `is_platform_staff=True` são isentos.

**Implementação (cache de 5s — não bate no banco em todo request):**

```python
def _is_global_maintenance() -> bool:
    cached = redis.get('platform:maintenance_flag')
    if cached is None:
        flag = PlatformFlag.objects.filter(key='maintenance_mode', value='true').exists()
        redis.set('platform:maintenance_flag', '1' if flag else '0', ex=5)
        return flag
    return cached == b'1'
```

### Nível 2 — Manutenção por Módulo

**Aciona:** `Modulo.em_manutencao = True`.

**Efeito:** requests para endpoints daquele módulo → 503. Tokens **não são invalidados**. Outros módulos funcionam normalmente.

Cache do estado de módulo: Redis com TTL 30s, invalidado ao salvar o `Modulo`.

```python
class MaintenanceMiddleware:
    def __call__(self, request):
        # Nível 1
        if self._is_global_maintenance() and not request.user.is_platform_staff:
            return JsonResponse({'detail': 'Sistema em manutenção', 'retry_after': 600}, status=503)
        # Nível 2
        if hasattr(request, 'auth') and request.auth:
            module_code = self._extract_module_from_path(request.path)
            if module_code and self._is_module_in_maintenance(module_code):
                return JsonResponse({'detail': f'Módulo {module_code} em manutenção'}, status=503)
        return self.get_response(request)
```

## Drivers

- Sessão 2: manutenção global precisa invalidar tokens (tela de manutenção no re-login); manutenção por módulo não precisa (só bloqueia o módulo específico)
- `platform_token_version` no Redis é mais rápido que iterar todos os Users para incrementar `token_version`

## Alternatives Considered

| Opção | Por quê não |
|---|---|
| Flag em arquivo de config (restart necessário) | Downtime; restart é exatamente o que queremos evitar |
| Blacklist de todos os tokens ativos | N tokens no Redis — impraticável em produção |
| Apenas nível global | Não atende deploy gradual por módulo (Decisão 14) |

## Consequences

- **Positiva:** manutenção global é imediata sem invalidar cada token individualmente
- **Positiva:** manutenção por módulo permite deploy sem derrubar o sistema inteiro
- **Negativa:** cache de 30s no módulo significa que desligar a manutenção demora até 30s para propagar
- **Negativa:** `platform_token_version` no Redis vira dependência — Redis down leva a fail-open

## What agents MUST do

- **TODO** `MaintenanceMiddleware`: após `TenantMiddleware`, antes de auth middleware
- **TODO** `PlatformFlag` model: tabela no schema `public`, cache 5s via Redis
- **TODO** `Modulo.em_manutencao` cache: Redis TTL 30s, invalidado ao salvar

## What agents MUST NEVER do

- **NUNCA** invalidar tokens individuais para manutenção global — usar `platform_token_version`
- **NUNCA** exigir restart para mudar maintenance mode
- **NUNCA** colocar check de `em_manutencao` em código de cada view — responsabilidade do middleware

## References

- Requisitos D6, D7 (sessão 2) — aprovação do design de maintenance mode
- Decisão 11 — `Modulo.em_manutencao` definido ali

---

# Decisão 14 — Deploy policy: gate manual com Celery migration por schema

## Decision

O deploy de versões com migration de schema segue este fluxo obrigatório:

```
1. Operador ativa maintenance mode global (Decisão 13 Nível 1)
2. CI/CD build + push nova imagem Docker
3. Celery task `run_tenant_migrations.delay(deploy_id, modulo_code)`:
   a. Para cada Conta ativa (loop sequencial):
      - Cria MigrationRun(conta, modulo, deploy_id, status='pending')
      - Ativa manutenção do módulo: Modulo.em_manutencao = True
      - Executa: call_command('migrate_schemas', '--schema', conta.schema_name, '--app', app_label)
      - Atualiza MigrationRun.status = 'success' | 'failed'
      - Atualiza ContaModulo.schema_version = nova_versao
4. Backoffice mostra progresso em tempo real: N/Total schemas migrados
5. Operador confirma ("tudo verde") via botão no backoffice
6. Sistema desativa maintenance mode global + por módulo
```

### Rollback

Falha em `MigrationRun` → task para e notifica operador. Rollback automático **não** é suportado na v1 (migration Django não tem rollback transacional confiável cross-schema). Operador decide: corrigir e re-executar para schemas com `status='failed'`.

### Dashboard de progresso

```python
MigrationRun.objects.filter(deploy_id=X).values('status').annotate(count=Count('id'))
# → [{'status': 'success', 'count': 42}, {'status': 'pending', 'count': 8}]
```

## Drivers

- D6 (sessão 2): gate manual aprovado — automação avisa, operador confirma
- N schemas por cliente → migration em Celery distribui o custo sem bloquear request handling
- Progress dashboard dá visibilidade ao operador antes de confirmar

## Alternatives Considered

| Opção | Por quê não |
|---|---|
| `migrate_schemas --executor=multiprocessing` | Possível erro de conexão cross-process com PgBouncer session mode |
| Blue-green deployment (sem maintenance mode) | Requer schema backward-compatible por 2 releases — restrição alta |
| Rollback automático | Django migrations não suportam rollback confiável cross-schema em prod |

## Consequences

- **Positiva:** deploy com visibilidade total — operador sabe N/Total schemas migrados
- **Positiva:** falha em uma Conta não bloqueia as outras
- **Negativa:** em escala (1000 Contas) o loop serial demora — otimização futura: workers paralelos
- **Negativa:** maintenance mode global = downtime total — agendar fora do horário de pico

## What agents MUST do

- **TODO** `tasks/tenant_migration.py`: Celery task com o loop por schema
- **TODO** API: `GET /api/v1/platform/migrations/{deploy_id}/progress/`
- **TODO** Backoffice page: `/backoffice/migrations` — lista deploys, progresso, falhas, botão de confirm

## What agents MUST NEVER do

- **NUNCA** executar `migrate_schemas` em código de aplicação web (fora de Celery)
- **NUNCA** confirmar desativação de maintenance mode antes do operador aprovar
- **NUNCA** criar Conta com schema creation síncrona no request cycle

## References

- Requisito D6 (sessão 2) — fluxo de deploy aprovado
- Decisão 10 — schema por Conta (o que está sendo migrado)
- Decisão 13 — maintenance mode habilitado/desabilitado durante deploy

---

# Decisão 15 — Validação de `ContaModulo.params_overrides` com Pydantic v2

## Decision

Cada módulo define uma `BaseModel` Pydantic v2 que descreve o shape de seus `params_overrides`. Um registry central mapeia `modulo.code → Pydantic model`.

### Registry

```python
# apps/platform/module_params.py
from pydantic import BaseModel

_REGISTRY: dict[str, type[BaseModel]] = {}

def register_params(modulo_code: str):
    def decorator(cls: type[BaseModel]):
        _REGISTRY[modulo_code] = cls
        return cls
    return decorator

def validate_params(modulo_code: str, params: dict) -> dict:
    model_cls = _REGISTRY.get(modulo_code)
    if model_cls is None:
        return params  # módulo sem schema declarado aceita qualquer dict
    return model_cls(**params).model_dump()
```

### Exemplo por módulo

```python
# apps/financeiro/module_params.py
from apps.platform.module_params import register_params
from pydantic import BaseModel, Field
from decimal import Decimal

@register_params('erp.financeiro')
class FinanceiroParams(BaseModel):
    aliquota_iss_padrao:       Decimal = Field(default=Decimal('0.05'), ge=0, le=1)
    dias_vencimento_boleto:    int     = Field(default=5, ge=1, le=90)
    centro_custo_obrigatorio:  bool    = Field(default=False)
```

### Hook no ContaModulo

```python
class ContaModulo(TimestampMixin):
    def clean(self):
        from apps.platform.module_params import validate_params
        try:
            self.params_overrides = validate_params(self.modulo.code, self.params_overrides)
        except ValidationError as e:
            raise DjangoValidationError({'params_overrides': str(e)})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
```

### Auto-discovery

```python
class FinanceiroConfig(AppConfig):
    def ready(self):
        import apps.financeiro.module_params  # dispara @register_params
```

### JSON Schema para frontend

`GET /api/v1/platform/modulos/{code}/params-schema/` retorna `FinanceiroParams.model_json_schema()` — para o backoffice renderizar form dinâmico sem hard-code.

## Drivers

- D19 (sessão 2): Pydantic v2 escolhido sobre jsonschema e marshmallow
- Validação tipada com mensagens de erro claras (operador vê "aliquota_iss_padrao deve ser entre 0 e 1")
- `model_dump()` retorna dict limpo e tipado para persistir no JSONField
- Integração natural com ecosistema Django/DRF moderno em 2026

## Alternatives Considered

| Opção | Por quê não |
|---|---|
| jsonschema (draft-07) | Mensagens de erro fracas, sem conversão de tipos |
| marshmallow | Terceira opção no ecossistema; overhead duplicado se Pydantic entrar em outros lugares |
| Sem validação | Params inválidos quebram o módulo em runtime — discovery tardio de erro |

## Consequences

- **Positiva:** erros de configuração detectados na escrita, não no runtime do ERP
- **Positiva:** type-checking nos params schemas via IDE
- **Positiva:** endpoint JSON Schema permite form dinâmico no backoffice
- **Negativa:** schema de params vira código Python — operador não edita via SQL; requer endpoint API
- **Negativa:** auto-discovery via `AppConfig.ready()` exige disciplina — módulo sem import não registra (fail-open)

## What agents MUST do

- **TODO** todo módulo com `params_overrides`: criar `apps/<modulo>/module_params.py` com `@register_params`
- **TODO** `AppConfig.ready()`: importar `module_params` do próprio app
- **TODO** Grid: testar que `ContaModulo.save()` com params inválidos levanta `ValidationError` com mensagem útil

## What agents MUST NEVER do

- **NUNCA** acessar `ContaModulo.params_overrides` sem passar pelo schema validado
- **NUNCA** usar `jsonschema.validate()` em módulo que já tem Pydantic model
- **NUNCA** `ContaModulo.objects.create(params_overrides={...})` sem `full_clean()` (bulk create bypassa)

## References

- Requisito D19 (sessão 2) — decisão formal
- Decisão 11 — `ContaModulo` model definido ali

---

# Trade-offs gerais acumulados

Cada decisão acima fechou um trade-off; aqui o saldo macro:

| Trade-off | Escolha | Custo aceito |
|---|---|---|
| Liberdade vs Previsibilidade | Previsibilidade rígida (padrão de módulo, mixins, proxy obrigatório) | Boilerplate alto, curva de aprendizado para devs novos |
| Performance vs Consistência | Consistência (UUID, soft delete, audit) | +5-15% em índices; relatórios históricos pesam |
| Magic vs Explicit | Magic moderada (Manager filtrando empresa_id automaticamente, save() injetando) | Debug exige conhecer o mixin; novato leva ~1d para entender |
| Configurável vs Codificado | Configurável (workflow data-driven) | Debug "por que travou" exige consultar matriz; sem versionamento na v1 |
| Greenfield vs Espelho-do-legado | Greenfield com legado como referência funcional | Não há paridade 1:1; OP desacoplada quebra mental model do legado |
| Isolamento vs Performance | Schema por Conta (isolamento forte) | Migrations em loop, queries cross-Conta exigem Python loop |
| Sistema unificado vs Simplicidade inicial | 1 User global + Membership (ZOHO) | 6 modelos no schema public; JWT mais rico; D1 parcialmente invalidada |
| Maintenance imediato vs Complexidade | platform_token_version Redis + dois níveis | Redis vira dependência de disponibilidade do maintenance mode |

---

# Riscos arquiteturais (não-bloqueantes para o piloto)

| # | Risco | Severidade | Mitigação |
|---|---|---|---|
| AR1 | `ContextVar` empresa_id mal propagado em Celery task → vaza dados cross-tenant em job | **Alto** | Wrapper `@with_empresa_context(empresa_id)` decorator obrigatório em todo task; teste explícito com 2 empresas |
| AR2 | `EmpresaScopedManager` interage de forma inesperada com `select_related` aninhado em FK heterogênea | Médio | Coverage de teste de queryset cross-model em Step 4 |
| AR3 | `action_method` string-as-callable do workflow vulnerável a renomes silenciosos | Médio | Registry explícito (`@workflow_action('...')`); CI test que valida que todo `action_method` em fixtures resolve |
| AR4 | OP desacoplada cria complexidade UX no front (status produção do pedido vem por prefetch) | Médio | Documentar em `coding-standards.md` o pattern de "render status derivado"; teste vitest |
| AR5 | Argon2 dependência nativa pode complicar build em Docker | Baixo | Usar `python:3.12-slim` (Debian-based) com `argon2-cffi` pre-built wheel — testar no Step 1 |
| AR6 | Cobertura ≥80% em service vira "vou cobrir o que é fácil" — qualidade de teste cai | Médio | Lens-reviewer rejeita PR com testes "trivially passing"; mutation testing (`mutmut`) em fase posterior |
| AR7 | `SET search_path` perdido em PgBouncer mal configurado → queries em schema errado silenciosamente | **Alto** | PgBouncer obrigatório em session mode (D12); health check valida `SHOW search_path` no boot |
| AR8 | `token_version` check em todo request → N leituras ao banco por segundo | Médio | Cache `user.token_version` no Redis (TTL 60s) com invalidação explícita no increment |
| AR9 | Auto-discovery de `module_params` via `AppConfig.ready()` — módulo sem import não registra params schema (fail-open) | Médio | CI test que valida que todos os módulos em `TENANT_APPS` têm `module_params` importado no `ready()` |
| AR10 | `auto_create_schema = True` no request cycle (criação de Conta) bloqueia ~2s | Alto (UX) | Criação de Conta via Celery task assíncrona — request retorna 202 Accepted |

---

# Open Questions (não-bloqueantes para o piloto, registrar e diferir)

- [ ] **OQ-A1** — Versionamento de workflow: empresa altera matriz com pedidos em curso — política de "freeze por entidade" ou "migração assistida"? **Diferida para após piloto.** Risco médio em produção real.
- [ ] **OQ-A2** — `Empresa.proxy_fiscal_provider` configuração: armazenar credenciais por empresa em quê? `Empresa.fiscal_credentials` JSON encriptado (django-encrypted-model-fields) ou Vault externo (HashiCorp/AWS Secrets Manager)? **Diferida para MIG-08 (Integrações Fiscais).** Risco alto em prod (LGPD + segurança).
- [ ] **OQ-A3** — Política de retenção de soft-delete: hard-delete depois de quanto tempo? Job de purge precisa existir antes do GO ir a produção. **Diferida para MIG-09 (Compliance).**
- [ ] **OQ-A4** — BoM (Bill of Materials) de produto: schema-fonte de "produto X consome Y matérias-primas" ainda não foi modelado. Hipótese: tabela `produto_bom` (produto_id, mp_id, quantidade, perda_pct). **Diferida para MIG-05 (Produção).** Bloqueia trigger de criação automática de OP.
- [ ] **OQ-A5** — Audit log universal: signal-based ou middleware tipo `simple_history`? **Diferida para MIG-02 (Accounts/Auditoria).**
- [ ] **OQ-A6** — `cidade` carga IBGE completa (~5.500): preferiu-se top200 + endpoint sync no piloto. Em prod, cliente final pode pedir cidade fora do top200 — sync sob demanda + alert? **Diferida para MIG-03.**
- [ ] **OQ-A7** — Cache de `token_version` no Redis: TTL recomendado? TTL longo reduz hits no banco mas aumenta janela de revogação. TTL 60s parece razoável, mas é decisão operacional. **Diferida para MIG-02.**
- [ ] **OQ-A8** — `platform_token_version` Redis down: fail-open (assume sem manutenção) ou fail-closed (bloqueia tudo)? Fail-open é mais seguro para disponibilidade; fail-closed é mais seguro para manutenção. **Diferida para MIG-09.**
- [ ] **OQ-A9** — Migration em loop serial (Decisão 14): threshold de N Contas a partir do qual vale paralelizar workers Celery? Agendar análise quando N > 50 Contas. **Diferida para escala.**
- [ ] **OQ-A10** — `MigrationRun.retry`: retentar apenas schemas com `status='failed'` ou full replay? Retry parcial é mais eficiente; mas exige que migrations sejam idempotentes. Enforçar `RunPython` com `elidable=True` onde possível. **Diferida para MIG-02.**

---

# Follow-ups (ações concretas após este ADR)

- [ ] **F1** — Bolt-executor: aplicar Decisões 1, 2, 5, 7, 10, 11, 12 no Step 1b do plano (Unified User System + django-tenants + PgBouncer + EmpresaScopedModel refactor). **Bloqueia Steps 2-6.** Owner: @bolt-executor + @grid-tester. Prazo: dia 1 do piloto.
- [ ] **F2** — Quill-writer: documentar `agent-instructions.md` final com exemplos do app `cadastros` rodando. Owner: @quill-writer. Prazo: Step 6.
- [ ] **F3** — Lens-reviewer: incluir checklist deste ADR no `[C]code-review-...` do piloto — cada Decisão é um item de checklist explícito. Owner: @lens-reviewer. Prazo: Step 5.
- [ ] **F4** — Apex (eu): produzir ADRs específicos quando MIG-02..MIG-N abrirem decisões fora deste escopo (ex: ADR de auditoria, ADR de schema BoM). Owner: @apex-architect. Prazo: por demanda dos sucessores.
- [ ] **F5** — Raven-critic: revisar este ADR antes da execução do Step 1 (consenso adversarial nas 9 decisões). Owner: @raven-critic. Prazo: 1 dia.
- [ ] **F6** — Atualizar este ADR ao final do piloto com notas de "o que aprendemos" (sessão Retro). Owner: @mirror-retro. Prazo: após Step 6.
- [ ] **F7** — Bolt: implementar `MaintenanceMiddleware` + `PlatformFlag` + `platform_token_version` Redis (Decisão 13). Owner: @bolt-executor. Prazo: Step 1b (antes de qualquer deploy de módulo).
- [ ] **F8** — Bolt: implementar `run_tenant_migrations` Celery task + backoffice de progresso (Decisão 14). Owner: @bolt-executor + @canvas-designer. Prazo: antes do primeiro deploy em staging com dados.
- [ ] **F9** — Grid: criar isolation test suite (guardrail G9) — 2 Contas em schemas reais, user da Conta A nunca vê dados da Conta B. Owner: @grid-tester. Prazo: Step 1b.
- [ ] **F10** — Bolt: criar registry de `module_params` + `@register_params` decorator + `validate_params()` + hook no `ContaModulo.clean()` (Decisão 15). Owner: @bolt-executor. Prazo: Step 1b.

---

# Documentos relacionados (mesmo feature folder)

- [Discovery](./[C]discovery-migracao-minierp-adianti-python-react.md)
- [PRD](./[C]prd-migracao-minierp-adianti-python-react.md)
- [Plan](./[C]plan-migracao-minierp-adianti-python-react.md)
- Repositório-alvo: `/home/evonexus/evo-projects/go-control-erp/` (ainda vazio, será populado no Step 1)
- Guardrails para agentes: `/home/evonexus/evo-projects/go-control-erp/docs/agent-instructions.md`
- Convenções de código: `/home/evonexus/evo-projects/go-control-erp/docs/coding-standards.md`

