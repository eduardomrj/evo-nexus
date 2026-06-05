---
author: oracle
type: prd
date: 2026-06-03
feature: discord-plus-extra-dirs
status: draft
---

# PRD — Discord Plus Extra Dirs: pastas adicionais por tópico/canal

## Problema

O Discord Plus já permite vincular um projeto ativo por tópico via `/project set`, que define o contexto principal da sessão. Porém não há como declarar diretórios adicionais que o agente também deve enxergar na mesma execução.

Na prática, um tópico de trabalho pode precisar que o agente acesse simultaneamente o projeto principal (`/project set`) **e** outros repositórios ou pastas relacionadas — por exemplo, um backend e um frontend separados, ou dois microserviços que se comunicam.

Hoje o único `--add-dir` extra é `/home/evonexus/evo-nexus`, injetado automaticamente para preservar agentes/skills/regras do EvoNexus. Não há mecanismo para o usuário declarar pastas adicionais por tópico.

## Objetivos

- Permitir adicionar/remover pastas extras ao contexto de execução de um tópico/canal.
- Cada pasta extra vira um `--add-dir` adicional passado ao CLI nas execuções daquele escopo.
- Manter `/project set` intocável — as pastas extras são complementares, não substituem o projeto ativo.
- Restringir as pastas extras à allowlist `/home/evonexus/evo-projects/`.
- Persistir a lista de pastas extras por escopo (guild/channel/thread), com sobrevivência a restart do serviço.

## Não objetivos

- Não alterar o projeto ativo definido via `/project set`.
- Não trocar o `cwd` da sessão.
- Não permitir paths fora de `/home/evonexus/evo-projects/`.
- Não aceitar arquivos, apenas diretórios.
- Não aceitar paths relativos, com `..`, ou symlinks que escapem da allowlist.
- Não remover o `--add-dir /home/evonexus/evo-nexus` automático.
- Não alterar o core do OpenClaude.

## Usuários

- **Eduardo**: operador principal, precisa que o agente veja múltiplos repositórios numa mesma sessão Discord sem perder o projeto ativo ou o contexto do EvoNexus.

## Casos de uso

1. **Adicionar pasta extra**
   Eduardo usa `/dirs add path:/home/evonexus/evo-projects/go-payment-hub` num tópico onde `/project set` já aponta para `go-control-erp`. As próximas execuções passam ambos os caminhos ao CLI.

2. **Listar pastas extras ativas**
   Eduardo usa `/dirs list` e vê quais pastas extras estão ativas no tópico atual.

3. **Remover pasta extra**
   Eduardo usa `/dirs remove path:/home/evonexus/evo-projects/go-payment-hub` para remover uma pasta que não é mais necessária.

4. **Limpar todas as pastas extras**
   Eduardo usa `/dirs clear` para remover todas as pastas extras do tópico, sem afetar o projeto ativo.

5. **Execução com múltiplos contextos**
   Tópico tem `/project set` apontando para `go-control-erp` e duas pastas extras (`go-payment-hub`, `go-message`). O CLI é invocado com:
   ```
   --add-dir /home/evonexus/evo-nexus
   --add-dir /home/evonexus/evo-projects/go-payment-hub
   --add-dir /home/evonexus/evo-projects/go-message
   ```
   O `cwd` permanece `/home/evonexus/evo-projects/go-control-erp`.

## Requisitos funcionais

### RF1 — Comando `/dirs add path:<path>`

- Deve validar que `path` existe e é diretório.
- Deve canonicalizar/normalizar o path antes de persistir.
- Deve aceitar apenas paths dentro de `/home/evonexus/evo-projects/`.
- Deve rejeitar path traversal (`..`), path relativo e symlink que escape da allowlist.
- Deve rejeitar arquivos (incluindo `.env` e secrets).
- Deve persistir a pasta no escopo atual (guild/channel/thread).
- Não deve duplicar pastas já presentes na lista.
- Deve exigir permissão `dirs.write`.
- Deve responder com confirmação e recomendar `/session reset` se houver sessão ativa.
- Não deve resetar, renovar ou salvar sessão automaticamente.

