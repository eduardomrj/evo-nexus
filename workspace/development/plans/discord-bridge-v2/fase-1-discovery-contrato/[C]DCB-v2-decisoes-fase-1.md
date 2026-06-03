---
author: claude
agent: oracle
type: decision-record
date: 2026-05-19
phase: 1
status: ready-for-adr
plan: discord-bridge-v2
source-items: [DCB-v2-01, DCB-v2-02]
---

# DCB-v2 — Decisões da Fase 1

**Objetivo:** centralizar as decisões que Eduardo precisa tomar para a Discord Bridge v2 seguir de forma autônoma, sem os agentes pararem a cada fase para perguntar o mesmo contexto.

**Como usar:** marque a coluna **Decisão Eduardo** ou preencha os campos `Decisão:`. Depois disso, este arquivo vira a fonte de verdade para Apex, Raven, Bolt, Grid, Oath e SysOps.

---

## 1. Decisão-base da Fase 1

### 1.1 Compatibilidade com contrato oficial Channel/Discord

**Recomendação dos agentes:** a v2 deve ser compatível com o contrato oficial de Channel/Discord, mesmo que algumas features da v1 fiquem temporariamente fora do Dia 1.

**Evidência:**
- `docs/guides/channels.md` define Channels como ponte bidirecional entre mensagens externas e uma sessão Claude Code em execução.
- `docs/guides/channels-reference.md` define inbound via `notifications/claude/channel` e outbound via tool `reply(chat_id, text)`.
- `Makefile` usa `claude --channels plugin:discord@claude-plugins-official` no alvo `discord-channel`.

**Decisão Eduardo:**
- [X] Aprovado — compatibilidade oficial é mandatória.
- [ ] Parcial — compatível onde possível, mas preservar v1 em pontos críticos.
- [ ] Rejeitado — v2 seguirá contrato custom próprio.

**Notas do Eduardo:**

```text

```

---

### 1.2 Princípio de outbound único

**Recomendação dos agentes:** toda resposta gerada pelo agente/modelo deve sair somente por `bridge_reply` / `OutboundGateway.reply()` ou equivalente. `result.text`, stdout, stderr, milestones ou fallbacks não podem virar mensagem visível no Discord.

**Decisão Eduardo:**
- [X] Aprovado — output do agente só via gateway único.
- [ ] Parcial — gateway único para resposta final, mas permitir exceções listadas abaixo.
- [ ] Rejeitado.

**Exceções permitidas, se houver:**

```text

```

---

## 2. Matriz de features — Dia 1 / Pós-v2 / Fallback / Remover

Preencha a coluna **Decisão Eduardo** com uma destas opções:

- `Dia 1`
- `Pós-v2`
- `Fallback v1`
- `Remover`
- `A decidir`

