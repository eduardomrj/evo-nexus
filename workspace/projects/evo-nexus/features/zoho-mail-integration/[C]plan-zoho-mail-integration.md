# [C] Plano — Zoho Mail Integration

## Status

**Atualizado após validação Apex: APROVADO COM AJUSTES.**  
Documento preparado para implementação futura. Nada foi implementado ainda.

## Decisões fechadas para o próximo handoff

- Storage: namespace próprio `ZOHO_MAIL_*`, sem reaproveitar Bling.
- Multi-DC: usar `accounts_server_url` e `api_domain` capturados, sem domínio hardcoded.
- Rascunho MVP: local/payload revisável, não draft remoto na Zoho.
- Envio: confirmação literal obrigatória `YES, SEND`.
- Dashboard: status real `not_configured`, `needs_auth`, `connected`, `needs_reauth`, `error_sanitized`.
- Logs/erros: sanitização obrigatória antes de stderr/log/UI; não copiar cegamente o tratamento de erro do `int-bling`.

## Objetivo

Implementar integração Zoho Mail via API/OAuth no EvoNexus, começando como `custom-int-zoho-mail`, com status em `/integrations` e envio somente com confirmação explícita.

## Guardrails

- Usar Zoho Mail API/OAuth2.
- Não usar Gmail, SMTP, IMAP ou POP3.
- Reaproveitar padrão OAuth do `int-bling`, exceto tratamento de erro que deve ser mais seguro.
- Reaproveitar segurança operacional de `gog-email-*`.
- Não hardcodar data center Zoho.
- Não logar tokens/secrets.
- Envio de e-mail só com confirmação literal `YES, SEND`.
- Não criar draft remoto na Zoho no MVP.

## Etapa 1 — Confirmar docs oficiais Zoho antes do build

**Agentes:** Scroll + Scout  
**Objetivo:** confirmar documentação oficial e padrões internos antes de codar.

Verificar:

- authorization URL e token URL por região/data center;
- retorno de `accounts_server_url` e/ou `api_domain`;
- scopes finais;
- endpoint/payload oficial de envio;
- endpoints de accounts, folders, messages/view e search;
- pontos reutilizáveis do `int-bling`;
- pontos de erro do `int-bling` que não devem ser copiados.

**Aceite:** endpoints/payloads oficiais confirmados e anotados no handoff para Bolt.

## Etapa 2 — Implementar OAuth/client Zoho

**Agente:** Bolt  
**Objetivo:** criar camada reutilizável de autenticação e API.

Implementar:

- geração de authorization URL;
- callback com validação de `state`;
- troca de `code` por tokens;
- persistência atômica em namespace `ZOHO_MAIL_*`;
- armazenamento de `access_token`, `refresh_token`, expiry, `accounts_server_url`, `api_domain`;
- refresh automático;
- retry único em `401`;
- redaction/sanitização centralizada de erros e logs.

**Aceite:** OAuth conecta, refresh funciona e tokens não aparecem em logs/UI/stderr.

## Etapa 3 — Implementar operações Mail API

**Agente:** Bolt  
**Objetivo:** cobrir MVP funcional.

Métodos:

- listar contas;
- listar pastas;
- listar mensagens da Inbox;
- buscar mensagens;
- preparar rascunho local/payload revisável;
- enviar e-mail apenas após `YES, SEND`.

**Aceite:** contas, pastas, Inbox e busca funcionam; envio de teste só ocorre com confirmação literal.

## Etapa 4 — Criar skill `custom-int-zoho-mail`

**Agente:** Bolt  
**Objetivo:** expor uso operacional seguro.

Capacidades:

- status;
- conectar/reautenticar;
- listar contas;
- listar pastas;
- triagem Inbox read-only;
- busca;
- preparar rascunho local;
- enviar com `YES, SEND`.

**Aceite:** skill nunca envia automaticamente.

## Etapa 5 — Dashboard `/integrations`

**Agentes:** Bolt/Canvas  
**Objetivo:** expor status OAuth real.

Status obrigatórios:

- `not_configured`;
- `needs_auth`;
- `connected`;
- `needs_reauth`;
- `error_sanitized`.

Dashboard deve mostrar:

- conectar/reautenticar;
- conta conectada;
- última validação;
- erro sanitizado.

**Aceite:** dashboard não confunde env configurado com conta conectada.

## Etapa 6 — Segurança, revisão e verificação

**Agentes:** Vault + Lens + Oath  
**Objetivo:** validar antes de declarar pronto.

Verificar:

- OAuth válido;
- `state` inválido rejeitado;
- refresh;
- retry `401`;
- listagem de contas/pastas/Inbox;
- busca;
- envio confirmado com `YES, SEND`;
- ausência de tokens/secrets em logs;
- erros sanitizados;
- build/testes aplicáveis.

## Arquivos prováveis

- `.claude/skills/custom-int-zoho-mail/SKILL.md`
- `.claude/skills/custom-int-zoho-mail/scripts/zoho_mail_auth.py`
- `.claude/skills/custom-int-zoho-mail/scripts/zoho_mail_client.py`
- `.claude/skills/custom-int-zoho-mail/scripts/zoho_mail_cli.py`
- `dashboard/backend/routes/integrations.py`
- `dashboard/frontend/src/lib/integrationMeta.ts`
- `Makefile` para possível `make zoho-mail-auth`

## Riscos

1. Endpoint de envio Zoho diferente do esperado.
2. Code OAuth expirar em 2 minutos.
3. Data center incorreto.
4. Token leak.
5. Envio acidental.
6. Duplicação de OAuth.
7. Dashboard quebrar por integração específica demais.

## Pendências antes de implementar

1. Confirmar endpoint/payload oficial de envio Zoho.
2. Confirmar redirect URI dev/prod.
3. Decidir se disconnect/revoke entra no MVP.

## Próximo passo futuro

Quando Eduardo pedir implementação: chamar Bolt com este plano + PRD atualizado e exigir verificação final com Vault/Lens/Oath.
