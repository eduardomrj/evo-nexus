---
author: claude
agent: compass-planner
type: work-plan
date: 2026-05-07
plan-name: ciclo2-redesign-identidade-tenancy
status: ready
mode: direct
feature: migracao-minierp-adianti-python-react
supersedes: Steps 6-10 do plan original (parcialmente)
prd: ./[C]requisitos-go-control-erp.md
decisions: ./[C]decisions-redesign-identidade-tenancy.md
---

# Plano Revisado — Ciclo 2 (Redesign de Identidade + Backoffice)
## GO Control ERP — Pós-decisões D-R01..D-R12 (2026-05-08)

## Context

As decisões D-R01..D-R12 (sessão de discovery 2026-05-08) reformularam profundamente a camada de identidade e tenancy:

- Subdomínio por Conta foi **eliminado** (D-R01) → 3 URLs fixas
- Roteamento de schema migra de hostname para JWT claim (D-R02)
- `Conta` deixa de ser container operacional e vira **entidade de billing** (D-R03)
- `Empresa` torna-se **unidade operacional primária** (D-R04)
- Módulos passam a ser por **Empresa**, não por Conta (D-R05)
- Surge `UserEmpresaVinculo` substituindo a semântica operacional de `Membership` (D-R06)
- `Perfil` (template de papéis) vive no schema da Conta (D-R07)
- Arquitetura federada Backoffice DB ↔ ERP Schema com `EmpresaMirror` (D-R08)
- Login em 3 etapas com seleção progressiva (D-R09)
- 3 frontends SPA separados (D-R10)
- Impersonation de Platform Staff com audit log (D-R11)
- Billing por Empresa (D-R12)

Os Steps 6, 7, 8 e 9 já foram implementados sobre a arquitetura antiga (`ContaModulo`, `Membership` operacional, hostname routing). Este plano define o que **refatorar**, **descartar** e **acrescentar** para alinhar o Ciclo 2 ao novo desenho — **sem tocar Ciclo 3** (módulos ERP de domínio).

## Objectives

- Camada de identidade reformulada: `Conta` (billing), `Empresa` (operacional), `UserEmpresaVinculo`, `EmpresaModulo`, `EmpresaMirror`, `Perfil` no schema da Conta
- `JWTTenantMiddleware` substitui `TenantMainMiddleware` (sem hostname routing)
- Fluxo de login em 3 etapas (`/auth/login` → `/auth/select-conta` → `/auth/select-empresa`) emitindo JWT com `ctx.conta_id` + `ctx.empresa_id` + `permissions`
- Sincronização federada `Empresa (public)` ↔ `EmpresaMirror (schema tenant)` via signal síncrono
- Endpoints `/api/v1/erp/modules/` e sidebar dinâmica migrados para `EmpresaModulo`
- backoffice.account refatorado sobre `UserEmpresaVinculo` + `EmpresaModulo`
- backoffice.platform implementado com a nova arquitetura, incluindo wizard de criação de Conta + Empresa matriz e fluxo de impersonation
- 3 SPAs separados (ERP / Account / Platform Admin) com login independente — bootstrap mínimo neste ciclo (separação física de bundles + roteamento de domínio); polish de UX cross-portal fica para Ciclo 2.5
- Cobertura ≥ 80% nos services novos/refatorados; suite de testes de isolamento cross-tenant verde

## Guardrails

### Must Have

- `JWTTenantMiddleware` ativa o schema **antes** de `JWTAuthMiddleware` (DRF) e **antes** de qualquer view; ordem documentada e testada
- `Empresa` em SHARED_APPS (public) com FK para `Conta`; `EmpresaMirror` em TENANT_APP (schema da Conta) com **mesmo UUID** do public
- Signal síncrono `post_save`/`post_delete` em `Empresa` atualiza `EmpresaMirror` no schema correspondente — falha aborta a transação (atomicidade)
- `EmpresaModulo` substitui completamente `ContaModulo` — modelo antigo removido após migração de dados (aceitável: dev tem dados de teste; sem migração de produção)
- `UserEmpresaVinculo` é a fonte de verdade para "user pode acessar empresa X" — `Membership` mantido apenas como elo billing/owner (`is_account_owner`)
- `Perfil` vive no schema da Conta; `PapelTemplate` em public é catálogo read-only
- JWT inclui `ctx.conta_id`, `ctx.empresa_id`, `ctx.perfil`, `permissions` (resolvidos na emissão)
- Dois bypasses de tenant explicitamente autorizados: rotas `/api/v1/auth/login`, `/api/v1/auth/select-conta`, `/api/v1/auth/me/contexts` (não dependem de tenant ativo)
- Toda escrita em `Empresa` executa em transaction com o sync para `EmpresaMirror` — rollback se um falhar
- Audit log para impersonation com `actor="staff:{nome}"` em todas as ações no schema da Conta
- TDD obrigatório (@grid-tester antes de @bolt-executor) para Steps 11, 12, 13, 14, 15
- Testes de isolamento cross-tenant: usuário da Conta A não pode acessar dados da Conta B mesmo com `conta_id` forjado no JWT (assinatura inválida)
- Linguagem pt-BR em mensagens de erro e UI

### Must NOT Have

