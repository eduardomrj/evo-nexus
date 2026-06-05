---
author: probe-qa
agent: probe-qa
type: qa-test-report
date: 2026-05-26
target: evonexus-discord-plus inbound real após loader v2
verdict: INCOMPLETE
confidence: high
---

# QA Test Report — evonexus-discord-plus inbound real após loader v2

## Ambiente
- Session name: `qa-discord-inbound-20260526-203647`
- Service: `claude-channel-discord` 0.0.1 em `/home/evonexus/evo-projects/evonexus-discord-plus`
- Runtime isolado: `/home/evonexus/evo-projects-data/evonexus-discord-plus`
- Bot esperado: `1502373220886646964` / OpenClaude Nexus
- Guild esperado: `958097121133862984`
- Canal esperado: `1502371179858755584`
- Prerequisites: tmux 3.4; diretório do projeto existe; `.env` isolado existe; `access.json` isolado existe
- Escopo de segurança: não foi impresso token, env completo, header Authorization, prompt, nem conteúdo completo de mensagens

## Test Cases

| TC | Comando / fonte | Esperado | Actual | Status |
|---|---|---|---|---|
| TC1 | `command -v tmux && tmux -V` | tmux disponível | `/usr/bin/tmux`, `tmux 3.4` | PASS |
| TC2 | checagem do runtime isolado | `.env` e `access.json` existem | ambos existem em `/home/evonexus/evo-projects-data/evonexus-discord-plus` | PASS |
| TC3 | iniciar runtime controlado em tmux | gateway conecta como OpenClaude Nexus | `discord channel: gateway connected as OpenClaude Nexus#4241` | PASS |
| TC4 | aguardar inbound real de mensagem manual | linha de decisão com `action`, `guildId`, `channelId`, `userId`, `allowed/effect`, `reasonCode` | nenhuma decisão inbound apareceu no stderr durante a janela aguardada | INCOMPLETE |
| TC5 | user permitido `783488179000442891` | `allow` / `allowed` | não observado nesta execução | INCOMPLETE |
| TC6 | user negado `1128044010309693480`, se recebido | `deny` / `user_operation_not_allowed` | não observado nesta execução | INCOMPLETE |

## Evidência capturada

- Readiness real capturada no tmux: `discord channel: gateway connected as OpenClaude Nexus#4241`.
- Houve apenas warning de depreciação do Discord.js sobre o evento `ready`; não bloqueou conexão.
- Após duas janelas de espera, não houve linha de autorização inbound no pane capturado.
- Não foi capturado conteúdo de mensagem.

## Summary
- Total: 6
- Passed: 3
- Failed: 0
- Incomplete: 3

## Cleanup
- Session killed: yes, `qa-discord-inbound-20260526-203647` encerrada
- Artifacts removed: yes, `/tmp/qa-discord-inbound-20260526-203647.stdout` removido
- Process leak check: partial; a sessão tmux desta execução foi eliminada, mas já havia processos `bun server.ts` não relacionados/anteriores ainda visíveis (`2131`, `2132`) e não foram encerrados para evitar matar runtime fora do escopo

## Recommendation

NEEDS_MORE_EVIDENCE.

A runtime controlada subiu corretamente com o loader v2 e conectou ao Discord, mas nenhuma mensagem inbound real chegou na janela razoável. Reexecutar com mensagem manual enviada enquanto a sessão estiver ativa para fechar os critérios do user permitido/negado.
