---
author: claude
agent: lens-reviewer
type: code-review
date: 2026-05-21
target: discord-openclaude-bridge MOD-06
verdict: HOLD
---

# Code Review — Discord OpenClaude Bridge MOD-06

## Summary
**Files reviewed:** 6
**Total issues:** 2

### By Severity
- **CRITICAL:** 0
- **HIGH:** 1
- **MEDIUM:** 1
- **LOW:** 0

## Stage 1 — Spec Compliance

| Requirement | Status | Notes |
|---|---|---|
| Slash tree pública permanece igual | Parcial | `register_slash_commands` cria `slash_help` mas não registra `@tree.command(name="help")`; o teste novo espera árvore sem `help`, enquanto o diff removido tinha `/help`. |
| `/start` e `/reset-session` preservam defer/followup | Atendido | `slash_commands.py:90-104` chama `defer_and_followup`; teste cobre ausência de `response.send_message` e presença de followup. |
| `on_ready` preserva sync slash + logging/cache sem sobrescrever handler | Atendido | `slash_commands.py:210-263` unifica logging/cache e sync em um único handler registrado via `client.event`. |
| Fallback `message.reply` → `channel.send` | Atendido | `discord_adapter.py:53-61`; testes existentes cobrem erro de system message e chunk longo. |
| Chunking preservado | Atendido | `discord_adapter.py:78-134` e `175-199`; testes existentes cobrem split, retry progressivo e entrega parcial. |
| Reactions best-effort | Atendido | `discord_adapter.py:137-160` captura erro e loga sem falhar fluxo. |
| Imports/contrato legado | Parcial | Smoke com `PYTHONPATH=src` passa, mas import pelo pacote raiz pode recursar em `build_discord_client`/`main`. |
| Novos arquivos untracked stageados | Não atendido | `src/discord_openclaude_bridge/discord_adapter.py` e `src/discord_openclaude_bridge/slash_commands.py` estão untracked; `git diff --stat` nem inclui esses arquivos. |

## Stage 2 — Code Quality

### Issues Found

#### [HIGH] `/help` desaparece da slash tree pública
- **File:** `/home/evonexus/evo-projects/discord-openclaude-bridge/src/discord_openclaude_bridge/slash_commands.py:60`
- **Issue:** `slash_help` foi mantido como função, mas perdeu o decorator `@tree.command(name="help", description="Mostra os comandos disponíveis da bridge")`. O critério do MOD-06 é não alterar a slash tree pública; o diff anterior registrava `/help`, agora o teste novo consagra a remoção.
- **Why it matters:** Regressão de contrato Discord para usuário final. Mesmo sem smoke live, o próximo sync de slash commands remove/omite `/help`.
- **Fix:** Reaplicar o decorator de `/help` e ajustar `test_slash_adapter_registers_public_tree_and_deferred_session_commands` para esperar `help` na árvore pública. Se a remoção for intencional, ela precisa sair de MOD-06 e virar decisão explícita de produto/compatibilidade.

#### [MEDIUM] Wrapper do pacote raiz recursa fora do layout `PYTHONPATH=src`
- **File:** `/home/evonexus/evo-projects/discord-openclaude-bridge/discord_openclaude_bridge/__init__.py:45`
- **Issue:** `build_discord_client()` faz `from discord_openclaude_bridge import build_discord_client as _build_discord_client`, que resolve para o próprio wrapper quando o pacote raiz é importado diretamente. Evidência local read-only: `import discord_openclaude_bridge as b; b.build_discord_client(None)` resultou em `RecursionError maximum recursion depth exceeded` com `sys.path` apontando para a raiz do repo.
- **Why it matters:** O smoke informado valida `PYTHONPATH=src`, mas consumidores legados/imports a partir da raiz podem quebrar ao chamar os símbolos adicionados justamente para contrato legado.
- **Fix:** Resolver o símbolo a partir do módulo monolítico real sem reimportar o próprio pacote, ou não exportar lazy wrappers que não são seguros no layout raiz. Adicionar teste subprocess no cwd do repo sem `PYTHONPATH=src` chamando `build_discord_client`/`main` até pelo menos validar que não recursa.

## Security Checklist
- [x] No hardcoded secrets encontrados no diff revisado
- [x] Sem nova superfície SQL/NoSQL
- [x] Sem nova renderização HTML/XSS
- [x] Autorização de slash preservada via `require_allowed_interaction`
- [x] Logs de IDs continuam usando redaction em `on_ready`

## Code Quality Checklist
- [x] Extração reduz tamanho/acoplamento do monólito
- [x] Adapter Discord centraliza chunking, fallback e reactions
- [x] `on_ready` evita sobrescrita dupla anterior
- [ ] Teste de slash tree está alinhado ao contrato público anterior
- [ ] Contrato legado cobre layout de import sem `PYTHONPATH=src`
- [ ] Arquivos novos estão prontos para stage/commit

## Positive Observations
- A extração do adapter preserva bem a semântica de entrega: limite seguro, fallback de system message e retry progressivo sem duplicar depois de envio parcial.
- A unificação de `on_ready` corrige o risco estrutural anterior de um handler sobrescrever o outro; agora logging/cache e sync convivem no mesmo evento.
- A cobertura nova para `/start` e `/reset-session` foca no comportamento certo: defer primeiro, followup depois.

## Recommendation
**HOLD**

Não recomendo commitar ainda. Precisa patch para restaurar `/help` na slash tree pública e corrigir/decidir o contrato do wrapper legado; depois stagear os dois arquivos novos e reexecutar os testes já informados. Sem smoke live é aceitável seguir em MONITOR após esses patches, desde que MOD-08 cubra o smoke Discord manual.

## Follow-ups
- [ ] Recolocar `@tree.command(name="help", description="Mostra os comandos disponíveis da bridge")` em `slash_help` ou documentar decisão explícita de breaking change fora do MOD-06.
- [ ] Ajustar teste da slash tree para incluir `help`.
- [ ] Corrigir wrapper recursivo de `discord_openclaude_bridge/__init__.py` e adicionar teste de import pelo layout raiz.
- [ ] Stagear `src/discord_openclaude_bridge/discord_adapter.py` e `src/discord_openclaude_bridge/slash_commands.py` antes do commit.
- [ ] Reexecutar: `PYTHONPATH=src python3 -c "import discord_openclaude_bridge as b; assert hasattr(b, 'build_discord_client'); assert hasattr(b, 'main')"`, `PYTHONPATH=src python3 src/discord_openclaude_bridge.py --check-config`, e `timeout 420s python3 -m pytest -q --color=no tests/test_discord_openclaude_bridge.py`.
