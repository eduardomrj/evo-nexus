---
author: claude
agent: hawk-debugger
type: bug-report
date: 2026-05-12
component: discord-openclaude-bridge-tests
severity: medium
status: fixed
---

# Bug Report — Timeout em teste de cancelamento da bridge Discord

## Symptom
O teste isolado `tests/test_discord_openclaude_bridge.py::test_cancel_command_cancels_in_memory_active_task` não concluía dentro de 90s. Após corrigir esse teste, o bloco BLOCK7.4 expôs falhas adicionais nos testes de progresso/milestones com erro de keyword argument inesperado.

## Reproduction
1. Acessar `/home/evonexus/evo-projects/discord-openclaude-bridge`.
2. Rodar o teste isolado com timeout Python: `python3 -m pytest -vv -s tests/test_discord_openclaude_bridge.py::test_cancel_command_cancels_in_memory_active_task`.
3. Antes do fix, a execução expirava no wrapper em 95s com `TIMEOUT_EXPIRED`/exit 124.
4. Depois do primeiro fix, rodar os 5 testes BLOCK7.4 revelou `unexpected keyword argument 'cwd'` em fakes adicionais.

**Frequency:** consistent
**Environment:** Linux, Python 3.12.3, pytest 8.4.2, repo `/home/evonexus/evo-projects/discord-openclaude-bridge`

## Root Cause
A implementação de produção de `BridgeHandler._run_record` passou a chamar `runner.run_async(...)` com o contrato completo incluindo `progress_callback`, `process_callback`, `cwd` e `add_dirs`.

Fakes de teste ainda implementavam a assinatura antiga e não aceitavam `cwd`/`add_dirs`:

- `tests/test_discord_openclaude_bridge.py:2417` — `SlowAsyncRunner.run_async` rejeitava kwargs novos. No teste de cancelamento, o `TypeError` acontecia antes de `self.started.set()`, deixando o teste preso em `await runner.started.wait()`.
- `tests/test_discord_openclaude_bridge.py:2480` — `ProgressAsyncRunner.run_async` rejeitava kwargs novos, fazendo a execução cair em erro e reagir com `❌`.
- `tests/test_discord_openclaude_bridge.py:2520` — `AgentMilestoneRunner.run_async` rejeitava kwargs novos, quebrando os testes de milestones.

- **Where it manifests:** `/home/evonexus/evo-projects/discord-openclaude-bridge/tests/test_discord_openclaude_bridge.py:2451`
- **Where the root cause originates:** `/home/evonexus/evo-projects/discord-openclaude-bridge/tests/test_discord_openclaude_bridge.py:2417`, `/home/evonexus/evo-projects/discord-openclaude-bridge/tests/test_discord_openclaude_bridge.py:2480`, `/home/evonexus/evo-projects/discord-openclaude-bridge/tests/test_discord_openclaude_bridge.py:2520`
- **Production contract:** `/home/evonexus/evo-projects/discord-openclaude-bridge/src/discord_openclaude_bridge.py:2645-2655`

## Hypothesis Tested
1. Hipótese inicial: `/cancel` não cancelava/aguardava a task em memória. Refutada parcialmente pela leitura de `cancel_active_execution`, que já chama `task.cancel()` e `await task` quando há task ativa.
2. Hipótese corrigida: o fake do teste de cancelamento não aceitava o contrato atual do runner, então `runner.started.set()` nunca era executado. Confirmada pelo diff de assinatura e pela passagem do teste isolado após adicionar os kwargs.
3. Hipótese de regressão BLOCK7.4: outros fakes assíncronos mantinham assinatura antiga. Confirmada pelo output de pytest com `AgentMilestoneRunner.run_async() got an unexpected keyword argument 'cwd'` e corrigida adicionando os mesmos kwargs.

## Fix
Atualizar os fakes assíncronos afetados para aceitar o contrato atual do runner:

```diff
 async def run_async(
     self,
     prompt,
     *,
     session_id=None,
     model=None,
     provider=None,
     mode=bridge.ExecutionMode.CHAT,
     progress_callback=None,
     process_callback=None,
+    cwd=None,
+    add_dirs=(),
 ):
```

**Lines changed:** 6 linhas funcionais neste bugfix (2 kwargs em 3 fakes diretamente afetados)
**Files affected:** 1 — `/home/evonexus/evo-projects/discord-openclaude-bridge/tests/test_discord_openclaude_bridge.py`

## Verification
- [x] Reproduzido antes do fix: wrapper Python expirou em 95s com exit 124 no teste isolado.
- [x] Teste isolado após fix: `1 passed, 1 warning in 6.30s`.
- [x] BLOCK7.4 após fix completo: `5 passed, 1 warning in 26.15s`.
- [x] `git diff --check`: passou sem output.

## Similar Patterns Checked
- `SlowAsyncRunner` — afetado e corrigido.
- `ProgressAsyncRunner` — afetado e corrigido.
- `AgentMilestoneRunner` — afetado e corrigido.
- O `replace_all` também alinhou fakes assíncronos similares no arquivo que já tinham `progress_callback`/`process_callback`, evitando o mesmo drift em testes próximos.

## Failed Hypotheses (3-failure circuit breaker tracking)
1. `/cancel` não cancela/aguarda a task ativa — refutada pela leitura de `cancel_active_execution`, que cancela e aguarda `active_tasks_by_channel[channel_id]`.
2. Não houve terceira tentativa. Circuit breaker não acionado.
3. Não aplicável.

## References
- Repro timeout: `python3 -m pytest -vv -s tests/test_discord_openclaude_bridge.py::test_cancel_command_cancels_in_memory_active_task` via wrapper com timeout de 95s, exit 124.
- Contrato de produção: `/home/evonexus/evo-projects/discord-openclaude-bridge/src/discord_openclaude_bridge.py:2645-2655`.
- Teste/fakes corrigidos: `/home/evonexus/evo-projects/discord-openclaude-bridge/tests/test_discord_openclaude_bridge.py`.
