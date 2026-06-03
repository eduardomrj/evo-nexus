---
author: compass-planner
agent: compass-planner
type: prd
date: 2026-05-31
feature: discord-plus-project-context
status: delivered
mode: direct
---

# PRD — Discord Plus Project Context aditivo por canal/tópico

## Problema

O Discord Plus já opera com Hybrid CLI Engine, Oracle real via CLI, comandos `/model` e `/session`, e sessões publicadas/testadas. Hoje, porém, um canal ou tópico do Discord não consegue declarar qual projeto externo está ativo para aquele contexto de conversa.

Eduardo quer trabalhar em projetos como `/home/evonexus/evo-projects/go-control-erp` a partir de canais/tópicos específicos, sem perder a casa operacional do EvoNexus em `/home/evonexus/evo-nexus`, onde vivem agentes, skills, memória, políticas e runtime.

## Objetivos

- Permitir vincular um diretório de projeto a um canal ou tópico do Discord.
- Injetar o projeto ativo como contexto adicional no prompt das mensagens do canal/tópico.
- Manter o EvoNexus como `cwd`/home operacional nesta fase.
- Implementar apenas o modo `additive` inicialmente.
- Persistir vínculos por escopo de Discord de forma compatível com os stores existentes do Discord Plus.
- Proteger o host contra leitura indevida de filesystem, path traversal, symlinks perigosos e exposição de arquivos sensíveis.
- Exigir permissão específica para alterações de vínculo.

## Não objetivos

- Não trocar o `cwd` da sessão/engine nesta fase.
- Não criar modo workspace substitutivo.
- Não alterar o core do OpenClaude.
- Não mover agentes, skills, memória ou runtime para o projeto externo.
- Não expor listagem completa do filesystem.
- Não permitir roots genéricas como `/`, `/home`, `/root`, `/etc` ou home inteira.
- Não resetar/renovar sessão silenciosamente quando o projeto mudar.

## Usuários

- **Eduardo**: operador principal do Discord Plus, precisa alternar contexto de projeto por canal/tópico sem perder o ambiente operacional do EvoNexus.
- **Agentes via Discord Plus**: recebem contexto explícito do projeto ativo e usam esse caminho para leitura/código/testes quando solicitado.
- **Administradores do bot**: configuram allowlist de roots e permissões de comandos.

## Casos de uso

1. **Consultar projeto ativo**
   - Eduardo usa `/project current` em um canal/tópico e vê se há projeto vinculado, incluindo se o valor foi herdado do canal pai.

2. **Vincular projeto ao tópico atual**
   - Eduardo usa `/project set path:/home/evonexus/evo-projects/go-control-erp` em um tópico de trabalho.
   - As próximas mensagens no tópico passam a receber bloco curto de contexto com o path ativo.

3. **Remover vínculo**
   - Eduardo usa `/project clear` para remover o projeto do tópico/canal atual.
   - Mensagens posteriores deixam de receber o bloco `Active Discord Project`, salvo se houver herança do canal pai aplicável.

4. **Listar vínculos permitidos com segurança**
   - Eduardo usa `/project list` para ver vínculos configurados/permitidos sem expor árvore completa do filesystem.

5. **Herdar projeto do canal pai**
   - Um thread sem projeto próprio herda o projeto vinculado ao canal pai quando apropriado.
   - Se o thread tiver vínculo próprio, ele prevalece sobre o canal pai.

## Requisitos funcionais

### RF1 — Comando `/project current`

- Deve mostrar o projeto ativo do escopo atual.
- Deve informar o modo: `additive`.
- Deve indicar a origem do vínculo quando relevante: thread, channel ou herdado do canal pai.
- Deve ser permitido para usuários com permissão de leitura do Discord Plus.

### RF2 — Comando `/project set path:<path>`

- Deve validar que `path` existe e é diretório.
- Deve normalizar/canonicalizar o path antes de persistir.
- Deve aceitar apenas paths dentro de roots allowlisted.
- Deve persistir o vínculo no escopo atual: guild/channel/thread.
- Deve gravar modo `additive`.
- Deve exigir operação/permissão nova, recomendada como `project.context.write`.
- Deve responder com confirmação curta e recomendar `/session reset` quando já houver sessão ativa para o escopo.
- Não deve resetar, renovar ou salvar sessão automaticamente.

### RF3 — Comando `/project clear`

