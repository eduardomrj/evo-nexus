---
author: claude
agent: oracle
type: work-plan-item
date: 2026-04-17
phase: 1
item-id: F1-006
status: pending
---

# F1-006. Atlas — Monitoramento GitHub Automático

**Fase:** 1 — Quick Wins
**Eixo:** Engineering
**Tipo:** [ATIVAR]
**Prazo sugerido:** Sem 2

## O que é

Ativar o heartbeat do Atlas para monitorar os repositórios GitHub da Automação Software 3x por semana: PRs abertas, issues sem resposta, builds quebrados. Eduardo recebe alerta se algo fica parado > 48h sem ação.

## O que fazer

- Habilitar heartbeat `atlas-4h` em `config/heartbeats.yaml` com decision prompt focado nos repos da Automação Software (Emporion, GO Platform, SERKET)
- Configurar `int-github-review` com token GitHub apontando para os repos relevantes
- Ativar rotina periódica `int-github-review` (Mon/Wed/Fri 09:15)
- Vincular issues do GitHub aos goals criados em F1-004 via `goal_id`

## Agente / Skill / Rotina

`@atlas-project` + heartbeat `atlas-4h` + skill `int-github-review` + rotina periódica Mon/Wed/Fri

## O que o usuário precisa decidir/fornecer

- Lista de repositórios a monitorar (Emporion Desktop? GO? SERKET? todos?)
- Token GitHub com permissão de leitura nos repos (privados precisam de token com `repo` scope)
- Quer alerta via Telegram ou Discord quando issue fica > 48h sem resposta?

## Impacto esperado

Nenhuma PR esquecida. Issues sem resposta > 48h geram alerta. Eduardo sabe o estado do desenvolvimento sem entrar no GitHub.

## Dependências

- Repositórios no GitHub com issues habilitadas
- Token GitHub configurado no workspace

## Riscos

- Repos privados precisam de token com escopo adicional — mitigação: configurar com `repo` scope desde o início

## Agente sugerido pra implementação

**Agente:** @atlas-project

**Por quê:** item [ATIVAR] direto — Atlas é o dono do domínio de projetos e GitHub.

## Status

- [x] Pendente
- [ ] Em progresso
- [ ] Concluído
