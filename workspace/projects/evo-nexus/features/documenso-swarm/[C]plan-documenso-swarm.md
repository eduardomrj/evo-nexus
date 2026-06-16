# Plano — Implantação do Documenso self-hosted em Docker Swarm

**Projeto:** evo-nexus / infraestrutura operacional  
**Feature:** documenso-swarm  
**Fonte:** `runbook_documenso_swarm_sysops.md` + revisão Nova/Apex/Vault/Raven  
**Data:** 2026-06-11  
**Status:** Draft operacional — não executar sem aprovar blockers

---

## 0. Veredito operacional

**Status recomendado:** `PREFLIGHT READ-ONLY APROVADO; EXECUÇÃO AINDA BLOQUEADA ATÉ CONFIRMAÇÃO FINAL`.

O runbook é bom como base e as decisões principais foram coletadas com Eduardo. A topologia escolhida para o POC foi explicitamente ajustada para **Traefik dentro do Swarm**, usando o Cloudflare Tunnel existente apontando para o IP do manager Swarm na porta 80.

Ainda não executar mudanças reais até concluir o preflight read-only e apresentar rollback/ações para aprovação final.

Decisões críticas já aprovadas:

1. **Domínio:** `signature.myworkhome.com.br`.
2. **Exposição:** pública controlada.
3. **Topologia:** Cloudflare Tunnel existente → IP do manager Swarm:80 → Traefik Swarm existente → Documenso.
4. **Placement:** apenas workers da homelab; excluir manager e worker externo/Hetzner.
5. **Persistência:** PostgreSQL existente com DB `documenso`/user `documenso_app`; MinIO principal com bucket `documenso`.
6. **Segurança:** certificado `.p12` self-signed de teste no POC; secrets em Vaultwarden + Docker Swarm secrets; signup só durante bootstrap.
7. **Próximo passo autorizado:** atualizar artefatos e executar preflight read-only, sem criar DB/bucket/secrets e sem publicar rota.

---

## 1. Arquitetura alvo aprovada para POC

```text
Cloudflare DNS/Tunnel existente
  → http://IP_MANAGER_SWARM:80
  → Traefik Swarm existente
  → Documenso service, 1 réplica, apenas workers homelab
  → PostgreSQL existente: database documenso, user documenso_app
  → MinIO principal: bucket documenso
  → SMTP Zoho: gocontrol@automacaosoftware.com.br
  → Docker secret: certificado .p12 self-signed de teste
```

### Decisões

| Decisão | Valor aprovado | Motivo |
|---|---|---|
| 1 réplica | Sim | Evita concorrência com jobs locais sem Redis/BullMQ |
| Redis/BullMQ | Não no POC | Reduz complexidade; reavaliar após uso real |
| Gotenberg | Não no POC | Fluxo esperado usa PDF já pronto |
| S3/MinIO | MinIO principal, bucket `documenso` | Evita storage efêmero/local no Swarm |
| PostgreSQL | Existente, DB `documenso`, user `documenso_app` | Isola blast radius e facilita restore |
| Traefik | Traefik Swarm existente | Decisão explícita do Eduardo para o POC |
| Tunnel | Cloudflare Tunnel existente → manager Swarm:80 | Simples para POC, exige backup da config antes de alteração |
| Placement | Apenas workers da homelab | Evita secrets no manager e no worker externo/Hetzner |
| Imagem | Release estável pinada no deploy | Rollback e reprodução de incidente exigem tag/digest fixos |
| Secrets | Vaultwarden + Docker Swarm secrets | Proteção de DB, SMTP, S3, API e certificado |
| Signup | Só durante bootstrap | Reduz risco em domínio público |
| Smoke externo | `eduardo@sysautomacao.com.br` | Valida entrega/link/assinatura fora do domínio principal |

---

## 2. Blockers de decisão antes de executar

A etapa atual autorizada é apenas preflight read-only. Antes de qualquer mudança real, ainda precisam ser confirmados com evidência:

- [x] Domínio final definido: `signature.myworkhome.com.br`.
- [x] Topologia aprovada: Cloudflare Tunnel existente → manager Swarm:80 → Traefik Swarm existente.
- [x] Placement desejado: apenas workers da homelab.
- [x] PostgreSQL/banco/usuário definidos: `documenso` / `documenso_app`.
- [x] MinIO/bucket definido: MinIO principal / bucket `documenso`.
- [x] SMTP/remetente definido: Zoho / `gocontrol@automacaosoftware.com.br` após troca autorizada em 2026-06-12.
- [x] Certificado POC definido: `.p12` self-signed de teste gerado por SysOps.
- [x] Backup mínimo aprovado antes de qualquer deploy.
- [x] Signup: abrir só no bootstrap e fechar imediatamente.
- [ ] Preflight confirma IP atual do manager Swarm.
- [ ] Preflight confirma Traefik Swarm existente e porta/entrypoint 80.
- [ ] Preflight confirma labels/constraints disponíveis para workers homelab.
- [ ] Preflight confirma Postgres alvo e versão 14+.
- [ ] Preflight confirma MinIO principal e endpoint correto.
- [ ] Preflight confirma config atual do Cloudflare Tunnel para backup/rollback.
- [ ] Tag/digest exato do Documenso escolhido antes do deploy; proibido `latest`.
- [ ] Confirmação final humana antes de criar DB, bucket, secrets, stack ou rota.

