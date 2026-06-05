---
author: claude
agent: oracle
type: work-plan-item
date: 2026-05-25
phase: 3
item-id: F3-03
status: done
---

# F3-03. Backlog v2+ documentado e separado

**Fase:** Fase 3 — Smoke, documentação e backlog
**Eixo:** Roadmap / Controle de escopo
**Tipo:** [DECIDIR]
**Prazo sugerido:** 0,25 dia

## O que é

Registrar explicitamente o que ficou fora do v1, agrupando backlog por valor e risco, para evitar creep durante a implementação da segurança.

## O que fazer

- Criar seção “Backlog fora do v1”.
- Registrar UX/controle: ack reaction, resposta formatada, chunking melhor e `/health`.
- Registrar operação EvoNexus: `.env`/Vaultwarden, logs JSONL, diagnóstico redigido e `systemd` separado.
- Classificar cada item como v2, v3 ou “avaliar”.
- Indicar dependências com o v1.
- Marcar que backlog não bloqueia aceite do v1.

## Agente / Skill / Rotina

@oracle conduz a decisão; @compass-planner estrutura backlog; @helm-conductor pode sequenciar com outras frentes Discord; @vault-security prioriza operação segura futura.

## O que o usuário precisa decidir/fornecer

- Prioridade inicial pós-v1: UX/controle primeiro ou operação EvoNexus primeiro.
- Se `/health` entra em v2 imediato ou fica junto com operação.

## Impacto esperado

Mantém foco do v1 em segurança/acesso e evita reabrir discussão durante build.

## Dependências

Escopo v1 confirmado e lista de backlog aprovada por Eduardo.

## Riscos

- Backlog virar requisito implícito do v1.
- Operação ficar adiada demais e dificultar produção.
- UX ruim causar percepção de falha mesmo com segurança funcionando.

## Agente sugerido pra implementação

**Time:** @oracle → @compass → @helm → @vault

| Fase | Agente | Papel |
|---|---|---|
| 1. Decisão | @oracle | Conduzir prioridades com Eduardo |
| 2. Estrutura | @compass | Organizar backlog |
| 3. Sequenciamento | @helm | Ordenar próximas frentes |
| 4. Segurança | @vault | Priorizar riscos operacionais |

**Por quê esse time:** item [DECIDIR] evita scope creep e mantém v1 focado.

## Status

- [ ] Pendente
- [ ] Em progresso
- [x] Concluído

## Backlog fora do v1

### v2 imediato — segurança operacional

- **Smoke real controlado** — validar em guild/canal/thread/user de teste, com IDs e token fora do relatório.
- **TTL para `pendingPermissions` antigas** — expirar requests antigos e validar `pendingPermissions.has(request_id)` antes de enviar qualquer notification.
- **Policy v2 nativa no comando/skill de acesso** — parar de depender da conversão do formato legado para escrever configurações novas.
- **Diagnóstico redigido** — comando/check que imprime config efetiva sem tokens, prompts, payloads ou conteúdo de mensagens.

### v2 — operação EvoNexus

- **`.env` / Vaultwarden** — documentar item Vaultwarden, variáveis mínimas e bootstrap local seguro sem imprimir segredo.
- **`systemd` separado** — unit dedicada para `evonexus-discord-plus`, sem misturar com bridge custom.
- **Logs JSONL operacionais** — persistência local com rotação/retenção, mantendo `stderr` seguro para runtime MCP.
- **Health check operacional** — comando `/health` ou script local para versão, audit, status de conexão e policy carregada.

### v3 — UX e controle

- **Ack reaction** — reação curta para indicar recebimento sem poluir canal.
- **Resposta formatada** — padronizar respostas longas/erros sem vazar detalhes internos.
- **Chunking melhor** — divisão segura de respostas grandes, com preservação de contexto.
- **Permissões interativas v2** — reavaliar relay de permissão somente quando houver `user_id` real e recurso original confiável no runtime.

### Avaliar depois

- Comparação automatizada com plugin oficial para equivalência de allow em Discord real.
- Dashboard simples de auditoria de decisões de autorização.
- Migração assistida do `access.json` legado para policy v2 nativa.

## Nota de escopo

Este backlog não bloqueia o aceite do v1. O v1 entregue cobre fork oficial, policy fail-closed por usuário/recurso/operação, logs seguros, testes locais, audit limpo e documentação operacional mínima.
