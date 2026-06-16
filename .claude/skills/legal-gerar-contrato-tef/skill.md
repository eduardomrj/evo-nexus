# Skill: legal-gerar-contrato-tef

Gera o Contrato Complementar TEF (SmartPOS e/ou Pinpad) em PDF, preenchido automaticamente com os dados da empresa consultados via CNPJ.

## Quando usar

Sempre que o usuário pedir para gerar, emitir ou criar um contrato TEF para um cliente.

Exemplos de trigger:
- "gera contrato TEF para o CNPJ 12.345.678/0001-90"
- "preciso do contrato TEF SmartPOS para essa empresa"
- "emite o contrato pinpad para CNPJ 98765432000100"

## Fluxo de execução

### 1. Coletar informações (se não fornecidas na mensagem)

Perguntar:
- **CNPJ** do cliente (aceitar com ou sem formatação)
- **Modalidade**: SmartPOS / Pinpad / Ambos
- **Parceiro/Revendedor**: "Esse contrato tem participação de um parceiro ou revendedor?" (sim/não)
  - Se sim:
    1. Ler `ADWs/scripts/legal/parceiros.json`
    2. Listar os parceiros ativos com número, empresa e representante
    3. Usuário escolhe pelo número ou nome
    4. Usar os dados do cadastro (empresa, representante, cpf, email) — não pedir novamente
    - Se o parceiro não estiver no cadastro: coletar empresa, representante, CPF e email manualmente
      e orientar o usuário a adicionar em `ADWs/scripts/legal/parceiros.json` para uso futuro

Não perguntar data — usar a data de hoje por padrão. Só perguntar se o usuário indicar explicitamente uma data diferente.

### 2. Executar o script

```bash
python3 /home/evonexus/evo-nexus/ADWs/scripts/legal/gerar_contrato_tef.py \
  "<CNPJ>" \
  "<modalidade: smartpos|pinpad|ambos>" \
  [--smartpos N]                    # qtd equipamentos SmartPOS (padrão: 1)
  [--pinpad N]                      # qtd equipamentos Pinpad (padrão: 1)
  [--vol-smartpos N]                # volume estimado transações SmartPOS/mês (padrão: 500)
  [--vol-pinpad N]                  # volume estimado transações Pinpad/mês (padrão: 500)
  [--data YYYY-MM-DD]               # data da assinatura (padrão: hoje)
  # Preços customizáveis — omitir usa o padrão da tabela
  [--adesao-smartpos X]             # taxa de adesão SmartPOS (padrão: 150,00)
  [--mensal-smartpos X]             # mensalidade por equip. SmartPOS (padrão: 49,90)
  [--trans-smartpos X]              # preço por transação SmartPOS (padrão: 0,25)
  [--adesao-pinpad X]               # taxa de adesão Pinpad (padrão: 360,00)
  [--mensal-pinpad X]               # mensalidade por equip. Pinpad (padrão: 140,00)
  [--trans-pinpad X]                # preço por transação Pinpad (padrão: 0,14)
  # Parceiro/revendedor (todos os 3 obrigatórios juntos se houver parceiro)
  [--parceiro-empresa "Nome Ltda"]           # nome da empresa parceira
  [--parceiro-representante "João Silva"]    # nome do representante
  [--parceiro-cpf "123.456.789-00"]          # CPF do representante
```

> Quando preços customizados forem informados, o terminal exibirá um aviso `⚠ preço customizado` antes de pedir confirmação — confirmar antes de gerar.

O script vai:
1. Consultar a BrasilAPI com o CNPJ informado
2. Exibir os dados encontrados e pedir confirmação
3. Gerar o PDF em `workspace/legal/contratos/clientes/gerados/`

### 3. Confirmar os dados para o usuário

Antes de o script gerar o PDF, exibir ao usuário:
- Razão social encontrada
- Endereço completo
- Modalidade, quantidade de equipamentos e valores (mensalidade + taxa por transação aprovada)
- Volume estimado de transações/mês
- Se houver preços customizados, destacar com `⚠` e listar os valores negociados
- Se houver parceiro: nome da empresa, representante e CPF

Aguardar confirmação do usuário antes de prosseguir.

### 4. Reportar resultado

Ao final, informar o caminho do PDF gerado e oferecer as próximas ações:
- Abrir/visualizar o arquivo
- Enviar para assinatura eletrônica via `legal-enviar-assinatura`
  - Se tiver parceiro: o email já vem do cadastro — não precisa pedir novamente
- Gerar outro contrato

## Valores padrão (referência)

| Modalidade | Taxa de Adesão | Mensalidade por equip. | Por transação aprovada |
|---|---|---|---|
| SmartPOS | R$ 150,00 | R$ 49,90 | R$ 0,25 |
| Pinpad | R$ 360,00 | R$ 140,00 | R$ 0,14 |

Qualquer um desses valores pode ser substituído via parâmetros customizáveis. Se o usuário informar valores diferentes do padrão, perguntar: "Confirma os preços negociados para esse cliente?" antes de executar.

## Cadastro de parceiros

Arquivo: `ADWs/scripts/legal/parceiros.json`

Estrutura de cada entrada:
```json
{
  "id": "slug-unico",
  "empresa": "Nome da Empresa Parceira Ltda",
  "cnpj": "12.345.678/0001-90",
  "representante": "Nome do Representante",
  "cpf": "123.456.789-00",
  "email": "representante@parceiro.com.br",
  "ativo": true
}
```

- `id` — slug curto para identificação (ex: `"abc-distribuidora"`)
- `email` — obrigatório; usado pelo Documenso para envio de assinatura
- `ativo: false` — desativa o parceiro sem apagar o histórico; não aparece na listagem

## Arquivos envolvidos

| Arquivo | Função |
|---|---|
| `ADWs/scripts/legal/gerar_contrato_tef.py` | Script principal |
| `workspace/legal/contratos/modelos/contrato-tef-template.md.j2` | Template Jinja2 |
| `workspace/legal/contratos/clientes/gerados/` | PDFs gerados |
| `workspace/legal/contratos/modelos/contrato-tef-cliente-final-v1.md` | Modelo de referência (leitura humana) |

## Erros comuns

| Erro | Causa | Ação |
|---|---|---|
| CNPJ não encontrado | CNPJ inexistente ou inapto na RF | Verificar CNPJ e tentar novamente |
| Timeout na consulta | BrasilAPI indisponível | Aguardar e tentar novamente |
| Erro de geração PDF | weasyprint não instalado | `pip install weasyprint --break-system-packages` |
