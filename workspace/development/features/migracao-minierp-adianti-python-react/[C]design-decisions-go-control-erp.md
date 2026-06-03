---
author: canvas-designer
type: design-decisions
date: 2026-05-07
feature: migracao-minierp-adianti-python-react
status: aprovado
---

# Design Decisions — GO Control ERP (Step 4.5)

> Documento de referência de UI/UX. Todas as decisões aqui são **vinculantes** para o Step 5 e devem ser seguidas sem exceção. Qualquer desvio requer revisão explícita neste documento.

---

## 1. Direção Estética e Tom

**Mood:** ERP operacional de alta densidade — estilo **terminal profissional**, não "app bonito".

O operador de estoque/vendas trabalha 8h/dia com essa interface. Cada segundo economizado em uma busca de produto ou cadastro de cliente multiplica por centenas de operações por mês. A interface prioriza:

- **Densidade de informação** sem ser opressiva: linhas compactas, margens calibradas, não espaçosas
- **Legibilidade numérica** como primeiro cidadão: valores monetários, códigos, quantidades precisam de fonte mono onde faz sentido
- **Escuro por padrão (v0.1)**: reduz fadiga visual em turnos longos; o operador não precisa de uma tela branca brilhante às 14h debaixo do sol do interior do Ceará
- **Operabilidade por teclado**: Tab, Enter, Esc — o usuário avançado não toca no mouse para cadastros

**Tom comprometido:** Sério, denso, confiável. Não "moderno e belo". Não gradiente. Não cards flutuantes. Não animações de entrada em cada elemento.

**O que diferencia do genérico:**
- Tema escuro com sidebar coerente (não o padrão azul-claro do Lara Light)
- IBM Plex Sans — projetada pela IBM para interfaces densas de dados, com variante Mono nativa
- Paleta com toque industrial: cinza-ardósia como base, azul-marinha profundo como primária, âmbar como accent operacional
- Sidebar colapsível com mini-mode de ícones — padrão ERP profissional, não SaaS marketing

---

## 2. Paleta de Cores

### Tokens principais

| Token | Nome | Hex | Uso |
|---|---|---|---|
| `--color-primary` | Azul Índigo | `#4F6AF5` | Botões primários, links ativos, foco |
| `--color-primary-dark` | Índigo Profundo | `#3B5BDB` | Hover em primário |
| `--color-accent` | Âmbar Operacional | `#F59E0B` | Badges de atenção, ícones de alerta, estoque baixo |
| `--color-surface-0` | Superfície Base | `#0F1117` | Background da página (corpo principal) |
| `--color-surface-1` | Superfície Card | `#1A1D26` | Cards, panels, DataTable header |
| `--color-surface-2` | Superfície Elevada | `#22263A` | Modals, dropdowns, tooltips |
| `--color-sidebar-bg` | Sidebar | `#13151F` | Background da sidebar |
| `--color-topbar-bg` | Topbar | `#1A1D26` | Background da topbar |
| `--color-border` | Borda | `#2E3347` | Bordas gerais, divisores |
| `--color-text-primary` | Texto Principal | `#E8EAF0` | Labels, headings, valor principal |
| `--color-text-secondary` | Texto Secundário | `#8B90A8` | Captions, placeholders, metadados |
| `--color-text-muted` | Texto Atenuado | `#545870` | Informação terciária |

### Tokens semânticos

| Token | Hex | Uso |
|---|---|---|
| `--color-success` | `#22C55E` | Status ativo, confirmação, estoque OK |
| `--color-warning` | `#F59E0B` | Atenção, estoque baixo, pendente |
| `--color-error` | `#EF4444` | Erros, inativo, cancelado |
| `--color-info` | `#60A5FA` | Informação neutra, tooltips |

### Dark mode v0.1

**Dark mode é o padrão único para v0.1.** Light mode é roadmap pós-MVP. Não implementar toggle agora — aumenta complexidade sem valor imediato para o operador.

---

## 3. Tipografia

