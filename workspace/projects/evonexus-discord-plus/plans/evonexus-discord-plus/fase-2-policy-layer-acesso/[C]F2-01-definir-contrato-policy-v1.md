---
author: claude
agent: oracle
type: work-plan-item
date: 2026-05-25
phase: 2
item-id: F2-01
status: done
---

# F2-01. Definir contrato de policy v1

**Fase:** Fase 2 — Policy layer de acesso
**Eixo:** Segurança / Produto / Configuração
**Tipo:** [DECIDIR]
**Prazo sugerido:** 0,5 dia

## O que é

Definir o formato da política de acesso v1 antes de implementar. O contrato precisa ser simples, explícito e suficiente para allowlist por guild/canal/thread/user e perfis.

## O que fazer

- Definir entidades suportadas no v1: guild, channel, thread, user e profile.
- Definir semântica de decisão: deny por padrão, allow explícito e precedência.
- Definir formato inicial da configuração: arquivo local, env JSON ou híbrido.
- Definir perfis mínimos: `admin`, `operator`, `readonly` ou equivalentes.
- Definir eventos que geram log de autorização.
- Registrar exemplos de policy permitida e negada.

## Agente / Skill / Rotina

@oracle conduz a decisão com Eduardo; @compass-planner estrutura critérios; @apex-architect valida contrato técnico; @vault-security e @raven-critic revisam segurança e bypass.

## O que o usuário precisa decidir/fornecer

- Confirmar perfis do v1.
- Confirmar se o default é `deny-by-default`.
- Confirmar se configuração v1 será arquivo, env JSON ou híbrida.
- Confirmar se DMs ficam bloqueadas ou permitidas para usuários allowlisted.

## Impacto esperado

Cria a “lei” de acesso antes do código, reduzindo ambiguidade e risco de bypass.

## Dependências

F1-03 concluído.

## Riscos

- Política flexível demais para v1.
- Política simples demais e incapaz de cobrir threads.
- Configuração acidentalmente incluir segredos ou IDs sensíveis em local inadequado.

## Agente sugerido pra implementação

**Time:** @oracle → @compass → @apex → @vault → @raven

| Fase | Agente | Papel |
|---|---|---|
| 1. Decisão | @oracle | Conduzir alinhamento com Eduardo |
| 2. Estrutura | @compass | Organizar critérios e opções |
| 3. Arquitetura | @apex | Validar contrato técnico |
| 4. Segurança | @vault | Revisar bypass e redaction |
| 5. Crítica | @raven | Pressionar riscos e ambiguidades |

**Por quê esse time:** item [DECIDIR] com impacto de segurança; precisa interação humana e revisão adversarial.

## Status

- [ ] Pendente
- [ ] Em progresso
- [x] Concluído
