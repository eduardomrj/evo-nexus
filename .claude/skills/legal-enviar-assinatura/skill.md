# Skill: legal-enviar-assinatura

Envia um contrato PDF gerado para assinatura eletrônica via Documenso self-hosted
(`https://signature.automacaosoftware.com.br`).

## Quando usar

Sempre que o usuário pedir para enviar um contrato para o cliente assinar.

Exemplos de trigger:
- "envia o contrato TEF-2026-0001 para o João assinar"
- "manda o contrato da Bike & Ciclo para assinatura"
- "envia o LIC-2026-0003 para o cliente assinar via Documenso"

---

## Pré-requisito

O `.env` deve ter:
```
DOCUMENSO_API_URL=https://signature.automacaosoftware.com.br
DOCUMENSO_API_KEY=<token gerado em /settings/tokens>
```

Se `DOCUMENSO_API_KEY` não estiver configurada, o script avisa e interrompe.

---

## Fluxo de execução

### 1. Coletar informações obrigatórias

**NUNCA execute o script sem ter todos os campos obrigatórios.** Se qualquer um deles estiver faltando na mensagem do usuário, pergunte antes de prosseguir — um campo por vez se necessário.

| Campo | Obrigatório | Observação |
|---|---|---|
| **Contrato** (número ou arquivo) | ✅ Sim | Consultar `contratos_registro.json` pelo número (ex: LIC-2026-0001); o PDF fica em `workspace/legal/contratos/clientes/gerados/` |
| **Nome do signatário** | ✅ Sim | Nome completo do representante legal do cliente |
| **E-mail do signatário** | ✅ Sim | Para onde o Documenso enviará o link de assinatura |
| **CC** | ❌ Opcional | E-mail de cópia interno (ex: `contratos@automacaosoftware.com.br`) |
| **Enviar agora ou salvar como DRAFT?** | ✅ Sim | Se o usuário não especificar, perguntar: "Quer que o Documenso envie o e-mail agora, ou prefere revisar e enviar manualmente pela plataforma?" |

Exemplo de pergunta quando o e-mail estiver faltando:
> "Para qual e-mail devo enviar o link de assinatura para o cliente?"

### 2. Exibir resumo completo e pedir confirmação

Antes de executar qualquer coisa, ler `ADWs/scripts/legal/contratos_registro.json` para buscar os dados do contrato pelo número informado e exibir um resumo completo para o usuário confirmar.

**O resumo varia por tipo de contrato:**

**Contrato de Licença (LIC):**
```
── Resumo do Contrato ───────────────────────────────────
  Nº Contrato : LIC-2026-0004
  Empresa     : Comercial Silva e Santos Ltda
  CNPJ        : 12.345.678/0001-95
  Tipo        : Licença de Software
  Softwares   : Emporion PDV, Emporion Manager
  Total mensal: R$ 198,00/mês
  Vencimento  : dia 10 de cada mês
  Data        : 16/06/2026
  Arquivo     : CONTRATO_LIC_LIC-2026-0004_12345678000195.pdf

── Envio para Assinatura ────────────────────────────────
  Signatário  : Daniel Gomes <danielgsn99@gmail.com>
  Contratada  : Automação Comercial LTDA. <eduardo@automacaosoftware.com.br>
  Modo        : DRAFT (envio manual pela plataforma)
  Plataforma  : https://signature.automacaosoftware.com.br
─────────────────────────────────────────────────────────
As informações acima estão corretas? Confirma? [s/N]
```

**Contrato TEF (TEF):**
```
── Resumo do Contrato ───────────────────────────────────
  Nº Contrato : TEF-2026-0001
  Empresa     : Clebio Paiva Sampaio
  CNPJ        : 04.056.245/0001-91
  Tipo        : TEF SmartPOS
  Equipamentos: 1 SmartPOS — R$ 90,00/mês + R$ 0,50/transação
  Adesão      : R$ 300,00 (cobrança única)
  Vencimento  : dia 5 de cada mês
  Data        : 12/06/2026
  Arquivo     : CONTRATO_TEF_TEF-2026-0001_04056245000191.pdf

── Envio para Assinatura ────────────────────────────────
  Signatário  : João da Silva <joao@empresa.com.br>
  Contratada  : Automação Comercial LTDA. <eduardo@automacaosoftware.com.br>
  Modo        : DRAFT (envio manual pela plataforma)
  Plataforma  : https://signature.automacaosoftware.com.br
─────────────────────────────────────────────────────────
As informações acima estão corretas? Confirma? [s/N]
```

