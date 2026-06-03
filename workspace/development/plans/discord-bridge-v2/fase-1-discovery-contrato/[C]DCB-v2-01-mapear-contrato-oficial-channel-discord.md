---
author: claude
agent: oracle
type: work-plan-item
date: 2026-05-19
phase: 1
item-id: DCB-v2-01
status: pending
---

# DCB-v2-01. Mapear contrato oficial Channel/Discord

**Fase:** Fase 1 — Discovery/Contrato oficial e inventário must-have
**Eixo:** arquitetura-contrato-integracao
**Tipo:** [DECIDIR]
**Prazo sugerido:** início da fase 1

## O que é

Extrair o contrato mínimo do Channel oficial que a v2 precisa respeitar: entrada, reply tool, lifecycle, streaming, erro, sessão e cancelamento. A decisão evita copiar o oficial cegamente e evita reconstruir abstrações incompatíveis.

## O que fazer

- Ler `docs/guides/channels.md`.
- Ler `docs/guides/channels-reference.md`.
- Confirmar o comando oficial no `Makefile` linhas 169-174.
- Listar eventos inbound e ferramentas outbound, principalmente `reply`.
- Identificar comportamento oficial para erro, streaming, sessão e cancelamento.
- Produzir tabela “oficial vs requisito local”.

## Agente / Skill / Rotina

`@scout-explorer` para inventário rápido, `@scroll-docs` se precisar de documentação externa, `@apex-architect` para validar o contrato.

## O que o usuário precisa decidir/fornecer

- Confirmar se compatibilidade com o contrato oficial é mandatória mesmo que reduza features locais temporariamente.
- Confirmar quais features são must-have no dia 1.

## Impacto esperado

Reduz divergência entre a bridge custom e o modelo oficial. Evita que a v2 nasça com o mesmo problema estrutural da v1.

## Dependências

Docs oficiais locais e Makefile do EvoNexus.

## Riscos

- Interpretar o oficial de forma superficial.
- Confundir “compatível com Channel” com “copiar implementação oficial”.

## Agente sugerido pra implementação

**Time:** @oracle → @scout-explorer → @apex-architect → @raven-critic

| Fase | Agente | Papel |
|---|---|---|
| 1. Framing | @oracle | Conduzir decisões com Eduardo |
| 2. Pesquisa | @scout-explorer | Levantar evidências file:line |
| 3. Arquitetura | @apex-architect | Interpretar contrato e trade-offs |
| 4. Crítica | @raven-critic | Validar se há lacunas |

**Por quê esse time:** item [DECIDIR] com impacto arquitetural; precisa evidência e decisão humana.

## Status

- [x] Pendente
- [ ] Em progresso
- [ ] Concluído
