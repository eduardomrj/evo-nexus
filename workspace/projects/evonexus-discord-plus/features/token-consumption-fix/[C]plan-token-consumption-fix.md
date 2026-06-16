# Plano de Execução — Token Consumption Fix

**Feature:** `token-consumption-fix`
**Projeto:** evonexus-discord-plus
**Data:** 2026-06-15
**Status:** ✅ IMPLEMENTADO (verificado 2026-06-16)
**Owner:** bolt-executor
**Verificação:** oath-verifier

---

## Sequência de execução

Os 4 passos são independentes entre si — podem ser executados em qualquer ordem. Sugestão: do mais simples ao mais complexo.

---

### Passo 1 — P4: Salvar token count real após compact

**Arquivo:** `src/sessions/cli-session-runner.ts`

**Mudança:**
```typescript
// ANTES (linha ~640):
this.options.store.setTokenCount(this.supervised.key, 0)

// DEPOIS:
this.options.store.setTokenCount(
  this.supervised.key,
  compactOutput.inputTokens ?? 0,
)
```

Aplicar nos dois pontos onde `setTokenCount(supervised.key, 0)` aparece após compact (linha ~640 e ~666 — o segundo é no catch, mantém 0 pois compact falhou).

**Também:** rebaixar `COMPACT_THRESHOLD_FRACTION` de `0.80` para `0.70`:
```typescript
// linha 53
const COMPACT_THRESHOLD_FRACTION = 0.70
```

**Teste:** `bun test tests/sessions/cli-session-runner.test.ts` — verificar que nenhum teste de compact quebra. Adicionar assertion: após compact com `inputTokens=80000`, `getTokenCount()` retorna `80000` (não `0`).

---

### Passo 2 — P1: Reduzir AUTO_RESUME default

**Arquivo:** `server.ts`

**Mudança:**
```typescript
// linha 210
cliMaxAutoResume: Number(process.env.DISCORD_SDK_INBOUND_CLI_AUTO_RESUME ?? '1'),
```

Alterar default de `'5'` para `'1'`.

**Também:** adicionar comentário explicativo:
```typescript
// Auto-resume após max_turns: 1 é suficiente para a maioria dos casos.
// Valores altos (ex: 5) multiplicam o custo — cada resume recarrega o histórico completo.
cliMaxAutoResume: Number(process.env.DISCORD_SDK_INBOUND_CLI_AUTO_RESUME ?? '1'),
```

**Teste:** sem mudança de comportamento observável no suite existente (valor vem de env). Verificar que o teste de `maxAutoResume` em `cli-session-runner.test.ts` continua passando.

---

### Passo 3 — P3: BRIDGE_SYSTEM_NOTE via --append-system-prompt

**Arquivo:** `src/sessions/cli-session-runner.ts` + `src/projects/project-context-resolver.ts`

**3a — Extrair a constante:**
Em `project-context-resolver.ts`, exportar `BRIDGE_SYSTEM_NOTE`:
```typescript
export const BRIDGE_SYSTEM_NOTE = [
  '## EvoNexus Discord Plus — Instruções do sistema',
  ...
].join('\n')
```

**3b — Remover do conteúdo:**
```typescript
export function prependActiveProjectBlock(content: string, resolved: ResolvedProjectContext | null): string {
  const projectBlock = activeProjectBlock(resolved)
  // BRIDGE_SYSTEM_NOTE saiu daqui — vai via --append-system-prompt no runner claude
  const blocks = [projectBlock, content].filter(Boolean)
  return blocks.join('\n\n')
}
```

**3c — Injetar no buildCliInvocation:**
Em `cli-session-runner.ts`, `buildCliInvocation`:
```typescript
export function buildCliInvocation(
  runner: SupervisedSession['launch']['runner'],
  agent: string,
  prompt: string,
  provider: string,
  model: string,
  sessionId?: string,
  toolMode: CliToolMode = 'none',
  effort?: string,
  maxTurns?: number,
): { command: string; args: string[]; stdinPrompt: string } {
  if (runner === 'claude') {
    const args = ['-p', '--model', model, '--output-format', CLI_OUTPUT_FORMAT, ...CLI_OUTPUT_FORMAT_EXTRA_ARGS]
    if (effort) args.push('--effort', effort)
    if (maxTurns) args.push('--max-turns', String(maxTurns))
    if (sessionId) args.push('--resume', sessionId)
    if (toolMode === 'none') args.push('--tools', '')
    if (toolMode === 'all') args.push('--tools', ALL_CLI_TOOLS_ARG, '--permission-mode', 'bypassPermissions', '--dangerously-skip-permissions')
    // Sistema: instrui o agente sobre o canal Discord Plus (não vai no histórico de usuário)
    args.push('--append-system-prompt', BRIDGE_SYSTEM_NOTE)
    assertNoDiscordGatewayArgs(args)
    return { command: 'claude', args, stdinPrompt: prompt }
  }
  // openclaude: mantém comportamento anterior (sem --append-system-prompt)
  // ...
}
```

