# PRD — Implantação do Documenso self-hosted em Docker Swarm

**Projeto:** evo-nexus / infraestrutura operacional  
**Feature:** documenso-swarm  
**Owner:** Eduardo / Automação Software  
**Data:** 2026-06-11  
**Fonte:** `runbook_documenso_swarm_sysops.md` anexado no Discord Plus  
**Status:** Draft aprovado para preflight read-only; execução depende de confirmação final  
**Decisões:** `[C]decisions-documenso-swarm.md`

---

## 1. Problem Statement

A Automação Software precisa de um serviço próprio para assinatura digital e gestão de documentos, com controle operacional sobre dados, certificados, integrações e armazenamento. Hoje, a ausência desse serviço self-hosted limita automações internas, aumenta dependência de SaaS externo e dificulta padronizar fluxos de assinatura para contratos, documentos administrativos e integrações futuras.

A implantação do Documenso em Docker Swarm deve entregar um POC operacional seguro, com PostgreSQL externo, MinIO/S3 desde o início, Traefik HTTPS, SMTP Zoho e certificado `.p12` obrigatório para selar PDFs.

---

## 2. Objetivos

| Objetivo | Métrica de sucesso |
|---|---|
| Disponibilizar Documenso self-hosted em ambiente Swarm | Serviço acessível via domínio HTTPS e `/api/health` = 200 |
| Validar fluxo mínimo de assinatura | 1 PDF enviado, assinado e finalizado com sucesso |
| Garantir persistência externa desde o início | Banco em PostgreSQL externo e objetos gravados em MinIO/S3 |
| Garantir capacidade de selar PDFs | `/api/certificate-status` retorna OK ou equivalente válido |
| Preparar base para automações futuras | Token API em cofre e webhook criado/documentado pós-POC |

---

## 3. Não-objetivos

| Fora de escopo | Motivo |
|---|---|
| Alta disponibilidade com múltiplas réplicas | POC inicial deve reduzir complexidade operacional |
| Redis/BullMQ | Jobs locais são suficientes até prova de gargalo |
| Gotenberg | Conversão/renderização avançada não é requisito do POC |
| MCP interno em produção | Só após validação funcional e segurança mínima |
| Migração de documentos históricos | Não há base legada definida para importar |
| Customização visual profunda | Não resolve o problema central da implantação |
| SLA externo formal | Serviço ainda estará em fase de validação interna |

---

## 4. Usuários e stakeholders

| Persona / stakeholder | Necessidade |
|---|---|
| Eduardo / owner | Validar se o Documenso resolve o fluxo de assinatura da Automação Software |
| Operações/SysOps | Implantar, proteger, monitorar e manter o serviço |
| Administrativo/Financeiro | Usar assinatura para documentos internos, contratos e autorizações |
| Signatário externo | Receber link por email e assinar documento sem complexidade técnica |
| Integrações internas futuras | Consumir API/webhooks para automações controladas |

---

## 5. User Stories

### Owner / Administração

- Como owner da Automação Software, quero acessar o Documenso em domínio HTTPS próprio para centralizar fluxos de assinatura em infraestrutura controlada.
- Como administrador, quero criar o primeiro usuário e depois desabilitar signup público para impedir criação indevida de contas.
- Como administrador, quero enviar um PDF para assinatura e receber o documento final assinado para validar o fluxo completo.

### Signatário externo

- Como signatário externo, quero receber um email com link de assinatura para assinar o documento sem instalar certificado cliente.
- Como signatário externo, quero concluir a assinatura com clareza para saber que minha ação foi registrada.

### Operações/SysOps

- Como operador de infraestrutura, quero rodar o Documenso em Docker Swarm com 1 réplica para manter implantação simples e reversível.
- Como operador de infraestrutura, quero usar PostgreSQL e MinIO externos para evitar perda de dados em recriação de containers.
- Como operador de infraestrutura, quero armazenar o certificado `.p12` como secret para não expor credenciais sensíveis.
- Como operador de infraestrutura, quero validar healthcheck, logs e backups antes de liberar uso real.

### Integração futura

- Como integrador interno, quero ter token API e webhook documentados para conectar o Documenso a automações futuras da Automação Software.

---

## 6. Requisitos funcionais

### P0 — Must-have

