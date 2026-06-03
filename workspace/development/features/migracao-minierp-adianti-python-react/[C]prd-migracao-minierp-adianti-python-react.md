---
author: claude
agent: compass-planner
type: prd
date: 2026-05-06
feature: migracao-minierp-adianti-python-react
phase: piloto-pessoas-produtos
status: draft
ticket: MIG-01 (ad313e49-c22e-4d52-aaf8-713e21f3fe78)
goal: minierp-01-discovery-classificacao
---

# PRD — Piloto Pessoas + Produtos (GO Control ERP)

## 1. Contexto

A migração do MiniERP (Adianti/PHP 8.2) para o **GO Control ERP** (Django 5 + React 18) parte do zero — sem migração de dados, com o legado servindo apenas como referência funcional. O discovery do @echo-analyst (`[C]discovery-migracao-minierp-adianti-python-react.md`) registrou todas as decisões de stack, multi-empresa, soft delete, proxy pattern e TDD.

Este PRD descreve o **piloto end-to-end** que valida a stack completa antes de abrir os tickets de cada módulo (MIG-02..MIG-N). O piloto cobre as **duas raízes do grafo de FKs do ERP**: Pessoas (clientes/fornecedores) e Produtos. Toda outra entidade do GO depende delas — se este slice fecha, a stack está provada.

## 2. Problema

Não temos hoje:
- Repositório `go-control-erp` bootstrapped com a estrutura aprovada
- Schema PostgreSQL multi-empresa para as entidades raiz
- API REST com autenticação JWT, soft delete e filtro automático por `empresa_id`
- Frontend React (PrimeReact) com padrão de módulo definido
- Camada proxy de integrações externas (CEP, CNPJ) com múltiplos providers
- Suite de testes TDD funcionando ponta a ponta

Sem isso, qualquer próximo módulo (Financeiro, Vendas, Estoque) começa do zero e replica decisões — ou pior, replica decisões diferentes em cada módulo.

## 3. Objetivos

| # | Objetivo | Mensurável |
|---|---|---|
| O1 | Validar a stack Django 5 + DRF + React 18 + PrimeReact ponta a ponta | Usuário cadastra 1 cliente e 1 produto via UI; dado persiste no PostgreSQL com `empresa_id` correto |
| O2 | Estabelecer o padrão de módulo Django (`models/serializers/services/selectors/views/urls/permissions/tests`) que todos os módulos seguintes usarão | App `cadastros` segue o padrão; `agent-instructions.md` documenta-o |
| O3 | Estabelecer o padrão de módulo React (`pages/components/services/hooks/types/routes.tsx`) | Módulo `cadastros` no frontend segue o padrão; `coding-standards.md` documenta-o |
| O4 | Validar arquitetura proxy de integrações (Strategy + Fallback) | Proxy CEP roda com ≥ 2 providers; Proxy CNPJ roda com ≥ 2 providers; teste cobre fallback |
| O5 | Provar que TDD funciona com @grid-tester escrevendo testes antes de @bolt-executor implementar | Cobertura ≥ 80% nos services do app `cadastros`; CI verde |

## 4. Não-Objetivos (Fronteiras)

O piloto **NÃO** inclui:
- Outros módulos do legado (financeiro, vendas, estoque, produção, expedição, CRM, communication, sac, etc.) — entram em MIG-02..MIG-N
- Importação de dados do legado (Q5 do discovery: GO parte do zero)
- Workflow data-driven com estados/transições — só usado em pedido de venda; piloto tem CRUD simples
- Proxy Fiscal (NF-e) e Proxy Bancário — fases posteriores
- Notificações (Telegram, e-mail, WhatsApp) — fases posteriores
- Audit log universal — entra junto com módulo accounts em MIG-02
- Controle granular de permissões por papel — piloto usa autenticação JWT simples + flag de superuser
- Telas de configuração de tipo_cliente, categoria_cliente, fabricante, familia_produto, tipo_produto (apenas seeds + endpoints `GET` para popular dropdowns)
- Multi-banco por CNPJ (decidido no onboarding, não no código) — piloto roda em banco único
- Portal cliente público
- Mensageria interna entre usuários

## 5. Usuários

