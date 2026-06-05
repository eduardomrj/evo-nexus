---
author: claude
agent: compass-planner
type: work-plan
date: 2026-05-26
plan-name: evonexus-discord-plus-refactor-sem-perfis
status: done
mode: direct
---

# Work Plan — evonexus-discord-plus: refactor sem perfis

## Context

Eduardo decidiu remover a arquitetura de perfis do `evonexus-discord-plus`: a autorização deve ser por canal/thread e ID real de usuário Discord, não por `owner`, `operator`, `viewer` ou `permission_approver`. O plano anterior ainda cita política por perfil no índice e em F2-01/F3-01, enquanto o repo alvo já contém `AuthorizationProfile`, `UserPolicy.profile`, defaults por perfil e testes/documentação orientados a perfil.

## Objectives

- Remover o modelo de perfis da policy e do runtime sem perder o baseline do Discord Channel oficial.
- Manter autorização fail-closed por guild/canal/thread/DM e `userId` Discord explícito.
- Preservar conceitualmente o F2-04: logs JSONL em `stderr`, `stdout` reservado ao MCP, sem token/prompt/env/stack/conteúdo e com `matchedRule` seguro/redigido.
- Corrigir o risco do F3-01: tool-call não pode ser autorizado por “qualquer usuário autorizado no canal” quando o solicitante real não é conhecido.
- Eliminar o uso de `access.allowFrom` legado como fonte suficiente para `permission_request` sem contexto de solicitante real.

## Guardrails

### Must Have

- Partir do fork oficial existente em `/home/evonexus/evo-projects/evonexus-discord-plus`, sem importar código do bridge custom.
- Política final baseada em IDs Discord: guild/canal/thread/DM + `allowedUserIds`/equivalente explícito.
- `permission_request` e tool-call devem negar ou limitar quando não houver `user_id` real do solicitante.
- `stderrAuthorizationLogger`/logger equivalente deve continuar emitindo só campos seguros.
- Testes devem cobrir deny-by-default, usuário fora da allowlist, canal/thread fora da policy, tool desconhecida, ausência de `userId` real e permission response sem contexto confiável.

### Must NOT Have

- Não manter `AuthorizationProfile`, `PolicyProfile`, `UserPolicy.profile`, `profile` em audit/decision, nem matchedRule com nomes de perfil.
- Não criar papéis alternativos com outro nome; a decisão de produto é sem autorização por perfil.
- Não voltar para “qualquer membro do canal autorizado pode acionar tool” como fallback silencioso.
- Não logar `description`, `input_preview`, prompt, stack trace, token, env ou conteúdo de mensagem.
- Não sobrescrever a estrutura de planos existente; este plano substitui conceitualmente os itens com perfil, mas não apaga o histórico.

## Task Flow

```text
Step 1 → Step 2 → Step 3 → Step 4 → Step 5
                 ↓
             Step 3.5: decisão runtime MCP se user_id real não existir
```

## Detailed TODOs

### Step 1 — Congelar contrato novo e mapa de remoção

- **What:** Revisar e marcar como obsoletas as premissas de perfil nos planos atuais (`[C]index-2026-05-25.md`, F2-01 e F3-01) e abrir o contrato novo: `policy.version = 2` ou migração explícita de schema sem perfis. Mapear remoções obrigatórias em `src/auth/types.ts`, `src/auth/authorization-service.ts`, `src/auth/legacy-access-adapter.ts`, `src/auth/runtime-adapter.ts`, `tests/auth/*` e `ACCESS.md`.
- **Owner agent:** @apex-architect + @vault-security
- **Acceptance criteria:**
  - Dado o plano anterior, quando comparado ao novo contrato, então qualquer requisito de perfil (`owner`, `operator`, `viewer`, `permission_approver`) fica classificado como obsoleto.
  - Dado `src/auth/types.ts:11-20` e `src/auth/types.ts:46-71`, quando o refactor for executado, então não deve restar campo/tipo de perfil no contrato público.
  - Dado `src/auth/authorization-service.ts:12-33`, quando o refactor for executado, então não deve existir tabela de permissões por perfil; autorização deve depender de operation + resource + userId permitido.
- **Estimated complexity:** MEDIUM

### Step 2 — Refatorar engine isolada para policy por recurso + usuário

