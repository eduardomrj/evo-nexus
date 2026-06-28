# Handoff para Agentes — SERKET Gestor

## Objetivo

Este arquivo é o contexto curto para delegar trabalho no repositório externo `serket-gestor`.

## Repo alvo

```text
/home/evonexus/evo-projects/serket-gestor
```

## Regra crítica de delegação

Ao chamar subagentes para trabalhar neste repo externo, usar `cwd` apontando para o repo e **não usar** `isolation: "worktree"`.

Exemplo correto:

```text
Agent({
  subagent_type: "apex-architect",
  cwd: "/home/evonexus/evo-projects/serket-gestor",
  prompt: "Analise ..."
})
```

Motivo: `isolation: "worktree"` cria worktree do EvoNexus, não do repo externo. Para repos externos, o padrão é `cwd`.

## Leitura obrigatória antes de agir

Antes de qualquer análise profunda, plano, revisão ou implementação, ler:

1. `/home/evonexus/evo-projects/serket-gestor/AGENTS.md`
2. `/home/evonexus/evo-projects/serket-gestor/.github/copilot-instructions.md`
3. `/home/evonexus/evo-projects/serket-gestor/README.md`

## Resumo técnico

- Projeto PHP web para gestão de fluxos de saúde.
- Framework: Adianti 7.5.x + MAD/Mad Builder.
- App executável fica em `_src/`.
- Banco: MySQL/MariaDB.
- Dependências via Composer em `_src/composer.json`.
- Arquitetura esperada: View → Controller → Service.
- APIs:
  - Web: `_src/index.php`
  - REST moderna: `_src/MadRestServer.php`
  - REST legada: `_src/rest.php`
  - Rotas modernas: `_src/app/routes/api.php`

## Guardrails

- LXC230 na homelab é ambiente de desenvolvimento/testes, não produção.
- App executável dev/test no LXC230: `/var/www/apps/serket/demo/_src`.
- Produção fica no servidor `Hetzner-App-Production` (`37.27.202.125:2299`, usuário `emrj`).
- App executável produção: `/home/emrj/stacks/app-serket-caninde/source`.
- Qualquer publicação/deploy para servidores deve acionar `@custom-sysops`, pois ele detém as credenciais e o caminho operacional seguro.
- Antes de qualquer build/deploy/sincronização no LXC230 ou produção, mostrar comandos/estratégia e pedir aprovação do Eduardo.
- Não imprimir credenciais de `_src/app/config/` nem sobrescrever configs do ambiente dev/test ou produção sem confirmação explícita.
- Não versionar logs, caches, `.env`, dumps, `vendor/` ou arquivos gerados.
- Antes de mudanças grandes, criar ticket/plano formal e pedir aprovação do Eduardo.
- Para implementação, preferir Bolt com escopo bem definido.
- Para arquitetura/debug read-only, preferir Apex.
- Para revisão, usar Lens.
- Para verificação, usar Oath.

## Comando base de status

```bash
git -C /home/evonexus/evo-projects/serket-gestor status --short --branch
```

## Próxima ação sugerida

Quando Eduardo passar a primeira demanda, classificar:

- Bug claro → Hawk ou Bolt, depois Oath.
- Feature ambígua → Echo → Compass → aprovação → Bolt → Oath.
- Decisão arquitetural → Apex, opcional Raven.
- Revisão de código → Lens.
