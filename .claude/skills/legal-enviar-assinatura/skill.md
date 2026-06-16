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

### 1. Coletar informações (se não fornecidas na mensagem)

Perguntar:
- **PDF**: qual contrato enviar? (número do contrato ou caminho do arquivo)
  - Os PDFs ficam em `workspace/legal/contratos/clientes/gerados/`
  - Consultar `ADWs/scripts/legal/contratos_registro.json` para localizar pelo número
- **Nome do signatário**: nome completo do representante legal do cliente
- **E-mail do signatário**: e-mail para onde o link de assinatura será enviado
- **CC** (opcional): se quiser cópia para algum e-mail interno (ex: `contratos@automacaosoftware.com.br`)

### 2. Confirmar antes de enviar

Exibir resumo e aguardar confirmação:
```
Contrato  : CONTRATO_TEF_TEF-2026-0001_04056245000191.pdf
Signatário: João da Silva <joao@empresa.com.br>
Plataforma: https://signature.automacaosoftware.com.br
Confirma o envio? [s/N]
```

### 3. Executar o script

```bash
python3 /home/evonexus/evo-nexus/ADWs/scripts/legal/enviar_documenso.py \
  --pdf "/home/evonexus/evo-nexus/workspace/legal/contratos/clientes/gerados/<ARQUIVO>.pdf" \
  --nome "<NOME DO SIGNATÁRIO>" \
  --email "<EMAIL DO SIGNATÁRIO>" \
  [--titulo "<TÍTULO OPCIONAL>"] \
  [--cc "<EMAIL DE CÓPIA>"]
```

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
