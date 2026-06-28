# Contexto do Projeto — SERKET Gestor

## Localização

- Repositório externo: `/home/evonexus/evo-projects/serket-gestor`
- App executável: `/home/evonexus/evo-projects/serket-gestor/_src`
- Workspace EvoNexus: `workspace/projects/serket/plans/serket-gestor/`
- Remoto GitHub: `https://github.com/eduardomrj/serket-gestor.git`
- Branch base clonada: `main`

## Stack

- Linguagem: PHP
- Framework principal: Adianti Framework 7.5.x
- Extensões: MAD Framework / Mad Builder
- Banco: MySQL/MariaDB
- Dependências: Composer, com `composer.json` dentro de `_src/`
- Timezone/locale: `America/Fortaleza`, `pt-BR`

## Estrutura principal

```text
serket-gestor/
  _src/                         # aplicação PHP principal
    app/config/                 # configs da aplicação e bancos
    app/control/                # telas, TPage/TWindow/TForm
    app/controller/             # controllers REST/API
    app/database/               # SQLs e permissões
    app/middleware/             # middlewares REST
    app/model/                  # models Active Record
    app/routes/                 # rotas REST
    app/service/                # regras de negócio
    index.php                   # entrada web principal
    MadRestServer.php           # API REST moderna
    rest.php                    # API REST legada
    composer.json               # dependências PHP
  PROJECT-theme/                # tema/protótipos visuais
  docs/                         # documentação técnica do repo externo
  scripts/                      # scripts de migração/manutenção
  sql/                          # SQLs auxiliares
  test/                         # testes/cenários
  tools/                        # ferramentas operacionais
  AGENTS.md                     # guia operacional obrigatório
  README.md                     # visão geral
```

## Arquivos obrigatórios antes de qualquer alteração

Antes de implementar, revisar ou planejar mudanças no repo, o agente deve ler:

1. `/home/evonexus/evo-projects/serket-gestor/AGENTS.md`
2. `/home/evonexus/evo-projects/serket-gestor/.github/copilot-instructions.md`
3. `/home/evonexus/evo-projects/serket-gestor/README.md`

Regra do próprio projeto: se houver conflito, `.github/copilot-instructions.md` prevalece para arquitetura.

## Regras de desenvolvimento observadas

- Arquitetura em camadas: View → Controller → Service.
- Priorizar recursos nativos Adianti/MAD antes de criar abstrações próprias.
- Operações de banco devem usar `TTransaction`.
- Validar permissões e sanitizar entradas/saídas.
- Cuidado com credenciais em `_src/app/config/`.
- Não publicar tokens, senhas, chaves REST ou valores sensíveis em logs/documentação.
- Atualizar cabeçalhos/versionamento em arquivos PHP quando aplicável ao padrão interno.

## Comandos citados pelo README

Instalar dependências:

```bash
cd /home/evonexus/evo-projects/serket-gestor/_src
composer install
```

Rodar localmente com servidor PHP embutido:

```bash
cd /home/evonexus/evo-projects/serket-gestor/_src
php -S localhost:8000
```

Validação rápida de sintaxe:

```bash
php -l /home/evonexus/evo-projects/serket-gestor/_src/app/routes/api.php
```

Testes citados:

```bash
cd /home/evonexus/evo-projects/serket-gestor
php test/TestRunner.php
php test/TestRunner.php --cleanup
php test/TestRunner.php --cenario=tratamento_basico
php test/TestRunner.php --verbose
php test/TestRunner.php --list
```

## Pontos de atenção

- O README informa que `_src/app/config/` pode conter credenciais; não imprimir esses arquivos integralmente sem necessidade.
- A raiz pública em Apache/Nginx deve apontar para `_src/`.
- API moderna: `_src/MadRestServer.php`.
- API legada: `_src/rest.php`.
- Rotas modernas: `_src/app/routes/api.php`.
- Logs de erro PHP esperados em `_src/tmp/php_errors.log`.

## Status inicial

- Clone realizado em 2026-06-26.
- Working tree limpo após clone.
- Branch `main` rastreando `origin/main`.
