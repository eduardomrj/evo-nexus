---
name: feature-kickoff
description: "Orquestra o planejamento completo de uma feature, módulo, recurso ou aplicação — cobrindo PRD, modelagem funcional, UX/UI e arquitetura técnica, com checkpoints interativos entre cada etapa. Use quando: 'feature-kickoff', 'planejar feature', 'novo módulo', 'nova aplicação', 'quero documentar antes de codar', 'falta modelagem/UX/arquitetura'."
argument-hint: "[nome da feature] [--auto]"
---

# Feature Kickoff

Skill que orquestra o planejamento completo de uma feature/módulo/aplicação, cobrindo todas as etapas de documentação antes de codar — com **checkpoints interativos** entre cada etapa para que você revise e aprove antes de avançar.

## Quando Usar

- "quero planejar uma feature nova para o projeto X"
- "vou criar um novo módulo/recurso/aplicação"
- "preciso de PRD + modelagem + UX + arquitetura documentados"
- "feature-kickoff"
- Qualquer início de trabalho que precise de documentação antes de implementar

## Quando NÃO Usar

- Feature simples que já tem PRD aprovado e só falta implementar → use `@bolt-executor` diretamente
- Só quer criar tickets avulsos → use `create-ticket`
- Só quer o PRD → use `pm-write-spec`

## Modos

- **`/feature-kickoff`** — modo guiado (padrão): pausa após cada etapa, mostra o artefato e aguarda aprovação antes de avançar
- **`/feature-kickoff --auto`** — modo automático: executa todas as etapas selecionadas sem pausar

---

## Workflow

### Step 0 — Coleta inicial

Antes de qualquer coisa, pergunte ao usuário em bloco único:

```
Para iniciar o planejamento, preciso de algumas informações:

1. **Projeto:** a qual projeto isso pertence? (ex: go-control-erp, serket, evo-crm...)
2. **Nome:** qual é o nome desta feature/módulo/recurso/aplicação?
3. **Objetivo:** em uma frase, o que ela faz ou resolve?
4. **Contexto:** há alguma decisão técnica já tomada (stack, padrões, dependências) que devo considerar?
```

Aguarde a resposta. Derive:
- `project_name` — nome do projeto
- `feature_name` — nome da feature (ex: "Módulo Fiscal", "Tela de Relatórios", "API de Pagamentos")
- `slug` — kebab-case do feature_name (ex: `modulo-fiscal`, `tela-relatorios`, `api-pagamentos`)
- `feature_folder` — `workspace/projects/{project_name}/features/{slug}/`

### Step 1 — Seleção de etapas

Apresente o menu de etapas e peça ao usuário que confirme quais ativar. As etapas marcadas com ✅ estão ativas por padrão:

```
Quais etapas você quer incluir no planejamento desta feature?

✅ 1. Discovery (gaps, requisitos implícitos, riscos) — sempre recomendado
✅ 2. PRD + Plano executável — sempre recomendado
   3. Modelagem funcional (casos de uso, fluxos, backlog) — recomendado para features com regras de negócio complexas
   4. UX/UI (wireframes HTML interativos) — recomendado se houver interface
   5. Arquitetura técnica (ADR: stack, banco, APIs, infra) — recomendado para features novas ou complexas

Responda com os números que quer ativar além dos padrões (ex: "3 4 5" ou "todas" ou "só padrão").
```

Armazene a lista de etapas selecionadas como `etapas_ativas`.

Se o argumento `--auto` foi passado, informe: *"Modo automático ativo — executarei todas as etapas selecionadas sem pausar."*

---

### Step 2 — Etapa 1: Discovery [@echo-analyst]

> *Sempre executada.*

Invoque `@echo-analyst` com briefing completo:
- Nome e objetivo da feature
- Projeto e contexto técnico informados pelo usuário
- Instrução para gerar `[C]discovery-{slug}.md` em `{feature_folder}`
- Instrução para identificar: requisitos não óbvios, regras de negócio implícitas, riscos, dependências, critérios de aceitação em aberto, anti-requisitos

**Modo guiado — CHECKPOINT após retorno:**
```
✅ Discovery concluído → {feature_folder}[C]discovery-{slug}.md

Principais achados do Echo:
• [resumo em 3-5 bullets dos principais gaps e requisitos identificados]

Quer ajustar algo antes de partirmos para o PRD?
Responda "ok" para continuar ou aponte o que corrigir.
```
**Aguarde confirmação antes de avançar.**

