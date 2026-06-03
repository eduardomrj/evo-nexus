# GO Control ERP — Architecture Standards (ADR-001)

Applies to every agent (Bolt, Canvas, Compass, Apex, etc.) that touches the GO Control ERP project at `/home/evonexus/evo-projects/go-control-erp/`.

## Document de referência obrigatório

Before writing any backend or frontend code, read:

```
/home/evonexus/evo-projects/go-control-erp/docs/ADR-001-architecture-standards.md
```

## Backend — layer contract

```
views.py  →  services.py  →  repositories.py  →  models.py
                                                ↓
                                        serializers.py
                                        exceptions.py
```

| Layer | Responsability | Forbidden |
|---|---|---|
| `views.py` | HTTP in/out only — validate serializer, call service, return response | Business logic, ORM queries, if/else domain rules |
| `services.py` | Orchestration — domain rules, cascades, side effects | Direct ORM access; import other service unless explicitly composing |
| `repositories.py` | All ORM queries — one class per model | Business rules, HTTP concerns |
| `exceptions.py` | Domain-specific exceptions per app | Generic `ValueError`, `Exception` |

**Hard limits:** file ≤ 300 lines, method ≤ 30 lines.

## Frontend — feature folder contract

```
src/features/{domínio}/
  api.ts          ← all axios/fetch calls
  hooks.ts        ← useQuery / useMutation wrappers
  types.ts        ← TypeScript types for this domain
  components/     ← UI components
```

**Forbidden:** API call (`axios`, `fetch`) directly inside a React component. Must be in `features/*/api.ts`.

## SOLID quick reference

| Principle | What it means in practice |
|---|---|
| SRP | One reason to change — view handles HTTP, service handles domain |
| OCP | Add via new service/strategy, not by modifying existing views |
| LSP | Subtypes (serializers, services) must honour parent contracts |
| ISP | Small, focused interfaces — `LicencaRepository` ≠ `EmpresaRepository` |
| DIP | Views depend on service interface, not concrete class |

## GoF patterns in use

| Pattern | Where |
|---|---|
| Repository | `repositories.py` — isolates ORM from business logic |
| Strategy | Payment providers, status transitions |
| Factory | Object creation in services (e.g. `UserLicenca` cascade) |
| Observer | Post-save signals for cross-domain side effects |
| Template Method | Base views with hook methods |

## PR rejection criteria

Any PR that introduces:
- Business logic in `views.py`
- ORM query outside `repositories.py`
- Method > 30 lines in a view or service
- File > 300 lines
- `raise ValueError(...)` or `raise Exception(...)` for domain errors
- `axios`/`fetch` call directly in a React component

…is automatically rejected regardless of functionality.

## Scope

All apps under `go-control-erp/backend/apps/` and `go-control-erp/frontend/apps/`:
- `account`, `platform`, `backoffice` (current)
- All future apps (vendas, fiscal, estoque, etc.)

Incremental migration applies to existing code: touch a file → extract to service pattern.
