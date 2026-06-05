---
author: compass-planner
agent: compass-planner
type: work-plan
date: 2026-05-31
plan-name: discord-plus-project-context
status: delivered
mode: direct
---

# Work Plan — Discord Plus Project Context aditivo por canal/tópico

## Context

O Discord Plus já tem Hybrid CLI Engine, Oracle real via CLI, `/model` e `/session` publicados/testados. Este plano adiciona contexto de projeto por canal/tópico sem substituir o EvoNexus como casa operacional.

Repo de implementação: `/home/evonexus/evo-projects/evonexus-discord-plus`.

## Objectives

- Criar comandos `/project current`, `/project set path:<path>`, `/project clear` e `/project list`.
- Persistir vínculo de projeto por guild/channel/thread no state dir do Discord Plus.
- Resolver herança de canal pai para threads quando apropriado.
- Injetar bloco `Active Discord Project` de modo persistente por mensagem enquanto houver vínculo ativo.
- Validar paths com allowlist, canonicalização e bloqueio de symlink/path traversal/arquivos sensíveis.
- Garantir autorização separada para escrita via operação `project.context.write`.
- Preservar `/model`, `/session` e o comportamento atual do Hybrid CLI Engine.

## Guardrails

### Must Have

- Modo inicial exclusivamente `additive`.
- EvoNexus permanece como `cwd`/home operacional para agentes, skills, memória, runtime e políticas.
- Projeto externo é apenas `project_path` aditivo no prompt/contexto.
- Allowlist inicial: `/home/evonexus/evo-projects/`, com roots extras somente por env/config explícita.
- `path` deve existir, ser diretório e permanecer dentro da allowlist após resolução real/canonicalização.
- `/project set` e `/project clear` exigem `project.context.write`.
- Mudança de projeto não reseta sessão silenciosamente; responder recomendando `/session reset` se houver sessão ativa.
- Testes automatizados com `bun test`.
- Smoke real no Discord em `#nexus-bridge` ou canal/tópico definido por Eduardo.

### Must NOT Have

- Não trocar `cwd` nesta fase.
- Não alterar core do OpenClaude.
- Não reintroduzir comandos antigos do discord-bridge.
- Não expor listagem completa do filesystem.
- Não permitir `/etc`, `/root`, `/`, `/home` ou home inteira como projeto/allowlist ampla.
- Não imprimir conteúdo de `.env`, secrets, chaves privadas ou arquivos sensíveis.
- Não salvar artefatos de planejamento fora de `/home/evonexus/evo-nexus/workspace/development/plans/discord-plus-project-context/`.

## Task Flow

```text
Step 1 → Step 2 → Step 3 → Step 4 → Step 5 → Step 6
```

## Detailed TODOs

### Step 1 — Mapear pontos de extensão existentes

- **What:** No repo `/home/evonexus/evo-projects/evonexus-discord-plus`, identificar os arquivos atuais de comandos slash, registro de comandos, stores de state, resolução de permissões e montagem do prompt para o Hybrid CLI Engine. Confirmar onde `/model` e `/session` foram implementados para seguir o mesmo padrão.
- **Arquivos prováveis:**
  - arquivos de comandos slash existentes;
  - registrador de comandos Discord;
  - store de sessões/modelos;
  - módulo de permissões/policies;
  - camada que monta input/prompt para o CLI engine.
- **Owner agent:** @scout-explorer para mapeamento rápido; @bolt-executor para aplicar depois.
- **Acceptance criteria:**
  - Lista dos pontos de edição confirmada antes de alterar código.
  - Nenhuma mudança feita no core do OpenClaude.
  - Padrão existente de store/commands reutilizado em vez de criar arquitetura paralela.
- **Estimated complexity:** LOW

### Step 2 — Implementar ProjectContextStore e validação segura de paths

