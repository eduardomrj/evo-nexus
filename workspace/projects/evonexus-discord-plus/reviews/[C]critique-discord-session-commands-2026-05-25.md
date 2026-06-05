## Critique — Discord session commands redesign

### VERDICT
**REVISE**

### Overall Assessment
A direção geral é correta: `/new` como sessão default EvoNexus e `/reset-session` preservando roteamento reduzem o acidente atual de perder projeto/cwd. Mas a proposta ainda mistura troca de sessão, salvamento via agente e interação de confirmação assíncrona no Discord sem contrato transacional. Isso é risco operacional real para a bridge ativa.

### Pre-commitment Predictions
- Predicted: conflito entre sessão ativa e execução ativa.
- Found: confirmado; há store de execução ativa e task em memória separados.
- Predicted: `/reset-session` apaga mais estado do que deveria.
- Found: confirmado no código atual.
- Predicted: chamar `/salve` de dentro da bridge criaria acoplamento perigoso.
- Found: confirmado por ausência de contrato de skill e runner como subprocesso OpenClaude.
- Predicted: `/config` expõe paths sensíveis.
- Found: parcialmente confirmado; já expõe cwd/add_dirs quando projeto ativo.

### Critical Findings
Nenhum CRITICAL. Não há evidência de perda inevitável de dados se os gates abaixo forem exigidos antes de deploy.

### Major Findings
[MAJOR] `/reset-session` atual viola a semântica proposta e apaga roteamento — `/home/evonexus/evo-projects/discord-openclaude-bridge/src/discord_openclaude_bridge.py:772-778` — `command_reset_session_text` chama `delete_session_for_channel` e depois `delete_project_for_channel`; `bootstrap.reset_session_and_start_text` repete o padrão em `bootstrap.py:90-96`. Fix: separar explicitamente `reset_current_openclaude_session(scope)` de `clear_project_route(channel)`. `/reset-session` deve deletar só `channel_sessions(channel_id, project_slug atual)` e recriar com o mesmo `active_project`, modelo e add_dirs.

[MAJOR] `/new` default EvoNexus colide com escopo por `project_slug=''` e pode sobrescrever sessão legada/canal — `/home/evonexus/evo-projects/discord-openclaude-bridge/src/discord_openclaude_bridge/execution_store.py:252-258` — sessões são chaveadas por `(channel_id, project_slug)`, com projeto vazio para escopo sem projeto. Fix: definir se “default EvoNexus sem projeto custom” reutiliza `project_slug=''` ou ganha escopo nominal (`evonexus-default`). Se reutilizar vazio, precisa migrar/aceitar impacto sobre `/session`, histórico e compatibilidade de sessões legadas.

[MAJOR] Chamar skill `/salve` automaticamente é frágil e não transacional — `/home/evonexus/evo-projects/discord-openclaude-bridge/src/discord_openclaude_bridge/runner.py:93-148` — o runner executa `openclaude -p` e só conhece prompt, sessão, modelo, modo, cwd/add_dirs; não existe API interna de skill/save com confirmação de sucesso. Fix: não embutir `/salve` como side effect obrigatório de `/new`. Se indispensável, trate como etapa explícita assíncrona: criar execução `save-before-new`, bloquear nova sessão até retorno com sucesso, timeout/cancelamento, e falha não pode deletar sessão antiga.

[MAJOR] Fluxo sim/não/cancelar no Discord precisa de máquina de estados persistida, não parsing solto — `/home/evonexus/evo-projects/discord-openclaude-bridge/src/discord_openclaude_bridge.py:962-979` — já existe rejeição quando há execução ativa, mas não há evidência de estado pendente para confirmação de comando. Fix: criar pending action por channel/user com TTL, nonce/mensagem alvo, respostas permitidas e cancelamento idempotente. Sem isso, “sim” atrasado ou de outro usuário pode iniciar sessão no escopo errado.

[MAJOR] Compatibilidade com `/start` não pode quebrar slash commands existentes sem janela de depreciação — `/home/evonexus/evo-projects/discord-openclaude-bridge/src/discord_openclaude_bridge/slash_commands.py:105-119` — `/start` e `/reset-session` estão registrados como slash commands. Fix: manter `/start` como alias temporário para comportamento antigo ou resposta de migração clara; registrar `/new`; atualizar help/docs/testes; sincronizar comandos no Discord e validar que não ficam comandos órfãos.