| ID | Requisito | Critério associado |
|---|---|---|
| RF-01 | Implantar Documenso em Docker Swarm com 1 réplica | CA-01 |
| RF-02 | Expor serviço via Traefik com HTTPS válido | CA-08 |
| RF-03 | Configurar DNS no Cloudflare para o domínio final | CA-08 |
| RF-04 | Usar PostgreSQL externo existente, versão 14+ | CA-03 |
| RF-05 | Usar MinIO/S3 externo desde o primeiro deploy | CA-04 |
| RF-06 | Criar bucket MinIO com policy mínima e CORS restrito | CA-04 |
| RF-07 | Configurar SMTP Zoho obrigatório | CA-05 |
| RF-08 | Criar secret Swarm versionado para o certificado `.p12` | CA-02 |
| RF-09 | Configurar passphrase/path do `.p12` sem expor segredo em git/log/prompt | CA-02 |
| RF-10 | Configurar `NEXTAUTH_SECRET`, encryption keys e URLs de banco | CA-01, CA-03 |
| RF-11 | Permitir criação do primeiro usuário administrativo | CA-06 |
| RF-12 | Desabilitar signup público após bootstrap inicial | CA-07 |
| RF-13 | Permitir upload de PDF | CA-04, CA-06 |
| RF-14 | Permitir envio do documento por email | CA-05 |
| RF-15 | Permitir assinatura sem certificado cliente no navegador | CA-06 |
| RF-16 | Gerar PDF final assinado e baixável | CA-06 |
| RF-17 | Definir backup mínimo de PostgreSQL, MinIO e certificado | CA-10 |
| RF-18 | Aplicar placement constraint para impedir agendamento em nó externo/Hetzner | CA-13 |

### P1 — Should-have

| ID | Requisito | Critério associado |
|---|---|---|
| RF-19 | Configurar healthcheck Docker usando `/api/health` | CA-01 |
| RF-20 | Definir resources entre 512M e 1024M inicialmente | CA-09 |
| RF-21 | Revisar logs após smoke test | CA-09 |
| RF-22 | Gerar token API e armazenar em cofre | CA-11 |
| RF-23 | Criar ou documentar webhook inicial | CA-12 |
| RF-24 | Fixar imagem por tag e, se possível, digest | CA-14 |

### P2 — Future considerations

| ID | Requisito futuro | Observação |
|---|---|---|
| RF-25 | MCP interno controlado | Somente após POC e hardening |
| RF-26 | Webhooks automatizados para fluxos internos | Depende da escolha dos eventos prioritários |
| RF-27 | Templates padrão de documentos | Após validação de uso real |
| RF-28 | Monitoramento e alertas | Pós-POC, se serviço virar operacional |
| RF-29 | Redis/BullMQ | Reavaliar se jobs locais degradarem |
| RF-30 | Gotenberg | Reavaliar se houver necessidade de conversão/renderização |

---

## 7. Requisitos não funcionais

| ID | Requisito |
|---|---|
| RNF-01 | Dados persistentes não podem depender do filesystem efêmero do container. |
| RNF-02 | Documentos devem ser armazenados em MinIO/S3 desde o início. |
| RNF-03 | PostgreSQL deve ser externo e versão 14+. |
| RNF-04 | Secrets não podem ser salvos em git, stack versionada, logs ou prompts de LLM. |
| RNF-05 | Certificado `.p12` e passphrase devem ter backup seguro fora do container. |
| RNF-06 | Serviço deve operar via HTTPS válido. |
| RNF-07 | Signup público deve ficar desabilitado após o primeiro usuário. |
| RNF-08 | Logs devem permitir diagnóstico sem vazar credenciais, tokens, URLs pré-assinadas ou payloads sensíveis. |
| RNF-09 | A implantação deve ser reproduzível via stack Docker Swarm. |
| RNF-10 | O deploy deve ser reversível sem perda de banco, objetos S3 ou certificado. |
| RNF-11 | O POC deve evitar componentes não essenciais para reduzir superfície operacional. |
| RNF-12 | O serviço não deve ser agendado em nó externo sem aprovação explícita. |
| RNF-13 | Integrações por agentes devem passar por backend/MCP interno allowlisted, nunca API token direto no LLM. |

---

## 8. Success Metrics

### Leading indicators

| Métrica | Meta |
|---|---|
| Healthcheck | `/api/health` retorna 200 após deploy |
| Certificado | `/api/certificate-status` retorna OK |
| Upload | 1 PDF enviado com sucesso |
| Persistência S3 | Objeto aparece no bucket MinIO esperado |
| Email | Email Zoho entregue ao signatário |
| Assinatura | Signatário conclui assinatura sem certificado cliente |
| Logs | Sem erro crítico recorrente após smoke test |
| Segurança inicial | Signup desabilitado e secrets não expostos |

