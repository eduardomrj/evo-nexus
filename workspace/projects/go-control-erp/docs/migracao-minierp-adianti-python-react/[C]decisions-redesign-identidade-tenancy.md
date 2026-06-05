# Decisões de Redesign — Identidade, Tenancy e Estrutura de Portais
## GO Control ERP — Sessão de Discovery 2026-05-08

> **Status:** APROVADO por Eduardo Martins em 2026-05-08  
> **Substitui parcialmente:** D8, D9, D10, D11, D12, D21, D22 do ADR principal  
> **Próximo passo:** @apex-architect atualiza o ADR com estas decisões → @compass-planner replana Ciclo 2

---

## D-R01 — Estrutura de portais: 3 URLs fixas, sem subdomínio por Conta

**Decisão:** Três portais com URLs fixas. Subdomínio por Conta eliminado completamente.

| Portal | Homologação | Produção |
|---|---|---|
| ERP | `erp.myworkhome.com.br` | `erp.gocontrol.com.br` |
| Account Manager | `account.myworkhome.com.br` | `account.gocontrol.com.br` |
| Platform Admin | `admin.myworkhome.com.br` | `admin.gocontrol.com.br` |

**Drivers:**
- Subdomínio por Conta exige provisionamento no Cloudflare a cada onboarding → atrito operacional inaceitável no início
- `{slug}.gocontrol.com.br` pode ser retomado no futuro como vanity URL (whitelabel) — sem impacto arquitetural

**Consequências:**
- Modelo `Domain` (django-tenants) torna-se desnecessário — pode ser removido
- `TenantMainMiddleware` (hostname routing) é substituído por `JWTTenantMiddleware` (ver D-R02)
- `Conta.slug` mantido apenas como identificador amigável, sem função de roteamento

---

## D-R02 — Multi-tenancy: 1 schema PostgreSQL por Conta, roteado pelo JWT

**Decisão:** Manter 1 schema PostgreSQL por Conta (isolamento físico preservado). Roteamento do schema migra de hostname para `conta_id` no claim JWT.

**Implementação:**
```python
class JWTTenantMiddleware:
    """Substitui TenantMainMiddleware. Lê conta_id do JWT claim."""
    def __call__(self, request):
        token = extract_bearer_token(request)  # sem hit no DB de tenant
        if token:
            conta_id = decode_jwt_claim(token, 'ctx.conta_id')
            conta = Conta.objects.using('default').get(id=conta_id)
            connection.set_tenant(conta)
        return self.get_response(request)
```

**Ordem obrigatória de middlewares:**
1. `JWTDecodeMiddleware` — decodifica token, valida assinatura (sem DB)
2. `JWTTenantMiddleware` — lê `conta_id`, ativa schema via `connection.set_tenant()`
3. `JWTAuthMiddleware` (DRF) — autentica User (já no schema correto)

**Sem autenticação circular:** `User` vive em `public` (SHARED_APPS). Decode do JWT roda antes de ativar o tenant. `conta_id` no claim é suficiente — `ctx.schema` pode ser removido ou mantido como redundância defensiva.

**Consequências:**
- Isolamento físico mantido: backup por cliente via `pg_dump -n schema_da_conta` continua funcionando
- Race condition de schema eliminada pelo JWT (não pelo hostname)
- IDOR cross-tenant prevenido pelo middleware + RLS por `empresa_id` como segunda camada

---

## D-R03 — Modelo de Conta reformulado: entidade de billing + proprietário

**Decisão:** `Conta` deixa de ser o container operacional e passa a ser a entidade de billing e dados do proprietário.

**Modelo resultante:**
```python
class Conta(TenantMixin):  # TenantMixin mantido para django-tenants
    id                    = UUIDField(primary_key=True)
    proprietario          = ForeignKey('platform.User', ...)
    razao_social_billing  = CharField(max_length=200)  # empresa para faturamento
    cnpj_billing          = CharField(max_length=14)
    plano                 = CharField(choices=['starter','pro','enterprise'])
    forma_pagamento       = CharField(...)
    ativo                 = BooleanField(default=True)
    schema_name           = CharField(unique=True)  # ex: tenant_12345678000195
    # REMOVIDOS: subdomain, slug para roteamento DNS
    # MANTIDO: slug como identificador amigável
```

**O que mudou:** Conta não agrega módulos diretamente — isso passa para `EmpresaModulo` (D-R05). Conta agrupa Empresas para fins de billing e administração.

---

## D-R04 — Empresa como unidade operacional primária

**Decisão:** `Empresa` é a unidade operacional real. A matriz é um registro de Empresa como qualquer outra. Empresas de ramos diferentes podem coexistir na mesma Conta.