| Feature | Recomendação | Por quê | Decisão Eduardo | Observações |
|---|---|---|---|---|
| Inbound compatível com Channel ou equivalente mínimo | Dia 1 | Contrato oficial de entrada; sem isso a v2 não é channel-compatible |Dia 1|  |
| Outbound único via `reply` / `bridge_reply` | Dia 1 | Resolve a causa-raiz de raw output/chunk leak |Dia 1|  |
| Tool inventory provando ausência de transporte Discord genérico fora do gateway | Dia 1 | Sem isso a v2 pode reproduzir o bug da v1 |Dia 1|  |
| Allowlist/pairing por sender ID | Dia 1 | Segurança oficial exige gate antes de emitir inbound |Dia 1|  |
| Async-first job em background | Dia 1 | Evita timeout do Discord e preserva UX atual |Dia 1|  |
| ACK imediato com `execution_id` | Dia 1 | Usuário precisa rastrear job longo |Dia 1|  |
| Concorrência por canal/tópico | Dia 1 | Evita corrida de sessão/projeto/resposta |Dia 1|  |
| Sessão por canal/tópico | Dia 1 | Continuidade terminal-like |Dia 1|  |
| Sessão separada por projeto | Dia 1 | Evita contaminação entre projetos |Dia 1|  |
| Project routing declarativo | Dia 1 | Segurança de filesystem e contexto correto |Dia 1|  |
| Bloqueio de paths amplos/sensíveis | Dia 1 | Evita expor `/home`, secrets, root, etc. |Dia 1|  |
| Access policy declarativa | Dia 1 | Permissões auditáveis por usuário/projeto |Dia 1| Decisão inferida das respostas 16–20: MASTER auditado, read-only existe, permissão por usuário e canal |
| Allowlist canal/usuário | Dia 1 | Segurança mínima operacional |Dia 1|  |
| `/status` current-only | Dia 1 | Operação básica de jobs longos |Dia 1|  |
| `/cancel` real | Dia 1 | Jobs longos precisam interrupção confiável |Dia 1|  |
| Timeout por execução | Dia 1 | Previne processo zumbi |Dia 1|  |
| `/start` bootstrap leve | Dia 1 | Cria sessão sem trabalho caro |Dia 1|  |
| `/reset-session` + bootstrap | Dia 1 | Evita estado sem sessão após reset |Dia 1|  |
| `/project` mínimo | Dia 1 | Seleção segura de projeto |Dia 1|  |
| `/session` | Dia 1 | Diagnóstico de continuidade |Dia 1|  |
| `/last` redigido | Dia 1 | Debug/auditoria operacional |Dia 1|  |
| `/context` current-only | Dia 1 | Contexto atual sem histórico bruto |Dia 1|  |
| Modelo por canal/tópico | Dia 1 leve | Útil, mas não deve bloquear outbound seguro |Dia 1|  |
| Reações de status | Dia 1 controlado | Baixo risco se enum fixo controlado pela bridge |Dia 1|  |
| Chunking 1900 chars no gateway | Dia 1 | Limite Discord; precisa estar no caminho único |Dia 1|  |
| Idempotência de `bridge_reply` | Dia 1 | Evita duplicidade/spam |Dia 1|  |
| `execution_token` com TTL/escopo | Dia 1 | Vincula resposta à execução correta |Dia 1|  |
| Callback HTTP/MCP com Bearer secret | Dia 1 | Isola MCP do Discord direto |Dia 1|  |
| Supressão de `result.text` | Dia 1 | Fecha bypass principal |Dia 1|  |
| Supressão de stdout/stderr bruto | Dia 1 | Evita vazamento de prompt/path/segredo |Dia 1|  |
| Logs SQLite/JSONL redigidos | Dia 1 | Evita persistir segredo |Dia 1|  |
| Auditoria project/cwd/add_dirs | Dia 1 | Explica contexto real da execução |Dia 1|  |
| Progress parser interno | Dia 1 interno | Útil para status/auditoria, sem virar outbound livre |Dia 1|  |
| Agent milestones como mensagens | Remover Dia 1 / Pós-v2 | Caminho lateral de saída visível |  |  |
| Slash `/help` | Dia 1 | Descoberta operacional |Dia 1|  |
| Slash `/model` | Dia 1 leve | Controle de custo/qualidade |Dia 1|  |
| Slash `/skills` e `/skill` | Pós-v2 | Superfície grande de execução e side effects | Pós-v2 |  |
| Texto commands `/status`, `/cancel`, etc. | Fallback v1 / Pós-v2 | Útil se slash falhar, mas aumenta ambiguidade |Dia 1|  |
| Anexos Discord | Pós-v2 ou Dia 1 limitado | Risco de storage, path traversal e prompt injection |Dia 1|  |
| Onboarding tópico novo | Pós-v2 | Melhora UX/custo, mas não é core de transporte |Dia 1|  |
| `/project new/create` | Pós-v2 | Efeitos colaterais amplos; precisa wizard/confirmação |Dia 1|  |
| Permission relay remoto | Pós-v2 | Oficial documenta, mas não é necessário para provar transporte |Dia 1|  |
| Anexos/reactions/edit avançados | Pós-v2 | Não bloqueiam causa-raiz |Dia 1|  |
| Multi-channel/multi-project avançado | Pós-v2 | Requisito de produto, não contrato mínimo |Dia 1|  |
| Fallback v1 completo | Fallback v1 | Segurança durante migração |Remover|  |
| Entrega de `result.text` direto ao Discord | Remover | Reintroduz fronteira que a v2 elimina |Remover|  |
| Prompt “sempre use bridge_reply” como único enforcement | Remover | Prompt não é controle arquitetural |Remover|  |
| Fallback `channel.send` bruto em erro de chunk | Remover | Mantém payload fora do splitter/gateway |Remover|  |
| `interaction.followup.send` livre | Remover como genérico | Pode bypassar gateway via slash |Remover|  |