### Minor Findings
[MINOR] Mensagens atuais de falha ainda dizem “Tente novamente com `/start`” — `/home/evonexus/evo-projects/discord-openclaude-bridge/src/discord_openclaude_bridge/command_handlers/bootstrap.py:107-111` — precisa trocar para `/new` ou texto compatível com alias.

[MINOR] `/config` já mostra paths em claro para projeto ativo — `/home/evonexus/evo-projects/discord-openclaude-bridge/src/discord_openclaude_bridge/formatting.py:111-128` — aceitável para usuário único/admin, mas perigoso se o canal/tópico for visível a terceiros. Fix: política clara: mostrar paths só para usuário autorizado/admin, redigir `$HOME`, ou ter `/config verbose`.

### What's Missing
- Definição formal de “sessão ativa” versus “execução ativa” — sessão salva em DB não é processo rodando; execução ativa é store/task em progresso.
- Contrato de atomicidade para `/new`: quando deletar sessão antiga, quando salvar, quando criar a nova, e rollback se bootstrap falhar.
- Política de escopo: canal vs tópico, projeto ativo vs default EvoNexus, e como `/project clear` interage com `/new`.
- UX de confirmação: TTL, botões ou select menu, quem pode responder, e como cancelar.
- Plano de rollout para slash command rename `/start` -> `/new`.

### Ambiguity Risks
- “se já existe sessão ativa” — pode significar sessão OpenClaude persistida ou execução em andamento. Deve virar dois termos separados: `sessão salva` e `execução em andamento`.
- “perguntar se quer salvar” — salvar o quê: resumo do contexto da sessão, memória do agente, artefato em arquivo, ou chamar literalmente skill `/salve`?
- “depois criar sessão nova sem projeto custom” — pode significar limpar `channel_projects`, usar `workspace_path` como cwd, ou criar escopo novo sem `project_slug`.
- “/reset-session deve preservar configuração do tópico” — precisa listar estado preservado: `channel_projects`, `channel_models`, role/access, mode, cwd/add_dirs derivados do projeto.

### Multi-Perspective Notes
- **Security engineer:** `/config` com paths absolutos é disclosure moderado; em Discord privado talvez aceitável, mas não deve expor env, tokens, Vaultwarden, ou paths de secrets. Confirmação sim/não deve ser bound ao usuário autorizado e interação original.
- **New-hire:** nomes atuais confundem: `/start` não inicia tarefa, faz bootstrap; `/reset-session` hoje também limpa projeto. `/new` precisa doc curta com tabela de efeitos por comando.
- **Ops engineer:** comandos de sessão mexem em estado persistente em SQLite e sessões do OpenClaude. Exigir logs estruturados (`new_requested`, `save_started`, `save_failed`, `session_replaced`) e teste em staging/sombra antes de reiniciar o serviço systemd.

### Verdict Justification
**REVISE** porque a intenção está correta, mas a proposta ainda não é segura para implementar sem especificar estado, atomicidade e rollback. Realist check: pior caso realista não é vazamento massivo; é usuário perder o roteamento do tópico ou sobrescrever uma sessão longa sem salvar por confirmação ambígua/skill falhando. Isso justifica MAJOR, não CRITICAL, desde que não seja deployado sem gates.

### Open Questions
- `/new` deve sempre limpar projeto ativo ou só criar sessão default sem tocar no projeto salvo?
- `/salve` existe com contrato estável no OpenClaude CLI? Qual output indica sucesso?
- Confirmação deve ser via botões Discord, slash subcommand (`/new confirm save=true`) ou mensagem textual?
- `/start` fica alias por quantos releases e com qual semântica?

### Gates/Testes exigidos
- Unit: `/reset-session` preserva `channel_projects`, modelo, mode, cwd/add_dirs efetivos; só troca `channel_sessions` do escopo atual.
- Unit: `/new` sem sessão cria sessão default EvoNexus com `cwd=workspace_path`, `add_dirs=()`, sem projeto custom.
- Unit: `/new` com sessão salva e resposta `não` cria nova sessão sem chamar save e sem deixar pending action.
- Unit: `/new` com resposta `sim` só troca sessão depois de save bem-sucedido; falha mantém sessão antiga.
- Unit: `cancelar` e TTL expiram sem mutar sessão/projeto.
- Concurrency: `/new` recusado durante `store.active_for_channel` ou `_active_task_for_channel` ativo.
- Discord integration: slash `/new` registrado, `/start` alias/deprecated, defer/followup para operações longas.
- Security: `/config` redige ou autoriza paths; snapshot não contém secrets/env.
- Migration: testes de sessão legada `project_slug=''` continuam passando ou migração explícita é adicionada.
