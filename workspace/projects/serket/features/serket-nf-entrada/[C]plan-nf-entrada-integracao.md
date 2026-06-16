# Plano — Integração NF Entrada no serket-abastecimento

**Feature:** serket-nf-entrada-integracao
**Status:** APROVADO
**Data:** 2026-06-09
**Owner:** @bolt-executor
**PRD:** [C]prd-nf-entrada-integracao.md
**Arquitetura:** [C]architecture-serket-nf-entrada.md

---

## Visão geral

4 etapas sequenciais. Etapas 1–3 não envolvem UI (backend puro). Etapa 4 é a interface.

```
Etapa 1: Parar serviço + Mover código
Etapa 2: Consolidar config e banco
Etapa 3: Registrar Blueprint no Flask
Etapa 4: UI de upload, preview e execução
```

---

## Etapa 1 — Parar serviço + Mover código

**Owner:** @bolt-executor
**Pré-requisito:** nenhum

### T1.1 — Confirmar que serket-nf-entrada.service está inativo
```bash
systemctl is-active serket-nf-entrada.service
# Se ativo: sudo systemctl stop serket-nf-entrada.service
# Se enabled: sudo systemctl disable serket-nf-entrada.service
```
Serviço já está inactive (verificado em 09/06/2026).

### T1.2 — Copiar módulo para o projeto
```
ORIGEM:  ADWs/routines/custom/serket_nf_entrada/
DESTINO: /home/evonexus/evo-projects/serket-abastecimento/src/nf_entrada/
```

Arquivos a copiar:
- `__init__.py`
- `config.py`
- `db.py`
- `horus_automation.py`
- `parser.py`
- `transformer.py`
- `run_entrada.py`
- `FIELD_IDS.md` (referência)

**NÃO copiar:** `app.py` do nf_entrada (será substituído pelo blueprint), scripts `diag*.py`

### T1.3 — Criar diretório uploads
```
/home/evonexus/evo-projects/serket-abastecimento/uploads/
```
Onde os PDFs enviados via browser serão armazenados temporariamente.

**Critério de saída:** `ls src/nf_entrada/` lista todos os arquivos acima sem erro.

---

## Etapa 2 — Consolidar config e banco

**Owner:** @bolt-executor
**Pré-requisito:** T1.2 concluído

### T2.1 — Atualizar `src/nf_entrada/config.py`

Substituir:
```python
# ANTES
DATA_DIR = Path(os.environ.get("SERKET_NF_ENTRADA_DATA_DIR",
                               "/home/evonexus/evo-projects/serket-nf-entrada"))
DB_PATH  = DATA_DIR / "serket_nf_entrada.db"
FLASK_PORT   = int(os.environ.get("SERKET_NF_ENTRADA_PORT", 8084))
FLASK_PREFIX = "/serket-nf-entrada"
UPLOADS_DIR  = DATA_DIR / "uploads"   # <-- não existia

# DEPOIS
DATA_DIR     = Path(os.environ.get(
    "SERKET_EXTRACT_ABASTECIMENTO_DATA_DIR",
    "/home/evonexus/evo-projects/serket-abastecimento"
))
DB_PATH      = DATA_DIR / "serket_extract_abastecimento.db"
UPLOADS_DIR  = DATA_DIR / "uploads"
```

Remover `FLASK_PORT` e `FLASK_PREFIX` — não são mais usados.
Manter todos os outros valores (`MAX_ITENS_POR_ENTRADA`, `FUZZY_THRESHOLD`,
`FONTE_FINANCIAMENTO_VALUE`, `PROGRAMA_SAUDE_VALUE`, `LOCALIZACAO_FISICA_VALUE`).

### T2.2 — Atualizar `src/nf_entrada/db.py`

Mudar import de `config`:
```python
# ANTES
from serket_nf_entrada.config import DB_PATH

# DEPOIS
from nf_entrada.config import DB_PATH
```

### T2.3 — Atualizar `src/nf_entrada/horus_automation.py`

Mudar imports:
```python
# ANTES
from serket_nf_entrada.config import (...)
from serket_nf_entrada.db import get_conn

# DEPOIS
from nf_entrada.config import (...)
from nf_entrada.db import get_conn
```

### T2.4 — Atualizar `src/nf_entrada/parser.py`

```python
# ANTES
from serket_nf_entrada.transformer import parse_fator_embalagem, calcular_item

# DEPOIS
from nf_entrada.transformer import parse_fator_embalagem, calcular_item
```

### T2.5 — Adicionar criação das tabelas NF ao startup

Em `src/routes.py`, dentro da função `setup_extraction_runs_table()`, adicionar ao final:

