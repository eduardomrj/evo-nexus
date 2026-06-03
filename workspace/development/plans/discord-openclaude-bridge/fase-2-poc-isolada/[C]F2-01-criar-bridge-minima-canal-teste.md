---
author: claude
agent: oracle
type: work-plan-item
date: 2026-05-08
phase: 2
item-id: F2-01
status: completed
---

# F2-01. Criar bridge mínima em canal de teste

**Fase:** Fase 2 — POC isolada  
**Eixo:** bridge-discord  
**Tipo:** [CONSTRUIR NOVO]  
**Prazo sugerido:** após F1-01 e F1-02

## O que é

Construir o primeiro ciclo funcional da bridge: bot Discord próprio recebe mensagem em canal de teste, reage com status, chama `openclaude -p`, responde no Discord e marca sucesso ou erro.

## O que fazer

- Criar script em `ADWs/routines/evo-projects/discord_openclaude_bridge.py`.
- Criar data dir `/home/evonexus/evo-projects/discord-openclaude-bridge/` com `logs/`, `reports/`, `src/` e SQLite.
- Configurar `.env` com `DISCORD_OPENCLAUDE_BRIDGE_DATA_DIR` e variáveis necessárias do Discord.
- Implementar allowlist de usuário/canal e reações básicas: 👀, 🛠️, ✅, ❌.
- Chamar `openclaude -p` via subprocess com timeout inicial e captura de saída.

## Agente / Skill / Rotina

@bolt implementa. @grid cria testes. @oath verifica evidência final. @vault pode revisar se houver manuseio de token/segredo.

## O que o usuário precisa decidir/fornecer

- Token/canal/user IDs para teste.
- Timeout inicial.
- Confirmação de que a POC deve rodar fora do canal principal.

## Impacto esperado

Prova o ciclo completo de atendimento com feedback visível sem tocar no serviço atual.

## Dependências

F1-01 e F1-02 concluídos.

## Riscos

- OpenClaude funcionar apenas de forma stateless.
- Saída não estruturada dificultar status fino.
- Falha de permissão para adicionar reações.

## Agente sugerido pra implementação

**Time:** @compass → @apex → @bolt → @grid → @oath

| Fase | Agente | Papel |
|---|---|---|
| 1. Spec | @compass | Quebrar POC em 3-6 passos executáveis |
| 2. Arquitetura | @apex | Validar decisão mínima de arquitetura e subprocess |
| 3. Build | @bolt | Implementar bridge mínima |
| 4. Testes | @grid | Criar testes unitários/integração com mocks |
| 5. Verify | @oath | Verificar evidências antes de liberar |

**Por quê esse time:** item novo com integração externa, subprocess e segurança operacional precisa de plano, arquitetura mínima, build e verificação.

## Resultado reconciliado

Concluído em código. A bridge mínima foi implementada em `ADWs/routines/evo-projects/discord_openclaude_bridge.py` com allowlist, reações básicas, chamada ao OpenClaude, MCP vazio isolado e comando `--check-config`. Falta apenas validação com o bot real no Discord.

## Validação real

Concluída em 2026-05-08 no tópico/canal de teste com o novo bot. O bot conectou, recebeu mensagem do usuário permitido e respondeu corretamente sem substituir o `make discord-channel` oficial.

## Status

- [ ] Pendente
- [ ] Em progresso
- [x] Concluído
