# Preparação de dependências — tentativa 2026-06-11/12

**Projeto:** Documenso Swarm  
**Escopo autorizado:** preparar dependências sem publicar serviço  
**Status:** BLOQUEADO antes de criar recursos, por indisponibilidade do Vaultwarden CLI

---

## Autorização recebida

Eduardo autorizou explicitamente:

```text
AUTORIZO PREPARAR DEPENDÊNCIAS SEM PUBLICAR
```

Depois do alerta de exposição de credenciais no output do `mc alias list`, Eduardo autorizou continuar com:

```text
CONTINUE COM COMANDOS REDIGIDOS
```

---

## Escopo mantido

Permitido nesta etapa:

- criar DB `documenso`;
- criar role `documenso_app`;
- criar bucket MinIO `documenso`;
- criar credenciais dedicadas;
- gerar secrets técnicos;
- salvar em Vaultwarden + Docker Swarm secrets;
- gerar `.p12` self-signed de teste;
- montar stack draft.

Não permitido nesta etapa:

- alterar DNS;
- alterar Cloudflare Tunnel;
- alterar rota pública;
- publicar serviço;
- executar stack/deploy;
- rodar migrations.

---

## Estado validado com comandos redigidos

### Vaultwarden CLI

- `bw status` falha.
- `BW_SESSION` não está presente.
- Erro observado:

```text
EROFS: read-only file system, mkdir '/home/evonexus/.config/Bitwarden CLI/data.json.lock'
```

Conclusão: Vaultwarden CLI indisponível nesta sessão/ambiente. Como a decisão aprovada define Vaultwarden como fonte de verdade, não é seguro gerar secrets finais sem conseguir salvar no cofre.

### PostgreSQL

Host: `192.168.88.106`

Estado:

```text
db_documenso_exists=false
role_documenso_app_exists=false
```

Nenhuma alteração executada.

### MinIO

Host principal: `192.168.88.240`

Estado:

```text
bucket_documenso_exists=false
minio_user_documenso_app_exists=false
minio_policy_documenso_rw_exists=false
```

Nenhuma alteração executada.

### Swarm

Manager: `192.168.88.73`

Estado:

```text
stack_documenso_exists=false
network_traefik_homelab_exists=true
target_worker_label={"allow_app":"true","host":"vm-docker-worker-2","postgres_task":"0itjjc9eri78","provider":"local","zone":"lan"}
```

Nenhuma alteração executada.

---

## Artefato gerado

Criado somente draft sem segredos reais:

```text
workspace/projects/evo-nexus/features/documenso-swarm/stack-draft-documenso.yml
```

Esse arquivo contém placeholders `REDACTED` e `PIN_VERSION_BEFORE_DEPLOY`. Não deve ser aplicado sem revisão.

---

## Incidente/risco observado

Durante validação read-only anterior, o comando `mc alias list` imprimiu credenciais MinIO no output interno da ferramenta. Os valores não devem ser repetidos. Recomenda-se planejar rotação posterior das credenciais MinIO expostas, com janela controlada.

---

## Decisão operacional

Preparação real foi pausada antes de criar recursos porque:

1. secrets precisam ser salvos no Vaultwarden;
2. Vaultwarden CLI não está funcional no ambiente atual;
3. criar DB/bucket/credentials sem cofre quebraria a decisão aprovada e aumentaria risco operacional.

---

## Próximas opções

### Opção A — Corrigir Vaultwarden CLI e continuar

Recomendada.

Resolver erro de lock/EROFS no Bitwarden CLI ou usar ambiente com `BW_SESSION` funcional. Depois:

- gerar secrets;
- salvar no Vaultwarden;
- criar DB/user;
- criar bucket/user/policy;
- criar Docker secrets;
- gerar `.p12` de teste.

### Opção B — Autorizar armazenamento temporário seguro fora do Vaultwarden

Exige autorização explícita do Eduardo.

Exemplo: arquivo temporário root-only em host de operação, com remoção após salvar no cofre. Não recomendado enquanto Vaultwarden estiver indisponível.

### Opção C — Pausar e planejar rotação MinIO

Tratar primeiro a exposição do `mc alias list` e só depois continuar Documenso.