```python
# Tabelas NF Entrada
conn_nf = sqlite3.connect(db_path)
conn_nf.executescript("""
    CREATE TABLE IF NOT EXISTS notas_entrada (
        id INTEGER PRIMARY KEY,
        nmf_numero TEXT NOT NULL,
        destinatario TEXT,
        municipio TEXT,
        programa TEXT,
        data_emissao TEXT,
        data_recebimento TEXT,
        requisitante TEXT,
        valor_total_nmf REAL,
        total_itens INTEGER,
        status TEXT DEFAULT 'importada',
        pdf_path TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS itens_nota (
        id INTEGER PRIMARY KEY,
        nota_id INTEGER REFERENCES notas_entrada(id) ON DELETE CASCADE,
        item_seq INTEGER NOT NULL,
        medicamento TEXT NOT NULL,
        codigo_nmf TEXT,
        embalagem_str TEXT,
        fator_embalagem INTEGER,
        unidade_horus TEXT,
        qtd_embalagens_total INTEGER,
        vlr_unit_embalagem REAL,
        vlr_unit_unidade REAL,
        vlr_total_item REAL,
        nome_horus_match TEXT,
        match_score INTEGER,
        revisao_manual INTEGER DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS lotes_item (
        id INTEGER PRIMARY KEY,
        item_id INTEGER REFERENCES itens_nota(id) ON DELETE CASCADE,
        lote TEXT NOT NULL,
        validade TEXT,
        qtd_embalagens INTEGER,
        qtd_unidades INTEGER,
        vlr_unit_embalagem REAL,
        vlr_unit_unidade REAL,
        vlr_total REAL,
        fabricante TEXT,
        lista TEXT,
        endereco TEXT
    );
    CREATE TABLE IF NOT EXISTS execucoes_horus (
        id INTEGER PRIMARY KEY,
        nota_id INTEGER REFERENCES notas_entrada(id),
        entrada_seq INTEGER,
        nr_entrada_horus TEXT,
        item_inicio INTEGER,
        item_fim INTEGER,
        started_at TEXT,
        finished_at TEXT,
        total_itens INTEGER,
        itens_ok INTEGER DEFAULT 0,
        itens_erro INTEGER DEFAULT 0,
        pct_sucesso REAL,
        status TEXT DEFAULT 'em_andamento'
    );
    CREATE TABLE IF NOT EXISTS log_digitacao (
        id INTEGER PRIMARY KEY,
        execucao_id INTEGER REFERENCES execucoes_horus(id),
        item_id INTEGER REFERENCES itens_nota(id),
        lote_id INTEGER REFERENCES lotes_item(id),
        etapa TEXT,
        status TEXT,
        mensagem TEXT,
        screenshot_path TEXT,
        ts TEXT DEFAULT (datetime('now'))
    );
""")
conn_nf.commit()
conn_nf.close()
```

**Critério de saída:** `sqlite3 serket_extract_abastecimento.db ".tables"` exibe as 5 tabelas NF.

---

## Etapa 3 — Blueprint Flask + run_entrada como subprocess

**Owner:** @bolt-executor
**Pré-requisito:** Etapa 2 concluída

### T3.1 — Criar `src/nf_routes.py`

Novo Blueprint com os seguintes endpoints:

```python
bp_nf = Blueprint("nf_entrada", __name__)
```

**Endpoints de API:**

| Método | Path | Descrição |
|--------|------|-----------|
| POST | `/upload` | Recebe PDF, chama `parser.parse_nmf()`, persiste no DB, retorna `{nota_id}` |
| GET | `/notas` | Lista `notas_entrada` com status (paginado, 50/pág) |
| GET | `/notas/{nota_id}` | Retorna nota + itens + lotes (para preview) |
| DELETE | `/notas/{nota_id}` | Deleta nota e cascata (itens, lotes, execuções) |
| POST | `/notas/{nota_id}/run` | Lança `run_entrada.py` como subprocess, retorna `{run_id: execucao_id}` |
| GET | `/runs/{run_id}` | Status + últimas 100 linhas do log da execução |
| GET | `/runs` | Lista execuções recentes (join com nota) |

**Regras do endpoint `/upload`:**
- Aceitar apenas `application/pdf` (validar content-type e extensão)
- Salvar em `UPLOADS_DIR/{uuid4().hex}.pdf`
- Chamar `parse_nmf(pdf_path)` — pode levar até 5s; OK síncrono
- Inserir `notas_entrada` + `itens_nota` + `lotes_item` no DB
- Retornar `{nota_id, nmf_numero, total_itens, redirect: "/serket-extract/nf-entrada/{nota_id}"}`

**Regras do endpoint `/notas/{nota_id}/run`:**
- Verificar `status != "executando"` (evitar duplo disparo)
- Setar `status = "executando"` na nota
- Lançar subprocess: `python3 run_entrada_cli.py --nota-id {nota_id} --db-path {DB_PATH}`
- Log do subprocess em `DATA_DIR/logs/nf-runs/{nota_id}-{ts}.log`
- Thread monitor que ao terminar: lê log, atualiza `status` (concluida/erro), atualiza nota
- Retornar `{run_id, status: "executando"}`

### T3.2 — Criar `src/nf_entrada/run_entrada_cli.py`

Wrapper CLI que `nf_routes.py` chama via subprocess:

