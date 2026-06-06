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
      ciclos/{ciclo}/
      reviews/
      manuais/
        tecnico/
        operacional/
      ux/               ← mockups HTML, protótipos
```

**Não existe pasta `docs/` dentro de `{app}/`.** Não há subpasta `docs/docs/`.

---

## Onde vai cada tipo de artefato

| Artefato | Caminho físico |
|---|---|
| ADR do projeto inteiro | `docs/architecture/decisions/ADR-NNN-*.md` |
| Padrões de código/arquitetura | `docs/architecture/` |
| Design System | `docs/design-system.md` |
| PRD de feature | `docs/{app}/features/{slug}/[C]prd-*.md` |
| Plano de feature | `docs/{app}/features/{slug}/[C]plan-*.md` |
| ADR de feature específica | `docs/{app}/features/{slug}/[C]adr-*.md` |
| Discovery / modelagem / CUs / fluxos de feature | `docs/{app}/features/{slug}/[C]*.md` |
| PRD e plano do sub-app (MVP ou ciclo) | `docs/{app}/plans/{slug}/` |
| Brainstorm, backlog, decisões transversais | `docs/{app}/plans/{slug}/` |
| Verification de ciclo/sprint | `docs/{app}/ciclos/{ciclo}/[C]*.md` |
| Code review | `docs/{app}/reviews/` |
| Referência técnica (API docs, integrações) | `docs/{app}/manuais/tecnico/` |
| Runbooks, guias de onboarding, release notes | `docs/{app}/manuais/operacional/` |
| Mockup HTML | `docs/{app}/ux/` |

---

## Regras rápidas para agentes

1. **Qualquer doc** → sempre dentro de `docs/{app}/` — nunca na raiz do projeto nem em `backend/` ou `frontend/`
2. **ADR do projeto inteiro** → `docs/architecture/decisions/`
3. **Feature com nome próprio** → `docs/{app}/features/{slug}/` (PRD, plan, ADR, modelagem, CUs, fluxos, verification, retro)
4. **PRD/plan do sub-app, brainstorm, backlog, decisões** → `docs/{app}/plans/{slug}/` (ex: `plans/mvp/`)
5. **Plano multi-fase** → `docs/{app}/plans/{slug}/`
6. **Verification de ciclo/sprint** → `docs/{app}/ciclos/{ciclo}/`
7. **Code review** → `docs/{app}/reviews/`
8. **Referência técnica** (API docs, integração) → `docs/{app}/manuais/tecnico/`
9. **Runbook / guia operacional / release notes** → `docs/{app}/manuais/operacional/`
10. **Mockup HTML** → `docs/{app}/ux/`
11. **Slug em kebab-case** — ex: `async-emission`, `payment-method-catalog`
12. **Nada solto na raiz de `docs/{app}/`** — tudo vai em subpasta tipada
13. **Não criar pasta `docs/` dentro de `{app}/`** — não existe `docs/{app}/docs/`

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
