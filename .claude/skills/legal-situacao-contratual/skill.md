# Skill: legal-situacao-contratual

Gera um panorama cruzado dos contratos de uma empresa específica, verificando três dimensões:
local (PDF existe?), Documenso (publicado e assinado?) e Asaas (assinatura ativa com valor correto?).

## Quando usar

Sempre que o usuário pedir uma visão geral dos contratos de uma empresa, auditoria de status
ou verificação de pendências de assinatura/cobrança.

Exemplos de trigger:
- "situação contratual da empresa X"
- "situação contratual do CNPJ 04.056.245/0001-91"
- "verifica os contratos da Elitanio"
- "confere se os valores do Asaas batem com os contratos da [empresa]"
- "quais contratos da [empresa] estão com cobrança divergente"
- "rodar a varredura de contrato no CNPJ X"
- "auditoria de contratos da empresa X"

## Coleta de dados obrigatória

**Antes de executar o script**, verificar se o usuário informou CNPJ ou nome da empresa.
Se não veio na mensagem, perguntar:

> "Qual empresa devo consultar? Informe o CNPJ (com ou sem formatação) ou parte do nome."

Só prosseguir com a execução após ter um dos dois.

---

## Pré-requisitos

O `.env` deve ter:
```
ASAAS_API_KEY=<token>
DOCUMENSO_API_URL=https://signature.automacaosoftware.com.br
DOCUMENSO_API_KEY=<token>
```

---

## Fluxo de execução

### 1. Executar o script de coleta

Use `--cnpj` ou `--nome` conforme o dado informado pelo usuário (mutuamente exclusivos):

```bash
# Por CNPJ (com ou sem formatação)
python3 /home/evonexus/evo-nexus/ADWs/scripts/legal/situacao_contratual.py \
  --cnpj "04.056.245/0001-91"

# Por nome (busca parcial, case-insensitive)
python3 /home/evonexus/evo-nexus/ADWs/scripts/legal/situacao_contratual.py \
  --nome "Elitanio"
```

O script retorna JSON no stdout com a seguinte estrutura:

```json
{
  "gerado_em": "2026-06-25 14:30:00",
  "empresa": "ELITANIO COMERCIO E SERVICOS LTDA",
  "cnpj": "04.056.245/0001-91",
  "resumo": {
    "total_contratos": 22,
    "pdf_local_ok": 22,
    "pdf_local_ausente": 0,
    "documenso_assinados": 10,
    "documenso_pendentes": 8,
    "documenso_nao_enviados": 4,
    "asaas_match_ok": 9,
    "asaas_divergentes": 1,
    "asaas_sem_assinatura": 5
  },
  "contratos": [ ... ],
  "erros": []
}
```

### 2. Montar o template padrão de resposta

Use exatamente o template abaixo. Apenas a seção **Observacoes** muda a cada execução —
ela deve ser gerada com analise propria do agente a partir dos dados coletados.

---

## Template padrao de resposta

```
SITUAÇÃO CONTRATUAL — {empresa} | CNPJ: {cnpj}
Gerado em: {data_hora}
Fonte: contratos_registro.json x Documenso x Asaas

RESUMO EXECUTIVO
────────────────────────────────────────────────────────
Total de contratos registrados : {total}
PDFs gerados (arquivo local)   : {pdf_ok} / {total}
Assinados no Documenso         : {assinados} / {total}
Pendentes de assinatura        : {pendentes}
Não enviados ao Documenso      : {nao_enviados}
Valores Asaas OK               : {match_ok}
Valores DIVERGENTES            : {divergentes}
Sem assinatura Asaas           : {sem_assinatura}

DETALHE POR CONTRATO
────────────────────────────────────────────────────────
[Para cada contrato, uma linha no formato abaixo:]

  Contrato : {numero}
  Empresa  : {empresa} | CNPJ: {cnpj}
  Tipo     : {tipo} | Data: {data_contrato}
  PDF local: {SIM / NAO — arquivo: {arquivo}}
  Documenso: {documenso_status} | Doc #{documenso_doc_id} | {documenso_link}
             Enviado em: {documenso_enviado_em}
  Asaas    : {asaas_status} | Valor assinatura: R$ {asaas_valor} | Ciclo: {asaas_ciclo}
             Próxima cobrança: {asaas_proxima_cobranca}
  Contrato : R$ {valor_contrato_local}/mês esperado
  Match    : {match_valor}
  ────────

OBSERVAÇÕES
────────────────────────────────────────────────────────
{CAMPO LIVRE — gerado pelo agente a cada execução}

Inclua nesta seção:
- Alertas sobre divergências de valor (DIVERGENTE)
- Contratos sem assinatura Asaas quando deveriam ter
- Contratos não enviados ao Documenso
- PDFs ausentes localmente
- Assinaturas ainda pendentes no Documenso (PENDENTE)
- Padrões observados (ex: todos os TEF de um parceiro sem assinatura)
- Recomendação de próximo passo para cada grupo de problema
- Avisos sobre possíveis erros de dados (ex: mesmo sub_id em contratos diferentes)

DISCLAIMER
────────────────────────────────────────────────────────
Orientação operacional, não parecer jurídico definitivo.
Em caso de dúvida relevante, risco alto ou exceção contratual,
escale para Eduardo ou para um advogado qualificado.
```

