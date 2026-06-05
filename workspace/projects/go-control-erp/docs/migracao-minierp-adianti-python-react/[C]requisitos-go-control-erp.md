---
author: oracle
type: requirements
date: 2026-05-06
updated: 2026-05-08
feature: migracao-minierp-adianti-python-react
status: parcialmente_desatualizado
---

# Requisitos Consolidados — GO Control ERP

> ⚠️ **PARCIALMENTE DESATUALIZADO — 2026-05-08**
>
> As seções **3 (Arquitetura de Plataforma)** e **4 (Sistema de Identidade)** deste documento foram
> revisadas pelas decisões D-R01..D-R12 aprovadas em 2026-05-08. Consulte as fontes canônicas:
>
> - **Decisões**: `[C]decisions-redesign-identidade-tenancy.md`
> - **ADR v2**: `[C]architecture-v2-go-control-erp.md`
>
> Itens específicos desatualizados neste arquivo:
> - §3.1: `{conta}.gocontrol.com.br` → **ELIMINADO** (D-R01). URL do ERP é `erp.gocontrol.com.br`
> - §4.2: `ContaModulo` → substituído por `EmpresaModulo` (D-R05)
> - §4.2: `Membership` como vínculo operacional → substituído por `UserEmpresaVinculo` (D-R06)
> - §4.3: Login em 1 etapa → substituído por fluxo de 3 etapas progressivas (D-R09)
> - §4.2: `Conta` como container operacional → `Conta` é entidade de billing apenas (D-R03)
>
> As seções de **stack** (§2) e **módulos funcionais** (§5+) permanecem válidas.

> ~~Documento de referência para o ADR e todos os steps de implementação.~~
> ~~Consolida todas as decisões tomadas nas sessões de discovery, planejamento e alinhamento arquitetural.~~
> ~~**Fonte de verdade.** Qualquer dúvida sobre uma decisão, consultar aqui primeiro.~~
>
> Fonte de verdade atualizada: **`[C]architecture-v2-go-control-erp.md`**

---

## 1. Visão Geral do Projeto

| Campo | Valor |
|---|---|
| **Nome do produto** | GO Control ERP |
| **Repositório** | `/home/evonexus/evo-projects/go-control-erp/` |
| **Origem** | Migração do MiniERP (Adianti Framework 7.5 + PHP 8.2) |
| **Fonte legada** | `/home/evonexus/go_mini_erp_src` (read-only, referência funcional) |
| **Estratégia de dados** | GO parte do zero — sem migração de dados; legado é referência funcional apenas |
| **Escopo final** | 18 módulos do legado + novos módulos, com redesenho de Expedição e Produção |
| **Módulo piloto** | Pessoas + Produtos (primeiro slice end-to-end) |

---

## 2. Tech Stack Aprovado

### Backend
| Componente | Tecnologia | Versão |
|---|---|---|
| Framework web | Django | 5.x |
| API REST | Django REST Framework (DRF) | latest |
| Autenticação JWT | djangorestframework-simplejwt | latest |
| Multi-tenant | django-tenants | latest |
| Task queue | Celery | latest |
| Cache / broker | Redis | 7 |
| Banco de dados | PostgreSQL | 16 |
| Connection pool | PgBouncer | session mode |
| Server WSGI | Gunicorn | latest |
| Proxy reverso | Traefik | latest |
| Containerização | Docker + Docker Compose | latest |

### Frontend
| Componente | Tecnologia |
|---|---|
| Framework | React 18 + TypeScript |
| Build | Vite |
| UI components | PrimeReact |
| CSS | Tailwind CSS |
| Requisições HTTP + cache | TanStack Query (React Query) |
| Formulários | React Hook Form |
| Validação | Zod |
| HTTP client | Axios (com interceptors JWT + auto-refresh) |

### Metodologia de desenvolvimento
- **TDD obrigatório**: @grid-tester escreve testes antes de @bolt-executor implementar
- **Cobertura mínima**: ≥ 80% nos services
- **Padrão de módulo Django**: `models / serializers / services / selectors / views / urls / permissions / tests`
- **Padrão de módulo React**: `pages / components / services / hooks / types / routes.tsx`

---

## 3. Arquitetura de Plataforma — 3 Superfícies

### 3.1. As 3 superfícies da plataforma

```
┌──────────────────────────────────────────────────────────────────────┐
│  BACKOFFICE — /backoffice/platform/                                  │
│  Acesso: Platform Staff (equipe GO Control)                          │
│  • Cria e gerencia Contas (clientes contratantes)                    │
│  • Onboarding de novos clientes                                      │
│  • Maintenance mode global e por módulo                              │
│  • Gerencia catálogos globais (estados, cidades, módulos)            │
│  • Acompanha progresso de migrations/deploys                         │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│  ACCOUNT — /backoffice/account/  (inspiração: ZOHO My Account)      │
│  Acesso: Account Manager (cliente que contratou o GO Control)        │
│  • Gerencia empresas do grupo (matriz + filiais)                     │
│  • Ativa/desativa módulos contratados                                │
│  • Configura parâmetros do ERP da sua conta                          │
│  • Gerencia usuários da conta                                        │
│  • Vê billing e plano contratado                                     │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│  ERP — erp.gocontrol.com.br  ⚠️ [ATUALIZADO D-R01]                  │
│  ~~{conta}.gocontrol.com.br~~ — ELIMINADO em D-R01                   │
│  Acesso: ERP Users (operadores do dia-a-dia)                         │
│  • Acessa apenas módulos habilitados para a Empresa ativa            │
│  • Visão filtrada pela empresa ativa no JWT (conta_id + empresa_id)  │
│  • Schema routing via JWTTenantMiddleware (não hostname)             │
└──────────────────────────────────────────────────────────────────────┘
```

**Importante:** Backoffice (Platform + Account) e ERP são **a mesma aplicação Django**, com rotas e seções separadas. Não são projetos diferentes.

### 3.2. Três tipos de dados

