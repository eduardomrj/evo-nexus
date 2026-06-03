---
author: claude
agent: trail-tracer
type: trace-report
date: 2026-05-17
topic: discord-chunk-limit-error
status: converged
---

# Trace Report — Discord chunk limit error

## Observation
Erro recorrente observado no Discord/OpenClaude Bridge: `Separator is found, but chunk is longer than limit`. O incidente aparece em contexto de resposta do bridge para Discord e já há código/testes específicos tentando recuperar ou contornar essa assinatura.

## Question Frame
Por que o bridge ainda expõe ou registra `Separator is found, but chunk is longer than limit` apesar de existir split de mensagens longas e retry com chunks menores?

## Hypothesis Table
| Rank | Hypothesis | Confidence | Evidence Strength | Why plausible |
|---|---|---|---|---|
| 1 | O erro é produzido dentro do OpenClaude/SDK Discord antes da resposta final do bridge, por uso de tool Discord pela própria sessão; o bridge recupera stdout parcial quando possível, mas não elimina a causa | high | strong | O runner usa `--include-partial-messages`, recupera stream falho contendo essa string, e o prompt tenta proibir tools Discord mas o erro/testes indicam ferramentas Discord no payload técnico |
| 2 | `send_response`/fallback antigo para `channel.send` reintroduzia o mesmo payload bruto e repetia o erro; mudança atual propaga para `reply_in_chunks` reduzir chunks | medium-high | strong | Diff mostra remoção do fallback por chunk-limit em `send_response`, e testes novos garantem propagação + retry sem `channel.send` |
| 3 | O splitter local gera chunk maior que o limite Discord | low | moderate | Testes cobrem sem separadores, separador após limite, linha/palavra maior que limite e preservação, todos exigindo `len(chunk) <= limit` |
| 4 | Caminhos de comando/status bypassam `reply_in_chunks` e podem disparar limite em respostas próprias longas | medium | moderate | `/help`, `/status`, `/last`, `/projects`, erros de anexo e milestones chamam `send_response` direto; muitos são curtos, mas `/last`/`/projects` podem crescer |
| 5 | Fallback de erro reintroduz payload bruto técnico grande na resposta ao usuário | medium-low | moderate | Diff adiciona sanitização de erro técnico; antes era plausível, agora mitigado para `OpenClaude failed: evento técnico omitido` |

## Evidence For
- **H1:** `/home/evonexus/evo-projects/discord-openclaude-bridge/src/discord_openclaude_bridge.py:1611-1617` adiciona `--output-format stream-json`, `--verbose`, `--include-partial-messages`. Isso torna possível receber texto parcial mesmo quando o processo falha depois.
- **H1:** `/home/evonexus/evo-projects/discord-openclaude-bridge/src/discord_openclaude_bridge.py:1679-1684` e `:1793-1799` chamam `recover_openclaude_result_from_failed_stream(..., detail)` antes de levantar `OpenClaude failed`. O erro nasce no processo OpenClaude, não necessariamente no envio final do bridge.
- **H1:** `/home/evonexus/evo-projects/discord-openclaude-bridge/src/discord_openclaude_bridge.py:2105-2116` só recupera quando `detail` contém exatamente `Separator is found...` e existe texto + evento terminal. Isso é assinatura de falha do stream de OpenClaude, não do splitter local.
- **H1:** `/home/evonexus/evo-projects/discord-openclaude-bridge/tests/test_discord_openclaude_bridge.py:1244-1266` confirma o caso: stream parcial com `message_stop` + detail `Separator is found...` vira resultado recuperado.
- **H1:** `/home/evonexus/evo-projects/discord-openclaude-bridge/src/discord_openclaude_bridge.py:3751-3755` instrui o agente: “Não tente enviar respostas via tool Discord; apenas retorne o texto final para a bridge responder.” A presença dessa instrução só é necessária porque há risco real de a sessão usar tool Discord.
- **H1:** `/home/evonexus/evo-projects/discord-openclaude-bridge/tests/test_discord_openclaude_bridge.py:2117-2144` simula erro técnico `OpenClaude failed` com `tools: ["Read", "mcp__plugin_discord_discord__reply"]`, indicando que payloads técnicos com tool Discord já foram causa observada/esperada.
- **H2:** `/home/evonexus/evo-projects/discord-openclaude-bridge/src/discord_openclaude_bridge.py:2298-2304` agora só faz fallback para `channel.send` em erro de system message; não faz fallback para erro de chunk.
- **H2:** Diff atual mostra a troca: antes `if is_system_message_reply_error(exc) or is_discord_chunk_limit_error(exc): return await message.channel.send(content)`, agora só system-message. Isso evita mandar o mesmo conteúdo bruto novamente por outro método.
- **H2:** `/home/evonexus/evo-projects/discord-openclaude-bridge/tests/test_discord_openclaude_bridge.py:1855-1862` exige que `send_response` propague o erro chunk-limit sem mandar `channel.send`.
- **H2:** `/home/evonexus/evo-projects/discord-openclaude-bridge/tests/test_discord_openclaude_bridge.py:3522-3540` e `:3543-3560` validam que `reply_in_chunks` reduz de 1501 para 1000/501 após erro de transporte.
- **H3:** `/home/evonexus/evo-projects/discord-openclaude-bridge/tests/test_discord_openclaude_bridge.py:3452-3458` afirma invariantes: chunks existem, não vazios, `len(chunk) <= limit`, concatenação preserva conteúdo.
- **H3:** `/home/evonexus/evo-projects/discord-openclaude-bridge/tests/test_discord_openclaude_bridge.py:3462-3505` cobre textos sem separadores, separador perto/depois do limite, linha/palavra maior que limite, muitos espaços/newlines.
- **H4:** `/home/evonexus/evo-projects/discord-openclaude-bridge/src/discord_openclaude_bridge.py:3149-3162` usa `send_response` direto para acesso negado, `/help`, `/status`, `/last`.
- **H4:** `/home/evonexus/evo-projects/discord-openclaude-bridge/src/discord_openclaude_bridge.py:3675-3677` milestones também usam `send_response` direto, sem `reply_in_chunks`, embora erros sejam tratados como best-effort.
- **H5:** Diff atual adiciona `/home/evonexus/evo-projects/discord-openclaude-bridge/src/discord_openclaude_bridge.py:1440-1490`, que omite eventos técnicos e troca a resposta por mensagem curta em erro técnico OpenClaude.

