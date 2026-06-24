# Open Questions — ADR-015 Modulo Environment URLs

> **Status: TODAS RESOLVIDAS — 2026-06-23**

## ADR-015 Plano de Implementação — 2026-06-20

- [x] **OQ-1:** Migration 0065 — RenameModel+AlterField(FK) vs. recriação de tabela sob django-tenants — Garantir preservação dos dados de URL no schema público; bloqueia STEP-2 — Risco: média
  **Decisão:** recriação de tabela via `CreateModel` + `RunPython` (backfill de `AplicativoEnvironmentUrl` → `ModuloEnvironmentUrl`) + `DeleteModel`. Evitou ambiguidade do `RenameModel`+`AlterField` com django-tenants no schema público. Migration 0065 aplicada e verificada com 12 registros preservados.

- [x] **OQ-2:** Rota `/aplicativos/{uuid}/environment-urls/` passa a ser por módulo ou mantém por aplicativo resolvendo o principal — Contrato de API com o frontend admin; bloqueia STEP-5 — Risco: média
  **Decisão:** mantida por aplicativo (`/aplicativos/{uuid}/environment-urls/`), resolvendo internamente o módulo principal via `Modulo.objects.get(code=app.key)`. Sem breaking change no contrato de API do frontend admin. Implementado em `views_aplicativo_urls.py`.

- [x] **OQ-3:** Mover `ModuloEnvironmentUrl` para `modulo.py` (coesão) ou manter em `aplicativo.py` — Estilo, sem impacto funcional — Risco: baixa
  **Decisão:** movido para `apps/platform/models/modulo.py` (linha 307) por coesão — o modelo tem FK para `Modulo`, faz sentido conviver com ele.

- [x] **OQ-4:** Precedência seed (0061/0062) vs. campo legado `url_producao` preenchido para o mesmo `(modulo, prod)` — Proposta: seed prevalece; confirmar com Eduardo se algum app tem URL divergente — Risco: baixa
  **Decisão:** seed prevalece. O backfill usou `update_or_create` pelos seeds existentes primeiro; campos legados de `Aplicativo` só preenchiam ausências. Na prática, os campos legados estavam vazios para todos os apps SaaS (a fonte viva eram os seeds 0061/0062). Sem divergência detectada.