- Subdomínio por Conta (`{slug}.gocontrol.com.br`) — eliminado
- `Domain` model (django-tenants) — pode ser removido após Step 11
- Implementação de módulos ERP novos (Financeiro, Comercial, Estoque, etc.) — Ciclo 3
- Whitelabel / vanity URLs — fora do escopo deste ciclo
- SSO cross-portal — cada SPA faz login independente
- Migração de dados de produção — só dados de dev, recriáveis

## Task Flow

```
Step 11 (Refactor models centrais) ──┐
   ↓                                  │
Step 12 (JWTTenantMiddleware + login) │
   ↓                                  │
Step 13 (EmpresaMirror + sync signal) │
   ↓                                  │
Step 14 (Migrar Steps 7-8 para EmpresaModulo)
   ↓
Step 15 (Refatorar backoffice.account)
   ↓
Step 16 (backoffice.platform completo + impersonation)
   ↓
Step 17 (Bootstrap dos 3 frontends separados)
   ↓
Step 18 (Smoke test ponta-a-ponta + handoff Oath)
```

Steps 11-13 são fundamentais e bloqueiam tudo. 14-16 são sequenciais. 17 pode iniciar em paralelo após 15.

## Detailed Steps

### Step 11 — Refatorar modelos centrais (Conta / Empresa / EmpresaModulo / UserEmpresaVinculo)

**Objetivo:** Substituir o modelo "Conta = container operacional" por "Conta = billing + Empresa operacional" conforme D-R03..D-R06.

**O que fazer:**

1. **`apps.platform` — alterações de modelo (SHARED_APPS, schema public):**
   - `Conta`:
     - Remover: `nome` operacional, `subdomain`/`slug` para roteamento DNS
     - Adicionar: `proprietario` (FK User), `razao_social_billing`, `cnpj_billing`, `plano`, `forma_pagamento`
     - Manter: `id` (UUID), `schema_name` (`tenant_{cnpj_billing_14}`), `ativo`, `slug` (apenas como identificador amigável)
     - Manter `TenantMixin` (django-tenants para schema management)
   - **Novo:** `Empresa(TimestampMixin)` em `apps.platform` (SHARED) — NÃO no schema da Conta:
     ```python
     class Empresa(TimestampMixin):
         id = UUIDField(primary_key=True)
         conta = ForeignKey(Conta, on_delete=CASCADE)
         cnpj = CharField(max_length=14)
         razao_social = CharField(max_length=200)
         nome_fantasia = CharField(blank=True)
         tipo = CharField(choices=['matriz','filial','independente'])
         empresa_pai = ForeignKey('self', null=True, on_delete=SET_NULL)
         ativo = BooleanField(default=True)
     ```
   - **Novo:** `EmpresaModulo(TimestampMixin)` substitui `ContaModulo`:
     ```python
     class EmpresaModulo(TimestampMixin):
         empresa = ForeignKey(Empresa, on_delete=CASCADE)
         modulo = ForeignKey(Modulo, on_delete=PROTECT)
         ativo = BooleanField(default=True)
         em_manutencao = BooleanField(default=False)
         params_overrides = JSONField(default=dict)
         contratado_em = DateTimeField(auto_now_add=True)
         class Meta:
             unique_together = ('empresa', 'modulo')
     ```
   - **Novo:** `UserEmpresaVinculo(TimestampMixin)`:
     ```python
     class UserEmpresaVinculo(TimestampMixin):
         user = ForeignKey('platform.User', on_delete=CASCADE)
         empresa = ForeignKey(Empresa, on_delete=CASCADE)
         perfil_id = UUIDField()  # FK lógica para Perfil no schema da Conta
         status = CharField(choices=['invited','active','suspended'])
         convidado_por = ForeignKey('platform.User', null=True, related_name='convites_feitos')
         invited_at, accepted_at
         class Meta:
             unique_together = ('user', 'empresa')
     ```
   - **Novo:** `VinculoModuloExtra` (módulos adicionais além do Perfil)
   - **Membership simplificado** — manter, mas só com `is_account_owner` + status (sem semântica operacional)
   - **Remover:** `ContaModulo` (após Step 14 migrar consumidores)
   - **Remover:** `MembershipPapel` operacional (substituído por `UserEmpresaVinculo.perfil_id`)
   - **Manter:** `Modulo`, `Papel`, `MigrationRun`, `PlatformFlag`
   - **Novo:** `PapelTemplate(TimestampMixin)` — catálogo read-only para Account Manager copiar

2. **Migrations:**
   - Criar `0010_redesign_identidade.py` em `apps.platform` que faz tudo num bloco (dev sem produção, simplifica)
   - Drop `ContaModulo`, `MembershipPapel` operacional
   - Criar `Empresa`, `EmpresaModulo`, `UserEmpresaVinculo`, `VinculoModuloExtra`, `PapelTemplate`
   - Atualizar `Conta` (drop `subdomain`, adicionar campos de billing)

3. **Manager de tenant agora cria Empresa matriz junto com a Conta:**
   - `Conta.objects.criar_com_matriz(cnpj_billing, razao_social, owner_user, ...)` em uma transação:
     - Cria Conta + provisiona schema
     - Cria Empresa(tipo='matriz', cnpj=cnpj_billing, conta=conta)
     - Cria Membership(user=owner, conta=conta, is_account_owner=True)
     - Cria UserEmpresaVinculo(user=owner, empresa=matriz, perfil=Perfil.OWNER) — Perfil OWNER seedado
     - Ativa `EmpresaModulo` para `erp.pessoas` na matriz por padrão

