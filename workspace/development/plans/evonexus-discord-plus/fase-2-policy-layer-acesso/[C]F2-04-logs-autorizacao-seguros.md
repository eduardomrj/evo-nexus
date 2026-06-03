---
author: claude
agent: oracle
type: work-plan-item
date: 2026-05-25
phase: 2
item-id: F2-04
status: done
---

# F2-04. Logs de autorização seguros

**Fase:** Fase 2 — Policy layer de acesso
**Eixo:** Auditoria / Segurança / Operação mínima
**Tipo:** [CONSTRUIR NOVO]
**Prazo sugerido:** 0,5 a 1 dia

## O que é

Registrar decisões de autorização de forma útil para diagnóstico e auditoria, sem vazar token, prompt, conteúdo sensível ou dados além do necessário.

## O que fazer

- Definir campos permitidos: timestamp, action/command, guild id, channel id, thread id, user id, allowed, reason code e matched rule seguro.
- Proibir logs de token, conteúdo completo da mensagem, prompt completo, secrets/env e stack trace com dados sensíveis.
- Implementar logger simples do v1.
- Garantir logs para allow e deny.
- Adicionar testes ou smoke demonstrando os dois casos.
- Documentar que JSONL operacional completo fica no backlog, fora do v1.

## Agente / Skill / Rotina

@bolt-executor implementa; @vault-security revisa redaction; @oath-verifier registra evidência; @lens-reviewer revisa clareza e manutenção.

## O que o usuário precisa decidir/fornecer

- Destino v1 dos logs: stdout, arquivo local simples ou ambos.
- Retenção de logs fica fora do v1 ou recebe recomendação mínima.

## Impacto esperado

Permite entender por que uma interação foi permitida ou negada sem abrir risco operacional.

## Dependências

F2-02 concluído; preferencialmente F2-03 concluído.

## Riscos

- Logar conteúdo sensível por conveniência.
- Logs insuficientes para diagnosticar falso negativo.
- Log de deny revelar regra interna ao usuário final.

## Agente sugerido pra implementação

**Time:** @compass → @bolt → @vault → @lens → @oath

| Fase | Agente | Papel |
|---|---|---|
| 1. Plano | @compass | Definir escopo do logger |
| 2. Build | @bolt | Implementar logs |
| 3. Segurança | @vault | Revisar redaction |
| 4. Review | @lens | Revisar manutenção |
| 5. Verify | @oath | Evidenciar logs allow/deny |

**Por quê esse time:** logs de segurança precisam ser úteis sem virar vazamento.

## Status

- [ ] Pendente
- [ ] Em progresso
- [x] Concluído
