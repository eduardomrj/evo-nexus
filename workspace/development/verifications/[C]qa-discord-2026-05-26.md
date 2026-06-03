## QA Test Report — Discord Metadata Probe

### Environment
- Session name: `qa-discord-metadata-20260526201831`
- Service: evonexus-discord-plus `0.0.1`
- Prerequisites: tmux OK / diretórios OK / `.env` isolado OK / `bun` OK

### Test Cases
| TC | Command | Expected | Actual | Status |
|---|---|---|---|---|
| TC1 | `bun /tmp/discord-auth-probe-20260526201831.mjs` em tmux com `DISCORD_STATE_DIR=/home/evonexus/evo-projects-data/evonexus-discord-plus` | Bot correto conecta sem imprimir token/env | `botId=1502373220886646964` | PASS |
| TC2 | Inspeção segura via Discord API do canal esperado | Identificar tipo/parent sem conteúdo de mensagens | `guildId=958097121133862984`, `channelId=1502371179858755584`, `type=0`, `parentChannelId=1495242245585113108`, `isThread=false` | PASS |
| TC3 | Aguardar inbound real do user permitido | Capturar `guildId`, `channelId`, `parentChannelId`, `threadId`, `isThread`, `userId`, `reasonCode`, `allowed` | Timeout: `reasonCode=no_inbound_message`; nenhum inbound recebido durante a janela | INCOMPLETE |

### Summary
- Total: 3
- Passed: 2
- Failed: 0
- Incomplete: 1

### Cleanup
- Session killed/encerrada: sim
- Artifacts removed: sim (`/tmp/discord-auth-probe-20260526201831.mjs`, `/tmp/discord-auth-probe-20260526201831.log`)
- Process leak check: sem sessão `qa-discord-metadata-20260526201831` remanescente

### Recommendation
Reenviar uma mensagem curta no canal/thread a ser validado e repetir a captura. A inspeção já confirmou que o canal policy `1502371179858755584` é canal de texto normal, não thread, e tem parent/categoria `1495242245585113108`.
