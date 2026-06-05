# GO Control ERP — Estrutura de Documentação

Applies to every agent (Bolt, Canvas, Compass, Apex, etc.) that creates or organizes documentation for GO Control ERP and all apps under its umbrella (go-payment-hub, go-message, account, platform, go-control-auth, go-cobranca, modulo-pessoas, any future app).

---

## Regra central

**Arquivo físico** → `evo-projects/go-control-erp/docs/{app}/`  
**Acesso no workspace** → `workspace/projects/go-control-erp/{app}/` (symlink automático — não criar symlinks individuais)

Nunca criar arquivo físico dentro de `workspace/projects/`. O workspace é só acesso via symlinks.

---

## Estrutura completa

```
evo-projects/go-control-erp/
  backend/              ← código Django (nunca misturar docs aqui)
  frontend/             ← código React (nunca misturar docs aqui)
  infra/
  scripts/
  tests/
  docs/
    architecture/
      decisions/        ← ADRs do projeto inteiro (ADR-001..N)
      coding-standards.md
      crud-and-design-patterns.md
    design-system.md    ← Design System visual (leitura obrigatória antes de frontend)
    agent-instructions.md
    {app}/              ← account | platform | go-control-auth | go-message |
      features/{slug}/  ← go-payment-hub | go-cobranca | modulo-pessoas
      plans/{slug}/
      docs/             ← docs principais do sub-app (PRD, arquitetura, planos do módulo)
      ux/               ← mockups HTML, protótipos
      manuais/
        tecnico/
        operacional/
      ciclos/{ciclo}/
```

---

## Onde vai cada tipo de artefato

| Artefato | Caminho físico |
|---|---|
| ADR do projeto inteiro | `docs/architecture/decisions/ADR-NNN-*.md` |
| Padrões de código/arquitetura | `docs/architecture/` |
| Design System | `docs/design-system.md` |
| PRD / arquitetura / plano do sub-app | `docs/{app}/docs/` |
| ADR de feature específica | `docs/{app}/features/{slug}/[C]adr-*.md` |
| PRD de feature | `docs/{app}/features/{slug}/[C]prd-*.md` |
| Plano de feature | `docs/{app}/features/{slug}/[C]plan-*.md` |
| Discovery / verification de feature | `docs/{app}/features/{slug}/[C]*.md` |
| Plano multi-fase | `docs/{app}/plans/{slug}/[C]index-{data}.md` |
| Verification de ciclo/sprint | `docs/{app}/ciclos/{ciclo}/[C]*.md` |
| Manual técnico | `docs/{app}/manuais/tecnico/` |
| Manual operacional | `docs/{app}/manuais/operacional/` |
| Mockup HTML | `docs/{app}/ux/` |

---

## Regras rápidas para agentes

1. **Qualquer doc** → sempre dentro de `docs/` — nunca na raiz do projeto nem em `backend/` ou `frontend/`
2. **ADR do projeto** → `docs/architecture/decisions/`
3. **Doc do sub-app inteiro** (PRD, arquitetura, plano de módulo) → `docs/{app}/docs/`
4. **Feature com nome próprio** → `docs/{app}/features/{slug}/`
5. **Plano multi-fase** → `docs/{app}/plans/{slug}/`
6. **Verification de ciclo** → `docs/{app}/ciclos/{ciclo}/`
7. **Manual** → `docs/{app}/manuais/tecnico/` ou `manuais/operacional/`
8. **Mockup** → `docs/{app}/ux/`
9. **Slug em kebab-case** — ex: `async-emission`, `payment-method-catalog`
10. **Nada solto na raiz de `docs/{app}/`** — tudo vai em subpasta

---

## Symlinks no workspace

O workspace espelha `docs/{app}/` via symlinks em:
```
workspace/projects/go-control-erp/{app}/ → evo-projects/docs/{app}/
```

**Não é necessário criar symlinks individuais por arquivo.** Salvar em `docs/{app}/` já torna o arquivo visível no workspace automaticamente.

Exceção — arquivos diretos em `docs/` (não em `docs/{app}/`):
```bash
ln -sf "/home/evonexus/evo-projects/go-control-erp/docs/<arquivo>" \
       "/home/evonexus/evo-nexus/workspace/projects/go-control-erp/docs/<arquivo>"
```

---

## Exemplo: criar PRD de nova feature no go-payment-hub

```bash
# 1. Salvar o arquivo físico
PHYSICAL=/home/evonexus/evo-projects/go-control-erp/docs/go-payment-hub/features/dark-mode/[C]prd-dark-mode.md
mkdir -p "$(dirname $PHYSICAL)"
# ... escrever o arquivo ...

# 2. Symlink não é necessário — workspace/go-payment-hub já aponta para docs/go-payment-hub/
# O arquivo aparece automaticamente em:
# workspace/projects/go-control-erp/go-payment-hub/features/dark-mode/[C]prd-dark-mode.md
```
