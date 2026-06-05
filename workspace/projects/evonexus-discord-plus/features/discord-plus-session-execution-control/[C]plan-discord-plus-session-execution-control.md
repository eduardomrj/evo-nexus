# Plano — Discord Plus Session Execution Control

## Escopo

Implementar controle de execução por sessão no Discord Plus para resolver:

1. notificações periódicas em execuções longas;
2. lock/cancelamento por `sessionKey`.

Repo alvo:

```text
/home/evonexus/evo-projects/evonexus-discord-plus
```

Runtime alvo:

```text
evonexus-discord-plus.service
```

Fora de escopo: Discord oficial/plugin oficial.

## Fase 1 — Registry de execução ativa

### Item 1.1 — Criar `SessionExecutionRegistry`

**Tipo:** [CONSTRUIR NOVO]  
**Eixo:** runtime/session control  
**Arquivos prováveis:**

- `src/sessions/session-execution-registry.ts`
- `tests/sessions/session-execution-registry.test.ts`

**Passos:**

1. Criar registry in-memory por `sessionKey`.
2. Registrar execução com:
   - `sessionKey`
   - `startedAt`
   - `child process`
   - estado `running|cancelling|cancelled|finished|failed`
   - função cleanup
3. Expor métodos:
   - `tryStart(sessionKey, execution)`
   - `get(sessionKey)`
   - `finish(sessionKey)`
   - `cancel(sessionKey)`
   - `listActive()`
4. Garantir liberação em `finally`.
5. Adicionar TTL/janitor simples para locks antigos.

**Critérios de aceite:**

- Segunda execução na mesma `sessionKey` é recusada.
- Execuções em sessionKeys diferentes são permitidas.
- `finish` libera lock.
- `cancel` chama encerramento do processo.

## Fase 2 — Integrar registry ao CLI runner

### Item 2.1 — Envolver `CliSessionRunner.sendMessage`

**Tipo:** [EVOLUIR]  
**Eixo:** runtime/session control  
**Arquivos prováveis:**

- `src/sessions/cli-session-runner.ts`
- `tests/sessions/cli-session-runner.test.ts`

**Passos:**

1. Antes de spawnar CLI, chamar `registry.tryStart(envelope.sessionKey, ...)`.
2. Se já houver execução ativa, retornar resposta curta:
   ```text
   Já existe uma execução em andamento neste tópico há Xm. Use /session cancel para interromper ou aguarde.
   ```
3. Armazenar child process no registry assim que spawnar.
4. Em `exit/close/error/timeout`, liberar registry.
5. Em cancelamento, impedir entrega de resposta final tardia.

**Critérios de aceite:**

- Não abre segundo processo para mesma sessão.
- Lock é liberado após sucesso, erro e timeout.
- Teste cobre fake process pendurado.

## Fase 3 — Progress notifications

### Item 3.1 — Criar callback de progresso

**Tipo:** [CONSTRUIR NOVO]  
**Eixo:** UX/Discord feedback  
**Arquivos prováveis:**

- `src/sessions/cli-session-runner.ts`
- `src/sessions/gateway-dispatcher.ts`
- `tests/sessions/cli-session-runner.test.ts`
- `tests/sessions/gateway-dispatcher.test.ts`

**Passos:**

1. Adicionar opção `onProgress(sessionKey, elapsedMs)` no runner ou dispatcher.
2. Timer:
   - primeira notificação: 30s;
   - intervalo: 90s;
   - limite: 10 mensagens/edições.
3. Preferir editar uma mensagem de status; se não houver suporte pronto, enviar mensagens espaçadas.
4. Limpar timer em `finally`.
5. Mensagens devem ser honestas e curtas:
   ```text
   ⏳ Ainda trabalhando... 2m decorridos.
   ```

**Critérios de aceite:**

- Tarefa simulada >30s gera update.
- Tarefa curta não gera update.
- Timer é limpo em sucesso, erro, timeout e cancelamento.
- Não há progresso inventado.

## Fase 4 — `/session cancel` e status expandido

### Item 4.1 — Adicionar subcomando `/session cancel`

**Tipo:** [EVOLUIR]  
**Eixo:** comando/session control  
**Arquivos prováveis:**

- `src/sessions/session-command.ts`
- `server.ts`
- `tests/sessions/session-command.test.ts`

**Passos:**

1. Adicionar `cancel` ao parser/handler de `/session`.
2. Resolver `sessionKey` atual pelo mesmo mecanismo de `status/reset/renew`.
3. Chamar registry cancel para a sessão atual.
4. Responder:
   - execução cancelada;
   - ou nenhuma execução ativa.

**Critérios de aceite:**

- `/session cancel` cancela apenas a sessão atual.
- Não afeta outros tópicos.
- Resposta clara no Discord.

### Item 4.2 — Expandir `/session status`

**Tipo:** [EVOLUIR]  
**Eixo:** observabilidade  
**Arquivos prováveis:**

- `src/sessions/session-command.ts`

**Passos:**

1. Incluir `execution: running|idle`.
2. Incluir tempo decorrido se running.
3. Não expor secrets nem payloads.

**Critérios de aceite:**

- Status mostra execução ativa enquanto processo está vivo.
- Status volta para idle após término/cancelamento.

## Fase 5 — Verificação operacional

### Item 5.1 — Testes automatizados

**Tipo:** [ATIVAR]  
**Eixo:** qualidade  
**Comandos:**

```bash
cd /home/evonexus/evo-projects/evonexus-discord-plus
bun test tests/sessions/cli-session-runner.test.ts
bun test tests/sessions/session-command.test.ts
bun test
```

**Critérios de aceite:**

- Suíte focada passa.
- Suíte completa passa ou falhas preexistentes documentadas.

### Item 5.2 — Smoke manual no Discord Plus

**Tipo:** [ATIVAR]  
**Eixo:** operação  
**Passos:**

1. Reiniciar apenas `evonexus-discord-plus.service`.
2. No tópico CPSMQ, rodar `/session reset`.
3. Disparar uma tarefa longa controlada.
4. Confirmar progress notification.
5. Durante execução, enviar nova mensagem e confirmar lock.
6. Rodar `/session cancel` e confirmar encerramento.

**Critérios de aceite:**

- Não surgem múltiplos processos para mesma `sessionKey`.
- O usuário recebe feedback periódico.
- `/session cancel` funciona.
- Discord oficial permanece intocado.

## Riscos e cuidados

- Garantir que registry seja compartilhado entre dispatcher e command handler.
- Evitar leak de timers.
- Evitar matar processos que não sejam filhos da execução registrada.
- Não usar `pkill claude`; cancelamento deve mirar child process registrado.
- Não reiniciar nem alterar Discord oficial.

## Time sugerido

- Implementação: `bolt-executor` ou execução direta guiada pelo Oracle.
- Revisão: `lens-reviewer`.
- Verificação: `oath-verifier` ou teste manual + `bun test`.

## Pendência de decisão

- Preferir editar uma mensagem de status única ou enviar mensagens periódicas separadas?
  - Recomendação inicial: enviar mensagens separadas se edição exigir refactor maior; evoluir depois para edição.
