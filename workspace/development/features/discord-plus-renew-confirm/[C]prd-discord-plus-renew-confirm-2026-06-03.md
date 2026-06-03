---
author: oracle
type: prd
date: 2026-06-03
feature: discord-plus-renew-confirm
status: approved
repo: /home/evonexus/evo-projects/evonexus-discord-plus
---

# PRD — Discord Plus: Session Renew com Confirmação Explícita

## Problema

O fluxo atual de `/session renew` é confuso:

1. O usuário não sabe o que está configurado antes de iniciar a nova sessão.
2. Não há oportunidade de ajustar model/agent/project antes de confirmar.
3. O renew acontece imediatamente — não existe "revisar antes de começar".
4. Trocar model requer `/model set` + `/session reset` em passos separados sem feedback claro.

## Objetivo

Criar um fluxo de renew com confirmação explícita:

- `/session renew` entra em estado de espera (`pending_confirm`)
- O bot exibe a configuração atual no Discord
- O usuário pode ajustar model, agent, project, dirs antes de confirmar
- `/confirm` inicia a nova sessão com a configuração final
- Mensagens normais são ignoradas até o `/confirm`

---

## Fluxo completo

```
Usuário: /session renew
   ↓
Bot: exibe summary + entra em pending_confirm
   ↓
Usuário: (opcional) /model set gpt5.5
Bot: confirma ajuste + exibe summary atualizado
   ↓
Usuário: (opcional) /agent set bolt-executor
Bot: confirma ajuste + exibe summary atualizado
   ↓
Usuário: /confirm
   ↓
Bot: evicta sessão atual, limpa pending state
     "Sessão iniciada. Próxima mensagem usa [config final]."
   ↓
Usuário: primeira mensagem → nova sessão com checkpoint injetado
```

---

## Mensagem de summary (exibida no `/session renew` e após cada ajuste)

```
Sessão preparada para reinício. Configuração atual:

engine:     `cli`
agent:      `oracle`
model:      **Claude Sonnet 4.6** (`anthropic/claude-sonnet-4-6`)
project:    `/home/.../go-control-erp` (additive)
dirs:       nenhum
checkpoint: 2026-06-03 20:14 — "verificar payment hub"

Ajuste se precisar:
  /model set <model>     /agent set <slug>
  /project set path:..   /project clear
  /dirs add path:..      /dirs clear

Quando pronto: `/confirm` para iniciar a sessão.
⚠️ Mensagens normais serão ignoradas até o /confirm.
Expira em 15 minutos se não confirmado.
```

---

## Comportamento por input durante `pending_confirm`

| Input | Comportamento |
|---|---|
| Mensagem normal | Ignorada. Responde: "⏳ Aguardando `/confirm`. Ajuste com `/model`, `/agent`, `/project`, `/dirs` ou confirme." |
| `/model set` | Executa normalmente + exibe summary atualizado |
| `/agent set/clear` | Executa normalmente + exibe summary atualizado |
| `/project set/clear` | Executa normalmente + exibe summary atualizado |
| `/dirs add/clear` | Executa normalmente + exibe summary atualizado |
| `/confirm` | Evicta sessão, limpa pending state, inicia nova sessão |
| `/session reset` | Cancela pending state + executa reset normal |
| `/session renew` | Idempotente — re-exibe summary com config atual |
| `/session status` | Mostra status + indica que scope está em `pending_confirm` |
| `/session cancel` | Comportamento normal (cancela execução ativa se houver) |

---

## Componentes a implementar

### 1. `src/sessions/pending-confirm-store.ts` (novo)

Store persistente por scope. Arquivo: `pending-confirm.json` no state dir.

```typescript
type PendingConfirmEntry = {
  initiatedAt: string   // ISO timestamp
  expiresAt: string     // initiatedAt + 15 min
}

class PendingConfirmStore {
  set(scopeKey: string): void
  get(scopeKey: string): PendingConfirmEntry | undefined
  remove(scopeKey: string): void
  isExpired(entry: PendingConfirmEntry): boolean
  prune(): void  // remove expirados
}
```

Timeout padrão: **15 minutos**. Após expirar, scope volta ao normal automaticamente.

