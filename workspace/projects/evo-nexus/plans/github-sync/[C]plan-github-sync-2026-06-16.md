# [C] Plano — EvoNexus Tickets → GitHub Issues + Projects V2

**Data:** 2026-06-16
**Autor:** @compass-planner
**Escopo:** Sincronização unidirecional EvoNexus → GitHub Issues + Project #2 (Automacao-Software)
**Status:** Pronto para execução

---

## Visão geral

```
EvoNexus Ticket
  │
  ├── create_ticket() / update_ticket()
  │       └── enqueue_sync(ticket_id, event)  ← hook pós-commit [thread daemon]
  │
  ├── github_issues.py                        ← novo módulo
  │       ├── REST: create/update/close issue
  │       └── GraphQL: add/update item no Project V2 #2
  │
  ├── ticket_github_links                     ← tabela de mapeamento (nova)
  │
  ├── UI: dropdown "Sync GitHub" + badge link
  │
  └── ticket_janitor.py                       ← extensão para detecção 404
```

**Direção:** apenas EvoNexus → GitHub (push-only). Sem inbound, sem webhook.
**PAT:** `GITHUB_TOKEN` em `.env` (scopes `repo` + `project`).
**Repos alvo (12):** go-control-erp, go-control-platform, go-control-admin, go-control-auth,
go-control-account, go-control-sdk, go-control-app-template, go-payment-hub, go-message,
go-produtos, go-pessoas, go-cobranca (todos sob `Automacao-Software/`).

---

## Mapeamentos de estado

| EvoNexus status | GitHub state | state_reason | Labels aplicadas |
|-----------------|--------------|--------------|-----------------|
| open | open | — | — |
| in_progress | open | — | `status:in-progress` |
| blocked | open | — | `status:blocked` |
| review | open | — | `status:review` |
| resolved | closed | completed | — |
| closed | closed | not_planned | — |

| EvoNexus priority | GitHub label |
|-------------------|--------------|
| urgent | `priority:urgent` |
| high | `priority:high` |
| medium | `priority:medium` |
| low | `priority:low` |

---

## Fase 1 — Fundação

**Objetivo:** schema de banco + cliente GitHub reutilizável + labels bootstrap nos 12 repos.
**Dependências externas:** nenhuma (só `GITHUB_TOKEN` já existente).
**Pode ser entregue isoladamente e testada antes da Fase 2.**

---

### F1-1 · Migração de banco — `github_repo` + `ticket_github_links`

**Tipo:** `[CONSTRUIR NOVO]`
**Estimativa:** P (< 2h)

**Descrição:**
Adicionar coluna `github_repo TEXT` nullable na tabela `tickets` e criar a tabela
`ticket_github_links` de mapeamento. Usar a convenção de migração já existente no projeto
(SQLite `CREATE TABLE IF NOT EXISTS`, sem Alembic).

**Passos concretos:**

1. Abrir `dashboard/backend/models.py` e adicionar `github_repo` ao modelo `Ticket`:
   - Linha 810 (após `resolved_at`) inserir: `github_repo = db.Column(db.Text, nullable=True)`
   - Incluir `"github_repo": self.github_repo` no método `to_dict()` (linha 841).

2. Criar o modelo `TicketGithubLink` após `TicketActivity` (~linha 905):
   ```python
   class TicketGithubLink(db.Model):
       __tablename__ = "ticket_github_links"
       id = db.Column(db.String(36), primary_key=True)
       ticket_id = db.Column(db.String(36), db.ForeignKey("tickets.id", ondelete="CASCADE"),
                             nullable=False, unique=True)
       github_repo = db.Column(db.Text, nullable=False)   # ex: Automacao-Software/go-payment-hub
       issue_number = db.Column(db.Integer, nullable=True)
       issue_url = db.Column(db.Text, nullable=True)
       project_item_id = db.Column(db.Text, nullable=True)  # node_id do item no Project V2
       last_synced_at = db.Column(db.String(30), nullable=True)
       sync_error = db.Column(db.Text, nullable=True)
       created_at = db.Column(db.String(30), nullable=False)
       updated_at = db.Column(db.String(30), nullable=False)

       ticket = db.relationship("Ticket", backref=db.backref("github_link", uselist=False))

       def to_dict(self):
           return {
               "id": self.id,
               "ticket_id": self.ticket_id,
               "github_repo": self.github_repo,
               "issue_number": self.issue_number,
               "issue_url": self.issue_url,
               "project_item_id": self.project_item_id,
               "last_synced_at": self.last_synced_at,
               "sync_error": self.sync_error,
               "created_at": self.created_at,
               "updated_at": self.updated_at,
           }
   ```