### Família principal: IBM Plex Sans

**Justificativa técnica:** Inter é a fonte padrão de 80% dos dashboards SaaS. IBM Plex Sans tem caráter industrial, foi projetada para interfaces densas de dados, tem excelente legibilidade em corpo pequeno (12px), inclui variante Mono para valores numéricos e é gratuita via Google Fonts.

**NUNCA usar:** Inter, Roboto, system-ui como fonte display/body.

### Escala tipográfica

| Role | Família | Tamanho | Peso | Uso |
|---|---|---|---|---|
| `--text-display` | IBM Plex Sans | 24px | 600 | Títulos de página (h1) |
| `--text-heading` | IBM Plex Sans | 18px | 600 | Títulos de seção (h2) |
| `--text-subheading` | IBM Plex Sans | 14px | 600 | Sub-seções, labels de grupo |
| `--text-body` | IBM Plex Sans | 14px | 400 | Texto geral, células de tabela |
| `--text-label` | IBM Plex Sans | 12px | 500 | Labels de campo, headers de coluna |
| `--text-caption` | IBM Plex Sans | 11px | 400 | Metadados, timestamps, versão |
| `--text-mono` | IBM Plex Mono | 13px | 400 | CPF/CNPJ, códigos de barras, preços |

### Import (Google Fonts — adicionar ao index.html)

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
```

---

## 4. Layout Base

### Estrutura geral

```
┌──────────────────────────────────────────────────────────┐
│ TOPBAR (h-12, bg-surface-1, border-b)                    │
│  [logo/empresa ativa]              [user] [company] [sair]│
├─────────────────┬────────────────────────────────────────┤
│ SIDEBAR         │ CONTEÚDO PRINCIPAL                      │
│ w-60 (240px)    │ flex-1, bg-surface-0, overflow-auto     │
│ colapsível      │ p-6                                     │
│ → mini: w-14   │                                         │
│   (56px, icons) │                                         │
└─────────────────┴────────────────────────────────────────┘
```

### Sidebar

- **Largura expandida:** 240px (`w-60`)
- **Largura colapsada (mini-mode):** 56px (`w-14`) — apenas ícones, tooltip ao hover
- **Comportamento de colapso:** botão de toggle no rodapé da sidebar (ícone `pi-chevrons-left` / `pi-chevrons-right`)
- **Persistência:** estado salvo em `localStorage['sidebar_collapsed']`
- **Background:** `#13151F` (mais escuro que o conteúdo — cria hierarquia visual)
- **Item ativo:** highlight com `bg-primary/10` + borda esquerda `border-l-2 border-primary`
- **Item hover:** `bg-surface-2` (sem animação excessiva)
- **Separadores de grupo:** label de categoria em caps pequenas `text-[10px] text-text-muted tracking-widest`

### Topbar

- **Altura:** 48px (`h-12`)
- **Conteúdo esquerdo:** Logo "GO Control" + nome da empresa ativa como badge
- **Conteúdo direito:** nome do usuário + dropdown de troca de empresa + botão sair
- **Empresa ativa:** badge pequeno `text-xs bg-surface-2 border border-border px-2 py-0.5 rounded`
- **Troca de empresa:** click no badge abre Overlay do PrimeReact com lista de empresas disponíveis

### Área de conteúdo

- **Background:** `#0F1117`
- **Padding:** `p-6` (24px) para telas de lista, `p-6` para formulários
- **Max-width de formulário:** `max-w-2xl` (640px) — impede formulários se estendendo demais em monitores widescreen

### Breakpoints

| Breakpoint | Comportamento |
|---|---|
| Desktop (>= 1280px) | Layout padrão — sidebar + conteúdo |
| Tablet (768-1279px) | Sidebar colapsada por padrão (mini-mode) |
| Mobile (< 768px) | Sidebar oculta; hamburger abre overlay. DataTable mostra apenas colunas essenciais |

