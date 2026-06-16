# Decisões — Documenso self-hosted em Docker Swarm

**Projeto:** evo-nexus / infraestrutura operacional  
**Feature:** documenso-swarm  
**Data local:** 2026-06-11 (America/Fortaleza)  
**Origem:** entrevista decisória com Eduardo via Discord Plus

---

## Decisões aprovadas

| ID | Decisão | Valor aprovado | Observação operacional |
|---|---|---|---|
| D-01 | Domínio público | `signature.myworkhome.com.br` | URL canônica do serviço |
| D-02 | Exposição inicial | Pública controlada | HTTPS, signup fechado após bootstrap, sem porta direta |
| D-03 | Topologia de entrada | Cloudflare Tunnel existente → IP do manager Swarm → Traefik Swarm → Documenso | Decisão explícita de não usar Traefik LXC 211 neste POC |
| D-04 | Placement | Apenas workers da homelab | Excluir manager e worker externo/Hetzner |
| D-05 | Certificado `.p12` | Certificado de teste no POC | Troca para oficial em etapa posterior |
| D-06 | PostgreSQL | Existente, com DB/user dedicados | DB `documenso`, user `documenso_app` |
| D-07 | Storage | MinIO existente com bucket dedicado | Usar MinIO principal |
| D-08 | SMTP | Zoho com remetente dedicado | Credencial via cofre/secret |
| D-09 | Remetente SMTP | `gocontrol@automacaosoftware.com.br` | Alterado em 2026-06-12 após validação: app password existente autentica para `gocontrol@...` e falha para `signature@...`; secret `documenso_smtp_password_v1` criado sem expor valor |
| D-10 | Endpoint do tunnel | IP do manager Swarm | Preflight deve confirmar IP atual |
| D-11 | Banco/usuário | DB `documenso`, user `documenso_app` | Permissões mínimas |
| D-12 | MinIO alvo | MinIO principal existente | Preflight deve confirmar endpoint |
| D-13 | Bucket | `documenso` | Policy mínima, sem public read |
| D-14 | Tunnel → Traefik | HTTP interno porta 80 | Cloudflare termina HTTPS externo |
| D-15 | Imagem Documenso | Última release estável pinada no deploy | Tag explícita e digest se disponível; nunca `latest` |
| D-16 | Componentes opcionais | POC simples | Sem Redis/BullMQ, sem Gotenberg |
| D-17 | Cloudflare Tunnel | Usar tunnel existente | Backup/registro de config antes de alteração |
| D-18 | Preparação autorizada | Preparar dependências sem publicar | DB, bucket, credenciais, secrets e stack draft; sem tráfego público |
| D-19 | Segredos | Vaultwarden + Docker Swarm secrets | Discord/prompt/logs nunca recebem segredos |
| D-20 | Admin inicial | `eduardo@automacaosoftware.com.br` | Criar no bootstrap e fechar signup |
| D-21 | Traefik Swarm | Usar Traefik Swarm existente | Preflight deve validar existência, rede e entrypoint |
| D-22 | Backup | Backup mínimo antes de qualquer deploy | DB, tunnel config, Traefik config, bucket/secrets por nome, stack sem segredos |
| D-23 | `.p12` de teste | SysOps gera self-signed | Somente POC |
| D-24 | Stack Swarm | `documenso` | Serviço `documenso_app`, rede `documenso_internal` |
| D-25 | Recursos | Conservador | RAM limit 1024 MB; reservation 512 MB; CPU limit 1.0; reservation 0.25 |
| D-26 | Geração de secrets | SysOps gera tudo | Salvar em Vaultwarden + Swarm secrets |
| D-27 | Signup | Aberto só durante bootstrap e fechado imediatamente | Validar bloqueio antes de smoke externo |
| D-28 | Smoke test externo | `eduardo@sysautomacao.com.br` | Destinatário externo para validar email/link/assinatura |
| D-29 | Próximo passo | Atualizar artefatos + preflight read-only | Sem criar recursos ainda |

---

## Escopo autorizado agora

Autorizado:

- atualizar PRD/plano/tasks/runbook com as decisões;
- executar preflight read-only para identificar/validar:
  - IP do manager Swarm;
  - Traefik Swarm existente;
  - MinIO principal;
  - PostgreSQL alvo;
  - Cloudflare Tunnel/config atual;
  - labels/placement disponíveis no Swarm.

Não autorizado nesta etapa:

- criar banco;
- criar usuário PostgreSQL;
- criar bucket;
- criar credenciais;
- criar Docker secrets;
- alterar Cloudflare Tunnel;
- publicar domínio;
- rodar stack/deploy;
- executar migrations.

---

## Critério para avançar após preflight

Antes de executar qualquer mudança real, SysOps deve apresentar:

1. achados do preflight;
2. rollback mapeado;
3. comandos/ações propostas;
4. confirmação humana explícita.
