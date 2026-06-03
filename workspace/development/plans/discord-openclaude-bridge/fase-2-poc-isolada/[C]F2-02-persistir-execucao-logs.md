---
author: claude
agent: oracle
type: work-plan-item
date: 2026-05-08
phase: 2
item-id: F2-02
status: completed
---

# F2-02. Persistir execução e logs

**Fase:** Fase 2 — POC isolada  
**Eixo:** observabilidade  
**Tipo:** [CONSTRUIR NOVO]  
**Prazo sugerido:** junto ou logo após F2-01

## O que é

Registrar cada execução da bridge com estado, timestamps, stdout/stderr e resultado. Isso cria o rastro necessário para diagnosticar se uma tarefa está trabalhando, travada, em erro ou concluída.

## O que fazer

- Criar schema SQLite para execuções com status `started`, `running`, `success`, `error`, `timeout`, `cancelled`.
- Salvar `message_id`, `channel_id`, `user_id`, prompt, timestamps e duração.
- Salvar stdout/stderr em arquivos por execução dentro de `logs/`.
- Criar logs JSONL com transições de estado e erros.
- Garantir que tokens e segredos nunca sejam gravados em logs.

## Agente / Skill / Rotina

@bolt implementa persistência. @grid cobre transições de status. @vault revisa risco de vazamento de segredo, se necessário.

## O que o usuário precisa decidir/fornecer

Política de retenção de logs e nível de detalhe permitido para mensagens/prompt.

## Impacto esperado

Permite responder “o que aconteceu?” quando o bot parece travado. Também prepara base para dashboard/status futuro.

## Dependências

F2-01 iniciado ou concluído.

## Riscos

- Logar dados sensíveis do Discord ou prompt.
- Crescimento de logs sem retenção.
- Divergência entre status no Discord e status persistido.

## Agente sugerido pra implementação

**Time:** @compass → @bolt → @grid → @vault → @oath

| Fase | Agente | Papel |
|---|---|---|
| 1. Spec | @compass | Definir campos mínimos e retenção |
| 2. Build | @bolt | Implementar SQLite e JSONL |
| 3. Testes | @grid | Validar transições e persistência |
| 4. Segurança | @vault | Revisar risco de segredo em log |
| 5. Verify | @oath | Confirmar evidência de logs/status |

**Por quê esse time:** observabilidade com dados de usuário precisa de testes e cuidado com segurança.

## Resultado reconciliado

Concluído em código. A POC já cria SQLite para execuções, registra status, persiste prompt/resultado/erro e grava eventos JSONL em `logs/`. A validação real depende de iniciar o novo bot.

## Status

- [ ] Pendente
- [ ] Em progresso
- [x] Concluído