### 2. Modificar `/session renew` em `session-command.ts`

- Mantém: salvar checkpoint
- Muda: **não evicta a sessão** — apenas marca pending_confirm
- Retorna: mensagem de summary (ver acima)

A evicção ocorre somente no `/confirm`.

### 3. `/confirm` slash command — `src/sessions/confirm-command.ts` (novo)

```typescript
// Se pending_confirm ativo no scope:
//   1. pendingConfirmStore.remove(scopeKey)
//   2. cliSessionStore.delete(key)
//   3. supervisor.evictSession(key)
//   4. Responde com summary final + "Próxima mensagem inicia a sessão."
//
// Se não há pending_confirm:
//   Responde: "Nenhum renew pendente para confirmar neste scope."
```

O `/confirm` **não exige `session.reset` permission** — qualquer usuário com acesso ao canal pode confirmar.

### 4. Registro do `/confirm` em `server.ts`

- Adicionar ao `buildSessionCommand()` como subcomando, **ou** criar um slash command separado `/confirm`
- Recomendação: subcomando de `/session` → `/session confirm` — evita poluição de comandos
- Registrar no `registerSlashCommands`
- Handler: `handleConfirmSlashCommand`

### 5. Interceptação de mensagens normais

Em `server.ts`, antes do dispatch SDK inbound:

```typescript
// Antes de despachar ao Oracle:
const pending = pendingConfirmStore.get(scopeKey)
if (pending && !pendingConfirmStore.isExpired(pending)) {
  // ignora mensagem, responde com lembrete
  await reply("⏳ Aguardando `/confirm`. ...")
  return
}
if (pending && pendingConfirmStore.isExpired(pending)) {
  pendingConfirmStore.remove(scopeKey)
  // deixa passar normalmente
}
```

### 6. Exibir `pending_confirm` no `/session status`

Adicionar linha ao status quando scope estiver pendente:

```
renew pending: sim (expira em 12min — use /session confirm ou /session reset)
```

---

## Acceptance Criteria

| # | Critério | Como verificar |
|---|---|---|
| AC-1 | `/session renew` entra em `pending_confirm` e exibe summary | Chamar `/session renew`, verificar resposta e estado |
| AC-2 | Mensagem normal durante pending é ignorada com lembrete | Enviar mensagem durante pending, verificar que Oracle não responde |
| AC-3 | `/model set` durante pending atualiza config e exibe summary | Executar `/model set`, verificar summary atualizado |
| AC-4 | `/session confirm` evicta sessão e limpa pending | Chamar `/confirm`, verificar `pending-confirm.json` e sessão evictada |
| AC-5 | Primeira mensagem após `/confirm` injeta checkpoint | Verificar prompt da nova sessão |
| AC-6 | `/session reset` durante pending cancela pending e reseta | Chamar reset, verificar que pending foi limpo |
| AC-7 | Pending expira após 15 min e scope volta ao normal | Simular expiração ou aguardar timeout |
| AC-8 | `/session status` indica pending_confirm ativo | Chamar status durante pending |
| AC-9 | `/session confirm` sem pending responde com mensagem clara | Chamar confirm sem renew prévio |
| AC-10 | `bun test` passa sem regressão | Rodar suite completa |

---

## Out of scope

- Auto-cancelamento por timeout via janitor (pode ser adicionado depois — por ora o check acontece on-demand)
- Notificação no Discord quando o pending expira
- Múltiplos checkpoints simultâneos (uma sessão = um pending_confirm por scope)

---

## Dependências

- `session-command.ts` — renew já existe, será modificado
- `SessionCheckpointStore` — já existe, será reutilizado
- `AgentStoreService` — já existe, para exibir agent no summary
- `ModelStoreService` — já existe, para exibir model no summary
- `ProjectContextStoreService` — já existe, para exibir project no summary
- `ExtraDirsStore` — já existe, para exibir dirs no summary

---

## Handoff para implementação

**Owner:** @bolt-executor  
**Revisor:** @lens-reviewer  
**Verificador:** @oath-verifier  

Começar por `pending-confirm-store.ts` → modificar `session-command.ts` renew → implementar `confirm-command.ts` → interceptação em `server.ts` → testes → smoke no Discord.