**Critérios de aceitação:**
- [ ] `python manage.py migrate_schemas --shared` aplica sem erro
- [ ] Criar Conta sem matriz é proibido (regra de negócio): `Conta.objects.create(...)` direto levanta `IntegrityError` ou ValidationError
- [ ] `Conta.objects.criar_com_matriz(...)` cria Conta + schema + Empresa matriz + Membership + UserEmpresaVinculo em uma transação atômica
- [ ] Falha em qualquer etapa do criar_com_matriz reverte tudo (sem schema órfão, sem Empresa órfã)
- [ ] Testes de model: 30+ testes cobrindo constraints, transações, isolamento
- [ ] Cobertura ≥ 80% em `apps.platform.models` e `apps.platform.services.conta_service`

**Dependências:** Nenhuma (primeiro passo do ciclo).
**Agente responsável:** @grid-tester (testes de model e transação) → @bolt-executor (implementação)
**Complexidade:** VERY HIGH

---

### Step 12 — JWTTenantMiddleware + fluxo de login em 3 etapas

**Objetivo:** Substituir `TenantMainMiddleware` (hostname routing) por `JWTTenantMiddleware` (claim routing) e implementar o login em 3 etapas (D-R02, D-R09).

**O que fazer:**

1. **Novo middleware** `apps.core.middleware.JWTTenantMiddleware`:
   ```python
   class JWTTenantMiddleware:
       def __call__(self, request):
           # Bypass para rotas pré-tenant
           if request.path in PRE_TENANT_PATHS:
               connection.set_schema_to_public()
               return self.get_response(request)
           token = extract_bearer_token(request)
           if not token:
               return self.get_response(request)  # deixa DRF responder 401
           try:
               payload = decode_jwt(token)
               conta_id = payload['ctx']['conta_id']
               conta = Conta.objects.using('default').get(id=conta_id)
               connection.set_tenant(conta)
           except (InvalidToken, Conta.DoesNotExist):
               return JsonResponse({'detail': 'Tenant inválido'}, status=403)
           return self.get_response(request)
   ```
   - `PRE_TENANT_PATHS = ['/api/v1/auth/login', '/api/v1/auth/select-conta', '/api/v1/auth/me/contexts', '/api/v1/maintenance/status']`

2. **Ordem dos middlewares** (`config/settings/base.py`):
   ```python
   MIDDLEWARE = [
       'apps.core.middleware.JWTDecodeMiddleware',     # decode + validate (sem DB)
       'apps.core.middleware.JWTTenantMiddleware',     # set_tenant via conta_id
       'django.middleware.security.SecurityMiddleware',
       'django.contrib.sessions.middleware.SessionMiddleware',
       'django.middleware.common.CommonMiddleware',
       # ... auth DRF ocorre via DEFAULT_AUTHENTICATION_CLASSES, já no schema correto
   ]
   ```

3. **Remover** `django_tenants.middleware.main.TenantMainMiddleware` da config; manter `django_tenants` em `SHARED_APPS` para gerenciar schemas mas sem o middleware de routing.

4. **Endpoints de login (3 etapas) em `apps.platform.views.auth`:**
   - `POST /api/v1/auth/login {email, password}`:
     - Valida em public; retorna `{access_token_provisorio, contas: [{id, razao_social_billing, cnpj}, ...]}`
     - Token provisório só permite chamar `/auth/select-conta` (claim `ctx.stage='select_conta'`)
   - `POST /api/v1/auth/select-conta {conta_id}`:
     - Valida Membership ativa; ativa schema; retorna `{access_token_provisorio2, empresas: [{id, razao_social, tipo, cnpj}, ...]}`
     - Lista `UserEmpresaVinculo` filtrado por `conta` + `status=active`
     - Token provisório2: `ctx.stage='select_empresa', conta_id=...`
   - `POST /api/v1/auth/select-empresa {empresa_id}`:
     - Resolve `Perfil` no schema da Conta → carrega `Papeis` → emite JWT final com `permissions`
     - Retorna `{access_token, refresh_token}` final
   - `POST /api/v1/auth/switch-empresa {empresa_id}` (mesma Conta) → novo JWT final, sem senha
   - `POST /api/v1/auth/switch-conta {conta_id}` → volta para fase de select-empresa, sem senha
   - `POST /api/v1/auth/refresh` — preserva conta_id + empresa_id (LF4)
   - `GET /api/v1/auth/me/contexts` — lista todas as Contas + Empresas que o user pode acessar (para troca rápida)

5. **Atalho de login (1 etapa)**: se user tem exatamente 1 Conta + 1 Empresa ativa, `POST /auth/login` já retorna o JWT final.

6. **Resolver permissions:**
   - Em `select-empresa`, ativar schema da Conta, carregar `Perfil` → `PerfilPapel` → `Papel.permissions` (concatenado) + `VinculoModuloExtra` ativos
   - Incluir no JWT como array de strings (`['erp.pessoas.view', 'erp.pessoas.edit', ...]`)

