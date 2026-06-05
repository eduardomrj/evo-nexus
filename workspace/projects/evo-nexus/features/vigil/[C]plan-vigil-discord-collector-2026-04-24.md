---
author: claude
agent: compass-planner
type: work-plan
date: 2026-04-24
plan-name: vigil-discord-collector
status: draft
mode: direct
---

# Work Plan — Vigil Discord Message Collector

## Context

O Vigil ja coleta mensagens do WhatsApp via webhook (Evolution Go POST para `/vigil/api/whatsapp/webhook`) e salva no `community_messages` do SQLite. O Discord tem 18 canais configurados em `discord_channels.json` com CRUD completo na UI, mas **nenhuma coleta de mensagens**. Este plano adiciona um bot Discord que escuta mensagens em tempo real e as salva usando a mesma pipeline (`classify()` + `save_entry()`).

## Objectives

- Mensagens do Discord aparecem na tabela `community_messages` com `platform='discord'`
- Apenas canais configurados em `discord_channels.json` sao processados
- Classificacao (`classify()`) e salvamento (`save_entry()`) reutilizam a logica existente
- Hot-reload: quando o usuario salva canais via UI (`/vigil/api/discord/save`), o bot atualiza sua lista sem restart

## Guardrails

### Must Have
- Usar `discord.py` com gateway (real-time `on_message`), nao polling
- Rodar como thread daemon dentro do mesmo processo Flask (padrao ja usado: `threading.Thread(..., daemon=True)`)
- Filtrar apenas canais presentes em `discord_channels.json` (por channel ID)
- Usar `DISCORD_BOT_TOKEN` do `.env` (ja existe)
- Respeitar a logica de `classify()` com topics do canal + filtro de noise

### Must NOT Have
- Arquivo novo — tudo em `vigil.py`
- Dependencia de `DISCORD_USER_TOKEN` (esse e para listar canais na UI; o bot usa `DISCORD_BOT_TOKEN`)
- Comandos de bot (slash commands, prefixed commands) — apenas listener passivo
- Mensagens do proprio bot processadas

## Task Flow

```
Step 1 → Step 2 → Step 3 → Step 4 → Step 5
```

## Detailed TODOs

### Step 1 — Instalar discord.py no venv do EvoNexus

- **What:** Adicionar `discord.py[voice]==2.*` ao `pyproject.toml` (secao `[project.dependencies]` ou `[tool.uv.dependencies]`) e rodar `uv sync` (ou `pip install discord.py` no `.venv`). O Vigil roda com o Python do EvoNexus (`.venv/bin/python`) via symlink.
- **Where:** `/home/evonexus/evo-nexus/pyproject.toml` + `.venv/`
- **Owner agent:** @bolt-executor
- **Acceptance criteria:** `/home/evonexus/evo-nexus/.venv/bin/python -c "import discord; print(discord.__version__)"` imprime versao sem erro
- **Estimated complexity:** LOW

### Step 2 — Adicionar estado global DISCORD_CHANNELS + reload_discord()

- **What:** Criar variavel global `DISCORD_CHANNELS: dict = _load(CFG_DISCORD)` (mesmo padrao de `WHATSAPP_GROUPS` na linha 145) e funcao `reload_discord()` que recarrega o dict. Atualizar `api_discord_save()` (linha 894) para chamar `reload_discord()` apos salvar — mesmo padrao que `api_whatsapp_save()` chama `reload_whatsapp()`.
- **Where:** `vigil.py` — logo apos `WHATSAPP_GROUPS` (linha ~146) para o global; `api_discord_save()` (linha 894) para o reload
- **Owner agent:** @bolt-executor
- **Acceptance criteria:**
  - `DISCORD_CHANNELS` carrega na inicializacao com os 18 canais do JSON
  - `POST /vigil/api/discord/save` com payload alterado atualiza `DISCORD_CHANNELS` in-memory
  - Log `[discord] Monitoramento atualizado: N canais` aparece com contagem correta
- **Estimated complexity:** LOW

### Step 3 — Implementar classe VigilDiscordBot com on_message

- **What:** Criar classe `VigilDiscordBot(discord.Client)` dentro de `vigil.py` com:
  1. `__init__`: recebe referencia para `DISCORD_CHANNELS` (ou lê o global)
  2. `on_ready`: loga `[discord-bot] Conectado como {self.user}` + lista canais monitorados
  3. `on_message`: a logica core:
     - Ignorar mensagens do proprio bot (`message.author == self.user`)
     - Ignorar se `str(message.channel.id)` nao esta em `DISCORD_CHANNELS`
     - Ignorar se `message.content` vazio
     - Buscar config do canal: `g = DISCORD_CHANNELS[str(message.channel.id)]`
     - Chamar `classify(text, topics)` — se retornar `None`, ignorar
     - Montar dict `entry` no formato de `save_entry()`:
       ```python
       entry = {
           "ts": datetime.now(timezone.utc).isoformat(),
           "platform": "discord",
           "group": g.get("name", str(message.channel)),
           "group_jid": str(message.channel.id),  # reusa campo group_id
           "instance": str(message.guild.id) if message.guild else "",
           "priority": g.get("priority", "media"),
           "category": g.get("category", ""),
           "type": msg_type,
           "summary": text[:200],
           "sender": str(message.author),
           "raw": text[:500],
       }
       ```
     - Chamar `save_entry(entry)`
     - Chamar `process_links(text, ...)` em thread separada (mesmo padrao do webhook WhatsApp, linha 740-744)
     - Log: `[vigil/discord] [{channel_name}] {msg_type} | {author}: {text[:80]}`
  4. Intents: `discord.Intents.default()` + `intents.message_content = True` + `intents.messages = True`
