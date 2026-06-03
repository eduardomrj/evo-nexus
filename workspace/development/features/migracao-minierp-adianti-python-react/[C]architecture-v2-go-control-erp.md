---
author: claude
agent: apex-architect
type: architecture-decision
date: 2026-05-08
topic: stack-go-control-erp-v2-identidade-tenancy
status: accepted
supersedes: ./[C]architecture-migracao-minierp-adianti-python-react.md (parcial)
based_on: ./[C]decisions-redesign-identidade-tenancy.md
feature: migracao-minierp-adianti-python-react
---

# Architecture Decision v2 — Plataforma GO Control ERP

> **Este documento é o ADR canônico a partir de 2026-05-08.** Substitui partes do ADR v1 (`[C]architecture-migracao-minierp-adianti-python-react.md`) impactadas pelas decisões D-R01..D-R12 da sessão de discovery de identidade/tenancy. Decisões v1 não citadas aqui (D1 parcial, D2, D3, D4, D5, D6, D7, D8, D9, D12, D13, D14) **continuam válidas** e devem ser lidas no ADR v1.

---

## 1. Resumo das mudanças vs v1

A v1 ancorava a plataforma em **três pressupostos** que foram revistos:

1. **Subdomínio por Conta** como mecanismo de roteamento de tenant (D10/D11 v1)
2. **Conta agrega módulos** diretamente (`ContaModulo`)
3. **`Membership` + `MembershipPapel`** como única camada de vínculo

Os doze redesigns aprovados quebram cada um desses pressupostos:

| # | v1 (revogado / ajustado) | v2 (vigente) |
|---|---|---|
| Roteamento | Hostname `{slug}.gocontrol.com.br` resolve schema (D10 v1) | URLs fixas `erp.*` / `account.*` / `admin.*`; schema vem do claim JWT `ctx.conta_id` (D-R01, D-R02) |
| Conta | Container operacional + dono dos módulos (D10/D11 v1) | Entidade de **billing** + proprietário; agrupa Empresas (D-R03) |
| Empresa | Filial dependente da Conta-matriz (D10 v1, hierarquia rígida) | Unidade operacional **primária**; matriz é uma Empresa como qualquer outra; ramos diferentes coexistem (D-R04) |
| Módulos | `ContaModulo` (granularidade Conta) (D11 v1, D15 v1) | `EmpresaModulo` (granularidade **Empresa**); billing por Empresa (D-R05, D-R12) |
| Vínculo | `Membership(user, conta)` + `MembershipPapel` (D11 v1) | `Membership` reduzido a `is_account_owner`; vínculo operacional é `UserEmpresaVinculo(user, empresa, perfil)` + `VinculoModuloExtra` (D-R06) |
| Permissões | `Papel` em `public` com permissões hard-codadas no JWT (D11 v1) | `Perfil` (template por empresa) **vive no schema da Conta**; `PapelTemplate` opcional em `public` como catálogo (D-R07) |
| Domínio de dados | Tudo num único banco (public + N tenant_schemas) com FK lógica via UUID (G3 v1) | **Federado**: Backoffice DB (entidades de plataforma) ↔ ERP Schema por Conta com `EmpresaMirror` espelhado por signal síncrono (D-R08) |
| Login | Login + selector de empresa pós-autenticação (D11 v1, fluxo simples) | **Login em 3 etapas**: credencial → Conta → Empresa, com switch sem senha (D-R09) |
| Frontends | 1 SPA ERP + 2 backoffices em mesma origem (D21/D22 v1, design decisions) | **3 SPAs separadas** com login independente (D-R10) |
| Suporte | Impersonation read-only via TTL 2h (G7 v1) | Impersonation **read-write**, banner permanente, `ImpersonationLog` + `actor="staff:{nome}"` em `AuditLog` (D-R11) |
| Billing | Implícito (1 fatura/Conta) | `Fatura` por Conta **ou** por Empresa, itens = `EmpresaModulo` ativos (D-R12) |

**Decisões v1 explicitamente preservadas:**
- D1 (parcial): User custom UUID + email USERNAME_FIELD + argon2 — sim. `empresa_atual` FK e M2M `accounts_user_empresas` — **revogados** definitivamente.
- D2: `EmpresaContextMiddleware` + `EmpresaScopedModel` mixin com `contextvars.ContextVar` para isolamento intra-schema (entre Empresas dentro do mesmo tenant) — **continua obrigatório** dentro do ERP Schema.
- D3, D4, D5, D6, D7, D8, D9, D13, D14 — sem alteração.
- D12 (PgBouncer session mode) — **continua obrigatório** porque django-tenants segue ativo (apenas o trigger do `set_tenant` mudou de hostname para JWT).
- D15 (Pydantic v2 em `params_overrides`) — **continua válido**, mas o owner do JSON migra de `ContaModulo` → `EmpresaModulo`.

---

## 2. Decisões formalizadas (D-R01 a D-R12 em ADR-format)

### D-R01 — URLs fixas, sem subdomínio por Conta

**Decision.** Três portais com URLs fixas e independentes do tenant. `Conta.slug` mantido somente como identificador amigável para UX, **sem função de roteamento**.

| Portal | Homologação | Produção |
|---|---|---|
| ERP | `erp.myworkhome.com.br` | `erp.gocontrol.com.br` |
| Account Manager | `account.myworkhome.com.br` | `account.gocontrol.com.br` |
| Platform Admin | `admin.myworkhome.com.br` | `admin.gocontrol.com.br` |

**Drivers.**
- Subdomínio por Conta exige provisionamento Cloudflare/DNS a cada onboarding — atrito operacional inaceitável no piloto e perto-zero benefício antes de whitelabel real
- Vanity URL via `{slug}.gocontrol.com.br` pode ser reintroduzida no futuro como alias opcional, sem mudança arquitetural (apenas adicionar resolver alternativo)
- Reduz superfície DNS / TLS (3 certificados fixos vs N+1)

**Alternatives Considered.**

| Opção | Por quê não |
|---|---|
| Subdomínio por Conta (v1, D10/D11) | Atrito de onboarding (DNS), TLS wildcard cobre mas não simplifica revogação, força Cloudflare como dependência operacional |
| Path-prefix (`gocontrol.com.br/c/{slug}/...`) | Polui rotas de auth, complica CSP/cookies, mistura cookie escopo Conta entre tenants no mesmo origin |
| 1 origin com subpath por portal (`gocontrol.com.br/erp/`, `/account/`, `/admin/`) | Cookies compartilhados entre portais com escopos de risco distintos — Platform Admin não deve compartilhar cookie domain com ERP |