**Critérios de aceitação:**
- [ ] Login com user que tem 1 Conta + 1 Empresa retorna JWT final em 1 chamada
- [ ] Login com user que tem N Contas exige fluxo 3-step
- [ ] Token provisório de stage `select_conta` rejeitado em `/auth/select-empresa` (403)
- [ ] JWT final contém `ctx.conta_id`, `ctx.empresa_id`, `ctx.perfil`, `permissions`
- [ ] Request com `ctx.conta_id=A` e schema A → OK; request com `ctx.conta_id=A` mas assinatura inválida → 401; tentativa de forjar `ctx.conta_id=B` (sem chave) → 401
- [ ] `JWTTenantMiddleware` ativa schema correto antes de DRF authenticator rodar
- [ ] `switch-empresa` emite novo JWT sem pedir senha
- [ ] Refresh preserva `empresa_id` (volta para a empresa que o user estava)
- [ ] Suite de isolamento cross-tenant: 5+ testes (forjar conta_id, schema mismatch, etc.) — todos GREEN
- [ ] Cobertura ≥ 80% em `apps.platform.views.auth` e `apps.core.middleware`

**Dependências:** Step 11
**Agente responsável:** @grid-tester (testes de auth + middleware + isolamento) → @bolt-executor → @vault-security (audit do middleware antes do merge)
**Complexidade:** VERY HIGH

---

### Step 13 — EmpresaMirror + sync signal Empresa (public) ↔ EmpresaMirror (schema)

**Objetivo:** Implementar a arquitetura federada (D-R08): Empresa vive em public, EmpresaMirror espelha no schema da Conta com mesmo UUID.

**O que fazer:**

1. **`apps.erp_core` (TENANT_APP, novo app):**
   ```python
   # apps/erp_core/models.py
   class EmpresaMirror(TimestampMixin):
       id = UUIDField(primary_key=True)  # MESMO UUID do public.Empresa
       conta_id = UUIDField()  # auditoria
       cnpj = CharField(max_length=14)
       razao_social = CharField(max_length=200)
       tipo = CharField(max_length=20)
       ativo = BooleanField(default=True)
   ```
   - Registrar `apps.erp_core` em `TENANT_APPS`
   - Migration aplicada em todos os schemas tenant existentes via `migrate_schemas`

2. **Signal síncrono em `apps.platform.signals.py`:**
   ```python
   @receiver(post_save, sender=Empresa)
   def sync_empresa_to_mirror(sender, instance, created, **kwargs):
       conta = instance.conta
       with schema_context(conta.schema_name):
           EmpresaMirror.objects.update_or_create(
               id=instance.id,
               defaults={
                   'conta_id': conta.id,
                   'cnpj': instance.cnpj,
                   'razao_social': instance.razao_social,
                   'tipo': instance.tipo,
                   'ativo': instance.ativo,
               },
           )

   @receiver(post_delete, sender=Empresa)
   def remove_empresa_from_mirror(sender, instance, **kwargs):
       with schema_context(instance.conta.schema_name):
           EmpresaMirror.objects.filter(id=instance.id).delete()
   ```
   - **Atomicidade:** signal roda dentro da transaction da operação original. Se o sync falhar, `transaction.atomic()` aborta o save de Empresa (raise propagado).
   - Usar `transaction.on_commit()` é **insuficiente** aqui — precisamos sync dentro da mesma transaction para garantir que falha aborte tudo.

3. **Provisionamento de schema novo (em `Conta.objects.criar_com_matriz`):**
   - Após criar schema, executar `migrate_schemas --schema={novo}` para criar tabelas TENANT_APP
   - Popular `EmpresaMirror` com todas as Empresas existentes da Conta (no caso da matriz, apenas 1)

4. **FK lógica em apps tenant:**
   - Models de domínio em TENANT_APPS usam `empresa_id = UUIDField(db_index=True)` referenciando `EmpresaMirror.id` (FK lógica, não FK Django, para não cruzar schemas)
   - Documentar regra em `coding-standards.md`

**Critérios de aceitação:**
- [ ] Criar Empresa em public propaga para EmpresaMirror no schema correto (mesmo UUID)
- [ ] Update em Empresa.razao_social atualiza EmpresaMirror.razao_social
- [ ] Delete de Empresa remove EmpresaMirror correspondente
- [ ] Falha do sync (ex: schema inexistente) aborta a operação original (raise propagado, transaction reverte)
- [ ] Provisionamento de Conta nova popula EmpresaMirror para a matriz
- [ ] Teste: criar 2 Contas, cada uma com sua matriz; consultar `EmpresaMirror.objects.all()` em cada schema retorna apenas a empresa daquela Conta
- [ ] Cobertura ≥ 80% em `apps.platform.signals` e `apps.erp_core.models`

**Dependências:** Step 11
**Agente responsável:** @apex-architect (revisar atomicidade do signal — alternativa: outbox pattern se signal síncrono provar fragilidade) → @grid-tester → @bolt-executor
**Complexidade:** HIGH

---

### Step 14 — Migrar Steps 7-8 para EmpresaModulo (sidebar dinâmica)

**Objetivo:** Atualizar `GET /api/v1/erp/modules/` e a sidebar dinâmica para alimentar-se de `EmpresaModulo` (filtrado pela `empresa_id` ativa no JWT) em vez de `ContaModulo`.

**O que fazer:**

