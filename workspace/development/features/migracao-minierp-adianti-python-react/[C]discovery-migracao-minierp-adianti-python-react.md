# Discovery — Migração MiniERP (Adianti/PHP) → Python + React

- **Autor:** @echo-analyst
- **Data:** 2026-05-05
- **Atualizado:** 2026-05-06 (§8 respondido por Eduardo)
- **Ticket:** MIG-01 (id ad313e49-c22e-4d52-aaf8-713e21f3fe78)
- **Goal:** minierp-01-discovery-classificacao
- **Fonte analisada (read-only):** `/home/evonexus/go_mini_erp_src`
- **Destino dos artefatos:** `/home/evonexus/evo-nexus/workspace/development/features/migracao-minierp-adianti-python-react/`

---

## 1. Sumário executivo (TL;DR)

O legado é um ERP construído sobre **Adianti Framework 7.5 + PHP 8.2** com camadas tradicionais (control / model / service / view) e schema PostgreSQL com **68 tabelas**. A maior parte da UI (Forms, Lists, Kanban, Dashboards) é **inutilizável** para Python+React porque Adianti gera a interface server-side a partir de classes PHP — qualquer "tela" do legado é apenas um esqueleto a ser refeito em React.

**Onde está o ouro reaproveitável:**
1. **`app/service/grafix/`** — serviços de regra de negócio em PHP "puro" (estritamente tipado, namespaced, com docblocks de versionamento). Migram quase 1:1 para serviços Python.
2. **`app/database/minierp-pgsql.sql`** — modelo de dados completo (68 tabelas, FKs, seeds em `minierp-inserts.sql`). Reutilizável como base do schema PostgreSQL do GO, com adaptações.
3. **Workflow declarativo** — tabelas `estado_pedido_venda`, `matriz_estado_pedido_venda`, `estado_producao_item`, `workflow_notification_rule`, `aprovador` codificam a máquina de estados do pedido em **dados**, não em código. Esse design é excelente e deve ser preservado.

**Decisões de escopo registradas (2026-05-06):**
1. **Escopo:** todos os 18 módulos do legado replicados no GO, com redesenho de Expedição e Produção.
2. **Stack Python:** Django 5 + DRF + simplejwt + Celery + Redis + PostgreSQL.
3. **Stack React:** React 18 + TypeScript + Vite + PrimeReact + Tailwind + TanStack Query + React Hook Form + Zod.
4. **Multi-empresa:** `empresa_id` em todas as tabelas de domínio; banco compartilhado por grupo de mesma natureza, banco separado por CNPJ quando naturezas diferentes.
5. **Dados:** GO parte do zero — legado é referência funcional, sem migração de dados.
6. **Workflows:** data-driven (estados e transições configuráveis em banco), redesenhados para o GO.
7. **Integrações:** via camadas proxy com múltiplos providers (Proxy Fiscal, Proxy Bancário, Proxy CEP, Proxy CNPJ).
8. **Produção — maior mudança arquitetural:** `ordem_producao` desacoplada do pedido. Suporta dois modelos: produção sob demanda (pedido → OP) e produção por reposição de estoque (ruptura/manual → OP). Ao concluir: baixa automática nas matérias-primas + entrada do produto acabado no estoque.

**Módulo piloto sugerido:** **Pessoas (clientes/fornecedores) + Produtos** (ver §7). Justificativa: são as raízes do grafo de FKs; toda outra entidade depende delas; têm regras simples e um Service externo já útil (`CEPService`, `CNPJService`, `ProdutoService::gerarBarcode/gerarQrCode`).

---

## 2. Estrutura de pastas (alto nível)

```
go_mini_erp_src/
├── app/
│   ├── config/         # configs do framework Adianti
│   ├── control/        # 223 .php — controllers/telas (Forms, Lists, Kanban, Dashboards)
│   │   ├── admin/      # gestão de usuários, grupos, units, 2FA, framework update
│   │   ├── builder/    # ferramenta interna do Adianti (gerador de código)
│   │   ├── comercial/  # PedidoVenda (orçamento → venda)
│   │   ├── communication/ # mensagens internas, documentos compartilhados
│   │   ├── configuracoes/ # workflow rules, aprovadores, etapas
│   │   ├── crm/        # negociação (pré-venda), kanban CRM, atividades
│   │   ├── estoque/    # produto, família, fabricante, etiqueta, QR
│   │   ├── expedicao/  # entrega (header list, item simple list)
│   │   ├── financeiro/ # contas a pagar/receber, fluxo de caixa, baixa
│   │   ├── grafix/     # controllers REST/Workflow (camada nova)
│   │   ├── install/    # instalador inicial do legado
│   │   ├── log/        # access log, change log, sql log, request log
│   │   ├── pedidos/    # painel cliente, lista, documento PDF
│   │   ├── pessoas/    # cliente, contato, endereço, cidade, estado, grupo
│   │   ├── producao/   # kanban produção, dashboard, gerenciar itens
│   │   ├── public/ + publico/ # painel cliente externo (login + lista de contas)
│   │   ├── sac/        # ouvidoria (form público + interno)
│   │   └── supervisor/ # error log crontab, notification template/channel
│   ├── controller/     # 2 controllers REST (ApiAuth, Swagger)
│   ├── database/       # schemas .sql (pgsql/mysql/oracle/sqlite/fbird/mssql) + seeds + .db
│   ├── lib/            # libs internas (barcode, builder, html, menu, reports, util, validator, widget)
│   ├── middleware/     # Basic/Bearer/BuilderAdmin auth
│   ├── model/          # 82 .php — entidades (Active Record do Adianti, herdam de TRecord)
│   ├── output/         # diretório de outputs (PDFs gerados, exports)
│   ├── routes/         # api.php (rotas REST internas)
│   ├── service/        # 67 .php — serviços
│   │   ├── auth/       # autenticação, LDAP, 2FA email
│   │   ├── builder/    # serviços do builder
│   │   ├── grafix/     # *** NÚCLEO DE REGRA DE NEGÓCIO ***
│   │   │   ├── EstoqueService.php    # entrada/saída de estoque
│   │   │   ├── financeiro/           # baixa, lançamento, fluxo de caixa
│   │   │   ├── vendas/               # pedido, workflow, notificação, e-mail
│   │   │   ├── producao/             # iniciar/pausar/concluir produção
│   │   │   ├── expedicao/            # criar/despachar/concluir entrega
│   │   │   └── util/
│   │   ├── log/        # serviços para os logs
│   │   ├── rest/       # rest services para usuário/grupo
│   │   └── system/     # chat, file hash, db info, document upload
│   ├── templates/      # themes Adianti (theme3, theme3-adminlte3, theme4, theme-builder)
│   └── view/           # 1 arquivo único (welcome view)
├── lib/                # libs do framework (adianti, mad, etc.) — NÃO reaproveitar
├── vendor/             # composer deps (phpmailer, dompdf, JWT, barcode) — NÃO reaproveitar (tudo PHP)
├── files/              # uploads
├── tmp/                # cache do framework
├── menu*.xml           # 6 menus declarativos (dist, mobile, navbar, public)
├── composer.json       # deps PHP
├── manifest.json       # PWA manifest
└── *.php (raiz)        # bootstrap (index.php, init.php, engine.php, rest.php, etc.)
```