### Lagging indicators

| Métrica | Janela sugerida | Meta |
|---|---:|---|
| Adoção interna | 30 dias após POC | Pelo menos 1 fluxo real interno usando Documenso |
| Confiabilidade operacional | 30 dias após POC | Nenhum incidente de perda de documento |
| Reuso em automações | 60 dias após POC | Pelo menos 1 webhook ou integração interna validada |
| Redução de dependência externa | 90 dias após POC | Documentos recorrentes migráveis identificados ou iniciados |

---

## 9. Critérios de aceite

### CA-01 — Serviço saudável

**Given** que a stack Documenso foi implantada no Docker Swarm  
**When** o endpoint `/api/health` for acessado pelo domínio HTTPS  
**Then** a resposta deve ser HTTP 200.

### CA-02 — Certificado carregado

**Given** que o secret do certificado `.p12` foi criado  
**And** a passphrase correta foi configurada  
**When** `/api/certificate-status` for acessado  
**Then** o status deve retornar OK ou equivalente válido.

### CA-03 — PostgreSQL externo conectado

**Given** que existe PostgreSQL externo versão 14+  
**When** o Documenso iniciar  
**Then** a aplicação deve conectar e executar sem erro crítico de banco/migração.

### CA-04 — MinIO/S3 funcional

**Given** que o bucket MinIO foi criado com policy mínima e CORS  
**When** um PDF for enviado  
**Then** o objeto correspondente deve aparecer no bucket esperado.

### CA-05 — SMTP Zoho funcional

**Given** que as variáveis SMTP Zoho foram configuradas  
**When** um documento for enviado para assinatura  
**Then** o destinatário deve receber o email transacional.

### CA-06 — Assinatura ponta a ponta

**Given** que existe usuário administrativo ativo  
**And** um PDF foi enviado para assinatura  
**When** o signatário abrir o link e assinar  
**Then** o Documenso deve gerar PDF final assinado e baixável.

### CA-07 — Signup público desabilitado

**Given** que o primeiro usuário administrativo já foi criado  
**When** alguém tentar acessar cadastro público  
**Then** o cadastro deve estar bloqueado/desabilitado.

### CA-08 — DNS e HTTPS

**Given** que Cloudflare DNS/tunnel e Traefik foram configurados  
**When** o domínio for acessado  
**Then** o Documenso deve responder via HTTPS válido.

### CA-09 — Logs e recursos

**Given** que upload, email e assinatura foram testados  
**When** os logs da stack forem revisados  
**Then** não deve haver erro crítico recorrente de banco, S3, SMTP, certificado ou auth.

### CA-10 — Backup mínimo

**Given** que o serviço foi validado tecnicamente  
**When** ele for considerado pronto para uso real  
**Then** deve existir procedimento de backup para PostgreSQL, MinIO, certificado `.p12` e passphrase.

### CA-11 — Token API protegido

**Given** que um token API foi gerado  
**When** ele for armazenado  
**Then** deve estar salvo em cofre aprovado, não em arquivo versionado, prompt ou log.

### CA-12 — Webhook inicial

**Given** que o POC foi validado  
**When** for definida a primeira integração interna  
**Then** o webhook deve estar criado ou documentado com evento, destino, segredo e responsável.

### CA-13 — Placement seguro

**Given** que o Swarm possui nós locais e nó externo  
**When** o serviço Documenso for implantado  
**Then** a task deve rodar somente em nó local aprovado, excluindo Hetzner/nós externos.

### CA-14 — Imagem pinada

**Given** que a imagem Documenso foi escolhida  
**When** a stack for renderizada  
**Then** ela não deve usar `latest` e deve registrar tag explícita, preferencialmente também digest.

---

## 10. Riscos

