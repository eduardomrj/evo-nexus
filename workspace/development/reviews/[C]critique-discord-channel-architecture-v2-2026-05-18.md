## Critique — Discord Channel Architecture v2 PRD

### VERDICT
**REVISE**

### Overall Assessment
O PRD acerta a direção: parar de tratar Discord como stdout final e mover a entrega visível para uma tool controlada. Ainda não está pronto para virar plano executável porque a Opção B depende de uma suposição não comprovada: um MCP local passado ao agente principal será suficiente para impedir vazamento por plugins/settings herdados e por subagentes. Do jeito atual, há risco real de construir uma camada nova e ainda reproduzir o mesmo erro de chunk.

### Pre-commitment Predictions
- Predicted: o PRD provavelmente confundiria “MCP tool disponível” com “Channel runtime oficial equivalente”.
  - Found: confirmado. A Opção B é descrita como “simular Channel” via MCP local (`docs/prd/discord-channel-architecture-v2.md:298-310`), mas não prova que isso replica `notifications/claude/channel` nem o isolamento do runtime oficial.
- Predicted: haveria lacuna no bloqueio de tools Discord herdadas em Agent/subagentes.
  - Found: confirmado. O PRD exige “subagentes não conseguem enviar diretamente ao Discord” (`docs/prd/discord-channel-architecture-v2.md:411-416`), mas não define mecanismo verificável.
- Predicted: critérios de aceitação seriam bons para o cenário feliz, fracos para falhas parciais/retry/cancel/restart.
  - Found: parcialmente confirmado. Há critérios para chunks, logs e restart (`docs/prd/discord-channel-architecture-v2.md:451-464`), mas faltam testes de autorização efêmera, timeout/cleanup do MCP e “nenhum envio fora da bridge” com evidência negativa.
- Predicted: haveria overengineering por migrar comandos/UX antes de validar a causa raiz.
  - Found: confirmado. Fase 5 inclui `/status`, `/last`, `/projects`, anexos, reactions e DB (`docs/prd/discord-channel-architecture-v2.md:418-430`) antes de definir um spike mínimo obrigatório que mate ou confirme a hipótese.
- Predicted: o PRD não fecharia como preservar provider alternativo sem degradar Agent/Skill/MCP.
  - Found: confirmado. O texto quer preservar OpenClaude/provider alternativo (`docs/prd/discord-channel-architecture-v2.md:182`) e Agent/Skill/MCP (`docs/prd/discord-channel-architecture-v2.md:189`), mas só registra “pode não ser fácil” (`docs/prd/discord-channel-architecture-v2.md:338-340`).

### Critical Findings
Nenhum CRITICAL. O PRD ainda está em fase de decisão técnica; os riscos são grandes, mas corrigíveis antes de implementação.

### Major Findings
[MAJOR] Opção B pode reproduzir o mesmo problema que tenta eliminar — `docs/prd/discord-channel-architecture-v2.md:298-322` e `docs/prd/discord-channel-architecture-v2.md:405` — O plano troca “stdout final” por `bridge_reply`, mas continua rodando OpenClaude como subprocesso com Agent/Skill/MCP e settings herdados. O próprio código atual só usa `--strict-mcp-config` no modo CHAT, não no modo ORACLE (`src/discord_openclaude_bridge.py:1622-1631`, `src/discord_openclaude_bridge.py:3490`), e não há deny/allowlist efetiva de tools no ORACLE (`src/discord_openclaude_bridge.py:1595-1639`). Se a origem do erro é tool/plugin Discord herdado em subagente, adicionar um MCP local não remove esse caminho. Fix: antes do plano grande, exigir spike read/write controlado que rode o cenário CPSMQ com `Agent(oath/lens)` e capture a lista real de tools disponíveis no agente principal e no subagente; o plano só avança se provar que nenhuma tool `mcp__*discord*`, channel/plugin Discord ou transporte equivalente está disponível fora de `bridge_reply`.

Self-audit: confiança HIGH; refutável por log de execução real mostrando tool inventory e ausência de qualquer transporte Discord herdado em agente/subagente. Não é preferência: é a hipótese causal central do PRD.

Realist check: pior caso realista não é só “um teste falha”; é gastar implementação em MCP local, manter o mesmo vazamento e continuar sem bridge confiável para trabalho com subagentes.

[MAJOR] “Uso obrigatório da tool” depende de prompt, não de enforcement — `docs/prd/discord-channel-architecture-v2.md:397-405` e `docs/prd/discord-channel-architecture-v2.md:474-480` — O PRD diz “Prompt forte” e fallback curto se o modelo não chamar `bridge_reply`. Isso não garante o invariante arquitetural de `docs/prd/discord-channel-architecture-v2.md:202-204`. Modelos e subagentes podem ignorar instrução, falhar antes de chamar a tool ou tentar outra tool disponível. Fix: transformar o requisito em enforcement técnico: runner não entrega `result.text` ao Discord salvo modo fallback explicitamente marcado como degradado; execução sem `bridge_reply` deve ser FAIL no teste de aceitação; tool inventory deve ser allowlistada; e o prompt deve ser complemento, não barreira.