**Nota:** O ERP é **primariamente desktop**. Mobile deve ser funcional (navegação + visualização de listas), mas formulários complexos e DataTables com muitas colunas não precisam ser otimizados para mobile em v0.1.

---

## 5. Componentes-chave — Decisões de Padrão

### 5.1 DataTable (lista de Pessoas / Produtos)

**Preset:** PrimeReact DataTable com tema Lara Dark.

**Decisões:**

| Aspecto | Decisão | Justificativa |
|---|---|---|
| Filtro | Campo de busca global no header da página (debounce 400ms → `?search=`) | Simples, rápido, sem painel lateral desnecessário |
| Colunas | Ordenação habilitada via `sortable` por padrão em todas as colunas relevantes | Operador precisa ordenar por nome, status, data |
| Paginação | Server-side, `rows=20`, paginador simples (prev/next + número de página) | Backend já usa PageNumberPagination com page_size=20 |
| Row actions | Ícones inline na última coluna: `pi-pencil` (editar) + `pi-trash` (excluir) — sem menu contextual | Menu contextual adiciona clique extra sem benefício real para listas simples |
| Loading | Skeleton (`loadingMode="icon"` do DataTable) — não spinner global | Spinner global bloqueia toda a página; skeleton mostra estrutura |
| Empty state | Mensagem customizada com ícone e CTA "Criar primeiro registro" | Default do PrimeReact é texto seco sem direcionar ação |
| Row height | Compacto — `rowClassName` adiciona `py-2` (não o padding default cheio) | Densidade de informação — operador quer ver 20 linhas sem scroll |
| Hover | `bg-surface-2` no hover da linha | Feedback visual sem ser excessivo |
| Seleção | Não implementar seleção múltipla em v0.1 | Complexidade desnecessária para módulo piloto |

**Colunas padrão — PessoaList:**

| Coluna | Campo | Largura | Observação |
|---|---|---|---|
| Nome | `nome` | flex | Principal, clicável para editar |
| Documento | `documento` | 160px | Fonte mono, máscara automática CPF/CNPJ |
| Tipo | `tipo_cliente` | 120px | Badge colorido |
| Ativo | `ativo` | 80px | Badge verde/cinza (sim/não) |
| Ações | — | 80px | Ícones inline |

### 5.2 Formulário de Pessoa

**Layout:** Grid 2 colunas no desktop, 1 coluna no mobile.

```
[ nome*                          ] (span 2)
[ documento (CPF/CNPJ)          ] [ tipo_cliente (dropdown)    ]
[ categoria_cliente (dropdown)  ] [ fone                       ]
[ email                         ] [ ativo (toggle)             ]
[ obs (textarea)                ] (span 2)
```

**Validação:** Inline, abaixo do campo com `<small className="p-error">`. Não usar toast para erros de campo — o usuário precisa saber qual campo está errado.

**Auto-preenchimento CNPJ:**
- Trigger: quando `documento` tem 14 dígitos e tipo detectado é CNPJ (dígito 1-14)
- Indicador visual: spinner no campo + label "Buscando dados da empresa..."
- Preenchimento: nome, email, fone dos dados da Receita Federal
- Erro da API: toast de aviso (não bloqueia) — usuário preenche manualmente

**Label obrigatório:** asterisco vermelho `*` no label, não no placeholder.

**Botões de ação:** fixados no rodapé do formulário — `Salvar` (primário) + `Cancelar` (outlined/ghost). Não flutuante, não no topo.

### 5.3 Formulário de Produto

**Layout:** Mesmo padrão de 2 colunas do Formulário de Pessoa para consistência.

```
[ nome*                          ] (span 2)
[ unidade_medida* (dropdown)    ] [ tipo_produto (dropdown)    ]
[ familia_produto (dropdown)    ] [ fabricante                 ]
[ cod_barras (mono)             ] [ ativo (toggle)             ]
[ preco_venda (currency)        ] [ preco_custo (currency)     ]
[ obs (textarea)                ] (span 2)
```