3. Criar script de migração `dashboard/backend/migrations/add_github_sync.py`
   que executa `ALTER TABLE tickets ADD COLUMN github_repo TEXT` (idempotente com
   `PRAGMA table_info` como guard) e `CREATE TABLE IF NOT EXISTS ticket_github_links (...)`.

4. Registrar a migração no bootstrap do app (`app.py`) — adicionar chamada ao script
   de migração no bloco de inicialização do banco (padrão já existente para
   `with app.app_context(): db.create_all()`).

**Arquivos a modificar:**
- `dashboard/backend/models.py` — modelo `Ticket.github_repo` + modelo `TicketGithubLink`

**Arquivos a criar:**
- `dashboard/backend/migrations/add_github_sync.py`

**Critério de aceitação:**

```gherkin
Given o app reinicia após a migração
When executo: SELECT github_repo FROM tickets LIMIT 1
Then a coluna existe sem erro (resultado pode ser NULL)

Given o app reinicia após a migração
When executo: SELECT * FROM ticket_github_links LIMIT 1
Then a tabela existe sem erro (resultado pode ser vazio)

Given um ticket tem github_repo preenchido
When chamo GET /api/tickets/{id}
Then a resposta JSON inclui "github_repo": "<valor>"
```

**Dependências:** nenhuma

---

### F1-2 · Módulo `github_issues.py` — cliente REST + GraphQL

**Tipo:** `[CONSTRUIR NOVO]`
**Estimativa:** M (2–4h)

**Descrição:**
Novo módulo em `dashboard/backend/github_issues.py`. Reutiliza a infraestrutura HTTP
de `brain_repo/github_api.py` (`_headers`, `_get`, `_post`) e adiciona:
- Funções REST para issues (create, update, close, get)
- Funções GraphQL para Projects V2 (get_project_node_id, add_issue_to_project,
  update_project_item_status)
- Cache do `project_node_id` em variável de módulo (evita round-trip a cada sync)
- Função de alto nível `sync_ticket_to_github(ticket_id)` que orquestra tudo

**Estrutura do módulo:**

```
dashboard/backend/github_issues.py
  ├── _REPOS_ALLOWLIST          : set[str] — 12 repos válidos
  ├── _project_node_id_cache    : str | None
  ├── _headers(token)           : reutilizável
  ├── _get(url, token)          : reutilizável (copiar padrão de github_api.py)
  ├── _post(url, token, payload): reutilizável
  ├── _patch(url, token, payload): novo — para PATCH de issues
  ├── _graphql(query, variables): base GraphQL (POST /graphql)
  ├── get_project_node_id(org, project_number) → str | None
  ├── create_issue(repo, title, body, labels, assignees) → dict | None
  ├── update_issue(repo, issue_number, **fields) → dict | None
  ├── close_issue(repo, issue_number, state_reason) → dict | None
  ├── get_issue(repo, issue_number) → tuple[int, dict | None]
  ├── add_issue_to_project(project_node_id, issue_node_id) → str | None
  ├── update_project_item_status(project_node_id, item_id, field_id, value) → bool
  └── sync_ticket_to_github(ticket_id) → None   ← ponto de entrada principal
```

**Passos concretos:**

