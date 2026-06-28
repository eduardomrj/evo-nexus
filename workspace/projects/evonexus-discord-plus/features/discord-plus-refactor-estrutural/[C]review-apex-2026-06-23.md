# [C] Review Arquitetural — Apex — Discord Plus Refactor Estrutural

**Data:** 2026-06-23
**Autor:** @apex-architect
**Veredito:** REFATORAR
**Ticket:** `bc89ef74-4d4b-43d1-9817-510b2c9355bf`

---

## Veredito

**REFATORAR.** Os 7 problemas reportados em produção **não são bugs pontuais** — todos rastreiam para **3 decisões arquiteturais ruins**: D3 (dual-sink sem coordenação), D5+D6 (cancelamento sem propagação de cancel), e D8 (divergência thread/canal). Hotfixes continuam ressurgindo porque a raiz nunca foi endereçada. Os commits recentes (`2b04e62`, `3bf249f`) são band-aids **corretos** — acertam o sintoma — mas foram aplicados **sem teste de regressão**, então o próximo refactor pode silenciosamente reverter o comportamento.

## As 3 decisões arquiteturais ruins

### D3 — Dual-sink (`progressSink` + `intentSink` sem barreira de fim-de-turno)
`sdk-inbound-runtime.ts:65-85` cria dois caminhos de entrega para o Discord:
- `intentSink` (linha 65) — caminho "oficial" via `GatewayDispatcher`/`shadow-outbox`
- `progressSink` (linha 68) — caminho paralelo para preview de planejamento

Não há barreira que sincronize o fim do turno entre os dois sinks. O resultado:
- chunks tardios chegam até 56s **depois** do `done`
- 6 mensagens extras por turno
- o band-aid `alreadyDelivered` (`cli-session-runner.ts:376`) tenta suprimir duplicatas **comparando strings** do preview vs resultado final — frágil por construção (qualquer reformatação quebra a comparação).

**Recomendação:** `progressSink` deve carregar **apenas sinais efêmeros** (typing indicator, "🗜️ compactando"). **Todo conteúdo durável** passa pelo `intentSink` com barreira de fim-de-turno. Isso mata a comparação de strings.

### D5+D6 — Cancelamento teatral (timeout sem cancel real)
`gateway-dispatcher.ts:241-259` (`withTimeout`) faz `Promise.race([promise, timeout])` **sem AbortSignal**. Quando o timeout vence, a promise é *rejeitada* mas o trabalho subjacente (o processo `runCli`, o stream stdout) **continua rodando**. O "cancelamento" é teatral: a UI mostra timeout, o processo segue vivo.

Combinado com D6: `session-execution-registry.ts:79` (`pruneExpired`) só roda de forma **lazy** — quando `tryStart`/`get` são chamados (linhas 29, 45, 75). Não há timer dedicado. Uma sessão que travou e não recebe novas chamadas **nunca é podada**.

Consequência observada: travamentos de 57min, sessão de 23min sem deadline efetivo.

**Recomendação:** `AbortController` propagado de `gateway-dispatcher` → `cli-session-runner` → `runCli` (`spawn` recebe o signal, e o handler de abort mata o processo). Timer dedicado de prune no registry. **Este é pré-requisito de `cli-process-isolation`** (Fix 3, já planejado) — o isolamento em cgroup depende de um caminho de cancelamento que de fato mate o processo.

### D8 — Divergência thread/canal
Existem **dois handlers de mensagem inbound** com lógica divergente:
- caminho **canal** (`server.ts:252`) — seta `currentSessionUserId`, **loga `SDK inbound start`** (`server.ts:254`)
- caminho **thread** (`server.ts:1408`, `deliverLegacy`) — seta `currentSessionUserId` mas **NÃO loga `SDK inbound start`**

A divergência vaza para **autorização** (ambos escrevem a mesma global `currentSessionUserId` — base do C1) e **observabilidade** (threads são invisíveis no log de início). O sessionKey também bifurca em `types.ts:33-34` (`:thread:` vs `:channel:`).

**Recomendação:** logging e gate de autorização **idênticos** nos dois caminhos; emitir `SDK inbound start` **antes** do branch SDK/legacy nos dois.

## Sequência obrigatória

```
C1 (segurança) → R1 (unifica entrega / D3) → R2 (AbortController + prune / D5+D6) → R3 (paridade / D8)
```

R1 → R2 → R3 **antes** de qualquer feature nova. `cli-process-isolation` **pré-requisita R2**.

## Arquivos-chave por refactor

| Refactor | Arquivos |
|---|---|
| C1 | `server.ts:104,252,776,1408` |
| R1 | `sdk-inbound-runtime.ts:65-85`, `cli-session-runner.ts:374-392` |
| R2 | `gateway-dispatcher.ts:241-259`, `cli-session-runner.ts:343-407`, `session-execution-registry.ts:29,45,75,79` |
| R3 | `server.ts:120,132-134,252-254,1262-1427`, `types.ts:33-34` |

## Risco de não refatorar

Cada hotfix futuro tem chance alta de reabrir um dos 3 problemas, porque a estrutura **convida** ao bug (global mutável compartilhada, race sem barreira, cancel sem cancel). O custo de reconquistar o conhecimento de `stream-json` parsing é alto — preservar via testes de regressão é mandatório.
