---
author: compass-planner
agent: compass-planner
type: work-plan
date: 2026-06-03
plan-name: discord-plus-extra-dirs
status: ready
mode: direct
source-prd: workspace/development/plans/discord-plus-extra-dirs/[C]prd-discord-plus-extra-dirs-2026-06-03.md
---

# Work Plan — Discord Plus Extra Dirs: pastas adicionais por tópico/canal

## Context

O Discord Plus já tem o módulo `src/projects/` (store, validator, resolver, autocomplete, command) que governa o projeto ativo por escopo via `/project set`, e injeta `--add-dir /home/evonexus/evo-nexus` automaticamente no CLI. Este plano adiciona um grupo `/dirs` paralelo que declara **pastas extras** por escopo, cada uma virando um `--add-dir` adicional, sem tocar `/project set` nem o `cwd`.

Repo de implementação: `/home/evonexus/evo-projects/evonexus-discord-plus`.
Stack: Bun + TypeScript + discord.js, strict mode, baseline `bun test` = 300 pass / 0 fail.

Pontos de extensão confirmados (mapeamento Scout, 2026-06-03):

- Padrão de módulo a espelhar: `src/projects/` (`project-context-store.ts`, `project-path-validator.ts`, `project-autocomplete.ts`, `project-command.ts`, `types.ts`).
- Allowlist/validação: `src/projects/project-path-validator.ts` — já expõe `DEFAULT_PROJECT_ROOT`, `UNSAFE_ROOTS`, `SENSITIVE_BASENAMES`, `validateProjectPath`, `realpathSync` + bloqueio de traversal/symlink/arquivo. **Reaproveitar `validateProjectPath`** — não reescrever validação.
- Operações de autorização: `src/auth/types.ts` → `AUTHORIZATION_OPERATIONS` (precisa de `dirs.write`). O PRD também cita `CHANNEL_OPERATIONS`; confirmar nome real no `src/auth/` durante o Step 1 (no código atual só existe `AUTHORIZATION_OPERATIONS` + `ChannelPolicy.userOperations`).
- Injeção `--add-dir`: `src/sessions/cli-session-runner.ts:154-156` — hoje insere um único `--add-dir` antes do último arg. É aqui que as pastas extras entram, **depois** do `--add-dir /home/evonexus/evo-nexus`.
- Scope keys: `src/projects/project-context-resolver.ts` → `projectScopeKeyForContext` (`guild:{id}:thread:{id}` / `guild:{id}:channel:{id}`). Reusar a mesma convenção.
- Store persistente: `src/projects/project-context-store.ts` — JSON atômico (tmp+rename, mode 0o600) em `stateDir/project-contexts.json`. Espelhar para `extra-dirs.json`.
- Wiring de comandos/runtime: `src/sessions/sdk-inbound-runtime.ts`, `gateway-dispatcher.ts`, `session-command.ts`, `cli-session-runner.ts`.

## Objectives

- Criar grupo slash `/dirs` com subcomandos `add`, `remove`, `list`, `clear`.
- Persistir lista de pastas extras por escopo (guild/channel/thread) no state dir do Discord Plus, robusto a restart.
- Validar cada pasta contra a allowlist `/home/evonexus/evo-projects/` + `/home/evonexus/evo-projects-data/`, bloqueando traversal, symlink fora da allowlist, arquivos e `.env`.
- Limitar a 5 pastas extras por escopo.
- Autocomplete em `/dirs add` listando subdiretórios das duas roots.
- Adicionar operação `dirs.write` em `AUTHORIZATION_OPERATIONS` (e no equivalente de operações de canal, se existir).
- Injetar cada pasta extra como `--add-dir <path>` no CLI, **depois** do `--add-dir /home/evonexus/evo-nexus` automático, sem alterar `cwd` nem o projeto ativo.
- Cobrir com `bun test` e validar via smoke real no Discord.

## Guardrails

### Must Have

