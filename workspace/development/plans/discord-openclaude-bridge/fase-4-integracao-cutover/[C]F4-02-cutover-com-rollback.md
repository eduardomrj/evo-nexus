---
author: claude
agent: oracle
type: work-plan-item
date: 2026-05-08
phase: 4
item-id: F4-02
status: blocked-until-test-validation
---

# F4-02. Cutover com rollback

**Fase:** Fase 4 — Integração EvoNexus e cutover controlado  
**Eixo:** operacao  
**Tipo:** [DECIDIR]  
**Prazo sugerido:** depois de 1-2 dias de validação em canal de teste

## O que é

Planejar e executar a troca do Discord Channel oficial para a bridge própria apenas quando houver evidência de estabilidade, com rollback simples e documentado.

## O que fazer

- Rodar a bridge por 1-2 dias em canal de teste.
- Definir janela de troca e critério de sucesso.
- Parar `make discord-channel` apenas na janela aprovada.
- Ativar bridge no canal principal e monitorar logs/status.
- Manter rollback documentado: voltar com `make discord-channel` se a bridge falhar.

## Agente / Skill / Rotina

@custom-sysops conduz operação se envolver serviço persistente. @oath verifica estado final. Oracle mantém comunicação e decisão com o usuário.

## O que o usuário precisa decidir/fornecer

- Janela de troca.
- Critério de sucesso.
- Confirmação explícita para parar o channel oficial na hora do cutover.

## Impacto esperado

Substitui o fluxo atual por uma experiência com status e rastreabilidade, sem perder capacidade de voltar ao canal oficial.

## Dependências

F3-02 e F4-01 aprovados.

## Riscos

- Respostas duplicadas se os dois serviços ficarem ativos no mesmo canal.
- Interrupção do atendimento se a bridge falhar em produção.
- Rollback não testado.

## Agente sugerido pra implementação

**Time:** @oracle → @custom-sysops → @oath

| Fase | Agente | Papel |
|---|---|---|
| 1. Decisão | @oracle | Alinhar janela, riscos e confirmação |
| 2. Operação | @custom-sysops | Executar troca/serviço com segurança |
| 3. Verify | @oath | Confirmar evidências pós-cutover |

**Por quê esse time:** cutover é operação de produção; precisa de confirmação humana, execução segura e verificação independente.

## Status

- [x] Pendente
- [ ] Em progresso
- [ ] Concluído
