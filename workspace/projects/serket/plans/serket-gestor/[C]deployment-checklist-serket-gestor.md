# Checklist de Deploy — SERKET Gestor

## Objetivo

Documentar o fluxo seguro para trabalhar no `serket-gestor`, validar em desenvolvimento/testes no LXC230 e publicar em produção somente via `@custom-sysops`.

## Ambientes

### Repositório local de trabalho

```text
/home/evonexus/evo-projects/serket-gestor
```

### Desenvolvimento/Testes

```text
Servidor: LXC230 homelab
Path executável: /var/www/apps/serket/demo/_src
```

Este ambiente é exclusivamente de desenvolvimento/testes. Não deve ser tratado como produção.

### Produção

```text
Servidor: Hetzner-App-Production
HostName: 37.27.202.125
User: emrj
Port: 2299
Path: /home/emrj/stacks/app-serket-caninde/source
```

Qualquer publicação em produção deve ser feita por `@custom-sysops`, pois ele detém as credenciais e o caminho operacional seguro.

---

## Checklist operacional

### 1. Preparação local

- Trabalhar somente no repo local:
  - `/home/evonexus/evo-projects/serket-gestor`
- Confirmar branch atual e estado do Git.
- Ler antes de qualquer alteração/análise profunda:
  - `AGENTS.md`
  - `.github/copilot-instructions.md`
  - `README.md`
- Identificar exatamente quais arquivos serão afetados.
- Se for mudança grande, criar ticket/plano formal antes de código.

### 2. Análise da demanda

Antes de implementar, registrar:

- O que precisa mudar.
- Onde provavelmente muda.
- Risco da alteração.
- Critério de aceite.
- Agentes necessários, se aplicável:
  - `@apex-architect` para análise/arquitetura.
  - `@bolt-executor` para implementação.
  - `@oath-verifier` para verificação.
  - `@custom-sysops` para publicação/deploy.

Antes de alterar arquivos, apresentar ao Eduardo:

```text
Arquivos previstos:
- caminho/arquivo1.php
- caminho/arquivo2.php

Tipo de alteração:
- correção / feature / ajuste visual / integração / deploy

Riscos:
- baixo/médio/alto

Validação prevista:
- sintaxe PHP
- fluxo web
- endpoint/API
- logs
```

### 3. Implementação no repo local

Somente após aprovação explícita:

- Alterar arquivos no repo local.
- Não tocar sem confirmação explícita em:
  - `_src/app/config/`
  - `.env`
  - dumps
  - logs
  - caches
  - `_src/vendor/`
- Não imprimir credenciais.
- Não publicar nada automaticamente.

### 4. Validação local

Após alteração:

- Mostrar `git diff` ou resumo dos arquivos alterados.
- Checar sintaxe PHP dos arquivos modificados.
- Rodar Composer apenas se dependências forem afetadas.
- Revisar aderência às regras do projeto:
  - Adianti/MAD.
  - Arquitetura View → Controller → Service.
  - `TTransaction` em operações de banco.
  - Formatação esperada do projeto.

Se algo falhar, parar e reportar antes de seguir.

### 5. Preparação para Dev/Test no LXC230

Antes de qualquer comando no LXC230, apresentar a estratégia:

```text
Origem:
  /home/evonexus/evo-projects/serket-gestor/_src/

Destino:
  /var/www/apps/serket/demo/_src/

Excluir/preservar:
  app/config/
  vendor/
  logs/
  cache/
  .env
  dumps
```

Pedir aprovação explícita:

```text
Posso seguir com o sync para o ambiente dev/test?
```

### 6. Deploy/build no Dev/Test

Somente após aprovação:

- Sincronizar apenas os arquivos necessários para o LXC230.
- Preservar configs do ambiente:
  - `/var/www/apps/serket/demo/_src/app/config/`
- Rodar build/composer apenas se necessário.
- Registrar comandos executados.
- Não tratar este ambiente como produção.

### 7. Validação no Dev/Test

Depois do sync/build:

- Validar tela/fluxo afetado.
- Validar endpoint REST se aplicável:
  - `_src/MadRestServer.php`
  - `_src/rest.php`
  - `_src/app/routes/api.php`
- Verificar logs PHP do ambiente.
- Confirmar ausência de exposição de segredo.
- Confirmar resultado contra critério de aceite.

Formato esperado:

```text
Dev/Test: PASS / FAIL / PARCIAL
Evidências:
- comando X
- tela Y
- endpoint Z
- logs sem erro crítico
```

### 8. Promoção para produção

Antes de produção, obrigatório:

- Dev/Test validado.
- Diff final revisado.
- Lista de arquivos a publicar definida.
- Plano de rollback simples.
- Aprovação explícita do Eduardo.

### 9. Acionar `@custom-sysops`

Para produção, Oracle/agentes de desenvolvimento não publicam diretamente.

Handoff obrigatório para `@custom-sysops`:

```text
- repo local
- arquivos alterados
- destino produção
- comandos/estratégia aprovados
- configs que não podem ser sobrescritas
- validações esperadas
- rollback previsto
```

### 10. Deploy produção via SysOps

SysOps deve apresentar antes:

- O que será publicado.
- Para onde.
- Como configs serão preservadas.
- Quais comandos serão usados.
- Como validar.
- Como reverter.

Nada de produção sem aprovação explícita do Eduardo.

### 11. Pós-produção

Depois da publicação:

- Validar fluxo real afetado.
- Conferir logs.
- Confirmar ausência de erro crítico.
- Registrar resultado.
- Se houver ticket, perguntar antes de marcar como resolvido.

---

## Regra principal

Antes de qualquer alteração com efeito colateral, apresentar:

```text
1. O que será alterado
2. Onde será alterado
3. Quais comandos serão executados
4. O que NÃO será tocado
5. Como será validado
6. Como reverter se der problema
```

## Status

- Documentado em 2026-06-28.
- Próxima ação: criar/executar uma task futura para aplicar este checklist na primeira demanda do `serket-gestor`.