| Risco | Impacto | Mitigação |
|---|---|---|
| Certificado `.p12` inválido, expirado ou com passphrase incorreta | PDFs não serão selados | Validar CA-02 antes de liberar uso |
| Vazamento de passphrase/secrets | Comprometimento de assinatura e infraestrutura | Usar Swarm secrets/cofre; não imprimir env completo |
| MinIO/CORS incorreto | Upload/download falha | Validar CA-04 com objeto real |
| SMTP Zoho bloqueado | Convites não chegam | Testar envio real antes do uso |
| Signup público aberto | Criação indevida de contas | Validar CA-07 após bootstrap |
| PostgreSQL abaixo de 14 | Runtime/migration pode falhar | Confirmar versão antes do deploy |
| Backup incompleto do `.p12` | Perda de continuidade operacional | Incluir certificado e passphrase no backup seguro |
| Recursos insuficientes | Serviço instável | Começar com limite até 1024M e observar logs |
| Sem Redis/BullMQ | Jobs locais podem degradar em volume | Aceito no POC; reavaliar pós-uso |
| Topologia Traefik divergente | Serviço saudável internamente, domínio quebrado externamente | Decidir entrypoint antes da execução |
| Agendamento em nó externo | Perda de conectividade LAN e exposição de secrets | Placement constraint obrigatória |
| Rollback pós-migração | Imagem volta, mas banco/schema fica incompatível | Backup/restore de Postgres e MinIO antes do deploy |

---

## 11. Pendências e perguntas abertas

| Item | Status | Dono sugerido | Observação |
|---|---|---|---|
| [BLOCKER] Definir domínio final | Aberto | Eduardo/SysOps | Necessário para Cloudflare/Traefik |
| [BLOCKER] Definir topologia de entrada | Aberto | SysOps | Traefik LXC 211 existente vs Traefik Swarm |
| [BLOCKER] Confirmar PostgreSQL externo | Aberto | SysOps | Host, porta, database, usuário e versão 14+ |
| [BLOCKER] Confirmar bucket MinIO | Aberto | SysOps | Nome, endpoint, credenciais, CORS e policy |
| [BLOCKER] Obter/gerar certificado `.p12` | Aberto | Eduardo/SysOps | Obrigatório para selar PDFs |
| [DONE] Confirmar SMTP Zoho | Concluído técnico; smoke pendente | Eduardo/SysOps | Username/remetente trocado para `gocontrol@automacaosoftware.com.br`; app password validada e secret Swarm criado; envio real depende do deploy |
| [BLOCKER] Definir backup seguro do certificado | Aberto | SysOps | Não depender apenas do Swarm secret |
| [BLOCKER] Definir placement no Swarm | Aberto | SysOps | Excluir Hetzner/nó externo |
| [ASSUMPTION — VALIDATE] Jobs locais são suficientes no POC | Aberto | Produto/SysOps | Sem Redis/BullMQ inicialmente |
| [ASSUMPTION — VALIDATE] Gotenberg não é necessário no POC | Aberto | Produto/SysOps | Reavaliar conforme tipo de documento |
| Definir evento de webhook prioritário | Aberto | Eduardo/Nova | Ex.: documento concluído |
| Definir se acesso será interno ou público restrito | Aberto | Eduardo/SysOps | Afeta hardening e exposição |

---

## 12. Considerações de faseamento

### Fase 0 — Pré-deploy

- Confirmar domínio.
- Confirmar topologia de entrada.
- Confirmar PostgreSQL 14+.
- Criar bucket MinIO com policy/CORS.
- Obter/gerar certificado `.p12` e passphrase.
- Confirmar SMTP Zoho tecnicamente concluído; envio real será validado no smoke pós-deploy.
- Criar secret versionado do `.p12`.
- Definir backup mínimo.
- Definir placement constraint.

### Fase 1 — POC técnico

- Subir stack com 1 réplica.
- Validar DNS/HTTPS.
- Validar `/api/health`.
- Validar `/api/certificate-status`.
- Criar primeiro admin.
- Desabilitar signup público.
- Testar upload, email, assinatura e PDF final.
- Revisar logs.

### Fase 2 — Operação controlada

- Gerar token API e salvar em cofre.
- Criar/documentar webhook inicial.
- Rodar primeiro fluxo real interno.
- Monitorar consumo de recursos e erros.
- Decidir se Redis/BullMQ, Gotenberg ou monitoramento avançado entram no roadmap.

---

## 13. Decisões necessárias

**[APPROVAL REQUIRED]** Aprovar este PRD antes da execução operacional.

Decisões que precisam ser confirmadas:

1. Domínio final do Documenso.
2. Exposição inicial: interno, público restrito ou público aberto.
3. Topologia de borda: Traefik LXC 211 existente ou Traefik no Swarm.
4. PostgreSQL externo a ser usado.
5. Bucket MinIO dedicado.
6. Certificado `.p12` oficial ou self-signed para POC.
7. Política de backup do certificado e passphrase.
8. Placement no Swarm, excluindo nó externo.
9. Evento de webhook prioritário pós-POC.
10. Critério final para considerar o POC aprovado para uso real.
