## Trace Report

### Observation
Após o merge do PR #2 de safe delivery e após uma correção local adicionando `--disallowedTools` para padrões Discord no subprocesso OpenClaude, a bridge voltou a exibir no Discord: `Erro ao executar a bridge: Separator is found, but chunk is longer than limit`.

Nos logs persistentes de 2026-05-17, após `2026-05-17T22:27Z`, houve uma execução bem-sucedida seguida de uma execução com erro:

- linha 285: `access_policy_resolved` para `483bd7b4-648d-4a41-8ce2-9f128776c100`, `tools="default"`, `permission_mode="bypassPermissions"`.
- linha 287: `execution_success` para `483bd7b4-648d-4a41-8ce2-9f128776c100`.
- linha 288: `access_policy_resolved` para `ef2c281a-21b3-445d-957d-0733cc98825d`, `tools="default"`, `permission_mode="bypassPermissions"`.
- linhas 290-291: apenas reações de ciclo de status.
- linha 292: `execution_error` para `ef2c281a-21b3-445d-957d-0733cc98825d`, `error="Separator is found, but chunk is longer than limit"`.

O banco SQLite confirma que a execução `ef2c281a-21b3-445d-957d-0733cc98825d` terminou com `status='error'`, `result=None`, `error='Separator is found, but chunk is longer than limit'`, `current_tool='Read'`, `current_agent='lens-reviewer'`, `last_event='user'`.

### Hypothesis Table
| Rank | Hypothesis | Confidence | Evidence Strength | Why plausible |
|---|---|---|---|---|
| 1 | O erro nasce dentro do subprocesso OpenClaude/SDK, antes de a bridge receber um resultado final recuperável | alta | forte | Log registra `execution_error`, não `response_delivery_error`; SQLite mostra `result=None`; código só produz essa mensagem de usuário no handler genérico de exceção quando a exceção vem de `runner.run_async(...)` ou de fluxo anterior à entrega final |
| 2 | O erro nasce na entrega final da bridge ao Discord | baixa | moderada | A string é de transporte Discord e existe código para capturar delivery errors, mas o padrão de log esperado para entrega final seria `response_delivery_error` com execução preservada como `success`, não `execution_error` |
| 3 | O erro vem de milestone/status/slash/followup fora do adaptador seguro | baixa | moderada | Milestones usam `deliver_message_text` e erros são best-effort/logados como `agent_milestone_ignored`; status pós-22:27 só envia reações; não há evento slash/followup nos logs do incidente |
| 4 | O denylist não cobriu algum nome de tool Discord ou o SDK acionou caminho Discord interno apesar do denylist | média | moderada | O prompt e o comando tentam proibir Discord; porém o incidente ocorre dentro do OpenClaude/SDK e o denylist atual cobre padrões específicos, não necessariamente todos os aliases/transportes futuros |
| 5 | `recover_openclaude_result_from_failed_stream()` falhou por stream sem evento terminal ou sem texto, mantendo o erro como falha de execução | média | moderada | A função só recupera se houver texto e `message_stop`/`result`; SQLite `result=None` é compatível com ausência de recuperação, mas faltam stdout/stderr brutos para provar a condição exata |