Self-audit: confiança HIGH; refutável se OpenClaude suportar policy de tool obrigatória/channel output com bloqueio hard, mas o PRD não cita esse mecanismo. Não é preferência: “prompt como controle de segurança/arquitetura” é frágil.

Realist check: o pior caso realista é resposta “concluída” nos logs sem usuário receber nada, ou fallback reintroduzindo entrega por texto final e mascarando o bug.

[MAJOR] Falta contrato de segurança do MCP local — `docs/prd/discord-channel-architecture-v2.md:395` e `docs/prd/discord-channel-architecture-v2.md:489-495` — “endpoint/socket local seguro” e “autorização efêmera” são citados, mas sem contrato: bind address, token por execução, TTL, escopo por `chat_id`, validação de `execution_id`, replay protection, limpeza de sockets/processos órfãos e comportamento em concorrência. Como `bridge_reply` escreve no Discord, isso é superfície de escrita. Fix: antes de implementar, especificar: somente loopback ou Unix socket com permissões restritas; token randômico por execução; `execution_id` obrigatório; `chat_id` deve bater com o registro de execução no DB; token expira no fim/timeout/cancel; chamadas duplicadas devem ser idempotentes por chunk/tool-call-id; logs não podem gravar token.

Self-audit: confiança HIGH; refutável por contrato existente em outro documento não citado. Não é preferência: é controle mínimo para uma tool local que envia mensagem em canal autorizado.

Realist check: pior caso realista é outra execução/processo local reaproveitar endpoint e postar em canal errado, ou retry duplicar chunks depois de falha parcial.

[MAJOR] O menor plano de validação está soterrado por migração ampla — `docs/prd/discord-channel-architecture-v2.md:418-430` e `docs/prd/discord-channel-architecture-v2.md:522-526` — A Fase 5 quer migrar UX/comandos/anexos/logs antes de provar que a Opção B mata a causa raiz. O “próximo artefato recomendado” propõe três etapas, mas ainda mistura runner, MCP e testes sem um gate explícito de kill/continue. Fix: plano executável deve começar com um “validation spike” de 1-2 dias: MCP `bridge_reply` mínimo, sem migrar comandos; rodar cenário CPSMQ real; provar chunks longos e Agent/subagente; coletar evidência de tool inventory; decidir GO/NO-GO para Opção B. Só depois planejar comandos, anexos e UX.

Self-audit: confiança MEDIUM-HIGH; refutável se o time aceitar migração ampla por urgência operacional. Ainda assim, para o objetivo “resolver definitivamente o chunk”, o spike é o caminho de menor risco.

Realist check: pior caso realista é aumentar área de regressão e atrasar a única validação que importa: subagente + resposta longa sem erro.

[MAJOR] Critérios de aceitação não são mensuráveis o suficiente para impedir regressão — `docs/prd/discord-channel-architecture-v2.md:451-464` — “Subagentes continuam funcionando” e “Nenhuma tool Discord genérica” são bons objetivos, mas precisam de evidência observável: comando exato, log esperado, assert de payload máximo, lista de tools, contagem de chunks, IDs enviados, comportamento em falha parcial, restart e cancel. Fix: converter cada aceitação em Given/When/Then com artefato de prova: log JSONL/DB, transcript redigido, test id, comando executado e resultado esperado.

Self-audit: confiança HIGH; refutável se houver suite externa não citada. Não é preferência: sem critérios verificáveis, o bug pode ser declarado resolvido com teste manual frágil.

Realist check: pior caso realista é regressão voltar quando lens/oath usa caminho diferente do teste feliz.

### Minor Findings
[MINOR] Referências a linhas do plugin oficial estão instáveis — `docs/prd/discord-channel-architecture-v2.md:102-118` — O PRD cita `server.ts:520-599` e `455-464`, mas sem incluir o trecho ou commit/versão fixa além do cache `0.0.4`. Fix: registrar versão/commit do plugin oficial e copiar as invariantes relevantes no PRD, não depender só de line ranges locais.

[MINOR] `bridge_edit` e `bridge_react` entram cedo demais — `docs/prd/discord-channel-architecture-v2.md:223-228` — Para resolver chunk/subagente, `bridge_reply` basta. Fix: mover `bridge_react`, `bridge_edit`, fetch e attachment para follow-up após o spike.

