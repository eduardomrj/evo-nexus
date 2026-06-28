# Discord Plus — Open Questions

## Refactor Estrutural (dual-sink/cancel/auth) — 2026-06-23
- [ ] OQ-1 (R1) Bypass do Oracle via progressSink (cli-session-runner.ts:576-577) é "efêmero" ou migra p/ intentSink com barreira? — define blast radius de R1 — Risk: med
- [ ] OQ-2 (C1) AsyncLocalStorage propaga até tool calls do caminho MCP (download_attachment/fetch_messages) ou precisa carregador explícito de userId no envelope? — se não, C1 não fecha — Risk: high
- [ ] OQ-3 (R2) Grace period abort→SIGKILL (relação com killFallbackMs)? — afeta cli-process-isolation — Risk: med