1. Criar o arquivo com as funções REST básicas.
   - `_patch`: mesmo padrão de `_post` mas `method="PATCH"`.
   - `create_issue(repo, title, body, labels, assignees)`: `POST /repos/{repo}/issues`
     com `{"title", "body", "labels", "assignees"}`.
   - `update_issue(repo, issue_number, **fields)`: `PATCH /repos/{repo}/issues/{number}`
     com só os campos presentes em `fields`.
   - `close_issue(repo, issue_number, state_reason)`: wrapper de `update_issue` com
     `state="closed"` e `state_reason`.
   - `get_issue(repo, issue_number)`: retorna `(status_code, body)` — status 404 é
     sinal para o janitor fechar o ticket.

2. Implementar bloco GraphQL.
   - `_graphql(query, variables)`: `POST https://api.github.com/graphql` com
     `{"query": ..., "variables": ...}`.
   - `get_project_node_id(org, project_number)`:
     ```graphql
     query($org: String!, $num: Int!) {
       organization(login: $org) {
         projectV2(number: $num) { id }
       }
     }
     ```
     Cachear resultado em `_project_node_id_cache`.
   - `add_issue_to_project(project_node_id, issue_node_id)`:
     ```graphql
     mutation($proj: ID!, $content: ID!) {
       addProjectV2ItemById(input: {projectId: $proj, contentId: $content}) {
         item { id }
       }
     }
     ```
     Retorna `item.id` (o `project_item_id` para a tabela de links).

3. Implementar `sync_ticket_to_github(ticket_id)`:
   - Carregar ticket + link existente do banco.
   - Se `ticket.github_repo` é NULL ou não está em `_REPOS_ALLOWLIST` → retornar.
   - Montar `labels = [f"priority:{ticket.priority}"] + STATUS_LABELS[ticket.status]`.
   - Se link não existe (CREATE): `create_issue(...)` → salvar `issue_number` + `issue_url`
     → `add_issue_to_project(...)` → salvar `project_item_id`.
   - Se link existe (UPDATE): `update_issue(...)` com title/body/labels/state atuais.
   - Persistir `last_synced_at = now`, `sync_error = None` (ou a mensagem de erro).
   - Todo erro é capturado, logado, e salvo em `sync_error` — nunca propaga para o request.

4. Definir `_REPOS_ALLOWLIST`:
   ```python
   _REPOS_ALLOWLIST = {
       "Automacao-Software/go-control-erp",
       "Automacao-Software/go-control-platform",
       "Automacao-Software/go-control-admin",
       "Automacao-Software/go-control-auth",
       "Automacao-Software/go-control-account",
       "Automacao-Software/go-control-sdk",
       "Automacao-Software/go-control-app-template",
       "Automacao-Software/go-payment-hub",
       "Automacao-Software/go-message",
       "Automacao-Software/go-produtos",
       "Automacao-Software/go-pessoas",
       "Automacao-Software/go-cobranca",
   }
   ```

**Arquivos a criar:**
- `dashboard/backend/github_issues.py`

**Critério de aceitação:**

```gherkin
Given GITHUB_TOKEN válido no ambiente
When chamo create_issue("Automacao-Software/go-payment-hub", "Teste", "corpo", [], ["eduardomrj"])
Then retorno é dict com "number" e "html_url" (verificar via API real ou mock)

Given project_number=2 e org="Automacao-Software"
When chamo get_project_node_id("Automacao-Software", 2)
Then retorno é string começando com "PVT_" (node_id do projeto)

Given issue criada no passo anterior
When chamo add_issue_to_project(project_node_id, issue_node_id)
Then retorno é string não-vazia (project_item_id)

Given ticket com github_repo="Automacao-Software/go-payment-hub" e status="in_progress"
When chamo sync_ticket_to_github(ticket_id)
Then TicketGithubLink é criado com issue_number preenchido e sync_error=None
```

**Dependências:** F1-1 (modelo `TicketGithubLink` deve existir)

---

### F1-3 · Bootstrap de labels nos 12 repos

**Tipo:** `[CONSTRUIR NOVO]`
**Estimativa:** P (< 2h)

**Descrição:**
Script one-shot que cria as labels de status e prioridade nos 12 repos da allowlist,
idempotente (ignora 422 "already exists"). Executa uma única vez no deploy inicial.

**Labels a criar:**