**Volumetria PHP do `app/`:** 444 arquivos `.php` no total — 223 control / 82 model / 67 service / o restante é lib, middleware, routes.

---

## 3. Inventário de módulos

Os módulos abaixo são derivados das pastas em `app/control/` cruzadas com os agrupamentos de `app/service/grafix/` e `app/model/` (todos os models ficam em namespace global).

| # | Módulo | Pastas | Tabelas principais | Volume |
|---|---|---|---|---|
| 1 | **admin** (auth/users/groups/units) | `control/admin`, `model/admin`, `service/auth` | system_users, system_group, system_user_group, system_program, system_unit, system_preference | ~37 controllers |
| 2 | **builder** | `control/builder`, `service/builder` | (gera código) | 11 controllers |
| 3 | **comercial** (pedido de venda) | `control/comercial`, `service/grafix/vendas` | pedido_venda, pedido_venda_item, pedido_venda_historico, estado_pedido_venda, matriz_estado_pedido_venda | 12 controllers + 7 services |
| 4 | **communication** (mensagens / documentos) | `control/communication`, `model/communication` | system_message, system_notification, system_document* | 10 controllers |
| 5 | **configuracoes** (workflow / aprovadores) | `control/configuracoes` | aprovador, estado_pedido_venda, estado_pedido_venda_aprovador, etapa_pedido_venda_acoes, workflow_notification_rule | 7 controllers |
| 6 | **crm** (negociação/pré-venda) | `control/crm` | negociacao, negociacao_item, negociacao_atividade, negociacao_historico_etapa, etapa_negociacao, origem_contato, tipo_atividade | 26 controllers |
| 7 | **estoque** (produto/família/fabricante) | `control/estoque`, model `Produto*`, `MovimentoEstoque`, `service/grafix/EstoqueService` | produto, familia_produto, fabricante, tipo_produto, unidade_medida, movimento_estoque, tipo_movimento_estoque | 15 controllers + 1 service |
| 8 | **expedicao** (entregas) | `control/expedicao`, `control/grafix/expedicao`, `service/grafix/expedicao` | entrega, entrega_item, estado_entrega | 2 + 3 controllers + 2 services |
| 9 | **financeiro** (contas, fluxo de caixa) | `control/financeiro`, `service/grafix/financeiro` | conta, conta_anexo, conta_bancaria, fluxo_caixa, categoria, tipo_conta, forma_pagamento, condicao_pagamento, tipo_anexo | 31 controllers + 3 services |
| 10 | **install** | `control/install` | (instalador) | 4 controllers |
| 11 | **log** | `control/log`, `model/log`, `service/log` | system_access_log, system_change_log, system_sql_log, system_request_log, system_access_notification_log | 7 controllers |
| 12 | **pedidos** (visão de pedido p/ cliente) | `control/pedidos` | (usa pedido_venda) | 6 controllers |
| 13 | **pessoas** (cliente/fornecedor) | `control/pessoas`, model `Pessoa*` | pessoa, pessoa_contato, pessoa_endereco, pessoa_grupo, grupo_pessoa, tipo_cliente, categoria_cliente, cidade, estado | 17 controllers |
| 14 | **producao** | `control/producao`, `service/grafix/producao` | pedido_venda_item (estado_producao_item_id), estado_producao_item, item_producao_historico | 8 controllers + 2 services |
| 15 | **public/publico** (painel cliente externo) | `control/public`, `control/publico` | usa pessoa, conta | 4 controllers |
| 16 | **sac** (ouvidoria) | `control/sac` | ouvidoria, tipo_ouvidoria | 3 controllers |
| 17 | **supervisor** (notification engine + crontab errors) | `control/supervisor`, `service/grafix/vendas/channels` | notification_channel, notification_template, error_log_crontab | 4 controllers |
| 18 | **integrações externas** (CEP, CNPJ, e-mail, fake data) | `service/CEPService.php`, `CNPJService.php`, `SendGridMailService.php`, `FakeDataService.php`, `TempoService.php` | cep_cache, email_template | (services soltos) |

