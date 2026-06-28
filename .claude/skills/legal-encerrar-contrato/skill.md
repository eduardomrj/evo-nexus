# Skill: legal-encerrar-contrato

Encerra um contrato por **desistência** (antes de assinar) ou **cancelamento** (após assinar),
atualizando o registro, removendo o documento do Documenso e aplicando as regras corretas de
retenção de dados.

## Quando usar

Sempre que o usuário informar que um cliente desistiu ou cancelou um contrato.

Exemplos de trigger:
- "o cliente desistiu do contrato TEF-2026-0010"
- "preciso cancelar o contrato LIC-2026-0011, o cliente encerrou"
- "encerra o TEF-2026-0024 por desistência"
- "cancelar contrato da empresa X"
- "cliente voltou atrás, não vai assinar o contrato"

---

## Distinção obrigatória: desistência vs cancelamento

| | Desistência | Cancelamento |
|---|---|---|
| **Quando ocorre** | Antes de o cliente assinar | Após assinatura (contrato estava ativo) |
| **Status no registro** | `desistido` | `cancelado` |
| **Documenso** | Deleta o documento (se existir) | Deleta o documento (se existir) |
| **PDF local** | **Deleta** (processo não concluído) | **Mantém** (histórico completo) |
| **envios_assinatura.json** | **Remove** a entrada | **Mantém** (histórico: foi enviado, assinado, depois cancelado) |
| **Asaas** | Não altera (a menos que `--cancelar-asaas`) | Não altera (a menos que `--cancelar-asaas`) |

---

## Pré-requisito

O `.env` deve ter:
```
DOCUMENSO_API_URL=https://signature.automacaosoftware.com.br
DOCUMENSO_API_KEY=<token>
ASAAS_API_KEY=<token>   # só necessário se --cancelar-asaas for usado
```

---

## Fluxo de execução

### 1. Coletar informações obrigatórias

Antes de executar, confirme:

| Campo | Obrigatório | Observação |
|---|---|---|
| **Número do contrato** | ✅ Sim | Ex: TEF-2026-0010, LIC-2026-0011 |
| **Motivo** | ✅ Sim | `desistencia` ou `cancelamento` — perguntar se não for claro |
| **Cancelar no Asaas?** | ❌ Só se pedido explicitamente | `--cancelar-asaas` cancela subscription e/ou cobrança de adesão |

Se o motivo não for claro, perguntar:
> "O cliente desistiu **antes** de assinar, ou o contrato já estava **ativo/assinado** e foi encerrado depois?"

**Nunca assuma o motivo — a diferença determina o que será deletado.**

Se o usuário pedir para cancelar/remover do Asaas, confirmar antes de prosseguir:
> "Isso vai cancelar a subscription e/ou a cobrança de adesão no Asaas. Confirma?"

### 2. Exibir resumo (gerado pelo script) e pedir confirmação

O script exibe automaticamente um resumo com todas as ações antes de executar. Informe o usuário que o script pedirá confirmação interativa.

### 3. Executar o script

**Desistência (sem cancelar Asaas):**
```bash
python3 /home/evonexus/evo-nexus/ADWs/scripts/legal/encerrar_contrato.py \
  --contrato <NUMERO> \
  --motivo desistencia
```

**Cancelamento (sem cancelar Asaas):**
```bash
python3 /home/evonexus/evo-nexus/ADWs/scripts/legal/encerrar_contrato.py \
  --contrato <NUMERO> \
  --motivo cancelamento
```

**Com cancelamento no Asaas (qualquer motivo):**
```bash
python3 /home/evonexus/evo-nexus/ADWs/scripts/legal/encerrar_contrato.py \
  --contrato <NUMERO> \
  --motivo desistencia|cancelamento \
  --cancelar-asaas
```

### 4. Reportar resultado

Ao final, informar ao usuário:
- ✓ Novo status do contrato no registro
- ✓ O que foi deletado/mantido (Documenso, PDF, envios_assinatura)
- ✓ O que foi feito no Asaas (se `--cancelar-asaas` usado)
- Se alguma ação falhou (ex: doc não encontrado no Documenso), mencionar com contexto

---

## O que o script faz internamente

| Ação | Desistência | Cancelamento |
|---|---|---|
| Atualiza `contratos_registro.json` | `status: desistido` | `status: cancelado` |
| Deleta doc no Documenso | ✓ (se `doc_id` registrado) | ✓ (se `doc_id` registrado) |
| Remove PDF local | ✓ deleta | ✗ mantém |
| Remove entrada em `envios_assinatura.json` | ✓ remove | ✗ mantém |
| Cancela subscription Asaas | Só com `--cancelar-asaas` | Só com `--cancelar-asaas` |
| Cancela cobrança de adesão Asaas | Só com `--cancelar-asaas` | Só com `--cancelar-asaas` |

O script sempre mostra um resumo completo das ações e pede confirmação antes de executar.

---

## Arquivos envolvidos

| Arquivo | Função |
|---|---|
| `ADWs/scripts/legal/encerrar_contrato.py` | Script principal |
| `ADWs/scripts/legal/contratos_registro.json` | Registro de contratos (source of truth) |
| `workspace/legal/contratos/clientes/gerados/` | PDFs dos contratos |
| `workspace/legal/contratos/clientes/gerados/envios_assinatura.json` | Histórico de envios Documenso |

---

## Erros comuns

| Erro | Causa | Ação |
|---|---|---|
| `Contrato X não encontrado no registro` | Número digitado errado ou já removido | Verificar `contratos_registro.json` |
| Erro HTTP 404 no Documenso | Doc já foi deletado manualmente | Normal — o script ignora e continua |
| Erro HTTP 400/404 no Asaas | Subscription/cobrança já cancelada | Verificar status no painel Asaas |
| `DOCUMENSO_API_KEY não encontrada` | `.env` incompleto | Verificar `.env` na raiz do EvoNexus |