- Deve remover o vínculo explícito do escopo atual.
- Deve exigir `project.context.write`.
- Deve indicar se, após limpar, haverá herança do canal pai.
- Deve recomendar `/session reset` quando já houver sessão ativa para o escopo.
- Não deve resetar, renovar ou salvar sessão automaticamente.

### RF4 — Comando `/project list`

- Deve listar vínculos conhecidos e/ou roots permitidos de forma segura.
- Não deve varrer nem expor filesystem completo.
- Deve redigir ou ocultar informações sensíveis quando aplicável.
- Deve ser leitura apenas.

### RF5 — Resolução por escopo

- Deve suportar chave por guild/channel/thread.
- A resolução deve seguir precedência:
  1. vínculo explícito do thread;
  2. vínculo explícito do canal;
  3. nenhum projeto ativo.
- Para threads, deve herdar canal pai quando não houver vínculo explícito no thread.
- Deve evitar colisão entre guilds/canais com IDs distintos.

### RF6 — Injeção aditiva no prompt

- Enquanto existir projeto ativo resolvido para o escopo, cada mensagem enviada ao engine deve receber o bloco curto:

```markdown
## Active Discord Project
Path: <project_path>
Mode: additive

This path is the user's active project for this Discord thread/channel.
Use it for project-specific code/file work.
Keep EvoNexus as the operational home for agents, skills, memory, and policies.
```

- A recomendação é injeção persistente por mensagem enquanto o vínculo existir, não one-shot, para sobreviver a retomadas e conversas longas.
- O bloco deve ser curto e determinístico para minimizar custo de tokens.
- O bloco não deve substituir instruções de sistema, políticas, permissões ou configuração operacional do EvoNexus.

### RF7 — Storage

- Deve persistir em state dir do Discord Plus, seguindo padrão dos stores existentes.
- Deve armazenar no mínimo:
  - guildId;
  - channelId;
  - threadId quando aplicável;
  - canonicalPath;
  - mode=`additive`;
  - createdAt/updatedAt;
  - updatedBy;
  - source/scope.
- Deve ser robusto a restart do serviço.

### RF8 — Registro de comandos

- O registro de slash commands deve incluir `/model`, `/session` e `/project`.
- Deve preservar os comandos já publicados e não reintroduzir comandos antigos do discord-bridge.

## Segurança

- Allowlist inicial obrigatória: `/home/evonexus/evo-projects/`.
- Deve permitir roots adicionais apenas via env/config explícita, por exemplo `DISCORD_PLUS_PROJECT_ROOTS` ou nome equivalente definido na implementação.
- Deve rejeitar path traversal (`..`), path relativo inseguro e canonical path fora da allowlist.
- Deve resolver symlinks e bloquear symlink que escape da allowlist.
- Deve rejeitar arquivos, incluindo `.env`, secrets, chaves privadas e qualquer path que não seja diretório.
- Deve rejeitar roots sensíveis: `/`, `/etc`, `/root`, `/home`, `/home/evonexus` como root ampla, diretórios de sistema e home inteira.
- Deve não imprimir segredos, conteúdo de `.env` ou listagens completas do filesystem nas respostas.
- Deve aplicar autorização separada:
  - `/project current` e `/project list`: leitura;
  - `/project set` e `/project clear`: `project.context.write`.
- Deve registrar erro de validação de forma clara ao usuário sem revelar detalhes sensíveis.

## UX de comandos

### `/project current`

Resposta esperada quando há vínculo:

```text
Projeto ativo: /home/evonexus/evo-projects/go-control-erp
Modo: additive
Escopo: thread atual
Observação: EvoNexus continua como casa operacional.
```

Resposta esperada com herança:

```text
Projeto ativo: /home/evonexus/evo-projects/go-control-erp
Modo: additive
Escopo: herdado do canal pai
```

Resposta esperada sem vínculo:

```text
Nenhum projeto ativo configurado para este canal/tópico.
```

### `/project set path:<path>`

Resposta esperada:

```text
Projeto vinculado a este tópico/canal em modo additive: <path>
EvoNexus permanece como casa operacional. Se já havia uma sessão ativa, recomendo rodar /session reset para evitar contexto antigo.
```

### `/project clear`

Resposta esperada:

```text
Vínculo de projeto removido deste escopo.
Se já havia uma sessão ativa, recomendo rodar /session reset para evitar contexto antigo.
```

