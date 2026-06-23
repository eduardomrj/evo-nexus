# Skill: legal-cobranca-adesao

Cria uma cobrança avulsa de taxa de adesão no Asaas a partir de um contrato
TEF ou LIC registrado em `contratos_registro.json`. O contrato deve existir e
estar ativo — sem contrato, não há cobrança.

## Quando usar

- "cria cobrança de adesão para o contrato TEF-2026-0010"
- "gera cobrança de adesão do LIC-2026-0011"
- "lança a taxa de adesão do TEF-2026-0013 no Asaas"

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

Buscar o contrato pelo campo `numero`. Se não encontrado:
> "Contrato [NÚMERO] não encontrado no registro. Verifique o número e tente novamente."
— **Interromper.**

Se `status != "ativo"`:
> "Contrato [NÚMERO] está com status '[STATUS]'. Só é possível criar cobrança de adesão para contratos ativos."
— **Interromper.**

Extrair do contrato:
- `tipo` → `"tef"` ou `"licenca"`
- `cnpj`
- `empresa`
- `signatario.email` (LIC) ou ausente (TEF)

### 3. Determinar o valor de adesão

**Para contratos TEF:**
- Verificar `smartpos.adesao` ou `pinpad.adesao` (o que existir)
- Se o campo existir e for > 0: usar diretamente, mostrar ao usuário
- Se ausente ou zero: perguntar
  > "O contrato TEF [NÚMERO] não tem valor de adesão registrado. Qual o valor? (R$)"

**Para contratos LIC:**
- O JSON não tem campo de adesão por padrão
- Verificar se `adesao` já existe no contrato (campo salvo de execução anterior)
- Se existir: mostrar e perguntar se confirma ou quer alterar
- Se não existir: perguntar
  > "Qual o valor da taxa de adesão para o contrato LIC [NÚMERO]? (R$)"
- Salvar o valor informado no contrato dentro do JSON (campo `adesao` na raiz do contrato) antes de continuar

### 4. Resolver o cliente no Asaas

**Para contratos LIC:**
- Usar `asaas_customer_id` já gravado no contrato
- Se por algum motivo estiver ausente: tratar como TEF (busca por CNPJ)

**Para contratos TEF:**
- Se o contrato já tiver `asaas_customer_id`: usar diretamente
- Se não tiver: buscar por CNPJ

```bash
curl -s "https://api.asaas.com/v3/customers?cpfCnpj=<CNPJ_LIMPO>" \
  -H "access_token: $ASAAS_API_KEY"
```

  - Se encontrado (`totalCount > 0`): usar o primeiro resultado, salvar `asaas_customer_id` no contrato no JSON
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

  Salvar o `id` retornado como `asaas_customer_id` no contrato no JSON.

**Salvar `asaas_customer_id` no JSON:** sempre que obtiver ou criar um customer_id
que ainda não estava no contrato, atualizar `contratos_registro.json` imediatamente
antes de prosseguir.

### 5. Calcular vencimento D+1

```python
from datetime import date, timedelta
due_date = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
```

### 6. Exibir resumo e pedir confirmação

```
── Cobrança de Adesão ───────────────────────────────────
  Contrato   : TEF-2026-0010  (tef / smartpos)
  Empresa    : Clebio Paiva Sampaio
  CNPJ       : 04.056.245/0001-91
  Cliente    : cus_000103863229
  Valor      : R$ 150,00
  Vencimento : 2026-06-24  (D+1)
  Tipo       : PIX
  Descrição  : Taxa de adesão — TEF-2026-0010
─────────────────────────────────────────────────────────
Confirma criar a cobrança? [s/N]
```

**Só chamar a API após confirmação explícita.**

### 7. Criar a cobrança no Asaas

```bash
curl -s -X POST "https://api.asaas.com/v3/payments" \
  -H "access_token: $ASAAS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "customer": "<CUSTOMER_ID>",
    "billingType": "PIX",
    "value": <VALOR>,
    "dueDate": "<YYYY-MM-DD>",
    "description": "Taxa de adesão — <NUMERO_CONTRATO>"
  }'
```

Se a API retornar erro (status HTTP != 2xx): exibir a mensagem de erro e interromper.

Guardar `payment.id` (formato `pay_xxx`) do response.

### 8. Buscar QR code Pix

```bash
curl -s "https://api.asaas.com/v3/payments/<PAYMENT_ID>/pixQrCode" \
  -H "access_token: $ASAAS_API_KEY"
```

Guardar `payload` (string Pix copia-e-cola) e `encodedImage` (base64 PNG).

### 9. Salvar resultado no JSON

Atualizar o contrato em `contratos_registro.json` adicionando os campos:

```json
"asaas_adesao_payment_id": "pay_xxx",
"asaas_adesao_due_date": "2026-06-24",
"asaas_adesao_valor": 150.00
```

Reescrever o arquivo com `json.dump(..., indent=2, ensure_ascii=False)`.

### 10. Exibir resultado

```
✓ Cobrança criada com sucesso!

  ID do pagamento : pay_xxx
  Valor           : R$ 150,00
  Vencimento      : 24/06/2026

  Pix copia-e-cola:
  <payload>
```

---

## Erros comuns

| Erro | Causa | Ação |
|---|---|---|
| Contrato não encontrado | Número errado ou não registrado | Verificar e tentar novamente |
| Contrato não está ativo | Status diferente de "ativo" | Informar ao usuário e interromper |
| Cliente não encontrado e criação falhou | CNPJ inválido ou erro de API | Exibir erro da API, interromper |
| Erro ao criar cobrança | Saldo, cliente inativo, dados inválidos | Exibir erro do Asaas, interromper |
| ASAAS_API_KEY ausente | Token não configurado | Orientar a adicionar ao `.env` |

---

## Arquivos envolvidos

| Arquivo | Função |
|---|---|
| `ADWs/scripts/legal/contratos_registro.json` | Fonte de verdade dos contratos; atualizado com customer_id, payment_id e adesão |
