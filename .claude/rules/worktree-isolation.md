# Worktree Isolation — Regra para Repos Externos

Aplica-se a todos os agentes de engenharia (Oath, Grid, Bolt, Lens, Apex, etc.) que precisam verificar, testar ou trabalhar em repos fora do EvoNexus.

---

## O problema

`isolation: "worktree"` troca o CWD do subagente para o worktree do repo-alvo.  
Quando o repo-alvo é **externo** ao EvoNexus (ex: `go-control-erp`), o agente perde acesso a:

- `config/workspace.yaml`
- `memory/` e `.claude/agent-memory/`
- `.claude/agents/*.md`, `.claude/rules/`, `.claude/skills/`
- qualquer arquivo relativo ao workspace EvoNexus

Resultado: 3 falhas de leitura → agente para antes de fazer qualquer trabalho útil.

---

## Regra

> **Nunca use `isolation: "worktree"` para repos externos ao EvoNexus.**

```
# ERRADO — quebra o contexto do EvoNexus
Agent({
  isolation: "worktree",
  prompt: "verifique o commit c556a9d do go-control-erp..."
})
```

---

## Padrão correto para repos externos

Crie o worktree manualmente via Bash com caminhos absolutos. O CWD do agente permanece no EvoNexus.

### 1. Criar worktree temporário

```bash
REPO=/home/evonexus/evo-projects/go-control-erp
WORKTREE=/tmp/verify-$(basename $REPO)-$(date +%s)
git -C "$REPO" worktree add "$WORKTREE" <commit-ou-branch>
```

### 2. Trabalhar com caminhos absolutos

```bash
# Rodar testes
cd "$WORKTREE/backend" && python manage.py test apps/go_payment_hub/

# Ou sem trocar diretório
python -m pytest "$WORKTREE/backend/apps/go_payment_hub/tests/" -x

# Typecheck frontend
cd "$WORKTREE/frontend/apps/go-payment-hub" && bun run typecheck
```

### 3. Limpar ao terminar

```bash
git -C "$REPO" worktree remove "$WORKTREE" --force
```

---

## Quando `isolation: "worktree"` É seguro

Apenas quando o repo-alvo **é o próprio EvoNexus** — por exemplo, para testar uma feature em branch isolada sem afetar o working tree principal.

```
# OK — worktree do EvoNexus, contexto preservado
Agent({
  isolation: "worktree",
  prompt: "implemente X na branch feature/y do EvoNexus..."
})
```

---

## Agentes mais afetados

| Agente | Risco | Padrão recomendado |
|---|---|---|
| **Oath** | Alto — lê memória no startup | Bash com caminhos absolutos no worktree manual |
| **Grid** | Alto — lê workspace.yaml | Bash com caminhos absolutos no worktree manual |
| **Bolt** | Médio — só se CWD mudar | Manter CWD no EvoNexus, passar caminho absoluto do repo |
| **Lens** | Baixo — read-only | Pode ler arquivos por caminho absoluto sem worktree |

---

## Exemplo completo — Oath verificando go-control-erp

```bash
# 1. Criar worktree
REPO=/home/evonexus/evo-projects/go-control-erp
WT=/tmp/oath-verify-go-payment-hub-$(date +%s)
git -C "$REPO" worktree add "$WT" backup/go-payment-hub-wip-2026-06-03

# 2. Verificar
cd "$WT/backend"
SECRET_KEY=verify-only python manage.py check --deploy 2>&1 | head -20
python -m pytest apps/go_payment_hub/tests/ -x --tb=short 2>&1 | tail -30

# 3. Limpar
git -C "$REPO" worktree remove "$WT" --force
```

O agente Oath continua rodando no EvoNexus, lê sua memória normalmente, e acessa o repo externo via caminho absoluto.