- **Where:** `vigil.py` — nova secao entre as funcoes utilitarias e as rotas Flask (sugestao: antes da secao `# ── WhatsApp webhook`, por volta da linha 680)
- **Owner agent:** @bolt-executor
- **Acceptance criteria:**
  - Classe instanciavel sem erro
  - `on_message` filtra por channel ID, aplica `classify()`, chama `save_entry()`
  - Mensagens do bot sao ignoradas
  - Canais nao monitorados sao ignorados silenciosamente
- **Estimated complexity:** MEDIUM

### Step 4 — Iniciar o bot como thread daemon no startup

- **What:** No bloco `if __name__ == "__main__":` (linha 2377), adicionar:
  1. Verificar se `DISCORD_BOT_TOKEN` existe no `.env` — se nao, logar warning e pular (nao crashar)
  2. Criar funcao `_run_discord_bot()` que:
     - Cria um novo `asyncio.EventLoop` (necessario porque Flask roda no main thread)
     - Instancia `VigilDiscordBot(intents=intents)`
     - Chama `loop.run_until_complete(bot.start(token))`
  3. Iniciar `threading.Thread(target=_run_discord_bot, daemon=True).start()` — mesmo padrao de `_register_evogo_webhook` na linha 2385
  4. Logar `[vigil] Discord bot iniciado (N canais monitorados)`
- **Where:** `vigil.py` — bloco `if __name__ == "__main__":` (linha 2377+) e funcao helper acima dele
- **Owner agent:** @bolt-executor
- **Acceptance criteria:**
  - Vigil inicia normalmente mesmo sem `DISCORD_BOT_TOKEN` (graceful skip com log)
  - Com token valido, bot conecta e loga `on_ready`
  - Flask e Discord bot rodam concorrentemente no mesmo processo
  - `Ctrl+C` encerra ambos (daemon thread morre com o processo principal)
- **Estimated complexity:** MEDIUM

### Step 5 — Teste end-to-end e verificacao

- **What:** Verificar a integracao completa:
  1. Reiniciar Vigil: `pkill -f 'python.*vigil.py'` + re-executar via `start-services.sh`
  2. Checar logs: `tail -f /home/evonexus/evo-nexus/logs/vigil.log` — confirmar `[discord-bot] Conectado como ...`
  3. Enviar mensagem de teste em canal monitorado no Discord
  4. Verificar no SQLite: `sqlite3 /home/evonexus/evo-projects/vigil/vigil.db "SELECT * FROM community_messages WHERE platform='discord' ORDER BY ts DESC LIMIT 5"`
  5. Testar hot-reload: alterar canais via UI (POST `/vigil/api/discord/save`) e confirmar log de reload
  6. Verificar dashboard (`/vigil/`) mostra mensagens do Discord nos graficos
- **Where:** Terminal + SQLite + UI
- **Owner agent:** @bolt-executor (execucao) + @oath-verifier (se necessario)
- **Acceptance criteria:**
  - Mensagens do Discord aparecem em `community_messages` com `platform='discord'`
  - `group_id` contem o channel ID numerico
  - `classify()` funciona (mensagens curtas/noise sao filtradas)
  - Hot-reload de canais funciona sem restart
  - Dashboard mostra dados do Discord
- **Estimated complexity:** LOW

## Success Criteria

- [ ] `discord.py` instalado e importavel no venv do EvoNexus
- [ ] Bot conecta ao gateway do Discord e loga `on_ready` no startup do Vigil
- [ ] Mensagens de canais monitorados sao salvas em `community_messages` com `platform='discord'`
- [ ] Mensagens de canais NAO monitorados sao ignoradas
- [ ] `classify()` filtra noise e aplica topics do canal
- [ ] Hot-reload via `POST /vigil/api/discord/save` atualiza canais in-memory
- [ ] Vigil inicia normalmente se `DISCORD_BOT_TOKEN` nao estiver configurado (graceful degradation)
- [ ] Links extraidos de mensagens Discord sao salvos no `links-log.jsonl`

## Open Questions

- [ ] **Message Content Intent aprovado?** — O bot precisa do intent `MESSAGE_CONTENT` (privilegiado desde set/2022). Verificar se o bot no Discord Developer Portal tem esse intent habilitado. Se nao, `message.content` vira vazio para mensagens em guilds com 100+ membros. — Risk: high
- [ ] **Backfill de mensagens?** — Queremos coletar mensagens anteriores ao deploy do bot (via `channel.history()`)? Isso adicionaria complexidade. Recomendacao: nao nesta iteracao. — Risk: low

## Handoff

- **Next agent:** @bolt-executor
- **Next skill:** implementacao direta dos 5 steps
- **Nota:** verificar o intent `MESSAGE_CONTENT` no Discord Developer Portal ANTES de implementar (Open Question #1). Se nao estiver habilitado, habilitar manualmente no portal.