**Campos monetários:** InputNumber do PrimeReact com `mode="currency" currency="BRL" locale="pt-BR"`.

**Código de barras:** InputText com `className="font-mono"` — usa IBM Plex Mono para manter legibilidade do EAN.

### 5.4 Seletor de Empresa Ativa

**Localização:** Topbar, lado direito, antes do nome do usuário.

**Comportamento:**
- Badge pequeno mostrando nome da empresa atual: `"[Nome da Empresa]"`
- Click abre `OverlayPanel` do PrimeReact com lista de empresas acessíveis
- Cada empresa na lista: nome + indicador da atual (check icon)
- Ao selecionar: chama `auth.trocarEmpresa(id)` → recarrega tokens → `window.location.reload()`

**Implementação:** `EmpresaSelector` como componente autônomo em `shared/components/EmpresaSelector.tsx`.

### 5.5 Estados Globais

**Toast notifications:**

```typescript
// Posição: top-right
// Duração: 4000ms (sucesso), 6000ms (erro) — erros precisam de mais tempo para leitura
// Sucesso: ícone pi-check-circle, severity="success"
// Erro: ícone pi-times-circle, severity="error"
// Warning: severity="warn", 5000ms
```

**Confirmação de delete:**
- Modal `ConfirmDialog` do PrimeReact — não inline, não toast com undo
- Mensagem: "Excluir {nome}? Esta ação não pode ser desfeita."
- Botão de confirmação: vermelho (`p-button-danger`)
- Justificativa: undo em ERP é complicado pois registros podem ter relacionamentos; confirmação explícita é mais segura

**Páginas de erro:**
- `403` — "Sem permissão" + botão "Voltar ao início"
- `404` — "Página não encontrada" + botão "Voltar ao início"
- `500` — "Erro interno" + botão "Recarregar" + texto de suporte
- Todas com layout centralizado, ícone PrimeIcons grande, sem design elaborado

---

## 6. PrimeReact Theme

**Preset:** `lara-dark-blue`

**Justificativa:** Lara é o preset mais maduro e profissional do PrimeReact. A variante dark-blue combina com nossa paleta de azul-índigo primário. Evitamos Aura (muito arredondado/moderno para ERP denso) e Material (polui o bundle com muita customização de Material Design).

**Import no main.tsx:**
```typescript
import 'primereact/resources/themes/lara-dark-blue/theme.css';
import 'primereact/resources/primereact.min.css';
import 'primeicons/primeicons.css';
```

**Customizações via CSS variables** — sobrepor em `index.css` após o import do tema:

```css
:root {
  /* Fonte */
  --font-family: 'IBM Plex Sans', sans-serif;
  
  /* Cores primárias — sobrepõem o lara-dark-blue */
  --primary-color: #4F6AF5;
  --primary-color-text: #ffffff;
  
  /* Superfícies */
  --surface-a: #1A1D26;   /* cards, panels */
  --surface-b: #0F1117;   /* body background */
  --surface-c: #22263A;   /* hover state */
  --surface-d: #2E3347;   /* border */
  --surface-e: #1A1D26;   /* overlay */
  --surface-f: #22263A;   /* tooltip */
  
  /* Texto */
  --text-color: #E8EAF0;
  --text-color-secondary: #8B90A8;
  
  /* Bordas */
  --surface-border: #2E3347;
  
  /* Border radius — menos arredondado para aparência mais profissional */
  --border-radius: 4px;
  --content-padding: 0.75rem;  /* mais compacto que o default 1rem */
}
```

**Passthrough (pt)** — usado pontualmente para customizações de componente específico. Exemplo DataTable:

```typescript
// Linhas compactas
pt={{
  bodyRow: { className: 'hover:bg-surface-2 transition-colors duration-100' },
  headerCell: { className: 'text-xs font-medium text-text-secondary uppercase tracking-wide bg-surface-1' },
}}
```

---

## 7. Estrutura de Pastas do Frontend

