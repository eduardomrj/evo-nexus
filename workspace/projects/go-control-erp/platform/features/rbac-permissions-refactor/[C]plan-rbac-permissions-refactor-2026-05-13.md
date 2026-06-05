# Plano: Refactoring RBAC Permissions — GO Control ERP
**Data:** 2026-05-13  
**Status:** Aguardando aprovação

---

## Contexto

O audit identificou que a arquitetura de permissões saiu do trilho em 3 pontos: bugs ativos, o guard não está plugado em nada e há uma camada de snapshot desnecessária. Este plano corrige tudo isso em 4 fases ordenadas da menor para a maior mudança.

---

## O que está CERTO (não mexer)

- `PapelEmpresa` + `UserAplicativoEmpresa` — modelagem correta
- `Licenca` + `LicencaOverride` + `Plano` — fonte de verdade viva, funciona
- `empresa_tem_modulo()` + `empresa_tem_recurso()` em `licencas/services.py` — funções corretas, usam dados vivos
- `match_permission()` com wildcards — correto
- Seed automático dos 4 papéis (owner/manager/operator/readonly) — funciona

---

## O que está ERRADO (corrigir)

### 🔴 Bug 1: `updatePapel` usa PUT (vai dar 405 em runtime)
`frontend/apps/platform/src/services/permissoes.ts:97`  
Backend só tem `patch()` no `PapelEmpresaDetailView`. Fix: `api.put` → `api.patch`.

### 🔴 Bug 2: `createPapelFromTemplate` URL errada (vai dar 404 em runtime)
`frontend/apps/platform/src/services/permissoes.ts:121`  
Frontend envia para `/papeis-empresa/${template_id}/from-template/`  
Backend registrou a URL como `/papeis-empresa/from-template/` (ID no body, não na URL)  
Fix: remover `template_id` da URL e incluir no body.

### 🔴 Bug 3: `EmpresaPapeisListView` ignora `?aplicativo_id=`
`backend/apps/backoffice/platform/views.py:1299`  
Frontend manda `?aplicativo_id=X` mas a query não filtra.  
Fix: adicionar `request.query_params.get('aplicativo_id')` ao queryset.

### 🔴 Bug 4: `HasLicensedPermission` etapas 2+3 são genéricas
`backend/apps/platform/permissions.py:112-127`  
Verifica "existe algum snapshot no banco" em vez de "este módulo/recurso específico está disponível".  
Fix: parse do `perm_code` e usar `empresa_tem_recurso()` que já existe.

### 🔴 Bug 5: `HasLicensedPermission` não está plugado em nenhuma view de produção
Papéis são editáveis mas não bloqueiam acesso a nada. Fix: plugar em pelo menos 1 endpoint piloto.

---

## O que está DESNECESSÁRIO (remover)

### 🟡 `LicencaModuloSnapshot` + `LicencaRecursoSnapshot` + `LicencaSnapshotService`
- Duplicam `PlanoModulo` + `LicencaOverride` sem benefício real
- Criam drift: snapshot criado em D0 não reflete mudanças no plano em D+30
- As funções `empresa_tem_modulo()` e `empresa_tem_recurso()` já fazem o mesmo de forma dinâmica e correta
- `LicencaAcessoView` pode ser reescrita com dados vivos em 10 linhas

---

## Fases do refactoring

### Fase 1 — Bugs pontuais (frontend + backend, sem migration) ~30min

1. `permissoes.ts:97` → `api.patch` em vez de `api.put`
2. `permissoes.ts:121` → URL corrigida para `/papeis-empresa/from-template/`; `template_id` no body
3. `views.py:1299` → adicionar filtro por `aplicativo_id` ao queryset de `EmpresaPapeisListView`
4. Mesmo filtro em `EmpresaUsuariosAplicativoListView` (já tem `aplicativo_id` no query param mas verificar)

### Fase 2 — Corrigir o guard (backend, sem migration) ~45min

5. Reescrever etapas 2+3 do `HasLicensedPermission`:
   - Parse `perm_code = "modulo.recurso.acao"`
   - Se wildcard `*.*.*`: pular verificação (qualquer módulo ok)
   - Se tem módulo real: `empresa_tem_recurso(empresa_id, modulo_code, recurso_code)`
   - Remover imports de `LicencaModuloSnapshot` + `LicencaRecursoSnapshot`
6. Atualizar `test_permissions.py`: remover mocks de snapshot, usar `empresa_tem_recurso()` real
7. Plugar `licensed_perm("*.*.*")` em pelo menos 1 view de teste (ex: `LicencaAcessoView`)

### Fase 3 — Remover snapshots (backend, COM migration) ~1h

8. Deletar `LicencaSnapshotService` de `licencas/services.py`
9. Remover `LicencaModuloSnapshot` + `LicencaRecursoSnapshot` de `licencas/models.py`
10. Reescrever `LicencaAcessoView` para usar dados vivos (`PlanoModulo` + `LicencaOverride`)
11. Remover chamada `LicencaSnapshotService.criar(lic, plano)` do fluxo de criação de licença
12. Criar migration `0022_remove_snapshot_tables`
13. Deletar `backfill_licenca_snapshot.py` + `test_step_snapshot.py`

### Fase 4 — Nova tela "Permissões da Licença" ~2h

14. Backend: endpoint `GET /api/platform/licencas/:id/acesso-completo/` retornando:
    ```json
    {
      "licenca": { "id", "empresa_nome", "aplicativo_nome", "plano_nome", "status", "data_fim" },
      "modulos": [ { "code", "nome", "recursos": [...] } ],
      "papeis": [ { "id", "code", "nome", "permissions": [...] } ],
      "usuarios": [ { "id", "nome", "email", "papel": {...}, "status" } ]
    }
    ```
15. Frontend: nova página `/licencas/:licencaId/permissoes`
    - Header com info da licença
    - Tab "O que está contratado" → módulos/recursos do plano+override
    - Tab "Papéis" → reusa componente existente de papéis
    - Tab "Usuários" → reusa componente existente de usuários

---

## Dependências entre fases

```
Fase 1 → independente (bugs pontuais, pode ir agora)
Fase 2 → depende de Fase 1 (guard precisa funcionar sem snapshot)
Fase 3 → depende de Fase 2 (remover snapshot só depois do guard não depender mais dele)
Fase 4 → depende de Fase 3 (tela usa dados vivos, não snapshot)
```

---

## Risco

**Baixo** — as fases 1-3 são internals/backend sem impacto visível no frontend existente.  
**Zero migration rollback risk** — snapshot tables estão vazias de fato se `backfill_licenca_snapshot` nunca foi rodado em produção.

---

## Decisão necessária antes de executar Fase 3

Confirmar: **o `backfill_licenca_snapshot` foi rodado em produção alguma vez?**  
Se não: as tabelas estão vazias e a migration de remoção é sem risco.  
Se sim: verificar se alguma view depende dos dados antes de remover.