**Catálogo de modelos (82):** entidades de domínio em raiz (`PedidoVenda.php`, `Pessoa.php`, `Produto.php`, `Conta.php`, `Negociacao.php`, etc.) seguem padrão Active Record do Adianti — `extends TRecord`, com getters/setters gerados, hooks `onBeforeDelete`, e métodos compostos como `PedidoVenda::createFromNegociacao(...)`.

---

## 4. Padrões arquiteturais relevantes (para a migração)

### 4.1. Workflow declarativo via tabelas
A máquina de estados do pedido de venda é dirigida por **dados**, não por código:
- `estado_pedido_venda` — define cada estado (id, nome, cor, ordem, estado_inicial, estado_final, permite_edicao, permite_exclusao, **setor**).
- `matriz_estado_pedido_venda` — define transições válidas (origem → destino) e a **ação** disparada (`action_call`, `action_method`, `action_finaliza_etapa`).
- `aprovador` + `estado_pedido_venda_aprovador` — quem precisa aprovar para avançar de cada estado.
- `workflow_notification_rule` + `notification_template` + `notification_channel` — regras "quando entrou no estado X, notifique via canal Y com template Z".

**Reaproveitável:** sim, **conceito + schema + seeds**. A implementação PHP em `WorkflowService.php` (`getAcoesDisponiveis`) é simples (105 linhas) e migra facilmente para Python.

Estados produtivos em `estado_producao_item` têm flags `is_start`, `is_work`, `is_paused`, `is_waiting`, `is_end` — design limpo.

### 4.2. Camada `service/grafix/` é o núcleo limpo
Diferente do resto do legado (que mistura UI + regra), `service/grafix/` traz:
- `declare(strict_types=1);`
- Namespaces (`App\Service\Grafix\Financeiro`)
- Docblocks com versão e changelog em cada arquivo
- Métodos com tipagem (entrada e retorno)
- Transações explícitas (`TTransaction::open/close/rollback`)

Exemplos de métodos com regra real:
- `FinanceiroBaixaService::liquidar` / `estornarBaixa` / `baixarContaParcialmente` (272 linhas)
- `FinanceiroLancamentoService::gerarContasFromPedido` / `cancelarContasPorPedido` (190 linhas)
- `FluxoCaixaService::lancarAvulso` / `registrarMovimentoCaixa` / `removerMovimentoCaixa` (142 linhas)
- `PedidoVendaService::salvarPedido` / `avancarStatus` / `gerarFinanceiro` / `salvarPrecificacao` / `cancelarPedido` / `recalcularTotalPedido` (404 linhas)
- `ProducaoService::iniciarOuRetomarProducao` / `pausarProducao` / `concluirItemProducao` / `registrarApontamento` (252 linhas)
- `ExpedicaoService::criarEntregaAutomatica` / `despacharEntrega` / `concluirEntrega` / `retornarEntrega` (349 linhas)
- `EstoqueService::registrarSaidaMateriaPrima` / `registrarEntradaProdutoAcabado` (64 linhas)

**Total da camada `grafix/`:** ~2.500 linhas de PHP estritamente tipado e tranquilo de portar para Python (Pydantic + SQLAlchemy + um service por arquivo).

### 4.3. Camada `app/control/` é descartável (em sua forma atual)
Cada controller é uma classe que estende `TWindow`/`TPage` do Adianti e **constrói a UI server-side** — botões, formulários, datagrids, kanban, callbacks JS. Exemplos:
- `PedidoVendaForm.php` (654 linhas) — monta o formulário de pedido linha a linha em PHP.
- `ContaReceberForm.php` (228 linhas) — idem.
- `ProdutoForm.php` (274 linhas) — idem.

**Não migram para React.** O que importa nesses arquivos é:
- **Quais campos a tela tem** (referência funcional).
- **Quais validações o controller faz antes de chamar o service** (pode haver regra implícita).
- **Quais ações o usuário dispara** (mapa de operações para a futura API).

### 4.4. Models como Active Record + relacionamentos
`app/model/*.php` são classes Adianti que herdam de `TRecord`. Características úteis:
- Constantes `TABLENAME`, `PRIMARYKEY`, `IDPOLICY`, `CREATED_BY_USER_ID`, `UPDATEDAT`, `DELETEDAT`, `CREATEDAT`, `UPDATED_BY_USER_ID` — **soft delete + auditoria já no design**.
- Relacionamentos via setters tipados (`set_cliente(Pessoa $object)`).
- Métodos `getX()` que retornam coleções (1:N).
- Hooks `onBeforeDelete()` com regras (ex: `Conta::onBeforeDelete()`).
- Métodos de domínio: `Conta::get_status()`, `PedidoVenda::createFromNegociacao(...)`.

**O design é informativo**, mas o código em si é Adianti-específico. Migra-se para Pydantic + SQLAlchemy mantendo o **shape** das entidades.

### 4.5. Schema PostgreSQL maduro
- 68 tabelas, FKs explícitas, padrões de auditoria (`created_at`, `updated_at`, `deleted_at`, `created_by`, `updated_by`).
- Seeds essenciais em `minierp-inserts.sql` (estados, tipos, etapas) — preservar.
- IDs reservados especiais (ex: `estado_pedido_venda` 1=ORÇAMENTO, 100=FINALIZADO, 101=REPROVADO, 999=CANCELADO).

### 4.6. Sinais de tech-debt
- `vendor/` (Composer) usa `dev-master` em 6 deps internas (`adianti/plugins`, `adianti/pdfdesigner`, `pablodalloglio/*`) — não vão sobreviver à migração.
- `app/control/builder/` é a ferramenta interna de geração de código do Adianti — descartar inteiro.
- `app/control/install/` é instalador legado — descartar.
- 6 menus XML diferentes (`menu.xml`, `menu-dist.xml`, `menu-mobile.xml`, `menu-navbar-dropdown.xml`, `menu-public.xml`, `menu-public-mobile.xml`, `top_menu.xml`) — sinal de evolução incremental sem refactor.
- `MadRestServer.php`, `cmd.php`, `db-mad-manager.php` na raiz — bootstraps específicos do framework.

