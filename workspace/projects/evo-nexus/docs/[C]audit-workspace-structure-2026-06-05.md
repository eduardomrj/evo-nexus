# AUDIT: workspace/projects/ — Estrutura Fora de Conformidade

**Data:** 2026-06-05  
**Executor:** Scout  
**Escopo:** Verificação de conformidade com `.claude/rules/go-control-doc-structure.md` e convenções de projeto

---

## Resumo Executivo

- **Total de projetos auditados:** 6
- **Projetos com problemas:** 1 (go-control-erp)
- **Problemas identificados:** 6 categorias
- **Arquivos fora do lugar:** 40+ (12 .md soltos + 2 pastas ux + 15+ symlinks duplicados)
- **Risco:** Alto — confusão entre source-of-truth (evo-projects vs workspace)

---

## Estrutura Esperada (Conforme Convenção)

```
workspace/projects/{projeto}/
  features/{slug}/              ← 1 nível de profundidade (symlinks)
  plans/{slug}/                 ← planos multi-fase isolados
  docs/                         ← backlog, glossário, brainstorm global
  architecture/                 ← ADRs standalone (opcional)
  reviews/                      ← reviews standalone (opcional)
  verifications/                ← verifications standalone (opcional)
  debug/                        ← traces (opcional)
  manuais/                      ← técnico, operacional (opcional)
  ux/                           ← mockups HTML globais (opcional)
  INDEX.md                      ← catálogo navegável
```

**Regra crítica para `go-control-erp`:**
- **Físico** → `/home/evonexus/evo-projects/go-control-erp/features/{slug}/`
- **Acesso** → `/home/evonexus/evo-nexus/workspace/projects/go-control-erp/features/{slug}/` (symlink)

Nunca:
- ❌ Criar .md solto em `workspace/projects/go-control-erp/{nome}/`
- ❌ Ter pasta paralela a `features/` com artefatos dentro

---

## Problemas Encontrados

### PROBLEMA 1: Pastas com Arquivos MD Soltos

**Severidade:** 🔴 CRÍTICA

Três pastas contêm arquivos reais (não symlinks) que violam a separação físico/acesso:

#### 1a. `modulo-pessoas/` — 9 arquivos + 1 pasta

Localização: `/home/evonexus/evo-nexus/workspace/projects/go-control-erp/modulo-pessoas/`

| Arquivo | Tipo | Tamanho | Criado |
|---------|------|---------|--------|
| `[C]backlog-modulo-pessoas.md` | DOCS | 28KB | 2026-05-27 |
| `[C]casos-de-uso-modulo-pessoas.md` | DOCS | ? | 2026-05-27 |
| `[C]code-review-modulo-pessoas-mvp.md` | REVIEW | ? | 2026-05-27 |
| `[C]plan-modulo-pessoas.md` | PLAN | 21KB | 2026-05-27 |
| `[C]prd-modulo-pessoas.md` | PRD | 31KB | 2026-05-27 |
| `[C]release-pessoas-mvp-2026-05-27.md` | RELEASE | ? | 2026-05-27 |
| `[C]verification-modulo-pessoas-mvp.md` | VERIFICATION | ? | 2026-05-27 |
| `brainstorm-modulo-pessoas-2026-05-26.md` | DOCS | ? | 2026-05-26 |
| `ux/` | PASTA | — | — |

**O que deveria ser:** Estes 9 arquivos deveriam estar em `/home/evonexus/evo-projects/go-control-erp/features/modulo-pessoas/` (git do projeto), não em `workspace/`.

**Impacto:** 
- Version control não rastreia esses artefatos (estão fora do repo)
- Trabalho em paralelo diverge facilmente
- Difficult to sync com o go-control-erp repo

#### 1b. `go-cobranca/` — 2 arquivos + 1 pasta

Localização: `/home/evonexus/evo-nexus/workspace/projects/go-control-erp/go-cobranca/`

| Arquivo | Tipo | Tamanho | Criado |
|---------|------|---------|--------|
| `brainstorm-go-cobranca-2026-05-26.md` | DOCS | 26KB | 2026-05-26 |
| `ux/` | PASTA | — | — |

**O que deveria ser:** Em `/home/evonexus/evo-projects/go-control-erp/features/go-cobranca/` + symlink em `workspace/`.

#### 1c. `go-control-auth/` — 1 arquivo

Localização: `/home/evonexus/evo-nexus/workspace/projects/go-control-erp/go-control-auth/`

| Arquivo | Tipo | Tamanho | Criado |
|---------|------|---------|--------|
| `[C]design-go-control-auth-spa-2026-05-28.md` | DESIGN | 5KB | 2026-05-28 |

**O que deveria ser:** Em `/home/evonexus/evo-projects/go-control-erp/features/go-control-auth/` + symlink em `workspace/`.

---