| Label | Cor |
|-------|-----|
| `status:in-progress` | `#0075ca` (azul) |
| `status:blocked` | `#d93f0b` (vermelho) |
| `status:review` | `#e4e669` (amarelo) |
| `priority:urgent` | `#b60205` (vermelho escuro) |
| `priority:high` | `#d93f0b` (laranja) |
| `priority:medium` | `#f9d0c4` (rosa claro) |
| `priority:low` | `#c2e0c6` (verde claro) |

**Passos concretos:**

1. Criar `dashboard/backend/scripts/bootstrap_github_labels.py`.
2. Para cada repo em `_REPOS_ALLOWLIST`:
   - `POST /repos/{repo}/labels` com `{"name", "color", "description"}`.
   - Status 201 → sucesso. Status 422 → já existe, ignorar.
   - Logar resultado por repo.
3. Adicionar ao `Makefile` (ou `ROUTINES.md`): `make github-labels` executa o script.

**Arquivos a criar:**
- `dashboard/backend/scripts/bootstrap_github_labels.py`

**Critério de aceitação:**

```gherkin
Given GITHUB_TOKEN válido
When executo: python bootstrap_github_labels.py
Then output mostra "OK" ou "already_exists" para cada label × repo (84 combinações = 7 labels × 12 repos)
And nenhuma linha mostra "ERROR" ou status ≥ 400 (exceto 422)

Given script executado duas vezes consecutivas
When executo a segunda vez
Then nenhum erro — idempotente
```

**Dependências:** nenhuma (independente do banco)

---

## Fase 2 — Sync Core

**Objetivo:** hook pós-save funcional + UI com dropdown e badge.
**Dependências:** Fase 1 completa.

---

### F2-1 · Hook pós-save em `tickets.py`

**Tipo:** `[EVOLUIR]`
**Estimativa:** M (2–4h)

**Descrição:**
Adicionar `github_repo` ao fluxo de create/update e disparar `enqueue_sync` em
thread daemon após o `db.session.commit()`. A thread nunca bloqueia o request —
falhas são silenciosas para o usuário (logadas no `sync_error` da tabela de links).

**Passos concretos:**

1. Em `create_ticket()` (linha 244):
   - Ler `github_repo = (data.get("github_repo") or "").strip() or None` junto com os outros campos.
   - Passar `github_repo=github_repo` ao construtor `Ticket(...)`.
   - Após `db.session.commit()` (linha 289), inserir:
     ```python
     if ticket.github_repo:
         _enqueue_github_sync(ticket.id, "created", current_app._get_current_object())
     ```

2. Em `update_ticket()` (linha 297):
   - Adicionar handler para `"github_repo"` nos campos patcháveis:
     ```python
     if "github_repo" in data:
         ticket.github_repo = (data["github_repo"] or "").strip() or None
         changes["github_repo"] = ticket.github_repo
     ```
   - Após `db.session.commit()` (linha 351), inserir:
     ```python
     if ticket.github_repo:
         _enqueue_github_sync(ticket.id, "updated", current_app._get_current_object())
     ```

3. Implementar `_enqueue_github_sync(ticket_id, event, app)` no topo do arquivo
   (ou em módulo auxiliar `github_sync_queue.py`):
   ```python
   def _enqueue_github_sync(ticket_id: str, event: str, app) -> None:
       """Dispara sync com GitHub em thread daemon. Nunca bloqueia o request."""
       def _run():
           try:
               with app.app_context():
                   from github_issues import sync_ticket_to_github
                   sync_ticket_to_github(ticket_id)
           except Exception as exc:
               import logging
               logging.getLogger(__name__).error(
                   "github sync failed for ticket %s (%s): %s", ticket_id, event, exc
               )
       t = threading.Thread(target=_run, daemon=True, name=f"gh-sync-{ticket_id[:8]}")
       t.start()
   ```

4. Garantir que `threading` já está importado no topo de `tickets.py`
   (verificar — pode já existir).

**Arquivos a modificar:**
- `dashboard/backend/routes/tickets.py` — funções `create_ticket` e `update_ticket`

**Critério de aceitação:**