---

## 5. Classificação por módulo

Legenda:
- **Reaproveitar** — schema, regras e/ou código portam-se com pouca adaptação.
- **Adaptar** — conceito serve, mas precisa reescrita no stack-alvo.
- **Descartar** — específico do framework legado ou fora de escopo provável do GO.
- **Dúvida** — depende de decisão de produto pendente (ver §8).

| # | Módulo | Decisão | Confiança | Justificativa |
|---|---|---|---|---|
| 1 | admin (users/groups/units/2FA) | **Adaptar** | Alta | Schema (`system_users`, `system_group`, `system_user_group`, `system_program`, `system_unit`) é genérico e bom. Mas autenticação/2FA/permissões são acopladas ao Adianti — refazer com lib Python (ex: `python-jose`+`passlib`+ próprio middleware ou Authlib). Manter conceito de "unit" se GO for multi-tenant (**dúvida**). |
| 2 | builder | **Descartar** | Alta | Ferramenta de geração de código do framework PHP. Inútil em Python+React. |
| 3 | comercial (pedido de venda) | **Reaproveitar** (schema + service) / Adaptar (controllers) | Alta | `PedidoVendaService` (404 linhas) e `WorkflowService` (105 linhas) traduzem-se bem. Schema `pedido_venda*` + `matriz_estado_pedido_venda` é excelente. Forms/Kanban são UI Adianti — descartar. |
| 4 | communication (mensagens / documentos internos) | **Dúvida** | Média | Útil se GO precisar de mensageria/docs internos; descartar se for substituído por integração externa (Slack, Discord, Drive). |
| 5 | configuracoes (workflow rules) | **Reaproveitar** (schema) | Alta | Tabelas de configuração de workflow são reuso direto. UI é descartável. |
| 6 | crm (negociação/pré-venda) | **Adaptar** | Média-Alta | Modelo de negociação (funil → kanban → ordem) é boa referência. Tem 26 controllers Adianti + `NegociacaoService.php` minúsculo (3 métodos). A maior parte da lógica está nos controllers — perigoso, vai exigir leitura cuidadosa antes de portar. |
| 7 | estoque (produto / movimento) | **Reaproveitar** (schema + service) / Adaptar (controllers) | Alta | Schema rico (produto, familia, fabricante, unidade, movimento_estoque). `EstoqueService` é direto. `ProdutoService::gerarBarcode/gerarQrCode` substitui-se por libs Python equivalentes (python-barcode, qrcode). |
| 8 | expedicao (entregas) | **Reaproveitar** (schema + service) | Alta | Schema (entrega, entrega_item, estado_entrega) + `ExpedicaoService` (349 linhas) bem-feito. |
| 9 | financeiro (contas + fluxo) | **Reaproveitar** (schema + service) | Muito Alta | É o **melhor pedaço de código** do legado. `FinanceiroBaixaService`, `FinanceiroLancamentoService`, `FluxoCaixaService` são candidatos a migração 1:1. Schema (`conta`, `fluxo_caixa`, `tipo_conta`, `forma_pagamento`, `condicao_pagamento`, `categoria`, `tipo_anexo`, `conta_bancaria`) é maduro. |
| 10 | install | **Descartar** | Alta | Instalador do framework legado. |
| 11 | log (access/change/sql/request) | **Adaptar** | Média | Schema dos logs é reusável. Mecanismo (intercepta tudo via Adianti) é específico do framework — refazer com middleware FastAPI/Django + structlog/audit-log dedicado. |
| 12 | pedidos (visão de pedido p/ cliente) | **Adaptar** | Média | Sobreposto com "publico" — possivelmente mesma feature em duas pastas. Confirmar antes de planejar. |
| 13 | pessoas (clientes/contato/endereco) | **Reaproveitar** (schema) / Adaptar (lógica) | Muito Alta | Entidade central. Schema completo (pessoa, pessoa_contato, pessoa_endereco, pessoa_grupo, grupo_pessoa, tipo_cliente, categoria_cliente, cidade, estado). Sem service grafix — lógica espalhada entre `PessoaForm.php` e `model/Pessoa.php` (1.319 linhas, mas a maior parte é getter/setter/relacionamento). **Risco:** parte do código de validação pode estar no controller. |
| 14 | producao | **Reaproveitar** (schema + service) | Alta | `ProducaoService` (252 linhas) cobre iniciar/pausar/concluir/apontamento. Schema (`estado_producao_item`, `item_producao_historico`, campos `qtde_produzida` em `pedido_venda_item`) é simples e direto. Kanban UI é descartável. |
| 15 | public/publico (painel cliente externo) | **Dúvida** | Média | GO terá portal cliente público? Se sim, **adaptar**. Se não, **descartar**. |
| 16 | sac (ouvidoria) | **Dúvida** | Baixa | Ouvidoria é nicho — confirmar se faz parte do GO. |
| 17 | supervisor (notification engine + crontab errors) | **Adaptar** | Média-Alta | `notification_template/channel` + `service/grafix/vendas/channels` (Email/SystemNotification + Interface) é design bom — porta para Celery/RQ + canais (E-mail, Telegram, WhatsApp via Evolution). `error_log_crontab` substitui-se pelo logger do scheduler do GO. |
| 18 | integrações (CEP, CNPJ, e-mail, etc.) | **Adaptar** | Alta | `CEPService`/`CNPJService` reutilizam APIs públicas (ViaCEP, ReceitaWS) — porta-se em 30 minutos. `SendGridMailService` substitui-se conforme stack-alvo. `cep_cache` table reusável. `FakeDataService` é só seed; descartar. |

