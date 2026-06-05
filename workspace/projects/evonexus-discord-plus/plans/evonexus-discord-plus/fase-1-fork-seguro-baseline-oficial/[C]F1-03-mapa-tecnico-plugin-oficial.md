---
author: claude
agent: oracle
type: work-plan-item
date: 2026-05-25
phase: 1
item-id: F1-03
status: done
---

# F1-03. Mapa técnico do plugin oficial

**Fase:** Fase 1 — Fork seguro e baseline oficial
**Eixo:** Descoberta técnica / Planejamento de modificação
**Tipo:** [ATIVAR]
**Prazo sugerido:** 0,5 dia

## O que é

Mapear onde o plugin oficial recebe eventos, identifica guild/canal/thread/user, executa comandos e responde ao Discord. Esse mapa orienta a inserção da policy layer sem espalhar condicionais pelo código.

## O que fazer

- Identificar entrada de eventos/interações.
- Identificar o contexto disponível: guild id, channel id, thread id, user id e action/command.
- Identificar ponto único ideal para checagem de autorização.
- Identificar ponto de logging atual, se existir.
- Registrar proposta de inserção da policy layer sem modificar comportamento ainda.
- Marcar arquivos críticos a não refatorar no v1 salvo necessidade.

## Agente / Skill / Rotina

@scout-explorer faz busca estrutural; @apex-architect indica ponto de extensão com menor acoplamento; @raven-critic é opcional se houver alternativas arriscadas.

## O que o usuário precisa decidir/fornecer

Nada além da aprovação pra começar, salvo se houver mais de uma abordagem com trade-off relevante.

## Impacto esperado

Evita implementação espalhada e facilita revisão de segurança.

## Dependências

F1-01 concluído; preferencialmente F1-02 concluído.

## Riscos

- Código oficial não ter ponto único limpo de autorização.
- Exigir pequeno adapter/wrapper para não alterar demais o core.

## Agente sugerido pra implementação

**Time:** @scout → @apex → @raven opcional

| Fase | Agente | Papel |
|---|---|---|
| 1. Mapeamento | @scout | Localizar fluxo e contexto |
| 2. Arquitetura | @apex | Escolher ponto de inserção |
| 3. Crítica | @raven | Pressionar alternativas se houver risco |

**Por quê esse time:** a decisão de onde inserir policy define o custo de manutenção do fork.

## Status

- [ ] Pendente
- [ ] Em progresso
- [x] Concluído