**Atenção:** importar `BRIDGE_SYSTEM_NOTE` de `project-context-resolver.ts` em `cli-session-runner.ts`.

**Teste:** atualizar `gateway-dispatcher.test.ts` — o teste que verifica `env.content` contendo `'EvoNexus Discord Plus'` precisará ser ajustado: o note não aparece mais no content. Verificar que o content contém apenas o projectBlock + mensagem do usuário.

---

### Passo 4 — P2: Renovação automática pós-compact

**Arquivo:** `src/sessions/cli-session-runner.ts`

**4a — Nova constante:**
```typescript
/** Renovar sessão automaticamente se contexto pós-compact ainda superar este fraction. */
const POST_COMPACT_RENEW_THRESHOLD_FRACTION = 0.50
```

**4b — Lógica em `runAutoCompactIfNeeded`:**
Após compact bem-sucedido e notificação de conclusão, verificar se o contexto pós-compact ainda está alto:

```typescript
// Após setar token count com o valor real (Passo 1):
const postCompactTokens = compactOutput.inputTokens ?? 0
this.options.store.setTokenCount(this.supervised.key, postCompactTokens)

// Se ainda acima do threshold pós-compact → renovar sessão
const postCompactPct = Math.round((postCompactTokens / MODEL_CONTEXT_LIMIT_TOKENS) * 100)
if (postCompactTokens > MODEL_CONTEXT_LIMIT_TOKENS * POST_COMPACT_RENEW_THRESHOLD_FRACTION) {
  // Limpar session ID para forçar nova sessão na próxima invocação
  this.options.store.setSessionId(this.supervised.key, undefined)
  this.options.store.setTokenCount(this.supervised.key, 0)
  void this.options.progressSink.capture({
    type: 'reply',
    sessionKey: envelope.sessionKey,
    input: {
      content: `🔄 Contexto renovado automaticamente — sessão anterior estava muito densa após compactação (${postCompactPct}%). Iniciando sessão limpa para a próxima mensagem.`,
      messageId: envelope.messageId,
      channelId: envelope.channelId,
      guildId: envelope.guildId,
      threadId: envelope.threadId,
      userId: envelope.userId,
      username: envelope.username,
      timestamp: envelope.timestamp,
    },
  })
}
```

**Teste:** adicionar teste unitário:
- Mock compact retorna `inputTokens: 110_000` (55% de 200k > 50% threshold)
- Verificar que `store.getSessionId()` retorna `undefined` após a chamada
- Verificar que `store.getTokenCount()` retorna `0`
- Verificar que progressSink recebeu a mensagem de renovação

---

### Passo 5 — Build, testes e deploy

```bash
bun test                          # deve: 401+ pass, 0 fail
bun build server.ts --target=bun --outfile=dist/server.js
sudo systemctl restart evonexus-discord-plus.service
sudo systemctl is-active evonexus-discord-plus.service
```

**Verificação manual no Discord:**
- Enviar mensagem no tópico `1507433098810495046`
- Confirmar que rodapé `📊 X% do contexto` aparece com valor < o esperado antes do fix
- Fazer `/session renew` nesse tópico para limpar o contexto acumulado (ação manual pontual)

---

## Critérios de aceite do plano completo

- [x] `bun test`: 0 falhas
- [x] `bun build`: sem erros de tipo
- [x] Serviço ativo após restart
- [x] Default `AUTO_RESUME` = 1 visível no código (server.ts:212)
- [x] `COMPACT_THRESHOLD_FRACTION` = 0.70 no código (cli-session-runner.ts:54)
- [x] `BRIDGE_SYSTEM_NOTE` ausente do content do envelope
- [x] `BRIDGE_SYSTEM_NOTE` presente nos args do CLI (`--append-system-prompt`) (cli-session-runner.ts:95)
- [x] Após compact com tokens > 50%, session ID é limpo e usuário notificado (cli-session-runner.ts:671)

---

## Rollback

Todos os valores são constantes ou defaults de env. Rollback imediato:
- `DISCORD_SDK_INBOUND_CLI_AUTO_RESUME=5` no env → volta ao comportamento anterior
- Reverter os 3 arquivos tocados e rebuild