```python
class Empresa(TimestampMixin):  # em SHARED_APPS (public schema)
    id           = UUIDField(primary_key=True)
    conta        = ForeignKey(Conta, on_delete=CASCADE)
    cnpj         = CharField(max_length=14)
    razao_social = CharField(max_length=200)
    nome_fantasia = CharField(max_length=200, blank=True)
    tipo         = CharField(choices=['matriz','filial','independente'], default='independente')
    empresa_pai  = ForeignKey('self', null=True, blank=True, on_delete=SET_NULL)
    ativo        = BooleanField(default=True)
```

**Regra de negócio:** Ao criar uma Conta, a empresa matriz deve ser criada imediatamente como `Empresa(tipo='matriz')`. Uma Conta sem Empresa matriz não pode acessar o ERP.

**Mesma empresa (CNPJ) em Contas diferentes:** UUID diferente — sem conflito. É tratado como empresa independente para todos os fins.

---

## D-R05 — EmpresaModulo: módulos contratados por Empresa

**Decisão:** `ContaModulo` é substituído por `EmpresaModulo`. Granularidade de módulo é por Empresa, não por Conta.

```python
class EmpresaModulo(TimestampMixin):  # em SHARED_APPS
    id               = UUIDField(primary_key=True)
    empresa          = ForeignKey(Empresa, on_delete=CASCADE)
    modulo           = ForeignKey(Modulo, on_delete=PROTECT)
    ativo            = BooleanField(default=True)
    em_manutencao    = BooleanField(default=False)
    params_overrides = JSONField(default=dict)
    contratado_em    = DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('empresa', 'modulo')
```

**Billing:** Cada `EmpresaModulo` gera uma linha de cobrança. Fatura pode ser consolidada por Conta (somando todas as empresas) ou discriminada por Empresa — decisão de billing no futuro.

**Ativação de módulo:** Ao setar `ativo=True`, Celery task executa:
1. `run_migrations_for_module(conta, modulo)` — roda migrations no schema da Conta
2. `seed_initial_data(empresa, modulo)` — popula dados-semente (tipos, categorias, Perfis padrão)

---

## D-R06 — UserEmpresaVinculo: vínculo User ↔ Empresa com Perfil

**Decisão:** Introduzir `UserEmpresaVinculo` como camada de vínculo entre usuário e empresa específica. Substitui a semântica operacional de `Membership` (que passa a ser apenas o elo User ↔ Conta para fins de `is_account_owner`).

```python
class UserEmpresaVinculo(TimestampMixin):  # em SHARED_APPS
    id              = UUIDField(primary_key=True)
    user            = ForeignKey('platform.User', on_delete=CASCADE)
    empresa         = ForeignKey(Empresa, on_delete=CASCADE)
    perfil          = ForeignKey('Perfil', on_delete=PROTECT)
    status          = CharField(choices=['invited','active','suspended'], default='invited')
    convidado_por   = ForeignKey('platform.User', null=True, related_name='convites_feitos')
    invited_at      = DateTimeField(auto_now_add=True)
    accepted_at     = DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('user', 'empresa')

class VinculoModuloExtra(TimestampMixin):  # módulos adicionais além do Perfil
    vinculo  = ForeignKey(UserEmpresaVinculo, on_delete=CASCADE)
    modulo   = ForeignKey(Modulo, on_delete=CASCADE)
    ativo    = BooleanField(default=True)
```

**Cross-Conta:** Um usuário pode ter `UserEmpresaVinculo` em empresas de Contas diferentes. Convite é livre — não requer aprovação da Conta de origem do usuário.

**Perfil vs Papel:**
- `Papel` = permissão granular dentro de um módulo (`erp.financeiro.editor`)
- `Perfil` = template funcional que agrega Papéis de vários módulos (ex: CAIXA, VENDEDOR, GERENTE)
- `UserEmpresaVinculo.perfil` define o conjunto de permissões na emissão do JWT

---

## D-R07 — Perfil: template de permissões por empresa no schema da Conta

**Decisão:** `Perfil` vive no schema da Conta (TENANT_APP). Account Manager cria/personaliza Perfis por empresa. Platform Staff oferece `PapelTemplate` como catálogo opcional em `public`.

```python
# Em TENANT_APP (schema da Conta)
class Perfil(TimestampMixin):
    id       = UUIDField(primary_key=True)
    empresa  = ForeignKey('erp_core.EmpresaMirror', on_delete=CASCADE)
    nome     = CharField(max_length=100)  # 'CAIXA', 'VENDEDOR', 'GERENTE'
    papeis   = ManyToManyField('platform.Papel', through='PerfilPapel')
    is_template_base = BooleanField(default=False)  # se copiado de PapelTemplate

# Em SHARED_APPS (public schema)
class PapelTemplate(TimestampMixin):
    nome       = CharField(max_length=100)
    descricao  = TextField()
    papeis     = ManyToManyField('platform.Papel')
    # Apenas leitura para Account Manager — pode copiar para criar Perfil próprio
```

