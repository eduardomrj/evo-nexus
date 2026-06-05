---
name: project-module-plan
description: "Planeja um novo módulo de um projeto de sistema executando as fases 1-6 do Engineering Layer (Discovery, Planning, Solutioning, Build, Verify, Retro) e materializa o resultado em Goals e Tickets rastreáveis no dashboard. Use quando: 'planejar módulo', 'novo módulo para o projeto', 'project-module-plan', 'quero planejar um módulo'."
---

# Project Module Plan

Skill que orquestra o planejamento completo de um novo módulo de sistema, cobrindo todas as 6 fases do Engineering Layer (Discovery, Planning, Solutioning, Build, Verify, Retro) e materializando o resultado como Goal + Tickets rastreáveis no dashboard — incluindo tickets de implementação (Fase 4), verificação (Fase 5) e retrospectiva (Fase 6).

## Quando Usar

- "quero planejar um novo módulo para o projeto X"
- "vamos refinar os requisitos do módulo Y"
- "project-module-plan"
- Início de qualquer módulo grande que precisa de discovery, PRD e arquitetura antes de codar

## Quando NÃO Usar

- Pequenas features ou bugs — use diretamente `@bolt-executor` com um plano simples
- Quando o PRD já existe e você só quer gerar tickets — use `create-ticket` diretamente
- Quando o módulo já tem architecture doc — pule para a Fase 4 (Build)

## Inputs

- `project_name` (obrigatório) — nome do projeto ao qual o módulo pertence
- `module_name` (obrigatório) — nome do módulo a ser planejado
- Demais informações coletadas via entrevista interativa no Step 1

## Workflow

### Step 1 — Coleta de contexto (entrevista)

Antes de qualquer delegação, conduza uma entrevista com o usuário. Faça as perguntas abaixo em bloco único (não uma por vez):

```
Para planejar o módulo "{module_name}" do projeto "{project_name}", preciso entender:

1. Qual é o objetivo principal desse módulo? O que ele resolve ou entrega?
2. Quais são as regras de negócio mais importantes que ele deve seguir?
3. Existe alguma dependência com outros módulos ou sistemas externos?
4. Quais são as restrições técnicas ou de prazo?
5. Tem algum comportamento que o módulo NÃO deve ter? (anti-requisitos)
6. Qual é o contexto atual do projeto — stack, padrões, decisões arquiteturais já tomadas?
```

Aguarde a resposta completa. Se alguma resposta for vaga ou incompleta, faça uma rodada de follow-up antes de avançar.

Defina o slug do módulo: `{project_name}-{module_name}` em kebab-case.
Feature folder: `workspace/development/features/{slug}/`

### Step 2 — Fase 1: Discovery (@echo-analyst)

Invoque `@echo-analyst` com um briefing completo contendo:
- Contexto do projeto e do módulo
- Todas as respostas da entrevista do Step 1
- Instrução para gerar `[C]discovery-{module_name}.md` em `workspace/development/features/{slug}/`
- Instrução para identificar: requisitos não óbvios, regras de negócio implícitas, riscos, dependências, critérios de aceitação em aberto

Após o retorno do Echo, apresente ao usuário um resumo dos principais achados e pergunte:
> "O Echo identificou esses pontos. Tem algo a acrescentar ou corrigir antes de partirmos para o PRD?"

Aguarde confirmação.

### Step 3 — Fase 2: Planning (@compass-planner)

Invoque `@compass-planner` com:
- O arquivo `[C]discovery-{module_name}.md` gerado pelo Echo
- Contexto completo do projeto
- Instrução para gerar na feature folder:
  - `[C]prd-{module_name}.md` — o quê e por quê, com critérios de aceitação em Given/When/Then
  - `[C]plan-{module_name}.md` — 3-6 steps executáveis com: título, descrição, agente responsável, dependências, riscos e critérios de aceitação de cada step

Após o retorno do Compass, apresente o plano ao usuário e solicite aprovação explícita:
> "Plano gerado com X steps. Você aprova para seguirmos para a arquitetura? (responda 'sim' ou aponte o que ajustar)"

**NÃO avance para o Step 4 sem aprovação explícita.**

### Step 4 — Fase 3: Solutioning (@apex-architect) [OBRIGATÓRIO]

Esta fase nunca pode ser pulada.

Invoque `@apex-architect` com:
- `[C]prd-{module_name}.md`
- `[C]plan-{module_name}.md`
- Contexto do projeto (stack, padrões existentes)
- Instrução para gerar `[C]architecture-{module_name}.md` em formato ADR com: Decisão, Drivers, Alternativas consideradas, Consequências, Riscos arquiteturais, Follow-ups

