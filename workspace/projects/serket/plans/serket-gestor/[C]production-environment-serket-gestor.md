# Ambiente de Produção — SERKET Gestor

## Definição oficial

Este é o ambiente de **produção** do SERKET.

Diferente do LXC230 da homelab, que é desenvolvimento/testes, este ambiente roda no servidor Hetzner de produção e deve ser tratado com máxima cautela operacional.

## Servidor

```text
Host: Hetzner-App-Production
HostName: 37.27.202.125
User: emrj
Port: 2299
```

## Caminho da aplicação em produção

```text
/home/emrj/stacks/app-serket-caninde/source
```

## Separação de ambientes

### Desenvolvimento/Testes

```text
Servidor: LXC230 homelab
Path: /var/www/apps/serket/demo/_src
```

Uso: validar build, dependências, telas, APIs e fluxos reais antes de produção.

### Produção

```text
Servidor: Hetzner-App-Production
Path: /home/emrj/stacks/app-serket-caninde/source
```

Uso: ambiente real do cliente/operação.

## Regra obrigatória de publicação

Qualquer publicação/deploy para servidores deve acionar o agente:

```text
@custom-sysops
```

Motivo: o `@custom-sysops` detém as credenciais e o caminho operacional seguro para publicar arquivos nos servidores.

## Guardrails de produção

Nenhum agente deve executar diretamente em produção sem aprovação explícita do Eduardo:

- `rsync`
- `scp`
- `git pull`
- `composer install` / `composer update`
- alteração de permissões
- restart de serviço
- edição de arquivo remoto
- qualquer comando SSH com efeito colateral

Antes de qualquer ação em produção, o agente responsável deve:

1. acionar `@custom-sysops`;
2. explicar o que será publicado;
3. mostrar os comandos ou a estratégia operacional;
4. pedir aprovação explícita do Eduardo;
5. preservar configs sensíveis do ambiente;
6. validar o resultado após a publicação.

## Segurança

- Não imprimir credenciais.
- Não registrar senhas, tokens ou chaves em documentação/logs.
- Não sobrescrever configurações de produção sem confirmação explícita.
- Não tratar produção como ambiente de teste.

## Status

- Registrado em 2026-06-26.
- Produção definida por Eduardo como Hetzner-App-Production.
- Publicação deve ser roteada via `@custom-sysops`.
