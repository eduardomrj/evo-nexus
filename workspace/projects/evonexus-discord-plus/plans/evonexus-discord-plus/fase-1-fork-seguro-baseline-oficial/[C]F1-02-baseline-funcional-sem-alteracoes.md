---
author: claude
agent: oracle
type: work-plan-item
date: 2026-05-25
phase: 1
item-id: F1-02
status: done
---

# F1-02. Baseline funcional sem alterações

**Fase:** Fase 1 — Fork seguro e baseline oficial
**Eixo:** Qualidade / Compatibilidade / Regressão zero
**Tipo:** [ATIVAR]
**Prazo sugerido:** 0,5 a 1 dia

## O que é

Validar que o plugin forkado roda como o oficial antes de implementar segurança. O objetivo é separar problemas herdados do oficial de problemas introduzidos pelo v1.

## O que fazer

- Ler a documentação mínima do plugin oficial.
- Identificar comandos, entrypoints, variáveis de ambiente e fluxo de execução.
- Rodar instalação, build e testes existentes, se houver.
- Executar um smoke mínimo equivalente ao oficial.
- Registrar evidência do baseline: comando, resultado, limitações e falhas herdadas.
- Se o baseline não rodar, abrir item de decisão antes de alterar arquitetura.

## Agente / Skill / Rotina

@scout-explorer localiza scripts e entrypoints; @bolt-executor faz ajustes mínimos apenas se aprovados; @oath-verifier registra evidência; @hawk-debugger entra se o baseline oficial falhar.

## O que o usuário precisa decidir/fornecer

Se o plugin oficial falhar no baseline: corrigir compatibilidade mínima ou trocar a versão-base.

## Impacto esperado

Reduz risco de atribuir ao v1 problemas que já existiam no plugin original.

## Dependências

F1-01 concluído.

## Riscos

- Baseline depender de credenciais Discord reais.
- Teste oficial inexistente ou insuficiente.
- Alterações “só para rodar” virarem refatoração prematura.

## Agente sugerido pra implementação

**Time:** @scout → @bolt → @oath; @hawk se falhar

| Fase | Agente | Papel |
|---|---|---|
| 1. Mapeamento | @scout | Identificar comandos e entrypoints |
| 2. Ajuste mínimo | @bolt | Corrigir apenas se aprovado |
| 3. Verificação | @oath | Registrar evidência do smoke |
| 4. Debug | @hawk | Diagnosticar falhas do baseline |

**Por quê esse time:** baseline precisa ser comprovado antes de qualquer evolução; Oath evita “parece funcionar”.

## Status

- [ ] Pendente
- [ ] Em progresso
- [x] Concluído
