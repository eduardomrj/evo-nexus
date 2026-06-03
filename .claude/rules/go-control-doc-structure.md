# GO Control ERP — Estrutura de Documentação no Workspace

Applies to every agent (Bolt, Canvas, Compass, Apex, etc.) that creates or organiza documentação para o GO Control ERP e todos os projetos sob seu guarda-chuva (go-payment-hub, go-message, account, platform, backoffice, qualquer app futuro).

---

## Regra central

**Arquivo físico** → git do projeto em `/home/evonexus/evo-projects/go-control-erp/`  
**Symlink de acesso** → `workspace/projects/go-control-erp/{app}/{categoria}/`

Nunca criar arquivo físico dentro de `workspace/projects/`. Nunca colocar symlinks em `workspace/development/features/` para projetos externos.

---

## Estrutura de pastas por app/módulo

```
workspace/projects/go-control-erp/
  {app}/                        ← ex: go-payment-hub, go-message, account
    modulo/                     ← documentação do app como um todo
    features/                   ← uma subpasta por feature/refatoração/bugfix
      {slug}/
    ciclos/                     ← verifications de steps, sprints, entregas
      {ciclo}/
    manuais/                    ← documentação viva de uso
      tecnico/
      operacional/
    docs/                       ← backlog, brainstorm, glossário (transversal)
    ux/                         ← mockups HTML, protótipos visuais
```

---

## Onde vai cada tipo de artefato

| Artefato | Pasta |
|---|---|
| PRD do app inteiro | `{app}/modulo/` |
| Plano de implementação do app | `{app}/modulo/` |
| ADR de arquitetura do app (ex: ADR-007) | `{app}/modulo/` |
| Casos de uso, fluxos, modelagem do app | `{app}/modulo/` |
| Brainstorm e decisões preparatórias do app | `{app}/modulo/` |
| PRD de feature/refatoração/bugfix | `{app}/features/{slug}/` |
| Plano de feature/refatoração/bugfix | `{app}/features/{slug}/` |
| ADR específico de feature (ex: ADR-008) | `{app}/features/{slug}/` |
| Verification de step/sprint | `{app}/ciclos/{ciclo}/` |
| Manual técnico (API ref, arquitetura, connectors) | `{app}/manuais/tecnico/` |
| Manual operacional (onboarding, runbooks, troubleshooting) | `{app}/manuais/operacional/` |
| Backlog, glossário, brainstorm contínuo | `{app}/docs/` |
| Mockups HTML, protótipos visuais | `{app}/ux/` |

---

## Regras rápidas para agentes

1. **PRD/plano/ADR do app inteiro** → `modulo/`
2. **Feature, refactor, bugfix com nome próprio** → `features/{slug}/`
3. **Verification de step/sprint** → `ciclos/{ciclo}/`
4. **Manual técnico/operacional** → `manuais/tecnico/` ou `manuais/operacional/`
5. **Backlog, brainstorm, glossário** → `docs/`
6. **Mockups e protótipos** → `ux/`
7. **Nunca arquivo solto na raiz do app** — tudo vai em subpasta
8. **Slug de feature em kebab-case** — ex: `async-emission`, `payment-method-catalog`

---

## Como criar symlink ao salvar um artefato novo

```bash
# Exemplo: PRD de nova feature "dark-mode" no go-payment-hub
PHYSICAL=/home/evonexus/evo-projects/go-control-erp/features/go-payment-hub/[C]prd-dark-mode.md
LINK=/home/evonexus/evo-nexus/workspace/projects/go-control-erp/go-payment-hub/features/dark-mode/[C]prd-dark-mode.md

mkdir -p "$(dirname $LINK)"
ln -sf "$PHYSICAL" "$LINK"
```

---

## Referência: piloto go-payment-hub (estrutura aprovada 2026-06-02)

```
workspace/projects/go-control-erp/go-payment-hub/
  modulo/      ← prd, plan, architecture(ADR-007), casos-de-uso, fluxos, modelagem, brainstorm, decisoes
  features/
    async-emission/    ← ADR-008, prd-async-emission, plan-async-emission
    fase-2/            ← prd-fase2, plan-ciclo2
    platform-registration/ ← plan, runbook
  ciclos/
    fase-1/    ← step1..step6-verification
  docs/        ← backlog
  ux/          ← mockups HTML
```
