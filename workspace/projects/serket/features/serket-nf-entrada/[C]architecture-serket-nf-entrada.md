# Architecture — SERKET NF Entrada HORUS

**Feature:** serket-nf-entrada
**Phase:** Solutioning → aprovado
**Owner:** Oracle (mapeamento manual + confirmação usuário)
**Data:** 2026-04-30
**Status:** APROVADO — pronto para implementação

---

## Decisão

Módulo standalone Flask (padrão Vigil) que:
1. Recebe PDF de NMF (Nota de Medicamento Fornecido) do SISMED/COASF
2. Extrai e estrutura os dados (cabeçalho + itens + lotes)
3. Calcula transformações de unidade (embalagem → unidade menor)
4. Automatiza o cadastro no HORUS via Playwright
5. Mantém log detalhado de cada etapa de digitação

---

## Estrutura do Projeto

- **Código:** `ADWs/routines/custom/serket-nf-entrada/` (gitignored do EvoNexus)
- **Dados:** `/home/evonexus/evo-projects/serket-nf-entrada/`
- **Porta:** 8084
- **URL local:** `http://localhost:8084/serket-nf-entrada/`
- **URL produção:** `http://nexus.myworkhome.com.br/serket-nf-entrada/`

Estrutura de dados:
```
/home/evonexus/evo-projects/serket-nf-entrada/
  serket_nf_entrada.db
  logs/
  reports/
  screenshots/
```

---

## Credenciais HORUS

Reutilizar do `.env` principal do EvoNexus:
```
HORUS_EMAIL=livia.camerino@hotmail.com
HORUS_PASSWORD=levi1206
HORUS_SCAWEB_URL=https://scaweb.saude.gov.br/scaweb/
SERKET_NF_ENTRADA_DATA_DIR=/home/evonexus/evo-projects/serket-nf-entrada
```

---

## Mapa de Navegação HORUS (verificado em 30/04/2026)

### Rota de acesso

```
SCAWEB (pós-login com HORUS_EMAIL + HORUS_PASSWORD)
  → link "Gestor Municipal - I"          [a:has-text("Gestor Municipal - I")]
    → HORUS carrega                     [wait: **/horus/**]
      → Menu "Entrada" hover
        → "Entrada Produto" click       [menuitem text]
          → Tela "Consultar Entrada"    [wait: text=Consultar Entrada]
            → Botão "Novo" click        [button: "Novo"]
              → Formulário de Entrada
```

O módulo de login (`login()`) do `serket-extract-abastecimento/src/extractor.py` é reutilizado integralmente.

---

## Formulário — Cabeçalho da Entrada

| Campo | Valor | Comportamento |
|---|---|---|
| Fonte financiamento | `value="161"` — MUNICIPAL + ESTADUAL + FEDERAL PORTARIA N° 1.555/13 | select — **obrigatório este valor** |
| Tipo movimentação | ENTRADA EVENTUAL | select |
| Tipo fornecimento | Entidade | radio button |
| Entidade | SECRETARIA DA SAÚDE DO ESTADO DO CEARA | campo busca |
| Documento | — | **Dropdown — NÃO preencher, deixar padrão** |
| Nº Documento | Número da NMF (ex: `62268`) | input text |
| Data Documento | Data de EMISSÃO da NMF (ex: `27/04/2026`) | input DD/MM/AAAA |
| Data Armazenamento | Data atual (dia da execução) | input DD/MM/AAAA |
| Valor Total | `0,01` | obrigatório antes de salvar — recalculado pelos lotes |
| Observação | opcional | textarea |

---

## Etapa 2 — Adicionar Produto (por item da NMF)

1. Clicar **[+]** ao lado de "Produtos"
2. **Busca de produto**: fuzzy matching `token_set_ratio > 80` entre nome do medicamento na NMF e nomes no HORUS (rapidfuzz) — **não existe código DE→PARA**
3. **Unidade**: preenchida automaticamente pelo HORUS (COMP., CAPS., SUSP., etc.)
4. **Vl. Unitário**: preencher imediatamente com `vlr_unit_embalagem / fator_embalagem`
5. **Quantidade**: deixar **0** (zerado)
6. Clicar **"Salvar"** → gera Nº Entrada (ex: `9589061`)

