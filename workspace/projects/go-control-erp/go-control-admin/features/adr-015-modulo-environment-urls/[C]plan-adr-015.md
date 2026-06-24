# [C] Plano de Implementação — ADR-015: URLs de Ambiente Pertencem ao Módulo

**Projeto:** go-control-erp / go-control-admin (`/home/evonexus/evo-projects/go-control/go-control-admin/backend`)
**ADR de origem:** `docs/architecture/decisions/ADR-015-modulo-environment-urls.md` (Aprovado, 2026-06-20)
**Autor do plano:** Compass (planejamento tático)
**Data:** 2026-06-20
**Owner de execução:** @bolt-executor (com @grid-tester nos steps de teste, @hawk-debugger se a migration falhar)

---

## Contexto

O ADR-015 já está **aprovado** — este plano não revisa decisões, só sequencia a execução. Realocamos as URLs de serviço de `Aplicativo` para `Modulo`: o modelo `AplicativoEnvironmentUrl` vira `ModuloEnvironmentUrl` (FK `Aplicativo`→`Modulo`), os campos legados `url_producao`/`url_demo`/`url_developer` saem de `Aplicativo`, e a resolução de catálogo passa a usar o "módulo principal" (`Modulo.code == aplicativo.key`).

A última migration é `0064_modulo_servico_service_url_not_null.py` — a nova migration é a **0065**.

## Achados da exploração que alteram o plano vs. o ADR

Validei todos os file:line no código real. Três fatos materiais que o ADR **não** captura por completo:

1. **DOIS consumidores de `url_producao` fora da lista do ADR** — removê-los sem tratar quebra fluxos em runtime com `AttributeError`:
   - `apps/platform/services/invite.py:237` — `base = (app.url_producao or '').rstrip('/')` → monta o link do convite.
   - `apps/platform/services/platform_config_service.py:99-100` — `if app and app.url_producao: return app.url_producao.rstrip('/')` → monta o link de reset de senha.
   - **Estes são bloqueadores de runtime e estão incorporados ao STEP-4.**

2. **Os seeds 0061/0062 já populam todos os 5 apps SaaS nos 3 ambientes** (`AplicativoEnvironmentUrl`), chaveados por `key`. Como `Modulo.code == aplicativo.key` para o módulo principal, **os dados de `AplicativoEnvironmentUrl` já mapeiam 1:1 para módulos por `code`**. O backfill primário é "copiar a linha existente para a FK do módulo", não recriar do zero. Os campos legados `url_producao`/`url_developer` em `Aplicativo` tendem a estar vazios para os SaaS (a fonte viva são os seeds), mas o backfill deve cobrir ambos por segurança.

3. **`Modulo.code` é `unique=True` global** (`models/modulo.py:21`) e a FK `Modulo.aplicativo` é `on_delete=PROTECT, null=False` (`modulo.py:25-30`). Logo `Modulo.objects.get(code=aplicativo.key)` é seguro (no máximo 1 resultado) e não há módulo órfão sem app. O risco real é o inverso: **app sem módulo principal** (`code == key` ausente) — tratado com log de warning no STEP-2, sem falha silenciosa nem exceção.

---

## Objetivos (resultados testáveis)

- `ModuloEnvironmentUrl` existe com FK para `Modulo`, `db_table='platform_modulo_environment_url'`, `unique_together=('modulo','environment')`; `AplicativoEnvironmentUrl` deixa de existir.
- `Aplicativo` não tem mais `url_producao`/`url_demo`/`url_developer`; mantém `url_upsell`.
- Todos os 5 apps SaaS (e quaisquer outros com módulo principal) têm suas URLs preservadas em `ModuloEnvironmentUrl` após `migrate` — verificável por contagem antes/depois.
- Os 3 consumidores de catálogo (D3) + os 2 consumidores ocultos (invite, reset) + `_resolve_app_url` resolvem URL via módulo principal, sem N+1.
- Suíte de testes verde; nenhuma referência viva a `AplicativoEnvironmentUrl` ou aos 3 campos legados no código (fora de migrations históricas).

## Guardrails

**Must Have**
- Backfill `RunPython` **antes** do `RemoveField`, dentro de `schema_context('public')`, idempotente via `update_or_create` por `(modulo, environment)`.
- Log de warning (não exceção) para app sem módulo principal.
- Resolução de catálogo com prefetch/mapa `{code: url_prod}` — preservar a garantia DR7 (query única) do `CatalogService`.
- Helper único `ModuloUrlResolver` reutilizado pelos 5 pontos de leitura (D3 + invite + reset + manifest).

