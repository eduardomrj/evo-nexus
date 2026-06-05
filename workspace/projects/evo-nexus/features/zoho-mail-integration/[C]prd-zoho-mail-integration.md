# [C] PRD — Zoho Mail Integration

## Status

**Aprovado com ajustes arquiteturais pelo Apex.**  
Documento atualizado para implementação futura, sem iniciar build.

## Decisões arquiteturais fechadas para implementação futura

1. **Storage de tokens:** usar namespace próprio `ZOHO_MAIL_*`; não reaproveitar variáveis Bling.
2. **Persistência:** tokens podem ir para `.env`/ambiente conforme padrão atual, com escrita atômica e redaction obrigatória; segredos originais devem ficar no Vaultwarden.
3. **Multi-DC:** `accounts_server_url` e `api_domain` devem vir do OAuth/Zoho e ser usados pelo client; não hardcodar `.com`, `.com.br` ou qualquer região.
4. **Rascunho MVP:** usar rascunho local/payload revisável; não criar draft remoto na Zoho no MVP.
5. **Confirmação de envio:** exigir string literal `YES, SEND`, igual ao padrão `gog-email-send`.
6. **Dashboard:** status OAuth real, não apenas presença de env vars: `not_configured`, `needs_auth`, `connected`, `needs_reauth`, `error_sanitized`.
7. **Erros/logs:** não copiar cegamente o `int-bling`; sanitizar corpo de erro OAuth/API antes de stderr, log ou UI.
8. **Docs Zoho:** confirmar endpoints/payloads oficiais antes de codar a etapa de API.

## Problema

O EvoNexus hoje possui capacidades de e-mail orientadas principalmente ao ecossistema Google/Gmail, mas Eduardo precisa conectar contas Zoho Mail diretamente via API oficial/OAuth para leitura, triagem, rascunhos e envio confirmado.

A integração deve ser feita via **Zoho Mail API + OAuth2 server-based**, não via Gmail, SMTP, IMAP ou scraping.

## Objetivos

1. Implementar integração Zoho Mail via OAuth2 server-based.
2. Criar primeiro como `custom-int-zoho-mail`, com possibilidade de promover para `int-zoho-mail` depois.
3. Reaproveitar o padrão de OAuth2 do `int-bling`: callback, `state`, refresh token, retry em `401` e persistência segura.
4. Reaproveitar o contrato das skills `gog-email-*`: triagem read-only, rascunho sem envio automático e envio apenas com confirmação explícita.
5. Suportar múltiplos data centers Zoho capturando `accounts_server_url` e `api_domain`.
6. Expor status da conexão em `/integrations`.
7. Garantir que tokens, secrets e headers sensíveis nunca sejam logados.

## Fora de escopo

- Gmail, SMTP, IMAP ou POP3.
- Sync completo de mailbox.
- UI completa de webmail.
- Heartbeat/automações proativas no MVP.
- Envio automático sem confirmação humana.
- Anexos no MVP, salvo se for trivial e seguro.
- Assumir domínio Zoho `.com.br`; a região deve vir do OAuth.

## Uso esperado no MVP

1. Conectar Zoho Mail via OAuth.
2. Validar status da conexão.
3. Listar contas disponíveis.
4. Listar pastas.
5. Ler mensagens recentes da Inbox.
6. Buscar mensagens.
7. Preparar resposta/rascunho.
8. Enviar e-mail de teste somente após confirmação explícita.

## Requisitos funcionais

### RF0 — Decisões obrigatórias de implementação

A implementação futura deve seguir estas decisões fechadas após validação do Apex:

- variáveis e tokens em namespace próprio `ZOHO_MAIL_*`;
- `accounts_server_url` e `api_domain` capturados do OAuth/Zoho, não configurados manualmente como fallback principal;
- rascunho do MVP é local/payload revisável, não draft remoto;
- envio exige confirmação literal `YES, SEND`;
- dashboard usa status OAuth real: `not_configured`, `needs_auth`, `connected`, `needs_reauth`, `error_sanitized`;
- erros OAuth/API devem ser sanitizados antes de qualquer log, stderr, resposta ou UI.

### RF1 — OAuth2 server-based

A integração deve implementar fluxo OAuth2 server-based da Zoho com:

- authorization code com validade curta;
- access token com validade aproximada de 1h;
- refresh token;
- callback HTTP;
- validação de `state` contra CSRF;
- renovação automática do access token.

### RF2 — Multi-DC Zoho

A integração deve capturar e persistir:

- `accounts_server_url`;
- `api_domain`.

