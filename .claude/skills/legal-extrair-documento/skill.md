# Skill: legal-extrair-documento

Extrai dados de identificação (CNH ou RG/identidade) a partir de uma imagem ou PDF,
e atualiza a base de representantes legais em `ADWs/scripts/legal/representantes.json`.

## Quando usar

- "extrai os dados dessa CNH"
- "atualiza o representante com esse documento de identidade"
- "cadastra o responsável legal dessa empresa com o RG enviado"
- "lê esse documento e salva o representante para usar no contrato"

---

## Dados extraídos

| Campo | Fonte no documento |
|---|---|
| `nome` | Nome completo |
| `cpf` | CPF (formatar como `000.000.000-00`) |
| `doc_tipo` | `"CNH"` ou `"RG"` |
| `doc_numero` | Número do documento (CNH: registro; RG: número) |
| `doc_validade` | Data de validade (formato `YYYY-MM-DD`; CNH pode não ter no RG) |
| `data_nascimento` | Data de nascimento (formato `YYYY-MM-DD`) |
| `filiacao_mae` | Nome da mãe (se visível) |
| `filiacao_pai` | Nome do pai (se visível, opcional) |
| `cargo` | **Não está no documento** — perguntar ao usuário |

---

## Fluxo de execução

### 1. Receber o arquivo

O usuário envia a imagem (JPG, PNG) ou PDF do documento.

- Se for **imagem**: usar visão diretamente.
- Se for **PDF**: converter a primeira página para imagem antes de analisar:
  ```bash
  python3 -c "
  import fitz, sys
  doc = fitz.open(sys.argv[1])
  page = doc[0]
  pix = page.get_pixmap(dpi=200)
  pix.save(sys.argv[2])
  " /caminho/arquivo.pdf /tmp/doc_identidade.png
  ```
  Se `fitz` não estiver disponível: `pip install pymupdf --break-system-packages`

### 2. Extrair dados com visão

Analisar a imagem com cuidado. Campos com formatação especial:
- **CPF**: sempre formatar `000.000.000-00` — validar os dígitos verificadores.
- **Datas**: converter para `YYYY-MM-DD`.
- **CNH**: número de registro ≠ número do CPF — usar campo "Registro" ou "Nº Registro".
- **RG**: o número pode ter letras (ex: `12.345.678-X`).

Se algum campo não estiver legível ou ausente no documento, registrar como `null`.

### 3. Solicitar informações complementares

Perguntar ao usuário:

1. **CNPJ da empresa** representada por este signatário (aceitar com ou sem formatação)
2. **Cargo** do representante legal (ex: Sócio-Administrador, Diretor, Procurador)

Opcionalmente, perguntar:
3. **E-mail** — se não houver na base ainda
4. **Telefone** — se não houver na base ainda

### 4. Exibir resumo para confirmação

```
── Representante Legal ──────────────────────────────────
  Nome          : João da Silva
  CPF           : 123.456.789-00
  Documento     : CNH — Registro 12345678901
  Validade      : 2029-03-15
  Nascimento    : 1982-07-04
  Filiação mãe  : Maria da Silva
  Cargo         : Sócio-Administrador
  Empresa (CNPJ): 04.056.245/0001-91
──────────────────────────────────────────────────────────
Confirma salvar? [s/N]
```

Aguardar confirmação antes de salvar.

### 5. Salvar em `representantes.json`

Arquivo: `ADWs/scripts/legal/representantes.json`

#### Estrutura do arquivo

```json
{
  "representantes": [
    {
      "cnpj": "04056245000191",
      "nome": "João da Silva",
      "cpf": "123.456.789-00",
      "cargo": "Sócio-Administrador",
      "email": "joao@empresa.com.br",
      "telefone": "(88) 99999-0000",
      "doc_tipo": "CNH",
      "doc_numero": "12345678901",
      "doc_validade": "2029-03-15",
      "data_nascimento": "1982-07-04",
      "filiacao_mae": "Maria da Silva",
      "filiacao_pai": null,
      "atualizado_em": "2026-06-19"
    }
  ]
}
```

#### Lógica de upsert

1. Ler o arquivo (se existir).
2. Procurar entrada com mesmo `cnpj`.
   - **Encontrou**: atualizar todos os campos — não duplicar.
   - **Não encontrou**: adicionar nova entrada ao array.
3. Gravar o arquivo com `json.dumps(..., ensure_ascii=False, indent=2)`.

```python
import json
from pathlib import Path
from datetime import date

REPRESENTANTES = Path("ADWs/scripts/legal/representantes.json")

def salvar_representante(dados: dict):
    registro = {"representantes": []}
    if REPRESENTANTES.exists():
        registro = json.loads(REPRESENTANTES.read_text())

    cnpj = dados["cnpj"]
    lista = registro["representantes"]
    idx = next((i for i, r in enumerate(lista) if r["cnpj"] == cnpj), None)

    dados["atualizado_em"] = str(date.today())

    if idx is not None:
        lista[idx] = dados
    else:
        lista.append(dados)

    REPRESENTANTES.write_text(json.dumps(registro, ensure_ascii=False, indent=2))
```

### 6. Reportar resultado

Informar ao usuário:
- ✓ Representante salvo/atualizado
- CNPJ e nome vinculados
- Oferecer próximos passos:
  - "Quer usar esses dados agora para gerar um contrato? Basta chamar `legal-gerar-contrato-licenca`, `legal-gerar-contrato-tef` ou `legal-gerar-contrato-licenca-asaas` — o representante será preenchido automaticamente."

---

## Integração com geração de contratos

Quando a skill `legal-gerar-contrato-licenca`, `legal-gerar-contrato-tef` ou
`legal-gerar-contrato-licenca-asaas` for chamada para um CNPJ que já tem
entrada em `representantes.json`, **o signatário deve ser pré-preenchido**
automaticamente a partir dessa base:

```python
def buscar_representante(cnpj_limpo: str) -> dict | None:
    """Retorna o representante vinculado ao CNPJ ou None se não cadastrado."""
    arquivo = Path("ADWs/scripts/legal/representantes.json")
    if not arquivo.exists():
        return None
    dados = json.loads(arquivo.read_text())
    return next(
        (r for r in dados["representantes"] if r["cnpj"] == cnpj_limpo),
        None
    )
```

Ao pré-preencher, mostrar ao usuário:
```
ℹ Representante encontrado na base:
  João da Silva — Sócio-Administrador (CPF: 123.456.789-00)
  Usando esses dados para o contrato. Deseja alterar?
```

Se o usuário confirmar, usar os dados. Se não confirmar, coletar manualmente.

---

## Erros comuns

| Erro | Causa | Ação |
|---|---|---|
| CPF ilegível | Foto com brilho/sombra | Pedir nova foto com melhor iluminação |
| PDF com múltiplas páginas | Fitz abre apenas página 0 | Sempre converter a primeira página |
| `pymupdf` não instalado | Falta dependência | `pip install pymupdf --break-system-packages` |
| CNPJ já tem representante | Upsert normal | Informar ao usuário que os dados foram **atualizados** |

---

## Arquivos envolvidos

| Arquivo | Função |
|---|---|
| `ADWs/scripts/legal/representantes.json` | Base de representantes legais (persistente) |
| `/tmp/doc_identidade.png` | Imagem temporária convertida de PDF (descartável) |