**Só execute o script após a confirmação explícita do usuário.** Se ele corrigir algum dado (ex: e-mail errado, nome errado), atualize antes de prosseguir.

### 3. Executar o script

```bash
python3 /home/evonexus/evo-nexus/ADWs/scripts/legal/enviar_documenso.py \
  --pdf "/home/evonexus/evo-nexus/workspace/legal/contratos/clientes/gerados/<ARQUIVO>.pdf" \
  --nome "<NOME DO SIGNATÁRIO>" \
  --email "<EMAIL DO SIGNATÁRIO>" \
  [--titulo "<TÍTULO OPCIONAL>"] \
  [--cc "<EMAIL DE CÓPIA>"] \
  [--tipo licenca|tef]           # define a página padrão automaticamente
  [--pagina-assinatura N]        # override manual da página
  [--enviar]                     # dispara o e-mail imediatamente (sem a flag = DRAFT)
```

**Modo de envio:**
- **Sem `--enviar` (padrão):** cria o documento como DRAFT no Documenso. O envio do e-mail é feito manualmente pela plataforma (`signature.automacaosoftware.com.br`).
- **Com `--enviar`:** o Documenso dispara o e-mail automaticamente para os signatários após a criação.

**Página de assinatura por tipo (detectada automaticamente pelo nome do arquivo):**
- Contrato de **Licença de Software** (`CONTRATO_LIC_*`) → página **11**
- Contrato **TEF** (`CONTRATO_TEF_*`) → página **8**

**Signatários sempre incluídos:**
- CONTRATANTE (cliente) → campo direito, e-mail informado pelo usuário
- CONTRATADA (Automação) → campo esquerdo, `eduardo@automacaosoftware.com.br`

### 4. Reportar resultado

Ao final, informar ao usuário:
- ✓ Confirmação de que o documento foi enviado ao Documenso
- Link de acompanhamento no Documenso
- Status atual do documento
- Que o Documenso enviará o e-mail ao cliente via SMTP (`signature@automacaosoftware.com.br`)

---

## O que o script faz internamente

| Etapa | Ação |
|---|---|
| 1 | Upload do PDF para o Documenso (`POST /api/v1/documents`) |
| 2 | Adiciona signatário com papel `SIGNER` (`POST /api/v1/documents/{id}/recipients`) |
| 2b | Adiciona cópia com papel `CC` (opcional) |
| 3 | Instrui o Documenso a iniciar o fluxo de assinatura (`POST /api/v1/documents/{id}/send`) — **é o Documenso quem envia o e-mail ao cliente** via SMTP Zoho configurado em `smtppro.zoho.com:587`, remetente `signature@automacaosoftware.com.br` |
| 4 | Registra o envio em `workspace/legal/contratos/clientes/gerados/envios_assinatura.json` |

---

## Arquivos envolvidos

| Arquivo | Função |
|---|---|
| `ADWs/scripts/legal/enviar_documenso.py` | Script principal |
| `ADWs/scripts/legal/contratos_registro.json` | Registro de contratos gerados (para localizar PDF pelo número) |
| `workspace/legal/contratos/clientes/gerados/` | PDFs a enviar |
| `workspace/legal/contratos/clientes/gerados/envios_assinatura.json` | Histórico de envios |

---

## Erros comuns

| Erro | Causa | Ação |
|---|---|---|
| `DOCUMENSO_API_KEY não encontrada` | Token não configurado no `.env` | Gerar token em `/settings/tokens` e adicionar ao `.env` |
| HTTP 401 | Token inválido ou expirado | Regenerar token no Documenso |
| HTTP 404 no endpoint `/api/v1/documents` | URL da API incorreta ou versão diferente | Verificar `DOCUMENSO_API_URL` no `.env` |
| Arquivo não encontrado | Caminho do PDF errado | Confirmar o nome exato em `contratos_registro.json` |

---

## Consultar histórico de envios

Para ver quais contratos já foram enviados:
```bash
cat workspace/legal/contratos/clientes/gerados/envios_assinatura.json
```

Para acompanhar um documento específico:
```
https://signature.automacaosoftware.com.br/documents/<doc_id>
```