### Evidence For
- H1: `/home/evonexus/evo-projects-data/discord-openclaude-bridge/logs/2026-05-17.jsonl:292` registra `event="execution_error"` com a string exata. No código, `/home/evonexus/evo-projects/discord-openclaude-bridge/src/discord_openclaude_bridge.py:3577-3586` é o bloco genérico que marca execução como erro e envia `format_execution_error_response(...)`.
- H1: SQLite para `ef2c281a-21b3-445d-957d-0733cc98825d` mostra `status='error'`, `result=None`. Se a bridge tivesse recebido o resultado final e falhado só ao entregar no Discord, o caminho em `/home/evonexus/evo-projects/discord-openclaude-bridge/src/discord_openclaude_bridge.py:3505-3510` capturaria `delivery_error`, e o fluxo seguiria para sucesso controlado.
- H1: `/home/evonexus/evo-projects/discord-openclaude-bridge/src/discord_openclaude_bridge.py:1713-1718` e o trecho async equivalente tratam retorno não-zero do OpenClaude: tentam `recover_openclaude_result_from_failed_stream(...)`; se não recuperar, levantam `RuntimeError(...)`.
- H1: `/home/evonexus/evo-projects/discord-openclaude-bridge/src/discord_openclaude_bridge.py:1524-1530` formata exceção não técnica como `Erro ao executar a bridge: {safe_error}`, exatamente o texto visto pelo usuário.
- H2: `/home/evonexus/evo-projects/discord-openclaude-bridge/src/discord_openclaude_bridge.py:2333-2382` tem caminho de envio Discord e pode levantar erro de chunk quando o transporte real rejeita payload.
- H2: `/home/evonexus/evo-projects/discord-openclaude-bridge/tests/test_discord_openclaude_bridge.py:1893-1917` testa explicitamente erro de entrega com `Separator is found...`.
- H3: `/home/evonexus/evo-projects/discord-openclaude-bridge/src/discord_openclaude_bridge.py:3781-3809` mostra milestones usando `deliver_message_text(...)` e ignorando erro em modo best-effort.
- H4: `/home/evonexus/evo-projects/discord-openclaude-bridge/src/discord_openclaude_bridge.py:181` define `DISCORD_TRANSPORT_TOOL_DENYLIST = "mcp__plugin_discord_discord__*,mcp__discord__*,discord-*"`; `/home/evonexus/evo-projects/discord-openclaude-bridge/src/discord_openclaude_bridge.py:1621` injeta isso no comando.
- H5: `/home/evonexus/evo-projects/discord-openclaude-bridge/src/discord_openclaude_bridge.py:2139-2150` só recupera stream falho quando `contains_discord_chunk_limit_error(detail)`, `result.text.strip()` e `has_terminal_assistant_event(...)` são verdadeiros.

### Evidence Against / Gaps
- H1: não temos stdout/stderr bruto do subprocesso para a execução `ef2c281a-21b3-445d-957d-0733cc98825d`; portanto não dá para afirmar se foi uma tool Discord específica, uma falha interna de renderer/chunker do SDK, ou uma stream parcial sem terminal event.
- H2: contra forte: o log pós-22:27 não contém `response_delivery_error`. O teste em `/home/evonexus/evo-projects/discord-openclaude-bridge/tests/test_discord_openclaude_bridge.py:1893-1917` documenta que erro de chunk na entrega final preserva `ExecutionStatus.SUCCESS` e grava `response_delivery_error`, diferente do observado.
- H3: contra forte: status updates no incidente são apenas `execution_status_cycle_reaction_sent` nas linhas 290-291; milestones são best-effort e seriam logados como `agent_milestone_ignored`, não como `execution_error`.
- H4: lacuna: o banco mostra `current_tool='Read'`, não uma tool Discord no último progresso persistido. Isso não elimina uma tool Discord não persistida, mas enfraquece a hipótese de evidência direta por progress tracking.
- H5: lacuna: sem linhas de stdout do OpenClaude, não sabemos se havia `message_stop`, evento `result` ou texto parcial suficiente para recuperação.

### Rebuttal Round
O melhor desafio à H1 é: a string `Separator is found, but chunk is longer than limit` é semanticamente um erro de chunking Discord, então poderia ser a própria bridge ao entregar uma mensagem. Essa alternativa falha em duas previsões distintivas: primeiro, o código de entrega final captura chunk-limit em `/home/evonexus/evo-projects/discord-openclaude-bridge/src/discord_openclaude_bridge.py:3505-3510`; segundo, o teste de regressão em `/home/evonexus/evo-projects/discord-openclaude-bridge/tests/test_discord_openclaude_bridge.py:1893-1917` fixa que esse caso vira `response_delivery_error` e mantém a execução como `success`. O incidente real virou `execution_error` com `result=None`. Logo, a hipótese de entrega final precisa de suposições extras: que houve outro caminho de envio não coberto e ainda assim formatado como erro principal. A evidência observada favorece falha anterior à entrega final.

### Convergence / Separation
H1, H4 e H5 convergem para o mesmo domínio: falha no subprocesso OpenClaude/SDK antes da bridge ter um `OpenClaudeResult` completo. Elas permanecem separadas quanto ao mecanismo:

- H4: causa imediata seria uma tool Discord não bloqueada ou invocação por nome não coberto.
- H5: causa imediata seria recuperação insuficiente após o subprocesso falhar com texto parcial.
- H1: categoria mais ampla: erro de execução do subprocesso, não transporte final da bridge.