- **What:** Criar store persistente no state dir do Discord Plus para vínculos por escopo e módulo de validação de paths. A validação deve canonicalizar o path, resolver symlinks, exigir diretório existente, bloquear traversal, arquivos e paths sensíveis, e confirmar que o resultado fica dentro das roots allowlisted.
- **Arquivos prováveis:**
  - novo store de project context junto aos stores existentes;
  - novo validador/helper de project roots;
  - configuração/env para roots adicionais;
  - testes unitários de validação.
- **Acceptance criteria:**
  - Store persiste e recarrega vínculos após restart/process reload.
  - Chave por guild/channel/thread evita colisões.
  - Root default `/home/evonexus/evo-projects/` aplicada.
  - Roots adicionais só entram por env/config explícita.
  - Paths `/etc`, `/root`, `/`, `/home`, arquivos, `.env`, traversal e symlink para fora são rejeitados.
- **Estimated complexity:** MEDIUM

### Step 3 — Implementar comandos `/project`

- **What:** Adicionar grupo slash `/project` com subcomandos `current`, `set`, `clear` e `list`. `current/list` são leitura; `set/clear` exigem `project.context.write`. As respostas devem ser curtas, seguras e deixar claro que o modo é `additive`.
- **Arquivos prováveis:**
  - definição/handler de comandos Discord;
  - registrador de slash commands;
  - módulo de autorização/operações;
  - testes de handlers.
- **Acceptance criteria:**
  - `/project current` mostra projeto ativo, modo e origem do vínculo ou ausência de configuração.
  - `/project set path:<path>` valida, persiste e confirma vínculo em modo `additive`.
  - `/project clear` remove vínculo explícito do escopo e informa se restará herança.
  - `/project list` lista vínculos/roots conhecidos sem varrer filesystem completo.
  - Usuário sem `project.context.write` não consegue set/clear.
  - Registro final contém `/model`, `/session` e `/project`.
- **Estimated complexity:** MEDIUM

### Step 4 — Resolver escopo e injetar contexto aditivo no prompt

- **What:** Integrar o resolver de project context ao fluxo de mensagens do Hybrid CLI Engine. Para cada mensagem, resolver projeto ativo por precedência thread → canal pai → nenhum, e injetar bloco curto `Active Discord Project` quando houver vínculo.
- **Arquivos prováveis:**
  - builder de prompt/input para CLI;
  - resolver de sessão/escopo Discord;
  - store de project context;
  - testes de integração do prompt.
- **Acceptance criteria:**
  - Em thread com vínculo próprio, usa o vínculo do thread.
  - Em thread sem vínculo próprio, herda canal pai quando houver.
  - Em canal sem vínculo, não injeta bloco.
  - Enquanto vínculo existir, a injeção é persistente por mensagem.
  - O bloco contém exatamente o path, `Mode: additive` e instrução para manter EvoNexus como home operacional.
  - Nenhum código troca `cwd` por causa deste recurso.
- **Estimated complexity:** MEDIUM

### Step 5 — Testes automatizados e regressão de comandos

- **What:** Cobrir o recurso com testes unitários/de integração e rodar a suite `bun test`. Incluir testes de segurança, store por scope, comandos, autorização, herança, injeção e registro de comandos.
- **Arquivos prováveis:**
  - testes de validador de path;
  - testes de ProjectContextStore;
  - testes de handlers `/project`;
  - testes de prompt injection;
  - testes de command registry.
- **Acceptance criteria:**
  - `bun test` passa.
  - Testes cobrem path/allowlist, path traversal, symlink perigoso, arquivo, `.env`, store por guild/channel/thread, current/set/clear/list, autorização write e registro `/model`/`/session`/`/project`.
  - Não há snapshots/respostas contendo segredos ou listagem de filesystem.
- **Estimated complexity:** MEDIUM

### Step 6 — Deploy, smoke real e rollback

