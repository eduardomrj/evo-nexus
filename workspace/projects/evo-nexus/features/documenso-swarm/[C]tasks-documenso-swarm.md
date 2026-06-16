# Tasks — Implantação Documenso self-hosted em Docker Swarm

**Projeto:** evo-nexus / infraestrutura operacional  
**Feature:** documenso-swarm  
**Data:** 2026-06-11  
**Status:** Draft backlog

---

## Epic 1 — Decisões e preflight

### TASK-001 — Definir domínio final

- **Prioridade:** P0
- **Dono:** Eduardo/SysOps
- **Status:** concluída
- **Decisão:** `signature.myworkhome.com.br`
- **Descrição:** escolher subdomínio público do Documenso.
- **Aceite:** domínio registrado no plano e usado como URL canônica.
- **Bloqueia:** Traefik, Cloudflare, CORS, SMTP links.

### TASK-002 — Aprovar topologia de entrada

- **Prioridade:** P0
- **Dono:** SysOps/Eduardo
- **Status:** concluída
- **Decisão:** Cloudflare Tunnel existente → IP do manager Swarm:80 → Traefik Swarm existente → Documenso.
- **Descrição:** decidir entre Traefik LXC 211 existente ou Traefik Swarm.
- **Aceite:** decisão registrada e diagrama atualizado.
- **Bloqueia:** publicação externa.

### TASK-003 — Definir placement Swarm home-only

- **Prioridade:** P0
- **Dono:** SysOps
- **Status:** decidida; pendente validação read-only
- **Decisão:** apenas workers da homelab; excluir manager e Hetzner/nó externo.
- **Descrição:** definir labels/constraints para impedir schedule em nó externo/Hetzner.
- **Aceite:** constraint documentada e validável por `docker service ps`.
- **Bloqueia:** deploy de stack.

### TASK-004 — Escolher versão/tag Documenso

- **Prioridade:** P0
- **Dono:** SysOps
- **Status:** pendente antes do deploy
- **Decisão:** SysOps escolhe última release estável pinada no momento do deploy; proibido `latest`.
- **Descrição:** consultar releases oficiais e escolher tag/digest; proibido `latest`.
- **Aceite:** imagem e digest registrados no plano.
- **Bloqueia:** stack final.

### TASK-005 — Validar requisitos oficiais da versão escolhida

- **Prioridade:** P0
- **Dono:** SysOps
- **Status:** pendente antes do deploy
- **Decisão:** POC simples, sem Redis/BullMQ e sem Gotenberg.
- **Descrição:** confirmar se opera sem Redis/BullMQ e sem Gotenberg para o fluxo POC.
- **Aceite:** decisão documentada com referência.
- **Bloqueia:** deploy funcional.

---

## Epic 2 — Dependências persistentes

### TASK-006 — Criar banco PostgreSQL dedicado

- **Prioridade:** P0
- **Dono:** SysOps
- **Descrição:** criar database e role dedicados no PostgreSQL 14+ existente.
- **Aceite:** conexão validada a partir do nó Swarm aprovado; role sem superuser.

### TASK-007 — Preparar backup/restore PostgreSQL pré-deploy

- **Prioridade:** P0
- **Dono:** SysOps
- **Descrição:** criar dump antes da migration e testar restore quando possível.
- **Aceite:** dump localizado e procedimento de restore documentado.

### TASK-008 — Criar bucket MinIO/S3 dedicado

- **Prioridade:** P0
- **Dono:** SysOps
- **Descrição:** escolher instância MinIO canônica, criar bucket e credenciais exclusivas.
- **Aceite:** upload/download de teste OK.

### TASK-009 — Aplicar policy mínima e CORS restrito no MinIO

- **Prioridade:** P0
- **Dono:** SysOps
- **Descrição:** bucket privado, sem public read/list amplo, CORS apenas no domínio Documenso.
- **Aceite:** policy validada; sem wildcard público.

### TASK-010 — Definir backup/snapshot do bucket

- **Prioridade:** P0
- **Dono:** SysOps
- **Descrição:** garantir que objetos MinIO podem ser restaurados junto do banco.
- **Aceite:** política e procedimento registrados.

---

## Epic 3 — Secrets, certificado e SMTP

### TASK-011 — Obter ou gerar certificado `.p12`

- **Prioridade:** P0
- **Dono:** Eduardo/SysOps
- **Descrição:** definir se POC usa certificado oficial ou certificado de teste.
- **Aceite:** `.p12`, passphrase, validade e owner de renovação definidos.

### TASK-012 — Criar secrets Swarm versionados

- **Prioridade:** P0
- **Dono:** SysOps
- **Descrição:** criar secrets para `.p12`, passphrase e demais segredos suportados.
- **Aceite:** secrets versionados e não impressos em logs.

### TASK-013 — Validar leitura do `.p12`

- **Prioridade:** P0
- **Dono:** SysOps
- **Descrição:** validar arquivo, passphrase e formato antes do deploy.
- **Aceite:** teste de leitura OK; expiração registrada.

### TASK-014 — Configurar SMTP Zoho

