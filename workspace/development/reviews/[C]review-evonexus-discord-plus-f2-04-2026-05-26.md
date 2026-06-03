---
author: claude
agent: lens-reviewer
type: code-review
date: 2026-05-26
target: evonexus-discord-plus F2-04
verdict: REQUEST_CHANGES
---

# Code Review — evonexus-discord-plus F2-04

## Summary
**Files reviewed:** 3
**Total issues:** 2

### By Severity
- **CRITICAL:** 0 (must fix)
- **HIGH:** 1 (should fix)
- **MEDIUM:** 1 (consider fixing)
- **LOW:** 0 (optional)

## Stage 1 — Spec Compliance

| Requirement | Status | Notes |
|---|---|---|
| Definir campos permitidos: timestamp, action/command, guild id, channel id, thread id, user id, allowed, reason code e matched rule seguro | ✅ MET | `AuthorizationLogEntry` limita a estrutura a esses campos em `src/auth/runtime-adapter.ts:14-24`; os testes validam allow/deny sem request/message. |
| Proibir logs de token, conteúdo completo da mensagem, prompt completo, secrets/env e stack trace com dados sensíveis | ✅ MET | `logAuthorizationDecision()` não serializa `message`, `request`, env, stack ou conteúdo; teste de deny valida ausência de `request-secret-1`, `mentioned`, `token`, `prompt`, `stack`. |
| Implementar logger simples do v1 | ⚠️ PARTIAL | O logger é simples, mas escreve em `stdout`, que neste servidor é o transporte MCP via `StdioServerTransport`; isso não preserva o comportamento oficial do plugin. |
| Garantir logs para allow e deny | ✅ MET | Chamadas em `authorizeRuntimeOperation`, `authorizeRuntimeTool` para tool desconhecida e `authorizeRuntimePermissionResponse`; testes cobrem allow e deny. |
| Adicionar testes ou smoke demonstrando os dois casos | ✅ MET | `tests/auth/runtime-adapter.test.ts` cobre allow, deny e emissão de linha. |
| Documentar que JSONL operacional completo fica no backlog, fora do v1 | ❌ MISSING | Nenhum arquivo de plano/doc foi atualizado; o teste inclusive chama a saída de “JSONL”, mas não documenta que persistência JSONL/retention está fora do v1. |
| Diff mínimo | ✅ MET | Mudança pequena e concentrada: `server.ts` só injeta logger; adapter adiciona sink tipado; testes adicionam cobertura direta. |
| Preservar comportamento do plugin oficial | ❌ MISSING | Logs em `stdout` introduzem frames não-MCP no mesmo canal usado pelo plugin oficial. |
| Não misturar persistência JSONL/retention | ✅ MET | Não há escrita em arquivo, retention ou rotação; a alteração não adiciona persistência operacional. |

## Stage 2 — Code Quality

### Issues Found

#### [HIGH] Logger escreve em stdout e corrompe o transporte MCP stdio
- **File:** `/home/evonexus/evo-projects/evonexus-discord-plus/src/auth/runtime-adapter.ts:143`
- **Evidence:** `/home/evonexus/evo-projects/evonexus-discord-plus/server.ts:762` conecta o servidor com `new StdioServerTransport()`, portanto `stdout` é canal de protocolo MCP. A implementação de `stdoutAuthorizationLogger` faz `process.stdout.write(JSON.stringify(entry) + '\n')`, e `server.ts:243`/`server.ts:266` injeta esse logger no fluxo runtime.
- **Issue:** qualquer decisão de autorização passa a emitir uma linha JSON “solta” no mesmo stream usado pelo MCP. Isso quebra a compatibilidade com o plugin oficial, que espera mensagens MCP em stdout, não logs operacionais.
- **Why it matters:** pode causar falhas intermitentes ou imediatas no cliente MCP, especialmente em operações normais como `reply`, `fetch_messages` e respostas de permissão. Também viola o requisito explícito de preservar o comportamento do plugin oficial.
- **Fix:** não usar `stdout` no runtime MCP. Direcione logs para `stderr` ou para um sink injetável controlado pelo host que não compartilhe o transporte MCP. Se o destino v1 for stdout por decisão explícita do usuário, ele precisa ser incompatível com `StdioServerTransport` ou condicionado a um modo fora do plugin stdio.

#### [MEDIUM] Falta cobertura contra regressão do contrato stdio do plugin oficial
- **File:** `/home/evonexus/evo-projects/evonexus-discord-plus/tests/auth/runtime-adapter.test.ts:559`
- **Issue:** o teste novo valida que o logger escreve uma linha em stdout, mas não existe teste/guarda garantindo que o servidor MCP não emita logs não-MCP em stdout quando roda com `StdioServerTransport`.
- **Why it matters:** a suíte passa mesmo com a regressão mais importante para integração oficial: poluição do stream MCP. Isso incentiva a implementação incompatível em vez de capturar o contrato real.
- **Fix:** trocar a expectativa para um sink seguro (`stderr` ou logger injetado) e adicionar teste que falhe se o logger padrão do runtime MCP escrever em `process.stdout`.

## Security Checklist
- [x] No hardcoded secrets
- [x] Inputs sanitized / não há serialização de conteúdo do usuário no log
- [x] Injection prevented / sem execução dinâmica ou interpolação em shell
- [x] XSS prevented / não aplicável a UI neste diff
- [x] Auth enforced / autorização continua fail-closed; allow/deny passam pelo policy engine
- [x] Sensitive data redaction / campos sensíveis não são logados pelo adapter

## Code Quality Checklist
- [x] Functions < 50 lines
- [x] Cyclomatic complexity < 10
- [x] No deeply nested code (> 4 levels)
- [x] No duplicate logic
- [x] Clear, descriptive naming
- [x] Diff focused/minimal
- [ ] Preserves runtime integration contract (`stdout` reservado ao MCP stdio)

## Positive Observations
- O formato do log é tipado e allowlisted, o que reduz risco de vazar prompt, token, request payload ou stack trace por acidente.
- A injeção opcional de `authorizationLogger` mantém o adapter testável e evita acoplamento direto à policy engine.
- Os testes novos cobrem allow e deny de forma direta e verificam que `message`/`request` não entram no log.

## Recommendation
**REQUEST_CHANGES**

A implementação é pequena e bem isolada, mas o logger em `stdout` quebra o contrato do plugin MCP oficial; precisa mover a emissão para um canal seguro antes de aprovação.

## Follow-ups
- [ ] Substituir `stdoutAuthorizationLogger` por sink compatível com `StdioServerTransport` (`stderr` ou sink injetável fora de stdout).
- [ ] Ajustar testes para cobrir que logs operacionais não poluem stdout no runtime MCP.
- [ ] Registrar explicitamente no artefato F2-04 que persistência JSONL operacional e retention ficam fora do v1.