---

## 3. Perguntas objetivas para Eduardo

### A. Contrato de outbound

1. `bridge_reply` será o único canal permitido para output do agente no Discord?
   - Recomendação: **Sim**
   - Decisão: sim

```text

```

2. Quando `bridge_reply` estiver habilitado e não for chamado, a bridge pode enviar `result.text`?
   - Recomendação: **Não**
   - Decisão: não

```text

```

3. A mensagem de fallback quando `bridge_reply` não for chamado deve ser fixa?
   - Recomendação: **Sim** — “A execução terminou, mas não chamou o canal seguro `bridge_reply`. Nenhuma saída bruta foi enviada.”
   - Decisão: sim

```text

```

4. `bridge_reply` Dia 1 permite uma única resposta final ou múltiplas mensagens?
   - Opções: `Única final` / `Múltiplas com sequence` / `Streaming` / `Única + status sistêmico`
   - Recomendação: **Única + status sistêmico**
   - Decisão: Múltiplas com sequence

```text

```

5. Reações Discord contam como outbound permitido?
   - Recomendação: **Sim, apenas enum fixo controlado pela bridge**
   - Decisão: Recomendação

```text

```

---

### B. Mensagens sistêmicas vs output do agente

6. Quais mensagens podem sair sem `bridge_reply`?
   - Recomendação: ACK, status, cancelamento, timeout fixo, erro fixo, help, project/model/session commands e reactions.
   - Decisão:Recomendação

```text

```

7. Mensagens sistêmicas podem incluir texto dinâmico gerado pelo agente?
   - Recomendação: **Não**
   - Decisão: Recomendação

```text

```

8. `/last` pode mostrar trecho da resposta final?
   - Recomendação: **Só se já foi entregue via `bridge_reply` e redigido**
   - Decisão:Recomendação

```text

```

---

### C. Fallback e rollback

9. Se `bridge_reply` falhar tecnicamente, qual fallback é permitido?
   - Recomendação: retry + mensagem fixa + orientar `/last`; nunca enviar bruto.
   - Decisão:Recomendação

```text

```

10. A v2 deve rodar atrás de feature flag/toggle?
    - Recomendação: **Sim**
    - Decisão:Recomendação

```text

```

11. Qual é o critério de rollback para v1?
    - Sugestão: falha de entrega segura, perda de slash commands, perda de cancelamento, perda de project routing, regressão de sessão, raw output leak, chunk error.
    - Decisão:Recomendação

```text

```

---

### D. Project routing

12. Sem projeto selecionado, a bridge deve bloquear execução normal?
    - Recomendação: **Sim, sugerir `/project select`**
    - Decisão:não

```text

```

13. `/start` pode rodar sem projeto?
    - Opções: `Sim, workspace default` / `Não, exige projeto` / `Sim, mas sem tools e sem leitura`
    - Recomendação: **Sim, mas sem tools e sem leitura**
    - Decisão:Sim, workspace default