A estrutura proposta inicialmente é boa. Refinamentos para acomodar crescimento modular:

```
src/
  app/
    providers.tsx       ← QueryClient + PrimeReact + Toast ref
    router.tsx          ← Roteamento principal
  
  pages/                ← Páginas por módulo (criado no Step 5)
    pessoas/
      PessoaList.tsx    ← Listagem (DataTable + busca + paginação)
      PessoaForm.tsx    ← Formulário criação/edição
      index.ts          ← Re-exports
    produtos/
      ProdutoList.tsx
      ProdutoForm.tsx
      index.ts
    auth/
      LoginPage.tsx     ← Mover de shared/components para cá
  
  shared/
    components/
      Layout.tsx        ← Sidebar + Topbar + área de conteúdo
      EmpresaSelector.tsx
      PageHeader.tsx    ← Título + breadcrumb + slot de ação (botão "Novo")
      StatusBadge.tsx   ← Badge reutilizável (ativo/inativo, tipos)
      ConfirmDeleteDialog.tsx
      ErrorPage.tsx     ← 403/404/500
    hooks/
      useToast.ts       ← Acesso ao Toast global via ref
  
  services/             ← Chamadas de API (criado no Step 5)
    pessoas.ts
    produtos.ts
    empresas.ts
  
  hooks/                ← React Query hooks de domínio (criado no Step 5)
    usePessoas.ts
    useProdutos.ts
  
  types/                ← Tipos TypeScript de domínio (criado no Step 5)
    pessoa.ts
    produto.ts
  
  lib/                  ← Infraestrutura (já existe)
    api.ts
    auth.ts
    logger.ts
    types.ts
```

**Regra de nomenclatura:**
- Componentes: PascalCase (ex: `PessoaList.tsx`)
- Hooks: camelCase com prefixo `use` (ex: `usePessoas.ts`)
- Services: camelCase, sem prefixo (ex: `pessoas.ts`)
- Types: camelCase, singular (ex: `pessoa.ts`)

**Regra de importação:**
- Sempre usar alias `@/` (configurado no `vite.config.ts` via `resolve.alias`)
- NUNCA importação relativa que sobe mais de 1 nível (`../../` é proibido)

---

## 8. Animações e Micro-interações

**Princípio:** animações apenas em momentos de alto impacto. ERP não é landing page.

| Elemento | Animação | Duração |
|---|---|---|
| Sidebar collapse/expand | `transition-all duration-200 ease-in-out` na largura | 200ms |
| Row hover na DataTable | `transition-colors duration-100` no background | 100ms |
| Toast entrada | padrão do PrimeReact (slide from right) | 200ms |
| Modal abertura | padrão do PrimeReact (fade + scale) | 150ms |
| Botão loading | spinner do PrimeReact (nativo) | — |
| Skeleton loading | pulsar do PrimeReact (nativo) | — |

**O que NÃO animar:**
- Entradas de página (sem page-transition, sem fade-in de conteúdo)
- Células de DataTable
- Form fields
- Qualquer coisa que ocorre mais de uma vez por segundo durante uso normal

---

## Verificação de Coerência

| Check | Status |
|---|---|
| Fonte: sem Inter/Roboto/system-ui como primária | IBM Plex Sans |
| Paleta: sem gradientes genéricos | Tonais sólidos em tema escuro |
| PrimeReact: sem componentes duplicados | Usando DataTable, InputText, Button, Dropdown, etc. nativos |
| Densidade: operador consegue ver 20 linhas sem scroll | Rows compactas (`py-2`) |
| Mobile: pelo menos navegável | Sidebar oculta em mobile, DataTable com colunas reduzidas |
| Acessibilidade: labels explícitos, foco visível | Labels `htmlFor`, foco com `outline-primary` |

---

## Arquitetura de Sidebar — Decisão (2026-05-07)

**Decisão aprovada por Eduardo em sessão de 2026-05-07.**

### Princípio: ERP totalmente modular