---

## Regras de preenchimento do template

### Status PDF local
- `SIM` — arquivo encontrado em `workspace/legal/contratos/clientes/gerados/`
- `NAO` — arquivo ausente (risco: contrato não pode ser enviado para assinatura)

### Status Documenso
| Valor no JSON         | Exibir no template         |
|-----------------------|----------------------------|
| `ASSINADO`            | ASSINADO (COMPLETED)       |
| `PENDENTE`            | PENDENTE (aguardando assinaturas) |
| `RASCUNHO`            | RASCUNHO (DRAFT)           |
| `enviado_sem_status`  | ENVIADO (sem status disponível na API principal) |
| `documento_removido`  | REMOVIDO DO DOCUMENSO (enviado, doc_id registrado, mas documento não existe mais) |
| `nao_encontrado`      | NAO ENVIADO AO DOCUMENSO   |

### Match de valor
| Valor       | Exibir                                             |
|-------------|-----------------------------------------------------|
| `OK`        | OK — valor confere (R$ X,XX)                       |
| `DIVERGENTE`| DIVERGENTE — esperado R$ X,XX / Asaas R$ Y,YY      |
| `sem_assinatura` | SEM ASSINATURA no Asaas                       |
| `erro_consulta`  | ERRO AO CONSULTAR ASAAS                       |
| `sem_valor_local`| Valor local não mapeado                       |
| `sem_dados` | Sem dados suficientes                              |

### Ciclos Asaas
- `MONTHLY` → mensal
- `WEEKLY` → semanal
- `YEARLY` → anual

---

## Arquivos envolvidos

| Arquivo | Funcao |
|---|---|
| `ADWs/scripts/legal/situacao_contratual.py` | Script que coleta e cruza os dados |
| `ADWs/scripts/legal/contratos_registro.json` | Registro de todos os contratos (TEF + LIC) |
| `workspace/legal/contratos/clientes/gerados/` | PDFs gerados + `envios_assinatura.json` |
| `workspace/legal/` | Pasta de trabalho do agente legal |

---

## Observações tecnicas

- O script usa `envios_assinatura.json` como cache local dos envios ao Documenso.
  Se um contrato foi enviado via conta de parceiro (Inforcell, Solutiontec), o status
  pode aparecer como `enviado_sem_status` porque a API principal não tem acesso à conta
  do parceiro. Isso é esperado — não é erro.

- Contratos sem `asaas_subscription_id` no registro (ex: alguns TEF) nao terão dados
  Asaas. Verificar se a assinatura foi criada ou se o contrato é de adesão única.

- LIC-2026-0023 e LIC-2026-0026 compartilham o mesmo `asaas_customer_id`; verificar
  se compartilham também o mesmo `asaas_subscription_id` — pode indicar que a segunda
  assinatura ainda não foi criada no Asaas.

- O match de valor para contratos TEF usa `smartpos.mensalidade` como referência,
  ignorando a taxa por transação (variável).

- Para salvar o resultado em arquivo:
  ```bash
  python3 /home/evonexus/evo-nexus/ADWs/scripts/legal/situacao_contratual.py \
    --cnpj "04.056.245/0001-91" \
    --output /tmp/panorama_$(date +%Y%m%d).json
  ```
