---
author: claude
agent: trail-tracer
type: trace-report
date: 2026-05-13
topic: discord-openclaude-bridge-test-hang
status: converged
---

# Trace Report — Discord OpenClaude Bridge Test Hang

## Observation

A suíte de testes do repo `/home/evonexus/evo-projects/discord-openclaude-bridge` não conclui em execuções completas/por blocos e aparenta travar perto da região de progress/async. O serviço real da bridge estava rodando separadamente e não foi tocado. O repo alvo está no HEAD `33bbd3d1ff2dd79d01b36077f8868b42357b3342`, com modificação local em `tests/test_discord_openclaude_bridge.py`.

## Question Frame

Por que a suíte parece travar perto dos testes async/progress depois da correção anterior em `ProgressRunner.run_async(timeout_seconds=None)`?

## Hypothesis Table

| Rank | Hypothesis | Confidence | Evidence Strength | Why plausible |
|---|---|---|---|---|
| 1 | Fakes assíncronos adicionais não aceitam `timeout_seconds`; `_run_record` sempre passa esse kwarg, o background task falha antes de sinalizar `started`, e testes aguardam indefinidamente eventos como `runner.started.wait()` | high | strong | O teste exato `test_normal_message_acknowledges_before_background_completion` trava isolado; probe controlado mostrou `runner_started=False`, status `error`, e erro `BlockingAsyncRunner.run_async() got an unexpected keyword argument 'timeout_seconds'` |
| 2 | Os blocos iniciais parecem hang por lentidão agregada de testes SQLite/store/handler, não por travamento individual | medium | moderate | Blocos 37–48, 49–60, 81–95 e 101–121 excederam limites curtos, mas seus testes passaram isolados ou em subfaixas com limites maiores; alguns subgrupos levaram 41s, 87s, 35s |
| 3 | Caminhos reais de timeout/cancel em `OpenClaudeRunner.run_async` ficam presos em `proc.wait()`/process group | low | weak-to-moderate | Era plausível pela observação inicial, mas os testes específicos `test_async_runner_timeout_kills_process_group` e `test_async_runner_cancel_kills_process_group` passaram em grupo; não é o primeiro hang localizado |
| 4 | `drain_background_tasks()` retém uma task ativa que nunca termina por bug de cleanup em `active_tasks_by_channel` | low | weak | O helper é ponto de risco, mas o probe do suspeito mostrou `task_present=False`; o teste estava preso antes disso, em `runner.started.wait()` |

## Evidence For

- **H1:** `tests/test_discord_openclaude_bridge.py:2532` define `BlockingAsyncRunner.run_async(...)` sem `timeout_seconds`. `src/discord_openclaude_bridge.py:2959-2970` chama `self.runner.run_async(..., timeout_seconds=timeout_seconds)` sempre que o runner possui `run_async`.
- **H1:** `test_normal_message_acknowledges_before_background_completion` trava isolado com `timeout --kill-after=2s 60s python3 -m pytest -vv tests/test_discord_openclaude_bridge.py::test_normal_message_acknowledges_before_background_completion`, retornando `rc=124`.
- **H1:** Probe controlado importando o próprio teste mostrou: `runner_started=False`, `latest_status=error`, `latest_error=BlockingAsyncRunner.run_async() got an unexpected keyword argument 'timeout_seconds'`, `message_replies=[ack, erro]`. Isso explica por que `await runner.started.wait()` nunca retorna.
- **H1:** AST do arquivo de testes listou vários fakes `run_async` sem `timeout_seconds`: `BlockingAsyncRunner`, `SlowAsyncRunner`, `ProgressAsyncRunner`, `AgentMilestoneRunner`, `SensitiveErrorRunner`, `SecretTelemetryRunner`, `SecretOutputRunner`, `SlowRunner`. Apenas `FakeRunner` e `ProgressRunner` tinham o kwarg.
- **H2:** Bloco 37–48 retornou timeout com limite de 18s, mas a execução do mesmo bloco com 70s passou: `12 passed in 41.45s`.
- **H2:** Testes 81–95 passaram com `15 passed in 87.76s`; portanto timeout de 90s para grupo maior 81–100 era insuficiente para separar lentidão de hang.
- **H3:** Testes 72–80, incluindo timeout/cancel async, passaram: `9 passed in 35.11s`.
- **H4:** O helper `drain_background_tasks` é usado nos testes, mas no probe do suspeito `handler.active_tasks_by_channel` já estava limpo (`task_present=False`).