H2 e H3 ficam separados e down-rankados porque predizem logs e status diferentes dos observados.

### Current Best Explanation
A causa raiz provável do incidente recorrente pós-22:27 é: o erro ainda está saindo do subprocesso OpenClaude/SDK, não da entrega final da bridge. A bridge recebe/levanta uma exceção com `Separator is found, but chunk is longer than limit`, não consegue recuperá-la como `OpenClaudeResult`, marca a execução como `error` e envia ao usuário a mensagem genérica `Erro ao executar a bridge: ...`.

As duas correções anteriores foram insuficientes por motivos diferentes:

1. O PR #2 de safe delivery resolveu a fronteira de saída da bridge para Discord, mas não elimina erros que nascem antes da bridge receber o texto final. A evidência do incidente aponta exatamente para esse domínio: `execution_error`, `result=None`, sem `response_delivery_error`.
2. A correção local com `--disallowedTools` reduziu a chance de o subprocesso chamar ferramentas Discord por nomes conhecidos, mas não transforma erro de chunk interno do OpenClaude/SDK em resultado recuperável, nem prova cobertura completa de todos os aliases/tool names. O denylist atual é necessário, mas não suficiente como fronteira dura se o SDK ainda expõe outro nome, se há caminho interno de delivery, ou se a falha acontece no streaming/chunking interno sem tool registrada.

Correção definitiva proposta, em ordem de força:

1. Fortalecer a fronteira do subprocesso: executar OpenClaude com MCP config filtrado para remover completamente servidores/tools Discord do subprocesso quando a origem for a bridge Discord, não apenas `--disallowedTools`. Isso reduz a dependência de nomes e aliases.
2. Persistir diagnóstico mínimo de falha de subprocesso: returncode, stderr redigido, último tipo de evento de stream, presença/ausência de `message_stop`, tamanho de stdout, e tools anunciadas no init com redaction. Hoje a investigação fica parcialmente cega.
3. Fortalecer recuperação: quando `contains_discord_chunk_limit_error(detail)` for verdadeiro e houver texto parcial substancial, registrar por que não recuperou (`no_text`, `no_terminal_event`, `parse_error`) e considerar recuperação controlada se o stream já tiver uma resposta final suficientemente formada, sem expor payload técnico.
4. Tratar essa string como erro técnico de OpenClaude quando vier do subprocesso, evitando mostrá-la literalmente ao usuário. A resposta ao usuário deveria ser a mensagem segura já usada para erro técnico de sessão/OpenClaude, não `Erro ao executar a bridge: Separator...`.

### Critical Unknown
O fato faltante mais responsável pela incerteza é o stdout/stderr bruto redigido da execução `ef2c281a-21b3-445d-957d-0733cc98825d`: ele diria se houve tool Discord anunciada/invocada, se houve `message_stop`, e por que `recover_openclaude_result_from_failed_stream()` retornou `None`.

### Discriminating Probe
Rodar uma reprodução controlada read-only com fake subprocess/fixture que simule a execução `ef2c281a-21b3-445d-957d-0733cc98825d` em três variantes e verificar o evento final:

1. stderr contém `Separator is found...`, stdout contém texto + `message_stop` → deve virar `success` recuperado.
2. stderr contém `Separator is found...`, stdout contém texto sem `message_stop` → deve registrar motivo `no_terminal_event` e responder erro técnico seguro.
3. stderr/init anuncia uma tool Discord fora dos padrões `mcp__plugin_discord_discord__*`, `mcp__discord__*`, `discord-*` → o teste deve falhar até o MCP config filtrado remover a tool da origem.

O probe discrimina entre falha de denylist/tool exposure e falha de recuperação de stream.

### Uncertainty Notes
- Não foi encontrado evento pós-22:27 que prove entrega final da bridge como origem.
- Não foi encontrado evento pós-22:27 que prove milestone/status/slash/followup como origem.
- A hipótese de tool Discord não coberta permanece plausível, mas não comprovada; o último progresso persistido aponta `current_tool='Read'` e `current_agent='lens-reviewer'`.
- A investigação é forte para localizar o domínio da falha: subprocesso OpenClaude/SDK antes da entrega final. Ela é menos forte para identificar o mecanismo interno exato sem stdout/stderr redigidos.