Cada módulo (`erp.pessoas`, `erp.produtos`, `erp.estoque`, `erp.financeiro`, etc.) é **independente e autocontido**. Não existe agrupamento genérico tipo "Cadastros Gerais". A plataforma permite montar ERPs para qualquer tipo de negócio combinando blocos de módulos.

### Sidebar dinâmica em runtime

A sidebar é montada em tempo de execução com base nos módulos contratados pela Conta:

1. **Backend** expõe `GET /api/v1/modules/` → retorna array de codes ativos ex: `["erp.pessoas", "erp.produtos"]`
2. **Frontend** mantém um **manifesto estático** por módulo: define quais seções (Cadastros, Relatórios, Configurações) e links cada módulo expõe
3. A sidebar renderiza **apenas os módulos ativos**, em formato accordion colapsável

### Estrutura visual por módulo

```
▼ PESSOAS                    ← módulo ativo, expandido
    Cadastros
      → Pessoas
    Relatórios
      → Pessoas por tipo
    Configurações
      → Tipos de Cliente

▼ PRODUTOS                   ← módulo ativo, colapsado
    Cadastros → Produtos
    ...

(módulos não contratados não aparecem)
```

### Separação de responsabilidades

| Camada | Responsável | Conteúdo |
|---|---|---|
| Quais módulos estão ativos | Backend (`GET /api/v1/modules/`) | `["erp.pessoas", ...]` |
| O que cada módulo mostra | Frontend (manifesto estático) | Seções, links, ícones, placeholders |

### Pendências de implementação

- [x] `GET /api/v1/erp/modules/` no backend (retorna `EmpresaModulo` ativos da Empresa autenticada) — Step 7/8 ✅ (D-R05: `ContaModulo` → `EmpresaModulo`)
- [ ] Hook `useModules()` no frontend consumindo esse endpoint — Step 8
- [ ] `Layout.tsx` renderizando sidebar a partir da lista de módulos ativos — Step 8
- [ ] Manifesto completo de cada módulo no frontend (seções, links, ícones) — Step 8

**Nota:** Rotas padronizadas conforme D20 — usa `/api/v1/erp/modules/` (não `/api/v1/modules/`).

---

## 9. Backoffice — Diretrizes de UI/UX (D21 + D22 — Aprovado 2026-05-07)

### 9.1. Princípio

Os dois backoffices (account + platform) seguem o **mesmo design system** do ERP (paleta, tipografia, componentes PrimeReact), mas têm um `BackofficeLayout` próprio — sem sidebar modular de módulos ERP.

### 9.2. BackofficeLayout

```
┌───────────────────────────────────────────────────────────┐
│ TOPBAR (h-12, bg-surface-1, border-b)                     │
│  [GO Control — Conta / Platform]      [user] [sair]       │
├────────────────┬──────────────────────────────────────────┤
│ SIDEBAR FIXA   │ CONTEÚDO PRINCIPAL                        │
│ w-56 (224px)   │ bg-surface-0, p-6                        │
│ Não colapsível │                                           │
│ (menus fixos)  │                                           │
└────────────────┴──────────────────────────────────────────┘
```

**Diferenças do ERP Layout:**
- Sidebar **não** é dinâmica — itens são hardcoded por superfície (account / platform)
- Sem mini-mode (backoffice é usado esporadicamente, não 8h/dia)
- Topbar mostra a superfície ativa: "Gestão de Conta" ou "Administração da Plataforma"

### 9.3. Sidebar fixa — backoffice.account

```
▸ Dashboard
▸ Módulos
▸ Empresas
▸ Usuários
```

### 9.4. Sidebar fixa — backoffice.platform

```
▸ Dashboard
▸ Contas
▸ Catálogo de Módulos
▸ Manutenção
▸ Usuários Staff
```

### 9.5. Componentes compartilhados

Os componentes `PageHeader`, `StatusBadge`, `ConfirmDeleteDialog`, `ErrorPage` do ERP são reutilizados sem modificação nos backoffices.