## Evidence Against / Gaps
- **H1:** Não li logs reais de produção nesta investigação; a inferência vem de código/testes e da assinatura de erro. Falta correlacionar evento real com `OpenClaude failed` versus `response_delivery_error`.
- **H2:** A mudança atual parece correta, mas não prova que o incidente recorrente remanescente vem desse caminho; pode explicar incidentes anteriores ou parte deles.
- **H3:** Não há leitura da implementação de `split_discord_message` nesta etapa, mas os testes são fortes contra essa hipótese. Se testes não rodam no deploy ou código implantado difere da branch, a hipótese reabre.
- **H4:** Evidência é estrutural, não de reprodução. A maioria das respostas diretas parece curta; hipótese só ganha força se logs apontarem comando/status/projetos/last como origem.
- **H5:** A mitigação está em diff não necessariamente implantado. Se produção roda versão anterior, esse caminho ainda pode expor payload bruto.

## Lens Application
- **Systems:** há duas fronteiras independentes de envio Discord: envio pelo bridge (`message.reply/channel.send`) e envio pela sessão OpenClaude via tool Discord/MCP. Split local só protege a primeira fronteira.
- **Premortem:** mesmo com splitter perfeito, o incidente persiste se o agente usar uma tool Discord antes de retornar resultado, ou se comandos internos usarem `send_response` direto com payload longo.
- **Science:** o discriminante é o log: `OpenClaude failed`/stream recovery aponta origem no processo OpenClaude; `response_delivery_error` aponta origem no envio final do bridge; comando sem `execution_id` aponta bypass de comando/milestone.

## Rebuttal Round
A melhor objeção contra H1 é H2: se o erro vinha apenas de `send_response` local tentando `reply` e depois `channel.send` com o mesmo conteúdo, o problema seria puramente no transporte final. Porém H1 outranka H2 porque o código possui recuperação explícita de `Separator is found...` no stderr/stdout do processo OpenClaude antes de qualquer entrega final do bridge (`run_async`), e o prompt/teste mencionam tool Discord dentro da sessão. Isso é uma fronteira que `reply_in_chunks` não controla.

## Convergence / Separation
- H1 e H2 não colapsam: H1 é erro antes/de dentro do OpenClaude; H2 é entrega final do bridge.
- H3 é praticamente separado e down-ranked: splitter local tem invariantes testados.
- H4 é uma variante de bypass de entrega local, separada de H1, mas provavelmente secundária.
- H5 é mitigação de exposição/observabilidade, não causa raiz primária.

## Current Best Explanation
A explicação mais provável é dupla, com causa primária em **uso de caminho Discord fora do splitter principal**. O caso mais forte é o OpenClaude/SDK Discord tentando enviar ou processar conteúdo por uma tool Discord própria antes da bridge receber o texto final; quando isso falha com `Separator is found, but chunk is longer than limit`, o runner só consegue recuperar se o stream já teve texto e evento terminal. Em paralelo, havia/estava sendo corrigido um bug local: `send_response` fazia fallback para `channel.send` no mesmo erro, preservando o payload problemático e impedindo `reply_in_chunks` de reduzir o tamanho.

Recomendação definitiva: tratar `reply_in_chunks` como único caminho permitido para qualquer conteúdo potencialmente longo gerado pela bridge e, principalmente, bloquear/remover tools Discord do subprocesso OpenClaude nesse fluxo ou validar nos logs que nenhuma `mcp__plugin_discord_discord__reply` entra no toolset da sessão. A correção de `send_response` no diff atual é necessária, mas não suficiente se a sessão ainda puder chamar tool Discord.

## Critical Unknown
Nos incidentes reais, a linha de log imediatamente anterior ao erro é `OpenClaude failed...` no runner ou `response_delivery_error` na entrega final do bridge?

## Discriminating Probe
Rodar uma reprodução controlada com logging/assertion de toolset e de ponto de falha: enviar uma resposta > 2000 caracteres em modo `/chat` com `--tools "" --strict-mcp-config` e depois repetir em modo que inclua tool Discord. O probe deve registrar se o erro aparece antes de `_execute_record_background` chamar `reply_in_chunks` ou dentro de `response_delivery_error`. Se aparecer antes, H1 confirmado; se aparecer só em `response_delivery_error`, H2/H4 confirmado.

## Uncertainty Notes
Não houve execução de testes nem leitura de logs de produção, por solicitação de investigação read-only. A confiança alta de H1 vem de artefatos primários de código/teste, não de reprodução direta do incidente real.