---

## Etapa 3 — Cadastrar Lote (por lote de cada produto)

Após Salvar, aparece botão **"Lote"** ([+] na coluna Ação) → clicar.

| Campo | Valor | Fonte na NMF |
|---|---|---|
| Fabricante | busca fuzzy pelo nome | campo `Fab.:` |
| Nº Lote | número do lote | campo `Lote:` |
| Fator Embalagem | N da embalagem | ex: `500` de "CAIXA C/ 500 COMP" |
| Data Validade | DD/MM/AAAA | campo `Val.:` |
| Status Bloqueio | `● Não` | padrão |
| **Programa Saúde** | `value="361"` — ASSISTÊNCIA FARMACÊUTICA | **obrigatório este valor** |
| Quantidade | `qtd_embalagens × fator_embalagem` | calculado |
| Localização Física | `CAF` | padrão |

Após salvar lote → clicar **"Voltar"** → volta ao formulário principal → próximo produto.

---

## Regra dos 30 Itens

- **Máximo 30 produtos por entrada no HORUS**
- Se a NMF tiver > 30 itens → criar nova entrada com **mesmo cabeçalho** (mesmo Nº Documento, mesma Data Documento, mesma Data Armazenamento, mesma Fonte financiamento)
- Continuar os produtos a partir do item 31

Exemplo — NMF 62268 (95 itens):
```
Entrada 1: itens 1–30
Entrada 2: itens 31–60
Entrada 3: itens 61–90
Entrada 4: itens 91–95
```

---

## Finalização

- **NÃO clicar em "Armazenar"** ao terminar — o usuário fará manualmente após conferência
- Registrar todos os Nº Entrada gerados no log e relatório final

---

## Cálculos de Transformação de Unidade

```python
import re
from rapidfuzz import fuzz

def parse_fator_embalagem(embalagem_str: str) -> int:
    """
    "CAIXA C/ 500 COMP"    → 500
    "CAIXA C/ 30 COMP"     → 30
    "CAIXA C/ 01 SPR ORAL" → 1
    "BISNAGA C/ 50 CR DERM"→ 50
    """
    m = re.search(r'C/\s*(\d+)', embalagem_str)
    return int(m.group(1)) if m else 1

def calc_vlr_unit_unidade(vlr_unit_embalagem: float, fator: int) -> float:
    return round(vlr_unit_embalagem / fator, 7)

def calc_qtd_unidades(qtd_embalagens: int, fator: int) -> int:
    return qtd_embalagens * fator

def buscar_produto_horus(nome_nmf: str, lista_horus: list[str]) -> tuple[str, int]:
    """Retorna (nome_horus, score). Usa token_set_ratio, threshold 80."""
    best, score = max(
        ((n, fuzz.token_set_ratio(nome_nmf, n)) for n in lista_horus),
        key=lambda x: x[1]
    )
    return (best, score) if score >= 80 else (None, score)
```

---

## Schema SQLite