### PROBLEMA 2: Duplicação de Estrutura

**Severidade:** 🟡 ALTA

Há **duas hierarquias coexistindo** em `go-control-erp`:

**Hierarquia 1 (Correta):**
```
workspace/projects/go-control-erp/
  features/ ← 18 symlinks para evo-projects/features/
  plans/
  docs/
  INDEX.md
```

**Hierarquia 2 (Incorreta):**
```
workspace/projects/go-control-erp/
  go-cobranca/              ← arquivo + symlink duplicado
  go-control-auth/          ← arquivo + symlink duplicado
  modulo-pessoas/           ← arquivo + symlink duplicado
  canal-shared/             ← symlink apenas
  cnpj-api-module/          ← symlink apenas
  go-payment-hub/           ← sub-app local + symlink
  licencas-nova-refactor/   ← symlink apenas
  login-app-aware/          ← symlink apenas
  plano-edit-wizard/        ← symlink apenas
  plano-telas-selection/    ← symlink apenas
  platform-notifications/   ← symlink apenas
```

**Impacto:**
- Agentes veem `modulo-pessoas/` paralelo a `features/` e ficam em dúvida sobre qual usar
- Referências em docs podem apontar para um ou outro
- Difícil de manter navegável com o INDEX.md

---

### PROBLEMA 3: go-payment-hub Redundante

**Severidade:** 🟡 MÉDIA

`go-payment-hub` aparece **duas vezes**:

1. **Como sub-app local:**
   ```
   workspace/projects/go-control-erp/go-payment-hub/
     features/
       async-emission/[C]design-async-emission-ui-2026-06-02.md
     modulo/
     docs/
     ciclos/
     manuais/
     ux/
   ```

2. **Como symlink em features:**
   ```
   workspace/projects/go-control-erp/features/go-payment-hub/ → evo-projects/.../go-payment-hub/
   ```

**O que é este padrão?**
- `go-payment-hub` é um **sub-app** (tem sua própria estrutura com modulo/, ciclos/, etc.)
- Sub-apps devem estar num nível intermediário (conforme ADR-004)
- Logo, a pasta local `workspace/projects/go-control-erp/go-payment-hub/` é CORRETA
- Mas o symlink em `features/go-payment-hub/` é REDUNDANTE (aponta para features do mesmo projeto)

**Impacto:**
- Confusão: qual é a source-of-truth? A local ou o symlink?
- Se alguém edita em uma, a outra fica desincronizada (são diferentes)
- Dificulta referências no INDEX.md

**Recomendação:**
- Guardar APENAS a pasta local `go-payment-hub/` com estrutura de sub-app
- Remover o symlink `features/go-payment-hub/`

---

### PROBLEMA 4: Organização Incompleta de Docs

**Severidade:** 🟠 MÉDIA

Brainstorm e UX estão espalhados em pastas paralelas, não organizados por tipo:

```
workspace/projects/go-control-erp/
  go-cobranca/brainstorm-go-cobranca-2026-05-26.md      ← deveria estar em docs/ ou features/
  go-cobranca/ux/                                       ← deveria estar em features/{slug}/ux/
  modulo-pessoas/brainstorm-modulo-pessoas-2026-05-26.md ← deveria estar em docs/ ou features/
  modulo-pessoas/ux/                                     ← deveria estar em features/{slug}/ux/
```

**O que deveria ser:**
```
evo-projects/go-control-erp/features/go-cobranca/
  [C]brainstorm-go-cobranca-2026-05-26.md
  ux/

evo-projects/go-control-erp/features/modulo-pessoas/
  [C]brainstorm-modulo-pessoas-2026-05-26.md
  ux/
```

---

### PROBLEMA 5: Ausência de Índice/CLAUDE em Sub-Apps Locais

**Severidade:** 🟠 MÉDIA

Pastas de sub-apps locais (como `go-payment-hub/`, `modulo-pessoas/`) não têm:
- `[C]INDEX.md` ou `CLAUDE.md` para navegação interna
- Documentação de convenções específicas do sub-app
- Referência para agentes trabalhando ali

---

### PROBLEMA 6: Symlinks e Pastas Reais Side-by-Side

**Severidade:** 🔴 CRÍTICA

Exemplo concreto — confusão total:

```
workspace/projects/go-control-erp/
  features/go-cobranca/     ← symlink para evo-projects/.../features/go-cobranca/
  go-cobranca/              ← pasta REAL com arquivos MD soltos
```

**Possibilidades para um agente:**
- Criar doc em `features/go-cobranca/[C]novo.md`? Vai para evo-projects ✓
- Criar doc em `go-cobranca/[C]novo.md`? Fica em workspace apenas ✗
- Referenciar em INDEX? Qual caminho colocar?

**Impacto:** Caos absoluto na navegação e manutenção.

---

## Contexto Histórico Provável