| Perfil | Como interage no piloto |
|---|---|
| **Operador de cadastro** | Acessa GO Control via UI React; cadastra Pessoa (cliente, fornecedor, transportadora) com endereço autopreenchido por CEP e busca por CNPJ; cadastra Produto com geração automática de código de barras |
| **Backend dev (agente)** | Estende o app `cadastros` com novas entidades seguindo o padrão; consome a API DRF |
| **Frontend dev (agente)** | Cria novas páginas seguindo o padrão `pages/components/services/hooks/types/routes.tsx` |

## 6. Entidades em Escopo

### 6.1. Módulo `cadastros/pessoas`

Schema legado de referência (ver §12.1 do discovery e `app/database/minierp-pgsql.sql`):

| Tabela legada | Tabela GO | Notas de redesenho |
|---|---|---|
| `pessoa` | `pessoa` | Adicionar `empresa_id`, `created_by`, `updated_by`. Remover `login`/`senha` (autenticação fica em `accounts`). Documento → `documento` (CPF/CNPJ). Validar formato no serializer com Zod-equivalente Python. |
| `pessoa_contato` | `pessoa_contato` | Adicionar `empresa_id`, soft delete (`deleted_at`). |
| `pessoa_endereco` | `pessoa_endereco` | Adicionar `empresa_id`, soft delete. Manter FK `cidade_id`. |
| `pessoa_grupo` | `pessoa_grupo` (M2M) | Tabela associativa Pessoa ↔ GrupoPessoa. |
| `grupo_pessoa` | `grupo_pessoa` | Catálogo simples (nome). |
| `tipo_cliente` | `tipo_cliente` | Catálogo (nome, sigla). Seed: Cliente, Fornecedor, Transportadora, Cliente+Fornecedor. **Sem `empresa_id`** — catálogo global. |
| `categoria_cliente` | `categoria_cliente` | Catálogo (nome). Seed mínimo: PF, PJ, MEI. |
| `cidade` | `cidade` | Catálogo IBGE com `estado_id`. Seed: cidades brasileiras (carga inicial via fixture do IBGE). |
| `estado` | `estado` | Catálogo IBGE (nome, sigla, codigo_ibge). Seed: 27 UFs. |

### 6.2. Módulo `cadastros/produtos`

| Tabela legada | Tabela GO | Notas de redesenho |
|---|---|---|
| `produto` | `produto` | Adicionar `empresa_id`, `created_by`, `updated_by`, soft delete. Remover campos de estoque (`qtde_estoque`, `estoque_minimo`, `estoque_maximo`) — esses ficam no módulo `estoque` que será criado em MIG-04. Manter dimensões físicas, preços, código de barras, foto. |
| `familia_produto` | `familia_produto` | Catálogo simples por empresa (nome, `empresa_id`). |
| `fabricante` | `fabricante` | Catálogo simples por empresa (nome, `empresa_id`). |
| `tipo_produto` | `tipo_produto` | Catálogo simples por empresa (nome, `empresa_id`). Ex: Matéria-prima, Produto acabado, Serviço, Insumo. |
| `unidade_medida` | `unidade_medida` | Catálogo global (nome, sigla, fraciona). Seed: UN, KG, L, M, M2, M3, CX, PCT. **Sem `empresa_id`** — catálogo global. |

### 6.3. Suporte: `cep_cache`

| Tabela legada | Tabela GO | Notas de redesenho |
|---|---|---|
| `cep_cache` | `cep_cache` | Cache do Proxy CEP. Sem `empresa_id` — cache global compartilhado. TTL aplicado em consulta (`created_at` < 30 dias). |

## 7. Integrações em Escopo

### 7.1. Proxy CEP (obrigatório no piloto)

Fluxo: usuário digita CEP no formulário de Pessoa → frontend chama `GET /api/v1/integrations/cep/{cep}` → proxy decide qual provider usar → retorna logradouro/bairro/cidade/UF → frontend autopreenche os campos.

