# Skill: legal-gerar-contrato-licenca

Gera o Contrato de Prestação de Serviços de Software (Licença) em PDF, preenchido automaticamente com os dados da empresa consultados via CNPJ.

## Quando usar

Sempre que o usuário pedir para gerar, emitir ou criar um contrato de licença de software para um cliente.

Exemplos de trigger:
- "gera contrato de licença para o CNPJ 12.345.678/0001-90"
- "preciso do contrato de software para essa empresa"
- "emite o contrato Emporion para CNPJ 98765432000100"
- "gera o contrato de licença com Emporion PDV e módulo NF-e"

## Fluxo de execução

### 1. Coletar informações na conversa

Perguntar ao usuário:
- **CNPJ** do cliente (aceitar com ou sem formatação)
- **Vencimento** do boleto mensal: 5, 10, 15 ou 20 (obrigatório)
- **Signatário**: nome, CPF, cargo, e-mail, telefone
- **Softwares contratados**: nome, quantidade e valor mensal total (já inclui qtd × unitário)
- **Desconto de licença** em R$ (0 se não houver)
- **Serviços de implantação**: nome, descrição e valor de cada um (mínimo 1)
- **Desconto de serviços** em R$ (0 se não houver)
- **Data** da assinatura (padrão: hoje — só perguntar se o usuário indicar outra)

Não calcular preços unitários — o usuário informa o **valor_mensal total da linha**.

### 2. Montar o JSON de entrada

```json
{
  "cnpj": "04056245000191",
  "vencimento": 10,
  "signatario": {
    "nome": "João da Silva",
    "cpf": "123.456.789-00",
    "cargo": "Sócio-Administrador",
    "email": "joao@empresa.com",
    "telefone": "(85) 99999-9999"
  },
  "softwares": [
    {"nome": "Emporion PDV", "qtd": 1, "valor_mensal": 350.00},
    {"nome": "Módulo NF-e", "qtd": 1, "valor_mensal": 80.00}
  ],
  "desconto_licenca": 0.00,
  "servicos": [
    {"nome": "Implantação", "descricao": "Instalação e configuração do sistema", "valor": 500.00},
    {"nome": "Treinamento", "descricao": "8 horas presenciais", "valor": 300.00}
  ],
  "desconto_servicos": 0.00,
  "data": "2026-06-12"
}
```

**Campos explicados:**

| Campo | Tipo | Obrigatório | Notas |
|---|---|---|---|
| `cnpj` | string | sim | Com ou sem formatação |
| `vencimento` | int | sim | Apenas 5, 10, 15 ou 20 |
| `signatario.nome` | string | sim | Nome completo |
| `signatario.cpf` | string | sim | Validado por dígitos verificadores |
| `signatario.cargo` | string | sim | Ex: Sócio-Administrador, Diretor |
| `signatario.email` | string | sim | E-mail do signatário |
| `signatario.telefone` | string | sim | Telefone/WhatsApp |
| `softwares[].nome` | string | sim | Nome do módulo/software |
| `softwares[].qtd` | int | sim | Quantidade de licenças |
| `softwares[].valor_mensal` | float | sim | Valor total da linha (não unitário) |
| `desconto_licenca` | float | não | Desconto em R$ sobre subtotal de licenças (omitir ou 0 se não houver) |
| `servicos[].nome` | string | sim | Nome do serviço |
| `servicos[].descricao` | string | sim | Descrição curta |
| `servicos[].valor` | float | sim | Valor do serviço |
| `desconto_servicos` | float | não | Desconto em R$ sobre subtotal de serviços |
| `data` | string | não | YYYY-MM-DD; padrão: hoje |

### 3. Salvar JSON e executar o script

Salvar o JSON em um arquivo temporário e executar:

```bash
python3 /home/evonexus/evo-nexus/ADWs/scripts/legal/gerar_contrato_licenca.py \
  --input /tmp/contrato_licenca.json
```

O script vai:
1. Validar todos os campos (CNPJ, CPF, vencimento)
2. Consultar a BrasilAPI com o CNPJ informado
3. Calcular todos os totais automaticamente
4. Exibir resumo e pedir confirmação
5. Gerar o PDF em `workspace/legal/contratos/clientes/gerados/`

### 4. Confirmar os dados antes de gerar

O script exibe o resumo — confirme os dados com o usuário antes de responder "s":

```
── Contrato LIC-2026-0001 ───────────────────────────
  Empresa   : [razão social da BrasilAPI]
  CNPJ      : [formatado]
  Softwares : N módulo(s) — R$ X,XX/mês
  Implantação: R$ X,XX (única)
  Total anual: R$ X,XX
  Vencimento : dia N de cada mês
  Signatário : [nome] — [cargo]
  Data       : [data extenso]
────────────────────────────────────────────────────
```

### 5. Reportar resultado

Ao final, informar o caminho do PDF gerado e oferecer as próximas ações:
- Abrir/visualizar o arquivo
- Enviar para assinatura eletrônica (DocuSign/ClickSign)
- Gerar outro contrato

## Cálculos realizados pelo script (não fazer manualmente)

- `subtotal_licenca = sum(valor_mensal)` para todos os softwares
- `total_mensal = subtotal_licenca - desconto_licenca`
- `total_anual = total_mensal × 12`
- `subtotal_servicos = sum(valor)` para todos os serviços
- `total_servicos = subtotal_servicos - desconto_servicos`
- `total_contrato = total_anual + total_servicos`
- `data_validade = data + 15 dias`

## Softwares comuns (sugestão de preenchimento)

| Software | Qtd padrão | Valor mensal sugerido |
|---|---|---|
| Emporion PDV | 1 | R$ 350,00 |
| Módulo NF-e | 1 | R$ 80,00 |
| Módulo NFC-e | 1 | R$ 80,00 |
| Módulo NFS-e | 1 | R$ 80,00 |
| Emporion PDV + NF-e + NFC-e | 1 | R$ 490,00 (combo) |

## Numeração

Sequência `LIC-YYYY-NNNN`, separada da numeração TEF. Ambas compartilham o mesmo arquivo `contratos_registro.json`.

## Arquivos envolvidos

| Arquivo | Função |
|---|---|
| `ADWs/scripts/legal/gerar_contrato_licenca.py` | Script principal |
| `workspace/legal/contratos/modelos/contrato-licenca-template.md.j2` | Template Jinja2 |
| `workspace/legal/contratos/clientes/gerados/` | PDFs gerados (nome: `CONTRATO_LIC_{numero}_{cnpj}.pdf`) |
| `ADWs/scripts/legal/contratos_registro.json` | Registro de todos os contratos (TEF + LIC) |
| `workspace/legal/contratos/modelos/contrato-licenca-software-modelo-2026.md` | Modelo de referência (leitura humana) |

## Erros comuns

| Erro | Causa | Ação |
|---|---|---|
| CNPJ não encontrado | CNPJ inexistente ou inapto na RF | Verificar CNPJ e tentar novamente |
| CPF inválido | Dígitos verificadores errados | Verificar o CPF do signatário |
| vencimento inválido | Valor diferente de 5, 10, 15 ou 20 | Corrigir o campo vencimento |
| servicos vazio | Seção 2 nunca pode ser vazia | Informar ao menos 1 serviço de implantação |
| Timeout na consulta | BrasilAPI indisponível | Aguardar e tentar novamente |
| Erro de geração PDF | weasyprint não instalado | `pip install weasyprint --break-system-packages` |
