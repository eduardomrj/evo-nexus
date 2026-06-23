# Skill: legal-assinatura-asaas

Cria uma assinatura mensal (PIX) no Asaas a partir de um contrato TEF ou LIC
registrado em `contratos_registro.json`. O contrato deve existir, estar ativo e
ainda não possuir assinatura — caso contrário, aborta com aviso claro.

## Quando usar

- "cria assinatura no Asaas para o contrato TEF-2026-0010"
- "gera assinatura mensal do LIC-2026-0015"
- "ativa cobrança recorrente do contrato TEF-2026-0013"

---

## Pré-requisitos

O `.env` deve ter:
```
ASAAS_API_KEY=<token>
```

---

## Fluxo de execução

### 1. Receber o número do contrato

Se não informado na mensagem, perguntar:
> "Qual o número do contrato? (ex: TEF-2026-0010 ou LIC-2026-0011)"

Normalizar para maiúsculas antes de buscar.

### 2. Localizar e validar o contrato

Ler `ADWs/scripts/legal/contratos_registro.json`.

Buscar pelo campo `numero`. Se não encontrado:
> "Contrato [NÚMERO] não encontrado no registro. Verifique o número e tente novamente."
— **Interromper.**

Se `status != "ativo"`:
> "Contrato [NÚMERO] está com status '[STATUS]'. Só é possível criar assinatura para contratos ativos."
— **Interromper.**

Se o contrato já tiver `asaas_subscription_id` preenchido:
> "Contrato [NÚMERO] já possui assinatura ativa no Asaas: [SUBSCRIPTION_ID]. Nenhuma ação realizada."
— **Interromper.**

Extrair do contrato:
- `tipo` → `"tef"` ou `"licenca"`
- `cnpj`
- `empresa`
- `vencimento_dia`

### 3. Determinar o valor mensal

**Para contratos TEF:**
- Verificar `smartpos.mensalidade` ou `pinpad.mensalidade` (o que existir)
- Se ausente ou zero: perguntar
  > "O contrato TEF [NÚMERO] não tem valor de mensalidade registrado. Qual o valor? (R$)"

**Para contratos LIC:**
- Usar `total_mensal`
- Se ausente ou zero: perguntar
  > "O contrato LIC [NÚMERO] não tem valor mensal registrado. Qual o valor? (R$)"

### 4. Resolver o cliente no Asaas

**Para contratos LIC:**
- Usar `asaas_customer_id` já gravado no contrato
- Se ausente: tratar como TEF (busca por CNPJ)

**Para contratos TEF:**
- Se o contrato já tiver `asaas_customer_id`: usar diretamente
- Se não tiver: buscar por CNPJ

```bash
curl -s "https://api.asaas.com/v3/customers?cpfCnpj=<CNPJ_LIMPO>" \
  -H "access_token: $ASAAS_API_KEY"
```

  - Se encontrado (`totalCount > 0`): usar o primeiro resultado
  - Se não encontrado: criar o cliente

```bash
curl -s -X POST "https://api.asaas.com/v3/customers" \
  -H "access_token: $ASAAS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "<empresa>",
    "cpfCnpj": "<CNPJ_LIMPO>"
  }'
```

Sempre salvar o `asaas_customer_id` no contrato no JSON antes de continuar (se ainda não estava gravado).

### 5. Calcular nextDueDate

Usar o `vencimento_dia` do contrato para calcular a próxima data de vencimento:

```python
from datetime import date
from calendar import monthrange

today = date.today()
dia = contrato["vencimento_dia"]

# Tentar este mês
if dia > today.day:
    next_due = today.replace(day=dia)
else:
    # Já passou — avançar para o próximo mês
    if today.month == 12:
        next_due = date(today.year + 1, 1, dia)
    else:
        # Garantir que o dia existe no próximo mês
        next_month = today.month + 1
        next_year = today.year
        max_day = monthrange(next_year, next_month)[1]
        next_due = date(next_year, next_month, min(dia, max_day))

due_date_str = next_due.strftime("%Y-%m-%d")
```

### 6. Montar a descrição

| Tipo | Descrição |
|---|---|
| `tef` | `"Mensalidade do contrato de TEF — <NUMERO>"` |
| `licenca` | `"Mensalidade do contrato de Licença — <NUMERO>"` |

### 7. Exibir resumo e pedir confirmação

```
── Assinatura Mensal ────────────────────────────────────
  Contrato     : TEF-2026-0010  (tef / smartpos)
  Empresa      : Clebio Paiva Sampaio
  CNPJ         : 04.056.245/0001-91
  Cliente      : cus_000103863229
  Valor mensal : R$ 49,90
  Primeiro venc: 2026-07-05
  Ciclo        : MENSAL / PIX
  Descrição    : Mensalidade do contrato de TEF — TEF-2026-0010
─────────────────────────────────────────────────────────
Confirma criar a assinatura? [s/N]
```

**Só chamar a API após confirmação explícita.**

### 8. Criar a assinatura no Asaas

```bash
curl -s -X POST "https://api.asaas.com/v3/subscriptions" \
  -H "access_token: $ASAAS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "customer": "<CUSTOMER_ID>",
    "billingType": "PIX",
    "value": <VALOR>,
    "cycle": "MONTHLY",
    "nextDueDate": "<YYYY-MM-DD>",
    "description": "<DESCRICAO>"
  }'
```

Se a API retornar erro (status HTTP != 2xx): exibir a mensagem de erro e interromper.

Guardar `subscription.id` (formato `sub_xxx`) do response.

### 9. Salvar resultado no JSON

Atualizar o contrato em `contratos_registro.json` adicionando:

```json
"asaas_subscription_id": "sub_xxx",
"asaas_subscription_next_due": "2026-07-05"
```

Se o `asaas_customer_id` foi obtido/criado nesta execução, salvar também.

Reescrever o arquivo com `json.dump(..., indent=2, ensure_ascii=False)`.

### 10. Exibir resultado

```
✓ Assinatura criada com sucesso!

  ID da assinatura : sub_xxx
  Valor mensal     : R$ 49,90
  Primeiro venc    : 05/07/2026
  Ciclo            : Mensal / PIX
```

---

## Erros comuns

| Erro | Causa | Ação |
|---|---|---|
| Contrato não encontrado | Número errado ou não registrado | Verificar e tentar novamente |
| Contrato não está ativo | Status diferente de "ativo" | Informar e interromper |
| Assinatura já existe | `asaas_subscription_id` presente | Informar o ID existente e interromper |
| Cliente não encontrado e criação falhou | CNPJ inválido ou erro de API | Exibir erro da API, interromper |
| Erro ao criar assinatura | Dados inválidos, cliente inativo | Exibir erro do Asaas, interromper |
| ASAAS_API_KEY ausente | Token não configurado | Orientar a adicionar ao `.env` |

---

## Arquivos envolvidos

| Arquivo | Função |
|---|---|
| `ADWs/scripts/legal/contratos_registro.json` | Fonte de verdade dos contratos; atualizado com customer_id, subscription_id e next_due |
