---
author: claude
agent: oracle
type: work-plan-item
date: 2026-05-25
phase: 2
item-id: F2-02
status: done
---

# F2-02. Implementar engine de autorização isolada

**Fase:** Fase 2 — Policy layer de acesso
**Eixo:** Segurança / Core técnico
**Tipo:** [CONSTRUIR NOVO]
**Prazo sugerido:** 1 dia

## O que é

Criar uma policy layer isolada, testável e sem dependência direta do Discord SDK, recebendo um contexto normalizado e retornando uma decisão de autorização.

## O que fazer

- Criar `AuthorizationContext` com guild id, channel id, thread id, user id, profile e action/command.
- Criar `AuthorizationDecision` com allowed, reason code, matched rule e safe log fields.
- Implementar `authorize(context, policy)`.
- Implementar deny-by-default.
- Implementar precedência conforme F2-01.
- Adicionar testes unitários para guild/canal/thread/user/operação/ausência de regra/conflitos.

## Agente / Skill / Rotina

@bolt-executor implementa; @grid-tester cria testes; @vault-security revisa bypass; @lens-reviewer revisa qualidade.

## O que o usuário precisa decidir/fornecer

Apenas se a implementação revelar conflito não resolvido no contrato.

## Impacto esperado

Entrega o núcleo do v1 sem acoplar a regra de segurança ao transporte Discord.

## Dependências

F2-01 aprovado e F1-03 com ponto de inserção identificado.

## Riscos

- Misturar autorização com parsing de Discord.
- Testar só happy path.
- Não registrar reason code suficiente para auditoria.

## Agente sugerido pra implementação

**Time:** @compass → @apex → @bolt → @grid → @vault → @lens → @oath

| Fase | Agente | Papel |
|---|---|---|
| 1. Plano | @compass | Quebrar build em 3-6 passos |
| 2. Arquitetura | @apex | Confirmar isolamento da engine |
| 3. Build | @bolt | Implementar engine |
| 4. Testes | @grid | Cobrir matriz de autorização |
| 5. Segurança | @vault | Revisar bypass/fail-closed |
| 6. Review | @lens | Revisar qualidade |
| 7. Verify | @oath | Verificar evidências |

**Por quê esse time:** construção nova com impacto de segurança exige testes e revisão antes de uso.

## Status

- [ ] Pendente
- [ ] Em progresso
- [x] Concluído