1. **Backend `apps.platform.views.modules`:**
   - Endpoint `GET /api/v1/erp/modules/`:
     ```python
     def get(self, request):
         empresa_id = request.user_ctx['empresa_id']  # do JWT decoded pelo middleware
         qs = EmpresaModulo.objects.filter(
             empresa_id=empresa_id,
             ativo=True,
         ).select_related('modulo')
         # Filtrar pelos módulos que o usuário tem permissão (via Perfil.permissions)
         return Response([{
             'code': em.modulo.code,
             'nome': em.modulo.nome,
             'surface': em.modulo.surface,
             'em_manutencao': em.em_manutencao or em.modulo.em_manutencao,
         } for em in qs])
     ```
   - Cache Redis 30s por `(empresa_id, perfil_id)` — invalidado por signal em EmpresaModulo

2. **Frontend ERP — atualizar `useModules()` hook:**
   - Sem mudança de assinatura — backend mudou mas o contrato JSON é o mesmo
   - Adicionar invalidação ao trocar empresa via `switch-empresa`

3. **Sidebar — adaptação mínima:**
   - Mostra apenas módulos retornados pela API (filtragem por permissão já feita no backend)
   - Badge "Em manutenção" continua funcionando

4. **Remover acoplamento com ContaModulo:**
   - Buscar `ContaModulo` em todo o codebase com Grep e remover/substituir
   - Drop da tabela `ContaModulo` (já feito em Step 11, validar aqui)

**Critérios de aceitação:**
- [ ] `GET /api/v1/erp/modules/` retorna apenas módulos ativos da empresa atual (não da Conta)
- [ ] Trocar de empresa via `switch-empresa` muda os módulos exibidos na sidebar
- [ ] Empresa A com `erp.pessoas` ativo e Empresa B (mesma Conta) sem → user vê módulo só na A
- [ ] Cache invalida quando `EmpresaModulo.ativo` muda
- [ ] Nenhuma referência a `ContaModulo` no codebase (verificado via Grep)
- [ ] Cobertura ≥ 80%

**Dependências:** Steps 11, 12
**Agente responsável:** @grid-tester → @bolt-executor
**Complexidade:** MEDIUM

---

### Step 15 — Refatorar backoffice.account com nova arquitetura

**Objetivo:** Reescrever os endpoints e telas de `backoffice.account` para operar sobre `Empresa`, `EmpresaModulo`, `UserEmpresaVinculo`, `Perfil` em vez dos modelos antigos.

**O que fazer:**

1. **Backend — endpoints `/api/v1/account/`:**
   - `GET /api/v1/account/overview/` — totais: empresas, usuários (vinculos ativos), módulos contratados (soma de EmpresaModulo ativos), plano
   - **Empresas:**
     - `GET /api/v1/account/empresas/` — lista
     - `POST /api/v1/account/empresas/` — criar filial (valida tipo, empresa_pai obrigatória se filial)
     - `PATCH /api/v1/account/empresas/{id}/` — atualizar
     - `DELETE /api/v1/account/empresas/{id}/` — soft delete (proibido para matriz se for única empresa)
   - **Módulos por empresa:**
     - `GET /api/v1/account/empresas/{empresa_id}/modulos/` — lista todos os módulos do catálogo + status ativo para a empresa
     - `PATCH /api/v1/account/empresas/{empresa_id}/modulos/{code}/` — ativar/desativar
     - Ativação dispara Celery task: `bootstrap_modulo_for_empresa.delay(empresa_id, modulo_code)` (migrations no schema da Conta + seed inicial)
   - **Usuários (UserEmpresaVinculo):**
     - `GET /api/v1/account/usuarios/` — lista todos os vínculos da Conta (todas empresas)
     - `POST /api/v1/account/usuarios/invite/` — convida user para empresa específica com perfil; cria User se não existir + envia email
     - `PATCH /api/v1/account/usuarios/{vinculo_id}/` — atualizar perfil ou status
     - `DELETE /api/v1/account/usuarios/{vinculo_id}/` — revogar acesso (suspended)
   - **Perfis:**
     - `GET /api/v1/account/empresas/{empresa_id}/perfis/` — lista Perfis da empresa (no schema)
     - `POST /api/v1/account/empresas/{empresa_id}/perfis/` — criar (opcional: copiar de PapelTemplate)
     - `PATCH /api/v1/account/empresas/{empresa_id}/perfis/{id}/` — editar papéis
     - `GET /api/v1/account/papel-templates/` — catálogo público (read-only)

2. **Permissão:** todos os endpoints exigem `Membership.is_account_owner=True` na Conta ativa.

3. **Frontend — refatorar páginas existentes:**
   - `/backoffice/account/` Dashboard: novos cards (empresas, vinculos ativos, módulos contratados)
   - `/backoffice/account/empresas/` — agora é a página primária (não mais "Módulos")
   - `/backoffice/account/empresas/{id}/modulos/` — drill-in para gerenciar módulos da empresa
   - `/backoffice/account/empresas/{id}/perfis/` — drill-in para perfis daquela empresa
   - `/backoffice/account/usuarios/` — convite agora pede empresa + perfil

4. **Migrar UI antiga:** páginas atuais (Step 9 concluído com modelo antigo) precisam ser ajustadas — fluxo de Módulos sai do nível Conta e vai para drill-in dentro de Empresa.