**Resumo numérico:**
- Reaproveitar (schema/service direto): **6 módulos** (comercial, configuracoes, estoque, expedicao, financeiro, producao)
- Adaptar: **6 módulos** (admin, crm, log, pedidos, pessoas, supervisor) + integrações
- Descartar: **3 módulos** (builder, install, view-Adianti em todos os módulos)
- Dúvida: **3 módulos** (communication, public/publico, sac)

---

## 6. Regras de negócio reaproveitáveis (concretas)

Lista priorizada do que vale a pena ler/portar com cuidado:

### Vendas
- `PedidoVendaService::salvarPedido` — calcula total do pedido a partir dos itens, valida estados, cria histórico.
- `PedidoVendaService::avancarStatus` (e `avancarStatus_DB`) — máquina de estados respeitando `matriz_estado_pedido_venda`.
- `PedidoVendaService::gerarFinanceiro` — gera contas a receber a partir do pedido + condição de pagamento.
- `PedidoVendaService::salvarPrecificacao` — recalcula preço unitário/total após edição.
- `WorkflowService::getAcoesDisponiveis` — dado um pedido, retorna quais transições o usuário pode disparar (depende de setor + papel).
- `PedidoVenda::createFromNegociacao` — converte negociação em pedido (CRM → Vendas).

### Financeiro
- `FinanceiroLancamentoService::gerarContasFromPedido` — quebra valor total em parcelas conforme condição de pagamento.
- `FinanceiroBaixaService::liquidar` — orquestra liquidação total/parcial, valida FKs, abre transação.
- `FinanceiroBaixaService::baixarContaParcialmente` — gera "conta residual" mantendo `pedido_venda_id` (correção citada no docblock).
- `FinanceiroBaixaService::estornarBaixa`.
- `FluxoCaixaService::registrarMovimentoCaixa` / `removerMovimentoCaixa` — vínculo de cada baixa com lançamento de caixa na conta bancária.
- `Conta::get_status()` (model) — status derivado da combinação `valor_pago/valor/dt_pagamento`.

### Estoque & Produção
- `EstoqueService::registrarSaidaMateriaPrima` (consumo na produção) e `registrarEntradaProdutoAcabado` (PA finalizado).
- `ProducaoService::iniciarOuRetomarProducao` — primeira ação muda estado do pedido se for a primeira do conjunto.
- `ProducaoService::concluirItemProducao` — verifica se todos os itens do pedido estão prontos e avança pedido.
- `ProducaoService::registrarApontamento` — log de quantidade produzida + observação.
- Regras `pode*` (`podeIniciarOuRetomar`, `podePausar`, `podeConcluir`, `podeRegistrarApontamento`) — invariantes de estado.

### Expedição
- `ExpedicaoService::criarEntregaAutomatica` (a partir de pedido) e `criarEntrega` (manual).
- `ExpedicaoService::despacharEntrega` / `concluirEntrega` (com nome/CPF do recebedor) / `retornarEntrega` (com motivo).
- `ExpedicaoService::getItensDisponiveisParaEntrega` — calcula `quantidade - qtde_entregue`.
- Verificação automática "entrega concluída → avança pedido".

### CRM
- `NegociacaoService::podeEditar` / `podeExcluir` — invariantes baseados em estado da negociação.
- (Maior parte da lógica está nos controllers `crm/*` — exigirá leitura caso-a-caso antes da migração.)

### Auxiliares
- `CEPService::get` (com cache em `cep_cache`).
- `CNPJService::get`.
- `ProdutoService::gerarBarcode` / `gerarQrCode` (substituíveis por libs Python).

### Conceitos transversais (portar como padrão, não como código)
- **Soft delete + auditoria embutidos** — `deleted_at`, `created_at`, `updated_at`, `created_by`, `updated_by` em quase toda tabela.
- **Workflow data-driven** — estados, transições e notificações em tabelas (não hardcoded).
- **Aprovadores por estado** — `aprovador` + `estado_pedido_venda_aprovador`.
- **Notificação multi-canal com templates** — `notification_channel` + `notification_template` + `workflow_notification_rule`.
- **IDs especiais reservados** (1=ORÇAMENTO, 100=FINALIZADO, 999=CANCELADO) — manter no seed do GO ou redesenhar.

---

## 7. Módulo piloto sugerido

### Recomendação: **Pessoas + Produtos** (combinados, primeiro slice end-to-end)

**Por quê pessoas?**
- É raiz de quase todas as outras entidades (FK em pedido_venda, conta, negociacao, entrega, nota_fiscal).
- Schema completo e estável (pessoa, pessoa_contato, pessoa_endereco, pessoa_grupo, tipo_cliente, categoria_cliente, cidade, estado).
- Lógica simples de CRUD + classificação (cliente/fornecedor/transportadora via tipo_cliente).
- Permite exercitar toda a stack: schema → ORM → API → React form/list → testes.
- Integra com `CEPService` e `CNPJService` (regras de negócio leves para validar a escolha de stack).

**Por quê produtos junto?**
- Segunda raiz mais usada (FK em pedido_venda_item, movimento_estoque, nota_fiscal_item).
- Schema rico mas direto (produto + familia_produto + fabricante + tipo_produto + unidade_medida).
- Lógica auxiliar leve (`gerarBarcode/gerarQrCode`) confirma que libs equivalentes Python servem.
- Sem dependência de workflow complexo — mantém o piloto pequeno.

