---
author: claude
agent: oracle
type: work-plan-item
date: 2026-05-08
phase: 3
item-id: F3-01
status: partial
---

# F3-01. Implementar runner robusto com timeout, concorrência e cancelamento

**Fase:** Fase 3 — Robustez, testes e status avançado  
**Eixo:** confiabilidade  
**Tipo:** [EVOLUIR]  
**Prazo sugerido:** após POC mínima responder no Discord

## O que é

Evoluir a POC para evitar execuções fantasmas e dar feedback contínuo quando uma tarefa demorar. Este item resolve a dor principal: não saber se o agente está trabalhando ou travado.

## O que fazer

- Implementar timeout configurável e encerramento seguro do subprocess.
- Bloquear ou enfileirar execuções simultâneas por canal/usuário.
- Enviar status periódico “ainda trabalhando” após limite configurado.
- Implementar comandos textuais `/status` e `/cancel`.
- Garantir transição final obrigatória: `success`, `error`, `timeout` ou `cancelled`.

## Agente / Skill / Rotina

@bolt evolui o runner. @grid cobre concorrência, timeout e cancelamento. @hawk investiga bugs caso o processo fique preso.

## O que o usuário precisa decidir/fornecer

- Timeout padrão.
- Política de concorrência: bloquear, enfileirar ou permitir por usuário.
- Frequência de atualização de status para não gerar spam.

## Impacto esperado

O Discord passa a mostrar claramente se a execução está ativa, demorando, cancelada ou quebrada.

## Dependências

F2-01 e F2-02.

## Riscos

- Cancelar processo errado.
- Excesso de mensagens/status no canal.
- Corrida entre mensagens simultâneas.

## Agente sugerido pra implementação

**Time:** @compass → @bolt → @grid → @hawk → @oath

| Fase | Agente | Papel |
|---|---|---|
| 1. Spec | @compass | Definir política de concorrência/status |
| 2. Build | @bolt | Implementar runner robusto |
| 3. Testes | @grid | Testar timeout, concorrência e cancelamento |
| 4. Debug | @hawk | Diagnosticar travas/reprodução se necessário |
| 5. Verify | @oath | Confirmar critérios de aceite |

**Por quê esse time:** evolução de confiabilidade precisa de implementação cuidadosa, testes de borda e verificação independente.

## Resultado reconciliado

Parcial. Já existe timeout configurável, transição final de status, bloqueio de concorrência por canal e `/status`. O `/cancel` ainda é stub explícito no MVP e status periódico “ainda trabalhando” ainda não foi implementado.

## Validação real parcial

Validado em 2026-05-08 no tópico/canal de teste:

- `/status` funcionando.
- Bloqueio de concorrência por canal funcionando.

Implementado e validado por testes automatizados depois da validação inicial:

- Status periódico “ainda estou trabalhando” configurável por `DISCORD_OPENCLAUDE_BRIDGE_STATUS_UPDATE_SECONDS`.
- Valor atual em `.env`: `45` segundos.
- Split de respostas longas em chunks seguros de `1900` caracteres, respeitando limite real do Discord de `2000` caracteres.
- `/cancel` real: cancela a task ativa em memória, marca execução como `cancelled` no SQLite, encerra o subprocesso OpenClaude no runner assíncrono e foi validado manualmente no Discord.
- Testes automatizados passaram com `17 passed`.
- Teste real de resposta longa passou no tópico/canal com o novo bot.

Ainda pendente nesta fase: validação manual do `/cancel` real no tópico/canal.

## Reações Discord implementadas

A bridge usa reações para comunicar o estado externo da execução:

| Reação | Estado | Quando aparece |
|---|---|---|
| `👀` | Recebido | Mensagem aceita pela allowlist |
| `🛠️` | Executando | Execução iniciada no OpenClaude |
| `✅` | Sucesso | Execução terminou e resposta foi enviada |
| `❌` | Erro | Erro genérico da bridge/OpenClaude |
| `⏱️` | Timeout | Execução excedeu `DISCORD_OPENCLAUDE_BRIDGE_TIMEOUT_SECONDS` |
| `🛑` | Cancelado | Execução cancelada via `/cancel` |
| `🔒` | Ocupado | Nova mensagem chegou enquanto já havia execução ativa no canal |

Limite atual: essas reações representam o ciclo externo da bridge. A bridge ainda não reflete ações internas do OpenClaude em tempo real.

## Funcionalidade futura — streaming real do OpenClaude

A próxima evolução planejada é ler o `stdout` do OpenClaude linha a linha durante a execução, em vez de esperar o subprocesso terminar. Isso permitirá reagir a eventos internos do stream JSON, como:

- geração parcial de texto;
- identificação de `session_id` antes do final;
- eventos internos do OpenClaude quando disponíveis;
- status mais fiel durante tarefas longas;
- possível atualização incremental de mensagem em vez de resposta apenas no final.

Fluxo futuro desejado:

```text
Discord message
→ cria execução
→ inicia subprocesso OpenClaude
→ lê stream JSON em tempo real
→ interpreta eventos
→ atualiza status/reação/log durante a execução
→ envia resposta final em chunks seguros
```

---

## Status

- [ ] Pendente
- [x] Em progresso
- [ ] Concluído