Após o retorno do Apex, apresente ao usuário os pontos arquiteturais principais:
> "Arquitetura definida. Pontos principais: [resumo em 3-5 bullets]. Posso seguir para materializar em Goals e Tickets?"

Aguarde confirmação.

### Step 5 — Criar Goal no dashboard

Leia o `[C]plan-{module_name}.md` e conte o número de steps (= número de tasks).

Use o EvoClient SDK para criar o Goal:

```python
from dashboard.backend.sdk_client import evo

# Buscar ou criar projeto vinculado
# O goal representa o módulo completo
goal = evo.post("/api/goals", {
    "title": "{module_name}",
    "description": "Módulo planejado via project-module-plan. PRD: workspace/development/features/{slug}/[C]prd-{module_name}.md",
    "metric_type": "count",
    "target_value": <número_de_steps>,
    "current_value": 0,
    "status": "active"
})
goal_id = goal["id"]
```

Se a API de goals exigir `project_id`, busque o projeto pelo nome (`GET /api/projects?name={project_name}`) e vincule. Se não existir, crie o projeto antes.

### Step 6 — Criar Tickets no dashboard

Crie tickets para todas as 6 fases. Divida em três blocos.

> **Padrão obrigatório — comentário de resultado:**
> Todo ticket deve incluir na description a instrução para o agente responsável postar um comentário ao finalizar. Use o bloco abaixo em todos os tickets:
>
> ```
> ## Instrução ao Agente — Ao Finalizar
> Ao concluir este ticket, poste um comentário via API com o resultado:
>
> POST /api/tickets/{ticket_id}/comments
> {
>   "author": "agent:{seu-slug}",
>   "body": "✅ {fase} concluída.\n\n**Resultado:** {resumo do que foi feito}\n**Artefato:** {caminho do arquivo gerado, se houver}\n**Commits:** {hashes se aplicável}\n**Status:** PASS | FAIL | INCOMPLETE\n\n{observações relevantes}"
> }
>
> Use o EvoClient SDK: evo.post(f"/api/tickets/{ticket_id}/comments", {...})
> ```

#### Bloco A — Fase 4: Build (um ticket por step do plano)

```python
from dashboard.backend.sdk_client import evo

priority_map = {1: "urgent", 2: "high", 3: "high", 4: "medium", 5: "medium", 6: "low"}

tickets_criados = []
for i, step in enumerate(steps, start=1):
    ticket = evo.post("/api/tickets", {
        "title": f"[Build] {step['title']}",
        "description": f"""## Contexto
{step["description"]}

## Critérios de Aceitação
{step["acceptance_criteria"]}

## Agente Responsável
{step["agent"]}

## Dependências
{step["dependencies"]}

## Riscos
{step["risks"]}

---
Fase: 4 - Build | Módulo: {module_name} | Projeto: {project_name}
PRD: workspace/development/features/{slug}/[C]prd-{module_name}.md
Arquitetura: workspace/development/features/{slug}/[C]architecture-{module_name}.md

## Instrução ao Agente — Ao Finalizar
Ao concluir este ticket, poste um comentário com o resultado usando o EvoClient SDK:

```python
from dashboard.backend.sdk_client import evo
evo.post("/api/tickets/TICKET_ID/comments", {{
    "author": "agent:bolt-executor",
    "body": "✅ Build concluído.\\n\\n**Resultado:** <resumo do que foi implementado>\\n**Commits:** <hashes>\\n**Arquivos alterados:** <lista>\\n**Status:** PASS | FAIL\\n\\n<observações>"
}})
```
""",
        "priority": priority_map.get(i, "medium"),
        "assignee_agent": step["agent"],
        "goal_id": goal_id,
        "source_agent": "project-module-plan",
        "source_session_id": "<session_id_atual>"
    })
    tickets_criados.append({"id": ticket["id"], "title": f"[Build] {step['title']}", "fase": 4})
```

#### Bloco B — Fase 5: Verify (dois tickets fixos)