**Providers iniciais (mínimo 2):**
- ViaCEP (https://viacep.com.br/)
- BrasilAPI (https://brasilapi.com.br/api/cep/v2/)

**Estratégia:** sequencial com fallback (provider 1 falha → tenta provider 2). Cache em `cep_cache` com TTL de 30 dias.

**Interface:**
```
class CepProvider(Protocol):
    def lookup(cep: str) -> CepResult | None
```

### 7.2. Proxy CNPJ (obrigatório no piloto)

Fluxo: usuário digita CNPJ no formulário de Pessoa (tipo PJ) → clica em "Buscar dados" → frontend chama `GET /api/v1/integrations/cnpj/{cnpj}` → proxy decide qual provider usar → retorna razão social, nome fantasia, e-mail, telefone, endereço → frontend autopreenche.

**Providers iniciais (mínimo 2):**
- ReceitaWS (https://receitaws.com.br/)
- BrasilAPI (https://brasilapi.com.br/api/cnpj/v1/)

**Estratégia:** sequencial com fallback + rate-limit awareness (ReceitaWS tem 3 req/min no plano free).

## 8. Critérios de Aceitação (Given/When/Then)

### CA-01 — Bootstrap do repositório
**Given** o repositório `go-control-erp` ainda não existe
**When** o agente executar o bootstrap (Step 1 do plano)
**Then** o repo conterá `backend/` (Django + DRF), `frontend/` (React + Vite), `docs/` (com `agent-instructions.md` e `coding-standards.md`), README, `.gitignore`, `.env.example`, `docker-compose.yml` para PostgreSQL + Redis

### CA-02 — Cadastro de Pessoa (cliente PJ com CNPJ)
**Given** o usuário está autenticado e tem `empresa_id` ativo
**When** abrir a tela "Pessoas → Nova", selecionar tipo "Cliente PJ", digitar CNPJ válido e clicar em "Buscar dados"
**Then** o formulário será autopreenchido com razão social, nome fantasia, e-mail e telefone retornados pelo Proxy CNPJ

**And When** salvar o registro
**Then** uma linha será criada em `pessoa` com `empresa_id` igual ao do usuário, `tipo_cliente_id` correspondente a "Cliente PJ", `created_by` populado, `deleted_at` nulo

### CA-03 — Cadastro de Pessoa (endereço com CEP autopreenchido)
**Given** o usuário está cadastrando uma Pessoa
**When** digitar um CEP válido no campo de endereço e sair do campo (blur)
**Then** o frontend chamará o Proxy CEP e autopreencherá rua, bairro, cidade (resolvendo `cidade_id`) e estado

**And When** o ViaCEP retornar erro/timeout
**Then** o proxy fará fallback para BrasilAPI sem o usuário perceber

**And When** o mesmo CEP for consultado novamente em até 30 dias
**Then** o resultado virá de `cep_cache` sem chamada externa

### CA-04 — Listagem de Pessoa com filtros
**Given** o usuário tem 50 pessoas cadastradas em sua empresa
**When** abrir a tela "Pessoas"
**Then** verá uma DataTable PrimeReact com paginação, busca por nome/documento, filtro por tipo_cliente, ordenação por colunas
**And** registros com `deleted_at IS NOT NULL` não aparecerão (filtro automático via Mixin)
**And** registros de outras empresas não aparecerão (filtro automático via middleware)

### CA-05 — Soft delete de Pessoa
**Given** o usuário visualiza uma Pessoa cadastrada
**When** clicar em "Excluir" e confirmar
**Then** a linha receberá `deleted_at = now()` em vez de DELETE físico
**And** sumirá das listagens
**And** as queries que tentem `SELECT WHERE id = X` continuarão respeitando o filtro do Mixin

### CA-06 — Cadastro de Produto com código de barras gerado
**Given** o usuário está autenticado
**When** abrir a tela "Produtos → Novo", preencher nome, tipo, família, unidade de medida e clicar em "Gerar código de barras"
**Then** o backend gerará um EAN-13 único na empresa via `python-barcode`
**And When** salvar
**Then** uma linha será criada em `produto` com `empresa_id` correto, `cod_barras` único na empresa

### CA-07 — Listagem de Produto com filtros
**Given** o usuário tem produtos cadastrados
**When** abrir a tela "Produtos"
**Then** verá DataTable com busca por nome/cod_barras, filtros por tipo_produto, familia_produto, fabricante e ordenação

### CA-08 — Multi-empresa: isolamento garantido
**Given** existem 2 empresas (E1 e E2) com pessoas cadastradas em cada
**When** o usuário da E1 chamar `GET /api/v1/cadastros/pessoas/`
**Then** receberá apenas pessoas com `empresa_id = E1`
**And When** tentar `GET /api/v1/cadastros/pessoas/{id_de_E2}/`
**Then** receberá HTTP 404 (não 403 — não vaza existência)

### CA-09 — Autenticação JWT
**Given** o usuário tem credenciais válidas
**When** chamar `POST /api/v1/auth/token/` com username/password
**Then** receberá `access` e `refresh` tokens
**And When** chamar qualquer endpoint protegido com `Authorization: Bearer <access>`
**Then** a request será autenticada e o middleware injetará `empresa_id` no contexto

### CA-10 — TDD: testes precedem implementação
**Given** o agente vai implementar uma funcionalidade do app `cadastros`
**When** @grid-tester rodar antes
**Then** existirá um arquivo `tests/test_<feature>.py` que falha por feature ainda não implementada (vermelho)
**And When** @bolt-executor implementar
**Then** os testes passarão (verde) e cobertura do service ficará ≥ 80%

### CA-11 — Proxy CEP com fallback testado
**Given** o ViaCEP está retornando 5xx
**When** o app chamar `cep_proxy.lookup("01310-100")`
**Then** o BrasilAPI será consultado e retornará o resultado
**And** um teste unitário em `tests/test_cep_proxy.py` cobre esse fallback (mockando os providers)

### CA-12 — Proxy CNPJ com fallback testado
**Given** o ReceitaWS retorna 429 (rate limit)
**When** o app chamar `cnpj_proxy.lookup("33.000.167/0001-01")`
**Then** o BrasilAPI será consultado e retornará o resultado
**And** um teste unitário em `tests/test_cnpj_proxy.py` cobre esse fallback

### CA-13 — Critério de validação do piloto (smoke teste manual)
**Given** o ambiente está rodando (`docker-compose up`)
**When** Eduardo acessar `http://localhost:5173`, fizer login e cadastrar:
1. Cliente PJ "Empresa X" com CNPJ válido (autopreenchido)
2. Endereço dessa pessoa com CEP "01310-100" (autopreenchido com fallback se necessário)
3. Produto "Saco de ração 60kg" com código de barras gerado
**Then** todos os 3 cadastros serão persistidos corretamente em PostgreSQL com `empresa_id` correto, e visíveis nas respectivas listagens

## 9. Constraints

| # | Constraint | Origem |
|---|---|---|
| C1 | Banco PostgreSQL ≥ 14 | Discovery Q2 |
| C2 | Backend: Django 5 + DRF + djangorestframework-simplejwt + Celery + Redis | Discovery Q2 |
| C3 | Frontend: React 18 + TypeScript + Vite + PrimeReact + Tailwind + TanStack Query + React Hook Form + Zod | Discovery Q3 |
| C4 | `empresa_id` obrigatório em todas as tabelas de domínio (exceto catálogos globais: `estado`, `cidade`, `tipo_cliente`, `categoria_cliente`, `unidade_medida`, `cep_cache`) | Discovery Q4 |
| C5 | Soft delete (`deleted_at`) em todas as tabelas de domínio | Discovery Q5 / pattern legado |
| C6 | Repositório novo `go-control-erp/` separado do EvoNexus | Handoff |
| C7 | TDD obrigatório (testes antes do código), cobertura ≥ 80% nos services | Discovery Q2 + handoff |
| C8 | Integrações externas via interface + providers (não chamada direta) | Discovery Q6 |
| C9 | Linguagem: pt-BR (mensagens, validação, UI) | Workspace |
| C10 | Não migrar dados do legado | Discovery Q5 |
| C11 | Convenção de projetos customizados (CLAUDE.md): código fora do EvoNexus repo, dados persistentes em `/home/evonexus/evo-projects/<projeto>/` quando aplicável. Para o GO, o repo será `go-control-erp/` em diretório próprio. |

## 10. Dependências

- PostgreSQL ≥ 14 instalado (via `docker-compose`)
- Redis ≥ 7 instalado (via `docker-compose`)
- Node ≥ 20 e Python ≥ 3.12
- Acesso a APIs públicas: ViaCEP, BrasilAPI, ReceitaWS (sem chave) — rate-limit a respeitar
- Token JWT funcional desde Step 1 (sem isso, frontend não consome API)

## 11. Riscos

| # | Risco | Mitigação |
|---|---|---|
| R1 | ReceitaWS rate-limita (3 req/min no free) durante desenvolvimento | Cache resultados de CNPJ por 7 dias; fallback BrasilAPI primeiro nos testes manuais |
| R2 | Carga inicial de cidades IBGE pode ser pesada (~5.500 cidades) | Fixture `cidades.json` enxuta com top 200 cidades + endpoint `POST /api/v1/cidades/sync-ibge/` para carga sob demanda |
| R3 | Padrão de módulo Django pode ser sub-especificado e cada agente interpretar diferente | `agent-instructions.md` com exemplo concreto do app `cadastros` + linter (`ruff`) configurado |
| R4 | PrimeReact + Tailwind podem conflitar em z-index e tema | Documentar tema base em `coding-standards.md`; usar `prefix` Tailwind se necessário |
| R5 | TDD pode atrasar o piloto se @grid-tester e @bolt-executor não sincronizarem | Sequência clara no plano: Step "schema" → Step "testes" → Step "código" para cada entidade |
| R6 | Catálogos globais sem `empresa_id` (estado, cidade, unidade_medida) podem ser editados por uma empresa e impactar outras | Endpoints de catálogos globais são read-only via API pública; mutação só via admin Django ou fixture |

## 12. Open Questions (não-bloqueantes para o piloto)

Estas questões NÃO bloqueiam o piloto. Resolvê-las antes de MIG-02 (Financeiro/Accounts):

- [ ] **OQ1** — Modelo de tenant: existe entidade `empresa` com `id` autoincremento ou UUID? **Recomendação Compass:** UUID v4 (evita enumeration; padrão moderno). **Decidir antes do Step 2.**
- [ ] **OQ2** — `created_by`/`updated_by` referenciam `auth_user.id` (Django) ou tabela própria `accounts_user`? **Recomendação Compass:** custom user model em `apps.accounts.User` desde Step 1 (Django só permite trocar antes da primeira migration).
- [ ] **OQ3** — `tipo_cliente.sigla` (char(2)) — manter ou descartar? **Recomendação Compass:** descartar; usar `id` semântico em código (enum no service).
- [ ] **OQ4** — Catálogos globais (`estado`, `cidade`, `unidade_medida`) precisam de `created_at`/`updated_at`? **Recomendação Compass:** sim, para auditoria de fixture updates.
- [ ] **OQ5** — Geração de código de barras: EAN-13 é o padrão correto para o GO ou usar um formato customizado? **Recomendação Compass:** EAN-13 (padrão de varejo brasileiro).
- [ ] **OQ6** — Senha do usuário (não da Pessoa): hash com `argon2` ou `pbkdf2`? Default Django é pbkdf2; argon2 é mais forte. **Recomendação Compass:** argon2 (Django 5 suporta out-of-the-box).

Estas questões serão consolidadas em `workspace/development/plans/[C]open-questions.md` quando o plano for aprovado.

## 13. Métricas de Sucesso do Piloto

Após o piloto entregue:
- [ ] CA-01 a CA-13 todos PASS no relatório de @oath-verifier
- [ ] CI verde no GitHub Actions (lint + tests + coverage ≥ 80%)
- [ ] Eduardo executa o smoke teste manual (CA-13) sem encontrar bug bloqueante
- [ ] `agent-instructions.md` e `coding-standards.md` aprovados — qualquer agente pode estender o app `cadastros` sem reabrir decisão arquitetural
- [ ] Tickets MIG-02 (Financeiro) e MIG-04 (Estoque) podem ser abertos imediatamente após, sem retrabalho do piloto

## 14. Próximos Passos (após aprovação deste PRD)

1. Compass produz o plano executável (`[C]plan-migracao-minierp-adianti-python-react.md`)
2. Eduardo aprova o plano
3. @apex-architect produz `[C]architecture-migracao-minierp-adianti-python-react.md` (ADR de stack)
4. @bolt-executor + @grid-tester executam os steps do plano
5. @oath-verifier valida contra os critérios de aceitação deste PRD
6. Após PASS, Eduardo decide o próximo módulo (sugestão: MIG-02 Financeiro)
