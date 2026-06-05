---
author: claude
agent: oracle
type: work-plan-item
date: 2026-05-25
phase: 3
item-id: F3-01
status: done
---

# F3-01. Smoke test de segurança v1

**Fase:** Fase 3 — Smoke, documentação e backlog
**Eixo:** Verificação / Segurança / Aceitação
**Tipo:** [ATIVAR]
**Prazo sugerido:** 0,5 dia

## O que é

Validar o v1 com cenários manuais e/ou automatizados cobrindo acesso permitido e negado por guild, canal, thread, user e operação explícita.

## O que fazer

- Criar matriz de smoke para guild/canal/thread/user/perfis permitidos e negados.
- Executar smoke em ambiente controlado.
- Confirmar que deny não executa side effects.
- Confirmar que allow mantém comportamento equivalente ao oficial.
- Confirmar que logs de autorização aparecem para allow e deny.
- Registrar evidência em documento de verificação.

## Agente / Skill / Rotina

@probe-qa executa smoke interativo; @oath-verifier produz evidência formal; @vault-security valida cenários de bypass; @grid-tester complementa com testes automatizados.

## O que o usuário precisa decidir/fornecer

- Quais guilds/canais/users reais usar no smoke.
- Se o smoke ocorrerá em servidor Discord de teste ou ambiente real controlado.

## Impacto esperado

Dá confiança mínima para usar o plugin sem expor todos os canais/users.

## Dependências

F2-03 e F2-04 concluídos; IDs reais ou fake de teste definidos.

## Riscos

- Smoke em ambiente real causar ruído em canal.
- Testar só allow e esquecer deny.
- Não validar threads, que costumam ter comportamento diferente de canais.

## Agente sugerido pra implementação

**Time:** @probe → @oath → @vault → @grid

| Fase | Agente | Papel |
|---|---|---|
| 1. QA | @probe | Executar smoke Discord |
| 2. Verify | @oath | Formalizar evidências |
| 3. Segurança | @vault | Validar bypass |
| 4. Testes | @grid | Complementar automação |

**Por quê esse time:** smoke de segurança precisa de teste real e verificação independente.

## Status

- [ ] Pendente
- [ ] Em progresso
- [x] Concluído
