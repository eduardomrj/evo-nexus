---
author: claude
agent: oracle
type: work-plan-item
date: 2026-05-25
phase: 3
item-id: F3-04
status: done
---

# F3-04. Handoff final para build/verificação

**Fase:** Fase 3 — Smoke, documentação e backlog
**Eixo:** Orquestração / Execução controlada
**Tipo:** [ATIVAR]
**Prazo sugerido:** 0,25 dia

## O que é

Preparar o handoff para os agentes de engenharia implementarem e verificarem o v1 sem ambiguidade, mantendo fases e artefatos organizados dentro da pasta do plano.

## O que fazer

- Confirmar plano materializado em `workspace/development/plans/evonexus-discord-plus/[C]index-2026-05-25.md`.
- Criar lista de critérios de aceite do v1.
- Definir sequência recomendada: Scout, Apex, Bolt/Grid, Vault/Lens, Probe/Oath.
- Declarar explicitamente que implementação só começa após aprovação de Eduardo.
- Registrar decisões pendentes do usuário.
- Preparar handoff para @apex-architect ou @bolt-executor, conforme complexidade encontrada na F1.

## Agente / Skill / Rotina

@oracle coordena e entrega; @compass-planner sustenta o plano; @apex-architect entra se houver decisão estrutural; @bolt-executor implementa após aprovação; @oath-verifier verifica aceite final.

## O que o usuário precisa decidir/fornecer

- Aprovar início da execução.
- Confirmar se passa por Apex antes do Bolt.
- Confirmar destino/repo do fork.

## Impacto esperado

Evita execução prematura e garante trilha clara de responsabilidades.

## Dependências

F3-03 concluído e plano revisado por Eduardo.

## Riscos

- Pular Apex mesmo se a camada de policy exigir decisão estrutural.
- Executar sem decisões de destino/configuração.
- Misturar verificação manual com “parece funcionar”.

## Agente sugerido pra implementação

**Time:** @oracle → @compass → @apex → @bolt → @oath

| Fase | Agente | Papel |
|---|---|---|
| 1. Coordenação | @oracle | Confirmar decisões e aprovação |
| 2. Plano | @compass | Sustentar escopo |
| 3. Arquitetura | @apex | Resolver trade-offs |
| 4. Build | @bolt | Implementar |
| 5. Verify | @oath | Verificar evidências |

**Por quê esse time:** handoff final protege contra execução prematura e garante aceite evidence-based.

## Handoff final — 2026-05-26

### Estado entregue

O v1 do `evonexus-discord-plus` está entregue como fork seguro do Discord Channel oficial, sem importação do bridge custom e sem arquitetura por perfis.

Modelo final:

- autorização por usuário Discord + recurso + operação explícita;
- deny-by-default quando falta policy, usuário real, recurso ou operação permitida;
- tool-call MCP sem `user_id` real confiável nega antes de side effect;
- DMs bloqueadas por padrão, exceto usuários explicitamente listados em `dm.users`;
- `access.allowFrom` legado não concede `permission.respond`;
- `claude/channel/permission` não é anunciado sem contexto real confiável;
- logs de autorização em `stderr`, stdout preservado para MCP;
- logs de erro sanitizados;
- dependências auditadas sem vulnerabilidades conhecidas pelo Bun.

### Commits entregues no repo `evonexus-discord-plus`

- `4e4afaf` — snapshot oficial/base do Discord Channel plugin.
- `357ec58` — engine de autorização isolada inicial.
- `0fa666c` — integração da policy no runtime Discord.
- `0845ba7` — logs seguros de autorização.
- `dfeba3a` — refactor removendo autorização por perfis.
- `60d51e9` — dependências vulneráveis atualizadas; `bun audit` limpo.
- `a5f8434` — documentação operacional v1 em `ACCESS.md`.

### Evidência de verificação

- `bun test`: 38 pass / 0 fail.
- `bun audit`: `No vulnerabilities found`.
- F3-01 smoke local: PASS nos três gates:
  - Probe QA: 11/11 cenários PASS.
  - Oath: PASS.
  - Vault: APPROVE.
- F3-02 documentação:
  - Vault: APPROVE.
  - Oath: PASS.

Relatórios salvos:

- `workspace/development/verifications/[C]qa-evonexus-discord-plus-2026-05-26.md`
- `workspace/development/verifications/[C]verify-evonexus-discord-plus-f3-01-local-refactor-sem-perfis-2026-05-26.md`

### Critérios de aceite do v1

- [x] Parte do plugin oficial Discord, não do bridge custom.
- [x] Repo limpo e rastreável.
- [x] Policy layer isolada e testável.
- [x] Sem autorização por perfis/papéis.
- [x] Autorização por userId/recurso/operação explícita.
- [x] Deny-by-default para ausência de contexto confiável.
- [x] Acesso negado não executa side effects.
- [x] Logs seguros em `stderr`, sem poluir `stdout` MCP.
- [x] Testes locais verdes.
- [x] Audit de dependências limpo.
- [x] Documentação operacional mínima publicada em `ACCESS.md`.
- [x] Backlog v2+ separado e não bloqueante.

### Pendências não bloqueantes / próximo ciclo

1. Smoke real controlado em Discord de teste.
2. TTL e validação de `pendingPermissions.has(request_id)` para botões antigos.
3. Comando/skill para escrever policy v2 nativa, reduzindo dependência do formato legado.
4. Diagnóstico redigido de configuração efetiva.
5. `.env` / Vaultwarden / bootstrap operacional seguro.
6. Unit `systemd` separada para produção.
7. Logs JSONL com rotação/retenção.
8. `/health` operacional.
9. UX futura: ack reaction, resposta formatada e chunking melhor.

### Próximo responsável recomendado

- Para smoke real: Oracle coordena com Eduardo; Probe/Oath executam/verificam; Vault revisa relatório.
- Para operação produtiva: custom-sysops prepara `systemd` e segredos; Vault revisa; Oath verifica.
- Para policy v2 nativa: Bolt implementa; Lens/Vault/Oath revisam.

## Status

- [ ] Pendente
- [ ] Em progresso
- [x] Concluído
