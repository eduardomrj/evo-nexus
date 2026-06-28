---
name: int-asaas-comissoes
description: "Gera o registro mensal de comissões a partir da API Asaas — calcula comissões dos revendedores, salva JSON e PDFs no workspace. Use quando o usuário pedir 'gerar comissões', 'calcular comissão do mês', 'comissão Asaas', 'fechar comissões de [mês]'."
---

# Comissões Asaas — Geração Mensal

Executa o script `asaas-commission` que busca cobranças recebidas na API Asaas, calcula comissões por regional (Regional de Boa Viagem e Regional Jaguaribe), grava o registro JSON mensal e os PDFs de comprovante no workspace EvoNexus.

## Quando Usar

- "gerar comissões de maio"
- "calcular comissão do mês"
- "fechar comissões de [mês/ano]"
- "gerar PDF de comissão dos revendedores"
- "rodar o script de comissões Asaas"

## Quando NÃO Usar

- Para consultar comissões já geradas → leia o JSON em `workspace/projects/asaas-commission/comissoes/YYYY-MM.json` diretamente
- Para alterar taxas de comissão → edite `config.py` em `/home/evonexus/evo-projects/asaas-commission/`
- Para outros relatórios financeiros → use `@flux-finance`

## Inputs

- **Mês** (1–12) e **ano** (ex.: 2026) — perguntar ao usuário se não informado no contexto
- Se JSON do mês já existir: confirmar com o usuário se quer sobrescrever antes de executar

## Workflow

### Step 1 — Obter mês e ano

Se o usuário já informou o mês/ano na mensagem, extraia diretamente.  
Caso contrário, pergunte:

> "Qual mês e ano de competência? (ex.: maio de 2026)"

Converta para `mes` (número com zero: `"05"`) e `ano` (string: `"2026"`).

### Step 2 — Verificar se já existe registro

Verifique se o JSON já existe:

```python
import os
json_path = f"/home/evonexus/evo-nexus/workspace/projects/asaas-commission/comissoes/{ano}-{mes}.json"
existe = os.path.exists(json_path)
```

Se existir, informe o usuário e pergunte se quer sobrescrever antes de continuar.

### Step 3 — Executar o script

**Sem registro existente:**
```bash
cd /home/evonexus/evo-projects/asaas-commission && \
printf "{mes}\n{ano}\n" | .venv/bin/python3 gerar_comissao.py 2>&1
```

**Com registro existente (usuário confirmou sobrescrita):**
```bash
cd /home/evonexus/evo-projects/asaas-commission && \
printf "{mes}\n{ano}\ns\n" | .venv/bin/python3 gerar_comissao.py 2>&1
```

Substitua `{mes}` e `{ano}` pelos valores reais (ex.: `5` e `2026`).

Aguarde a conclusão. O script busca a API Asaas — pode levar 20–60 segundos dependendo do volume.

### Step 4 — Ler e exibir o resultado

Leia o JSON gerado:

```python
import json
with open(json_path) as f:
    dados = json.load(f)
```

Exiba o resultado formatado em pt-BR:

```
## Comissões — [Mês por Extenso] de [Ano]
Gerado em: [gerado_em]

### Por Regional

| Regional             | Cobranças | Total Bruto  | Taxas    | Líquido     |
|----------------------|-----------|--------------|----------|-------------|
| Regional de Boa Viagem |  16     | R$ 4.737,38  | R$ 48,00 | R$ 2.320,69 |
| Regional Jaguaribe   |  11       | R$ 2.423,52  | R$ 33,00 | R$ 1.178,76 |

### Total Geral
- Cobranças: 27
- Total recebido: R$ 7.160,90
- Líquido a pagar: R$ 3.499,45

### Arquivos Gerados
- JSON: workspace/projects/asaas-commission/comissoes/2026-05.json
- PDFs: workspace/projects/asaas-commission/comissoes/2026/05/
  - comissao_Regional de Boa Viagem_[timestamp].pdf
  - comissao_Regional Jaguaribe_[timestamp].pdf
```

Use os valores reais do JSON. Formate valores monetários com `R$`, separador de milhar `.` e decimal `,`.

## Output

- **JSON** gravado em `workspace/projects/asaas-commission/comissoes/YYYY-MM.json`
- **PDFs** gravados em `workspace/projects/asaas-commission/comissoes/YYYY/MM/`
- Resumo formatado exibido ao usuário na conversa

## Anti-patterns

- NÃO execute o script sem confirmar mês e ano primeiro
- NÃO sobrescreva um registro existente sem confirmação explícita do usuário
- NÃO tente editar taxas ou grupos ativos — isso é configuração em `config.py`
- NÃO use o Python do sistema — sempre use `.venv/bin/python3` dentro do projeto

## Pairs With

- `int-asaas` — para consultas gerais à API Asaas (pagamentos, clientes, saldo)
- `@flux-finance` — para análise financeira dos registros gerados
- `fin-monthly-close` — para fechamento mensal que pode incluir comissões
