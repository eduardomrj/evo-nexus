# GO Control ERP — Índice de Documentação

Navegação central do projeto. Todos os links abrem direto na interface do EvoNexus.

---

## Documentação base

| Documento | Descrição |
|---|---|
| [ADR-001 — Padrões de Arquitetura](docs/ADR-001-architecture-standards.md) | **Lei do projeto.** Camadas, SOLID, GoF, limites duros. Autoridade máxima. |
| [Agent Instructions](docs/agent-instructions.md) | Ponto de entrada para agentes — lido primeiro antes de qualquer trabalho |
| [Coding Standards](docs/coding-standards.md) | Nomenclatura, lint, formatação, convenções de código |
| [CRUD & Design Patterns](docs/crud-and-design-patterns.md) | Padrões de implementação para endpoints, serializers, repositórios |
| [Design System](docs/design-system.md) | Tokens visuais, paleta, tipografia, componentes aprovados |

---

## Planos de execução

| Plano | Descrição |
|---|---|
| [ADR-001 Account Refactor](plans/[C]plan-adr001-account-refactor.md) | Refactor do app `account` para seguir as camadas do ADR-001 |

---

## Features

### aplicativo-entity
| Artefato | Tipo |
|---|---|
| [PRD](features/aplicativo-entity/[C]prd-aplicativo-entity.md) | Requisitos |
| [Plano](features/aplicativo-entity/[C]plan-aplicativo-entity.md) | Plano de execução |
| [Verificação](features/aplicativo-entity/[C]verification-aplicativo-entity.md) | Evidências de entrega |

### ciclo2-redesign
| Artefato | Tipo |
|---|---|
| [Verificação — Steps 15-17](features/ciclo2-redesign/[C]verification-ciclo2-steps15-17.md) | Evidências |
| [Verificação — Step 18 Smoke](features/ciclo2-redesign/[C]verification-ciclo2-step18-smoke.md) | Evidências |

### conexoes-banco
| Artefato | Tipo |
|---|---|
| [Plano](features/conexoes-banco/[C]plan-conexoes-banco.md) | Plano de execução |

### divergencias-backoffice
| Artefato | Tipo |
|---|---|
| [Divergências 2026-05-11](features/divergencias-backoffice/[C]divergencias-2026-05-11.md) | Auditoria |

### go-message-aplicativo-integration
| Artefato | Tipo |
|---|---|
| [PRD](features/go-message-aplicativo-integration/[C]prd-go-message-aplicativo-integration.md) | Requisitos |
| [Plano](features/go-message-aplicativo-integration/[C]plan-go-message-aplicativo-integration.md) | Plano de execução |

### modulo-hierarquico
| Artefato | Tipo |
|---|---|
| [Discovery Fase 2](features/modulo-hierarquico/[C]discovery-fase2-modulo-hierarquico.md) | Discovery |
| [PRD](features/modulo-hierarquico/[C]prd-modulo-hierarquico.md) | Requisitos |
| [Plano](features/modulo-hierarquico/[C]plan-modulo-hierarquico.md) | Plano de execução |
| [PRD Fase 2a](features/modulo-hierarquico/[C]prd-fase2a-modulo-hierarquico.md) | Requisitos fase 2a |
| [Plano Fase 2a](features/modulo-hierarquico/[C]plan-fase2a-modulo-hierarquico.md) | Plano fase 2a |

### owner-phone-nova-conta
| Artefato | Tipo |
|---|---|
| [Plano](features/owner-phone-nova-conta/[C]plan-owner-phone-nova-conta.md) | Plano de execução |

### permissoes-rbac
| Artefato | Tipo |
|---|---|
| [Architecture](features/permissoes-rbac/[C]architecture-permissoes-rbac.md) | Decisões arquiteturais |
| [Plano](features/permissoes-rbac/[C]plan-permissoes-rbac.md) | Plano de execução |
| [Audit Step 1](features/permissoes-rbac/[C]audit-step1.md) | Auditoria |

### planos-licencas
| Artefato | Tipo |
|---|---|
| [Plano](features/planos-licencas/[C]plan-planos-licencas.md) | Plano de execução |

### refactor-account-app
| Artefato | Tipo |
|---|---|
| [PRD](features/refactor-account-app/[C]prd-refactor-account-app.md) | Requisitos |

### template-app-cliente-go
| Artefato | Tipo |
|---|---|
| [PRD](features/template-app-cliente-go/[C]prd-template-app-cliente-go.md) | Requisitos |

---

> **Atualização automática:** toda vez que um agente criar um novo doc, plano ou artifact de feature neste projeto, o symlink e a entrada neste INDEX.md devem ser adicionados.