**Emissão do JWT:** Ao selecionar empresa, backend consulta `UserEmpresaVinculo` (public) → carrega `perfil_id` → ativa schema da Conta (`set_tenant`) → resolve `Perfil.papeis` → inclui claim `permissions` no token.

---

## D-R08 — Arquitetura federada: Backoffice DB + ERP Schema

**Decisão:** Dois domínios de dados separados com sincronização por UUID.

```
┌──────────────────────────────────────────┐
│  BACKOFFICE DB (schema: public)           │
│  User, Conta, Empresa                     │
│  UserEmpresaVinculo, Membership           │
│  EmpresaModulo, Modulo                    │
│  PapelTemplate, Papel                     │
│                                           │
│  → account.gocontrol.com.br               │
│  → admin.gocontrol.com.br                 │
└────────────────┬─────────────────────────┘
                 │ UUID idêntico (Empresa.id)
                 ▼ Signal síncrono (post_save/post_delete)
┌──────────────────────────────────────────┐
│  ERP SCHEMA (1 por Conta)                 │
│  EmpresaMirror (UUID = Empresa.id)        │
│  Perfil, PerfilPapel                      │
│  Pessoas, Produtos, Movimentos            │
│  NF-e, Estoque, Financeiro, PDV           │
│                                           │
│  → erp.gocontrol.com.br                   │
└──────────────────────────────────────────┘
```

**`EmpresaMirror` em `erp.core` (TENANT_APP):**
```python
class EmpresaMirror(TimestampMixin):
    id           = UUIDField(primary_key=True)  # MESMO UUID do public.Empresa
    conta_id     = UUIDField()                  # para auditoria
    cnpj         = CharField(max_length=14)
    razao_social = CharField(max_length=200)
    tipo         = CharField(max_length=20)
    ativo        = BooleanField(default=True)
```

**Sincronização:** `post_save` e `post_delete` em `Empresa` (public) disparam signal síncrono que atualiza `EmpresaMirror` no schema da Conta. Falha aborta a operação original (atomicidade garantida). Ao provisionar novo schema, popula mirror com todas as Empresas existentes da Conta.

---

## D-R09 — Fluxo de login e emissão de JWT

**Decisão:** Login em 3 etapas progressivas com seleção de contexto.

```
POST /auth/login (contexto: public)
  → Valida email + senha (User global em public)
  → Lista Contas via Membership
     ├── 1 Conta → ativa automaticamente
     └── N Contas → retorna lista → frontend mostra seletor

POST /auth/select-conta {conta_id}
  → Lista UserEmpresaVinculo do usuário nessa Conta (em public)
     ├── 1 Empresa → entra direto
     └── N Empresas → retorna lista → frontend mostra seletor

POST /auth/select-empresa {empresa_id}
  → Ativa schema da Conta (set_tenant via conta_id)
  → Resolve Perfil → carrega Papéis
  → Emite JWT:
     {
       "sub": user_id,
       "ctx": {
         "conta_id": "...",
         "empresa_id": "...",
         "perfil": "VENDEDOR",
         "permissions": ["erp.pessoas.view", "erp.produtos.view", ...]
       },
       "is_account_owner": true/false,
       "is_platform_staff": false
     }
```

**Switch de empresa (dentro do ERP, mesma Conta):** `POST /auth/switch-empresa {empresa_id}` → novo JWT, sem senha.

**Switch de Conta (cross-Conta):** `POST /auth/switch-conta {conta_id}` → volta para seletor de empresa da nova Conta, sem senha.

**Token refresh:** renova com mesmo `conta_id` + `empresa_id` (LF4 — volta para empresa que estava).

---

## D-R10 — 3 frontends separados

**Decisão:** 3 SPAs React independentes com login próprio. Mesma base de usuários (`platform.User`).

| Portal | Entry point | Auth scope |
|---|---|---|
| **ERP** | `erp.*` | User com `UserEmpresaVinculo` ativo |
| **Account** | `account.*` | User com `Membership.is_account_owner=True` |
| **Platform Admin** | `admin.*` | User com `is_platform_staff=True` |

**Sem SSO cross-portal:** cada portal faz login independente contra o mesmo backend.

**Account Manager no ERP:** ícone de perfil no ERP exibe link "Ir para Minha Conta" (`account.*`) quando `is_account_owner=True` no JWT.