```text

```

14. Quais projetos entram no registry Dia 1?
    - Sugestão: `discord-openclaude-bridge`, `evo-nexus`
    - Decisão:todos

```text

```

15. `add_dirs` pode incluir diretórios fora do repo?
    - Recomendação: **Sim, mas só allowlist explícita e nunca secrets**
    - Decisão:Recomendação

```text

```

---

### E. Access policy

16. Para usuário MASTER, Bash fica liberado?
    - Recomendação: **Sim, explicitamente auditado**
    - Decisão:Recomendação

```text

```

17. Para usuário MASTER, Agents ficam liberados?
    - Recomendação: **Sim, explicitamente auditado**
    - Decisão:Recomendação

```text

```

18. Para usuário MASTER, Skills ficam liberadas Dia 1?
    - Recomendação: **Não no Dia 1; liberar depois por política explícita**
    - Decisão:Recomendação

```text

```

19. Haverá usuário read-only além do Eduardo?
    - Decisão:sim

```text

```

20. Haverá diferença entre permissão por usuário e por canal?
    - Decisão:sim

```text

```

---

### F. Slash/text commands

21. A v2 deve ser slash-first?
    - Recomendação: **Sim**
    - Decisão:sim

```text

```

22. Comandos textuais `/status`, `/cancel`, etc. continuam como fallback?
    - Recomendação: **Manter subset mínimo durante transição**
    - Decisão:Recomendação

```text

```

23. Slash commands lentos devem sempre usar defer/follow-up?
    - Recomendação: **Sim, especialmente `/start` e `/reset-session`**
    - Decisão:Recomendação

```text

```

---

### G. Progresso e milestones

24. Milestones de agentes devem aparecer no Discord?
    - Recomendação Dia 1: **Não como texto; só status controlado**
    - Decisão:Recomendação

```text

```

25. `/status` deve mostrar progresso de tool/agente?
    - Recomendação: **Enum redigido, sem argumentos/conteúdo**
    - Decisão:Recomendação

```text

```

26. Eventos de tool podem aparecer no `/last`?
    - Recomendação: **Só nomes redigidos e métricas, sem payload**
    - Decisão:Recomendação

```text

```

---

### H. Anexos

27. Anexos entram no Dia 1?
    - Recomendação: **Não, ou limitado explicitamente**
    - Decisão:sim

```text

```

28. Quais tipos são permitidos?

```text
.pdf, .doc, .docx, .md, .jpg, 
```

29. Qual limite de tamanho?

```text
10mb
```

30. Onde salvar?

```text
na pasta temp do workspace
```

31. O path do anexo pode aparecer no prompt? No Discord? No log?

```text
sim, todos
```

---

### I. Auditoria e redaction

32. Quais campos são obrigatórios no log de execução?
    - Sugestão: `execution_id`, `user_id`, `channel_id/thread_id`, `project_slug`, `cwd`, `add_dirs`, `model`, `session_id`, `allowed_tools`, `permission_mode`, `bridge_reply_called`, `final_status`, `cost/tokens`, `redacted_error`.
    - Decisão:use a Sugestão

```text

```

33. Quanto do prompt pode ser persistido?
    - Recomendação: preview redigido ou hash, não prompt completo por padrão.
    - Decisão:Recomendação

```text

```

34. Erros podem mostrar stack trace no Discord?
    - Recomendação: **Não**
    - Decisão:não

```text

```

35. Paths como `cwd` e `add_dirs` podem aparecer no `/last`?
    - Recomendação: **Sim se forem não sensíveis e úteis para auditoria**
    - Decisão:Recomendação

```text

```

---

## 3.1 Normalização Oracle para execução autônoma

Estas regras interpretam as decisões do Eduardo sem substituí-las. Os próximos agentes devem seguir esta leitura para evitar novas interrupções.