Não deve hardcodar `accounts.zoho.com`, `mail.zoho.com` nem qualquer domínio regional.

### RF3 — Scopes MVP

Usar apenas:

- `ZohoMail.accounts.READ`;
- `ZohoMail.folders.READ`;
- `ZohoMail.messages.READ`;
- `ZohoMail.messages.CREATE`.

### RF4 — Endpoints Zoho Mail MVP

Cobrir:

- listar contas;
- listar pastas;
- listar mensagens;
- buscar mensagens;
- criar/enviar mensagem.

Os paths finais devem ser confirmados contra a documentação oficial antes da implementação.

### RF5 — Skill `custom-int-zoho-mail`

A skill deve permitir:

- status;
- conectar/reautenticar;
- listar contas;
- listar pastas;
- triagem Inbox read-only;
- busca;
- preparar rascunho;
- enviar somente após confirmação.

### RF6 — Dashboard `/integrations`

O dashboard deve mostrar status OAuth real, não apenas presença de env vars:

- `not_configured`: client id/secret ausentes;
- `needs_auth`: app configurado, mas sem conexão OAuth;
- `connected`: refresh token válido e conta detectada;
- `needs_reauth`: refresh token inválido/revogado;
- `error_sanitized`: erro operacional sem exposição de segredo.

Também deve mostrar:

- botão/ação conectar;
- conta conectada ou identificador seguro;
- última validação;
- erro sanitizado;
- reautenticação quando necessário.

## Requisitos não funcionais

### Segurança

- Nunca logar tokens ou secrets.
- Validar `state` no callback.
- Usar HTTPS em produção.
- Redigir erros antes de exibir.
- Manter escopos mínimos.
- Envio exige confirmação explícita.

### Confiabilidade

- Refresh automático quando access token expirar.
- Retry único após `401`.
- Se refresh falhar, marcar como “reautenticação necessária”.

### Observabilidade

Registrar eventos sanitizados:

- OAuth iniciado/concluído;
- refresh realizado;
- chamada falhou;
- envio confirmado executado.

Não registrar corpo integral de e-mail por padrão.

## Critérios de aceite

### CA1 — Conexão OAuth

**Dado** que as variáveis Zoho estão configuradas  
**Quando** Eduardo iniciar a conexão  
**Então** o EvoNexus redireciona para consentimento Zoho com `state` válido e scopes MVP.

### CA2 — Callback OAuth

**Dado** que Eduardo autorizou o app  
**Quando** a Zoho chamar o callback  
**Então** o EvoNexus valida `state`, troca `code` por tokens, salva domínios/tokens com segurança e marca a integração como conectada.

### CA3 — State inválido

**Dado** callback com `state` inválido  
**Quando** processado  
**Então** a autenticação é rejeitada e nenhum token é salvo.

### CA4 — Refresh automático

**Dado** access token expirado  
**Quando** uma chamada for feita  
**Então** o token é renovado e a chamada repetida uma vez.

### CA5 — Listagem e busca

**Dado** integração conectada  
**Quando** listar contas, pastas, Inbox ou buscar mensagens  
**Então** a API retorna dados resumidos sem expor segredos.

### CA6 — Envio confirmado

**Dado** mensagem pronta  
**Quando** Eduardo confirmar com a string literal `YES, SEND`  
**Então** a mensagem é enviada pela Zoho API e o evento é registrado sem tokens/conteúdo sensível.

### CA7 — Não vazamento

**Dado** qualquer operação OAuth/API  
**Quando** logs ou erros forem gerados  
**Então** tokens, secrets e Authorization headers não aparecem.

## Riscos

1. Data center incorreto se hardcodar domínio.
2. Authorization code expira rápido.
3. Escopo insuficiente para envio real.
4. Vazamento de tokens em logs.
5. Envio acidental.
6. Duplicação de lógica OAuth.
7. Divergência entre dashboard e skill.

## Decisões pendentes

1. Confirmar endpoint/payload exato de envio Zoho na documentação oficial antes da implementação.
2. Confirmar redirect URI dev/prod.
3. Decidir se disconnect/revoke entra no MVP ou fica para fase posterior.

## Decisões já fechadas

1. MVP usa rascunho local/payload revisável, não draft remoto.
2. Confirmação de envio será `YES, SEND`.
3. Storage usa namespace próprio `ZOHO_MAIL_*`.
4. Dashboard precisa status OAuth real, não apenas env configurado.
5. Multi-DC é obrigatório via `accounts_server_url` e `api_domain` capturados.