```gherkin
Given GITHUB_TOKEN válido e ticket com github_repo preenchido
When faço POST /api/tickets com {"title": "Teste sync", "github_repo": "Automacao-Software/go-payment-hub"}
Then resposta HTTP é 201 (imediata — sem timeout)
And em até 10s: TicketGithubLink com issue_number ≠ NULL existe no banco

Given ticket já sincronizado
When faço PATCH /api/tickets/{id} com {"status": "in_progress"}
Then em até 10s: issue no GitHub tem label "status:in-progress" aplicada

Given ticket com github_repo preenchido
When o sync falha (token inválido simulado)
Then o request original retorna 201 normalmente (falha silenciosa para o usuário)
And TicketGithubLink.sync_error contém a mensagem de erro
```

**Dependências:** F1-1 (modelo), F1-2 (sync_ticket_to_github)

---

### F2-2 · API: expor `github_link` no payload de tickets

**Tipo:** `[EVOLUIR]`
**Estimativa:** P (< 2h)

**Descrição:**
O frontend precisa saber se o ticket está sincronizado (para exibir badge e ícone).
Incluir dados do link no payload do `GET /api/tickets/{id}` e na listagem.

**Passos concretos:**

1. No `to_dict()` do modelo `Ticket` (`models.py` linha 815), adicionar:
   ```python
   "github_link": self.github_link.to_dict() if self.github_link else None,
   ```
   (o relationship `github_link` foi definido no `TicketGithubLink` com `uselist=False`).

2. Em `GET /api/tickets` (listagem), garantir que a query carrega o relacionamento
   com `joinedload(Ticket.github_link)` para evitar N+1.
   - Localizar a query de listagem em `routes/tickets.py` e adicionar o eager load.

3. Criar endpoint `GET /api/tickets/{id}/github-link` para consulta direta do link
   (útil para polling pós-create enquanto o sync está em background):
   ```python
   @bp.route("/api/tickets/<string:ticket_id>/github-link", methods=["GET"])
   def get_ticket_github_link(ticket_id: str):
       ...
   ```

**Arquivos a modificar:**
- `dashboard/backend/models.py` — `Ticket.to_dict()`
- `dashboard/backend/routes/tickets.py` — listagem + novo endpoint

**Critério de aceitação:**

```gherkin
Given ticket sincronizado com GitHub
When faço GET /api/tickets/{id}
Then resposta inclui "github_link": {"issue_number": N, "issue_url": "https://...", ...}

Given ticket sem sync
When faço GET /api/tickets/{id}
Then resposta inclui "github_link": null

Given ticket recém-criado (sync em andamento)
When faço GET /api/tickets/{id}/github-link imediatamente
Then resposta é {"github_link": null} sem erro 500
```

**Dependências:** F1-1 (modelo), F2-1 (sync popula a tabela)

---

### F2-3 · UI — dropdown "Sync GitHub" + badge + ícone na listagem

**Tipo:** `[CONSTRUIR NOVO]`
**Estimativa:** M (2–4h)

**Descrição:**
Adicionar interação de GitHub ao formulário de criação/edição de tickets e ao detalhe.
Usar o design system existente do dashboard (PrimeReact + dark theme).

**Componentes:**

1. **Formulário de criação/edição** — campo dropdown:
   - Label: "Sincronizar com GitHub"
   - Opções: `"(nenhum)"` + os 12 repos (exibir só o nome curto: `go-payment-hub`)
   - Valor enviado: `null` ou `"Automacao-Software/go-payment-hub"`
   - Posicionar após o campo "Projeto" no formulário

2. **Detalhe do ticket** — badge quando sincronizado:
   ```
   [GitHub ↗]  go-payment-hub #42
   ```
   - Link para `issue_url` (abre em nova aba)
   - Exibir somente quando `github_link.issue_number` não é null
   - Se `sync_error` não é null: badge em vermelho com tooltip mostrando o erro

3. **Listagem de tickets** — ícone GitHub:
   - Quando `github_repo IS NOT NULL`: exibir ícone GitHub à direita do título
   - Tooltip: nome do repo + número da issue (se já sincronizado)

**Passos concretos:**