```python
# Ticket 1 — Verificação de critérios de aceitação
ticket_oath = evo.post("/api/tickets", {
    "title": f"[Verify] Verificar critérios de aceitação — {module_name}",
    "description": f"""## Objetivo
Verificar que todos os critérios de aceitação definidos no PRD foram atendidos com evidência real (output de testes, build status, screenshots).

## Critérios de Aceitação
- Todos os Given/When/Then do PRD mapeados para evidência concreta
- Build passando sem erros
- Nenhum "should work" sem prova — apenas output real

## Agente Responsável
@oath-verifier

## Dependências
Todos os tickets de [Build] devem estar fechados antes de iniciar.

## Referências
PRD: workspace/development/features/{slug}/[C]prd-{module_name}.md
Plano: workspace/development/features/{slug}/[C]plan-{module_name}.md

---
Fase: 5 - Verify | Módulo: {module_name} | Projeto: {project_name}

## Instrução ao Agente — Ao Finalizar
Ao concluir, poste um comentário com o resultado:

```python
from dashboard.backend.sdk_client import evo
evo.post("/api/tickets/TICKET_ID/comments", {{
    "author": "agent:oath-verifier",
    "body": "✅ Verificação concluída.\\n\\n**Artefato:** workspace/development/features/{slug}/[C]verification-{module_name}.md\\n**Critérios verificados:** X/Y\\n**Status:** PASS | FAIL | INCOMPLETE\\n\\n<sumário das evidências>"
}})
```
""",
    "priority": "high",
    "assignee_agent": "oath-verifier",
    "goal_id": goal_id,
    "source_agent": "project-module-plan",
    "source_session_id": "<session_id_atual>"
})
tickets_criados.append({"id": ticket_oath["id"], "title": "[Verify] Verificar critérios de aceitação", "fase": 5})

# Ticket 2 — Code review
ticket_lens = evo.post("/api/tickets", {
    "title": f"[Review] Code review — {module_name}",
    "description": f"""## Objetivo
Realizar code review em 2 etapas: (1) conformidade com spec/PRD e (2) qualidade de código (OWASP, SOLID, lógica).

## Critérios de Aceitação
- Nenhum item CRITICAL ou HIGH sem resolução documentada
- Conformidade com todos os critérios do PRD verificada
- Issues MEDIUM e LOW registradas para acompanhamento

## Agente Responsável
@lens-reviewer

## Dependências
Tickets de [Build] devem estar fechados antes de iniciar.

## Referências
PRD: workspace/development/features/{slug}/[C]prd-{module_name}.md
Arquitetura: workspace/development/features/{slug}/[C]architecture-{module_name}.md

---
Fase: 5 - Verify | Módulo: {module_name} | Projeto: {project_name}

## Instrução ao Agente — Ao Finalizar
Ao concluir, poste um comentário com o resultado:

```python
from dashboard.backend.sdk_client import evo
evo.post("/api/tickets/TICKET_ID/comments", {{
    "author": "agent:lens-reviewer",
    "body": "✅ Code review concluído.\\n\\n**Artefato:** workspace/development/features/{slug}/[C]code-review-{module_name}.md\\n**CRITICAL:** X issues\\n**HIGH:** Y issues\\n**MEDIUM/LOW:** Z issues\\n**Veredicto:** SAFE | MONITOR | HOLD\\n\\n<sumário dos principais achados>"
}})
```
""",
    "priority": "high",
    "assignee_agent": "lens-reviewer",
    "goal_id": goal_id,
    "source_agent": "project-module-plan",
    "source_session_id": "<session_id_atual>"
})
tickets_criados.append({"id": ticket_lens["id"], "title": "[Review] Code review", "fase": 5})
```

#### Bloco C — Fase 6: Retro (um ticket fixo)

```python
ticket_retro = evo.post("/api/tickets", {
    "title": f"[Retro] Retrospectiva — {module_name}",
    "description": f"""## Objetivo
Executar retrospectiva completa do módulo após Verify: o que funcionou, o que não funcionou, padrões a reutilizar, padrões a evitar, atualizações de memória propostas.

## Critérios de Aceitação
- Artefato [C]retro-{module_name}.md gerado na feature folder
- Pelo menos 3 lições documentadas (positivas ou negativas)
- Memória atualizada com aprendizados relevantes para sessões futuras

## Agente Responsável
@mirror-retro

## Dependências
Tickets [Verify] e [Review] devem estar fechados antes de iniciar.

## Referências
Feature folder completa: workspace/development/features/{slug}/

---
Fase: 6 - Retro | Módulo: {module_name} | Projeto: {project_name}

## Instrução ao Agente — Ao Finalizar
Ao concluir, poste um comentário com o resultado:

```python
from dashboard.backend.sdk_client import evo
evo.post("/api/tickets/TICKET_ID/comments", {{
    "author": "agent:mirror-retro",
    "body": "✅ Retrospectiva concluída.\\n\\n**Artefato:** workspace/development/features/{slug}/[C]retro-{module_name}.md\\n**Lições positivas:** X\\n**Lições negativas:** Y\\n**Memória atualizada:** sim | não\\n\\n<sumário das principais lições>"
}})
```
""",
    "priority": "medium",
    "assignee_agent": "mirror-retro",
    "goal_id": goal_id,
    "source_agent": "project-module-plan",
    "source_session_id": "<session_id_atual>"
})
tickets_criados.append({"id": ticket_retro["id"], "title": "[Retro] Retrospectiva", "fase": 6})
```