1. **Contrato oficial é mandatário.** A v2 deve ser compatível com o modelo Channel/Discord oficial.
2. **Gateway único é obrigatório.** Qualquer output gerado por agente/modelo só pode sair via `bridge_reply` / `OutboundGateway.reply()` ou equivalente.
3. **`bridge_reply` Dia 1 aceita múltiplas mensagens com `sequence`.** Não usar streaming livre sem contrato de chunk/idempotência.
4. **Mensagens sistêmicas permitidas sem `bridge_reply`:** ACK, status, cancelamento, timeout fixo, erro fixo, help, comandos project/model/session e reactions enum fixo.
5. **Mensagens sistêmicas não podem incluir texto dinâmico gerado pelo agente.** Só texto fixo, dados redigidos ou metadados operacionais.
6. **Dia 1 do produto v2 é amplo.** Inclui anexos, project new/create, permission relay, reactions/edit avançados e multi-channel/multi-project avançado conforme matriz do Eduardo.
7. **Spike continua limitado.** O spike de 1 dia útil deve provar arquitetura/gateway/isolamento; não precisa implementar todo o Dia 1 do produto.
8. **Sem projeto selecionado é permitido apenas com workspace default explícito e seguro.** Nunca cair implicitamente em `/home/evonexus`, `/home/evonexus/evo-projects` amplo ou diretório sensível.
9. **Fallback v1 não é base nem evolução.** Manter apenas até cutover validado como segurança operacional; remover após v2 estável.
10. **Remover definitivamente:** `result.text` direto ao Discord, stdout/stderr bruto, prompt como enforcement único, `channel.send` bruto, `interaction.followup.send` livre e milestones textuais livres.
11. **Anexos Dia 1:** permitidos conforme decisão, mas com limite de 10 MB, tipos permitidos e storage temporário seguro; paths podem aparecer em prompt/Discord/log apenas se forem temporários e não sensíveis.
12. **Critérios de aceite abaixo são obrigatórios para desenho/teste, não marcadores de conclusão.** Grid/Oath devem marcar conclusão com evidência depois.

---

## 4. Critérios de aceite que os próximos agentes devem obedecer

### 4.1 Canal seguro `bridge_reply` / gateway único

- [ ] Dado `bridge_reply` habilitado, quando OpenClaude retorna `result.text` sem chamar a tool, a bridge não envia `result.text` ao Discord.
- [ ] Dado `bridge_reply` chamado com token válido, quando callback entrega com sucesso, a bridge marca execução como “resposta segura entregue”.
- [ ] Dado `bridge_reply` chamado duas vezes com mesmo token, a segunda chamada é rejeitada ou ignorada de forma idempotente.
- [ ] Dado token inválido/expirado, nenhuma mensagem é enviada ao Discord.
- [ ] Dado erro no callback, o Discord recebe apenas mensagem sistêmica fixa, sem stdout/stderr bruto.

### 4.2 Bloqueio de caminhos laterais

- [ ] Nenhum output de agente chama diretamente `message.reply`.
- [ ] Nenhum output de agente chama diretamente `message.channel.send`.
- [ ] Nenhum output de agente chama diretamente `interaction.response.send_message`.
- [ ] Nenhum output de agente chama diretamente `interaction.followup.send`.
- [ ] Fallbacks de timeout/erro/cancelamento não incluem conteúdo bruto do modelo, stderr ou stack trace.
- [ ] Agent milestones não são enviados como texto livre quando v2 está ativa.

### 4.3 Must-haves v1 preservados, se aprovados acima

- [ ] `/status` funciona durante execução ativa.
- [ ] `/cancel` cancela subprocesso real.
- [ ] `/start` cria sessão leve.
- [ ] `/reset-session` preserva projeto e recria sessão.
- [ ] `/project select` altera cwd/add_dirs da próxima execução.
- [ ] Sessão é isolada por canal/tópico/projeto.
- [ ] Modelo por canal/tópico é preservado ou explicitamente removido do Dia 1.
- [ ] `/last` mostra auditoria redigida.