### `/project list`

Resposta esperada:

```text
Projetos/vínculos conhecidos:
- #nexus-bridge → /home/evonexus/evo-projects/go-control-erp (additive)
Roots permitidas:
- /home/evonexus/evo-projects/
```

A listagem deve vir do store/config, não de varredura indiscriminada do filesystem.

## Critérios de aceite Given/When/Then

### CA1 — Consultar sem projeto configurado

Given um canal sem vínculo explícito e sem herança aplicável  
When Eduardo executa `/project current`  
Then o bot responde que não há projeto ativo configurado para aquele canal/tópico.

### CA2 — Vincular path válido

Given Eduardo tem permissão `project.context.write` e `/home/evonexus/evo-projects/go-control-erp` existe como diretório dentro da allowlist  
When ele executa `/project set path:/home/evonexus/evo-projects/go-control-erp`  
Then o vínculo é persistido para o escopo atual em modo `additive`  
And `/project current` mostra esse path como projeto ativo.

### CA3 — Bloquear path fora da allowlist

Given Eduardo tenta vincular `/etc` ou `/root`  
When ele executa `/project set path:/etc`  
Then o comando falha com erro seguro  
And nenhum vínculo é persistido.

### CA4 — Bloquear path traversal/symlink perigoso

Given um path com `..` ou symlink que resolve para fora das roots permitidas  
When o usuário executa `/project set path:<path>`  
Then o comando rejeita o path após canonicalização  
And a resposta não expõe detalhes sensíveis do filesystem.

### CA5 — Bloquear arquivo e `.env`

Given o path informado aponta para arquivo, `.env` ou segredo  
When o usuário executa `/project set path:<path>`  
Then o comando rejeita porque apenas diretórios permitidos podem ser vinculados.

### CA6 — Herança de canal pai em thread

Given um canal pai tem projeto vinculado  
And o thread atual não tem vínculo próprio  
When uma mensagem é enviada no thread  
Then o projeto do canal pai é resolvido como ativo  
And o bloco `Active Discord Project` é injetado no prompt.

### CA7 — Override por thread

Given um canal pai tem projeto A vinculado  
And o thread atual tem projeto B vinculado  
When uma mensagem é enviada no thread  
Then o projeto B é usado  
And o projeto A não é injetado.

### CA8 — Injeção persistente e aditiva

Given um projeto ativo está resolvido para o escopo  
When qualquer mensagem posterior é enviada ao engine  
Then o prompt inclui o bloco `## Active Discord Project`  
And o `cwd` operacional permanece EvoNexus  
And o modo exibido é `additive`.

### CA9 — Mudança de projeto não reseta sessão silenciosamente

Given existe uma sessão ativa no escopo atual  
When Eduardo executa `/project set` ou `/project clear`  
Then o bot não executa reset/renew/save automaticamente  
And a resposta recomenda `/session reset` ou pede confirmação conforme UX implementada.

### CA10 — Autorização de escrita

Given um usuário sem `project.context.write`  
When executa `/project set` ou `/project clear`  
Then o comando é negado  
And nenhum vínculo é alterado.

### CA11 — Registro de comandos

Given os comandos slash são registrados/publicados  
When a rotina de registro roda  
Then `/model`, `/session` e `/project` estão presentes  
And comandos antigos do discord-bridge não reaparecem.

### CA12 — Testes automatizados

Given a suite de testes do repo está disponível  
When `bun test` roda  
Then passam testes de validação de path/allowlist, store por scope, comandos current/set/clear/list, autorização write, injeção aditiva e registro de comandos.

## Riscos

- **Confusão entre projeto ativo e casa operacional**: mitigado por bloco explícito dizendo que EvoNexus continua como home operacional.
- **Vazamento de filesystem**: mitigado por allowlist, canonicalização, bloqueio de symlinks fora da root e listagem baseada em store/config.
- **Contexto antigo em sessão já ativa**: mitigado por recomendação explícita de `/session reset`, sem reset silencioso.
- **Permissão ampla demais**: mitigado por operação separada `project.context.write`.
- **Crescimento de escopo para troca de cwd**: mitigado por declarar modo `additive` como único modo desta fase e tratar troca de cwd apenas como futuro opcional.
- **Regressão nos comandos existentes**: mitigado por testes de registro preservando `/model` e `/session`.