## Evidence Against / Gaps

- **H1:** Ainda não foi executada a suíte completa com os fakes corrigidos, porque a tarefa era read-only e sem edição. A hipótese explica o primeiro teste exato encontrado, mas pode haver fakes subsequentes com o mesmo problema.
- **H2:** Lentidão agregada não explica o teste isolado `test_normal_message_acknowledges_before_background_completion` expirar; portanto é fator confundidor, não causa raiz principal.
- **H3:** A hipótese de `proc.wait()` continua possível para outro bug futuro, mas perdeu força porque os testes direcionados passaram e o primeiro hang reproduzido não envolve subprocesso real.
- **H4:** Não há evidência de task viva retida nesse caso; o background task falha e limpa antes do teste observar `started`.

## Lens Application

- **Systems:** A mudança de contrato em `_run_record` adicionou `timeout_seconds` ao protocolo informal de runners. Fakes de teste não centralizados divergiram do contrato e produziram falha assíncrona fora do fluxo de espera do teste.
- **Premortem:** Se só corrigir `BlockingAsyncRunner`, os próximos testes com `SlowAsyncRunner`, `ProgressAsyncRunner`, `AgentMilestoneRunner`, runners de redaction/telemetry e `SlowRunner` podem falhar ou travar por mecanismo semelhante.
- **Science:** Os primeiros probes por bloco confundiram tempo agregado com hang. O controle foi executar testes isolados/subfaixas maiores e então um probe controlado que mediu diretamente `runner.started`, status no store e erro persistido.

## Rebuttal Round

O melhor desafio à hipótese líder é: “talvez a suíte esteja apenas lenta e não travada”. Isso é verdadeiro para vários blocos iniciais, mas não para o teste suspeito isolado: ele expirou sozinho e o probe controlado demonstrou que o evento aguardado nunca é setado porque `run_async` falha no bind de argumento antes de entrar no corpo do fake.

## Convergence / Separation

- H1 e H2 são causas distintas: H2 mascarou a busca por H1 ao gerar falsos positivos de timeout em blocos grandes.
- H3 e H4 permanecem separados e enfraquecidos para este incidente específico.
- O padrão de H1 pode afetar múltiplos testes posteriores porque há vários fakes assíncronos com a mesma assinatura defasada.

## Current Best Explanation

A suíte não trava primeiro nos testes de timeout/cancel; o primeiro hang exato localizado é `test_normal_message_acknowledges_before_background_completion`. O teste aguarda `runner.started.wait()` sem timeout. O runner usado (`BlockingAsyncRunner`) não aceita o novo kwarg `timeout_seconds`, mas `_run_record` passa esse kwarg sempre. A background task então marca a execução como erro e termina antes de chamar `self.started.set()`, enquanto o corpo do teste continua aguardando indefinidamente.

Explicação auxiliar: vários blocos anteriores pareciam travar porque a suíte é muito lenta em grupos com SQLite/store/handler; limites de 18–90s em grupos grandes geraram falsos positivos.

## Critical Unknown

Quantos testes subsequentes ainda falhariam/travariam após corrigir `BlockingAsyncRunner`, dado que vários fakes `run_async` posteriores também não aceitam `timeout_seconds`?

## Discriminating Probe

Sem alterar produção, aplicar em uma cópia/patch mínimo de teste `timeout_seconds=None` a todos os fakes `run_async` listados pela AST e rodar primeiro:

```bash
timeout --kill-after=2s 90s python3 -m pytest -vv tests/test_discord_openclaude_bridge.py::test_normal_message_acknowledges_before_background_completion tests/test_discord_openclaude_bridge.py::test_status_reports_live_progress_for_running_async_job tests/test_discord_openclaude_bridge.py::test_cancel_command_cancels_in_memory_active_task tests/test_discord_openclaude_bridge.py::test_agent_tool_progress_adds_deduplicated_reactions
```

Se passar, rodar a cauda 142–164 em blocos menores com timeout externo para verificar se o padrão foi eliminado.

## Uncertainty Notes

- Não houve edição de arquivos nem commit.
- Não houve reinício, kill ou interação com o serviço real da bridge.
- O plugin `pytest-timeout` não está instalado (`has_pytest_timeout=False`), então todos os limites usados foram externos via `timeout`.
- O primeiro erro `exit 127` nos probes iniciais foi explicado por `python` ausente; `python3` existe e foi usado nos probes posteriores.