---

## 3. Plano em fases

### Fase 0 — Discovery/preflight

**Objetivo:** eliminar ambiguidades antes de tocar produção.

1. Confirmar topologia de entrada.
2. Confirmar domínio público e URL canônica do Documenso.
3. Inventariar Swarm: nós, labels, manager, workers locais, nó externo.
4. Definir placement constraint.
5. Confirmar PostgreSQL: host, porta, versão, DB/user dedicados.
6. Confirmar MinIO: instância canônica, endpoint interno/público, bucket, CORS, policy.
7. Confirmar SMTP Zoho: host, porta, TLS, remetente, SPF/DKIM/DMARC.
8. Confirmar certificado `.p12`: validade, passphrase, formato, owner de renovação.
9. Confirmar tag/digest Documenso e requirements oficiais da versão.
10. Confirmar se `/api/health` e `/api/certificate-status` existem na tag escolhida.

**Saída:** checklist de preflight aprovado.

---

### Fase 1 — Preparação de dependências

**Objetivo:** preparar estado externo com rollback mapeado.

1. Criar database dedicado no PostgreSQL.
2. Criar role dedicada sem superuser.
3. Criar backup/dump inicial do banco antes de migrations.
4. Criar bucket dedicado no MinIO/S3.
5. Aplicar policy mínima: sem public read, sem list amplo, sem wildcard desnecessário.
6. Aplicar CORS restrito ao domínio final do Documenso.
7. Criar credenciais S3 exclusivas para o Documenso.
8. Criar ou validar app password SMTP Zoho.
9. Criar secrets no Swarm com nomes versionados:
   - `documenso_cert_p12_v1`
   - `documenso_cert_p12_pass_v1` se suportado como secret/file
   - secrets de DB/S3/SMTP/auth, se o stack suportar `_FILE` ou alternativa segura
10. Registrar onde os secrets ficam guardados no cofre.

**Rollback da fase:** remover DB/bucket/secrets se nada foi publicado e preservar evidências/logs.

---

### Fase 2 — Stack draft e validação offline

**Objetivo:** preparar stack sem publicar ao usuário final.

1. Montar stack Docker Swarm com:
   - imagem Documenso pinada;
   - 1 réplica;
   - placement constraint home-only;
   - resource limits 512M–1024M;
   - healthcheck `/api/health`;
   - networks internas necessárias;
   - sem `latest`;
   - sem porta pública direta.
2. Definir `NEXTAUTH_URL`/URL pública final coerente com Traefik/Cloudflare.
3. Configurar DB URLs, SMTP, S3 e certificado sem expor segredo no arquivo versionado.
4. Validar render do stack sem secrets impressos.
5. Validar que a task não pode agendar em nó externo.

**Rollback da fase:** não aplicar stack; descartar draft ou manter como artefato revisável.

---

### Fase 3 — Deploy interno controlado

**Objetivo:** subir app e validar dependências sem uso real.

1. Fazer backup imediatamente antes do primeiro deploy.
2. Aplicar stack.
3. Verificar `docker service ps` e task placement.
4. Verificar logs de boot e migrations.
5. Validar `/api/health` internamente.
6. Validar `/api/certificate-status` internamente.
7. Validar conexão PostgreSQL e ausência de erro crítico.
8. Validar upload S3/MinIO em fluxo controlado.
9. Validar SMTP com email de teste.

**Rollback antes de publicar:** remover stack ou zerar réplica; se migrations rodaram e houve falha crítica, restaurar banco conforme dump pré-deploy.

---

### Fase 4 — Publicação via Traefik/Cloudflare

**Objetivo:** expor com HTTPS pela borda aprovada.

1. Se v1 seguir recomendação, criar rota no Traefik LXC 211 apontando para o endpoint interno do Swarm.
2. Garantir Cloudflare/Tunnel apontando para o Traefik correto.
3. Validar HTTPS público.
4. Validar headers `X-Forwarded-*`, host e scheme.
5. Confirmar que não há porta direta pública.
6. Criar primeiro admin.
7. Desabilitar signup público.
8. Revalidar acesso público após desabilitar signup.

**Rollback da fase:** remover rota Traefik/Cloudflare; manter app interno parado ou acessível apenas para diagnóstico.

---

### Fase 5 — Smoke test funcional

**Objetivo:** provar valor ponta a ponta.