### RF2 — Comando `/dirs remove path:<path>`

- Deve remover a pasta da lista de extras do escopo atual.
- Deve exigir `dirs.write`.
- Deve informar se a pasta não estava na lista.
- Deve recomendar `/session reset` se houver sessão ativa.
- Não deve resetar sessão automaticamente.

### RF3 — Comando `/dirs list`

- Deve listar as pastas extras ativas no escopo atual.
- Deve indicar quando a lista está vazia.
- Deve ser leitura apenas (sem `dirs.write`).
- Deve mostrar também o projeto ativo (via `/project`) e o `--add-dir` automático do EvoNexus, para que o usuário tenha visão completa do contexto.

### RF4 — Comando `/dirs clear`

- Deve remover todas as pastas extras do escopo atual.
- Deve exigir `dirs.write`.
- Não deve afetar o projeto ativo definido via `/project set`.
- Deve recomendar `/session reset` se houver sessão ativa.

### RF5 — Injeção no CLI

- Para cada execução num escopo com pastas extras, cada pasta deve ser passada como `--add-dir <path>` ao CLI, **depois** do `--add-dir /home/evonexus/evo-nexus` automático.
- A ordem de injeção deve ser determinística (ex: ordem de adição).
- O `cwd` da sessão não deve ser alterado por este recurso.
- O projeto ativo do `/project set` não deve ser afetado.

### RF6 — Storage

- Deve persistir no state dir do Discord Plus, seguindo padrão dos stores existentes.
- Deve armazenar por escopo (guildId/channelId/threadId).
- Deve ser robusto a restart do serviço.
- Deve armazenar no mínimo: `canonicalPath`, `addedAt`, `addedBy`, `scopeKey`.

### RF7 — Registro de comandos

- O registro de slash commands deve incluir `/dirs` junto de `/model`, `/session` e `/project`.
- Não deve reintroduzir comandos antigos do discord-bridge.

## Segurança

- Allowlist: `/home/evonexus/evo-projects/` e `/home/evonexus/evo-projects-data/` (fixo, sem configuração adicional nesta fase).
- Rejeitar path traversal, path relativo inseguro e symlink fora da allowlist.
- Rejeitar arquivos, `.env`, secrets e qualquer path que não seja diretório.
- Rejeitar roots sensíveis: `/`, `/etc`, `/root`, `/home`, `/home/evonexus` amplo.
- `/dirs add` e `/dirs remove` e `/dirs clear` exigem `dirs.write`.
- `/dirs list` é leitura apenas.
- Não imprimir conteúdo de `.env` ou listagens completas do filesystem nas respostas.

## UX de comandos

### `/dirs add`

```
Pasta adicionada ao contexto deste tópico:
  /home/evonexus/evo-projects/go-payment-hub

Pastas extras ativas: 1
Se já havia uma sessão ativa, recomendo /session reset para evitar contexto antigo.
```

### `/dirs list`

```
Contexto de execução deste tópico:

Projeto ativo (/project):  /home/evonexus/evo-projects/go-control-erp
Auto (EvoNexus):            /home/evonexus/evo-nexus
Pastas extras (/dirs):
  1. /home/evonexus/evo-projects/go-payment-hub
  2. /home/evonexus/evo-projects/go-message
```

### `/dirs remove`

```
Pasta removida do contexto deste tópico:
  /home/evonexus/evo-projects/go-payment-hub

Se já havia uma sessão ativa, recomendo /session reset para evitar contexto antigo.
```

### `/dirs clear`

```
Todas as pastas extras removidas deste tópico.
Projeto ativo (/project) não foi alterado.
Se já havia uma sessão ativa, recomendo /session reset.
```

## Critérios de aceite