```python
# Argumentos: --nota-id INT --db-path STR [--headless]
# Instancia HorusNFEntrada(db_path=...) e chama executar_nota(nota_id)
# Imprime progresso linha a linha (stdout)
# Exit code 0 = sucesso/parcial, 1 = erro fatal
```

Isso evita importar Playwright no processo Flask (conflito de event loop).

### T3.3 — Registrar Blueprint no `src/app.py`

```python
# Adicionar após imports existentes:
sys.path.insert(0, str(Path(__file__).parent))
from nf_routes import bp_nf, setup_nf_tables   # noqa

app.register_blueprint(bp_nf, url_prefix="/serket-extract/api/nf-entrada")

with app.app_context():
    setup_extraction_runs_table()   # existente
    setup_nf_tables()               # novo
```

**Critério de saída:** `curl localhost:8083/serket-extract/api/nf-entrada/notas` retorna `{"notas": [], "total": 0}`.

---

## Etapa 4 — UI: upload, preview e execução

**Owner:** @bolt-executor (lógica) / @canvas-designer (visual se necessário)
**Pré-requisito:** Etapa 3 concluída

Seguir o padrão visual já existente no `app.py` (dark theme `#0a0a0a`, sidebar colapsável,
mesmo CSS base). Não recriar o CSS — reaproveitar a variável `_CSS` e o template HTML do app.

### T4.1 — Adicionar item "NF Entrada" ao sidebar

Nos templates HTML do `app.py`, adicionar nav item:
```html
<a href="/serket-extract/nf-entrada" class="nav-item ...">
  📋 NF Entrada
</a>
```

### T4.2 — Tela `/serket-extract/nf-entrada` (lista)

Layout:
- Header: "Notas de Entrada HORUS" + botão "Nova NMF" (vai para /upload)
- Tabela: NMF N°, Destinatário, Emissão, Itens, Status (badge colorido), Ações (Preview / Ver log)
- Status badges: `importada`=cinza, `executando`=amarelo pulsante, `concluida`=verde, `erro`=vermelho
- Paginação simples (50/pág)

### T4.3 — Tela `/serket-extract/nf-entrada/upload`

Layout:
- Área de drag-and-drop para PDF (fallback: `<input type="file" accept=".pdf">`)
- Botão "Extrair NMF"
- Feedback de progresso (spinner enquanto processa)
- Em sucesso: redireciona automaticamente para o preview da nota
- Em erro: exibe mensagem inline (PDF inválido, campos não encontrados, etc.)

JavaScript: `fetch POST /api/nf-entrada/upload` com FormData.

### T4.4 — Tela `/serket-extract/nf-entrada/{nota_id}` (preview)

Layout em duas seções:

**Cabeçalho da NMF:**
```
NMF N°: 62268       Destinatário: 34 5° MICRORREGIONAL...    Município: CANINDÉ
Emissão: 27/04/2026  Requisitante: CAF I                     Total: R$ 12.345,67
Itens: 95           Status: importada
```

**Tabela de itens** (expandível):
```
# | Medicamento              | Embalagem          | Qtd | Vlr Unit   | Lotes | Status
1 | ACICLOVIR 200 MG         | CAIXA C/ 30 COMP   |  79 | R$ 0,0013  |   2   |  ok
  └ Lote: ABC123 | Val: 12/2026 | Qtd: 3000 | Fab: LABO...
```

**Botão de ação:**
- `status = importada` → botão verde "▶ Executar no HORUS"
- `status = executando` → botão desabilitado "⏳ Executando..." + painel de log ao vivo
- `status = concluida` → botão cinza "Concluída" + resumo de resultado + link "Ver log"
- `status = erro` → botão vermelho "Erro — tentar novamente" + detalhes

### T4.5 — Painel de log ao vivo (polling)

Quando `status = executando`:
- Polling `GET /api/nf-entrada/runs/{run_id}` a cada 3s
- Exibe log em `<pre>` com scroll automático no final
- Quando status muda para concluida/erro: para o polling e exibe resumo

**Critério de saída (Etapa 4):**
- Upload de PDF funciona end-to-end no browser
- Preview exibe corretamente os dados de uma NMF real
- Botão "Executar" dispara o Playwright e o log aparece na tela

---

## Ordem de execução

```
T1.1 → T1.2 → T1.3
            ↓
T2.1 → T2.2 → T2.3 → T2.4 → T2.5
                                ↓
                     T3.1 → T3.2 → T3.3
                                      ↓
                          T4.1 → T4.2 → T4.3 → T4.4 → T4.5
```

---

## Notas de implementação

- `horus_automation.py` recebe `db_path` e `data_dir` via construtor — não precisa de env vars globais.
  Passar `DB_PATH` e `DATA_DIR` da config consolidada.
- O campo `pdf_path` em `notas_entrada` guarda o path absoluto do PDF em `uploads/`
  para eventual re-processamento.
- Screenshots do Playwright continuam em `DATA_DIR/screenshots/` (mesmo diretório que o extractor Horus).
- O diag `ADWs/routines/custom/serket_nf_entrada/diag*.py` pode ser arquivado (não mover).