- **What:** Substituir a decisão por perfil em `AuthorizationService` por uma regra simples: validar policy, validar guild/canal/thread/DM, exigir `subject.userId`, checar se aquele `userId` está autorizado para o recurso e operação. Operações sensíveis como `permission.respond`, `message.history.read`, `attachment.download`, `message.edit` devem ser controladas por lista explícita por usuário/recurso ou por lista explícita de operações, nunca por papel.
- **Owner agent:** @bolt-executor
- **Acceptance criteria:**
  - Dado usuário ausente, quando qualquer operação for autorizada, então retorna deny com motivo equivalente a `user_required`.
  - Dado usuário não listado no recurso/canal/thread/DM, quando chamar `message.reply` ou `fetch_messages`, então retorna deny sem side effect.
  - Dado thread com `threadDefault = inherit`, quando houver `parentChannelId`, então herda somente a policy do canal pai; sem pai confiável deve negar.
  - Dado operação sensível sem permissão explícita para o usuário naquele recurso, quando autorizada, então retorna deny, mesmo que o canal esteja habilitado.
  - Dado a saída de decisão, então não contém `profile`, `subjectProfile` nem matchedRule com papel.
- **Estimated complexity:** HIGH

### Step 3 — Corrigir adapter/runtime e remover fallback “qualquer autorizado no canal”

- **What:** Ajustar `runtime-adapter.ts` e `server.ts` para que tool-calls usem o solicitante real. O ponto crítico atual está em `server.ts:441-452`, onde `fetchAllowedChannel` tenta candidatos do DM/channel (`access.groups[channelId]?.allowFrom`) e permite se algum usuário autorizado passar. Esse fallback deve ser removido ou tornado fail-closed quando o MCP não fornecer `user_id` real vinculado à tool-call.
- **Owner agent:** @bolt-executor + @vault-security
- **Acceptance criteria:**
  - Dado uma tool-call sem `userId` real do solicitante, quando chamar `reply`, `react`, `edit_message`, `download_attachment` ou `fetch_messages`, então o runtime nega por motivo explícito como `actor_user_required`/`runtime_actor_unavailable`, ou só permite modo estritamente limitado aprovado no Step 3.5.
  - Dado canal com múltiplos usuários allowlisted, quando uma tool-call é feita sem ator real, então não é suficiente que “algum usuário autorizado” exista no canal.
  - Dado `operationForTool` em `src/auth/runtime-adapter.ts:48-58`, quando tool desconhecida for chamada, então continua negando sem consultar estado legado.
  - Dado `runAuthorizedRuntimeTool` em `src/auth/runtime-adapter.ts:130-141`, quando auth retornar deny, então side effect não executa.
- **Estimated complexity:** HIGH

### Step 3.5 — Decisão fechada: runtime MCP sem `user_id` real para tool-call

- **What:** Se o runtime MCP/Discord Channel oficial não entrega o ID real do usuário que originou a tool-call, a política aprovada é **deny-by-default**. Tool-call sem `user_id` real confiável deve negar, inclusive `reply`, `react`, `edit_message`, `download_attachment` e `fetch_messages`. Não usar associação `last-inbound-actor` no v2 inicial.
- **Owner agent:** @bolt-executor + @vault-security + @oath-verifier
- **Acceptance criteria:**
  - Dado a ausência de `user_id` real, quando qualquer tool-call protegida for executada, então nega por motivo explícito como `actor_user_required`/`runtime_actor_unavailable`.
  - Dado a negação por falta de ator, quando logar, então registra somente action/guild/channel/thread/allowed=false/reasonCode/matchedRule redigido, sem prompt/input.
  - Dado um canal com múltiplos usuários allowlisted, quando uma tool-call não trouxer ator real, então nenhum usuário do canal pode ser usado como substituto.
- **Estimated complexity:** MEDIUM

### Step 4 — Preservar logger seguro e adaptar matchedRule sem perfis

- **What:** Manter o logger de autorização do F2-04, mas adaptar `safeMatchedRule` em `src/auth/runtime-adapter.ts:143-149`, que hoje só aceita `guild:channel:owner|operator|viewer` e `dm:user:owner|operator|viewer`. O novo matchedRule deve expor apenas identificadores mínimos e seguros, por exemplo `guild:<redacted-or-id>:channel:<redacted-or-id>:user:<redacted-or-id>` se aprovado, ou preferencialmente `policy:<ruleId>` controlado por configuração. Erros com `process.stderr.write` que imprimem objeto `Error` devem ser revisados para não vazar stack/conteúdo.
- **Owner agent:** @bolt-executor + @vault-security
- **Acceptance criteria:**
  - Dado decisão allow/deny, quando logger emitir JSONL, então usa `stderr`, nunca `stdout`.
  - Dado qualquer entrada com token, prompt, env, stack, `description`, `input_preview` ou conteúdo de mensagem, quando logar, então esses campos não aparecem.
  - Dado matchedRule inesperado, quando chamar `safeMatchedRule`, então retorna `redacted`.
  - Dado matchedRule válido sem perfil, quando logar, então não contém `owner`, `operator`, `viewer` ou `permission_approver`.
