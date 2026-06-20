# GO Control Platform — Workspace Index

Pasta raiz do ecossistema GO Control Platform no workspace do EvoNexus.
Cada entrada é um symlink para a pasta `docs/` do repositório real em
`/home/evonexus/evo-projects/go-control/`.

## Arquitetura da plataforma

```
GO Control Platform
├── Apps centrais     AUTH · ADMIN · ACCOUNT
├── SDK               go-control-sdk (Python + TypeScript)
├── Apps em dev       PAYMENT-HUB · MESSAGE · COBRANCA · ERP (planejado)
└── Shared services   PESSOAS · PRODUTOS (repos independentes, consumidos via API)
```

## Apps centrais

| Pasta | Repositório real | Descrição |
|---|---|---|
| `go-control-auth/` | `go-control/go-control-auth/docs/` | Auth Central — autenticação, tokens, SSO |
| `go-control-admin/` | `go-control/go-control-admin/docs/` | Platform Admin — tenants, módulos, licenças, RBAC |
| `go-control-account/` | `go-control/go-control-account/docs/` | App Account (multi-tenant) |
| `go-control-sdk/` | `go-control/go-control-sdk/docs/` | SDK compartilhado (Python + TypeScript) |
| `go-control-app-template/` | `go-control/go-control-app-template/docs/` | Template base para novos apps |

## Apps em desenvolvimento

| Pasta | Repositório real | Descrição |
|---|---|---|
| `go-payment-hub/` | `go-control/go-payment-hub/docs/` | Orquestrador bancário — Pix, boleto, conectores |
| `go-message/` | `go-control/go-message/docs/` | Mensageria multi-canal — WhatsApp, Discord, Email |
| `go-cobranca/` | `go-control/go-cobranca/docs/` | Cobrança recorrente — assinaturas, faturas |
| `go-control-erp/` | `go-control/go-control-erp/docs/` | ERP — **planejado, não iniciado** (origem: migração mini-ERP PHP) |

## Shared services

| Pasta | Repositório real | Descrição |
|---|---|---|
| `go-pessoas/` | `go-control/go-pessoas/docs/` | Cadastro mestre PF/PJ — shared service consumido por todos os apps (ADR-012) |
| `go-produtos/` | `go-control/go-produtos/docs/` | Catálogo de produtos — shared service |

## Documentação da plataforma

| Pasta | Repositório real | Descrição |
|---|---|---|
| `umbrella/` | `go-control/docs/` | Arquitetura, design system, padrões, port registry |