**Por quê NÃO escolher financeiro como piloto** (apesar do código grafix ser o melhor):
- Financeiro depende de Pessoas (cliente/fornecedor) e de Pedido (origem da conta a receber).
- Migrar financeiro primeiro força stubs ou seeds, gerando retrabalho.
- Financeiro exige decisões de schema multi-tenant antes (contas têm origem em pedido_venda — herda multi-tenant se houver).

**Por quê NÃO Pedido de Venda como piloto:**
- Maior módulo do legado, com workflow complexo e ~12 telas + 7 services interligados. Risco alto de o piloto não fechar em poucos dias.

**Plano sugerido para o piloto (a ser detalhado por @compass-planner):**
1. Schema PostgreSQL: `pessoa`, `pessoa_endereco`, `pessoa_contato`, `tipo_cliente`, `categoria_cliente`, `cidade`, `estado`, `cep_cache`, `produto`, `familia_produto`, `fabricante`, `tipo_produto`, `unidade_medida`. Adaptar para snake_case + `tenant_id` se aplicável.
2. ORM (SQLAlchemy ou Tortoise) + migrations (Alembic).
3. API REST mínima (FastAPI sugerido): CRUD pessoa, CRUD produto, integração CEPService.
4. React: lista + form para Pessoa, lista + form para Produto.
5. Testes unitários do service + integração da API.
6. Validação com Eduardo: "esse modelo serve como base para o resto do GO?"

**Validação esperada do piloto:** o usuário deve ser capaz de cadastrar um cliente (com endereço auto-preenchido por CEP) e cadastrar um produto, ambos via UI React → API Python → PostgreSQL. Se o piloto roda, a stack está validada.

---

## 8. Open Questions — Decisões registradas (2026-05-06)

> Respondidas por Eduardo em sessão de discovery com @oracle. Prontas para @compass-planner produzir o PRD/Plano.

### Q1 — Escopo funcional ✅ DECIDIDO
**Todos os 18 módulos do legado são replicados no GO.** Não há corte de escopo. Expedição e Produção receberão melhorias e correções de fluxo além da simples replicação.

### Q2 — Stack Python ✅ DECIDIDO
**Django 5 + Django REST Framework + djangorestframework-simplejwt + Celery + Redis + PostgreSQL.**

Justificativa: Django é o melhor "menor cenário seguro" para ERP com time de agentes — auth, permissões, ORM, migrations e admin já incluídos; estrutura previsível por módulo (`models/serializers/services/selectors/views/urls/permissions/tests`) reduz decisão por run dos agentes.

### Q3 — Stack React ✅ DECIDIDO
**React 18 + TypeScript + Vite + PrimeReact + Tailwind CSS + TanStack Query + React Hook Form + Zod.**

PrimeReact cobre DataTable, filtros, paginação, autocomplete, calendário, modais e formulários — ~80% das telas de ERP sem componente custom. Guardrails obrigatórios: `agent-instructions.md` + `coding-standards.md` no repositório, padrão rígido de módulo frontend (`pages/components/services/hooks/types/routes.tsx`).

### Q4 — Multi-empresa ✅ DECIDIDO
**`empresa_id` em todas as tabelas de domínio.** Banco compartilhado quando o grupo de empresas tem a mesma natureza de negócio (ex: 3 lojas de roupa do mesmo dono). Banco separado por CNPJ quando as naturezas são distintas (ex: loja de roupa + restaurante). A decisão de banco compartilhado ou isolado ocorre no onboarding, não no código. Django middleware injeta `empresa_id` no contexto da request; ORM Mixin aplica filtro automático em todos os models de domínio.

Schema:
```
empresa (id, cnpj, razao_social, grupo_id, ...)
pedido_venda (id, empresa_id FK→empresa, ...)
conta (id, empresa_id FK→empresa, ...)
```

### Q5 — Migração de dados ✅ DECIDIDO
**GO parte do zero — sem migração de dados.** Legado é referência funcional e de regras de negócio, não fonte de dados. Liberdade total para redesenhar schema, nomenclatura e fluxos sem compatibilidade retroativa.

### Q6 — Integrações externas ✅ DECIDIDO
Arquitetura de **proxy com múltiplos providers** por categoria — Strategy Pattern + Fallback/Rate-limit Router:

| Proxy | Providers iniciais | Operações |
|---|---|---|
| **Proxy Fiscal** | Focus NFe, Plug Nota, eNotas (SaaS) | NF-e, NF-Ce, eventos fiscais |
| **Proxy Bancário** | Banco Inter, Asaas | Boleto, PIX, consulta extrato |
| **Proxy CEP** | ViaCEP, OpenCEP, BrasilAPI | Autopreenchimento de endereço com rate-limit routing |
| **Proxy CNPJ** | ReceitaWS, BrasilAPI | Consulta por CNPJ com rate-limit routing |

Integrações adicionais:
- **E-mail SMTP** — notificações transacionais, envio de NF-e, cobranças
- **Barcode / QR Code** — etiquetas de produto (`python-barcode` + `qrcode`)
- **Módulos de importação** (one-way, entrada de dados): Asaas, Bling, Omie
- **API Legado** — endpoints REST no GO para receber dados do Emporion (Delphi) — fluxo unidirecional
- **WhatsApp (Evolution API)** e **Telegram** — fases posteriores (não v1)

Estrutura no Django:
```
apps/integrations/
├── fiscal/proxy.py + interface.py + providers/
├── banking/proxy.py + interface.py + providers/
├── cep/proxy.py + interface.py + providers/
└── cnpj/proxy.py + interface.py + providers/
```