- **Prioridade:** P0
- **Dono:** SysOps/Eduardo
- **Status:** concluída parcialmente; envio real depende do deploy/smoke
- **Decisão:** usar `gocontrol@automacaosoftware.com.br` como username/remetente após autorização de Eduardo em 2026-06-12.
- **Evidência:** app password do item Vaultwarden `email-evonexus` autentica em `smtp.zoho.com:465`; secret Swarm `documenso_smtp_password_v1` criado sem expor valor.
- **Descrição:** definir host, porta, TLS, remetente e app password.
- **Aceite:** envio real de teste OK.

### TASK-015 — Validar SPF/DKIM/DMARC

- **Prioridade:** P1
- **Dono:** SysOps
- **Descrição:** confirmar entregabilidade do domínio remetente.
- **Aceite:** email de teste entregue sem rejeição crítica.

---

## Epic 4 — Stack Docker Swarm

### TASK-016 — Criar stack draft sem segredos inline

- **Prioridade:** P0
- **Dono:** SysOps
- **Descrição:** montar stack com imagem pinada, 1 réplica, placement, networks, resources e healthcheck.
- **Aceite:** stack revisada sem `latest` e sem segredo literal.

### TASK-017 — Configurar variáveis de aplicação

- **Prioridade:** P0
- **Dono:** SysOps
- **Descrição:** configurar URL pública, DB, S3, SMTP, auth secrets e certificado.
- **Aceite:** render seguro e coerente com domínio final.

### TASK-018 — Deploy interno controlado

- **Prioridade:** P0
- **Dono:** SysOps
- **Descrição:** subir stack sem uso real e validar placement, logs e health.
- **Aceite:** service `1/1`, task no nó correto, `/api/health` OK.

### TASK-019 — Validar certificado no app

- **Prioridade:** P0
- **Dono:** SysOps
- **Descrição:** testar endpoint/status de certificado.
- **Aceite:** `/api/certificate-status` OK ou equivalente.

---

## Epic 5 — Publicação e smoke

### TASK-020 — Configurar rota Traefik/Cloudflare

- **Prioridade:** P0
- **Dono:** SysOps
- **Descrição:** criar rota via topologia aprovada.
- **Aceite:** HTTPS público funcional e sem porta direta exposta.

### TASK-021 — Bootstrap admin e bloquear signup

- **Prioridade:** P0
- **Dono:** SysOps/Eduardo
- **Descrição:** criar primeiro admin e desabilitar signup público.
- **Aceite:** tentativa de signup público bloqueada.

### TASK-022 — Executar smoke de upload e MinIO

- **Prioridade:** P0
- **Dono:** SysOps
- **Descrição:** subir PDF de teste e confirmar objeto no bucket.
- **Aceite:** objeto gravado e logs sem erro crítico.

### TASK-023 — Executar smoke SMTP

- **Prioridade:** P0
- **Dono:** SysOps
- **Descrição:** enviar documento de teste para email controlado.
- **Aceite:** email recebido com link correto.

### TASK-024 — Executar smoke assinatura ponta a ponta

- **Prioridade:** P0
- **Dono:** SysOps/Eduardo
- **Descrição:** assinar documento como destinatário externo e baixar PDF final.
- **Aceite:** PDF final gerado, baixável e logs limpos.

---

## Epic 6 — Operação controlada e integração futura

### TASK-025 — Documentar backup operacional

- **Prioridade:** P0
- **Dono:** SysOps
- **Descrição:** documentar backup de Postgres, MinIO, `.p12`, passphrase e stack.
- **Aceite:** runbook de backup/restore salvo.

### TASK-026 — Criar alertas mínimos

- **Prioridade:** P1
- **Dono:** SysOps
- **Descrição:** monitorar health, certificado, restarts, SMTP, S3 e backup.
- **Aceite:** checks definidos e destino de alerta aprovado.

### TASK-027 — Gerar token API e guardar em cofre

- **Prioridade:** P1
- **Dono:** SysOps/Eduardo
- **Descrição:** gerar token apenas após POC, guardar no Vaultwarden/cofre.
- **Aceite:** token não aparece em prompt/log/arquivo versionado.

### TASK-028 — Documentar webhook inicial

- **Prioridade:** P1
- **Dono:** SysOps/Produto
- **Descrição:** definir evento, destino, segredo e idempotência.
- **Aceite:** webhook criado ou documentado com segredo protegido.

### TASK-029 — Avaliar MCP interno controlado

- **Prioridade:** P2
- **Dono:** SysOps/Apex/Vault
- **Descrição:** desenhar backend/MCP allowlisted para automações com Documenso.
- **Aceite:** LLM sem acesso direto a API token; operações limitadas.

---

## Sequência mínima recomendada

1. TASK-001 a TASK-005
2. TASK-006 a TASK-010
3. TASK-011 a TASK-015
4. TASK-016 a TASK-019
5. TASK-020 a TASK-024
6. TASK-025 a TASK-029

---

## Critérios de pronto para executar

- Todos os P0 de decisão fechados.
- Rollback mapeado.
- Backup pré-deploy definido.
- Segredos fora de git/log/prompt.
- Placement home-only definido.
- Janela de menor tráfego aprovada.
