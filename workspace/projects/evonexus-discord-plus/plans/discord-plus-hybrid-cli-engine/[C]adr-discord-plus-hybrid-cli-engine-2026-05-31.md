---
author: apex-architect
agent: apex-architect
type: architecture-decision
date: 2026-05-31
topic: discord-plus-hybrid-cli-engine
status: proposed
---

# ADR — Discord Plus Hybrid CLI Engine

## Status

Proposta. A decisão recomendada é seguir com o modo híbrido C: Discord Plus permanece como gateway único de Discord, policy, roteamento por thread/canal, `sessionKey` e reply seguro; a execução do agente passa a ser feita por CLI pública `openclaude --agent <agent>` atrás de flag/configuração, sem patch no core do OpenClaude.

## Contexto

O PRD define que o Discord Plus já mantém gateway próprio, policy, threads e replies seguros, mas o engine SDK v2 não entrega agente principal real; o prompt de persona Oracle foi rejeitado porque não equivale a executar o OpenClaude com `--agent oracle` (`[C]prd-discord-plus-hybrid-cli-engine-2026-05-30.md:12-16`). Eduardo explicitamente não aceita alterar o core OpenClaude, então a solução deve usar somente a superfície pública da CLI e preservar o Discord Plus como camada de transporte/policy/reply (`[C]prd-discord-plus-hybrid-cli-engine-2026-05-30.md:16-25`).

O plano existente também impõe guardrails arquiteturais: manter SDK como rollback, não usar `--channels plugin:discord@...`, não substituir reply seguro por side effect direto da CLI/plugin oficial, e investigar flags reais da CLI antes de codificar continuidade ou modo não interativo (`[C]index-2026-05-30.md:23-40`).

Hipótese arquitetural antes do build: o risco principal não é “como chamar a CLI”, mas como preservar semântica de sessão, concorrência e side effects quando cada mensagem pode virar processo externo. Se o runner CLI for acoplado ao supervisor existente e tratado como engine substituível, o Discord Plus mantém controle operacional. Se a CLI for chamada fora do supervisor/policy/reply pipeline, o sistema recria o problema original: gateway duplicado, replies fora de controle e rollback frágil.

## Decisão

Adotar um engine CLI acoplável ao `SessionSupervisor`, selecionado por configuração explícita, com SDK atual preservado como engine legado/rollback.

A fronteira de responsabilidade fica assim:

1. Discord Plus continua dono de Discord: gateway único, policy, target resolver, threads, sessionKey, rate/TTL/restart e reply seguro.
2. CLI OpenClaude vira apenas engine de inferência/agente: recebe input autorizado de uma `sessionKey`, executa `openclaude --agent <agent>` com cwd controlado e devolve saída capturável.
3. Saída da CLI não publica diretamente no Discord. Ela é convertida para resposta/intenção passiva e passa pelo adapter/executor seguro do Plus, com policy revalidada antes de qualquer side effect.
4. Continuidade por thread/canal só pode usar mecanismo público confirmado da CLI (`--continue`, `--resume`, session id ou equivalente). Se não houver contrato público verificável, o fallback aceito é sessão isolada por `sessionKey` sem continuidade cross-process, documentada e testada.
5. O rollout deve ser opt-in (`EVONEXUS_DISCORD_PLUS_SESSION_ENGINE=cli` ou nome equivalente), com rollback por env para SDK/legado e estado CLI em namespace separado.

## Opções consideradas

| Opção | Decisão | Benefícios | Custos / problemas |
|---|---|---|---|
| A. Patch no core OpenClaude/SDK v2 para suportar `oracle` real | Rejeitada | Poderia manter SDK como runtime direto | Viola restrição explícita de Eduardo; aumenta dívida de fork; risco de quebrar updates do OpenClaude |
| B. Manter SDK v2 com prompt persona Oracle | Rejeitada | Menor mudança técnica; preserva runtime atual | Já foi rejeitada: persona não é agente principal real; não resolve objetivo do PRD |
| C. Reativar plugin Discord oficial como gateway | Rejeitada | A CLI poderia operar como OpenClaude “nativo” com Discord | Duplica gateway ativo; bypassa policy/reply seguro do Plus; conflita com requisito de gateway único (`[C]prd...:94-99`) |
| D. Discord Plus híbrido com CLI como engine substituível | Recomendada | Usa interface pública; preserva Plus como camada segura; rollback simples; entrega agente real configurável | Exige investigar contrato real da CLI; cria riscos de processo por mensagem, continuidade e parsing de stdout |
| E. Serviço daemon CLI persistente por sessionKey | Adiar | Reduz custo de spawn e melhora continuidade se suportado | Só deve existir após confirmar contrato público da CLI; maior complexidade de lifecycle/cancelamento |

## Consequências