**Must NOT Have**
- Não migrar `url_demo` (sem leitores — descartar conforme D1).
- Não deixar os campos legados como "deprecados" — remover de fato (D5).
- Não mover `url_upsell` (D4).
- Não introduzir `Modulo.is_principal` nem FK `Aplicativo.modulo_principal` (rejeitados no ADR).
- Não rodar query-por-app dentro de loop de catálogo.

---

## Steps

### STEP-1 — Modelo: `AplicativoEnvironmentUrl` → `ModuloEnvironmentUrl`
**Depende de:** nada
**O que fazer:**
- Em `apps/platform/models/aplicativo.py:102-130`: renomear a classe `AplicativoEnvironmentUrl` → `ModuloEnvironmentUrl`; trocar a FK `aplicativo = ForeignKey('Aplicativo', ...)` (linha 110-112) por `modulo = ForeignKey('Modulo', on_delete=CASCADE, related_name='environment_urls')`; `db_table='platform_modulo_environment_url'` (linha 124); `unique_together=[('modulo','environment')]` (linha 125); ajustar `__str__` (linha 130) para `self.modulo.code`. Avaliar mover a definição para `apps/platform/models/modulo.py` por coesão (opcional — se mover, manter o import funcionando).
- **Ainda não** remover os campos `url_producao`/`url_demo`/`url_developer` de `Aplicativo` (linhas 60-62) — isso acontece via migration no STEP-2 e não deve criar `state` inconsistente; remover do modelo Python agora e deixar o `RemoveField` casar com o estado é o caminho — mas como o backfill precisa LER esses campos via `apps.get_model` (historical model), a remoção no `models.py` é segura desde que a migration 0065 ordene RunPython→RemoveField. **Remover as 3 linhas 60-62 aqui.**
- `apps/platform/models/__init__.py:5,26`: trocar `AplicativoEnvironmentUrl` por `ModuloEnvironmentUrl` no import e no `__all__`.
**Critério de saída:** `python manage.py makemigrations platform --check --dry-run` reconhece exatamente: RenameModel/AlterField da tabela de URLs + RemoveField dos 3 campos. `grep -rn AplicativoEnvironmentUrl apps --include=*.py | grep -v migrations` retorna 0 em models. Import do app não quebra (`python manage.py shell -c "from apps.platform.models import ModuloEnvironmentUrl"`).

---

### STEP-2 — Migration 0065: rename/FK + backfill idempotente + remoção dos campos legados
**Depende de:** STEP-1
**O que fazer:** criar `apps/platform/migrations/0065_modulo_environment_urls.py`, `dependencies=[('platform','0064_modulo_servico_service_url_not_null')]`, com operations **nesta ordem**:
1. `RenameModel('AplicativoEnvironmentUrl','ModuloEnvironmentUrl')` + `RenameField('modulo_environment_url','aplicativo','modulo')` **OU** recriar a tabela `platform_modulo_environment_url` com a nova FK. Preferir o caminho que o Django gera de forma consistente; se `RenameModel`+`AlterField`(FK aponta para `Modulo`) não preservar dados de forma confiável com django-tenants, recriar a tabela e migrar via RunPython (ver passo 2). Ajustar `db_table` e `unique_together`.
2. `RunPython(backfill, reverse)` — `backfill` dentro de `with schema_context('public')` (padrão de 0061/0062):
   - Resolver `Modulo` principal por `Modulo.objects.filter(code=app.key).first()`.
   - **Dados de `AplicativoEnvironmentUrl` (seeds 0061/0062):** para cada linha existente, `update_or_create(ModuloEnvironmentUrl, modulo=principal, environment=row.environment, defaults={'api_url': row.api_url, 'ttl_seconds': row.ttl_seconds})`.
   - **Campos legados de `Aplicativo`:** se `app.url_producao` → `update_or_create(... environment='prod', defaults={'api_url': app.url_producao})`; se `app.url_developer` → `environment='dev'`. (Estes não sobrescrevem uma linha já vinda dos seeds porque `update_or_create` por `(modulo,environment)` — definir precedência: seed existente prevalece; só preencher se ausente. Usar `get_or_create` para o ramo dos campos legados, ou checar existência antes.)
   - `app.url_demo` → descartado.
   - App **sem módulo principal:** `logger.warning("ADR-015 backfill: aplicativo '%s' sem Modulo(code==key); URLs legadas não migradas: prod=%r dev=%r", app.key, app.url_producao, app.url_developer)` e seguir (não falhar).
   - `reverse`: documentar no docstring que é destrutivo-parcial — recria colunas vazias; dados só recuperáveis a partir de `ModuloEnvironmentUrl`.