- Espelhar o módulo `src/projects/` em vez de criar arquitetura paralela.
- Reaproveitar `validateProjectPath` de `project-path-validator.ts`; estender as roots para incluir `/home/evonexus/evo-projects-data/`.
- Allowlist fixa nesta fase: `/home/evonexus/evo-projects/` e `/home/evonexus/evo-projects-data/`.
- `path` deve existir, ser diretório e permanecer dentro da allowlist após `realpathSync`.
- `/dirs add`, `/dirs remove`, `/dirs clear` exigem `dirs.write`; `/dirs list` é leitura.
- Limite de 5 pastas por escopo, sem duplicatas (dedup por `canonicalPath`).
- Cada operação responde recomendando `/session reset` se houver sessão ativa — sem reset silencioso.
- Store atômico (tmp+rename, mode 0o600) seguindo o padrão existente.
- Ordem de injeção determinística (ordem de adição).
- Testes `bun test` verdes (baseline 300 pass) + smoke real no Discord.

### Must NOT Have

- Não alterar `/project set` nem qualquer comportamento do módulo `src/projects/`.
- Não trocar o `cwd` da sessão.
- Não remover o `--add-dir /home/evonexus/evo-nexus` automático.
- Não aceitar arquivos, paths relativos, `..`, ou symlink que escape da allowlist.
- Não permitir roots sensíveis (`/`, `/etc`, `/root`, `/home`, `/home/evonexus` amplo) — já cobertos por `UNSAFE_ROOTS`.
- Não alterar o core do OpenClaude.
- Não reintroduzir comandos antigos do discord-bridge.
- Não imprimir conteúdo de `.env`, secrets ou listagem completa do filesystem nas respostas.
- Não salvar artefatos de planejamento fora de `workspace/development/plans/discord-plus-extra-dirs/`.

## Task Flow

```text
Step 1 → Step 2 → Step 3 → Step 4 → Step 5 → Step 6
```

## Detailed TODOs

### Step 1 — Confirmar pontos de extensão e estender allowlist

- **What:** Confirmar no repo os nomes/arquivos reais antes de codar: (a) `AUTHORIZATION_OPERATIONS` em `src/auth/types.ts` e a existência (ou não) de `CHANNEL_OPERATIONS` citado no PRD; (b) ponto de injeção em `cli-session-runner.ts:154-156`; (c) como o envelope carrega `projectPath`/`projectMode` para descobrir como anexar `extraDirs` ao envelope; (d) onde os comandos `/project`/`/session`/`/model` são registrados no runtime para registrar `/dirs` no mesmo lugar. Estender a allowlist do validator para incluir `/home/evonexus/evo-projects-data/`.
- **Arquivos prováveis:**
  - `src/auth/types.ts` (operações);
  - `src/projects/project-path-validator.ts` (adicionar `evo-projects-data` às roots seguras / `SAFE_EXTRA_ROOT_PREFIXES`);
  - `src/sessions/cli-session-runner.ts`, `sdk-inbound-runtime.ts`, `gateway-dispatcher.ts` (envelope + injeção + registro).
- **Owner agent:** @scout-explorer para confirmação rápida; @bolt-executor aplica.
- **Acceptance criteria:**
  - Lista de pontos de edição confirmada; nome real da constante de operações de canal resolvido (usar `AUTHORIZATION_OPERATIONS` se `CHANNEL_OPERATIONS` não existir).
  - `validateProjectPath` aceita paths dentro de `/home/evonexus/evo-projects-data/` e continua rejeitando `evo-projects-data` raiz vazia, traversal, symlink e arquivos.
  - Nenhuma alteração no core do OpenClaude nem no módulo `src/projects/` além da extensão de roots compartilhada.
- **Estimated complexity:** LOW

### Step 2 — Implementar ExtraDirsStore (espelhando ProjectContextStore)