1. Login/admin.
2. Upload de PDF.
3. Confirmar objeto no bucket MinIO.
4. Enviar documento para email de teste via Zoho.
5. Abrir link como signatário externo.
6. Assinar sem certificado cliente.
7. Baixar PDF final.
8. Validar certificado/status do PDF final conforme suporte do Documenso.
9. Revisar logs da app, Traefik, cloudflared, Postgres, MinIO e SMTP.
10. Confirmar que signup continua desabilitado.

**Critério de aprovação:** todos os critérios CA-01 a CA-10 do PRD passam com evidência.

---

### Fase 6 — Pós-POC / operação controlada

1. Registrar versão, stack, domínio, banco, bucket e secrets criados.
2. Criar rotina de backup ou registrar integração com backup existente.
3. Testar restore em ambiente isolado quando possível.
4. Gerar token API e guardar em cofre.
5. Criar/documentar webhook inicial com segredo.
6. Definir alertas mínimos:
   - `/api/health` != 200;
   - `/api/certificate-status` != OK;
   - container reiniciando;
   - SMTP auth failure;
   - S3 access denied;
   - erro de backup;
   - certificado próximo do vencimento.
7. Rodar primeiro fluxo real interno.
8. Reavaliar Redis/BullMQ, Gotenberg, monitoramento avançado e MCP interno.

---

## 4. Segurança e hardening mínimo

### P0

- Segredos nunca chegam ao LLM.
- API Documenso futura deve passar por backend/MCP interno allowlisted.
- Signup público aberto apenas durante bootstrap controlado.
- `.p12` como Docker secret versionado.
- Passphrase fora de git/log/prompt.
- Bucket privado, sem public read/list amplo.
- CORS restrito ao domínio Documenso.
- Webhook com segredo obrigatório, validação segura, idempotência e rate limit.
- Traefik/Cloudflare com HTTPS, headers e rate limit básico.
- Placement home-only para não enviar secrets ao nó externo.

### P1

- Usuário Postgres mínimo, sem superuser.
- Backup criptografado e restore testado.
- Logs redigidos.
- Imagem pinada e scan de vulnerabilidades.
- Sem container privileged.
- Resource limits e restart policy.

---

## 5. Rollback detalhado

### Cenário A — Falha antes de migrations

1. Não publicar rota pública.
2. Remover stack ou zerar réplica.
3. Preservar logs.
4. Corrigir config e repetir deploy.

### Cenário B — Falha após migrations

1. Remover/desativar rota pública imediatamente.
2. Parar Documenso.
3. Decidir:
   - rollback de imagem se schema compatível;
   - restore do banco pré-deploy se schema incompatível.
4. Avaliar bucket MinIO: objetos órfãos ou inconsistentes.
5. Restaurar bucket/snapshot se necessário.
6. Validar consistência DB ↔ storage.

### Cenário C — Falha de certificado

1. Tirar fluxo de assinatura do ar.
2. Validar `.p12` e passphrase fora do app.
3. Criar secret versionado novo.
4. Atualizar serviço para novo secret.
5. Validar `/api/certificate-status`.

### Cenário D — Falha SMTP

1. Não enviar documentos reais.
2. Corrigir Zoho/SPF/DKIM/DMARC/porta TLS.
3. Reenviar eventos apenas se o Documenso suportar retry seguro.

### Cenário E — Domínio/URL errada em emails

1. Remover rota pública.
2. Pausar envio de novos documentos.
3. Corrigir `NEXTAUTH_URL`/URL pública.
4. Invalidar/reemitir convites de teste.
5. Confirmar links novos antes do uso real.

---

## 6. Critérios de não prosseguir

- Topologia Traefik/Cloudflare indefinida.
- Rota pública não testada com endpoint interno.
- Sem placement constraint excluindo nó externo.
- Imagem sem tag/digest fixo.
- Sem backup Postgres pré-deploy.
- Sem estratégia para backup/snapshot do bucket.
- Sem confirmação de suporte sem Redis/Gotenberg.
- `.p12` e passphrase não validados.
- SMTP Zoho sem envio real validado após deploy; credencial técnica já validada para `gocontrol@automacaosoftware.com.br`.
- Healthcheck limitado a HTTP 200 sem smoke funcional.
- Sem plano explícito para rollback pós-migração.
- Sem janela de manutenção aceita.

---

## 7. Handoff para execução

**Owner da execução:** SysOps  
**Revisões já feitas:** Nova/Product, Apex/Architecture, Vault/Security, Raven/Critic  
**Próximo passo:** Eduardo aprovar/decidir blockers principais.

Decisões que preciso do Eduardo antes de executar:

1. Domínio desejado para o Documenso.
2. Se a exposição inicial deve ser pública, pública restrita ou interna.
3. Aprovação para seguir com Traefik LXC 211 como borda v1.
4. Se usaremos certificado `.p12` oficial agora ou certificado de teste no POC.
5. Confirmação de que posso preparar DB/bucket/secrets sem executar deploy público ainda.