**Modo auto:** avance diretamente.

---

### Step 3 — Etapa 2: PRD + Plano [@compass-planner]

> *Sempre executada.*

Invoque `@compass-planner` com:
- Artefato `[C]discovery-{slug}.md` gerado pelo Echo
- Contexto completo do projeto
- Instrução para gerar na `{feature_folder}`:
  - `[C]prd-{slug}.md` — o quê e por quê, com critérios de aceitação em Given/When/Then
  - `[C]plan-{slug}.md` — 3-6 steps executáveis, cada um com: título, descrição, agente responsável, dependências, riscos e critérios de aceitação

**Modo guiado — CHECKPOINT após retorno:**
```
✅ PRD + Plano concluídos
   → {feature_folder}[C]prd-{slug}.md
   → {feature_folder}[C]plan-{slug}.md

O plano tem X steps. Resumo:
• Step 1: [título]
• Step 2: [título]
• ...

Quer ajustar algo antes de [próxima etapa ativa]?
Responda "ok" para continuar ou aponte o que corrigir.
```
**Aguarde confirmação antes de avançar.**

**Modo auto:** avance diretamente.

---

### Step 4 — Etapa 3: Modelagem funcional [@compass-planner ou @echo-analyst]

> *Executada somente se "3" estiver em `etapas_ativas`.*