**Critérios de aceitação:**
- [ ] Convite de usuário cria User (se não existir) + UserEmpresaVinculo(status=invited) + envia email com link
- [ ] Aceite do convite muda status para `active` e permite login
- [ ] Ativar módulo `erp.pessoas` na Empresa X dispara Celery task; `EmpresaModulo.ativo=True` quando task conclui
- [ ] Falha na task de bootstrap reverte para `EmpresaModulo.ativo=False` + mensagem de erro
- [ ] Owner cria Perfil "VENDEDOR" na Empresa X copiando de PapelTemplate, edita papéis, salva — Perfil persistido no schema da Conta
- [ ] Owner não pode deletar última empresa (matriz única) da Conta — 422
- [ ] Owner de Conta A não vê empresas/usuários da Conta B
- [ ] Cobertura ≥ 80% em services/selectors do `apps.platform.account`

**Dependências:** Steps 11, 12, 13, 14
**Agente responsável:** @grid-tester → @bolt-executor → @canvas-designer (ajustes de UI das páginas refatoradas)
**Complexidade:** HIGH

---

### Step 16 — backoffice.platform completo + impersonation

**Objetivo:** Implementar `backoffice.platform` (D22 do PRD) sobre a nova arquitetura, incluindo o fluxo de impersonation com audit log (D-R11).

**O que fazer:**

1. **Backend — endpoints `/api/v1/platform/`:**
   - **Contas:**
     - `GET /api/v1/platform/contas/` — lista
     - `POST /api/v1/platform/contas/` — wizard: cria Conta + Empresa matriz + owner User (se não existir) + Membership + UserEmpresaVinculo + Perfil OWNER em uma transação (chama `Conta.objects.criar_com_matriz`)
     - `PATCH /api/v1/platform/contas/{id}/` — ativar/desativar
   - **Catálogo de módulos:**
     - `GET /api/v1/platform/modulos/`
     - `POST /api/v1/platform/modulos/`
     - `PATCH /api/v1/platform/modulos/{code}/` — toggle `em_manutencao`
   - **Maintenance:**
     - Endpoints conforme requisitos §7.5 do PRD (já documentados)
   - **Usuários staff:**
     - `GET /api/v1/platform/usuarios/`
     - `PATCH /api/v1/platform/usuarios/{id}/` — promote/demote `is_platform_staff`
   - **Impersonation:**
     - `POST /api/v1/platform/impersonate {conta_id}` — emite JWT especial:
       ```json
       {
         "sub": staff_user_id,
         "ctx": {
           "conta_id": "...",
           "empresa_id": null,
           "impersonating": true,
           "impersonated_by_staff_id": staff_user_id,
           "stage": "select_empresa"
         },
         "is_platform_staff": true,
         "exp": now + 2h
       }
       ```
     - Logs entrada em `ImpersonationLog` (public)
     - Frontend ERP detecta `ctx.impersonating=true` no JWT e exibe banner amarelo "Modo suporte — ações auditadas como [nome staff]"
     - Toda ação CRUD em ERP, quando `ctx.impersonating=true`, escreve em `AuditLog` do schema da Conta com `actor="staff:{nome}"` + `before_state`/`after_state`

2. **Models:**
   - `ImpersonationLog(TimestampMixin)` em `apps.platform`:
     ```python
     staff_user = ForeignKey(User)
     conta = ForeignKey(Conta)
     empresa_id = UUIDField(null=True)
     action = CharField()  # CREATE/UPDATE/DELETE/READ
     resource_type = CharField()
     resource_id = UUIDField(null=True)
     before_state = JSONField(null=True)
     after_state = JSONField(null=True)
     ```
   - `AuditLog` no schema TENANT — já previsto no requisito §13.1; criar agora

3. **Frontend Platform:**
   - Wizard de criação de Conta: form em 3 steps (dados Conta → matriz → owner)
   - Lista de Contas com botão "Acessar como suporte" → chama `/impersonate` → abre nova aba para `erp.gocontrol.com.br` com token especial
   - Página de Audit log de impersonation

**Critérios de aceitação:**
- [ ] Wizard cria Conta + matriz + owner em transação atômica; falha em qualquer step reverte tudo
- [ ] Staff inicia impersonation → JWT especial expira em 2h, não renova
- [ ] No ERP em modo suporte, banner amarelo visível em todas as páginas
- [ ] Ação de Staff (criar pessoa, editar produto) registrada em `ImpersonationLog` (public) E `AuditLog` (schema) com actor `"staff:{nome}"`
- [ ] Maintenance global invalida tokens de todas as Contas via `INCR platform:token_version`
- [ ] Maintenance por módulo bloqueia o módulo em todas as empresas que o tenham contratado, sem invalidar tokens
- [ ] Cobertura ≥ 80%

**Dependências:** Steps 11, 12, 13, 15
**Agente responsável:** @grid-tester → @bolt-executor → @vault-security (audit do fluxo de impersonation antes de merge) → @canvas-designer (UI staff)
**Complexidade:** HIGH

---

### Step 17 — Bootstrap dos 3 frontends separados (estrutura mínima)

**Objetivo:** Separar fisicamente os 3 SPAs (ERP / Account / Platform Admin) com builds independentes, mas reutilizando código compartilhado. UX polish cross-portal fica para Ciclo 2.5.

**O que fazer:**