1. **Fase 1 (inicial):** Agentes criavam features em pastas paralelas (`modulo-pessoas/`, `go-cobranca/`)
2. **Fase 2 (formalização):** Convenção oficial saiu (`.claude/rules/go-control-doc-structure.md`) estabelecendo symlinks
3. **Fase 3 (migração incompleta):** Novo work foi para `features/` + symlinks, mas artefatos antigos ficaram nas pastas paralelas
4. **Resultado:** Coexistem 2 padrões; ninguém apagou as pastas antigas

---

## Outros Projetos — Status ✓

| Projeto | Status | Notas |
|---------|--------|-------|
| **cpsmq** | ✓ Correto | Estrutura limpa: `features/`, `plans/`, `docs/`, `manuais/`, `modulo/` |
| **evo-crm** | ✓ Correto | Estrutura minimalista: `features/`, `plans/`, `docs/` |
| **evo-nexus** | ✓ Correto | Estrutura padrão com `tickets/` adicional |
| **evonexus-discord-plus** | ✓ Correto | Estrutura rica: `features/`, `plans/`, `reviews/`, `verifications/`, `debug/`, `architecture/` |
| **serket** | ✓ Correto | Estrutura minimalista: `features/`, `plans/`, `docs/` |

---

## Recomendações — Plano de Ação

### Opção A: Limpar Completamente (Recomendado)

**Objetivo:** Mover todos os artefatos para `evo-projects/` e criar symlinks em `workspace/`.

**Passos:**

1. **Para cada pasta paralela (`modulo-pessoas/`, `go-cobranca/`, `go-control-auth/`):**
   ```bash
   # 1. Copiar arquivos para evo-projects
   cp -r /home/evonexus/evo-nexus/workspace/projects/go-control-erp/modulo-pessoas/*.md \
         /home/evonexus/evo-projects/go-control-erp/features/modulo-pessoas/
   
   # 2. Copiar pasta ux/ se existir
   cp -r /home/evonexus/evo-nexus/workspace/projects/go-control-erp/modulo-pessoas/ux/ \
         /home/evonexus/evo-projects/go-control-erp/features/modulo-pessoas/
   
   # 3. Deletar pasta em workspace
   rm -rf /home/evonexus/evo-nexus/workspace/projects/go-control-erp/modulo-pessoas/
   
   # 4. Criar symlink
   ln -s /home/evonexus/evo-projects/go-control-erp/features/modulo-pessoas/ \
         /home/evonexus/evo-nexus/workspace/projects/go-control-erp/modulo-pessoas/
   ```

2. **Para `go-payment-hub`:**
   ```bash
   # 1. Deletar o symlink em features/
   rm /home/evonexus/evo-nexus/workspace/projects/go-control-erp/features/go-payment-hub/
   
   # 2. Mover arquivos locais para evo-projects (se necessário)
   # go-payment-hub/features/async-emission/[C]design... → evo-projects/.../features/go-payment-hub/features/...
   
   # 3. Manter APENAS a pasta local workspace/projects/go-control-erp/go-payment-hub/
   ```

3. **Atualizar `INDEX.md`:**
   - Remover referências a pastas paralelas
   - Adicionar secção de "Sub-apps" com links para `go-payment-hub/`, `go-message/`, etc.

4. **Commit ao evo-projects:**
   ```bash
   cd /home/evonexus/evo-projects/go-control-erp/
   git add features/modulo-pessoas/ features/go-cobranca/ features/go-control-auth/
   git commit -m "Migração: consolidar artefatos de workspace para evo-projects"
   ```

---

### Opção B: Não Fazer Nada (Não Recomendado)

**Risco:** Coexistência continuada; possibilidade de divergência; confusão em futuras edições.

---

## Verificação Pós-Limpeza

Após a migração, executar:

```bash
# Verificar que não há pastas paralelas
ls -d /home/evonexus/evo-nexus/workspace/projects/go-control-erp/*/  2>/dev/null | \
  grep -v features | grep -v plans | grep -v docs | grep -v architecture | grep -v reviews | \
  grep -v verifications | grep -v debug | grep -v manuais | grep -v ux

# Output esperado: nenhuma linha (vazío)

# Verificar que todos os symlinks apontam para evo-projects
find /home/evonexus/evo-nexus/workspace/projects/go-control-erp -maxdepth 1 -type l \
  -exec ls -l {} \; | grep -E "features|modulo-pessoas|go-cobranca"

# Output esperado: symlinks todos apontando para /home/evonexus/evo-projects/...
```

---

## Aprovação Necessária

- [ ] Eduardo revisa esta auditoria
- [ ] Eduardo aprova a Opção A ou B
- [ ] Scout executa migração (se aprovado)
- [ ] Flow cria commit no evo-projects
- [ ] Bolt atualiza INDEX.md