[MINOR] “provider alternativo se possível” é ambíguo — `docs/prd/discord-channel-architecture-v2.md:329-340` — Se provider alternativo for requisito duro, não pode ficar como “se possível”. Fix: marcar como MUST para Opção B ou aceitar fallback explícito para Claude oficial no spike.

### What's Missing
- Tool inventory/provenance — precisa saber quais tools chegam ao agente principal e aos subagentes; sem isso a Opção B é tiro no escuro.
- GO/NO-GO gate da Opção B — critérios para abandonar MCP local e ir para Channel plugin real se o vazamento persistir.
- Contrato de idempotência — `bridge_reply` precisa evitar duplicação por retry/falha parcial com chave por execução/tool-call/chunk.
- Segurança do endpoint local — token, TTL, binding, escopo e limpeza não podem ficar para implementação improvisada.
- Teste de cancel/timeout — se execução for cancelada enquanto chunks estão sendo enviados, o comportamento precisa ser definido.
- Observabilidade mínima — evento “bridge_reply_called”, “chunk_send_attempt”, “chunk_sent”, “chunk_failed”, “non_bridge_output_detected” e “execution_without_bridge_reply”.
- Plano de rollback — como voltar ao bridge atual sem perder project routing/sessão se o spike falhar.

### Ambiguity Risks
- “`Manter Agent/Skill/MCP úteis, mas bloquear/remover apenas qualquer Discord transport tool que não seja bridge_reply`” — pode significar denylist por nome, allowlist global, strict MCP por execução ou configuração de plugin. Deve ser mecanismo explícito.
- “`Runner deixa de tratar result.text como resposta principal; result.text vira diagnóstico/log`” — ainda permite fallback? Se sim, quando e com qual limite? Se não, execução sem `bridge_reply` falha.
- “`endpoint/socket local seguro`” — seguro contra quem? outros processos locais, outra execução concorrente, replay, canal errado, token em log?
- “`provider alternativo se possível`” — requisito opcional ou bloqueador do projeto?
- “`validar que o erro não volta`” — precisa de número de execuções, cenário exato, comandos e logs esperados; uma execução manual não fecha.

### Multi-Perspective Notes
- **Executor:** Não implemente Fase 5 agora. O primeiro plano deve ter só: contrato `bridge_reply`, MCP mínimo, runner em modo experimental, teste CPSMQ com subagente e evidência de ausência de tool Discord genérica. Qualquer coisa além disso aumenta difusão de escopo.
- **Segurança:** `bridge_reply` é uma tool de escrita em Discord. O PRD precisa tratar como capability privilegiada com autorização por execução/canal e sem token em logs. Prompt não é controle de segurança.
- **Operação:** MCP por execução adiciona lifecycle: porta/socket, processo, cleanup, timeout, concorrência, restart e logs. Sem isso, o bridge pode ganhar falhas novas mesmo se o chunk sumir.

### Verdict Justification
**REVISE** porque a arquitetura proposta está na direção certa, mas o PRD ainda não prova que a Opção B remove o caminho causal do erro. O documento deve virar um plano executável apenas depois de adicionar um gate de validação real: subagente + resposta longa + tool inventory + nenhum Discord transport fora de `bridge_reply` + logs de chunks. Não escalo para ADVERSARIAL formal porque não há CRITICAL nem 3+ MAJOR em implementação já aprovada, mas há 5 MAJOR no PRD; a revisão deve ser tratada como bloqueante para build amplo.

Recalibração realista: o risco não é teórico. O código atual roda ORACLE sem `--strict-mcp-config` e sem `--mcp-config` no caminho principal (`src/discord_openclaude_bridge.py:1622-1631`, `src/discord_openclaude_bridge.py:3490`), então o PRD precisa provar isolamento real antes de preservar Agent/Skill/MCP.

### Próximos passos obrigatórios antes de implementar
1. Atualizar o PRD com GO/NO-GO gate para Opção B.
2. Especificar contrato de segurança/idempotência do MCP local e de `bridge_reply`.
3. Definir acceptance criteria em Given/When/Then com evidência exigida.
4. Fazer plano mínimo de validation spike, não plano de migração completa.
5. Só depois decidir se segue com Opção B ou salta para Opção A/Channel plugin real.

### Open Questions
- OpenClaude consegue listar/exportar tools efetivas por agente e por subagente em execução? Se não, como provar ausência de transporte Discord herdado?
- O provider alternativo é requisito bloqueante ou pode cair para `claude --channels` no primeiro spike?
- Subagentes recebem as tools MCP do processo pai por padrão ou apenas retornam texto ao agente principal?
- O erro `Separator is found...` vem de plugin Discord oficial herdado, de chunker interno do SDK ou de outro transport? O PRD pressupõe transporte Discord, mas ainda precisa de prova final.
