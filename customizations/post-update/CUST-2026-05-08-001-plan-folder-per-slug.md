# CUST-2026-05-08-001 — Planos em pasta própria por slug

**Status:** active  
**Criado em:** 2026-05-08  
**Origem:** feedback do Eduardo durante a criação do plano `discord-openclaude-bridge`  
**Área:** workspace/development/plans + skill `prod-activation-plan`

## Problema

A skill nativa `prod-activation-plan` documenta e cria planos diretamente em:

```text
workspace/development/plans/
├── [C]{plan-name}-{YYYY-MM-DD}.md
├── fase-1-...
├── fase-2-...
└── fase-3-...
```

Isso fica aceitável para poucos planos, mas começa a bagunçar quando existem vários planos independentes. As pastas `fase-*` de projetos distintos passam a disputar o mesmo nível em `workspace/development/plans/`.

## Decisão local

Planos devem seguir uma estrutura semelhante a `workspace/development/features/{feature-slug}/`, isolando cada plano em sua própria pasta:

```text
workspace/development/plans/{plan-slug}/
├── [C]index-{YYYY-MM-DD}.md
├── fase-1-{purpose-slug}/
│   ├── [C]{item-id}-{item-slug}.md
│   └── ...
├── fase-2-{purpose-slug}/
└── fase-3-{purpose-slug}/
```

Exemplo aplicado:

```text
workspace/development/plans/discord-openclaude-bridge/
├── [C]index-2026-05-08.md
├── fase-1-discovery-arquitetura/
├── fase-2-poc-isolada/
├── fase-3-robustez-testes-status/
└── fase-4-integracao-cutover/
```

## Arquivo nativo afetado

```text
.claude/skills/prod-activation-plan/SKILL.md
```

## Mudança desejada no core

Atualizar a skill `prod-activation-plan` para:

1. Criar uma pasta por plano:
   ```text
   workspace/development/plans/{plan-name}/
   ```
2. Escrever o índice como:
   ```text
   workspace/development/plans/{plan-name}/[C]index-{YYYY-MM-DD}.md
   ```
3. Criar as pastas de fase dentro da pasta do plano:
   ```text
   workspace/development/plans/{plan-name}/fase-1-...
   ```
4. Ajustar os links do índice para caminhos relativos dentro da pasta do plano.
5. Ao detectar planos legados no formato antigo, não sobrescrever; sugerir migração para `{plan-name}/`.

## Patch conceitual

Substituir no `SKILL.md` referências como:

```text
workspace/development/plans/
├── [C]{plan-name}-{YYYY-MM-DD}.md
├── {phase-1-slug}/
```

por:

```text
workspace/development/plans/{plan-name}/
├── [C]index-{YYYY-MM-DD}.md
├── {phase-1-slug}/
```

Substituir instruções como:

```bash
cd workspace/development/plans/
mkdir -p {phase-1-slug} {phase-2-slug} {phase-3-slug}
```

por:

```bash
cd workspace/development/plans/
mkdir -p {plan-name}/{phase-1-slug} {plan-name}/{phase-2-slug} {plan-name}/{phase-3-slug}
```

Substituir:

```text
Write `[C]{plan-name}-{YYYY-MM-DD}.md` at the root of `workspace/development/plans/`.
```

por:

```text
Write `[C]index-{YYYY-MM-DD}.md` inside `workspace/development/plans/{plan-name}/`.
```

## Como verificar se a nova versão já incorporou

Após atualizar EvoNexus, rodar/checar:

```bash
grep -n "workspace/development/plans/{plan-name}" .claude/skills/prod-activation-plan/SKILL.md
grep -n "\[C\]index-{YYYY-MM-DD}" .claude/skills/prod-activation-plan/SKILL.md
```

Se esses padrões existirem e o formato antigo `workspace/development/plans/[C]{plan-name}-{YYYY-MM-DD}.md` não for mais o padrão principal, marcar esta customização como `upstreamed`.

## Estado aplicado localmente

A customização foi aplicada localmente em 2026-05-08 nas três camadas:

1. `CLAUDE.md` agora instrui agentes a consultar `customizations/post-update/INDEX.md` e a não criar pastas `fase-*` soltas diretamente em `workspace/development/plans/`.
2. `.claude/skills/prod-activation-plan/SKILL.md` foi ajustada para criar planos em `workspace/development/plans/{plan-name}/[C]index-{YYYY-MM-DD}.md`.
3. Patch real salvo em:
   ```text
   customizations/post-update/patches/CUST-2026-05-08-001-prod-activation-plan-folder-per-slug.diff
   ```

O plano `discord-openclaude-bridge` já foi migrado manualmente para:

```text
workspace/development/plans/discord-openclaude-bridge/[C]index-2026-05-08.md
```

Referências conhecidas em memória foram atualizadas para o novo caminho.

## Como reaplicar após update

Se uma atualização do EvoNexus sobrescrever `.claude/skills/prod-activation-plan/SKILL.md`, revise primeiro se o upstream já incorporou o padrão novo. Se não incorporou, reaplique o patch:

```bash
git apply customizations/post-update/patches/CUST-2026-05-08-001-prod-activation-plan-folder-per-slug.diff
```

Se o patch não aplicar limpo, abra este arquivo e aplique manualmente a regra: planos ficam em `workspace/development/plans/{plan-name}/[C]index-{date}.md`.

## Observação

Não remover esta customização até confirmar que o EvoNexus oficial incorporou o padrão de pasta por plano.