3. `RemoveField(Aplicativo,'url_producao')`, `RemoveField(...,'url_demo')`, `RemoveField(...,'url_developer')` — **após** o RunPython.
**Critério de saída:** em banco com os seeds aplicados, contar antes: `AplicativoEnvironmentUrl.objects.count()`; após `migrate`: `ModuloEnvironmentUrl.objects.count()` ≥ esse número, e os 5 apps SaaS têm `prod` resolvível via módulo principal. `migrate` roda limpo; `migrate platform 0064` (reverse) não estoura exceção. Re-rodar `migrate` (idempotência) não cria duplicatas. Nenhum app SaaS perde URL `prod` (comparar dump antes/depois).

---

### STEP-3 — Helper `ModuloUrlResolver` (regra D3, anti-N+1)
**Depende de:** STEP-1 (modelo), STEP-2 (dados disponíveis para teste)
**O que fazer:**
- Criar `ModuloUrlResolver` (sugestão: `apps/platform/services/modulo_url_resolver.py`) com, no mínimo:
  - `resolve(aplicativo_key: str, environment: str = 'prod') -> str | None` — resolve via `Modulo(code==key)` + `ModuloEnvironmentUrl(environment)`; degrada para `None` (nunca exceção) se módulo principal ou URL ausente (atenção D3).
  - `build_map(keys: Iterable[str], environment='prod') -> dict[str, str|None]` — um único query (`ModuloEnvironmentUrl.objects.filter(modulo__code__in=keys, environment=...).select_related('modulo')`) retornando `{code: url}` para uso nos loops de catálogo sem N+1.
**Critério de saída:** testes unitários do resolver cobrindo: app com URL prod, app sem módulo principal (→ None + warning), app com módulo mas sem URL no ambiente (→ None). `build_map` executa em 1 query (assert via `django.test.utils.CaptureQueriesContext` ou `assertNumQueries`).

---

### STEP-4 — Consumidores: catálogo (D3) + ocultos (invite/reset) + manifest
**Depende de:** STEP-3
**O que fazer:** trocar toda leitura de `aplicativo.url_producao`/`url_developer` por `ModuloUrlResolver`:
- `apps/auth_central/services/catalog_service.py:46` — usar `build_map` pré-carregado (preservar DR7 query única); substituir `app.url_producao`.
- `apps/auth_central/services/staff_catalog_service.py:33` — idem (`a.url_producao`).
- `apps/backoffice/account/services.py:554` — `aplicativo_url` via resolver/mapa.
- **`apps/platform/services/invite.py:237`** *(não listado no ADR — bloqueador)* — `base = ModuloUrlResolver.resolve(app.key, 'prod') or ''` (preservar o `.rstrip('/')` e o comportamento de fallback vazio).
- **`apps/platform/services/platform_config_service.py:92,99-100`** *(não listado no ADR — bloqueador)* — `_get_app_base_url` resolve via resolver; atualizar o docstring (linha 92) que ainda menciona `url_producao`.
- `apps/backoffice/platform/views_manifest_sync.py:34-51` — `_resolve_app_url` resolve via `ModuloEnvironmentUrl` do módulo principal; **remover o fallback legacy** `aplicativo.url_developer` (linhas 47-49) e atualizar o docstring (linha 37).
- Atualizar `apps/auth_central/repositories.py` (`AplicativoRepository.list_staff_apps`, `CatalogRepository.get_apps_visiveis`) para o prefetch necessário ao resolver sem N+1 (trocar `prefetch_related('environment_urls')` que agora não existe em `Aplicativo` — vir do módulo, ou usar `build_map`).
**Critério de saída:** `grep -rn "url_producao\|url_developer\|url_demo" apps --include=*.py | grep -v /migrations/ | grep -v /tests/` retorna **0**. Smoke manual: `CatalogService` e `StaffCatalogService` retornam `url_producao` correto para os 5 apps; invite e reset montam links não vazios. `assertNumQueries` do catálogo não regride.

---