### Q7 — Workflow de pedido de venda ✅ DECIDIDO
**Redesenha mantendo o conceito data-driven.** O design do legado (estados e transições configuráveis em banco, aprovadores por estado, notificações por regra) é excelente e será preservado como padrão arquitetural. Os estados específicos (ORÇAMENTO, FINALIZADO, etc.) e as transições serão redefinidos para o que o GO precisa — não é replicação do legado.

### Q8 — Workflow de produção ✅ DECIDIDO (com redesenho significativo)
**Maior mudança arquitetural em relação ao legado.** O legado acopla produção diretamente ao pedido de venda (`pedido_venda_item.estado_producao_item_id`). O GO desacopla: a entidade central passa a ser a **Ordem de Produção (OP)**, que existe independentemente de pedido.

**Dois modelos de negócio suportados pelo mesmo módulo:**

*Modelo 1 — Sob demanda (trigger: pedido)*
```
Cliente faz pedido → pedido aprovado → sistema gera OP automaticamente
→ Produção executa → itens entram no estoque (baixa nas matérias-primas)
→ Pedido sinalizado "produção concluída" → segue para expedição
```

*Modelo 2 — Reposição de estoque (trigger: ruptura ou decisão manual)*
```
Estoque abaixo do mínimo (ou decisão manual)
→ Sistema gera OP independente (ex: "Produzir 100 sacos de ração 60kg")
→ Produção executa → produto acabado entra no estoque + baixa nas matérias-primas
→ OP encerra em si mesma (nenhum pedido vinculado)
```

**Schema central (novo — não existe no legado):**
```
ordem_producao
├── empresa_id
├── origem            ← enum: PEDIDO | ESTOQUE | MANUAL
├── pedido_venda_id   ← nullable (só quando origem=PEDIDO)
├── status            ← data-driven via estado_ordem_producao

ordem_producao_item
├── ordem_producao_id
├── produto_id        ← produto a fabricar
├── quantidade / quantidade_produzida
├── status_item       ← data-driven

ordem_producao_item_mp   ← matérias-primas por item
├── item_id
├── produto_id        ← matéria-prima
├── quantidade_necessaria / quantidade_consumida
```

Ao concluir a OP: `movimento_estoque` de saída para cada MP consumida + entrada para cada produto acabado. Se `origem=PEDIDO`, sinaliza o pedido vinculado.

---

### Questões diferidas (responder após piloto Pessoas+Produtos)

9. **Notificações** — Mantém design declarativo (`notification_template` + `notification_channel` + `workflow_notification_rule`) ou usa event bus em código?

### Diferidas para após o piloto
10. **Portal cliente público** (`control/public/`) — confirmado no escopo (Q1), detalhar fluxo no PRD do módulo.
11. **Mensageria interna + documentos** — confirmado no escopo (Q1), detalhar no PRD do módulo communication.
12. **Ouvidoria (SAC)** — confirmado no escopo (Q1), detalhar no PRD do módulo sac.
13. **Auditoria** — GO usa `audit_log` universal (tabela `audit_log` com before/after_data) via Django signals. Mais robusto que o legado.
14. **2FA** — escopo do módulo accounts, detalhar no PRD de admin/accounts.
15. **Internacionalização** — GO é pt-BR. Sem i18n na v1.
16. **Soft delete** — GO mantém o padrão `deleted_at` em todas as tabelas de domínio. Django ORM Mixin aplica filtro automático.

### Riscos não-funcionais (mantidos para @apex-architect)
17. **Banco do GO:** parte do zero (Q5) — sem conflito com legado.
18. **Performance:** a definir no PRD do módulo específico.
19. **LGPD:** campos de consentimento e exclusão sob demanda a especificar no módulo pessoas.
20. **Testes:** GO arranca com TDD. @grid-tester é responsável. Cobertura mínima definida no ADR de stack.

---

## 9. Premissas que estou assumindo (validar com Eduardo)

1. O destino do código Python+React do GO é **um repositório novo, separado do EvoNexus**. Não estou propondo migrar para dentro deste workspace.
2. **PostgreSQL** será o banco do GO (compatível com `minierp-pgsql.sql`). Se for MySQL/Mongo/outro, refazer adaptação do schema.
3. O **objetivo da migração não é paridade funcional 100%** com o legado. É construir base útil para o GO usando o legado como referência. (Já está explícito no contexto.)
4. **Não há usuários ativos** no MiniERP cuja experiência seja preservada — não há restrição de UX retro-compatível.
5. O legado é **fonte de verdade só para regras já validadas em produção**. Onde houver dúvida, o GO redesenha (já está nas regras: "Não assumir que uma regra de negócio está correta só porque existe no legado").
6. O **prazo de 7 dias** referido no contexto é para a **fase 1 da migração** (discovery + base + piloto), não para migração completa.

---

## 10. Riscos e armadilhas