- **Estimated complexity:** MEDIUM

### Step 5 — Atualizar testes, docs e smoke para sem perfis

- **What:** Reescrever testes de `tests/auth/authorization-service.test.ts` e `tests/auth/runtime-adapter.test.ts` removendo cenários por perfil e preservando os testes reaproveitáveis de deny/fail-closed/side-effect. Atualizar `ACCESS.md` para remover semântica de papéis e `allowFrom` global como aprovação de `permission_request`. Rodar `bun test` e registrar evidência de que o fork oficial continua sem importação do bridge custom.
- **Owner agent:** @grid-tester + @oath-verifier
- **Acceptance criteria:**
  - Dado a suíte, quando buscar por `profile|owner|operator|viewer|permission_approver`, então não há ocorrências em src/test/docs exceto histórico/plano antigo fora do repo alvo.
  - Dado `ACCESS.md:106-147`, quando atualizado, então documenta logs seguros e policy por canal/thread/user sem papéis.
  - Dado `bun test`, quando executado, então passa com cobertura de allow e deny para guild, canal, thread, DM, tool desconhecida, ausência de ator real e permission response.
  - Dado permission request, quando `access.allowFrom` tiver usuários globais, então isso não autoriza sozinho `permission.respond` sem contexto de userId real + recurso permitido.
- **Estimated complexity:** MEDIUM

## Reaproveitar vs remover

### Pode ser reaproveitado

- Estrutura isolada de `src/auth/authorization-service.ts` como ponto único de decisão, removendo só a semântica de perfil.
- `src/auth/runtime-adapter.ts` como camada de tradução tool→operation e gate de side effect.
- `runAuthorizedRuntimeTool` e testes de “deny antes de side effect”.
- Testes de fail-closed: policy ausente, guild ausente, canal não permitido, thread sem pai, tool desconhecida.
- Logger F2-04: JSONL em `stderr`, campos mínimos, `safeMatchedRule` redigindo entradas inesperadas.
- Estrutura de `LegacyAccess` apenas como compatibilidade temporária de configuração, desde que não converta `allowFrom` em perfis.

### Deve ser removido

- `AuthorizationProfile`, `PolicyProfile`, `UserPolicy.profile` e campos `profile`/`subjectProfile` em audit/decision.
- `DEFAULT_PROFILE_OPERATIONS` e `isKnownProfile`/`isOperationAllowed(profile, ...)`.
- `policy.users[userId] = { profile: 'owner' | 'operator' }` em `legacy-access-adapter.ts:28-40`.
- Testes cujo objetivo é diferenciar `owner`, `operator`, `viewer` ou `permission_approver`.
- Comentários/docs que dizem que `permission_request` é seguro porque “qualquer pessoa em `access.allowFrom`” passou pairing.
- `matchedRuleId` composto com perfil.

## Success Criteria

- [ ] Nenhum código runtime em `/home/evonexus/evo-projects/evonexus-discord-plus/src` depende de perfis.
- [ ] Autorização é fail-closed quando falta policy, guild/canal/thread confiável ou `userId` real.
- [ ] Tool-call não usa “qualquer usuário autorizado no canal” como substituto do solicitante real.
- [ ] Permission request não usa `access.allowFrom` legado como autorização suficiente sem contexto de usuário/recurso.
- [ ] Logs continuam em `stderr`, seguros e sem conteúdo sensível.
- [ ] `bun test` passa e inclui casos negativos para os riscos de F3-01.
- [ ] `ACCESS.md` reflete policy por canal/thread/ID Discord, sem papéis.

## Open Questions

- [x] O runtime MCP fornece hoje um `user_id` real e confiável para cada tool-call, ou só temos `chat_id`? — **DECIDIDO:** se a tool-call não trouxer `user_id` real confiável, usar deny-by-default. Não usar last-inbound actor/TTL no v2 inicial.
- [x] Operações sensíveis devem ser controladas por lista explícita por usuário/recurso (`allowedOperations`) ou por separação de listas (`allowedUserIds`, `allowedToolUserIds`, `permissionApproverUserIds` sem perfis)? — **DECIDIDO:** operações explícitas por usuário/recurso.
- [x] DMs continuam permitidas para usuários explicitamente allowlisted ou serão bloqueadas por padrão após remover perfis? — **DECIDIDO:** DMs bloqueadas por padrão, exceto usuários explicitamente listados em `dm.users`.

## Handoff

- **Next agent:** @apex-architect
- **Next skill:** dev-ralplan se a decisão do `user_id` real não estiver clara; caso contrário, handoff para @bolt-executor com este plano + revisão de @vault-security antes do build.