- **What:** Criar store persistente para a lista de pastas extras por escopo, espelhando `project-context-store.ts`. Arquivo `extra-dirs.json` no state dir, escrita atômica (tmp+rename, mode 0o600), `read()` com sanitização e descarte de entradas inválidas, `get/set/remove/list` por `scopeKey`. Definir tipos em um `types.ts` do módulo: registro por escopo com array de entradas, cada entrada `{ canonicalPath, addedAt, addedBy }`, mais `scopeKey` derivado.
- **Arquivos prováveis:**
  - novo `src/dirs/extra-dirs-store.ts`;
  - novo `src/dirs/types.ts` (`ExtraDirEntry`, `ExtraDirsScopeRecord`, `ExtraDirsStoreFile`);
  - testes unitários `test/dirs/extra-dirs-store.test.ts`.
- **Acceptance criteria:**
  - Store persiste e recarrega após restart (arquivo JSON).
  - Chave por `guild:{id}:thread:{id}` / `guild:{id}:channel:{id}` (mesma convenção do resolver).
  - `read()` descarta entradas malformadas sem quebrar (igual ao `sanitizeBinding`).
  - Limite de 5 por escopo aplicado no nível de store ou command (definir; default no command).
  - Sem duplicatas por `canonicalPath`.
- **Estimated complexity:** MEDIUM

### Step 3 — Implementar comandos `/dirs` + autocomplete

- **What:** Adicionar grupo slash `/dirs` com subcomandos `add`, `remove`, `list`, `clear`, espelhando `project-command.ts`. `add`/`remove`/`clear` exigem `dirs.write`; `list` é leitura. `add` valida via `validateProjectPath`, deduplica, aplica limite de 5, persiste e confirma recomendando `/session reset`. `list` mostra contexto completo: projeto ativo (via resolver do `src/projects/`), o `--add-dir` automático do EvoNexus, e as pastas extras numeradas. `remove` informa se a pasta não estava na lista. `clear` remove todas as extras sem tocar o projeto ativo. Autocomplete em `add` reaproveitando `buildProjectAutocompleteChoices` com as duas roots.
- **Arquivos prováveis:**
  - novo `src/dirs/dirs-command.ts`;
  - novo `src/dirs/dirs-autocomplete.ts` (ou reuso direto de `project-autocomplete.ts` com roots das duas allowlists);
  - `src/auth/types.ts` (`dirs.write` em `AUTHORIZATION_OPERATIONS`);
  - registrador de slash commands (onde `/project` é registrado);
  - testes `test/dirs/dirs-command.test.ts`.
- **Acceptance criteria:**
  - `/dirs add path:<valido>` persiste e `/dirs list` mostra a pasta como extra ativa.
  - `/dirs add` rejeita fora da allowlist, traversal, arquivo e `.env` com erro seguro, sem persistir.
  - `/dirs add` com path já presente informa duplicata e não duplica.
  - `/dirs add` no 6º path informa que o limite de 5 foi atingido.
  - `/dirs remove` remove e informa quando a pasta não existia.
  - `/dirs clear` zera as extras e responde que `/project` não foi alterado.
  - `/dirs list` mostra projeto ativo + auto EvoNexus + extras numeradas; vazio é indicado.
  - Usuário sem `dirs.write` é negado em `add`/`remove`/`clear`.
  - Autocomplete lista subdiretórios das duas roots (máx 25), sem `.dotfiles` nem sensíveis.
  - Registro final contém `/model`, `/session`, `/project` e `/dirs`.
- **Estimated complexity:** MEDIUM

### Step 4 — Resolver escopo e injetar `--add-dir` extras no CLI