| # | Risco | Impacto | Mitigação |
|---|---|---|---|
| R1 | Lógica espalhada entre Form (controller) e Service em módulos sem `grafix/` (pessoas, crm) | Alto | Antes de portar, fazer pass de leitura nos `*Form.php` para extrair validações implícitas. |
| R2 | Schema com soft-delete em quase tudo — esquecer o filtro `deleted_at IS NULL` em queries da nova API | Alto | Aplicar filtro globalmente no ORM (event listener ou Mixin). |
| R3 | IDs reservados (1=ORÇAMENTO, 100/101/999) — replicação de seeds essenciais é fácil de esquecer | Médio | Criar pacote de seeds explícito desde o piloto. |
| R4 | Dependências PHP (`adianti/plugins`, `pablodalloglio/*` em dev-master) não têm contrapartida 1:1 em Python | Médio | Mapear caso a caso (PDF → reportlab/weasyprint; barcode → python-barcode; QR → qrcode; e-mail → smtplib/aiosmtp). |
| R5 | `MadRestServer.php` + middlewares do legado podem ter regras de auth/autorização escondidas | Médio | Tratar como referência, redesenhar auth do zero. |
| R6 | `app/control/builder/` faz introspecção de schema e gera código — confundir com módulo de domínio | Baixo | Já marcado como Descartar; documentar para evitar confusão futura. |
| R7 | Fluxo `Negociacao → PedidoVenda` (`PedidoVenda::createFromNegociacao`) é regra cross-módulo crítica | Alto | Garantir que CRM e Vendas migrem juntos ou que haja stub estável entre eles. |
| R8 | "Tudo controller" para mensageria/documentos (`control/communication/`) — sem service externo | Médio | Reescrever do zero se mensageria entrar no escopo. |
| R9 | Possível duplicação entre `control/pedidos/` e `control/publico/FinanceiroClientePublicoList.php` | Baixo | Confirmar com Eduardo antes de modelar. |
| R10 | Integrações externas do legado (CEP, CNPJ, e-mail) podem ter chaves/secrets hard-coded | Alto | Auditar `app/config/` e `service/SendGridMailService.php` antes de qualquer reuso (já vetado pela regra "não expor secrets"). Buscar `apikey`, `password`, `token` no fonte. |

---

## 11. Próximos passos (discovery concluído — todas as decisões registradas)

1. **`@compass-planner`** lê este discovery e produz:
   - `[C]prd-migracao-minierp-adianti-python-react.md` — PRD do piloto (Pessoas+Produtos)
   - `[C]plan-migracao-minierp-adianti-python-react.md` — plano de 3-6 passos para o piloto
2. **`@apex-architect`** define ADR de stack em `[C]architecture-migracao-minierp-adianti-python-react.md`:
   - Django 5 + DRF + simplejwt + Celery + Redis
   - React 18 + TypeScript + Vite + PrimeReact + Tailwind
   - Padrão de módulo Django (`models/serializers/services/selectors/views/urls/permissions/tests`)
   - Padrão de módulo React (`pages/components/services/hooks/types/routes.tsx`)
   - Proxy pattern para integrações externas
   - Middleware empresa_id + ORM Mixin para multi-empresa
   - TDD obrigatório com @grid-tester
3. **`@bolt-executor`** executa o piloto (Pessoas + Produtos).
4. **`@oath-verifier`** verifica entrega do piloto contra PRD.
5. Após piloto validar a stack → abrir tickets MIG-02..MIG-N por módulo:
   - MIG-02: Financeiro (melhor código grafix/ do legado)
   - MIG-03: Vendas + Workflow de pedido redesenhado
   - MIG-04: Estoque
   - MIG-05: Produção (com melhorias de fluxo)
   - MIG-06: Expedição (com melhorias de fluxo)
   - MIG-07: CRM
   - MIG-08..N: Admin, Supervisor, SAC, Communication, Portal Cliente, Fiscal, Cobranças, Integrações

---

## 12. Anexos

### 12.1. Lista das 68 tabelas (PostgreSQL)
api_error, aprovador, categoria, categoria_cliente, cep_cache, cidade, condicao_pagamento, conta, conta_anexo, conta_bancaria, email_template, entrega, entrega_item, error_log_crontab, estado, estado_entrega, estado_pedido_venda, estado_pedido_venda_aprovador, estado_producao_item, etapa_negociacao, fabricante, familia_produto, fluxo_caixa, forma_pagamento, grupo_pessoa, item_producao_historico, matriz_estado_pedido_venda, movimento_estoque, negociacao, negociacao_arquivo, negociacao_atividade, negociacao_historico_etapa, negociacao_item, negociacao_observacao, nota_fiscal, nota_fiscal_item, notification_channel, notification_template, origem_contato, ouvidoria, pedido_venda, pedido_venda_historico, pedido_venda_item, pedido_venda_item_anexo, pessoa, pessoa_contato, pessoa_endereco, pessoa_grupo, produto, system_group, system_group_program, system_preference, system_program, system_unit, system_user_group, system_user_program, system_users, system_user_unit, tipo_anexo, tipo_atividade, tipo_cliente, tipo_conta, tipo_movimento_estoque, tipo_ouvidoria, tipo_pedido, tipo_produto, unidade_medida, workflow_notification_rule.

### 12.2. Volumetria do código
- `app/control/`: 223 arquivos `.php` (UI + handlers)
- `app/model/`: 82 arquivos `.php` (Active Record)
- `app/service/`: 67 arquivos `.php` (services — destaque para `grafix/` com ~2.500 linhas estritamente tipadas)
- `app/lib/`: helpers internos (barcode, builder, html, menu, reports, util, validator, widget)
- `app/database/`: schemas em 6 SGBDs (pgsql, mysql, oracle, sqlite, fbird, mssql) + seeds + .db (sqlite) iniciais

### 12.3. Arquivos-chave para leitura prioritária pelo time da migração
- `app/database/minierp-pgsql.sql` — fonte de verdade do modelo de dados.
- `app/database/minierp-inserts.sql` — seeds (estados, tipos, etapas).
- `app/service/grafix/financeiro/FinanceiroBaixaService.php` — exemplo do "código bom" do legado.
- `app/service/grafix/vendas/PedidoVendaService.php` — coração do workflow de venda.
- `app/service/grafix/producao/ProducaoService.php` — workflow de produção.
- `app/service/grafix/expedicao/ExpedicaoService.php` — workflow de expedição.
- `app/model/PedidoVenda.php` — relacionamentos da entidade central.
- `app/model/Pessoa.php`, `app/model/Produto.php`, `app/model/Conta.php` — entidades raiz.
- `menu.xml` — mapa funcional do sistema (perspectiva do usuário final).