1. Criar constante `GITHUB_REPOS` no frontend com os 12 repos.
2. Adicionar `githubRepo` ao estado do formulário de ticket (TicketModal ou equivalente).
3. Implementar `GitHubBadge` — componente pequeno que recebe `github_link` e renderiza
   o link ou o estado de erro.
4. Na listagem, adicionar coluna/ícone condicional baseado em `github_repo != null`.
5. Polling leve (3 tentativas × 3s) em `GET /api/tickets/{id}/github-link`
   após criação/edição para mostrar badge assim que o sync completar.

**Arquivos a criar/modificar:**
- Frontend — componente de formulário de ticket (localizar o arquivo atual)
- Frontend — componente de detalhe de ticket
- Frontend — listagem de tickets

> **Nota para Bolt:** identificar os arquivos exatos do frontend antes de iniciar
> (rodar `find /home/evonexus/evo-nexus/dashboard/frontend/src -name "*ticket*" -o -name "*Ticket*"`).

**Critério de aceitação:**

```gherkin
Given formulário de criação de ticket aberto
When seleciono "go-payment-hub" no dropdown "Sincronizar com GitHub"
And submeto o formulário
Then o campo github_repo aparece no payload do POST

Given ticket sincronizado com issue_number=42
When abro o detalhe do ticket
Then vejo badge "[GitHub ↗] go-payment-hub #42" clicável

Given ticket com sync_error não-nulo
When abro o detalhe do ticket
Then vejo badge vermelho "Sync erro" com tooltip mostrando a mensagem de erro

Given listagem de tickets com mix de tickets com e sem github_repo
When visualizo a lista
Then tickets com github_repo têm ícone GitHub visível; os demais não
```

**Dependências:** F2-1, F2-2

---

## Fase 3 — Completude

**Objetivo:** retroativo, detecção de deleção, observabilidade.
**Dependências:** Fase 2 completa.

---

### F3-1 · Sync retroativo no primeiro deploy

**Tipo:** `[CONSTRUIR NOVO]`
**Estimativa:** M (2–4h)

**Descrição:**
Script one-shot que sincroniza tickets existentes que tenham `github_repo IS NOT NULL`
e ainda não tenham um `TicketGithubLink`. Executa no primeiro deploy — depois disso
o hook em tempo real mantém tudo atualizado.

A lógica de seleção: tickets onde `github_repo IS NOT NULL` e `id NOT IN (SELECT ticket_id FROM ticket_github_links)`.

**Passos concretos:**

1. Criar `dashboard/backend/scripts/backfill_github_sync.py`:
   ```python
   # Uso: python backfill_github_sync.py [--dry-run]
   # Executa dentro do Flask app context
   ```
   - Buscar todos os tickets elegíveis (query acima).
   - Para cada ticket, chamar `sync_ticket_to_github(ticket_id)`.
   - Rate-limit: aguardar 0.5s entre chamadas para respeitar limite do GitHub (5000 req/h).
   - Logar: `[OK] ticket_id → issue#N` ou `[ERR] ticket_id → mensagem`.
   - `--dry-run`: listar tickets sem sincronizar.

2. Adicionar ao Makefile: `make github-backfill`.

3. Documentar em `ROUTINES.md` como etapa de deploy único.

**Arquivos a criar:**
- `dashboard/backend/scripts/backfill_github_sync.py`

**Critério de aceitação:**

```gherkin
Given 3 tickets com github_repo preenchido e sem TicketGithubLink
When executo: python backfill_github_sync.py
Then output mostra 3 linhas "[OK]"
And ticket_github_links tem 3 registros novos com issue_number preenchido

Given o mesmo contexto
When executo: python backfill_github_sync.py --dry-run
Then output lista os 3 tickets mas não cria nenhum link
And ticket_github_links permanece vazio

Given backfill já executado (links existem)
When executo novamente
Then output mostra "0 tickets elegíveis" — idempotente
```

**Dependências:** F1-2 (`sync_ticket_to_github`), F2-1 (labels existem)

---

### F3-2 · Detecção de deleção de issue — extensão do janitor

**Tipo:** `[EVOLUIR]`
**Estimativa:** M (2–4h)

