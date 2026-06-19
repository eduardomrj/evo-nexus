# Skill: legal-gerar-contrato-licenca-asaas

Gera o Contrato de Licença de Software (LIC) preenchido automaticamente com dados
da assinatura ativa do cliente no ASAAS — valor, vencimento e sistemas contratados
são extraídos da API sem precisar ser informados manualmente.

## Quando usar

Sempre que o usuário pedir para gerar um contrato de licença para um cliente que
já tem assinatura ativa no ASAAS.

Exemplos de trigger:
- "gera contrato LIC pelo ASAAS para o CNPJ 04056245000191"
- "cria contrato de licença com base na assinatura do ASAAS para essa empresa"
- "emite o contrato do cliente com base no que ele já paga no ASAAS"

---

## Pré-requisitos

O `.env` deve ter:
```
ASAAS_API_KEY=<token>
```

---

## Fluxo de execução

### 1. Receber o CNPJ

Se não informado na mensagem, perguntar:
> "Qual o CNPJ do cliente?"

### 2. Consultar o ASAAS

#### 2a. Buscar o cliente

```bash
curl -s "https://api.asaas.com/v3/customers?cpfCnpj=<CNPJ_LIMPO>" \
  -H "access_token: $ASAAS_API_KEY"
```

- Se `totalCount = 0`: informar ao usuário que o cliente não foi encontrado no ASAAS e interromper.
- Se encontrado: guardar `customer.id`, `customer.name`, `customer.email`.

#### 2b. Buscar assinatura ativa

```bash
curl -s "https://api.asaas.com/v3/subscriptions?customer=<CUSTOMER_ID>&status=ACTIVE" \
  -H "access_token: $ASAAS_API_KEY"
```

- Se `totalCount = 0`: informar que não há assinatura ativa e interromper.
- Se mais de uma assinatura ativa: listar todas e perguntar qual usar.
- Se uma assinatura: usar diretamente.

#### 2c. Extrair dados da assinatura

| Campo ASAAS | Uso no contrato |
|---|---|
| `value` | Valor mensal do pacote |
| `nextDueDate` | Extrair o dia (ex: `2026-08-20` → dia `20`) |
| `description` | Nomes dos sistemas (ex: "Emporion PDV Fiscal\nEmporion Manager\nEmporion NFe") |

**Montar o nome do pacote:**
- Limpar a `description`: remover `\t`, `\r`, normalizar espaços, separar por `\n`
- Formatar como: `PACOTE EMPORION (Sistema A, Sistema B, Sistema C)`
- Se a description estiver vazia: usar `PACOTE EMPORION`

**Vencimento:** extrair só o dia de `nextDueDate`. Se o dia não for 5, 10, 15 ou 20,
arredondar para o mais próximo e avisar o usuário.

### 3. Coletar dados que o ASAAS não tem

Perguntar na seguinte ordem:

| Campo | Obrigatório | Observação |
|---|---|---|
| **Nome do signatário** | ✅ Sim | Representante legal que vai assinar |
| **CPF do signatário** | ✅ Sim | Validar dígitos verificadores |
| **Cargo do signatário** | ✅ Sim | Ex: Sócio-Administrador, Diretor |
| **E-mail do signatário** | ✅ Sim | Para o Documenso |
| **Telefone do signatário** | ✅ Sim | WhatsApp/celular |
| **Parceiro/Revendedor?** | ✅ Sim | Sim/não → se sim, listar `parceiros.json` |
| **Implantação** | ❌ Opcional | Se não informada, lançar R$ 0,00 automaticamente |

Sobre a implantação: perguntar uma vez:
> "Há serviços de implantação a lançar no contrato? (ex: instalação, treinamento) Se não, deixo como R$ 0,00."

Se não houver, montar automaticamente:
```json
[{"nome": "Implantação", "descricao": "Incluso", "valor": 0.00}]
```

### 4. Exibir resumo e pedir confirmação

```
── Contrato via ASAAS ───────────────────────────────────
  Cliente    : Elitanio Veículos
  CNPJ       : 04.056.245/0001-91
  Assinatura : sub_u5vexpfhchg1bz1z — ATIVA
  Software   : PACOTE EMPORION (Emporion PDV Fiscal, Emporion Manager, Emporion NFe)
  Valor      : R$ 220,31/mês
  Vencimento : dia 20
  Implantação: R$ 0,00
  Signatário : João da Silva — Sócio-Administrador
  CPF        : 123.456.789-00
  Parceiro   : Inforcell Sistemas — Eridan Alves
─────────────────────────────────────────────────────────
Os dados acima estão corretos? Confirma? [s/N]
```

**Só montar o JSON e executar o script após confirmação explícita.**

### 5. Montar o JSON e executar o script

```json
{
  "cnpj": "<CNPJ_LIMPO>",
  "vencimento": <DIA>,
  "signatario": {
    "nome": "<NOME>",
    "cpf": "<CPF>",
    "cargo": "<CARGO>",
    "email": "<EMAIL>",
    "telefone": "<TELEFONE>"
  },
  "softwares": [
    {
      "nome": "PACOTE EMPORION (<sistemas>)",
      "qtd": 1,
      "valor_mensal": <VALUE>
    }
  ],
  "desconto_licenca": 0.00,
  "servicos": [
    {"nome": "Implantação", "descricao": "Incluso", "valor": 0.00}
  ],
  "desconto_servicos": 0.00
}
```

Salvar em `/tmp/contrato_licenca_asaas.json` e executar:

```bash
python3 /home/evonexus/evo-nexus/ADWs/scripts/legal/gerar_contrato_licenca.py \
  --input /tmp/contrato_licenca_asaas.json
```

Se houver parceiro com `documenso_api_key_env`: anotar para usar em `legal-enviar-assinatura`.

### 6. Reportar resultado

Ao final, informar:
- ✓ Número do contrato gerado (ex: LIC-2026-0010)
- Caminho do PDF
- Oferecer encaminhar para assinatura via `legal-enviar-assinatura`

---

## Erros comuns

| Erro | Causa | Ação |
|---|---|---|
| Cliente não encontrado no ASAAS | CNPJ não cadastrado | Verificar CNPJ e tentar novamente ou usar `legal-gerar-contrato-licenca` |
| Nenhuma assinatura ativa | Cliente sem assinatura ativa | Usar `legal-gerar-contrato-licenca` com dados manuais |
| Dia de vencimento inválido | `nextDueDate` com dia diferente de 5/10/15/20 | Arredondar e avisar o usuário |
| ASAAS_API_KEY não encontrada | Token não configurado no `.env` | Adicionar token ao `.env` |

---

## Arquivos envolvidos

| Arquivo | Função |
|---|---|
| `ADWs/scripts/legal/gerar_contrato_licenca.py` | Script que gera o PDF (reutilizado) |
| `ADWs/scripts/legal/parceiros.json` | Cadastro de parceiros |
| `ADWs/scripts/legal/contratos_registro.json` | Histórico de contratos gerados |
| `ADWs/scripts/legal/contratos_sequencia.json` | Controle de numeração |
| `/tmp/contrato_licenca_asaas.json` | JSON temporário de entrada para o script |