- **Positiva:** entrega agente real via CLI pública sem mexer no core OpenClaude.
- **Positiva:** mantém Discord Plus como ponto único de segurança: autorização antes da CLI e revalidação antes de reply/side effect.
- **Positiva:** rollback operacional é simples: voltar engine para SDK/legado e reiniciar somente o serviço Discord Plus.
- **Negativa:** a qualidade da continuidade depende de contrato público real da CLI. Sem `--continue`/`--resume`/session id verificável, não há continuidade cross-process confiável.
- **Negativa:** processo por mensagem pode elevar latência, custo, consumo de memória e risco de fila sob spam.
- **Negativa:** parser de stdout/stderr vira fronteira crítica. Se a CLI não oferecer modo JSON/stream estável, o Plus deve tratar saída como texto seguro e não como side effects automáticos.
- **Neutra:** estado de sessão CLI deve viver separado do estado SDK para evitar corrupção e permitir rollback sem migração destrutiva.

## Riscos/mitigações

| Risco | Severidade | Mitigação obrigatória |
|---|---:|---|
| Flags reais da CLI não suportam `--agent`, input não interativo, `--continue`, `--resume` ou session id como esperado | Alta | Step 1 factual antes de codificar contrato final; registrar evidência de `openclaude --help`/dry-run; não inventar flags privadas |
| Perda de continuidade por thread/canal | Alta | Persistir session id por `sessionKey` somente se CLI expuser contrato público; fallback explícito sem continuidade cross-process, com isolamento por chave |
| Explosão de processos por mensagem/canal sob spam | Alta | Limite de concorrência por `sessionKey` e global; fila/backpressure; timeout por chamada; cancelamento/kill controlado; mensagem operacional segura ao usuário |
| Corrida entre mensagens da mesma `sessionKey` | Alta | Serializar execução por `sessionKey`; impedir dois processos simultâneos para a mesma sessão lógica; manter isolamento entre chaves diferentes |
| Gateway/plugin Discord duplicado | Alta | Runner CLI nunca pode passar `--channels plugin:discord@...`; testes unitários devem falhar se args contiverem plugin Discord; deploy deve validar que só Plus está logado |
| Reply fora do pipeline seguro | Alta | Saída CLI vira texto/intenção passiva; publicação passa por `GatewayIntentExecutor`/adapter seguro e parent-channel policy; revalidar policy antes do side effect |
| Vazamento de segredo em stderr/env/log | Alta | Spawn com env mínimo allowlisted; redaction de stdout/stderr; nunca logar env completo, token Discord, headers ou payload sensível |
| Processo preso ou sem saída | Média/Alta | Timeout por execução; cancelamento por `AbortController`/kill tree equivalente; `stop()` implementado no handle do supervisor |
| Rollback corrompido por estado compartilhado | Média | Namespace separado para estado CLI; SDK preservado; alteração por env; nenhum migration destrutivo em policy/pairing/session store |

## Perguntas bloqueantes

- [ ] Quais flags públicas reais do `openclaude` suportam modo não interativo, input por stdin/arg, saída capturável e agente (`--agent oracle`)? Bloqueia montagem definitiva do runner.
- [ ] A CLI expõe continuidade pública por `--continue`, `--resume`, session id em stdout, arquivo de estado ou mecanismo equivalente? Bloqueia promessa de continuidade cross-process por thread/canal.
- [ ] A CLI permite especificar cwd/workspace de forma pública e estável, ou o cwd do processo é suficiente? Bloqueia garantia de contexto correto por workspace.
- [ ] Qual formato mínimo de saída será aceito como reply seguro: texto final, JSON, evento streaming ou transcript parseado? Bloqueia adapter de saída e evita duplicidade de reply.
- [ ] O processo deve ser um spawn por mensagem ou um processo persistente por `sessionKey`? Bloqueia dimensionamento de timeout, cancelamento, fila e uso de memória. Recomendação inicial: spawn por mensagem apenas se a CLI suportar continuidade pública e limites rígidos; caso contrário, avaliar daemon por sessão como fase posterior.
- [ ] Qual política operacional de timeout/cancelamento deve valer no Discord real: tempo máximo por mensagem, tamanho máximo de saída e mensagem de erro ao usuário?

## Critérios de aceitação

- [ ] Com engine ausente/legado, o Discord Plus mantém comportamento SDK atual.
- [ ] Com `EVONEXUS_DISCORD_PLUS_SESSION_ENGINE=cli` e `EVONEXUS_DISCORD_PLUS_DEFAULT_AGENT=oracle`, o runner invoca CLI pública do OpenClaude com agente configurado, sem alterar core OpenClaude.
- [ ] Nenhum comando CLI contém `--channels plugin:discord@...` nem inicia gateway/plugin Discord oficial.
- [ ] Policy bloqueia usuário/canal não autorizado antes de qualquer spawn da CLI.
- [ ] Saída do agente é publicada no canal/thread correto somente pelo mecanismo seguro do Plus, com policy revalidada.
- [ ] Mensagens da mesma thread/canal/DM usam a mesma `sessionKey`; mensagens de chaves distintas não compartilham estado.
- [ ] Se houver continuidade pública, o session id/continue token é persistido e reutilizado por `sessionKey`; se não houver, o fallback sem continuidade cross-process é explícito e testado.
- [ ] Execução por `sessionKey` é serializada ou protegida contra concorrência; existe limite global de processos.
- [ ] Timeout e cancelamento encerram processo travado e retornam erro operacional redigido, sem stack trace nem segredo.
- [ ] Rollback para SDK/legado funciona por env e reinício do serviço, sem migração destrutiva e sem tocar em tokens/policy/pairing.

