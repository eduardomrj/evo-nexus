---
author: claude
agent: hawk-debugger
type: bug-report
date: 2026-06-01
component: evonexus-discord-plus-session-supervisor
severity: high
status: fixed
---

# Bug Report — Discord Plus usa runner antigo após mudança de modelo

## Symptom
No Discord Plus, `/model current` no tópico `1504105580501926049` retornava `openai/gpt5.5`, mas o smoke real após commit `f455f76` e restart ainda criou processo filho `claude` com `cwd=/home/evonexus/evo-projects/cpsmq`.

Esperado: provider `openai` deve usar runner `openclaude`; `claude` deve ser usado apenas para provider `anthropic`.

## Reproduction
1. Criar o runtime inbound em modo CLI com preferência inicial do tópico para provider `anthropic`.
2. Despachar uma mensagem para criar a sessão inicial; o spawn esperado é `claude`.
3. Atualizar o store persistido do mesmo escopo de thread para `openai/gpt5.5`.
4. Resetar/reiniciar a sessão pelo `SessionSupervisor` e despachar nova mensagem.
5. Antes da correção persistente, o runtime ainda podia usar o snapshot antigo e lançar `claude`; depois da correção lança `openclaude`.

**Frequency:** consistente quando o runtime inbound é criado antes da mudança de preferência e mantém um snapshot antigo do store.
**Environment:** repo `/home/evonexus/evo-projects/evonexus-discord-plus`, Bun `v1.3.12`, engine CLI.

## Root Cause
O fix anterior ensinou o `SessionSupervisor` a aceitar `ModelStoreService` e reler o store em `createSession`/`restartLocked`, mas `createSdkInboundRuntime()` ainda convertia `options.modelStore` para snapshot no startup:

```ts
const modelStore = 'read' in options.modelStore ? options.modelStore.read() : options.modelStore
```

Com isso, `/model current` podia ler o store fresco, enquanto o caminho `SessionSupervisor -> sdk-inbound-runtime -> CliSessionRunner` continuava resolvendo `launch.runner` com o snapshot antigo entregue pelo runtime. O fallback legacy não precisava estar envolvido para reproduzir: o próprio runtime CLI já conseguia divergir.

- **Where it manifests:** `/home/evonexus/evo-projects/evonexus-discord-plus/src/sessions/cli-session-runner.ts:42-69` lança `claude` ou `openclaude` conforme `session.launch.runner`.
- **Where the root cause originates:** `/home/evonexus/evo-projects/evonexus-discord-plus/src/sessions/sdk-inbound-runtime.ts:41-63` congelava o store antes de construir o supervisor.
- **Scope observed:** thread `1504105580501926049`, cwd `/home/evonexus/evo-projects/cpsmq`, modelo esperado `openai/gpt5.5`.

## Hypothesis Tested
1. Allowlist/launcher resolveriam `openai/gpt5.5` como `claude` — disproved por leitura de `/home/evonexus/evo-projects-data/evonexus-discord-plus/model-allowlist.json` e pelos testes existentes de resolver/launcher.
2. `CliSessionRunner` ignoraria `launch.runner` — disproved por `/home/evonexus/evo-projects/evonexus-discord-plus/src/sessions/cli-session-runner.ts:42-69`; o comando vem diretamente do runner.
3. `sdk-inbound-runtime` ainda congelaria `modelStore` antes do supervisor — proved por código e pelo teste novo que muda o store após criação do runtime, faz reset e valida spawn `openclaude`.

## Fix
Mudança mínima: passar o `ModelStoreService` vivo para o `SessionSupervisor`, em vez de converter para snapshot no runtime. O teste adiciona injeção de `cliSpawn` para capturar o comando real sem executar CLI.

```diff
-  const modelStore = 'read' in options.modelStore ? options.modelStore.read() : options.modelStore
+  const modelStore = options.modelStore
```

Também foi exposto `cliSpawn` apenas para teste controlado do runtime CLI.

**Lines changed:** 4 em código, 76 em teste.
**Files affected:** 2.

## Verification
- [x] `cd /home/evonexus/evo-projects/evonexus-discord-plus && bun test tests/sessions/sdk-inbound-runtime.test.ts` — 8 pass, 0 fail.
- [x] `cd /home/evonexus/evo-projects/evonexus-discord-plus && bun test` — 268 pass, 1 skip, 0 fail.
- [x] `git -C /home/evonexus/evo-projects/evonexus-discord-plus diff --check` — sem saída.

## Similar Patterns Checked
- `/home/evonexus/evo-projects/evonexus-discord-plus/src/sessions/session-supervisor.ts` — clean; já relê store via `currentStore()` em criação/restart.
- `/home/evonexus/evo-projects/evonexus-discord-plus/src/sessions/openclaude-session-launcher.ts` — clean; `openai` recebe runner da allowlist, fallback padrão é `openclaude`.
- `/home/evonexus/evo-projects/evonexus-discord-plus/src/sessions/cli-session-runner.ts` — clean; respeita `launch.runner` e só usa command `claude` quando runner é `claude`.
- `/home/evonexus/evo-projects/evonexus-discord-plus/server.ts` — `/model current` lê `modelStore.read()`, coerente com o store vivo após a correção.

## Failed Hypotheses (3-failure circuit breaker tracking)
1. Allowlist/launcher errado — disproved por configuração e testes existentes.
2. Runner CLI ignorando launch — disproved por leitura direta do runner.
3. Nenhuma terceira hipótese necessária; hipótese 3 confirmou a causa raiz.

## References
- Observação reportada: `/model current` no tópico `1504105580501926049` = `openai/gpt5.5`; processo filho observado = `claude` com cwd `/home/evonexus/evo-projects/cpsmq`.
- Arquivos alterados: `/home/evonexus/evo-projects/evonexus-discord-plus/src/sessions/sdk-inbound-runtime.ts`, `/home/evonexus/evo-projects/evonexus-discord-plus/tests/sessions/sdk-inbound-runtime.test.ts`.
- Estado de modelos: `/home/evonexus/evo-projects-data/evonexus-discord-plus/models.json`.
- Allowlist: `/home/evonexus/evo-projects-data/evonexus-discord-plus/model-allowlist.json`.