- **What:** Integrar o ExtraDirsStore ao fluxo de mensagens. Resolver as pastas extras do escopo (mesma precedência thread → canal pai do resolver de projeto, se aplicável — definir: por padrão sem herança thread→canal para extras, a menos que o `/project` use herança; alinhar com o resolver existente) e anexá-las ao envelope (ex: `envelope.extraDirs: string[]`). Em `cli-session-runner.ts`, após injetar `--add-dir /home/evonexus/evo-nexus`, injetar cada pasta extra como `--add-dir <path>` em ordem de adição, **antes do último arg**, mantendo `cwd` e projeto ativo inalterados.
- **Arquivos prováveis:**
  - `src/sessions/cli-session-runner.ts` (loop de injeção logo após a linha do `--add-dir` automático);
  - builder/resolver de envelope em `sdk-inbound-runtime.ts` / `gateway-dispatcher.ts` (anexar `extraDirs` resolvidos por escopo);
  - testes de integração de injeção.
- **Acceptance criteria:**
  - Com projeto ativo `go-control-erp` + extra `go-payment-hub`, o CLI recebe `--add-dir /home/evonexus/evo-nexus` **e** `--add-dir /home/evonexus/evo-projects/go-payment-hub`.
  - `cwd` permanece `/home/evonexus/evo-projects/go-control-erp`.
  - Ordem das extras é determinística (ordem de adição).
  - Escopo sem extras não adiciona nenhum `--add-dir` além do automático.
  - `/project` permanece inalterado por qualquer operação `/dirs`.
- **Estimated complexity:** MEDIUM

### Step 5 — Testes automatizados e regressão

- **What:** Cobrir o recurso com testes unitários/integração e rodar `bun test`. Incluir validação de path/allowlist (as duas roots), traversal, symlink, arquivo, `.env`; store por escopo + persistência; add/remove/list/clear; limite de 5; dedup; autorização `dirs.write`; injeção `--add-dir`; e regressão garantindo que `/project` permanece intocado.
- **Arquivos prováveis:**
  - `test/dirs/extra-dirs-store.test.ts`;
  - `test/dirs/dirs-command.test.ts`;
  - `test/dirs/path-validation.test.ts` (cobrir nova root `evo-projects-data`);
  - teste de injeção em `test/sessions/`;
  - teste de regressão de `/project` (não muda após `/dirs *`).
- **Acceptance criteria:**
  - `bun test` passa (≥ 300 pass, 0 fail; novos testes somam ao baseline).
  - Cobertura inclui todos os CA1–CA9 do PRD.
  - Nenhum snapshot/resposta contém segredos ou listagem de filesystem.
- **Estimated complexity:** MEDIUM

### Step 6 — Deploy, smoke real e rollback

- **What:** Publicar no runtime do Discord Plus, registrar slash commands (incluindo `/dirs`) e executar smoke real. Confirmar que extras viram `--add-dir` no próximo prompt e que `/project` + EvoNexus continuam intactos.
- **Arquivos prováveis:**
  - config/env e `evonexus-discord-plus.service`;
  - script/comando de registro de slash commands;
  - logs do serviço.
- **Smoke real:**
  1. Bot/canal alvo: OpenClaude Nexus em `#nexus-bridge` ou tópico autorizado por Eduardo.
  2. `/project set path:/home/evonexus/evo-projects/go-control-erp` (estado base).
  3. `/dirs list` → confirmar projeto ativo + auto EvoNexus + extras vazias.
  4. `/dirs add path:/home/evonexus/evo-projects/go-payment-hub` (testar autocomplete).
  5. `/dirs add` com path fora da allowlist (`/home/evonexus/evo-projects-data/...` é válido; testar um inválido como `/etc`) → erro seguro.
  6. Enviar mensagem pedindo ao agente para confirmar que enxerga ambos os repositórios.
  7. `/dirs remove` e `/dirs clear` → confirmar que `/project` permanece.
- **Rollback:**
  - Reverter deploy para versão anterior do Discord Plus.
  - Remover/ignorar registro `/dirs` se necessário.
  - Preservar `extra-dirs.json` para diagnóstico, mas não usá-lo se feature for revertida.
  - Em ambiguidade de sessão, orientar `/session reset` no canal afetado.
