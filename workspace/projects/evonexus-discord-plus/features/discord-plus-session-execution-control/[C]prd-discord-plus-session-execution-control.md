# PRD — Discord Plus Session Execution Control

## Contexto

O Discord Plus já consegue executar o OpenClaude/Oracle via CLI em tópicos com Project Context ativo, usando o projeto ativo como `cwd` e `/home/evonexus/evo-nexus` via `--add-dir`. Durante o uso real no tópico CPSMQ (`1504105580501926049`), surgiram dois gaps de UX/controle:

1. Execuções longas ficam silenciosas, então o usuário não sabe se o agente está trabalhando ou travado.
2. Múltiplas mensagens podem abrir múltiplos processos CLI simultâneos no mesmo tópico/sessão, gerando confusão e processos pendurados.

## Objetivo

Dar previsibilidade operacional ao Discord Plus durante execuções longas, sem inventar progresso interno e sem tocar no Discord oficial.

## Não objetivos

- Não alterar o Discord oficial/plugin oficial.
- Não alterar o core do OpenClaude.
- Não expor chain-of-thought ou inferir passos internos do modelo.
- Não enviar mensagens falsas do tipo “estou editando X” sem evento real.
- Não mudar política de autorização MASTER/non-MASTER.

## Usuário alvo

Eduardo usando Discord Plus em tópicos de projeto, principalmente para execução com ferramentas locais e agentes EvoNexus.

## Problemas

### Gap 1 — Sem feedback em execuções longas

Quando uma execução demora, o usuário não sabe se:

- o OpenClaude ainda está rodando;
- o processo travou;
- o Discord Plus perdeu a resposta;
- outra mensagem pode ser enviada;
- é melhor aguardar ou cancelar.

### Gap 2 — Sem trava/cancelamento por sessão

Hoje é possível ter mais de um processo CLI filho do Discord Plus associado ao mesmo tópico/projeto. Isso causa:

- concorrência não intencional;
- múltiplas respostas fora de ordem;
- processos `claude/openclaude` vivos sem visibilidade;
- dificuldade de saber qual execução deve ser cancelada.

## Requisitos funcionais

### RF1 — Ack imediato

Ao receber uma mensagem que dispara execução CLI, o Discord Plus deve confirmar recebimento rapidamente.

Exemplo:

```text
Recebido. Estou processando esta solicitação.
```

Critérios:

- Deve acontecer antes da execução longa.
- Deve respeitar permissões/policy existentes.
- Deve preferir editar uma mensagem de status, se o Discord permitir.

### RF2 — Progress notification honesta

Enquanto o processo CLI estiver vivo, enviar/editar status periódico baseado apenas em fatos observáveis.

Exemplos:

```text
⏳ Ainda trabalhando... 1m30s decorridos.
⏳ Ainda trabalhando... processo ativo, sem resposta final ainda.
```

Critérios:

- Primeira atualização após 30s.
- Depois a cada 90s.
- Limite configurável, sugerido: 10 atualizações.
- Parar quando execução terminar, falhar, timeout ou for cancelada.
- Não inventar progresso interno.

### RF3 — Lock por `sessionKey`

Antes de iniciar execução CLI, o Discord Plus deve verificar se já existe execução ativa para a mesma `sessionKey`.

Se existir, responder:

```text
Já existe uma execução em andamento neste tópico há Xm. Use /session cancel para interromper ou aguarde a conclusão.
```

Critérios:

- Lock deve ser por `sessionKey`, não global.
- Diferentes tópicos podem executar em paralelo.
- Lock é liberado em `finally`, inclusive em erro/timeout.
- Deve ter janitor/TTL para evitar lock órfão.

### RF4 — `/session cancel`

Adicionar subcomando para cancelar execução ativa da sessão/tópico atual.

Exemplo:

```text
/session cancel
```

Critérios:

- Cancela apenas a execução da `sessionKey` atual.
- Envia `SIGTERM` primeiro.
- Se não encerrar em janela curta, pode escalar para `SIGKILL`.
- Responde se não houver execução ativa.
- Não afeta Discord oficial nem outras sessões/tópicos.

### RF5 — Status da execução no `/session status`

Adicionar ao status:

```text
execution: running|idle
elapsed: XmYs
pid: redacted/optional
```

Critérios:

- Não expor dados sensíveis.
- Pode omitir PID no Discord e manter só em log.

## Requisitos não funcionais

- Sem vazamento de tokens/env/secrets.
- Respeitar rate limit do Discord.
- Mensagens de status devem ser curtas.
- Testes automatizados para lock, cancel, timeout e progress timer.
- Compatível com engine CLI atual e rollback SDK sem regressão.

## Critérios de aceite

### Cenário 1 — Execução longa visível

Dado um tópico com Project Context ativo  
Quando o usuário envia uma tarefa que demora mais de 30s  
Então o Discord Plus envia ou edita status informando que continua trabalhando  
E continua atualizando periodicamente até concluir ou falhar.

### Cenário 2 — Segunda mensagem durante execução ativa

Dado que há uma execução ativa na mesma `sessionKey`  
Quando o usuário envia outra mensagem que dispararia CLI  
Então o Discord Plus não inicia novo processo  
E responde que já há execução em andamento, sugerindo `/session cancel`.

### Cenário 3 — Cancelamento

Dado que há execução ativa na sessão atual  
Quando o usuário roda `/session cancel`  
Então o processo CLI é encerrado  
E o lock é liberado  
E o Discord Plus informa cancelamento.

### Cenário 4 — Cancel sem execução

Dado que não há execução ativa na sessão atual  
Quando o usuário roda `/session cancel`  
Então o Discord Plus responde que não há execução em andamento.

### Cenário 5 — Execuções em tópicos diferentes

Dado dois tópicos diferentes  
Quando ambos recebem tarefas longas  
Então cada um pode executar em paralelo  
E cada lock/progress fica isolado por `sessionKey`.

## Riscos

- Spam de status no Discord se o timer não for limpo corretamente.
- Processo filho órfão se cancelamento falhar.
- Respostas fora de ordem se uma execução antiga terminar depois de cancelada.
- Locks órfãos se o processo do Plus cair.

## Mitigações

- Timer sempre limpo em `finally`.
- Registry de execução ativa com `startedAt`, `sessionKey`, child process e cleanup.
- `cancelled` flag para descartar resposta tardia.
- TTL/janitor para locks antigos.
- Testes com fake child process.

## Evidência da necessidade

Na sessão de 2026-06-01, o Discord Plus apresentou dois processos CLI filhos simultâneos no tópico CPSMQ, ambos com `cwd=/home/evonexus/evo-projects/cpsmq`. O serviço systemd continuava `active`, mas a UX parecia travada porque não havia feedback periódico nem comando de cancelamento por sessão.