### Step 7 — Resumo final

Apresente ao usuário:

```
## Módulo "{module_name}" planejado com sucesso

**Projeto:** {project_name}
**Feature folder:** workspace/development/features/{slug}/

### Artefatos gerados (Fases 1-3)
- [C]discovery-{module_name}.md — análise de requisitos e gaps
- [C]prd-{module_name}.md — requisitos e critérios de aceitação
- [C]plan-{module_name}.md — {X} steps executáveis
- [C]architecture-{module_name}.md — decisões arquiteturais (ADR)

### Rastreamento
- Goal criado: "{module_name}" (ID: {goal_id}) → /goals
- {N} tickets criados em /issues, todos linkados ao goal

### Tickets por fase
| Fase | Ticket | Prioridade | Agente |
|------|--------|------------|--------|
| 4 - Build | [Build] Step 1... | urgent | @bolt-executor |
| 4 - Build | [Build] Step 2... | high   | @bolt-executor |
| ...  | ...    | ...        | ...    |
| 5 - Verify | [Verify] Verificar critérios | high | @oath-verifier |
| 5 - Verify | [Review] Code review         | high | @lens-reviewer |
| 6 - Retro  | [Retro] Retrospectiva        | medium | @mirror-retro |

### Ordem de execução sugerida
1. Execute os tickets [Build] em sequência (respeitando dependências)
2. Ao fechar todos os [Build], abra os [Verify] e [Review] em paralelo
3. Ao fechar [Verify] e [Review], execute o [Retro]

### Próximos passos
- Revise os tickets em /issues
- Quando pronto, inicie a Fase 4 com @bolt-executor no ticket [Build] de prioridade urgent
```

## Output

- Feature folder `workspace/development/features/{slug}/` com 4 artefatos (`[C]discovery`, `[C]prd`, `[C]plan`, `[C]architecture`)
- 1 Goal criado em `/goals` com metric_type `count` e target = total de tickets gerados
- N tickets de **Fase 4 (Build)** — um por step do plano, assignee derivado do agente indicado
- 2 tickets fixos de **Fase 5 (Verify)** — `@oath-verifier` e `@lens-reviewer`
- 1 ticket fixo de **Fase 6 (Retro)** — `@mirror-retro`
- Todos os tickets linkados ao goal, com descrição completa e autocontida
- **Cada ticket instrui o agente a postar comentário de resultado ao finalizar** — visível em `/issues/{id}` na timeline

### Como acompanhar o resultado de cada ticket

Acesse `/issues/{ticket_id}` — a timeline mostra:
- Mudanças de status (`open` → `in_progress` → `resolved`)
- **Comentário do agente ao finalizar** com: resumo do que foi feito, caminho do artefato gerado, commits (se Build), veredicto (se Verify/Review), lições (se Retro)

Acesse `/goals` para ver o progresso agregado do módulo em % conforme tickets fecham.

## Anti-patterns

- **NUNCA** pular a Fase 3 (arquitetura com Apex) — ela é obrigatória
- **NUNCA** avançar da Fase 2 para a Fase 3 sem aprovação explícita do usuário
- **NUNCA** usar curl manual para criar goals ou tickets — sempre usar EvoClient SDK
- **NUNCA** criar tickets sem a seção "Instrução ao Agente — Ao Finalizar" — ela é o que fecha o loop de visibilidade
- **NUNCA** criar tickets genéricos sem descrição completa — cada ticket deve ser autocontido
- **NUNCA** criar o Goal antes de ter o número exato de steps do plano
- **NUNCA** continuar se `project_name` ou `module_name` não forem informados

## Pairs With

- `@echo-analyst` — Fase 1 (Discovery)
- `@compass-planner` — Fase 2 (Planning)
- `@apex-architect` — Fase 3 (Solutioning)
- `@bolt-executor` — Fase 4 (Build), etapa seguinte após este skill
- `@oath-verifier` — Fase 5 (Verify), para fechar o ciclo
- `create-ticket` — para adicionar tickets avulsos ao goal depois
