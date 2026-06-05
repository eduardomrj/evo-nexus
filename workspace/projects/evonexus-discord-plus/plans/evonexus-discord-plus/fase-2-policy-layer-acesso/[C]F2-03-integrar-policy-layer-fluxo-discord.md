---
author: claude
agent: oracle
type: work-plan-item
date: 2026-05-25
phase: 2
item-id: F2-03
status: done
---

# F2-03. Integrar policy layer no fluxo do plugin Discord

**Fase:** Fase 2 — Policy layer de acesso
**Eixo:** Integração / Segurança em runtime
**Tipo:** [EVOLUIR]
**Prazo sugerido:** 1 dia

## O que é

Conectar a engine de autorização ao fluxo real do plugin oficial, bloqueando execuções não autorizadas antes de qualquer ação sensível.

## O que fazer

- Normalizar contexto Discord para `AuthorizationContext`.
- Inserir chamada de autorização no ponto único definido em F1-03.
- Garantir que a checagem ocorra antes de comandos, respostas sensíveis, tools/agentes e side effects.
- Definir resposta segura para acesso negado.
- Garantir que erros de policy não abram acesso por fallback.
- Adicionar testes/instrumentação mínima para autorizado e negado.

## Agente / Skill / Rotina

@bolt-executor integra; @grid-tester testa; @vault-security revisa fail-closed; @hawk-debugger entra se a integração quebrar fluxo oficial.

## O que o usuário precisa decidir/fornecer

- Texto ou postura da resposta de negação: silenciosa ou mensagem curta.
- Se tentativa negada deve aparecer para o usuário ou só em log.

## Impacto esperado

Transforma o fork em uma versão segura por política, sem depender de disciplina manual nos canais.

## Dependências

F2-02 concluído e baseline F1-02 conhecido.

## Riscos

- Bloqueio acontecer tarde demais.
- Falha de parsing gerar allow acidental.
- Resposta de negação vazar detalhes da policy.

## Agente sugerido pra implementação

**Time:** @compass → @bolt → @grid → @vault → @hawk → @oath

| Fase | Agente | Papel |
|---|---|---|
| 1. Plano | @compass | Sequenciar integração |
| 2. Build | @bolt | Integrar policy no fluxo |
| 3. Testes | @grid | Validar allow/deny |
| 4. Segurança | @vault | Revisar fail-closed |
| 5. Debug | @hawk | Corrigir quebra de fluxo |
| 6. Verify | @oath | Evidenciar comportamento |

**Por quê esse time:** evolução de runtime de segurança; precisa preservar comportamento oficial e bloquear bypass.

## Status

- [ ] Pendente
- [ ] Em progresso
- [x] Concluído