| Tipo | Dono | Exemplos | Schema PostgreSQL |
|---|---|---|---|
| **Globais da plataforma** | Platform Staff | estados, cidades, CFOP, CST, catálogo de módulos | `public` |
| **Da conta** | Account Manager | Conta, Empresas do grupo, usuários, módulos ativos, configs | `public` |
| **De domínio** | ERP Users | Pessoas, Produtos, Pedidos, NF-e, Financeiro | `tenant_{cnpj_14_digitos}` |

---

## 4. Sistema de Identidade Unificado (Decisão Aprovada)

### 4.1. Decisão: Unified User System (modelo ZOHO)

**Uma identidade global por pessoa.** Platform Staff e Account Manager são autorizações (papéis), não tipos de usuário distintos. Um usuário pode ter papéis em múltiplas Contas e superfícies.

Alternativas rejeitadas:
- Split (3 modelos de User separados) — rejeitado: UX ruim, manutenção 3×, sync bugs garantidos
- Modelo com `is_platform_operator` boolean — rejeitado: conflação de contextos

### 4.2. Modelo de dados — identidade (schema `public`, SHARED_APPS)

```python
class User(AbstractBaseUser):
    id              = UUIDField(primary_key=True)
    email           = EmailField(unique=True)          # username global
    nome_completo   = CharField()
    is_platform_staff = BooleanField(default=False)    # acesso ao backoffice platform
    token_version   = PositiveIntegerField(default=0)  # revogação imediata de tokens
    mfa_enabled     = BooleanField(default=False)
    created_at, updated_at

class Conta(TenantMixin, TimestampMixin):  # django-tenants Tenant
    schema_name     = CharField(unique=True)   # 'tenant_12345678000195'
    nome            = CharField()
    cnpj_matriz     = CharField()
    plano           = CharField()
    ...

class Membership(TimestampMixin):          # vínculo User ↔ Conta
    user            = ForeignKey(User)
    conta           = ForeignKey(Conta)
    is_account_owner = BooleanField(default=False)
    status          = CharField(choices=['active','invited','suspended'])
    convidado_por   = ForeignKey(User, null=True)
    class Meta:
        unique_together = [('user', 'conta')]

class Modulo(TimestampMixin):              # catálogo de módulos
    code            = CharField(unique=True)   # 'erp.financeiro', 'backoffice.account'
    surface         = CharField(choices=['platform','account','erp'])
    nome, descricao
    em_manutencao   = BooleanField(default=False)
    manutencao_mensagem = TextField()
    manutencao_iniciada_em = DateTimeField(null=True)

class ContaModulo(TimestampMixin):         # módulos contratados/ativos por Conta
    conta           = ForeignKey(Conta)
    modulo          = ForeignKey(Modulo)
    ativo           = BooleanField(default=True)
    params_overrides = JSONField(default=dict)
    schema_version  = CharField()          # migration aplicada
    class Meta:
        unique_together = [('conta', 'modulo')]

class Papel(TimestampMixin):               # bundle de permissões em um módulo
    modulo          = ForeignKey(Modulo)
    code            = CharField()          # 'viewer', 'editor', 'admin'
    permissions     = JSONField()          # ['ver_lancamento', 'criar_lancamento', ...]
    class Meta:
        unique_together = [('modulo', 'code')]

class MembershipPapel(TimestampMixin):     # User tem este Papel nesta Conta
    membership      = ForeignKey(Membership)
    papel           = ForeignKey(Papel)
    concedido_por   = ForeignKey(User, null=True)
    class Meta:
        unique_together = [('membership', 'papel')]
```

### 4.3. Login e token

**Login único:**
```
POST /auth/login  { email, password }
→ { access_token, refresh_token, available_contexts }
```

`available_contexts` lista superfícies disponíveis para o usuário:
```json
[
  { "type": "platform" },
  { "type": "account", "conta_id": "...", "conta_nome": "ACME", "schema": "tenant_12345678000195" },
  { "type": "account", "conta_id": "...", "conta_nome": "Beta", "schema": "tenant_98765432000111" }
]
```

**JWT com contexto ativo:**
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
  "exp": "..."
}
```

**Permissões resolvidas no momento da emissão do token** — sem hit no banco por request.

**Switch de contexto (troca de Conta ou superfície):**
```
POST /auth/switch-context  { conta_id }
→ { access_token: <novo> }
```

### 4.4. Acesso ao ERP — subdomínio por Conta (obrigatório)

**`{slug_conta}.gocontrol.com.br`** — schema resolvido pelo hostname (django-tenants padrão), não por sessão ou query param. Isso é inegociável: elimina race condition de schema entre abas e previne IDOR cross-tenant.

**Validação no middleware:** `connection.tenant.schema_name == claim['ctx']['schema']` — mismatch retorna 403.

### 4.5. Regra crítica: sem FK de tabelas tenant para User

Modelos em `TENANT_APPS` **nunca** declaram `ForeignKey` para `User` (que está em `SHARED_APPS`). FK cross-schema quebra migrations e dumps.

```python
# CORRETO — em apps tenant
class Lancamento(EmpresaScopedModel):
    criado_por_user_id = UUIDField(db_index=True)    # UUID lógico, SEM FK
    criado_por_nome    = CharField(max_length=150)   # denormalizado

# ERRADO — não fazer isso
class Lancamento(EmpresaScopedModel):
    criado_por = ForeignKey('accounts.User', ...)    # FK cross-schema — PROIBIDO
```

### 4.6. Fluxo de onboarding de novo cliente

```
1. Platform Staff cria Conta no backoffice
2. Sistema cria schema tenant_{cnpj} no PostgreSQL
3. Sistema cria Membership(user=convidado, conta=nova_conta, is_account_owner=True)
   └── se User já existe: só cria o Membership
   └── se User não existe: cria User + Membership + envia convite por email
4. Sistema cria Empresa matriz + empresas filiais (se informadas)
5. Sistema ativa módulo 'erp.pessoas' por padrão (ContaModulo)
6. Usuário owner recebe email com link para:
   └── definir senha (se User novo)
   └── acessar Account: {conta}.gocontrol.com.br/account/
   └── acessar ERP:     {conta}.gocontrol.com.br/