1. **Estrutura de diretórios:**
   ```
   /home/evonexus/evo-projects/go-control-erp/frontend/
     apps/
       erp/                ← bundle erp.gocontrol.com.br
         src/
         vite.config.ts
         package.json
       account/            ← bundle account.gocontrol.com.br
         src/
         vite.config.ts
         package.json
       admin/              ← bundle admin.gocontrol.com.br
         src/
         vite.config.ts
         package.json
     shared/               ← componentes/hooks/auth comuns
       src/
         components/       (StatusBadge, ConfirmDialog, Layout primitives)
         hooks/            (useAuth, useApiClient)
         api/              (client Axios + interceptors)
         types/
       package.json (workspace package)
   ```

2. **Decisão de monorepo:** usar **pnpm workspaces** (mais leve que turborepo neste estágio). Cada app importa de `@gocontrol/shared` via workspace symlink.

3. **Migração do código atual:**
   - Frontend monolítico atual vira `apps/erp/`
   - `apps/account/` e `apps/admin/` começam com Layout + LoginPage próprios consumindo `@gocontrol/shared`
   - LoginPage de cada portal valida o tipo de acesso correto (account checa `is_account_owner`, admin checa `is_platform_staff`)

4. **Roteamento Traefik / Nginx:**
   - `erp.myworkhome.com.br` → bundle `apps/erp/dist/`
   - `account.myworkhome.com.br` → bundle `apps/account/dist/`
   - `admin.myworkhome.com.br` → bundle `apps/admin/dist/`
   - Backend Django responde em hostname compartilhado (ex: `api.myworkhome.com.br`) — chamado pelos 3 SPAs via CORS configurado

5. **CORS:**
   - Backend whitelista `https://erp.myworkhome.com.br`, `https://account.myworkhome.com.br`, `https://admin.myworkhome.com.br`

6. **Login independente:**
   - Cada SPA faz `POST /api/v1/auth/login` próprio
   - JWT armazenado em localStorage isolado por origem (browser separa por hostname)
   - Sem SSO cross-portal — usuário com 2 papéis loga 2x

**Critérios de aceitação:**
- [ ] `pnpm -r build` gera 3 bundles independentes em `apps/{erp,account,admin}/dist/`
- [ ] `apps/erp/` mostra módulos ERP; recusa user que não tem `UserEmpresaVinculo`
- [ ] `apps/account/` recusa user sem `Membership.is_account_owner=True`
- [ ] `apps/admin/` recusa user sem `is_platform_staff=True`
- [ ] Componentes em `shared/` reutilizados pelos 3 (verificado via Vite bundle analyzer)
- [ ] CORS configurado para os 3 hostnames; chamadas funcionam
- [ ] Build de cada app deploy-ável independentemente

**Dependências:** Steps 12, 15, 16
**Agente responsável:** @canvas-designer (estrutura) → @bolt-executor → @custom-sysops (Traefik/CORS infra)
**Complexidade:** MEDIUM-HIGH

---

### Step 18 — Smoke test ponta-a-ponta + handoff Oath

**Objetivo:** Validar o ciclo completo num cenário real e fechar o ciclo com verificação evidence-based.

**O que fazer:**

1. **Roteiro de smoke test:**
   1. Platform Staff abre `admin.myworkhome.com.br`, loga
   2. Cria Conta "Auto Peças" com matriz (CNPJ válido) e owner Eduardo
   3. Eduardo recebe email, define senha, abre `account.myworkhome.com.br`, loga
   4. No Account: cria filial "Auto Peças Norte"; ativa módulo `erp.produtos` na matriz
   5. Convida usuário "Maria" como CAIXA na matriz
   6. Maria recebe email, abre `erp.myworkhome.com.br`, loga (1 conta + 1 empresa) → entra direto
   7. Maria vê apenas módulos da empresa-matriz; tenta acessar módulo de outra empresa → 403
   8. Eduardo cria 2ª Conta "Comércio XYZ", convida Maria como GERENTE
   9. Maria volta ao login, agora vê 2 Contas → escolhe → vê empresas → escolhe → JWT final
   10. Staff entra em `admin/`, clica "Acessar como suporte" na Conta "Auto Peças" → impersonation
   11. Staff cria uma pessoa em nome de Eduardo → log em `ImpersonationLog` + `AuditLog` com `actor="staff:..."`
   12. Backup: `pg_dump -n tenant_{cnpj_billing} go_control_db > backup.sql` funciona

2. **Suite de testes automatizada cross-tenant:**
   - User da Conta A com JWT válido → request a recurso da Conta B (ID forjado) → 403/404
   - JWT com `conta_id` adulterado (assinatura quebrada) → 401
   - Schema mismatch entre `connection.tenant.schema_name` e claim → 403
   - Concorrência: 2 requests simultâneas com tokens de Contas diferentes → cada uma vê só o seu schema

3. **Documentação:**
   - Atualizar `docs/agent-instructions.md` com nova arquitetura (JWT routing, EmpresaMirror, login 3-step)
   - Atualizar `coding-standards.md`: regra "FK lógica entre public.Empresa e EmpresaMirror"
   - Diagrama atualizado da arquitetura federada

4. **Handoff:**
   - @oath-verifier produz `[C]verification-ciclo2-redesign.md` com evidências (logs de teste, screenshots do smoke test, métricas de cobertura)
   - @mirror-retro avalia o ciclo (retro)
   - Tag `v0.2.0-ciclo2-redesign`