**Descrição:**
Estender `ticket_janitor.py` com uma rotina que varre `ticket_github_links` não
sincronizados há mais de 1h, chama `get_issue()` e, se receber 404, fecha o
ticket correspondente no EvoNexus.

**Passos concretos:**

1. Em `ticket_janitor.py`, criar função `check_deleted_github_issues(app) -> int`:
   ```python
   def check_deleted_github_issues(app) -> int:
       """Fecha tickets cujas issues foram deletadas no GitHub (404).
       Retorna o número de tickets fechados."""
   ```
   - Query: links com `last_synced_at < now - 1h` ou `last_synced_at IS NULL`
     e tickets com `status NOT IN ('resolved', 'closed')`.
   - Para cada link: `status, body = get_issue(github_repo, issue_number)`.
   - Se `status == 404`:
     - `PATCH /api/tickets/{ticket_id}` com `{"status": "closed"}` via `EvoClient`
       (importar `sdk_client.evo`).
     - Logar atividade: `actor="system:github-janitor"`, `action="auto_closed_issue_deleted"`.
   - Se `status == 200`: atualizar `last_synced_at = now`.
   - Se `status == 0` (network error): ignorar, logar warning.

2. Registrar a função no `_janitor_loop` (linha 83), após o bloco de `release_expired_locks`:
   ```python
   try:
       check_deleted_github_issues(app)
   except Exception as exc:
       print(f"[ticket_janitor] github-check error: {exc}", flush=True)
   ```

3. Adicionar rate-limit interno: no máximo 50 issues verificadas por ciclo do janitor
   (evitar burst de 300 requests se muitos links acumularem).

**Arquivos a modificar:**
- `dashboard/backend/ticket_janitor.py` — nova função + registro no loop

**Critério de aceitação:**

```gherkin
Given ticket sincronizado com issue_number válida
When issue é deletada manualmente no GitHub
And o janitor roda (aguardar até 5min ou triggerizar manualmente)
Then ticket.status = "closed" no EvoNexus
And TicketActivity inclui registro actor="system:github-janitor", action="auto_closed_issue_deleted"

Given ticket sincronizado com issue_number válida (issue existe)
When janitor roda
Then ticket permanece no status original (sem alteração)
And TicketGithubLink.last_synced_at é atualizado

Given falha de rede (GitHub indisponível)
When janitor roda
Then nenhum ticket é fechado incorretamente
And log mostra warning — sem exceção propagada
```

**Dependências:** F1-2 (`get_issue`), F2-1 (links existem), F2-2 (`sdk_client.evo`)

---

### F3-3 · Observabilidade — endpoint de status e logs

**Tipo:** `[CONSTRUIR NOVO]`
**Estimativa:** P (< 2h)

**Descrição:**
Endpoint de status para diagnóstico rápido da saúde da sincronização GitHub,
sem precisar abrir o banco diretamente.

**Passos concretos:**

1. Criar `GET /api/github-sync/status`:
   ```json
   {
     "total_linked": 42,
     "sync_errors": 3,
     "last_sync_at": "2026-06-16T14:30:00Z",
     "oldest_pending_sync": "2026-06-15T10:00:00Z",
     "project_node_id_cached": true
   }
   ```
   - Query: `COUNT(*)`, `COUNT(*) WHERE sync_error IS NOT NULL`,
     `MAX(last_synced_at)`, `MIN(last_synced_at) WHERE last_synced_at IS NULL OR last_synced_at < now - 1h`.

2. Criar `GET /api/github-sync/errors`:
   ```json
   [
     {"ticket_id": "...", "github_repo": "...", "sync_error": "...", "last_synced_at": "..."},
     ...
   ]
   ```
   Limitado a 50 registros com `sync_error IS NOT NULL`.

3. Criar `POST /api/github-sync/retry/{ticket_id}`:
   - Força re-sync imediato de um ticket específico (útil para corrigir erros manualmente).
   - Chama `_enqueue_github_sync(ticket_id, "retry", app)`.

4. Registrar as rotas em `app.py` (ou no blueprint de tickets).