```

### 4.7. Os 9 guardrails inegociáveis

| # | Guardrail | Severidade se ignorado |
|---|---|---|
| G1 | **Subdomínio por Conta** — schema resolvido pelo hostname | CRÍTICO (IDOR cross-tenant) |
| G2 | **User em `SHARED_APPS`** — FK para User só funciona limpo em public | CRÍTICO (migrations quebram) |
| G3 | **Sem FK de tenant → User** — usar `user_id` UUID + `nome` denormalizado | CRÍTICO (dumps quebram) |
| G4 | **Row-Level Security (RLS)** no PostgreSQL em tabelas tenant com `empresa_id` | ALTO (vazamento se filtro esquecido) |
| G5 | **Token versioning** (`token_version` no User + `platform_token_version` Redis) | ALTO (revogação imediata) |
| G6 | **`acted_as_role` em todo log** de auditoria de operações | ALTO (LGPD Art. 37) |
| G7 | **Platform Staff sem papel de ERP** na mesma conta interna — conta de serviço separada | MÉDIO (auto-escalação de privilégio) |
| G8 | **Manager customizado obrigatório** (`objects.for_conta()`) — `objects.all()` proibido em views; lint rule no CI | MÉDIO (AI agents esquecem filtros) |
| G9 | **Suite de testes de isolamento no CI** — cada papel tenta ler dados de outra Conta, deve falhar | MÉDIO (gate de deploy) |

---

## 5. Arquitetura Multi-tenant — Alternativa B Aprovada

### 5.1. Decisão

**Schema por Conta (Grupo) + `empresa_id` em todos os modelos de domínio.**

- 1 instância PostgreSQL + PgBouncer (session mode)
- Schema `public` → identidade, plataforma, catálogos globais
- Schema `tenant_{cnpj_14_digitos}` → dados de domínio por Conta
- `empresa_id` permanece em todos os modelos de domínio (distingue matriz de filiais dentro do schema)
- `schema_name` = `tenant_{cnpj_14_digitos_da_matriz}` (ex: `tenant_12345678000195`)

### 5.2. Hierarquia empresarial

```
Conta (= Grupo = django-tenants Tenant)
├── schema_name = 'tenant_{cnpj_14_digitos}'
├── cnpj_matriz
│
└── Empresa (individual por CNPJ, dentro do schema)
    ├── conta (FK → Conta)
    ├── tipo: 'matriz' | 'filial'
    ├── empresa_pai (FK → Empresa, null para matriz)
    └── cnpj
```

**Exemplo — grupo com 3 lojas:**
```
Conta: Grupo Auto Peças  →  schema: tenant_12345678000195
├── Empresa: Loja Central (matriz)   empresa_id = uuid-A
├── Empresa: Loja Norte  (filial)    empresa_id = uuid-B
└── Empresa: Loja Sul    (filial)    empresa_id = uuid-C
```

### 5.3. Regra de pertencimento dos dados

| Tipo de dado | `empresa_id` | Quem acessa |
|---|---|---|
| Produto, Cliente, Fornecedor, Categoria | Matriz (uuid-A) | Todas as filiais |
| Venda, Compra, NF-e, Pedido | Filial originadora (uuid-B/C) | Aquela filial; matriz vê consolidado |
| Estoque saldo, Movimentação | Filial (uuid-B/C) | Filial + consolidado via `do_grupo()` |
| Financeiro, Cobrança | Filial (uuid-B/C) | Filial + consolidado via `do_grupo()` |

### 5.4. Querysets padrão

```python
class EmpresaScopedManager(models.Manager):
    def da_empresa(self, empresa_id):
        """Visão de uma empresa específica (1 loja)."""
        return self.get_queryset().filter(empresa_id=empresa_id)

    def do_grupo(self):
        """Visão consolidada do grupo (sem filtro de empresa)."""
        return self.get_queryset()