### 4.4 Project routing seguro

- [ ] Registry rejeita `/`, `/home`, `/home/evonexus`, `/home/evonexus/evo-projects` como projeto amplo.
- [ ] Registry rejeita `.ssh`, `.gnupg`, secrets, `/etc`, `/root`.
- [ ] Execução sem projeto é bloqueada ou segue comportamento aprovado neste documento.
- [ ] `cwd` real e `add_dirs` são auditados por execução.

### 4.5 Access policy

- [ ] Usuário não autorizado não dispara execução.
- [ ] Usuário autorizado sem `can_write` não recebe tools de escrita.
- [ ] Usuário sem `can_use_bash` não recebe Bash.
- [ ] Usuário sem projeto permitido não consegue selecionar projeto.
- [ ] Todas as permissões efetivas são auditáveis por execução.

---

## 5. Edge cases prioritários para teste

### Críticos

1. OpenClaude ignora instrução e não chama `bridge_reply`.
2. OpenClaude chama `bridge_reply` com token de outra execução.
3. OpenClaude chama `bridge_reply` duas vezes.
4. Execução é cancelada após `bridge_reply`, mas antes de persistir sucesso.
5. Timeout ocorre com stdout parcial sensível.
6. `message.reply` falha e fallback tenta `channel.send`.
7. Slash command demora mais que o limite do Discord.
8. Projeto ativo aponta para path sensível após mudança de config.

### Altos

9. Thread nova sem projeto recebe mensagem normal.
10. Usuário permitido tenta projeto não autorizado.
11. Anexo grande ou tipo não permitido.
12. Resposta final acima de 2.000 caracteres.
13. Erro no MCP server `bridge_reply`.
14. Bridge reinicia com execução em andamento.

---

## 6. Decisão final aprovada da Fase 1

Preencher quando Eduardo terminar as escolhas acima.

```text
Decisão final:

- Contrato oficial Channel/Discord: mandatário; v2 deve ser compatível com o modelo oficial.
- Gateway único: obrigatório para qualquer output gerado por agente/modelo.
- bridge_reply: múltiplas mensagens com sequence; sem streaming livre fora de contrato.
- Mensagens sistêmicas permitidas: ACK, status, cancelamento, timeout fixo, erro fixo, help, comandos project/model/session e reactions enum fixo.
- Must-have Dia 1: conforme matriz preenchida por Eduardo, incluindo escopo amplo de operação v2.
- Spike: limitado a provar arquitetura/gateway/isolamento em 1 dia útil; não precisa implementar todo o Dia 1 do produto.
- Pós-v2: skills via Discord permanecem Pós-v2; demais itens conforme matriz.
- Fallback v1: não será base nem evolução; manter apenas até cutover validado e remover após v2 estável.
- Remover: result.text direto, stdout/stderr bruto, prompt como enforcement único, channel.send bruto, followup livre e milestones textuais livres.
- Critérios de rollback: falha de entrega segura, perda de slash commands, perda de cancelamento, perda de project routing, regressão de sessão, raw output leak ou chunk error.
- Observações: workspace default concreto será `evo-nexus`; MASTER no default mantém Bash/Agents conforme policy auditada. Falha parcial de chunk: registrar parcial, retry apenas do chunk faltante quando seguro, `/last` redigido e nunca reenviar bruto. Auditoria de resposta entregue: hash + preview redigido por padrão; conteúdo completo só com flag explícita e retenção curta. Anexos não entram no spike funcional; no spike entram apenas testes do AttachmentStore/segurança com fixtures. Anexos entram no Dia 1 do produto depois que gateway passar.
```

**Status da decisão:**
- [x] Rascunho criado por Oracle
- [x] Eduardo preencheu decisões
- [x] Oracle revisou consistência
- [x] Aprovado para Apex criar ADR da Fase 2