## Próximos passos para Bolt

1. Antes de implementar, executar a investigação factual do contrato público da CLI: `--help`/dry-run/version, `--agent`, input não interativo, stdout/stderr, cwd, `--continue`/`--resume`/session ids. Registrar o resultado no próprio plano/nota técnica do feature folder.
2. Implementar configuração de engine/agente e seleção de runner mantendo SDK como default seguro até smoke real PASS.
3. Criar runner CLI atrás do contrato do supervisor existente, usando spawn com array de args, cwd controlado, env mínimo, redaction, timeout e `stop()` funcional.
4. Implementar store CLI por `sessionKey` somente com campos confirmados publicamente pela CLI; se continuidade não existir, codificar fallback explícito sem flags privadas.
5. Integrar saída CLI ao adapter/passive tools/reply seguro do Plus; não permitir side effects diretos da CLI/plugin Discord.
6. Adicionar testes de bloqueio: sem core patch, sem plugin Discord oficial nos args, policy antes do spawn, serialização por `sessionKey`, timeout/cancelamento, rollback SDK.
7. Handoff para Oath/Probe: validar smoke real em canal/thread autorizado, bloqueio em canal não autorizado, continuidade/fallback e rollback.

## Referências

- `/home/evonexus/evo-nexus/workspace/development/plans/discord-plus-hybrid-cli-engine/[C]prd-discord-plus-hybrid-cli-engine-2026-05-30.md:12-16` — problema: SDK v2 não entrega agente principal real; prompt Oracle não basta.
- `/home/evonexus/evo-nexus/workspace/development/plans/discord-plus-hybrid-cli-engine/[C]prd-discord-plus-hybrid-cli-engine-2026-05-30.md:20-25` — objetivos: CLI pública, agente configurável, sessionKey, reply seguro, sem core patch/gateway duplicado.
- `/home/evonexus/evo-nexus/workspace/development/plans/discord-plus-hybrid-cli-engine/[C]prd-discord-plus-hybrid-cli-engine-2026-05-30.md:54-67` — requisitos funcionais de engine, runner, sessionKey e persistência de session ids quando houver suporte público.
- `/home/evonexus/evo-nexus/workspace/development/plans/discord-plus-hybrid-cli-engine/[C]prd-discord-plus-hybrid-cli-engine-2026-05-30.md:69-78` — requisitos de segurança: redaction, spawn sem shell interpolation, cwd limitado, timeout/concorrência.
- `/home/evonexus/evo-nexus/workspace/development/plans/discord-plus-hybrid-cli-engine/[C]prd-discord-plus-hybrid-cli-engine-2026-05-30.md:94-120` — critérios de gateway único, policy, replies via Plus e continuidade/fallback.
- `/home/evonexus/evo-nexus/workspace/development/plans/discord-plus-hybrid-cli-engine/[C]prd-discord-plus-hybrid-cli-engine-2026-05-30.md:134-142` — riscos: flags CLI, parser stdout, custo de processos, continuidade limitada e tools passivas.
- `/home/evonexus/evo-nexus/workspace/development/plans/discord-plus-hybrid-cli-engine/[C]index-2026-05-30.md:23-40` — guardrails: engine config, supervisor, policy, spawn seguro, sem plugin Discord, sem flags inventadas.
- `/home/evonexus/evo-nexus/workspace/development/plans/discord-plus-hybrid-cli-engine/[C]index-2026-05-30.md:50-59` — Step 1: investigação factual do contrato público da CLI antes da implementação.
- `/home/evonexus/evo-nexus/workspace/development/plans/discord-plus-hybrid-cli-engine/[C]index-2026-05-30.md:78-92` — Step 3: runner CLI, comando seguro, stop/onExit, redaction e proibição de plugin Discord.
- `/home/evonexus/evo-nexus/workspace/development/plans/discord-plus-hybrid-cli-engine/[C]index-2026-05-30.md:95-107` — Step 4: persistência por sessionKey com fallback documentado.
- `/home/evonexus/evo-nexus/workspace/development/plans/discord-plus-hybrid-cli-engine/[C]index-2026-05-30.md:110-124` — Step 5: saída CLI integrada ao reply seguro e smoke/rollback.