```sql
CREATE TABLE notas_entrada (
    id INTEGER PRIMARY KEY,
    nmf_numero TEXT NOT NULL,
    destinatario TEXT,
    municipio TEXT,
    programa_nmf TEXT,
    data_emissao TEXT,          -- DD/MM/AAAA
    data_recebimento TEXT,      -- dia atual da execução
    requisitante TEXT,
    valor_total_nmf REAL,
    total_itens INTEGER,
    status TEXT DEFAULT 'importada',  -- importada | revisando | executando | concluida | erro
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE itens_nota (
    id INTEGER PRIMARY KEY,
    nota_id INTEGER REFERENCES notas_entrada(id),
    item_seq INTEGER NOT NULL,
    medicamento TEXT NOT NULL,
    codigo_nmf TEXT,
    embalagem_str TEXT,         -- "CAIXA C/ 500 COMP"
    fator_embalagem INTEGER,    -- 500
    unidade_horus TEXT,         -- "COMP." (preenchida pelo HORUS)
    qtd_embalagens_total INTEGER,
    vlr_unit_embalagem REAL,
    vlr_unit_unidade REAL,      -- vlr_unit_embalagem / fator_embalagem
    vlr_total_item REAL,
    nome_horus_match TEXT,      -- nome encontrado no HORUS via fuzzy
    match_score INTEGER,        -- score do fuzzy (0-100)
    revisao_manual INTEGER DEFAULT 0  -- 1 se score < 80 ou fator não parseable
);

CREATE TABLE lotes_item (
    id INTEGER PRIMARY KEY,
    item_id INTEGER REFERENCES itens_nota(id),
    lote TEXT NOT NULL,
    validade TEXT,              -- DD/MM/AAAA
    qtd_embalagens INTEGER,
    qtd_unidades INTEGER,       -- qtd_embalagens * fator_embalagem
    vlr_unit_embalagem REAL,
    vlr_unit_unidade REAL,
    vlr_total REAL,
    fabricante TEXT,
    lista TEXT,
    endereco TEXT
);

CREATE TABLE execucoes_horus (
    id INTEGER PRIMARY KEY,
    nota_id INTEGER REFERENCES notas_entrada(id),
    entrada_seq INTEGER,        -- 1, 2, 3... (para notas com >30 itens)
    nr_entrada_horus TEXT,      -- número gerado pelo HORUS (ex: 9589061)
    item_inicio INTEGER,        -- primeiro item desta entrada
    item_fim INTEGER,           -- último item desta entrada
    started_at TEXT,
    finished_at TEXT,
    total_itens INTEGER,
    itens_ok INTEGER DEFAULT 0,
    itens_erro INTEGER DEFAULT 0,
    pct_sucesso REAL,
    status TEXT DEFAULT 'em_andamento'
);

CREATE TABLE log_digitacao (
    id INTEGER PRIMARY KEY,
    execucao_id INTEGER REFERENCES execucoes_horus(id),
    item_id INTEGER REFERENCES itens_nota(id),
    lote_id INTEGER REFERENCES lotes_item(id),
    etapa TEXT,                 -- CABECALHO | PRODUTO | LOTE | SALVAR | VOLTAR
    status TEXT,                -- ok | erro | revisao
    mensagem TEXT,
    screenshot_path TEXT,
    ts TEXT DEFAULT (datetime('now'))
);
```

---

## Decisões Técnicas

| Decisão | Escolha | Motivo |
|---|---|---|
| Framework | Flask (padrão Vigil) | Sem npm/build; consistente com serket-extract |
| Unidade de cadastramento | Unidade menor (COMP, CAPS, SUSP) | Confirmado pelas telas do HORUS em 30/04/2026 |
| Campo "Fator Embalagem" | N extraído da string de embalagem da NMF | Campo nativo do HORUS na tela "Cadastro de Lotes" |
| Busca de produto | fuzzy `token_set_ratio` > 80 | Sem código DE→PARA; padrão do serket-extract |
| Credenciais | Reutilizar `.env` principal | HORUS_EMAIL + HORUS_PASSWORD já existem |
| Limite por entrada | 30 produtos | Limitação do HORUS — confirmada pelo usuário |
| Armazenar | **Manual pelo usuário** | Conferência obrigatória antes de armazenar |
| Campo Documento (cabeçalho) | Dropdown — não preencher | Confirmado: não é campo de texto |
| Campo Nº Documento | Número da NMF | ex: 62268 |
| Fonte financiamento | value="161" | MUNICIPAL + ESTADUAL + FEDERAL PORTARIA N° 1.555/13 |
| Programa Saúde (lote) | value="361" | ASSISTÊNCIA FARMACÊUTICA |

---

## Agentes Envolvidos

| Agente | Responsabilidade |
|---|---|
| `@bolt-executor` | F1-01 a F1-04, F3-01 a F3-05 (bootstrap, parser, HORUS) |
| `@canvas-designer` | F2-01 a F2-03 (interface web) |
| `@custom-sysops` | F4-01 (integração start-services.sh) |
| `@hawk-debugger` | debugging de automação Playwright |