**Critérios de aceitação:**
- [ ] Smoke test executado por Eduardo sem bug bloqueante
- [ ] Suite cross-tenant: 100% verde
- [ ] Cobertura backend ≥ 80% nos apps refatorados
- [ ] Cobertura frontend ≥ 70% nos 3 bundles
- [ ] CI verde
- [ ] Documentação revisada
- [ ] @oath-verifier: PASS em todos os critérios

**Dependências:** Steps 11-17
**Agente responsável:** @bolt-executor + @oath-verifier + @mirror-retro
**Complexidade:** MEDIUM

---

## Resumo do impacto sobre Steps anteriores

| Step | Status anterior | Ação no Ciclo 2 redesign |
|---|---|---|
| Step 6 — Padronização de rotas | ✅ Concluído | **Mantido** — rotas continuam válidas |
| Step 7 — `/erp/modules/` | ✅ Concluído (sobre ContaModulo) | **Refeito** dentro do Step 14 (migra para EmpresaModulo) |
| Step 8 — Sidebar dinâmica | ✅ Concluído | **Ajuste mínimo** dentro do Step 14 (contrato JSON igual; backend muda) |
| Step 9 — backoffice.account | ✅ Concluído (sobre Membership/ContaModulo) | **Reescrito** no Step 15 (UserEmpresaVinculo + EmpresaModulo + Perfis) |
| Step 10 — backoffice.platform | 🔜 Pendente (planejado sobre arquitetura antiga) | **Substituído** pelo Step 16 (com impersonation + nova arquitetura) |

## Success Criteria

- [ ] Step 11: Modelos centrais refatorados, migrations limpas, testes verdes
- [ ] Step 12: JWTTenantMiddleware + login 3-step funcionais; suite isolamento cross-tenant verde
- [ ] Step 13: EmpresaMirror + sync atomico funcional
- [ ] Step 14: Sidebar e modules consumindo EmpresaModulo; ContaModulo eliminado do codebase
- [ ] Step 15: backoffice.account refatorado; convite + ativação módulo + Perfis funcionais
- [ ] Step 16: backoffice.platform completo; impersonation + audit log funcionais
- [ ] Step 17: 3 bundles SPA buildam e deployam independentemente
- [ ] Step 18: Smoke test passa; @oath-verifier PASS; tag v0.2.0
- [ ] ADR `[C]architecture-migracao-minierp-adianti-python-react.md` atualizado por @apex-architect com D-R01..D-R12 formalizados

## Open Questions

- [ ] **OQ-R1** — Sync `Empresa → EmpresaMirror` síncrono é robusto o suficiente, ou devemos partir para outbox pattern (tabela `empresa_outbox` + worker Celery)? — **Recomendação Compass:** começar síncrono (Step 13). Se em testes de carga aparecer flakiness, migrar para outbox em ticket separado. Decisão arquitetural delegada a @apex-architect no ADR.
- [ ] **OQ-R2** — JWT tem `permissions` resolvidos na emissão (snapshot). Se Owner mudar Perfil de um vinculado, mudança só vale após próximo login/refresh. Aceitável? — **Recomendação:** sim, com refresh forçado via `INCR user:{id}:token_version` quando Perfil muda. Implementar em Step 15.
- [ ] **OQ-R3** — Domain model do django-tenants pode ser removido completamente, ou manter por hygiene/compatibilidade com comandos django-tenants? — **Recomendação:** remover em Step 12, junto com `TenantMainMiddleware`. Comandos `migrate_schemas`, `tenant_command` continuam funcionando sem `Domain`.
- [ ] **OQ-R4** — Monorepo dos frontends: pnpm workspaces vs turborepo vs nx? — **Recomendação:** pnpm workspaces (mais simples). Re-avaliar em Ciclo 2.5 se houver dor real.
- [ ] **OQ-R5** — Maintenance por módulo: `Modulo.em_manutencao` é global ou `EmpresaModulo.em_manutencao` é por empresa? Ambos? — **Recomendação:** ambos (já está nos modelos). Lógica do middleware: `bloqueado = Modulo.em_manutencao OR EmpresaModulo.em_manutencao`. Documentar em Step 16.

Estas OQs serão consolidadas em `workspace/development/plans/[C]open-questions.md`.

## Handoff

- **Pré-requisito imediato → @apex-architect:** atualizar ADR `[C]architecture-migracao-minierp-adianti-python-react.md` formalizando D-R01..D-R12 (substituindo D8-D12 originais). Sem o ADR atualizado, Step 11 não inicia.
- **Próximo passo após ADR → @grid-tester + @bolt-executor:** iniciar Step 11 (refactor models). Grid escreve testes de model + transação atômica + isolamento; Bolt implementa.
- **Sequência:** 11 → 12 → 13 → 14 → 15 → 16 → 17 → 18
- **Após Step 18 → @oath-verifier + @mirror-retro:** verificação evidence-based + retrospectiva do ciclo
- **Decisões aprovadas:** [./[C]decisions-redesign-identidade-tenancy.md](./[C]decisions-redesign-identidade-tenancy.md)
- **Requisitos:** [./[C]requisitos-go-control-erp.md](./[C]requisitos-go-control-erp.md)
- **Plano original (histórico):** [./[C]plan-migracao-minierp-adianti-python-react.md](./[C]plan-migracao-minierp-adianti-python-react.md)
