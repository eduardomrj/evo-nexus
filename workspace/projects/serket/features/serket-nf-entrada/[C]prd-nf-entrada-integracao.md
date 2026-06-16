# PRD — Integração NF Entrada no serket-abastecimento

**Feature:** serket-nf-entrada-integracao
**Status:** APROVADO — pronto para implementação
**Data:** 2026-06-09
**Owner:** Eduardo

---

## Problema

O módulo de digitação de notas de entrada (`serket_nf_entrada`) existe como pacote
isolado em `ADWs/routines/custom/serket_nf_entrada/` e tinha seu próprio serviço
Flask na porta 8084 (atualmente inativo). Isso gera:

- Dois projetos para o mesmo domínio (abastecimento CAF)
- Banco de dados separado (`serket_nf_entrada.db`) fora do DB consolidado
- Sem interface web para seleção/upload de PDFs — o usuário precisava rodar
  `run_entrada.py` manualmente pela linha de comando
- Contexto fragmentado: o usuário precisa alternar entre dois sistemas

---

## Solução

Integrar o módulo `serket_nf_entrada` dentro do `serket-abastecimento` (porta 8083),
consolidando tudo em um único Flask app com:

1. **Código movido** para `src/nf_entrada/` (submódulo Python do projeto)
2. **Banco unificado** em `serket_extract_abastecimento.db` (tabelas NF adicionadas ao DB existente)
3. **UI de NF Entrada** nova seção no sidebar com fluxo:
   - Upload de PDF da NMF via browser
   - Preview dos dados extraídos (cabeçalho + itens + lotes) para revisão
   - Botão "Executar no HORUS" que aciona a automação Playwright
   - Acompanhamento do log de execução em tempo real (polling)

---

## Scope

### IN SCOPE

- Mover `ADWs/routines/custom/serket_nf_entrada/` → `src/nf_entrada/`
- Atualizar imports (novo package path)
- Consolidar `config.py`: usar `SERKET_EXTRACT_ABASTECIMENTO_DATA_DIR` como data dir
- Criar tabelas NF no `serket_extract_abastecimento.db` (migração automática no startup)
- Upload de PDF via browser (multipart/form-data, armazenado em `uploads/`)
- Parser NMF: extração do PDF e persistência das tabelas `notas_entrada` + `itens_nota` + `lotes_item`
- Tela de preview: cabeçalho da NMF + tabela de itens expandível (lotes inline)
- Execução Playwright: subprocess assíncrono (mesmo padrão do extractor Horus existente)
- Log de execução: polling a cada 3s via `GET /api/nf-entrada/runs/{run_id}`
- Sidebar: novo item "NF Entrada" com ícone distinto

### OUT OF SCOPE

- Reescrever `horus_automation.py` (código maduro, já passou por diagnósticos extensos)
- Interface de edição de itens pós-extração
- Multi-upload (um PDF por vez na v1)
- Notificação por Telegram/Discord ao completar

---

## Acceptance Criteria

**AC-01 — Upload e extração**
```
Dado um PDF válido de NMF
Quando o usuário faz upload via browser
Então o sistema extrai cabeçalho, itens e lotes
  E salva em notas_entrada / itens_nota / lotes_item no DB consolidado
  E exibe preview na tela em < 5s
```

**AC-02 — Preview completo**
```
Dado uma NMF extraída
Quando o usuário abre o preview
Então vê: número da NMF, destinatário, data emissão, total de itens
  E cada item exibe: seq, medicamento, embalagem, qtd total, valor unitário
  E cada item pode ser expandido para ver seus lotes (lote, validade, qtd, fabricante)
```

**AC-03 — Execução assíncrona**
```
Dado uma NMF no estado "importada"
Quando o usuário clica "Executar no HORUS"
Então o Playwright inicia em background (subprocess)
  E a tela exibe log de execução com polling a cada 3s
  E ao final exibe: entradas criadas, itens ok, itens com erro, nº de entradas HORUS
```

**AC-04 — Histórico**
```
Dado execuções anteriores
Quando o usuário acessa a tela NF Entrada
Então vê lista de NMFs importadas com status (importada/executando/concluida/erro)
  E pode reabrir preview ou ver log de qualquer execução
```

**AC-05 — Banco consolidado**
```
Dado o startup do serket-abastecimento
Quando app.py inicializa
Então tabelas NF são criadas/migradas em serket_extract_abastecimento.db
  E nenhum arquivo serket_nf_entrada.db separado é criado
```

---

## Rotas previstas

| Método | Path | Descrição |
|--------|------|-----------|
| GET | `/serket-extract/nf-entrada` | Tela principal (lista de NMFs) |
| GET | `/serket-extract/nf-entrada/upload` | Tela de upload |
| POST | `/serket-extract/api/nf-entrada/upload` | Recebe PDF, extrai, retorna `nota_id` |
| GET | `/serket-extract/nf-entrada/{nota_id}` | Preview da NMF |
| POST | `/serket-extract/api/nf-entrada/{nota_id}/run` | Inicia Playwright (retorna `run_id`) |
| GET | `/serket-extract/api/nf-entrada/runs/{run_id}` | Status + log do run |
| GET | `/serket-extract/api/nf-entrada/notas` | Lista de NMFs |

---

## Dependências técnicas

- `pdfplumber` — já instalado (usado pelo copaf_extractor)
- `playwright` + `chromium` — já instalado (usado pelo extractor Horus)
- `rapidfuzz` — já instalado (usado pelo routes.py)
- `serket_nf_entrada` → movido para `nf_entrada` (código existente, sem reescrita)