### CA1 — Adicionar pasta válida
Given Eduardo tem `dirs.write` e `/home/evonexus/evo-projects/go-payment-hub` existe como diretório
When executa `/dirs add path:/home/evonexus/evo-projects/go-payment-hub`
Then a pasta é persistida no escopo atual
And `/dirs list` mostra essa pasta como extra ativa.

### CA2 — Bloquear path fora da allowlist
Given Eduardo tenta `/dirs add path:/home/evonexus/evo-projects-data/cpsmq`
Then o comando falha com erro seguro
And nenhuma pasta é persistida.

### CA3 — Bloquear path traversal e arquivo
Given path com `..` ou path apontando para arquivo
When executa `/dirs add`
Then o comando rejeita após canonicalização.

### CA4 — Injeção no CLI
Given tópico tem projeto ativo `go-control-erp` e pasta extra `go-payment-hub`
When uma mensagem é enviada ao engine
Then o CLI é invocado com `--add-dir /home/evonexus/evo-nexus` e `--add-dir /home/evonexus/evo-projects/go-payment-hub`
And o `cwd` permanece `/home/evonexus/evo-projects/go-control-erp`.

### CA5 — `/dirs clear` não afeta `/project`
Given tópico tem projeto ativo e 2 pastas extras
When executa `/dirs clear`
Then as pastas extras são removidas
And o projeto ativo permanece inalterado.

### CA6 — Autorização
Given usuário sem `dirs.write`
When executa `/dirs add`, `/dirs remove` ou `/dirs clear`
Then o comando é negado.

### CA7 — Persistência após restart
Given pastas extras configuradas no tópico
When o serviço é reiniciado
Then as pastas extras são mantidas.

### CA8 — Registro de comandos
Given os slash commands são registrados
Then `/dirs` está presente junto de `/model`, `/session` e `/project`.

### CA9 — Sem duplicatas
Given pasta `/home/evonexus/evo-projects/go-payment-hub` já está na lista
When executa `/dirs add` com o mesmo path
Then o comando informa que já está presente e não duplica.

### CA10 — Testes automatizados
Given a suite `bun test`
When roda
Then cobrem: validação de path/allowlist, store por escopo, add/remove/list/clear, autorização, injeção no CLI e registro de comandos.

## Riscos

- **Muitas pastas podem aumentar custo de tokens**: o `--add-dir` injeta contexto no prompt. Mitigado por limite máximo de pastas por escopo (sugestão: 5) a definir na implementação.
- **Confusão com projeto ativo**: mitigado por `/dirs list` mostrar o contexto completo e separar visualmente projeto vs extras.
- **Contexto antigo em sessão ativa**: mitigado por recomendar `/session reset` explicitamente sem reset silencioso.
- **Regressão em `/project`**: mitigado por testes de regressão cobrindo que `/project` permanece inalterado após operações `/dirs`.

## Dependências

- `ReadWritePaths` do `evonexus-discord-plus.service` já expandido para `/home/evonexus/evo-projects-data` (feito em 2026-06-03).
- Módulo `src/projects/` existente como referência de padrão para store/validator/command.
- Operação `dirs.write` deve ser adicionada a `AUTHORIZATION_OPERATIONS` e `CHANNEL_OPERATIONS`.

## Decisões (resolvidas em 2026-06-03)

- [x] Limite máximo de pastas extras por escopo: **5**.
- [x] Autocomplete no `/dirs add`: **sim**, listar subdiretórios de ambas as roots.
- [x] Allowlist: **`/home/evonexus/evo-projects/` e `/home/evonexus/evo-projects-data/`**.
- [x] Herança thread→canal: **sem herança na v1** — cada escopo começa independente.

## Handoff

- **Next agent:** @compass-planner (plano de implementação)
- **Source artifact:** este PRD
- **Expected output:** plano 4–6 steps em `workspace/development/plans/discord-plus-extra-dirs/[C]plan-discord-plus-extra-dirs-2026-06-03.md`