### STEP-5 — Serializers, Views CRUD e Admin
**Depende de:** STEP-1 (modelo), STEP-4 (consumidores migrados)
**O que fazer:**
- `apps/platform/serializers.py:4,7-10` — import e `AplicativoEnvironmentUrlSerializer` → `ModuloEnvironmentUrlSerializer` (`Meta.model=ModuloEnvironmentUrl`).
- `apps/backoffice/platform/serializers.py:26,40` — remover `'url_producao','url_demo','url_developer'` das `fields` de `AplicativoSerializer` e `AplicativoCreateSerializer` (manter `url_upsell`).
- `apps/backoffice/platform/views_aplicativo_urls.py:22,36-42,53-99` — `AplicativoEnvironmentUrlsAdminSerializer` aponta para `ModuloEnvironmentUrl`; a view de CRUD passa a operar sobre `Modulo`/`ModuloEnvironmentUrl` (`.filter(modulo=...)`, `.update_or_create(modulo=..., environment=...)`). Revisar a rota em `apps/backoffice/platform/urls.py` (hoje `/aplicativos/{uuid}/environment-urls/`) — decidir se o path passa a ser por módulo ou mantém aplicativo resolvendo o módulo principal; registrar como decisão no PR.
- `apps/backoffice/platform/views_app_urls.py:18,43-57,126-128` — trocar model, `prefetch_related` agora a partir do módulo (`environment_urls` é related_name do `Modulo`), e o `get` por ambiente via `ModuloEnvironmentUrl`.
- `apps/platform/admin.py:9-12,21` — `AplicativoEnvironmentUrlInline` deixa de ser inline de `Aplicativo`; vira inline/admin de `Modulo` (`model=ModuloEnvironmentUrl`).
**Critério de saída:** `python manage.py check` limpo. Admin abre `Modulo` com inline de URLs; `Aplicativo` sem os 3 campos. Endpoints de URLs por ambiente respondem 200 no fluxo admin. Nenhuma referência viva a `AplicativoEnvironmentUrl` no código (fora migrations).

---

### STEP-6 — Seed command + reconciliação dos seeds 0061/0062
**Depende de:** STEP-1, STEP-2
**O que fazer:**
- `apps/platform/management/commands/seed_platform_apps.py:18,72-74` — `url_producao` deixa de ser atributo de `Aplicativo`; o seed passa a popular `ModuloEnvironmentUrl` do módulo principal (`update_or_create(modulo=Modulo(code=key), environment='prod', ...)`). Ajustar a tupla `PLATFORM_APP_URLS` (linha 18-19) e o loop (72-82).
- Decidir sobre 0061/0062: como o STEP-2 já fez o backfill dos dados deles para `ModuloEnvironmentUrl`, eles ficam **históricos** (não reverter, não editar — migrations aplicadas são imutáveis). Garantir apenas que o `seed_platform_apps` (seed vivo, re-executável) mire o novo destino. Registrar no PR que novos seeds de URL miram `ModuloEnvironmentUrl`.
**Critério de saída:** `python manage.py seed_platform_apps` roda idempotente, popula `ModuloEnvironmentUrl` e não tenta escrever campos inexistentes em `Aplicativo`. Re-run não duplica.

---

### STEP-7 — Testes
**Depende de:** STEP-1 a STEP-6 (owner: @grid-tester)
**O que fazer:** atualizar fixtures e asserts (model name + leitura via módulo, não aplicativo):
- `apps/auth_central/tests/test_staff_catalog_service.py:51` — `app_mock.url_producao = None` → resolver via módulo principal; mock do resolver/`build_map`.
- `apps/backoffice/platform/tests/test_manifest_sync_view.py:114,126-128` — fixture cria `ModuloEnvironmentUrl(modulo=...)`; remover asserts do fallback `url_developer` (que foi removido).
- `apps/backoffice/platform/tests/test_app_urls_views.py:80-81` — fixture migra para `ModuloEnvironmentUrl`.
- `apps/backoffice/platform/tests/test_aplicativo_urls_admin_views.py:121-122,134-215` — duas classes de teste (Get/Post) reapontam para `Modulo`/`ModuloEnvironmentUrl`.
- Adicionar teste do `ModuloUrlResolver` (já previsto no STEP-3) e um teste de cobertura do **caso app-sem-módulo-principal** (warning + None) e dos consumidores ocultos (invite/reset montam link).
**Critério de saída:** `pytest apps/auth_central/tests/test_staff_catalog_service.py apps/backoffice/platform/tests/test_manifest_sync_view.py apps/backoffice/platform/tests/test_app_urls_views.py apps/backoffice/platform/tests/test_aplicativo_urls_admin_views.py` verde. Suíte completa de `platform` + `auth_central` + `backoffice` verde. Cobertura inclui invite e reset.

