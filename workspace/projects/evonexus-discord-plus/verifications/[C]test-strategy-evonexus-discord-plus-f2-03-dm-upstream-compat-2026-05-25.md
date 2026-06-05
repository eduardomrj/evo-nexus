---
author: claude
agent: grid-tester
type: test-strategy
date: 2026-05-25
component: evonexus-discord-plus-f2-03-dm-upstream-compat
---

# Test Strategy — evonexus-discord-plus F2-03 DM upstream compat

## Test Report

### Summary
- Coverage: não medido → não medido
- Test health: red
- Pyramid balance: unit 100% / integration 0% / e2e 0%

### Tests Written
- `/home/evonexus/evo-projects/evonexus-discord-plus/tests/auth/runtime-adapter.test.ts` — 5 testes cobrindo compatibilidade DM upstream, negação de DM não allowlisted, negação de `permission.respond` sem contexto, não-regressão guild/channel e uso do caminho central de autorização.

### Coverage Gaps
- `/home/evonexus/evo-projects/evonexus-discord-plus/src/auth/authorization-service.ts:57-68` — fluxo atual exige guild/channel antes de resolver usuário em DM; não atende o comportamento esperado para DM allowlisted — Risk: high.
- `/home/evonexus/evo-projects/evonexus-discord-plus/src/auth/legacy-access-adapter.ts:20-58` — policy legada retorna `null` quando não há guild, impedindo decisão de perfil para DM puro — Risk: high.

### Flaky Tests Fixed
- Nenhum flake corrigido; a falha atual é determinística.

### TDD Cycles
1. RED: `autoriza message.reply em DM allowlisted sem canal de grupo` → falhou como esperado (`deny`/`policy_missing`).
2. RED: `nega message.reply em DM não allowlisted sem canal de grupo` → expôs que o caminho ainda nega por `policy_missing`, antes de avaliar allowlist.
3. Guard rails adicionados: `permission.respond` sem contexto continua negando; guild/channel fora de DM continuam exigidos; adapter chama `authorize` central.

### Verification
- `bun test tests/auth/runtime-adapter.test.ts` → red: 13 passed, 2 failed, 0 flaky observed.
- `bun test` → red: 41 passed, 2 failed, 43 total.
- Multiple runs: não executado porque a suíte está red por falha determinística de implementação.

### Recommendations
- Handoff para `@bolt-executor`: implementar o menor ajuste no caminho central para permitir `message.reply` em DM quando o usuário está em `allowFrom`, sem relaxar `permission.respond` nem guild/channel em recursos não-DM.
- Depois do fix, rodar `bun test` e um flake simples de 3 a 5 execuções do arquivo `/home/evonexus/evo-projects/evonexus-discord-plus/tests/auth/runtime-adapter.test.ts`.