**Usuário com `is_platform_staff=True` E `is_account_owner=True`:** acessa cada portal pela URL correspondente — sem tela de escolha unificada.

**Compartilhamento de código:** componentes comuns (`StatusBadge`, `ConfirmDialog`, hooks de auth) em diretório `shared/` — copiados por build ou extraídos como lib interna. Decisão de monorepo vs polyrepo fica para quando os 3 builds existirem.

---

## D-R11 — Platform Staff: impersonation com audit log (read-write)

**Decisão:** Platform Staff pode acessar o ERP de qualquer Conta para diagnóstico e correção, com todas as ações registradas com o nome do usuário Staff.

**Fluxo de impersonation:**
```
1. Staff em admin.gocontrol.com.br seleciona Conta Alfa
2. POST /admin/impersonate {conta_id: "alfa"}
   → Valida is_platform_staff=True
   → Emite JWT especial:
     {
       "sub": staff_user_id,
       "ctx": {
         "conta_id": "alfa",
         "impersonating": true,
         "impersonated_by": staff_user_id,
         "empresa_id": null  # escolhe na próxima tela
       }
     }
3. Staff abre erp.gocontrol.com.br com token especial
4. ERP exibe banner "⚠️ Modo suporte — ações auditadas como [nome do staff]"
5. Todas as operações registradas em `ImpersonationLog`:
   {
     staff_user_id, conta_id, empresa_id,
     action, resource_type, resource_id,
     before_state, after_state,
     timestamp
   }
6. JWT especial expira em 2h (não renovável automaticamente)
```

**Scope:** Read-write. Staff pode corrigir dados em nome do cliente.

**Auditoria:** `ImpersonationLog` em `public` (SHARED_APPS) + entrada em `AuditLog` do schema da Conta com `actor = "staff:{nome_do_staff}"`.

---

## D-R12 — Billing discriminado por Empresa

**Decisão:** Billing pode ser gerado por Empresa (cada CNPJ tem sua fatura). Conta é a entidade pagadora.

**Modelo:**
```python
class Fatura(TimestampMixin):
    conta    = ForeignKey(Conta, ...)  # quem paga
    empresa  = ForeignKey(Empresa, null=True, ...)  # null = fatura consolidada da Conta
    periodo  = DateField()  # mês de competência
    status   = CharField(choices=['aberta','paga','vencida','cancelada'])
    itens    = JSONField()  # [{modulo_code, valor, descricao}, ...]
    total    = DecimalField(...)
```

**Regra:** Uma Conta pode ter N faturas por período (uma por Empresa com módulos ativos). Detalhe do módulo + valor = item da fatura.

---

## Impacto no Ciclo 2 atual

Os Steps 6-9 foram implementados com a arquitetura anterior (django-tenants + subdomínio). Precisam ser revisados:

| Step | Status | Impacto |
|---|---|---|
| Step 6 — Padronização de rotas | ✅ Concluído | Rotas mantidas — sem impacto |
| Step 7 — GET /api/v1/erp/modules/ | ✅ Concluído | Migrar de ContaModulo → EmpresaModulo |
| Step 8 — Sidebar dinâmica | ✅ Concluído | Adaptar para EmpresaModulo |
| Step 9 — backoffice.account | ✅ Concluído | Reescrever models: UserEmpresaVinculo + EmpresaModulo |
| Step 10 — backoffice.platform | 🔜 Pendente | Implementar com nova arquitetura |

**Próximo passo antes de retomar:** @apex-architect produz ADR atualizado (D8-D12 revisados + D-R01 a D-R12 formalizados) → @compass-planner replana Ciclo 2 com novos Steps de refatoração.

---

## Resumo das decisões aprovadas

| Decisão | O que muda | Aprovado |
|---|---|---|
| D-R01 | URLs fixas, sem subdomínio por Conta | ✅ |
| D-R02 | JWT-based schema routing (sem hostname) | ✅ |
| D-R03 | Conta = billing entity | ✅ |
| D-R04 | Empresa = unidade operacional | ✅ |
| D-R05 | Módulos por Empresa (EmpresaModulo) | ✅ |
| D-R06 | UserEmpresaVinculo + VinculoModuloExtra | ✅ |
| D-R07 | Perfil no schema da Conta | ✅ |
| D-R08 | Arquitetura federada + EmpresaMirror | ✅ |
| D-R09 | Fluxo de login com seleção progressiva | ✅ |
| D-R10 | 3 frontends separados | ✅ |
| D-R11 | Impersonation read-write com audit log | ✅ |
| D-R12 | Billing por Empresa | ✅ |