- **What:** Publicar a alteração no runtime do Discord Plus, registrar slash commands e executar smoke real. Validar no Discord que o vínculo é aplicado ao próximo prompt e que o bot continua usando EvoNexus como casa operacional.
- **Arquivos prováveis:**
  - configuração/env do serviço Discord Plus;
  - script/comando de registro de slash commands;
  - logs do serviço;
  - plano de rollback do deploy atual.
- **Smoke real:**
  1. Confirmar bot/canal alvo: OpenClaude Nexus em `#nexus-bridge` ou tópico autorizado por Eduardo.
  2. Rodar `/project current` e confirmar estado inicial.
  3. Rodar `/project set path:/home/evonexus/evo-projects/go-control-erp`.
  4. Enviar mensagem pedindo para identificar o projeto ativo sem ler segredos.
  5. Confirmar resposta coerente com `project_path` e EvoNexus como home operacional.
  6. Rodar `/project clear` e confirmar remoção/herança.
- **Rollback:**
  - Reverter deploy para versão anterior do Discord Plus.
  - Remover/ignorar registro `/project` se necessário.
  - Preservar arquivo de store para diagnóstico, mas não usá-lo se feature for revertida.
  - Se houver comportamento ambíguo de sessão, orientar `/session reset` no canal afetado.
- **Acceptance criteria:**
  - Slash `/project` aparece no Discord junto de `/model` e `/session`.
  - Set/current/list/clear funcionam no canal/tópico real.
  - Mensagem posterior recebe contexto aditivo.
  - Nenhum reset silencioso ocorre ao mudar projeto.
  - Logs não expõem segredos.
- **Estimated complexity:** MEDIUM

## Success Criteria

- [x] `/project current`, `/project set`, `/project clear` e `/project list` estão registrados e operacionais.
- [x] Vínculos persistem por guild/channel/thread no state dir do Discord Plus.
- [x] Threads herdam canal pai quando não têm vínculo próprio.
- [x] Prompt recebe bloco `Active Discord Project` em modo `additive` enquanto vínculo existir.
- [x] EvoNexus continua sendo casa operacional; não há troca de `cwd` nesta fase.
- [x] Paths fora da allowlist, traversal, symlinks perigosos, arquivos e `.env` são bloqueados.
- [x] `project.context.write` protege set/clear.
- [x] `bun test` passa (300 pass, 0 fail — 2026-06-03).
- [x] Smoke real no Discord passa (comandos `/project` validados em runtime).

## Open Questions

- [ ] Nome exato da variável/env para roots adicionais (`DISCORD_PLUS_PROJECT_ROOTS` ou equivalente) deve seguir padrão existente do repo — evita criar nomenclatura divergente.
- [ ] UX final para sessão ativa após mudança de projeto: apenas recomendar `/session reset` ou oferecer confirmação interativa futura — afeta fricção, mas não bloqueia v1.
- [ ] Critério exato do `/project list`: listar todos os vínculos do guild acessível ou apenas escopo atual + roots — impacta privacidade em servidores com múltiplos projetos.

## Consensus Mode

Não aplicado nesta fase. O recurso é sensível a segurança, mas o escopo está definido como aditivo, sem troca de `cwd` e sem alteração de core. Se a próxima fase quiser introduzir modo de `cwd` substitutivo, deve passar por ADR com @apex-architect e revisão de segurança com @vault-security.

## Handoff

- **Next agent:** @bolt-executor
- **Next skill:** dev-verify após build
- **Source artifacts:**
  - `/home/evonexus/evo-nexus/workspace/development/plans/discord-plus-project-context/[C]prd-discord-plus-project-context-2026-05-31.md`
  - `/home/evonexus/evo-nexus/workspace/development/plans/discord-plus-project-context/[C]plan-discord-plus-project-context-2026-05-31.md`
- **Expected output:** implementação no repo `/home/evonexus/evo-projects/evonexus-discord-plus`, testes `bun test`, smoke real no Discord e evidência de verificação.