**Arquivos a criar/modificar:**
- `dashboard/backend/routes/github_sync.py` — novo blueprint
- `dashboard/backend/app.py` — registrar blueprint

**Critério de aceitação:**

```gherkin
Given sistema com 10 tickets sincronizados e 2 com erros
When faço GET /api/github-sync/status
Then resposta contém {"total_linked": 10, "sync_errors": 2}

Given ticket com sync_error preenchido
When faço POST /api/github-sync/retry/{ticket_id}
Then resposta é 202 {"queued": true}
And em até 10s: sync_error é NULL (se token válido)

Given nenhum ticket sincronizado
When faço GET /api/github-sync/errors
Then resposta é []
```

**Dependências:** F1-1 (modelo), F2-1 (sync em operação)

---

## Resumo de esforço

| ID | Item | Tipo | Fase | Estimativa |
|----|------|------|------|------------|
| F1-1 | Migração banco (github_repo + ticket_github_links) | CONSTRUIR NOVO | 1 | P |
| F1-2 | Módulo github_issues.py (REST + GraphQL) | CONSTRUIR NOVO | 1 | M |
| F1-3 | Bootstrap de labels nos 12 repos | CONSTRUIR NOVO | 1 | P |
| F2-1 | Hook pós-save em tickets.py | EVOLUIR | 2 | M |
| F2-2 | API: expor github_link no payload | EVOLUIR | 2 | P |
| F2-3 | UI: dropdown + badge + ícone listagem | CONSTRUIR NOVO | 2 | M |
| F3-1 | Sync retroativo (backfill) | CONSTRUIR NOVO | 3 | M |
| F3-2 | Detecção deleção — extensão janitor | EVOLUIR | 3 | M |
| F3-3 | Observabilidade (status + errors + retry) | CONSTRUIR NOVO | 3 | P |

**Total estimado:** ~3P + ~5M = ~3h (P) + ~12h (M) = **~15h** de desenvolvimento

---

## Ordem de execução recomendada

```
F1-1 → F1-2 (depende de F1-1)
F1-3 (paralelo com F1-2)
   ↓
F2-1 (depende de F1-1 + F1-2)
F2-2 (depende de F1-1 + F2-1 em paralelo)
   ↓
F2-3 (depende de F2-1 + F2-2)
   ↓
F3-1 (depende de F1-2 + F2-1, pode ser após F2-1)
F3-2 (depende de F1-2 + F2-1)
F3-3 (depende de F1-1 + F2-1, pode ser paralelo com F3-1/F3-2)
```

---

## Arquivos-chave de referência

| Arquivo | Relevância |
|---------|-----------|
| `dashboard/backend/models.py:770` | Modelo Ticket — adicionar `github_repo` |
| `dashboard/backend/models.py:905` | Inserir modelo `TicketGithubLink` após `TicketActivity` |
| `dashboard/backend/routes/tickets.py:244` | `create_ticket()` — hook pós-commit |
| `dashboard/backend/routes/tickets.py:297` | `update_ticket()` — hook pós-commit |
| `dashboard/backend/ticket_janitor.py:83` | `_janitor_loop` — inserir `check_deleted_github_issues` |
| `dashboard/backend/brain_repo/github_api.py` | Base HTTP reutilizável (`_headers`, `_get`, `_post`) |
| `dashboard/backend/sdk_client.py` | EvoClient — para chamadas internas do janitor |

---

## Riscos e mitigações

| Risco | Probabilidade | Mitigação |
|-------|--------------|-----------|
| Rate limit GitHub (5000 req/h) | Média | Sleep 0.5s no backfill; janitor limita a 50 checks/ciclo |
| Project V2 node_id muda | Baixa | Cache invalidável via restart; endpoint retry permite forçar |
| Thread daemon perde contexto Flask | Baixa | `_enqueue_github_sync` usa `app._get_current_object()` — mesmo padrão do janitor existente |
| Repo não está na allowlist | Média | `sync_ticket_to_github` retorna silenciosamente; UI filtra dropdown |
| `threading` não importado em `tickets.py` | Baixa | Verificar import antes — já pode existir (verificar linha ~1–30) |
