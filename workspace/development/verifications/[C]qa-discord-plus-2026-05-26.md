## QA Test Report — Smoke real controlado evonexus-discord-plus

### Environment
- Session name: `qa-discord-plus-live-20260526193303`
- Service: `claude-channel-discord` v0.0.1 (`/home/evonexus/evo-projects/evonexus-discord-plus`, branch `master`, commit `a5f8434`)
- Prerequisites: tmux OK; bun OK; rede Discord OK; diretório OK; serviço antigo `discord-openclaude-bridge.service` inactive
- Política temporária usada em runtime isolado: guild `958097121133862984`; canal `1502371179858755584`; allowlist somente user permitido `783488179000442891`; DM disabled; `permission.respond` sem ator real negado
- Redação: tokens, prompts completos e conteúdo completo de mensagens não foram impressos neste relatório

### Test Cases
| TC | Command | Expected | Actual | Status |
|---|---|---|---|---|
| TC1 | `git status --short` | repo limpo | sem linhas no `status --short`; branch `master`; commit `a5f8434` | PASS |
| TC2 | `bun test` | suíte verde | 38 pass, 0 fail, 99 expects, 4 arquivos | PASS |
| TC3 | `bun audit` | sem vulnerabilidades conhecidas | `No vulnerabilities found` | PASS |
| TC4 | verificação de env/credenciais sem valores | token presente e protegido | `/home/evonexus/.claude/channels/discord/.env` existe, mode `0600`, `DISCORD_BOT_TOKEN` presente; env do shell sem valores carregados | PASS |
| TC5 | REST Discord `/users/@me` com token redigido | Bot ID esperado `1502373220886646964` | API OK, mas Bot ID real retornado `1494390018729447435`; username presente | FAIL |
| TC6 | REST Discord guild/canal | guild e canal acessíveis | guild OK; canal direto `GET /channels/1502371179858755584` retornou HTTP 403; listagem de canais do guild vê o canal aprovado entre 121 canais | INCOMPLETE |
| TC7 | runtime controlado em tmux com state temporário | conecta ou falha segura clara | conectou gateway como `Bot-Nexus#6824`; stderr operacional recebeu log de conexão; stdout length `0` | PASS com ressalva do TC5 |
| TC8 | policy: user permitido no canal | allow esperado | decisão controlada `message.deliver`: effect `allow`, reason `allowed`, matched rule do guild/canal/user | PASS |
| TC9 | policy: user negado no canal | deny esperado | decisão controlada `message.deliver`: effect `deny`, reason `user_operation_not_allowed` | PASS |
| TC10 | policy: tool-call sem ator real | deny esperado | decisão controlada `message.reply`: effect `deny`, reason `user_required` | PASS |
| TC11 | policy: DM bloqueado | deny esperado | decisão controlada `message.deliver` em DM: effect `deny`, reason `user_not_allowed_in_dm` | PASS |
| TC12 | policy: `permission.respond` não liberado sem ator real | deny esperado | decisão controlada: effect `deny`, reason `user_required` | PASS |
| TC13 | logs operacionais em stderr | logger não polui stdout | stderr contém `gateway connected as ...` e warning Discord.js; stdout length `0` | PASS |
| TC14 | mensagem real Discord automatizada | enviar/capturar mensagem real sem interação | não executado: não há credencial de usuário real aprovada para envio automatizado; bot tem leitura direta do canal via endpoint de mensagens bloqueada por HTTP 403 | INCOMPLETE |
| TC15 | runtime isolado real com `DISCORD_STATE_DIR=/home/evonexus/evo-projects-data/evonexus-discord-plus` | gateway conecta com bot esperado | conectou gateway como `OpenClaude Nexus#4241`; sessão `qa-discord-plus-inbound-20260526201132`; serviço antigo inactive antes da execução | PASS |
| TC16 | user permitido `783488179000442891` envia smoke no canal `1502371179858755584` | effect `allow`, reasonCode `allowed` | inbound real capturado: userId `783488179000442891`; channelId `1502371179858755584`; action `message.deliver`; effect `deny`; reasonCode `channel_not_allowed` | FAIL |
| TC17 | user negado `1128044010309693480` envia smoke no canal `1502371179858755584` | effect `deny` | nenhum inbound real desse user capturado dentro da janela de espera | INCOMPLETE |

### Evidência redigida
- `bun test`: 38 pass, 0 fail.
- `bun audit`: sem vulnerabilidades.
- Token: presença verificada apenas por boolean/mode do arquivo; valor não exibido.
- Identidade REST do bot no teste anterior: token autenticava como `1494390018729447435`, diferente do esperado.
- Runtime tmux anterior: `discord channel: gateway connected as Bot-Nexus#6824` em stderr; stdout vazio.
- Runtime tmux desta captura real: `discord channel: gateway connected as OpenClaude Nexus#4241`.
- Evidência inbound real desta captura, sem conteúdo de mensagem:

```json
{"timestamp":"2026-05-26T23:11:39.592Z","action":"message.deliver","guildId":"958097121133862984","channelId":"1502371179858755584","userId":"783488179000442891","allowed":false,"reasonCode":"channel_not_allowed"}
```

### Summary
- Total: 17
- Passed: 12
- Failed: 2
- Incomplete: 3

### Cleanup
- Session killed: yes (`qa-discord-plus-live-20260526193303` encerrada; `qa-discord-plus-inbound-20260526201132` encerrada)
- Artifacts removed: yes (`/tmp/qa-discord-plus-live-20260526193303-state` removido; `/tmp/qa-discord-plus-inbound-20260526201132.log` removido; state temporário anterior também removido)
- Process leak check: yes; nenhum processo `evonexus-discord-plus/server.ts` permaneceu após cleanup
- Serviço antigo após cleanup: `discord-openclaude-bridge.service` continuou `inactive`
- Arquivos persistentes editados: somente este relatório
- Commit realizado: nenhum

### Recommendation
- Veredito atualizado: INCOMPLETE com falha bloqueante na rota allow real.
- O gateway isolado com o bot correto ficou pronto e recebeu pelo menos um inbound real, mas o user permitido foi negado por `channel_not_allowed`.
- Encaminhar para `@hawk-debugger` diagnosticar a leitura/conversão de policy do `access.json` isolado antes de repetir a janela de captura allow/deny.
- Reexecutar o smoke real após correção exigindo dois eventos: permitido `allow/allowed` e negado `deny`.