Invoque `@compass-planner` com:
- `[C]prd-{slug}.md` e `[C]discovery-{slug}.md`
- Instrução para gerar `[C]functional-model-{slug}.md` em `{feature_folder}` com:

  **Casos de uso:**
  - Identificar todos os atores (usuário, sistema, agente externo)
  - Para cada ator, listar casos de uso em formato: `UC-{N}: [ator] [verbo] [objeto]`
  - Pré-condições, pós-condições e fluxo alternativo de erro para cada UC

  **Fluxos principais:**
  - Fluxo principal (happy path) em formato de lista numerada de passos
  - Fluxos alternativos e de exceção identificados

  **Backlog funcional:**
  - Lista priorizada de funcionalidades por critério MoSCoW (Must/Should/Could/Won't)
  - Cada item com: ID, título, ator beneficiado, critério de aceitação resumido

**Modo guiado — CHECKPOINT após retorno:**
```
✅ Modelagem funcional concluída → {feature_folder}[C]functional-model-{slug}.md

Resumo:
• X casos de uso identificados
• Atores: [lista]
• Must-have: Y itens | Should: Z | Could: W

Quer ajustar algo antes de [próxima etapa ativa]?
Responda "ok" para continuar ou aponte o que corrigir.
```
**Aguarde confirmação antes de avançar.**

**Modo auto:** avance diretamente.

---

### Step 5 — Etapa 4: UX/UI [@canvas-designer]

> *Executada somente se "4" estiver em `etapas_ativas`.*

Invoque `@canvas-designer` com:
- `[C]prd-{slug}.md` e `[C]functional-model-{slug}.md` (se existir)
- Contexto de projeto: stack frontend, design system existente (se houver), padrões visuais
- Instrução para gerar wireframes HTML interativos em `{feature_folder}ux/`:
  - Um arquivo HTML por tela/fluxo principal identificado nos casos de uso
  - Nomear como `ux-{tela}.html` (ex: `ux-cadastro.html`, `ux-listagem.html`)
  - Incluir: estrutura de layout, componentes principais, fluxo de navegação entre telas
  - Não inventar paleta — usar design system existente se informado; caso contrário, tema neutro

**Modo guiado — CHECKPOINT após retorno:**
```
✅ UX/UI concluído → {feature_folder}ux/

Telas geradas:
• ux-{tela1}.html — [descrição]
• ux-{tela2}.html — [descrição]
• ...

Quer ajustar algo antes de [próxima etapa ativa]?
Responda "ok" para continuar ou aponte o que corrigir.
```
**Aguarde confirmação antes de avançar.**

**Modo auto:** avance diretamente.

---

### Step 6 — Etapa 5: Arquitetura técnica [@apex-architect]

> *Executada somente se "5" estiver em `etapas_ativas`.*

Invoque `@apex-architect` com:
- `[C]prd-{slug}.md`, `[C]plan-{slug}.md`
- `[C]functional-model-{slug}.md` (se existir)
- Contexto do projeto (stack, padrões, ADRs existentes)
- Instrução para gerar `[C]architecture-{slug}.md` em `{feature_folder}` em formato ADR com:
  - **Decisão:** o que foi decidido
  - **Drivers:** contexto e restrições que motivaram a decisão
  - **Alternativas consideradas:** com prós e contras de cada
  - **Stack técnica:** linguagem, frameworks, banco de dados, infraestrutura
  - **Modelo de dados:** entidades principais e relacionamentos
  - **APIs e integrações:** contratos de interface (endpoints, eventos, mensagens)
  - **Consequências:** impactos positivos e negativos da decisão
  - **Riscos arquiteturais:** o que pode dar errado e como mitigar
  - **Follow-ups:** decisões que precisam ser tomadas depois

**Modo guiado — CHECKPOINT após retorno:**
```
✅ Arquitetura técnica concluída → {feature_folder}[C]architecture-{slug}.md

Pontos principais:
• Stack: [resumo]
• Decisões chave: [3-5 bullets]
• Riscos identificados: [resumo]

Quer ajustar algo antes de finalizar?
Responda "ok" para continuar ou aponte o que corrigir.
```
**Aguarde confirmação antes de avançar.**

**Modo auto:** avance diretamente.

---

### Step 7 — Criar tickets? (checkpoint)

Antes do resumo final, pergunte:

```
✅ Planejamento concluído! Todos os artefatos estão em {feature_folder}

Quer criar os tickets de implementação agora?
Isso vai gerar:
• 1 Goal no dashboard linkado a esta feature
• X tickets de [Build] — um por step do plano, assignados a @bolt-executor
• 2 tickets de [Verify] — @oath-verifier e @lens-reviewer
• 1 ticket de [Retro] — @mirror-retro

Responda "sim" para criar ou "não" para pular.
```

Se o usuário responder **não**, avance para o Step 8 (resumo final).
Se responder **sim**, execute o Step 7a antes do Step 8.

---

### Step 7a — Criar Goal e Tickets [condicional]

#### Criar o Goal

Leia `[C]plan-{slug}.md` e conte o número de steps (= `n_steps`).

```python
from dashboard.backend.sdk_client import evo

# Buscar projeto pelo nome — se não existir, criar
projects = evo.get(f"/api/projects?name={project_name}")
if projects:
    project_id = projects[0]["id"]
else:
    proj = evo.post("/api/projects", {"name": project_name, "description": f"Projeto {project_name}"})
    project_id = proj["id"]

# Criar o goal
goal = evo.post("/api/goals", {
    "title": feature_name,
    "description": f"Feature planejada via feature-kickoff. PRD: {feature_folder}[C]prd-{slug}.md",
    "metric_type": "count",
    "target_value": n_steps,
    "current_value": 0,
    "status": "active",
    "project_id": project_id
})
goal_id = goal["id"]
```

#### Criar tickets de Build (um por step do plano)

```python
priority_map = {1: "urgent", 2: "high", 3: "high", 4: "medium", 5: "medium", 6: "low"}
tickets_criados = []

for i, step in enumerate(steps, start=1):
    ticket = evo.post("/api/tickets", {
        "title": f"[Build] {step['title']}",
        "description": f"""## Contexto
{step['description']}

## Critérios de Aceitação
{step['acceptance_criteria']}

## Agente Responsável
{step['agent']}

## Dependências
{step['dependencies']}

## Riscos
{step['risks']}

---
Fase: 4 - Build | Feature: {feature_name} | Projeto: {project_name}
PRD: {feature_folder}[C]prd-{slug}.md
Plano: {feature_folder}[C]plan-{slug}.md
{f"Arquitetura: {feature_folder}[C]architecture-{slug}.md" if arquitetura_ativa else ""}

## Instrução ao Agente — Ao Finalizar
Ao concluir, poste um comentário via EvoClient SDK:

```python
from dashboard.backend.sdk_client import evo
evo.post("/api/tickets/TICKET_ID/comments", {{
    "author": "agent:bolt-executor",
    "body": "✅ Build concluído.\\n\\n**Resultado:** <resumo>\\n**Commits:** <hashes>\\n**Arquivos alterados:** <lista>\\n**Status:** PASS | FAIL\\n\\n<observações>"
}})
```
""",
        "priority": priority_map.get(i, "medium"),
        "assignee_agent": step.get("agent", "bolt-executor"),
        "goal_id": goal_id
    })
    tickets_criados.append({"id": ticket["id"], "title": f"[Build] {step['title']}", "fase": 4})
```

#### Criar tickets de Verify (dois fixos)

```python
# Ticket 1 — Verificação de critérios de aceitação
ticket_oath = evo.post("/api/tickets", {
    "title": f"[Verify] Verificar critérios de aceitação — {feature_name}",
    "description": f"""## Objetivo
Verificar que todos os critérios de aceitação definidos no PRD foram atendidos com evidência real (output de testes, build status, screenshots).

## Critérios de Aceitação
- Todos os Given/When/Then do PRD mapeados para evidência concreta
- Build passando sem erros
- Nenhum "should work" sem prova — apenas output real

## Dependências
Todos os tickets de [Build] devem estar fechados antes de iniciar.

## Referências
PRD: {feature_folder}[C]prd-{slug}.md
Plano: {feature_folder}[C]plan-{slug}.md

## Instrução ao Agente — Ao Finalizar
```python
from dashboard.backend.sdk_client import evo
evo.post("/api/tickets/TICKET_ID/comments", {{
    "author": "agent:oath-verifier",
    "body": "✅ Verificação concluída.\\n\\n**Artefato:** {feature_folder}[C]verification-{slug}.md\\n**Critérios verificados:** X/Y\\n**Status:** PASS | FAIL | INCOMPLETE\\n\\n<sumário das evidências>"
}})
```
""",
    "priority": "high",
    "assignee_agent": "oath-verifier",
    "goal_id": goal_id
})
tickets_criados.append({"id": ticket_oath["id"], "title": "[Verify] Verificar critérios de aceitação", "fase": 5})

# Ticket 2 — Code review
ticket_lens = evo.post("/api/tickets", {
    "title": f"[Review] Code review — {feature_name}",
    "description": f"""## Objetivo
Realizar code review em 2 etapas: (1) conformidade com spec/PRD e (2) qualidade de código (OWASP, SOLID, lógica).

## Critérios de Aceitação
- Nenhum item CRITICAL ou HIGH sem resolução documentada
- Conformidade com todos os critérios do PRD verificada

## Dependências
Tickets de [Build] devem estar fechados antes de iniciar.

## Referências
PRD: {feature_folder}[C]prd-{slug}.md
{f"Arquitetura: {feature_folder}[C]architecture-{slug}.md" if arquitetura_ativa else ""}

## Instrução ao Agente — Ao Finalizar
```python
from dashboard.backend.sdk_client import evo
evo.post("/api/tickets/TICKET_ID/comments", {{
    "author": "agent:lens-reviewer",
    "body": "✅ Code review concluído.\\n\\n**Artefato:** {feature_folder}[C]code-review-{slug}.md\\n**CRITICAL:** X | **HIGH:** Y | **MEDIUM/LOW:** Z\\n**Veredicto:** SAFE | MONITOR | HOLD\\n\\n<sumário>"
}})
```
""",
    "priority": "high",
    "assignee_agent": "lens-reviewer",
    "goal_id": goal_id
})
tickets_criados.append({"id": ticket_lens["id"], "title": "[Review] Code review", "fase": 5})
```

#### Criar ticket de Retro (um fixo)

```python
ticket_retro = evo.post("/api/tickets", {
    "title": f"[Retro] Retrospectiva — {feature_name}",
    "description": f"""## Objetivo
Executar retrospectiva completa da feature após Verify: o que funcionou, o que não funcionou, padrões a reutilizar e atualizações de memória propostas.

## Critérios de Aceitação
- Artefato [C]retro-{slug}.md gerado na feature folder
- Pelo menos 3 lições documentadas
- Memória atualizada com aprendizados relevantes

## Dependências
Tickets [Verify] e [Review] devem estar fechados antes de iniciar.

## Referências
Feature folder: {feature_folder}

## Instrução ao Agente — Ao Finalizar
```python
from dashboard.backend.sdk_client import evo
evo.post("/api/tickets/TICKET_ID/comments", {{
    "author": "agent:mirror-retro",
    "body": "✅ Retrospectiva concluída.\\n\\n**Artefato:** {feature_folder}[C]retro-{slug}.md\\n**Lições positivas:** X | **Negativas:** Y\\n**Memória atualizada:** sim | não\\n\\n<sumário>"
}})
```
""",
    "priority": "medium",
    "assignee_agent": "mirror-retro",
    "goal_id": goal_id
})
tickets_criados.append({"id": ticket_retro["id"], "title": "[Retro] Retrospectiva", "fase": 6})
```

---

### Step 8 — Resumo final

Apresente o resumo completo ao usuário:

```
## Feature "{feature_name}" planejada ✅

**Projeto:** {project_name}
**Feature folder:** {feature_folder}

### Artefatos gerados

| Arquivo | Etapa | Status |
|---------|-------|--------|
| [C]discovery-{slug}.md | Discovery | ✅ |
| [C]prd-{slug}.md | PRD | ✅ |
| [C]plan-{slug}.md | Plano | ✅ |
| [C]functional-model-{slug}.md | Modelagem funcional | ✅ / — (se não ativada) |
| ux/*.html | UX/UI | ✅ / — (se não ativada) |
| [C]architecture-{slug}.md | Arquitetura | ✅ / — (se não ativada) |

### Rastreamento (se tickets criados)
- Goal criado: "{feature_name}" (ID: {goal_id}) → /goals
- {N} tickets criados em /issues, todos linkados ao goal

### Tickets por fase (se criados)
| Fase | Ticket | Prioridade | Agente |
|------|--------|------------|--------|
| 4 - Build | [Build] Step 1... | urgent | @bolt-executor |
| 4 - Build | [Build] Step 2... | high | @bolt-executor |
| 5 - Verify | [Verify] Verificar critérios | high | @oath-verifier |
| 5 - Verify | [Review] Code review | high | @lens-reviewer |
| 6 - Retro | [Retro] Retrospectiva | medium | @mirror-retro |

### Ordem de execução sugerida
1. Execute os tickets [Build] em sequência (respeitando dependências)
2. Ao fechar todos os [Build], abra [Verify] e [Review] em paralelo
3. Ao fechar [Verify] e [Review], execute o [Retro]

### Próximos passos (se tickets não criados)
- **Implementar** → chame `@bolt-executor` com o `[C]plan-{slug}.md`
- **Criar tickets depois** → rode `/project-module-plan` com os artefatos gerados
- **Revisar arquitetura** → chame `@raven-critic` antes de codar
```

---

## Convenção de pastas

```
workspace/projects/{project_name}/features/{slug}/
├── [C]discovery-{slug}.md        ← Etapa 1 (Echo)
├── [C]prd-{slug}.md              ← Etapa 2 (Compass)
├── [C]plan-{slug}.md             ← Etapa 2 (Compass)
├── [C]functional-model-{slug}.md ← Etapa 3 (Compass) — se ativada
├── [C]architecture-{slug}.md     ← Etapa 5 (Apex)    — se ativada
└── ux/
    ├── ux-{tela1}.html           ← Etapa 4 (Canvas)  — se ativada
    └── ux-{tela2}.html
```

**Regra:** todos os artefatos ficam na feature folder do projeto correspondente. Nunca em `workspace/development/`.

---

## Anti-patterns

- **NUNCA** avançar para a próxima etapa sem checkpoint aprovado (modo guiado)
- **NUNCA** usar a pasta `workspace/development/` — sempre `workspace/projects/{project}/features/{slug}/`
- **NUNCA** inventar design system na etapa de UX — usar o do projeto ou tema neutro
- **NUNCA** pular a coleta inicial (Step 0) — `project_name` e `feature_name` são obrigatórios
- **NUNCA** executar todas as etapas se o usuário selecionou apenas algumas

## Pairs With

- `@echo-analyst` — Etapa 1 (Discovery)
- `@compass-planner` — Etapa 2 (PRD + Plano) e Etapa 3 (Modelagem funcional)
- `@canvas-designer` — Etapa 4 (UX/UI)
- `@apex-architect` — Etapa 5 (Arquitetura técnica)
- `@raven-critic` — revisão adversarial da arquitetura (pós-kickoff)
- `@bolt-executor` — implementação (após kickoff completo)
- `project-module-plan` — para materializar o resultado em Goals + Tickets rastreáveis