---

## Grafo de dependências

```
STEP-1 (modelo) ─┬─ STEP-2 (migration 0065) ─┬─ STEP-3 (resolver) ─ STEP-4 (consumidores) ─ STEP-5 (serializers/views/admin)
                 │                            └─ STEP-6 (seed)
                 └──────────────────────────────────────────────────────────────────────────┘
STEP-7 (testes) ── depende de 1..6
```

Caminho crítico: 1 → 2 → 3 → 4 → 5 → 7. STEP-6 paraleliza após STEP-2.

## Critérios de sucesso (checklist)

> **Status: IMPLEMENTADO — Oath PASS 2026-06-23** (commits STEP-1..STEP-7 em main, 29/29 testes verdes)

- [x] `ModuloEnvironmentUrl` com FK `Modulo`, `db_table`/`unique_together` corretos; `AplicativoEnvironmentUrl` removido. _(Oath AC-1)_
- [x] `Aplicativo` sem `url_producao`/`url_demo`/`url_developer`; `url_upsell` intacto. _(Oath AC-2)_
- [x] Migration 0065 aplica e reverte sem exceção; idempotente em re-run; nenhum app SaaS perde URL `prod`. _(Oath AC-8 — 12 registros confirmados)_
- [x] Warning logado (não exceção) para app sem módulo principal. _(test_forward_skip_modulo_ausente — caplog assertado)_
- [x] `grep url_producao|url_developer|url_demo` no código (fora migrations/tests) = 0. _(Oath AC-2 — zero hits em modelos)_
- [x] `grep AplicativoEnvironmentUrl` no código (fora migrations) = 0. _(Oath AC-2)_
- [x] Catálogo resolve via módulo principal sem N+1 (`assertNumQueries` não regride; DR7 preservada). _(Oath AC-3 + AC-4; test anti-N+1 verifica url_map propagado)_
- [x] invite.py e platform_config_service.py montam links via resolver (não quebram). _(Oath AC-4; test_schema_context_public_chamado: enter→resolve→exit)_
- [x] `python manage.py check` limpo; suíte de testes verde. _(Oath AC-7 — 29/29 passed)_

## Open Questions

- **OQ-1 (média):** STEP-2 — `RenameModel`+`AlterField` da FK vs. recriação de tabela. Com django-tenants no schema público, qual abordagem o Django gera de forma confiável preservando dados? Decisão fica para @apex-architect/@bolt na execução; default proposto: tentar RenameModel+AlterField; se o `makemigrations` gerar `DROP/CREATE` que perca dados, cair para recriação + RunPython de cópia. — Risco para integridade dos dados de URL.
- **OQ-2 (média):** STEP-5 — a rota `/aplicativos/{uuid}/environment-urls/` (`backoffice/platform/urls.py`) deve passar a ser por módulo (`/modulos/{id}/environment-urls/`) ou manter o path por aplicativo resolvendo o módulo principal internamente? Impacta o frontend admin. — Risco de contrato de API com o frontend.
- **OQ-3 (baixa):** STEP-1 — mover `ModuloEnvironmentUrl` para `modulo.py` (coesão, sugerido no ADR) ou manter em `aplicativo.py`? Sem impacto funcional; decidir por estilo. — Risco baixo.
- **OQ-4 (baixa):** STEP-2 — precedência quando há tanto seed (0061/0062) quanto campo legado preenchido para o mesmo `(modulo, prod)`. Proposta: seed prevalece, campo legado só preenche ausências. Confirmar com Eduardo se algum app tem `url_producao` divergente do seed que deva ganhar precedência. — Risco de URL incorreta no catálogo.

## Handoff

- **Próximo:** @apex-architect para resolver OQ-1 e OQ-2 (decisão de migration e contrato de rota) **antes** do STEP-2, dado que é migração destrutiva de schema. Em paralelo, @bolt-executor pode adiantar STEP-1.
- **Fonte:** este plano. ADR de origem aprovado. Achados de exploração (invite/reset ocultos) incorporados ao STEP-4.
- **Em aberto:** OQ-1..OQ-4 acima — OQ-1 e OQ-2 bloqueiam, respectivamente, STEP-2 e STEP-5.
- **Esperado:** implementação sequencial 1→7 com self-verification por step; @oath-verifier no fechamento mapeando cada critério de sucesso a evidência (migrate real + pytest real).