- **Acceptance criteria:**
  - `/dirs` aparece no Discord junto de `/model`, `/session`, `/project`.
  - add/remove/list/clear funcionam no canal/tópico real.
  - Mensagem posterior é executada com os `--add-dir` extras corretos e `cwd` preservado.
  - Persistência confirmada após restart do serviço (CA7).
  - Nenhum reset silencioso; logs não expõem segredos.
- **Estimated complexity:** MEDIUM

## Success Criteria

- [ ] `/dirs add`, `/dirs remove`, `/dirs list`, `/dirs clear` registrados e operacionais (CA8).
- [ ] Pastas extras persistem por guild/channel/thread no state dir, robusto a restart (CA7).
- [ ] Allowlist `/home/evonexus/evo-projects/` + `/home/evonexus/evo-projects-data/` aplicada; traversal/symlink/arquivo/`.env` bloqueados (CA2, CA3).
- [ ] Limite de 5 pastas por escopo e dedup por `canonicalPath` (CA9).
- [ ] Cada extra vira `--add-dir <path>` após `--add-dir /home/evonexus/evo-nexus`, ordem determinística, `cwd` preservado (CA4).
- [ ] `/dirs clear` não afeta `/project set` (CA5).
- [ ] `dirs.write` protege add/remove/clear; `list` é leitura (CA6).
- [ ] `bun test` passa cobrindo CA1–CA9 (CA10).
- [ ] Smoke real no Discord passa.

## Open Questions

- [ ] **Nome da constante de operações de canal.** O PRD pede `dirs.write` em `AUTHORIZATION_OPERATIONS` **e** `CHANNEL_OPERATIONS`, mas no código atual só existe `AUTHORIZATION_OPERATIONS` + `ChannelPolicy.userOperations`. Resolver no Step 1: se `CHANNEL_OPERATIONS` não existir, adicionar apenas a `AUTHORIZATION_OPERATIONS`. — Risco: baixo (não bloqueia; resolvido por inspeção).
- [ ] **Herança thread→canal para extras.** O resolver de `/project` herda canal pai em threads sem vínculo próprio. Definir se as pastas extras seguem a mesma herança ou ficam estritamente por escopo. Sugestão v1: estritamente por escopo (sem herança) para evitar surpresa de contexto; alinhar com Eduardo se quiser herança. — Risco: médio (afeta UX e quais `--add-dir` aparecem em threads).
- [ ] **Local do limite de 5.** Aplicar no store (`set` recusa o 6º) ou no command (mensagem amigável antes de persistir). Sugestão: validar no command para UX, com guarda redundante no store. — Risco: baixo.

## Consensus Mode

Não aplicado. Recurso sensível a segurança, mas escopo é aditivo, sem troca de `cwd`, sem alteração de core e reaproveita validação já endurecida do módulo `src/projects/`. Se uma fase futura introduzir extras em modo `writable` (com troca de `cwd`), deve passar por ADR com @apex-architect e revisão de segurança com @vault-security.

## Handoff

- **Next agent:** @bolt-executor
- **Next skill:** dev-verify após build (mapear CA1–CA10 a evidência)
- **Source artifacts:**
  - `/home/evonexus/evo-nexus/workspace/development/plans/discord-plus-extra-dirs/[C]prd-discord-plus-extra-dirs-2026-06-03.md`
  - `/home/evonexus/evo-nexus/workspace/development/plans/discord-plus-extra-dirs/[C]plan-discord-plus-extra-dirs-2026-06-03.md`
- **What's open:** 3 open questions acima (operações de canal, herança thread→canal, local do limite) — nenhuma bloqueia o início; resolver no Step 1.
- **Expected output:** implementação no repo `/home/evonexus/evo-projects/evonexus-discord-plus` (novo módulo `src/dirs/`), `bun test` verde, smoke real no Discord e evidência de verificação.