**Consequences.**
- ✅ Onboarding de Conta = `INSERT` no banco + `CREATE SCHEMA` (assíncrono via Celery); zero operação DNS
- ✅ TLS estático (3 certs Let's Encrypt) — automação trivial
- ❌ Modelo `Domain` do `django-tenants` torna-se **desnecessário** — pode ser removido do schema `public`
- ❌ `TenantMainMiddleware` (hostname routing) **substituído** pelo `JWTTenantMiddleware` (ver D-R02)
- ❌ Whitelabel por subdomínio fica como follow-up, não como produto v1

**Follow-ups.**
- F-R01.1 — Bolt: remover `Domain` model + migration de drop
- F-R01.2 — Bolt: configurar Traefik/Nginx com 3 hosts virtuais fixos por ambiente
- F-R01.3 — Vault: revisar CSP — cada portal tem sua própria policy, **sem `*.gocontrol.com.br`** wildcard

---

### D-R02 — Multi-tenancy: 1 schema por Conta, roteado pelo claim `ctx.conta_id` do JWT

**Decision.** Manter o isolamento físico por schema PostgreSQL (1 schema/Conta). Trocar o **mecanismo de seleção** de schema: ele deixa de vir do hostname e passa a vir do claim `ctx.conta_id` do JWT, ativado por um `JWTTenantMiddleware` que substitui `TenantMainMiddleware`.

```python
class JWTTenantMiddleware:
    def __call__(self, request):
        token = extract_bearer_token(request)
        if token:
            payload = decode_jwt_payload(token)  # já validado pelo middleware anterior
            conta_id = payload.get('ctx', {}).get('conta_id')
            if conta_id:
                conta = Conta.objects.using('default').get(id=conta_id)
                connection.set_tenant(conta)  # API do django-tenants
        return self.get_response(request)
```

**Ordem obrigatória de middlewares (substitui a chain v1):**
1. `JWTDecodeMiddleware` — valida assinatura, expiração, `token_version`. **Nenhuma query no DB.**
2. `JWTTenantMiddleware` — lê `ctx.conta_id`, ativa schema via `connection.set_tenant()`
3. `JWTAuthMiddleware` (DRF) — autentica `User` (já no schema `public`, sem ambiguidade)
4. `EmpresaContextMiddleware` (D2 v1) — lê `ctx.empresa_id`, popula `empresa_context.ContextVar`
5. `MaintenanceMiddleware` (D13 v1)

**Sem autenticação circular.** `User` vive em `public` (`SHARED_APPS`), e o decode do JWT roda **antes** de ativar o tenant. O `conta_id` vem do claim — não há "qual schema procurar o user?" porque o user é sempre do `public`.

**Drivers.**
- Eliminar dependência DNS (consequência de D-R01)
- Race condition de schema sob proxy (`Host:` header forjado) deixa de existir — assinatura JWT é o gatekeeper
- IDOR cross-tenant prevenido em **dupla camada**: middleware ativa schema certo + RLS em produção (G4 v1) como safety net + `EmpresaScopedModel` filtra por empresa dentro do schema

**Alternatives Considered.**

| Opção | Por quê não |
|---|---|
| Header `X-Conta-ID` | Falsificável trivialmente; precisaria de assinatura própria → reinventa JWT |
| Cookie `conta_id` separado | Stateful no cliente, sincronização com JWT vira fonte de bug |
| Manter hostname routing com URL fixa (resolve por path) | Mistura roteamento de DNS com aplicação; perde simplicidade de D-R01 |

**Consequences.**
- ✅ `pg_dump -n schema` continua funcionando (isolamento físico preservado)
- ✅ Switch de Conta = emitir novo JWT (D-R09); zero ginástica DNS
- ❌ Toda request faz 1 query `Conta.objects.using('default').get(id=...)` — mitigar com cache LRU de 60s por `conta_id` (`cachetools.TTLCache`)
- ❌ JWT sem `ctx.conta_id` em endpoints autenticados → 401 (não há fallback)

**Follow-ups.**
- F-R02.1 — Bolt: implementar `JWTTenantMiddleware` substituindo `TenantMainMiddleware` no `MIDDLEWARE` setting
- F-R02.2 — Bolt: cache `Conta` por `conta_id` (LRU, 60s, invalidado em `Conta.save`)
- F-R02.3 — Grid: teste de IDOR — usuário com JWT da Conta A trocando `ctx.conta_id` para Conta B → 403

---

### D-R03 — Conta = entidade de billing + proprietário (não mais container operacional)

**Decision.** `Conta` deixa de agregar módulos e operadores diretamente. Passa a ser:
1. Entidade de **billing** (razão social fiscal, CNPJ de cobrança, plano, forma de pagamento)
2. **Proprietário** da assinatura (FK para User)
3. Um **agrupador de Empresas** sob o mesmo guarda-chuva administrativo

```python
class Conta(TenantMixin):
    id                    = UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    proprietario          = ForeignKey('platform.User', on_delete=PROTECT, related_name='contas_owned')
    razao_social_billing  = CharField(max_length=200)
    cnpj_billing          = CharField(max_length=14, unique=True)
    plano                 = CharField(max_length=50, choices=[('starter','Starter'),('pro','Pro'),('enterprise','Enterprise')])
    forma_pagamento       = CharField(max_length=30)
    ativo                 = BooleanField(default=True)
    schema_name           = CharField(unique=True)  # ex: tenant_12345678000195
    slug                  = SlugField(unique=True)  # SOMENTE identificador amigável; sem função de DNS
    auto_create_schema    = True
    created_at            = DateTimeField(auto_now_add=True)
    # REMOVIDOS vs v1: subdomain, função de roteamento do slug, `nome` agregador
```

**Drivers.**
- Permite que Empresas com ramos diferentes (lanchonete + oficina) coexistam sob a mesma assinatura — caso citado pelo Eduardo (real, recorrente em PMEs do Nordeste)
- Separa "quem paga" (Conta) de "quem opera" (Empresa) — pré-requisito para D-R12 (billing por Empresa)

**Alternatives Considered.**

| Opção | Por quê não |
|---|---|
| Manter Conta como container operacional + adicionar Empresa como sub-unidade | Não resolve billing por CNPJ operacional — empresário com 2 CNPJs distintos cai em ambiguidade fiscal |
| Múltiplas Contas para o mesmo cliente (uma por CNPJ) | Força o cliente a logar em N contas e perde economia de assinatura plataforma |

**Consequences.**
- ✅ Modelo de negócio claro: 1 cliente = 1 Conta = N Empresas operacionais = N CNPJs fiscalmente independentes
- ❌ Códigos v1 que assumem `Conta.modulos` → reescrever para `empresa.modulos` ou `Conta.empresas.modulos`
- ❌ Migration de dados: contas existentes (zero no piloto) precisariam criar Empresa-matriz por padrão; **não-aplicável** por estarmos pré-produção

**Follow-ups.**
- F-R03.1 — Bolt: refatorar model `Conta` (remover campos de roteamento, adicionar billing)
- F-R03.2 — Compass: replanejar Step 9 do Ciclo 2 (backoffice account precisa expor edição de billing)

---

### D-R04 — Empresa como unidade operacional primária

**Decision.** `Empresa` é a unidade operacional real. A "matriz" passa a ser apenas uma Empresa com `tipo='matriz'` — não tem privilégio estrutural além do convencional. **Toda Conta deve ter pelo menos uma Empresa ao final do onboarding** (regra de negócio invariante).

```python
class Empresa(TimestampMixin):  # SHARED_APPS (public)
    id            = UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conta         = ForeignKey(Conta, on_delete=CASCADE, related_name='empresas')
    cnpj          = CharField(max_length=14)
    razao_social  = CharField(max_length=200)
    nome_fantasia = CharField(max_length=200, blank=True)
    tipo          = CharField(max_length=20, choices=[('matriz','Matriz'),('filial','Filial'),('independente','Independente')], default='independente')
    empresa_pai   = ForeignKey('self', null=True, blank=True, on_delete=SET_NULL, related_name='filiais')
    ativo         = BooleanField(default=True)

    class Meta:
        # CNPJ pode repetir em Contas diferentes (UUID separa). Único dentro da Conta.
        constraints = [
            models.UniqueConstraint(fields=['conta', 'cnpj'], name='uq_empresa_cnpj_por_conta'),
        ]
```

**Drivers.**
- Refletir realidade fiscal brasileira: cada CNPJ é uma pessoa jurídica autônoma; "matriz" é uma convenção contábil, não uma hierarquia de dados
- Permitir Empresas de ramos heterogêneos numa mesma Conta sem força-las a herdar configuração da matriz

**Alternatives Considered.**

| Opção | Por quê não |
|---|---|
| Hierarquia rígida matriz→filiais (v1) | Bloqueia o caso de empresário com 2 negócios distintos (lanchonete + oficina) |
| Empresa como modelo dentro do schema tenant (não em `public`) | Frustra criação progressiva no onboarding antes do schema existir; complica billing query consolidado |

**Consequences.**
- ✅ `Empresa` em `SHARED_APPS` é consultável sem ativar schema (útil para listagem no Account portal)
- ✅ Mesmo CNPJ em Contas diferentes é tratado como entidade independente — sem conflito
- ❌ Cria a necessidade de `EmpresaMirror` no schema da Conta (D-R08) para queries ERP rápidas com JOIN

**Follow-ups.**
- F-R04.1 — Bolt: enforce regra "Conta sem Empresa não acessa ERP" no `JWTTenantMiddleware` (404 se `vinculo.empresa` não está em `Empresa.objects.filter(conta=...)` ativa)
- F-R04.2 — Grid: teste — Conta criada sem Empresa não permite login no ERP até Empresa-matriz ser criada

---

### D-R05 — `EmpresaModulo` substitui `ContaModulo`

**Decision.** Granularidade de módulo é por **Empresa**, não por Conta. Cada Empresa contrata seus módulos; cada `EmpresaModulo` ativo gera uma linha de billing.

```python
class EmpresaModulo(TimestampMixin):  # SHARED_APPS
    id               = UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa          = ForeignKey(Empresa, on_delete=CASCADE, related_name='modulos')
    modulo           = ForeignKey(Modulo, on_delete=PROTECT)
    ativo            = BooleanField(default=True)
    em_manutencao    = BooleanField(default=False)
    params_overrides = JSONField(default=dict)  # validado por Pydantic v2 (D15 v1)
    schema_version   = CharField(max_length=20, blank=True)
    contratado_em    = DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('empresa', 'modulo')]
```

**Ativação de módulo (Celery task assíncrona):**
1. `run_migrations_for_module(conta, modulo)` — roda migrations no schema da Conta (idempotente, já garantido por D14 v1)
2. `seed_initial_data(empresa, modulo)` — popula dados-semente daquela Empresa (Perfis padrão, tipos, categorias específicas do módulo)

**Drivers.**
- Empresário com lanchonete + oficina contrata `erp.pdv` só na lanchonete e `erp.os` só na oficina — granularidade de Conta inviabilizaria isso
- Billing discriminado por CNPJ exige a relação `Modulo ↔ Empresa` direta (D-R12)

**Alternatives Considered.**

| Opção | Por quê não |
|---|---|
| Manter `ContaModulo` + flag `escopo: empresa[]` no `params_overrides` | Engessa billing; força queries esquisitas para "qual módulo da Empresa X?" |
| `ContaModulo` controla disponibilidade + `EmpresaModulo` controla ativação | Duas tabelas para o mesmo conceito; complica UI de account manager |

**Consequences.**
- ✅ Sidebar dinâmica (Step 8 já implementado) consulta `EmpresaModulo` filtrando por `empresa_id` do JWT — queries são puramente em `public`
- ❌ Step 7 (`GET /api/v1/erp/modules/`) precisa migrar de `ContaModulo.objects.filter(conta=...)` → `EmpresaModulo.objects.filter(empresa=...)`
- ❌ `Modulo.em_manutencao` (campo no `Modulo`) ainda permite manutenção global de um módulo (D13 v1, nível 2); `EmpresaModulo.em_manutencao` adiciona granularidade Empresa — **dois flags coexistem**, ambos checados (logical OR) no `MaintenanceMiddleware`

**Follow-ups.**
- F-R05.1 — Bolt: substituir `ContaModulo` → `EmpresaModulo` (rename + migration de dados — vazio no piloto)
- F-R05.2 — Bolt: ajustar `MaintenanceMiddleware` para checar `EmpresaModulo.em_manutencao` (granularidade Empresa) **OR** `Modulo.em_manutencao` (granularidade global)
- F-R05.3 — Bolt: ajustar registry de `module_params` (D15 v1) — owner do JSON migra de `ContaModulo` para `EmpresaModulo`

---

### D-R06 — `UserEmpresaVinculo` + `VinculoModuloExtra`

**Decision.** O vínculo **operacional** entre User e Empresa é representado por `UserEmpresaVinculo`. `Membership` permanece, mas reduzido à função de "este User é dono da Conta" (`is_account_owner`).

```python
class Membership(TimestampMixin):  # SHARED_APPS — REDUZIDO em escopo
    user             = ForeignKey('platform.User', on_delete=CASCADE)
    conta            = ForeignKey(Conta, on_delete=CASCADE)
    is_account_owner = BooleanField(default=False)
    status           = CharField(choices=[('active','Active'),('invited','Invited'),('suspended','Suspended')])
    class Meta:
        unique_together = [('user', 'conta')]

class UserEmpresaVinculo(TimestampMixin):  # SHARED_APPS — NOVO
    id            = UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user          = ForeignKey('platform.User', on_delete=CASCADE, related_name='vinculos')
    empresa       = ForeignKey(Empresa, on_delete=CASCADE, related_name='vinculos')
    perfil_id     = UUIDField(null=True, db_index=True)  # FK lógica para Perfil no schema da Conta (G3 v1)
    perfil_nome   = CharField(max_length=100, blank=True)  # denormalizado para listagem sem ativar tenant
    status        = CharField(choices=[('invited','Invited'),('active','Active'),('suspended','Suspended')], default='invited')
    convidado_por = ForeignKey('platform.User', null=True, on_delete=SET_NULL, related_name='convites_feitos')
    invited_at    = DateTimeField(auto_now_add=True)
    accepted_at   = DateTimeField(null=True, blank=True)
    class Meta:
        unique_together = [('user', 'empresa')]

class VinculoModuloExtra(TimestampMixin):  # SHARED_APPS — NOVO
    id        = UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vinculo   = ForeignKey(UserEmpresaVinculo, on_delete=CASCADE, related_name='modulos_extra')
    modulo    = ForeignKey(Modulo, on_delete=CASCADE)
    ativo     = BooleanField(default=True)
    class Meta:
        unique_together = [('vinculo', 'modulo')]
```

**Cross-Conta.** Um User pode ter `UserEmpresaVinculo` em Empresas de Contas diferentes. Convite é livre — não exige aprovação da Conta de origem do User.

**Perfil vs Papel (terminologia formal).**

| Conceito | Onde vive | Granularidade | Exemplo |
|---|---|---|---|
| `Papel` | `public` (existente do v1) | Permissão atômica em um Módulo | `erp.financeiro.editor` |
| `Perfil` | Schema da Conta (D-R07) | **Template** que agrega Papéis em uma Empresa | `CAIXA`, `VENDEDOR`, `GERENTE` |

`UserEmpresaVinculo.perfil_id` resolve para o Perfil dentro do schema da Conta no momento da emissão do JWT (D-R09).

**Drivers.**
- Separar "vínculo de billing" (Membership/Conta) de "vínculo operacional" (Vinculo/Empresa) — necessário porque a Conta agora é só faturamento (D-R03)
- Permitir que o mesmo User tenha papéis diferentes em Empresas distintas da mesma Conta sem replicar registros

**Alternatives Considered.**

| Opção | Por quê não |
|---|---|
| Estender `Membership` com `empresa_id` opcional | Sobrecarrega semântica — fica `Membership` ora "User-Conta", ora "User-Empresa"; migrations confusas |
| `UserEmpresaVinculo` no schema da Conta | Quebra a query "em quais Empresas de quais Contas o User está?" sem ativar N tenants; LF1/LF4 (D-R09) ficaria caro |

**Consequences.**
- ✅ Login (D-R09) consulta `public` apenas — `UserEmpresaVinculo` lista todas as opções sem trocar schema
- ✅ Convite cross-Conta é insert simples em `public.UserEmpresaVinculo`
- ❌ `perfil_id` é FK lógica (UUID) — guardrail G3 v1 mantém-se; resolução real do Perfil requer ativar schema da Conta no `select-empresa`
- ❌ `perfil_nome` denormalizado precisa ser sincronizado por signal quando Perfil é renomeado (signal síncrono no schema da Conta dispara update em `public`)

**Follow-ups.**
- F-R06.1 — Bolt: criar models `UserEmpresaVinculo` + `VinculoModuloExtra` em `apps.platform`
- F-R06.2 — Bolt: signal `post_save` em `Perfil` (TENANT_APPS) → atualiza `UserEmpresaVinculo.perfil_nome` em `public` para todos os vínculos com `perfil_id` correspondente
- F-R06.3 — Grid: teste cross-Conta — User A na Conta X convida User B (que já existe na Conta Y) sem fluxo extra

---

### D-R07 — `Perfil` no schema da Conta + `PapelTemplate` opcional em `public`

**Decision.** `Perfil` (template de permissões) é dado **operacional da Conta** — vive no schema da Conta como tabela TENANT_APP. O Account Manager (`is_account_owner=True`) cria/personaliza Perfis por Empresa. O Platform Admin pode publicar `PapelTemplate` (em `public`) como **catálogo opcional** que o Account Manager pode copiar para criar Perfis personalizados.

```python
# TENANT_APPS — schema da Conta
class Perfil(TimestampMixin, EmpresaScopedModel):  # herdamos D2 v1
    id               = UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nome             = CharField(max_length=100)
    is_template_base = BooleanField(default=False)  # marca quando copiado de PapelTemplate
    template_origem  = UUIDField(null=True, blank=True)  # FK lógica para public.PapelTemplate
    class Meta:
        unique_together = [('empresa', 'nome')]

class PerfilPapel(TimestampMixin):  # M2M com payload
    perfil = ForeignKey(Perfil, on_delete=CASCADE)
    papel  = UUIDField(db_index=True)  # FK lógica para public.Papel (G3 v1)

# SHARED_APPS — public
class PapelTemplate(TimestampMixin):  # NOVO — catálogo opcional
    id          = UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nome        = CharField(max_length=100)
    descricao   = TextField(blank=True)
    papeis      = ManyToManyField('platform.Papel', through='PapelTemplatePapel')
    publicado   = BooleanField(default=True)
```

**Emissão do JWT (`POST /auth/select-empresa`):**
1. Validar `UserEmpresaVinculo(user, empresa, status='active')` em `public`
2. Resolver `Conta` da `Empresa` → `connection.set_tenant(conta)`
3. Carregar `Perfil` por `vinculo.perfil_id` no schema ativo
4. Resolver `Papeis` via `PerfilPapel.papel` (FK lógica) → `Papel.permissions` em `public`
5. Embutir lista resolvida no claim `ctx.permissions` do JWT

**Drivers.**
- Perfis são parte do "ferramental operacional" da Conta, não da plataforma — devem ser backupados junto com os dados ERP via `pg_dump -n schema`
- Catálogo `PapelTemplate` em `public` permite que a EvoNexus publique perfis-padrão (ex: "CAIXA padrão LGPD") sem invadir o schema da Conta

**Alternatives Considered.**

| Opção | Por quê não |
|---|---|
| `Perfil` em `public` (v1, hardcoded em `Papel`) | Toda Conta tem o mesmo conjunto de perfis — não atende a "Perfil custom por empresa" |
| `Perfil` em `public` por Conta | Fragmenta dados de plataforma com dados operacionais; backup operacional fica incompleto |

**Consequences.**
- ✅ Backup `pg_dump -n schema` carrega Perfis junto — restore é completo
- ✅ Account Manager personaliza Perfis sem tocar em `public` (separation of concerns)
- ❌ Resolução de permissões no JWT requer cross-schema query (1 query em schema tenant + 1 em public para Papel) — cachear no Redis (TTL 60s) por `(conta_id, perfil_id)`
- ❌ Migration de novos Papeis precisa ser anunciada para Account Managers atualizarem Perfis (UI exibe "Novos papeis disponíveis: X")

**Follow-ups.**
- F-R07.1 — Bolt: criar `Perfil`, `PerfilPapel` em `apps.identidade_tenant` (TENANT_APPS)
- F-R07.2 — Bolt: criar `PapelTemplate`, `PapelTemplatePapel` em `apps.platform` (SHARED_APPS)
- F-R07.3 — Bolt: cache Redis de permissões resolvidas com TTL 60s + invalidação no `Perfil.save()`

---

### D-R08 — Arquitetura federada: Backoffice DB ↔ ERP Schema com `EmpresaMirror`

**Decision.** Dois domínios de dados **fisicamente separados** dentro do mesmo cluster PostgreSQL, sincronizados por UUID compartilhado e signal síncrono.

```
┌──────────────────────────────────────────────────┐
│  BACKOFFICE DB  (schema: public)                 │
│                                                  │
│   platform.User                                  │
│   platform.Conta              (TenantMixin)      │
│   platform.Empresa                               │
│   platform.Membership         (is_account_owner) │
│   platform.UserEmpresaVinculo                    │
│   platform.VinculoModuloExtra                    │
│   platform.Modulo                                │
│   platform.EmpresaModulo                         │
│   platform.Papel                                 │
│   platform.PapelTemplate                         │
│   platform.Fatura                                │
│   platform.ImpersonationLog                      │
│   platform.MigrationRun                          │
│   platform.PlatformFlag                          │
│                                                  │
│   Servido em:                                    │
│     account.gocontrol.com.br                     │
│     admin.gocontrol.com.br                       │
└────────────────┬─────────────────────────────────┘
                 │ UUID idêntico (Empresa.id)
                 │ Signal síncrono (post_save / post_delete)
                 │ Atomicidade: falha → aborta operação fonte
                 ▼
┌──────────────────────────────────────────────────┐
│  ERP SCHEMA  (1 por Conta — tenant_<cnpj>)       │
│                                                  │
│   erp_core.EmpresaMirror     (UUID = Empresa.id) │
│   identidade_tenant.Perfil                       │
│   identidade_tenant.PerfilPapel                  │
│                                                  │
│   cadastros.Pessoa, Produto, ...                 │
│   vendas.Pedido, NotaFiscal, ...                 │
│   estoque.Movimento, ...                         │
│   financeiro.Lancamento, Conta, ...              │
│   producao.OrdemProducao, ...                    │
│   ... (todos os módulos ERP)                     │
│                                                  │
│   Servido em:                                    │
│     erp.gocontrol.com.br                         │
└──────────────────────────────────────────────────┘
```

**`EmpresaMirror` (TENANT_APPS):**

```python
class EmpresaMirror(TimestampMixin):
    id           = UUIDField(primary_key=True)  # MESMO UUID do public.Empresa — não auto-gerado
    conta_id     = UUIDField(db_index=True)
    cnpj         = CharField(max_length=14)
    razao_social = CharField(max_length=200)
    nome_fantasia = CharField(max_length=200, blank=True)
    tipo         = CharField(max_length=20)
    ativo        = BooleanField(default=True)
```

**Sincronização (signal síncrono em `public.Empresa`):**

```python
@receiver(post_save, sender=Empresa)
def sync_empresa_mirror(sender, instance, created, **kwargs):
    conta = instance.conta
    with schema_context(conta.schema_name):
        EmpresaMirror.objects.update_or_create(
            id=instance.id,
            defaults={
                'conta_id': conta.id,
                'cnpj': instance.cnpj,
                'razao_social': instance.razao_social,
                'nome_fantasia': instance.nome_fantasia,
                'tipo': instance.tipo,
                'ativo': instance.ativo,
            },
        )
# transaction.atomic envolve a operação fonte → falha aborta tudo
```

**Provisionamento de schema novo:** ao criar Conta + primeira Empresa, após `auto_create_schema` rodar, popular `EmpresaMirror` com **todas** as Empresas pré-existentes da Conta (caso de re-sync).

**Drivers.**
- ERP precisa de `EmpresaMirror` local para JOIN nativo com `Pessoa`, `Pedido`, etc. — sem cross-schema FK (G3 v1)
- Account/Platform Admin precisam editar `Empresa` em `public` sem precisar ativar schema do ERP — UX e perf
- Atomicidade: se signal falha, operação original aborta (consistência forte) — rare-but-valid pattern para schema-per-tenant

**Alternatives Considered.**

| Opção | Por quê não |
|---|---|
| FK cross-schema de tabelas tenant para `public.Empresa` | Quebra G3 v1 — django-tenants não suporta FK cross-schema |
| Replicação eventual via outbox + Celery | Janela de inconsistência inaceitável (PDV mostraria Empresa errada por segundos) |
| `Empresa` apenas no schema da Conta (sem `public.Empresa`) | Quebra D-R03 (billing por CNPJ no `public`); listar Empresas no Account portal exigiria N tenants |

**Consequences.**
- ✅ Queries ERP com JOIN nativo em `EmpresaMirror`
- ✅ Backup `pg_dump -n schema` carrega `EmpresaMirror` consistente com momento do backup
- ❌ Sincronização síncrona adiciona latência ao `Empresa.save` (~5–20ms por schema afetado)
- ❌ Operações em batch (criar 100 Empresas) precisam usar `bulk_create` + signal manual em loop por schema — ferramenta de admin Bolt deve providenciar

**Follow-ups.**
- F-R08.1 — Bolt: implementar signal síncrono `sync_empresa_mirror` + handler de delete
- F-R08.2 — Bolt: comando `python manage.py rebuild_empresa_mirror --conta <id>` para re-sync manual
- F-R08.3 — Grid: teste — falha simulada no signal aborta `Empresa.save` original (atomicidade)
- F-R08.4 — Grid: teste — após `auto_create_schema`, `EmpresaMirror` está populado com todas Empresas da Conta

---

### D-R09 — Login em 3 etapas progressivas

**Decision.** Login com seleção progressiva de contexto:

```
┌─────────────────────────────────────────────────────────┐
│ POST /auth/login   (sempre em public)                   │
│   body: { email, senha }                                │
│   → valida credencial → User global                     │
│   → consulta Membership (public)                        │
│       ├ 1 Conta  → ativa automaticamente, segue p/ etapa 2│
│       └ N Contas → 200 OK { contas: [...] }             │
└─────────────────────────────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────┐
│ POST /auth/select-conta   { conta_id }                  │
│   → valida Membership(user, conta) ativo                │
│   → consulta UserEmpresaVinculo(user, empresa.conta=X)  │
│       ├ 1 Empresa  → ativa automaticamente, segue       │
│       └ N Empresas → 200 OK { empresas: [...] }         │
└─────────────────────────────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────┐
│ POST /auth/select-empresa   { empresa_id }              │
│   → valida UserEmpresaVinculo(user, empresa) ativo      │
│   → ativa schema da Conta (set_tenant via conta_id)     │
│   → resolve Perfil (TENANT) → Papeis (public) →         │
│     permissions[]                                       │
│   → emite JWT:                                          │
│     {                                                   │
│       "sub": user_id,                                   │
│       "ctx": {                                          │
│         "type": "account",                              │
│         "conta_id": "...",                              │
│         "empresa_id": "...",                            │
│         "perfil": "VENDEDOR",                           │
│         "permissions": ["erp.pessoas.view", ...]        │
│       },                                                │
│       "is_account_owner": bool,                         │
│       "is_platform_staff": bool,                        │
│       "token_version": 7,                               │
│       "iat": ..., "exp": ...                            │
│     }                                                   │
└─────────────────────────────────────────────────────────┘
```

**Switches (sem senha).**
- `POST /auth/switch-empresa { empresa_id }` — dentro da mesma Conta. Re-resolve `Perfil` → emite novo par de tokens com novo `ctx.empresa_id` + `ctx.permissions`.
- `POST /auth/switch-conta { conta_id }` — cross-Conta. Volta para a etapa de seletor de Empresa (não emite JWT direto — chama `select-empresa` em sequência).

**Token refresh.** `POST /auth/refresh` re-emite com mesmo `ctx.conta_id` + `ctx.empresa_id` (LF4 — voltar para o último contexto usado).

**Drivers.**
- Modelo ZOHO de seleção progressiva — familiar a usuários de SaaS B2B
- Single-context-at-a-time evita ambiguidade ("estou operando qual Empresa?") — claim `ctx.empresa_id` é fonte única de verdade
- Switch sem senha reduz fricção operacional; segurança mantida pelo `token_version` + TTL curto

**Alternatives Considered.**

| Opção | Por quê não |
|---|---|
| Login único com seletor frontend | Fronteira de auth fica confusa — JWT teria N empresas, frontend escolhe; quebra "fonte única de verdade" |
| JWT poliglota (`ctx.empresas: [{id, perfil, permissions}, ...]`) | Token gigante; switch tem que rebuildar permissions client-side; viola princípio de "permissions decididas pelo backend" |

**Consequences.**
- ✅ Cada request tem contexto inequívoco (uma Conta + uma Empresa)
- ✅ Auditoria tem actor + contexto trivial de extrair do claim
- ❌ Switch envolve roundtrip extra ao backend — aceitável (operação rara)
- ❌ Revogação de permissão exige re-emissão de JWT (já endereçado por `token_version` D11 v1)

**Follow-ups.**
- F-R09.1 — Bolt: implementar 3 endpoints + 2 switches em `apps.platform.views.auth`
- F-R09.2 — Bolt: claim `ctx.empresa_id` consumido pelo `EmpresaContextMiddleware` (D2 v1) substituindo a leitura atual de `request.user.empresa_atual_id` (que não existe mais)
- F-R09.3 — Grid: testes de fluxo completo + edge cases (User com 0 vínculos ativos → 403 com mensagem clara)

---

### D-R10 — 3 SPAs separadas (sem SSO cross-portal)

**Decision.** Três aplicações React independentes, cada uma com seu próprio bundle, login e cookie/storage isolado:

| Portal | Origin | Auth scope (regra de acesso) |
|---|---|---|
| ERP | `erp.gocontrol.com.br` | User com `UserEmpresaVinculo(status='active')` em pelo menos uma Empresa |
| Account | `account.gocontrol.com.br` | User com `Membership(is_account_owner=True, status='active')` |
| Platform Admin | `admin.gocontrol.com.br` | User com `is_platform_staff=True` |

**Sem SSO cross-portal.** Cada portal autentica independentemente contra o **mesmo** backend `api.gocontrol.com.br`. JWT do ERP não vale no Admin (rejeitado por checagem de `ctx.type` ou `is_platform_staff` no middleware do endpoint).

**Sinalização cross-portal:**
- ERP, ao detectar `is_account_owner=true` no JWT, exibe link no menu de perfil: "Ir para Minha Conta" → `https://account.gocontrol.com.br` (login independente)
- Mesmo padrão para Platform staff acessando Admin a partir do ERP

**Compartilhamento de código.** Componentes comuns (`StatusBadge`, `ConfirmDialog`, `EmpresaSelector`, hooks de auth) ficam em diretório `shared/`. **Decisão de monorepo vs polyrepo é diferida** para quando os 3 builds existirem; v1 usa cópia explícita por bundle.

**Drivers.**
- Isolamento de superfície de ataque (cookie/origin separados — XSS no ERP não escala para Admin)
- Bundle size — ERP não carrega telas de Platform Admin nem vice-versa
- Independência de deploy — Platform Admin em manutenção não derruba ERP

**Alternatives Considered.**

| Opção | Por quê não |
|---|---|
| 1 SPA com routing condicional (v1 implícito) | Bundle gigante (~3 MB); permission leak via inspeção de bundle; deploy acoplado |
| SSO cross-portal com JWT compartilhado | Cookie domain pai (`.gocontrol.com.br`) expõe Admin a riscos do ERP; aumenta superfície de ataque desproporcionalmente |

**Consequences.**
- ✅ Build/deploy independentes — Admin pode fazer deploy de hotfix sem rebuild do ERP
- ✅ CSP por portal pode ser restritiva (cada origin tem seu próprio domínio)
- ❌ Login duplicado para Account Manager que opera o ERP e gerencia a Conta — aceitável (uso diferente, sessão diferente)
- ❌ Componentes duplicados até decisão de monorepo

**Follow-ups.**
- F-R10.1 — Bolt: criar 3 projetos Vite separados — `frontend/erp/`, `frontend/account/`, `frontend/admin/`
- F-R10.2 — Bolt: extrair `shared/` como pacote local (não publicado) — symlink ou file dependency em `package.json`
- F-R10.3 — Sysops: configurar Traefik com 3 routers, cada um para uma origin
- F-R10.4 — Vault: 3 CSPs distintas; nenhuma com `*.gocontrol.com.br`

---

### D-R11 — Platform Staff: impersonation read-write com banner + audit log completo

**Decision.** Staff pode acessar o ERP de qualquer Conta para diagnóstico **e correção**. Toda ação fica registrada com identidade real do staff, banner é permanente na UI, JWT especial expira em 2h **não-renovável**.

**Fluxo de impersonation:**

```
1. Staff em admin.gocontrol.com.br seleciona Conta Alfa
2. POST /admin/impersonate { conta_id }
   - Valida is_platform_staff=True + razão (campo obrigatório)
   - Emite JWT especial:
     {
       "sub": staff_user_id,
       "ctx": {
         "type": "account",
         "conta_id": "alfa",
         "empresa_id": null,             # escolhe na próxima tela
         "impersonating": true,
         "impersonated_by": staff_user_id,
         "impersonation_reason": "...",  # texto livre + ticket id
         "permissions": ["*"]            # full read-write no escopo da Conta
       },
       "is_account_owner": false,
       "is_platform_staff": true,
       "exp": iat + 7200                  # 2h fixo, sem refresh
     }
3. Frontend ERP redireciona staff para erp.gocontrol.com.br com token especial
4. Banner permanente: "MODO SUPORTE — ações registradas como [Eduardo Martins]"
5. Toda mutation grava em ImpersonationLog:
     { staff_user_id, conta_id, empresa_id, action, resource_type,
       resource_id, before_state, after_state, timestamp, request_id }
6. Toda mutation grava também em AuditLog do schema com actor="staff:{nome}"
7. JWT expira em 2h — staff precisa re-iniciar fluxo se precisar de mais tempo
```

**`ImpersonationLog`** vive em `public` (`SHARED_APPS`). `AuditLog` continua no schema da Conta (D2/D11 v1).

**Drivers.**
- Suporte real exige read-write — read-only frustra correção (caso real: cliente liga, dado errado, suporte tem que pedir cliente para corrigir manualmente)
- Audit duplo (`ImpersonationLog` em `public` + `AuditLog` em tenant) protege contra tentativas de adulterar histórico via acesso direto ao schema da Conta
- TTL fixo 2h não-renovável força disciplina; se 2h não basta, há problema maior

**Alternatives Considered.**

| Opção | Por quê não |
|---|---|
| Impersonation read-only (G7 v1, original) | Frustra suporte — cliente continua sem correção; obriga fluxo de "passe o passo a passo para o cliente" |
| Impersonation com aprovação prévia do Account Owner | Inviável durante incidentes em horário comercial; suporte trava |
| JWT renovável em sessão de impersonation | Permite suporte permanente disfarçado de "auditoria" — abre brecha de longo-running access |

**Consequences.**
- ✅ Suporte resolve problemas em produção sem ginástica
- ✅ Cliente pode auditar `ImpersonationLog` no Account portal (transparência)
- ❌ Risco operacional: staff malicioso pode causar dano — mitigado pelo log duplo + revisão semanal de `ImpersonationLog`
- ❌ G7 v1 (impersonation read-only) é **revogado** — substituído por este fluxo

**Follow-ups.**
- F-R11.1 — Bolt: criar `ImpersonationLog` em `apps.platform`
- F-R11.2 — Bolt: middleware de mutation grava em ambos os logs
- F-R11.3 — Canvas: banner permanente no ERP quando `ctx.impersonating=true`
- F-R11.4 — Lex: review LGPD — base legal "execução de contrato + interesse legítimo (suporte)"; exposição em política de privacidade
- F-R11.5 — Atlas: rotina semanal de revisão de `ImpersonationLog` (pulse-monthly tipo)

---

### D-R12 — Billing por Empresa (com fatura consolidada opcional)

**Decision.** Billing pode ser gerado **por Empresa** (cada CNPJ tem sua fatura) ou **consolidado por Conta** (uma fatura englobando todas as Empresas).

```python
class Fatura(TimestampMixin):  # SHARED_APPS
    id        = UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conta     = ForeignKey(Conta, on_delete=PROTECT, related_name='faturas')  # quem paga
    empresa   = ForeignKey(Empresa, null=True, blank=True, on_delete=SET_NULL, related_name='faturas')
                # null = fatura consolidada da Conta
    periodo   = DateField()  # competência (1º do mês)
    status    = CharField(choices=[('aberta','Aberta'),('paga','Paga'),('vencida','Vencida'),('cancelada','Cancelada')])
    itens     = JSONField()  # [{empresa_modulo_id, modulo_code, valor, descricao, qtd_dias}]
    total     = DecimalField(max_digits=14, decimal_places=2)
    emitida_em = DateTimeField(null=True, blank=True)
    paga_em   = DateTimeField(null=True, blank=True)
    asaas_payment_id = CharField(max_length=80, blank=True)
    class Meta:
        # Em um período, ou tem 1 fatura consolidada (empresa=null) ou N faturas (empresa preenchido)
        # Não pode ter fatura empresa=X e fatura consolidada no mesmo período pra mesma Conta
        constraints = [
            models.UniqueConstraint(fields=['conta', 'empresa', 'periodo'], name='uq_fatura_conta_empresa_periodo'),
        ]
```

**Modos:** `Conta.billing_mode = 'consolidado' | 'por_empresa'` (default `consolidado` no piloto). Geração mensal escolhe modo a partir do flag.

**Drivers.**
- Cliente com 2 CNPJs operacionais distintos pode precisar de 2 NF-e separadas para escrituração contábil — sem isso, perde fluxo fiscal
- Manter modo consolidado como default reduz complexidade para o caso simples (1 Empresa)

**Alternatives Considered.**

| Opção | Por quê não |
|---|---|
| Sempre consolidado | Cliente com múltiplas Empresas em ramos distintos não consegue separar custo |
| Sempre por Empresa | Para cliente single-CNPJ, gera fatura desnecessariamente fragmentada |
| Decisão por fatura (não por Conta) | Imprevisível para cliente; dificulta automação de cobrança |

**Consequences.**
- ✅ Atende fiscalmente clientes multi-CNPJ
- ✅ `Fatura.empresa = null` continua suportando o modo simples
- ❌ Job mensal de geração de fatura precisa ler `Conta.billing_mode` e ramificar
- ❌ Integração Asaas (cobrança) precisa criar pagamento por fatura — hoje 1, no modo `por_empresa` pode ser N

**Follow-ups.**
- F-R12.1 — Bolt: criar `Fatura` em `apps.platform`
- F-R12.2 — Compass: planejar feature de billing após piloto (não bloqueia Ciclo 2)
- F-R12.3 — Flux: validar regras fiscais com contador (NF-e por Empresa contratante)

---

## 3. Mapa de impacto: tabelas que mudam vs continuam iguais

### Tabelas que MUDAM (alteração ou substituição)

| Tabela (v1) | Mudança | Observação |
|---|---|---|
| `platform.User` | Remove campos `empresa_atual` (FK), tabela auxiliar `accounts_user_empresas` (M2M) | D1 v1 parcial; D-R02/D-R09 substituem |
| `platform.Conta` | **Reformulado**: campos de billing entram (`razao_social_billing`, `cnpj_billing`, `plano`, `forma_pagamento`, `proprietario`); `slug` perde função de DNS; `Domain` model removido | D-R01, D-R03 |
| `platform.Membership` | **Reduzido**: agora só carrega `is_account_owner`. Vínculo operacional saiu para `UserEmpresaVinculo` | D-R06 |
| `platform.Modulo` | Sem mudança estrutural; semântica de `em_manutencao` continua (D13 v1) | — |
| `platform.ContaModulo` | **REMOVIDO** — substituído por `EmpresaModulo` | D-R05 |
| `platform.Papel` | Sem mudança estrutural | D-R07 mantém em `public` |
| `platform.MembershipPapel` | **REMOVIDO** — agora `Perfil ↔ Papel` via `PerfilPapel` (TENANT) | D-R06, D-R07 |
| `platform.Domain` (django-tenants) | **REMOVIDO** | D-R01 |

### Tabelas NOVAS

| Tabela | Schema | Decisão |
|---|---|---|
| `platform.Empresa` | `public` | D-R04 |
| `platform.EmpresaModulo` | `public` | D-R05 |
| `platform.UserEmpresaVinculo` | `public` | D-R06 |
| `platform.VinculoModuloExtra` | `public` | D-R06 |
| `platform.PapelTemplate` | `public` | D-R07 |
| `platform.PapelTemplatePapel` | `public` | D-R07 |
| `platform.Fatura` | `public` | D-R12 |
| `platform.ImpersonationLog` | `public` | D-R11 |
| `erp_core.EmpresaMirror` | tenant_<cnpj> | D-R08 |
| `identidade_tenant.Perfil` | tenant_<cnpj> | D-R07 |
| `identidade_tenant.PerfilPapel` | tenant_<cnpj> | D-R07 |

### Tabelas IGUAIS (sem alteração)

| Tabela | Motivo de continuidade |
|---|---|
| `platform.PlatformFlag` | D13 v1 (maintenance global) — sem mudança |
| `platform.MigrationRun` | D14 v1 (deploy policy) — sem mudança |
| Todas as tabelas de domínio ERP (`cadastros.Pessoa`, `vendas.Pedido`, `estoque.*`, `producao.*`, `financeiro.*`) | D2 v1 (`EmpresaScopedModel`) e demais decisões de domínio — sem mudança; FK lógica para `Empresa` continua sendo o `empresa_id` resolvido via `EmpresaContextMiddleware` |
| `core.AuditLog` (em cada tenant) | D11 v1 — adiciona suporte a `actor="staff:{nome}"` (D-R11) **sem mudança de schema** |

---

## 4. Diagrama ASCII da nova arquitetura de dados

```
                        ┌────────────────────┐
                        │  Cluster Postgres  │
                        └──────────┬─────────┘
                                   │
     ┌─────────────────────────────┴──────────────────────────────┐
     │                                                            │
     ▼                                                            ▼
┌──────────────────────────────┐                   ┌──────────────────────────────────┐
│  schema: public              │                   │  schema: tenant_12345678000195    │
│  (BACKOFFICE DB)             │                   │  (ERP SCHEMA da Conta Alfa)       │
│                              │                   │                                  │
│  ┌────────┐                  │                   │  ┌──────────────────────┐        │
│  │  User  │                  │   1               │  │ erp_core.EmpresaMirror│       │
│  └───┬────┘                  │   ▲               │  │ id (=public.Empresa) │        │
│      │1                      │   │ post_save     │  │ conta_id, cnpj, ...   │       │
│      │                       │   │ (síncrono)    │  └──────────┬───────────┘       │
│      │M                      │   │               │             │M                  │
│  ┌───▼───────┐  M ┌────────┐ │   │               │             │                   │
│  │Membership │◀──▶│ Conta  │─┼───┘               │             │                   │
│  │is_account │ 1  │TenantMx│ │                   │             ▼                   │
│  │_owner     │    │schema_ │ │                   │  ┌──────────────────────┐       │
│  └───────────┘    │name    │ │                   │  │ cadastros.Pessoa     │       │
│                   └───┬────┘ │                   │  │   FK lógica:         │       │
│                       │1     │                   │  │     empresa_id       │       │
│                       │      │                   │  │   (filtrado por D2   │       │
│                       │M     │                   │  │    EmpresaContext)   │       │
│                  ┌────▼─────┐│                   │  └──────────────────────┘       │
│                  │ Empresa  ││                   │                                  │
│                  │ id, cnpj ││                   │  ┌──────────────────────┐        │
│                  │ tipo     ││                   │  │ identidade_tenant.   │        │
│                  └──┬───────┘│                   │  │   Perfil             │        │
│                     │1       │                   │  │   id, nome, empresa  │        │
│                     │        │                   │  │   FK→ EmpresaMirror  │        │
│                     │M       │                   │  └──────────┬───────────┘        │
│              ┌──────▼───────┐│                   │             │M                   │
│   ┌────┐ M   │UserEmpresa   ││                   │             │                    │
│   │User│◀───▶│  Vinculo     ││                   │             ▼                    │
│   └────┘     │ user_id      ││                   │  ┌──────────────────────┐        │
│              │ empresa_id   ││                   │  │ identidade_tenant.   │        │
│              │ perfil_id ●──┼┼──────────────────►│  │   PerfilPapel        │        │
│              │ status       ││  FK lógica (UUID) │  │   perfil_id          │        │
│              └──────────────┘│  guardrail G3 v1  │  │   papel_id ●─────────┼────┐   │
│                              │                   │  └──────────────────────┘   │   │
│              ┌────────────┐  │                   │                              │   │
│              │ Modulo     │  │                   │                              │   │
│              └─────┬──────┘  │                   │                              │   │
│                    │M        │                   │                              │   │
│              ┌─────▼──────┐  │                   │                              │   │
│              │EmpresaMod  │  │                   │                              │   │
│              │ empresa_id │  │                   │                              │   │
│              │ modulo_id  │  │                   │                              │   │
│              │ params_jsn │  │                   │                              │   │
│              └────────────┘  │                   │                              │   │
│                              │                   │                              │   │
│  ┌──────────┐                │                   │                              │   │
│  │ Papel    │◀───────────────┼──────────────────────────────────────────────────┘   │
│  │ permissions JSON          │                   │                                  │
│  └──────────┘                │                   │                                  │
│                              │                   │                                  │
│  ┌──────────────────┐        │                   │                                  │
│  │ PapelTemplate    │ (catálogo opcional)        │                                  │
│  └──────────────────┘        │                   │                                  │
│                              │                   │                                  │
│  ┌──────────────────┐        │                   │                                  │
│  │ Fatura           │ (D-R12)│                   │                                  │
│  │ ImpersonationLog │ (D-R11)│                   │                                  │
│  │ MigrationRun     │ (D14)  │                   │                                  │
│  │ PlatformFlag     │ (D13)  │                   │                                  │
│  └──────────────────┘        │                   │                                  │
└──────────────────────────────┘                   └──────────────────────────────────┘

Três origins distintas (D-R10):
  account.gocontrol.com.br ─────► public (Backoffice DB)
  admin.gocontrol.com.br   ─────► public (Backoffice DB)
  erp.gocontrol.com.br     ─────► public (auth) → tenant_<cnpj> (operação ERP)

Roteamento de schema (D-R02):
  JWT.ctx.conta_id → connection.set_tenant(Conta.objects.get(id=...))
  (sem hostname; Domain model removido)
```

---

## 5. Middleware stack atualizado (substitui v1)

**Ordem obrigatória no `MIDDLEWARE` do Django:**

```python
MIDDLEWARE = [
    # 1. Plataforma — sempre primeiro
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',

    # 2. Decode JWT — sem DB hit (apenas valida assinatura/expiração/token_version cache)
    'apps.platform.middleware.JWTDecodeMiddleware',  # NOVO (D-R02)

    # 3. Roteamento de tenant via JWT — substitui TenantMainMiddleware
    'apps.platform.middleware.JWTTenantMiddleware',  # NOVO (D-R02)
    # (django_tenants.middleware.main.TenantMainMiddleware  ← REMOVIDO)

    # 4. Autenticação DRF (já no schema correto)
    'django.contrib.auth.middleware.AuthenticationMiddleware',

    # 5. Empresa context — para EmpresaScopedModel (D2 v1, agora lê ctx.empresa_id do JWT)
    'apps.core.middleware.EmpresaContextMiddleware',  # AJUSTADO (D2 v1 + D-R09)

    # 6. Maintenance mode — global (D13 v1) + por módulo + por EmpresaModulo (D-R05)
    'apps.platform.middleware.MaintenanceMiddleware',

    # 7. Impersonation banner trigger — log mutation se ctx.impersonating
    'apps.platform.middleware.ImpersonationLogMiddleware',  # NOVO (D-R11)

    # 8. Standard
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
```

**Diferenças vs v1:**

| Posição | v1 | v2 | Razão |
|---|---|---|---|
| Antes de auth | `TenantMainMiddleware` (hostname) | `JWTDecodeMiddleware` + `JWTTenantMiddleware` | D-R01, D-R02 |
| `EmpresaContextMiddleware` | Lia `request.user.empresa_atual_id` (DB) | Lê `request.auth.payload['ctx']['empresa_id']` (JWT) | D-R09 — campo `empresa_atual` removido |
| `ImpersonationLogMiddleware` | Não existia | Novo — captura mutations + grava em `ImpersonationLog` quando `ctx.impersonating=true` | D-R11 |

---

## 6. Os 9 Guardrails revisados

A v1 listou 9 guardrails (G1-G9) na D11. Os redesigns alteram metade. Lista canônica vigente:

| # | v2 — Guardrail vigente | Status vs v1 |
|---|---|---|
| **G1** | URLs fixas: `erp.*`, `account.*`, `admin.*` por ambiente. **Rejeitar** request com Host fora dessa lista (404). Subdomínio por Conta é proibido até feature de whitelabel ser priorizada. | **REESCRITO** (era "subdomínio obrigatório") — D-R01 |
| **G2** | `SHARED_APPS` contém apenas `apps.platform` (User, Conta, Empresa, Membership, UserEmpresaVinculo, EmpresaModulo, etc.) + django-tenants. Todo módulo ERP em `TENANT_APPS`. `apps.identidade_tenant` (Perfil, PerfilPapel) também em `TENANT_APPS`. | **AJUSTADO** — adiciona `identidade_tenant` em TENANT_APPS — D-R07 |
| **G3** | Sem FK cross-schema. Tabelas tenant referenciam `User`/`Empresa` por `UUIDField + db_index=True` + colunas denormalizadas (`criado_por_nome`, etc.) sincronizadas por signal. `EmpresaMirror` é a denormalização canônica de `Empresa` no schema da Conta. | **REFORÇADO** — D-R08 introduz `EmpresaMirror` como caso de uso explícito |
| **G4** | RLS PostgreSQL como safety net em produção em **todas** as tabelas tenant E em `public.UserEmpresaVinculo` / `public.EmpresaModulo` (limita por `conta_id` derivado de claim). | **EXPANDIDO** — RLS agora cobre algumas tabelas de `public` que dão escopo cross-Conta — D-R02, D-R06 |
| **G5** | Token versioning: middleware valida `payload['token_version'] == user.token_version` (cache Redis 60s, invalidado em increment). Mismatch → 401. Aplica também a impersonation tokens. | **MANTIDO** — sem mudança |
| **G6** | Claim `acted_as_role`: revogado/redundante. **Substituído** por `ctx.impersonating=true` + `ctx.impersonated_by` (D-R11). Auditoria precisa logar nome real do staff via `ImpersonationLog`. | **REESCRITO** — D-R11 |
| **G7** | `is_platform_staff=True` **não dá acesso direto** a schemas tenant. Acesso requer fluxo de impersonation (`POST /admin/impersonate`) com **razão obrigatória**, JWT TTL 2h **não-renovável**, `ImpersonationLog` em `public` + `AuditLog` em tenant. Modo é **read-write** com banner permanente na UI. | **REESCRITO** — read-only → read-write controlado — D-R11 |
| **G8** | Custom manager: `User.objects` retorna apenas `is_active=True`. `User.all_objects` faz bypass. **Adiciona:** `Empresa.objects` filtra `ativo=True`; `UserEmpresaVinculo.objects` filtra `status='active'`. | **EXPANDIDO** para Empresa/Vinculo — D-R04, D-R06 |
| **G9** | Isolation test suite obrigatório: 2 Contas em schemas reais, User da Conta A nunca vê dados da Conta B. **Adiciona:** teste IDOR — User com JWT da Conta A trocando `ctx.conta_id` no payload → 401/403 (assinatura inválida ou conta_id sem Membership). **Adiciona:** teste cross-Empresa intra-Conta — User com vínculo só na Empresa X não vê dados da Empresa Y na mesma Conta. | **EXPANDIDO** — D-R02, D-R04, D-R06 |

---

## 7. Impacto no Ciclo 2 (steps já executados)

| Step | Status | Ação |
|---|---|---|
| Step 6 — Padronização de rotas (`/api/v1/erp/...`) | ✅ Concluído | Mantido |
| Step 7 — `GET /api/v1/erp/modules/` | ✅ Concluído | **Refatorar** — origem de dados muda de `ContaModulo` (filtro por `conta`) para `EmpresaModulo` (filtro por `empresa` extraído de `ctx.empresa_id`). Resposta: shape igual. |
| Step 8 — Sidebar dinâmica | ✅ Concluído | **Adaptar** — hook `useModules()` passa a consumir endpoint refatorado; sem mudança visual |
| Step 9 — `backoffice.account` | ✅ Concluído | **Reescrever** — modelos e endpoints precisam alinhar com `UserEmpresaVinculo` + `EmpresaModulo` (não `ContaModulo`) |
| Step 10 — `backoffice.platform` | 🔜 Pendente | Implementar **direto** com nova arquitetura — listar Contas, Empresas, EmpresaModulo; expor `POST /admin/impersonate` |

**Ação prévia bloqueante (Step "1c"):**
- Migration de schema dos novos modelos em `public` (`Empresa`, `EmpresaModulo`, `UserEmpresaVinculo`, `VinculoModuloExtra`, `PapelTemplate`, `PapelTemplatePapel`, `Fatura`, `ImpersonationLog`)
- Drop dos modelos revogados (`ContaModulo`, `MembershipPapel`, `Domain`)
- Migration no schema tenant (`EmpresaMirror`, `Perfil`, `PerfilPapel`)
- Substituição de middlewares (`TenantMainMiddleware` → `JWTDecodeMiddleware` + `JWTTenantMiddleware`)
- Refatorar `EmpresaContextMiddleware` para ler `ctx.empresa_id` do JWT

---

## 8. Riscos arquiteturais novos

| # | Risco | Severidade | Mitigação |
|---|---|---|---|
| AR-R1 | Signal síncrono `sync_empresa_mirror` em `Empresa.save` falha (schema da Conta indisponível) → `Empresa.save` aborta | **Alto** | Wrapper `transaction.atomic` na operação fonte; comando `rebuild_empresa_mirror` para re-sync manual; alerta operacional se signal falha |
| AR-R2 | JWT com `ctx.conta_id` adulterado → IDOR | **Alto (mitigado)** | Assinatura HS256/RS256 cobre; `JWTDecodeMiddleware` rejeita assinaturas inválidas antes de tocar em qualquer tenant |
| AR-R3 | Cache LRU de `Conta` por `conta_id` (60s) sob alta concorrência → primeira request paga latência de 1 query DB | Médio | Pre-warm em boot com `Conta.objects.filter(ativo=True)` quando nº pequeno; fallback aceitável |
| AR-R4 | Impersonation read-write → staff malicioso causa dano em dado de cliente | Médio | `ImpersonationLog` cobre rastreabilidade; revisão semanal automática (Atlas); revogação por TTL fixo |
| AR-R5 | 3 SPAs separadas → componente compartilhado em `shared/` desincroniza entre bundles | Médio | CI valida hashes de `shared/` em cada bundle; transição para monorepo (npm workspaces / pnpm) após v1 estabilizar |
| AR-R6 | `EmpresaMirror` desincroniza após restore parcial de backup (schema tenant) | Médio | Comando `rebuild_empresa_mirror` parte de runbook de restore |
| AR-R7 | User com 0 `UserEmpresaVinculo` ativos mas com `Membership(is_account_owner=True)` → não consegue acessar ERP, mas é dono | Baixo (UX) | Account portal exibe estado e direciona para criar vínculo próprio na Empresa-matriz |

---

## 9. Open Questions diferidas

- [ ] **OQ-R1** — Modo de billing default (`consolidado` vs `por_empresa`): aplica-se a contas existentes ou cada Conta escolhe no onboarding? **Diferida para Ciclo 3 (billing).**
- [ ] **OQ-R2** — `Conta.billing_mode` pode ser alterado mid-período? Política proposta: alteração só vale para próximo período. **Diferida.**
- [ ] **OQ-R3** — Sincronização `EmpresaMirror`: se schema da Conta está em manutenção (D-R05 nível 2), signal grava em `OutboxEvent` para retry? **Diferida.** Por ora, manutenção implica `Empresa.save` no `public` falha — aceitável.
- [ ] **OQ-R4** — Vanity URL futura (`{slug}.gocontrol.com.br`): resolvedor adicional ao lado de `JWTTenantMiddleware` ou redirect para origin fixa? **Diferida.**
- [ ] **OQ-R5** — Switch de Conta com `current_empresa_id` salvo no User (LF4) precisa ser por User ou por (User, Conta)? **Diferida** — Bolt usa por (User, Conta) no piloto.

---

## 10. Follow-ups consolidados (para Compass replanjar Ciclo 2)

Ordem sugerida (sequência crítica → menos crítica):

1. **F-R02.1** Substituir middlewares de tenant (`JWTDecodeMiddleware` + `JWTTenantMiddleware`) — bloqueia tudo
2. **F-R03.1** + **F-R04.1** + **F-R05.1** + **F-R06.1** + **F-R12.1** + **F-R11.1** Migrations de `public` (modelos novos + remoção de revogados)
3. **F-R08.1** Migration de tenant para `EmpresaMirror` + signal síncrono
4. **F-R07.1** + **F-R07.2** Migrations de `Perfil`/`PerfilPapel` (TENANT) e `PapelTemplate` (public)
5. **F-R09.1** Endpoints de auth (3 etapas + 2 switches)
6. **F-R09.2** Refatorar `EmpresaContextMiddleware` para ler do JWT
7. Refatorar Steps 7/8/9 (Modules endpoint + sidebar + backoffice account) — D-R05/D-R06
8. **F-R11.2/3/4** Implementar fluxo de impersonation + banner + LGPD
9. **F-R10.1/2/3/4** Separar 3 SPAs (pode rodar em paralelo após item 5)
10. **F-R01.2** Configurar Traefik/Nginx com 3 origins fixas
11. **F-R12.2** Feature de billing (não bloqueia piloto)

**Owner principal:** @bolt-executor (implementação) + @grid-tester (TDD em todo passo) + @compass-planner (replan dos Steps a partir do passo 7).

---

## 11. Referências

- Decisões aprovadas: `./[C]decisions-redesign-identidade-tenancy.md` (D-R01..D-R12)
- ADR v1 (parcialmente substituído): `./[C]architecture-migracao-minierp-adianti-python-react.md`
- Design decisions UI/UX (D21/D22 ainda válidos para Backoffice): `./[C]design-decisions-go-control-erp.md`
- PRD: `./[C]prd-migracao-minierp-adianti-python-react.md`
- Plano (a replannejar): `./[C]plan-migracao-minierp-adianti-python-react.md`
- Repositório-alvo: `/home/evonexus/evo-projects/go-control-erp/`
- Guardrails para agentes (atualizar): `/home/evonexus/evo-projects/go-control-erp/docs/agent-instructions.md`
