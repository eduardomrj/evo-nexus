---
author: claude
agent: oracle
type: work-plan-item
date: 2026-05-25
phase: 3
item-id: F3-02
status: done
---

# F3-02. Documentação operacional mínima do v1

**Fase:** Fase 3 — Smoke, documentação e backlog
**Eixo:** Documentação / Handoff / Uso seguro
**Tipo:** [ATIVAR]
**Prazo sugerido:** 0,5 dia

## O que é

Documentar como instalar, configurar e validar o `evonexus-discord-plus` v1, com foco em política de acesso e diferenças em relação ao plugin oficial.

## O que fazer

- Documentar origem do fork e versão base.
- Documentar escopo v1 e fora de escopo.
- Documentar configuração da policy com exemplos.
- Documentar semântica de precedência e deny-by-default.
- Documentar campos de log de autorização.
- Documentar comandos de smoke/testes.
- Documentar limitações conhecidas.

## Agente / Skill / Rotina

@quill-writer escreve documentação técnica curta; @vault-security revisa se exemplos expõem IDs/segredos; @oath-verifier confirma que docs batem com o comportamento observado.

## O que o usuário precisa decidir/fornecer

- Se a documentação será interna apenas ou preparada para repo público.
- Se IDs reais devem ser mascarados nos exemplos.

## Impacto esperado

Reduz dependência de memória oral e permite retomada segura por outro agente/sessão.

## Dependências

F1-01 a F3-01 concluídos ou com resultados conhecidos.

## Riscos

- Documentação prometer backlog como se fosse v1.
- Exemplo de policy induzir configuração permissiva.
- Confundir `evonexus-discord-plus` com bridge custom atual.

## Agente sugerido pra implementação

**Time:** @quill → @vault → @oath

| Fase | Agente | Papel |
|---|---|---|
| 1. Docs | @quill | Escrever documentação técnica |
| 2. Segurança | @vault | Revisar exemplos e segredos |
| 3. Verify | @oath | Confirmar aderência ao comportamento |

**Por quê esse time:** documentação de segurança precisa ser curta, correta e não vazar dados.

## Status

- [ ] Pendente
- [ ] Em progresso
- [x] Concluído
