# Agentes em Repos Externos — Padrão de Delegação

Aplica-se a todos os agentes (Oracle, Oath, Grid, Bolt, Lens, Apex, etc.) que precisam trabalhar em repos fora do EvoNexus (ex: `go-control-erp`, `go-payment-hub`, `evonexus-discord-plus`).

---

## Padrão correto — `cwd` sem isolation

Use o parâmetro `cwd` do Agent tool apontando para o repo externo. **Não passe `isolation`.**

```
# CORRETO — sub-agente tem CWD no projeto e herda contexto do EvoNexus
Agent({
  subagent_type: "apex-architect",
  cwd: "/home/evonexus/evo-projects/go-control-erp",
  prompt: "analise a arquitetura do módulo account..."
})
```

**Por que funciona:** o parâmetro `cwd` só troca o diretório de trabalho do sub-agente. O `--add-dir /home/evonexus/evo-nexus` fica armazenado no estado global do processo pai (não no AsyncLocalStorage do CWD) e é herdado automaticamente. O sub-agente acessa os arquivos do projeto pelo CWD E os agents/rules/skills do EvoNexus pelo --add-dir.

**Pré-requisito:** o processo pai (oracle) deve ter sido iniciado com `--add-dir /home/evonexus/evo-nexus`. No Discord Plus com Project Context ativo isso acontece automaticamente.

---

## O que NÃO fazer

```
# ERRADO — isolation:worktree cria worktree do evo-nexus, não do repo externo
Agent({
  isolation: "worktree",
  cwd: "/home/evonexus/evo-projects/go-control-erp",
  prompt: "..."
})

# ERRADO — isolation e cwd são mutuamente exclusivos no Agent tool
# e isolation:worktree faz o sub-agente acordar num worktree do evo-nexus
```

---

## Acesso direto por caminho absoluto (sem Agent tool)

Quando não precisar delegar — só ler ou rodar algo no repo externo — use caminhos absolutos diretamente:

```bash
# Ler arquivo do projeto externo
Read("/home/evonexus/evo-projects/go-control-erp/backend/apps/account/models.py")

# Rodar testes
Bash("python -m pytest /home/evonexus/evo-projects/go-control-erp/backend/apps/account/tests/ -x")

# Build
Bash("bun run --cwd /home/evonexus/evo-projects/go-control-erp/frontend typecheck")
```

---

## Quando `isolation: "worktree"` é apropriado

Apenas para trabalho **interno ao EvoNexus** em branch isolada — ex: implementar uma feature sem afetar o working tree principal:

```
# OK — worktree do evo-nexus, contexto preservado, sem repo externo
Agent({
  isolation: "worktree",
  prompt: "implemente X na branch feature/y do EvoNexus..."
})
```

---

## Se você já está rodando num worktree

Se o seu CWD atual for `.claude/worktrees/agent-*`, você está num worktree do evo-nexus. Isso é normal para tarefas internas. Para acessar repos externos, use caminhos absolutos:

```bash
Read("/home/evonexus/evo-projects/go-control-erp/...")
Bash("python -m pytest /home/evonexus/evo-projects/go-control-erp/backend/...")
```

Não recuse o trabalho por estar num worktree. Use caminhos absolutos e siga normalmente.
