# PRD — Token Consumption Fix

**Feature:** `token-consumption-fix`
**Projeto:** evonexus-discord-plus
**Data:** 2026-06-15
**Status:** Aprovado para execução

---

## Contexto

Diagnóstico de 2026-06-15 identificou que o Discord Plus está consumindo tokens de forma excessiva — em sessões longas o contexto chega a percentuais muito altos em pouco tempo. O tópico `1507433098810495046` (sessão `f17f576c`) carrega contexto acumulado desde 12/06 com múltiplos rounds de debugging.

Quatro problemas independentes foram identificados, cada um com correção própria.

---

## Problemas e Acceptance Criteria

### P1 — AUTO_RESUME multiplica o custo de cada mensagem

**Causa:** `MAX_TURNS=20` + `AUTO_RESUME=5` = até 120 turns por mensagem. Cada auto-resume faz uma nova invocação CLI com `--resume`, carregando todo o histórico + adicionando mais contexto.

**AC-P1:** `DISCORD_SDK_INBOUND_CLI_AUTO_RESUME` default reduzido de `5` para `1`. Documentado no env com comentário explicando o trade-off.

---

### P2 — Sessões acumulam contexto indefinidamente sem teto de renovação

**Causa:** Sessões usam `--resume` indefinidamente. Não existe mecanismo que force renovação quando a sessão fica muito densa, mesmo após compact. O `/compact` comprime mas o summary pode ainda ocupar 60-70% do contexto antes da primeira palavra nova.

**AC-P2.1:** Após `runAutoCompactIfNeeded` executar o compact, se `compactOutput.inputTokens` ainda estiver acima de um threshold pós-compact (ex: 50% = 100k tokens), o Discord Plus executa `/session renew` automático.

**AC-P2.2:** Quando renovação automática ocorre, o usuário recebe notificação no Discord:
```
🔄 Contexto renovado automaticamente — a sessão anterior estava muito densa após compactação (X%). Iniciando sessão limpa.
```

**AC-P2.3:** O threshold de renovação pós-compact é configurável via constante `POST_COMPACT_RENEW_THRESHOLD_FRACTION` (default: `0.50`).

---

### P3 — BRIDGE_SYSTEM_NOTE consumindo tokens em cada mensagem de usuário

**Causa:** O `BRIDGE_SYSTEM_NOTE` (~100 tokens) é injetado como parte do conteúdo da mensagem do usuário via `prependActiveProjectBlock`. Aparece em toda invocação — incluindo cada auto-resume. Deveria ser system prompt, não mensagem de usuário.

**AC-P3.1:** `BRIDGE_SYSTEM_NOTE` é passado via `--append-system-prompt` no `buildCliInvocation` para o runner `claude` (único runner que suporta a flag).

**AC-P3.2:** Para o runner `openclaude`, o comportamento atual é mantido (sem mudança) — openclaude não tem `--append-system-prompt`.

**AC-P3.3:** `prependActiveProjectBlock` continua injetando o bloco de projeto ativo no conteúdo (isso deve permanecer como contexto de usuário). Apenas o `BRIDGE_SYSTEM_NOTE` sai do conteúdo.

**AC-P3.4:** O teste `envelope shadow inclui conteúdo textual` é atualizado para refletir a ausência do BRIDGE_SYSTEM_NOTE no conteúdo.

---

### P4 — Double compact: Layer 1 (interno) + Layer 2 (externo) disparam no mesmo threshold

**Causa:** Após o `/compact` de Layer 2 (`runAutoCompactIfNeeded`), o token count é zerado (`setTokenCount(0)`). Isso é impreciso — o contexto pós-compact ainda tem um tamanho real. Na próxima mensagem, Layer 2 não sabe o tamanho atual até a invocação rodar. Mas Layer 1 interno (`CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=80`) também pode disparar dentro da mesma invocação. Resultado: dois compacts em sequência custando tokens duplamente.

**AC-P4.1:** Após compact bem-sucedido, `setTokenCount` recebe `compactOutput.inputTokens` (tamanho real pós-compact) em vez de `0`.

**AC-P4.2:** Se `compactOutput.inputTokens` for `undefined` (CLI não reportou), usa `0` como fallback (comportamento atual preservado).

**AC-P4.3:** A constante `COMPACT_THRESHOLD_FRACTION` (atualmente `0.80`) é rebaixada para `0.70` para que Layer 2 dispare antes de Layer 1 (`CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=80`), evitando que as duas camadas compitam.

---

## Fora de Escopo

- Mudanças no agente Oracle ou nos agentes de projeto
- Mudanças no `maxTurns` (20 é razoável por invocação)
- Renovação automática de sessão por critério diferente de contexto pós-compact (ex: por tempo, por número de turns totais)

---

## Estimativa

4 problemas, todos em `cli-session-runner.ts` e `project-context-resolver.ts`. Mudanças cirúrgicas — sem migration, sem schema change, sem restart de infra adicional.