```

### 5.5. Backup por Conta

```bash
pg_dump -n tenant_12345678000195 go_control_db > backup_acme.sql
```

---

## 6. Sistema de Módulos

### 6.1. Módulos disponíveis na plataforma

| Código | Nome | Surface | Padrão | Dependências |
|---|---|---|---|---|
| `erp.pessoas` | Pessoas | erp | ativo | — |
| `erp.produtos` | Produtos | erp | opt-in | — |
| `erp.financeiro` | Financeiro | erp | opt-in | pessoas |
| `erp.estoque` | Estoque | erp | opt-in | produtos |
| `erp.fiscal` | Fiscal | erp | opt-in | financeiro |
| `erp.producao` | Produção | erp | opt-in | estoque |
| `erp.cobrancas` | Cobranças | erp | opt-in | financeiro |
| `erp.comercial` | Comercial (Pedidos) | erp | opt-in | pessoas, produtos |
| `erp.crm` | CRM | erp | opt-in | pessoas |
| `erp.expedicao` | Expedição | erp | opt-in | estoque |
| `erp.communication` | Chat Interno | erp | opt-in | — |
| `erp.mensageria` | Notificações de Workflow | erp | opt-in | — |
| `erp.documentos` | Gestão de Documentos | erp | opt-in | — |
| `erp.portal_cliente` | Portal do Cliente (externo) | erp | opt-in | comercial |
| `erp.sac` | SAC / Ouvidoria | erp | opt-in | — |
| `backoffice.account` | Gestão de Conta | account | ativo | — |
| `backoffice.platform` | Administração da Plataforma | platform | is_platform_staff | — |

### 6.2. Ativação de módulo por Conta

Quando Account Manager ativa um módulo:
1. Cria/atualiza `ContaModulo(conta, modulo, ativo=True)`
2. Celery task: `bootstrap_modulo_schema.delay(conta_id, modulo_code)` → roda migrations no schema tenant
3. Módulo aparece no menu do ERP para usuários com papel correspondente
4. `ContaModulo.params_overrides` herda `Modulo.params_default` e pode sobrescrever

### 6.3. Herança de parâmetros

```
params_efetivos = {**modulo.params_default, **conta_modulo.params_overrides}
```

---

## 7. Maintenance Mode — Dois Níveis (Decisão Aprovada)

### 7.1. Nível 1 — Plataforma (global)

- Flag: `PlatformFlag(key='maintenance.global', value={enabled, message, started_at})`
- Cache Redis (TTL 30s) + pub/sub para invalidação imediata em todos os workers
- **Invalida todos os tokens JWT** via `platform_token_version` Redis (incrementa)
- Backoffice (`/api/backoffice/*`) continua acessível — bypass por path
- Frontend detecta via interceptor Axios (503) + polling 10s na tela de manutenção

### 7.2. Nível 2 — Por módulo

- Flag: `Modulo.em_manutencao = True` (afeta todas as Contas com o módulo ativo)
- **Não invalida tokens** — usuário continua logado, só aquele módulo fica inacessível
- Outros módulos da Conta funcionam normalmente
- Desmarcamento: automação notifica quando 100% das Contas migraram → operador confirma

### 7.3. Tabela de tracking de migration

```python
class MigrationRun(TimestampMixin):
    conta       = ForeignKey(Conta)
    modulo      = ForeignKey(Modulo)
    deploy_id   = CharField()          # tag/SHA do release
    status      = CharField(choices=['pending','running','success','failed','skipped'])
    from_version, to_version
    started_at, finished_at
    error_message = TextField()
    class Meta:
        unique_together = [('conta', 'modulo', 'deploy_id')]
```

### 7.4. Política de deploy (D6 — Aprovada)

```
[T-0]   1. Operador → POST /api/backoffice/maintenance/modulo/{code}/start
           → Modulo.em_manutencao = True
           → Cache invalidado via Redis pub/sub
        2. Drain de 30s (requests in-flight terminam)

[T+30s] 3. CI/CD sobe novo código (rolling restart dos workers)

[T+2m]  4. Celery dispatcher: enfileira migrate_schema.delay()
           para cada Conta com o módulo ativo (máx 10 paralelas)

[T+X]   5. Backoffice mostra progresso: X de N Contas migradas (polling 5s)

[T+Y]   6. 100% success → notificação para operador

[T+Y+?] 7. Operador valida (smoke test em 1 Conta canário)
           → POST /api/backoffice/maintenance/modulo/{code}/end
           → Modulo.em_manutencao = False

[T+Y+1m] 8. Tráfego volta ao normal. Sessões não foram invalidadas.
```

**Gate manual obrigatório** — automação avisa quando pronto, operador confirma. Sem auto-release (exceto módulos marcados com `auto_release=True` para casos de baixo risco).

### 7.5. API de manutenção (backoffice)

Seguindo o padrão de rotas aprovado em D20 (seção 19):

```
POST   /api/v1/platform/maintenance/global/start        {message, expected_end}
POST   /api/v1/platform/maintenance/global/end
GET    /api/v1/platform/maintenance/global/status
POST   /api/v1/platform/maintenance/modulo/{code}/start {message, deploy_id}
POST   /api/v1/platform/maintenance/modulo/{code}/end
GET    /api/v1/platform/maintenance/modulo/{code}/progress
GET    /api/v1/platform/migration/runs?deploy_id=&status=
POST   /api/v1/platform/migration/runs/{id}/retry
GET    /api/v1/maintenance/status                       (público — frontend polling, sem auth)
```

---

## 8. Infraestrutura e Conexões

### 8.1. PgBouncer — session mode (D2 Aprovado)

- **Modo:** `session` (compatível com `SET search_path` do django-tenants)
- **Por quê não transaction mode:** quebraria o `SET search_path` — schemas varariam entre requests
- PgBouncer como camada obrigatória entre Django e PostgreSQL
- `CONN_MAX_AGE = 0` para aliases dinâmicos de tenant

### 8.2. Schema naming (D1 Aprovado)

- Formato: `tenant_{cnpj_14_digitos}` (ex: `tenant_12345678000195`)
- Sem formatação (sem pontos ou barras do CNPJ)
- Imutável — criado no onboarding, nunca renomeado

---

## 9. Módulos do Legado — Inventário e Decisão

| # | Módulo | Decisão | Justificativa |
|---|---|---|---|
| 1 | admin (auth/users/groups) | **Substituído** | Sistema de identidade unificado (seção 4) substitui |
| 2 | comercial (pedido de venda) | **Reaproveitar** schema + service | PedidoVendaService (404 linhas), WorkflowService portam 1:1 |
| 3 | configuracoes (workflow rules) | **Reaproveitar** schema | Tabelas de estados/transições excelentes; UI descartar |
| 4 | crm (negociação) | **Adaptar** | Conceito bom; lógica nos controllers exige leitura cuidadosa |
| 5 | estoque (produto/movimento) | **Reaproveitar** schema + service | EstoqueService direto; barcode via libs Python |
| 6 | expedicao (entregas) | **Reaproveitar** schema + service | ExpedicaoService (349 linhas) bem-feito; redesenhar UI |
| 7 | financeiro (contas/fluxo) | **Reaproveitar** schema + service | Melhor código do legado; FinanceiroBaixaService |
| 8 | pessoas (cliente/fornecedor) | **Reaproveitar** schema | Entidade central; validação a auditar no controller |
| 9 | producao | **Reaproveitar** schema + service | ProducaoService (252 linhas); REDESENHO arquitetural (§10) |
| 10 | supervisor (notification engine) | **Adaptar** | notification_template/channel → Celery + WhatsApp/Telegram/e-mail |
| 11 | integrações (CEP, CNPJ) | **Adaptar** | Porta em 30min via Proxy pattern |
| 12 | log (access/change/sql) | **Adaptar** | Schema reusável; mecanismo → middleware Django + structlog |
| 13 | communication | **Novo** | Chat interno por usuário/setor (não por pedido) |
| 14 | mensageria | **Novo** | Notificações de workflow via canais externos configuráveis |
| 15 | documentos | **Novo** | Compartilhamento interno + área pública para cliente final |
| 16 | portal_cliente | **Novo** | Portal externo para cliente ver pedidos e boletos (D3 — no escopo) |
| 17 | sac | **Novo — backlog** | Ouvidoria (D5 — no escopo, sem prioridade) |
| 18 | builder | **Descartar** | Ferramenta Adianti |
| 19 | install | **Descartar** | Instalador legado |

### 9.1. Módulos novos — detalhamento

**`erp.communication` — Chat Interno**
- Chat entre usuários organizados por: usuário-a-usuário ou por setor
- **Não** por pedido (apenas notificações de pedido vão para `erp.mensageria`)
- Mensagens persistidas no schema tenant da Conta

**`erp.mensageria` — Notificações de Workflow**
- Dispara alertas quando estados de workflow mudam (pedido aprovado, produção concluída, etc.)
- Canais configuráveis por Conta: WhatsApp (Evolution API), Telegram, e-mail, push interno
- Templates de mensagem configuráveis por estado (`workflow_notification_rule`)
- Reaproveita schema do legado: `notification_template`, `notification_channel`, `workflow_notification_rule`

**`erp.documentos` — Gestão de Documentos**
- Compartilhamento interno: entre setores e usuários da Conta
- Área pública: cliente externo acessa documentos vinculados ao pedido/conta via portal

**`erp.portal_cliente` — Portal do Cliente**
- Área pública com autenticação leve (token por link ou CPF/CNPJ)
- Consulta de pedidos, boletos, status de entrega
- Integrado com `erp.documentos` (download de notas, boletos)

---

## 10. Ordem de Produção — Decisão Arquitetural Crítica

### 10.1. Decisão

**Ordem de Produção (OP) totalmente desacoplada do Pedido de Venda.**

No legado: produção era filha do pedido (`pedido_venda_item.estado_producao_item_id`).
No GO: `OrdemProducao` é entidade independente.

### 10.2. Dois gatilhos para criar uma OP

| Gatilho | Descrição |
|---|---|
| **PEDIDO** | Pedido de venda aprovado → OP criada automaticamente para itens "Fabricar" |
| **ESTOQUE** | Ruptura detectada (saldo < mínimo) ou solicitação manual → OP para reposição |

### 10.3. Ao concluir a OP

1. Baixa automática nas matérias-primas consumidas
2. Entrada automática do produto acabado no estoque
3. Se origem = PEDIDO: verifica se todos os itens do pedido estão prontos → avança estado

---

## 11. Workflow Data-Driven

Estados e transições configuráveis em banco, não hardcoded.

```
estado_{entidade}            ← define cada estado (nome, cor, flags, setor)
matriz_transicao_{entidade}  ← transições válidas (origem → destino, ação disparada)
aprovador_estado             ← quem precisa aprovar para avançar
workflow_notification_rule   ← "ao entrar no estado X, notifique via canal Y com template Z"
```

Entidades com workflow: `pedido_venda`, `ordem_producao`, `entrega`, `negociacao`.

---

## 12. Integrações e Proxy Pattern

### 12.1. Padrão: Strategy + Fallback Router

Múltiplos providers por serviço, fallback automático, circuit breaker, cache Redis.

### 12.2. Proxies aprovados

| Proxy | Providers | Cache |
|---|---|---|
| **Proxy CEP** | ViaCEP → OpenCEP → AwesomeAPI | 30 dias Redis |
| **Proxy CNPJ** | ReceitaWS → CNPJá | TTL curto |
| **Proxy Fiscal** | Focus NFe → Plug Nota → SEFAZ direto | Sem cache (transacional) |
| **Proxy Bancário** | Asaas → Banco Inter | Sem cache (transacional) |

### 12.3. Integrações diretas

| Integração | Uso |
|---|---|
| Bling API | Sync de pedidos, produtos, NF-e |
| Omie API | Sync financeiro, clientes |
| WhatsApp (Evolution API) | Notificações de workflow |
| Telegram Bot | Notificações internas |
| SMTP | E-mail transacional |
| `python-barcode`, `qrcode` | Geração de código de barras e QR |

---

## 13. Segurança — Requisitos Mínimos (Day 1)

| Categoria | Requisito |
|---|---|
| Transporte | HTTPS obrigatório em produção |
| Auth | JWT RS256, access 15min, refresh 7 dias, `token_version` para revogação |
| Subdomínio | `{conta}.gocontrol.com.br` — schema resolvido pelo hostname |
| Isolamento | django-tenants schema switching + RLS no PostgreSQL |
| CSRF | Ativo (sessão) ou bypass (JWT puro) — decidir por surface |
| CORS | Restrito a origens explícitas |
| Autorização | RBAC contextual por (User, Conta, Módulo, Papel) |
| Soft delete | `deleted_at` em todos os modelos de domínio |
| Auditoria | `criado_por_user_id`, `atualizado_por_user_id`, `acted_as_role` |
| Rate limit | Login com lockout contra brute force |
| Secrets | Env vars; `.env` gitignored; secrets manager em produção |

### 13.1. Tabela de auditoria

```
audit_log
├── id (UUID)
├── empresa_id, conta_id
├── user_id (UUID lógico)
├── acted_as_role          ← qual papel estava ativo na operação
├── action (CREATE, UPDATE, DELETE, RESTORE)
├── modulo, entidade, entidade_id
├── before_data (JSON), after_data (JSON)
├── ip_address, user_agent
└── created_at
```

---

## 14. Core Models — Step 1 (Implementado)

### 14.1. Estado do Step 1

- 24 testes passando (10 mixin, 5 middleware, 9 auth) — 93% cobertura
- `TimestampMixin`, `SoftDeleteMixin`, `EmpresaScopedModel` implementados
- `EmpresaContextMiddleware` com `contextvars.ContextVar`
- JWT auth completo (login, refresh, logout, me, trocar empresa)
- Frontend: Axios + interceptors JWT + auto-refresh
- Docker Compose: PostgreSQL 16 + Redis 7

### 14.2. O que muda no Step 1b (refatoração para django-tenants)

| Componente | Mudança |
|---|---|
| `Empresa` → `Conta` | Herda `TenantMixin`; adiciona `schema_name` |
| `EmpresaContextMiddleware` | Adiciona `connection.set_schema(conta.schema_name)` |
| `accounts.User` | Adiciona `is_platform_staff`, `token_version` |
| `INSTALLED_APPS` | Divide em `SHARED_APPS` + `TENANT_APPS` |
| Novos models | `Membership`, `Modulo`, `ContaModulo`, `Papel`, `MembershipPapel` |
| Testes | ~30-40% de ajuste (middleware, User) |

---

## 15. Arquitetura de Apps Django

```
backend/apps/
├── core/               ← mixins, middleware, helpers        (SHARED)
├── identity/           ← User, Membership, Modulo, Papel    (SHARED)
├── conta/              ← Conta, Empresa, hierarquia         (SHARED)
├── platform/           ← PlatformFlag, MigrationRun, catálogos globais (SHARED)
│   └── catalogs/       ← Estado, Cidade, CFOP, CST          (SHARED)
│
└── módulos ERP (TENANT — schema tenant_{cnpj})
    ├── cadastros/
    │   ├── pessoas/    ← Pessoa, PessoaFisica, PessoaJuridica, Contato, Endereco
    │   └── produtos/   ← Produto, Categoria, Familia, Fabricante, UnidadeMedida
    ├── financeiro/
    ├── estoque/
    ├── fiscal/
    ├── producao/
    ├── cobrancas/
    ├── comercial/
    ├── crm/
    ├── expedicao/
    ├── communication/
    ├── mensageria/
    ├── documentos/
    ├── portal_cliente/
    └── sac/
```

---

## 16. Steps de Implementação — Plano Atualizado

### Ciclo 1 — Piloto (concluído)

| Step | Descrição | Status |
|---|---|---|
| **Step 1** | Bootstrap: core mixins, accounts, empresas, middleware, JWT, frontend auth | ✅ Concluído |
| **Step 1b** | Refatorar para django-tenants: TenantMixin, schema switching, SHARED/TENANT split, identity models | ✅ Concluído |
| **Step 2** | `platform/catalogs` + `identity` completo + `cadastros/pessoas` + `cadastros/produtos` | ✅ Concluído |
| **Step 3** | Proxy CEP + Proxy CNPJ com fallback, cache Redis | ✅ Concluído |
| **Step 4** | API REST DRF (services, selectors, serializers, views, permissions) para Pessoas + Produtos | ✅ Concluído |
| **Step 4.5** | @canvas-designer: decisões de UI/UX (tema, paleta, layout, sidebar modular) | ✅ Concluído |
| **Step 5** | Frontend React: Layout, LoginPage, módulos pessoas + produtos, deploy público via Cloudflare | ✅ Concluído (piloto funcional em goerp.myworkhome.com.br) |

### Ciclo 2 — Backoffice (próximo)

| Step | Descrição | Status |
|---|---|---|
| **Step 6** | Padronização de rotas (`/api/v1/erp/`, `/api/v1/account/`, `/api/v1/platform/`) + renaming de rotas ERP existentes | 🔜 Próximo |
| **Step 7** | `GET /api/v1/erp/modules/` — endpoint de módulos ativos (alimenta sidebar dinâmico) | 🔜 Aguarda 6 |
| **Step 8** | Sidebar dinâmica: hook `useModules()` + manifesto de módulos + `Layout.tsx` consumindo API | 🔜 Aguarda 7 |
| **Step 9** | **backoffice.account** — API + Frontend: Dashboard, Módulos (ativar/desativar), Empresas, Usuários | 🔜 Aguarda 7 |
| **Step 10** | **backoffice.platform** — API + Frontend: Contas (criar/gerenciar), Catálogo de Módulos, Maintenance | 🔜 Aguarda 9 |

### Ciclo 3 — Expansão ERP (aguarda Ciclo 2)

| Step | Descrição | Status |
|---|---|---|
| **Step 11** | Maintenance mode completo (Nível 1 + 2) + deploy pipeline Celery | 🔜 Aguarda 10 |
| **Step 12** | Módulo Financeiro (`erp.financeiro`) | 🔜 Aguarda 11 |
| **Step 13** | Módulo Comercial (`erp.comercial`) | 🔜 Aguarda 12 |
| **@oath-verifier** | Verificar ACs do PRD após cada ciclo | 🔜 Após Step 10, 11, 13 |

---

## 19. Padronização de Rotas de API (D20 — Aprovado 2026-05-07)

### 19.1. Princípio: prefixo por superfície

Toda rota segue o padrão `/api/v1/{superfície}/...`. Isso garante:
- Visibilidade imediata da superfície de origem de cada chamada
- Middleware de autorização por prefixo simples
- Bypass de maintenance apenas em `/api/v1/platform/*` sem regex complexa

### 19.2. Tabela de prefixos

| Prefixo | Superfície | Autorização |
|---|---|---|
| `/api/v1/auth/` | Auth compartilhada | Pública (login) ou JWT válido (me, switch-context) |
| `/api/v1/erp/` | ERP — módulos de domínio | JWT + `ContaModulo.ativo` + Papel no módulo |
| `/api/v1/account/` | backoffice.account | JWT + Membership ativo + papel `account_admin` |
| `/api/v1/platform/` | backoffice.platform | JWT + `User.is_platform_staff = True` |
| `/api/v1/integrations/` | Integrações externas (CEP, CNPJ) | JWT válido |
| `/api/v1/maintenance/` | Status público (polling frontend) | Sem autenticação |

### 19.3. Rota completa por endpoint (MVP)

#### Auth
```
POST   /api/v1/auth/token/               Login — retorna access + refresh
POST   /api/v1/auth/token/refresh/       Renovar access token
DELETE /api/v1/auth/token/logout/        Invalidar refresh token
GET    /api/v1/auth/me/                  Dados do usuário autenticado
POST   /api/v1/auth/switch-context/      Trocar Conta ou superfície
```

#### ERP
```
GET    /api/v1/erp/modules/              Módulos ativos da Conta (para sidebar)

GET    /api/v1/erp/cadastros/pessoas/          Lista de Pessoas
POST   /api/v1/erp/cadastros/pessoas/          Criar Pessoa
GET    /api/v1/erp/cadastros/pessoas/{id}/     Detalhe da Pessoa
PATCH  /api/v1/erp/cadastros/pessoas/{id}/     Atualizar Pessoa
DELETE /api/v1/erp/cadastros/pessoas/{id}/     Excluir Pessoa (soft delete)
GET    /api/v1/erp/cadastros/pessoas/tipos/    Seeds: TipoCliente
GET    /api/v1/erp/cadastros/pessoas/categorias/ Seeds: CategoriaCliente

GET    /api/v1/erp/cadastros/produtos/         Lista de Produtos
POST   /api/v1/erp/cadastros/produtos/         Criar Produto
GET    /api/v1/erp/cadastros/produtos/{id}/    Detalhe do Produto
PATCH  /api/v1/erp/cadastros/produtos/{id}/    Atualizar Produto
DELETE /api/v1/erp/cadastros/produtos/{id}/    Excluir Produto (soft delete)
```

#### Account (backoffice.account)
```
GET    /api/v1/account/overview/               Dashboard: stats da Conta
GET    /api/v1/account/modulos/                Módulos disponíveis + status ativo por Conta
PATCH  /api/v1/account/modulos/{code}/         Ativar/desativar módulo
GET    /api/v1/account/empresas/               Empresas do grupo (matriz + filiais)
POST   /api/v1/account/empresas/               Criar empresa (filial)
PATCH  /api/v1/account/empresas/{id}/          Atualizar empresa
GET    /api/v1/account/usuarios/               Memberships da Conta
POST   /api/v1/account/usuarios/invite/        Convidar usuário por email
PATCH  /api/v1/account/usuarios/{id}/          Atualizar papel / status
DELETE /api/v1/account/usuarios/{id}/          Revogar acesso (deactivate Membership)
```

#### Platform (backoffice.platform)
```
GET    /api/v1/platform/contas/                Lista de Contas
POST   /api/v1/platform/contas/                Criar nova Conta (cria schema tenant)
GET    /api/v1/platform/contas/{id}/           Detalhe da Conta
PATCH  /api/v1/platform/contas/{id}/           Atualizar Conta (ativar/desativar)

GET    /api/v1/platform/modulos/               Catálogo global de módulos
POST   /api/v1/platform/modulos/               Criar módulo no catálogo
PATCH  /api/v1/platform/modulos/{code}/        Atualizar módulo (nome, toggle em_manutencao)

GET    /api/v1/platform/usuarios/              Usuários com is_platform_staff
PATCH  /api/v1/platform/usuarios/{id}/         Promover/rebaixar platform staff

POST   /api/v1/platform/maintenance/global/start    Ativar maintenance global
POST   /api/v1/platform/maintenance/global/end      Desativar maintenance global
GET    /api/v1/platform/maintenance/global/status   Status atual
POST   /api/v1/platform/maintenance/modulo/{code}/start  Ativar maintenance do módulo
POST   /api/v1/platform/maintenance/modulo/{code}/end    Desativar maintenance do módulo
GET    /api/v1/platform/maintenance/modulo/{code}/progress  Progresso das migrations
GET    /api/v1/platform/migration/runs?deploy_id=&status=   Log de MigrationRuns
POST   /api/v1/platform/migration/runs/{id}/retry           Retentar migration falha
```

#### Integrações e Status
```
GET    /api/v1/integrations/cep/{cep}/         Proxy CEP (ViaCEP → fallbacks)
GET    /api/v1/integrations/cnpj/{cnpj}/       Proxy CNPJ (ReceitaWS → fallback)
GET    /api/v1/maintenance/status              Status público (sem auth) — frontend polling
```

### 19.4. Renaming necessário nas rotas existentes

| Rota atual | Nova rota |
|---|---|
| `POST /api/v1/auth/token/` | Mantém (sem mudança) |
| `GET  /api/v1/auth/me/` | Mantém (sem mudança) |
| `GET  /api/v1/cadastros/pessoas/` | `GET /api/v1/erp/cadastros/pessoas/` |
| `GET  /api/v1/cadastros/produtos/` | `GET /api/v1/erp/cadastros/produtos/` |
| `GET  /api/v1/integrations/cep/` | `GET /api/v1/integrations/cep/{cep}/` |
| `GET  /api/v1/integrations/cnpj/` | `GET /api/v1/integrations/cnpj/{cnpj}/` |

Mudança feita antes de ter clientes — sem necessidade de versioning ou backwards compat.

---

## 20. Backoffice MVP — Escopo e Funcionalidades (D21 + D22 — Aprovado 2026-05-07)

### 20.1. backoffice.account (D21)

**Acesso:** usuário com `Membership.is_account_owner = True` na Conta ativa
**Rota frontend:** `/backoffice/account/`
**Surface ID do Modulo:** `backoffice.account`

#### Páginas MVP

| Página | Rota | O que faz |
|---|---|---|
| **Dashboard** | `/backoffice/account/` | Cards: nome da Conta, total de empresas, total de usuários, módulos ativos / disponíveis |
| **Módulos** | `/backoffice/account/modulos/` | Lista todos os módulos com `surface=erp`; badge "Ativo" / "Inativo" / "Em manutenção"; toggle ativar/desativar por Conta |
| **Empresas** | `/backoffice/account/empresas/` | Lista Empresas do grupo (matriz + filiais); criar filial; editar dados básicos (nome, CNPJ, tipo) |
| **Usuários** | `/backoffice/account/usuarios/` | Lista Memberships; convidar por email; revogar acesso; badge de status (ativo/convidado/suspenso) |

#### O que fica fora do MVP (fase 2)
- Gestão de Papéis customizados por módulo
- Billing / plano contratado
- Switch de contexto entre múltiplas Contas
- Configurações de notificação

### 20.2. backoffice.platform (D22)

**Acesso:** `User.is_platform_staff = True`
**Rota frontend:** `/backoffice/platform/`
**Surface ID do Modulo:** `backoffice.platform`

#### Páginas MVP

| Página | Rota | O que faz |
|---|---|---|
| **Dashboard** | `/backoffice/platform/` | Cards: total de Contas ativas, módulos no catálogo, alertas de manutenção ativa |
| **Contas** | `/backoffice/platform/contas/` | Lista Contas com status; wizard de criação (nome + CNPJ + slug + email do owner); ativar/desativar |
| **Catálogo de Módulos** | `/backoffice/platform/modulos/` | Lista todos os `Modulo` do catálogo; criar/editar; toggle `em_manutencao` com mensagem |
| **Maintenance** | `/backoffice/platform/maintenance/` | Toggle maintenance global (com mensagem); lista módulos em manutenção; botão "Finalizar" por módulo |
| **Usuários Staff** | `/backoffice/platform/usuarios/` | Lista usuários com `is_platform_staff`; promover/rebaixar |

#### O que fica fora do MVP (fase 2)
- Acompanhamento de MigrationRun em tempo real (progress bars)
- Retry de migrations falhas pela UI (pode ser feito via shell)
- Billing / gestão de planos
- Logs de auditoria

### 20.3. Separação de responsabilidades no frontend

```
src/
  pages/
    erp/               ← módulos ERP (pessoas, produtos, financeiro, ...)
    backoffice/
      account/         ← Dashboard, Módulos, Empresas, Usuários
      platform/        ← Dashboard, Contas, CatálogoMódulos, Maintenance, Staff
    auth/              ← LoginPage
  shared/
    components/
      Layout.tsx       ← sidebar dinâmica (módulos ERP) + topbar
      BackofficeLayout.tsx  ← layout dos backoffices (sem sidebar modular)
```

---

## 17. Decisões Registradas — Índice Completo

| ID | Decisão | Aprovado em |
|---|---|---|
| D1 | Schema naming: `tenant_{cnpj_14_digitos}` (CNPJ sanitizado da matriz) | 2026-05-06 |
| D2 | PgBouncer em session mode (não transaction — quebraria SET search_path) | 2026-05-06 |
| D3 | Portal cliente externo: **no escopo** | 2026-05-06 |
| D4 | 3 módulos de comunicação: `erp.communication` (chat), `erp.mensageria` (workflow), `erp.documentos` | 2026-05-06 |
| D4a | Chat interno: por usuário ou por setor — **não** por pedido | 2026-05-06 |
| D5 | SAC: **no escopo**, sem prioridade (backlog) | 2026-05-06 |
| D6 | Deploy com gate manual: maintenance → Celery migration → progresso no backoffice → operador confirma | 2026-05-06 |
| D7 | Maintenance mode dois níveis: global (invalida tokens) + por módulo (não invalida tokens) | 2026-05-06 |
| D8 | Sistema de identidade unificado: 1 User global + Membership + Papel (modelo ZOHO) | 2026-05-06 |
| D9 | Subdomínio obrigatório por Conta para resolução de schema | 2026-05-06 |
| D10 | Sem FK de tabelas tenant → User: usar UUID lógico + nome denormalizado | 2026-05-06 |
| D11 | Multi-tenant Alternativa B: schema por Conta + `empresa_id` nos domínios | 2026-05-06 |
| D12 | Hierarquia: Conta → Empresa Matriz → Empresas Filiais (empresa_id distingue dentro do schema) | 2026-05-06 |
| D13 | Ordem de Produção desacoplada do Pedido — 2 gatilhos: PEDIDO e ESTOQUE | 2026-05-06 |
| D14 | Proxy pattern para CEP, CNPJ, Fiscal (SaaS), Bancário com fallback automático | 2026-05-06 |
| D15 | GO parte do zero — sem migração de dados do legado | 2026-05-06 |
| D16 | Stack: Django 5 + DRF + simplejwt + django-tenants + Celery + Redis + React 18 + PrimeReact + Tailwind | 2026-05-06 |
| D17 | TDD obrigatório: @grid-tester antes de @bolt-executor, cobertura ≥ 80% | 2026-05-06 |
| D18 | UI/UX adiado para antes do Step 5 (@canvas-designer) | 2026-05-06 |
| D19 | Validador de `ContaModulo.params_overrides`: **Pydantic v2** — BaseModel por módulo, validação tipada, erros claros | 2026-05-06 |
| D20 | **Padronização de rotas por superfície:** `/api/v1/erp/`, `/api/v1/account/`, `/api/v1/platform/`, `/api/v1/auth/`, `/api/v1/integrations/`, `/api/v1/maintenance/` | 2026-05-07 |
| D21 | **backoffice.account MVP:** Dashboard + Módulos (ativar/desativar) + Empresas + Usuários — fora: billing, papéis customizados, multi-conta | 2026-05-07 |
| D22 | **backoffice.platform MVP:** Dashboard + Contas (wizard criar) + Catálogo Módulos + Maintenance toggle + Usuários Staff — fora: MigrationRun UI, billing | 2026-05-07 |
| D23 | **Sidebar dinâmica:** `GET /api/v1/erp/modules/` alimenta hook `useModules()` no frontend; manifesto estático por módulo no frontend define seções e links | 2026-05-07 |

---

## 18. Referências

| Artefato | Caminho |
|---|---|
| Discovery (@echo-analyst) | `[C]discovery-migracao-minierp-adianti-python-react.md` |
| PRD (piloto Pessoas + Produtos) | `[C]prd-migracao-minierp-adianti-python-react.md` |
| Plano de implementação | `[C]plan-migracao-minierp-adianti-python-react.md` |
| ADR (a atualizar) | `[C]architecture-migracao-minierp-adianti-python-react.md` |
| Instruções para agentes | `/home/evonexus/evo-projects/go-control-erp/docs/agent-instructions.md` |
| Coding standards | `/home/evonexus/evo-projects/go-control-erp/docs/coding-standards.md` |
| Fonte legada (read-only) | `/home/evonexus/go_mini_erp_src` |
| Repositório GO | `/home/evonexus/evo-projects/go-control-erp/` |
