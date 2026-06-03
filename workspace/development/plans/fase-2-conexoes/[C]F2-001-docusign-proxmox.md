---
author: claude
agent: oracle
type: work-plan-item
date: 2026-04-17
phase: 2
item-id: F2-001
status: pending
---

# F2-001. DocuSign Self-Hosted — Implantação no Proxmox

**Fase:** 2 — Conexões
**Eixo:** Comercial
**Tipo:** [DECIDIR]
**Prazo sugerido:** Sem 5-6

## O que é

Decidir e implantar a solução de assinatura digital de contratos no homelab Proxmox de Eduardo. Avaliar DocuSign oficial (MCP disponível) vs alternativas open-source self-hosted (ex: Docuseal). Esta decisão desbloqueia o pipeline comercial completo (F2-002).

## O que fazer

- Research com @scroll-docs: DocuSign API (custo, limites, MCP disponível no EvoNexus) vs Docuseal (open-source, self-hosted, Docker) vs outras opções
- Avaliar compatibilidade com o MCP de DocuSign já disponível no workspace
- Produzir ADR com recomendação: custo, suporte, integração com EvoNexus, curva de implantação
- Implantar a opção escolhida no Proxmox (container Docker ou VM)
- Testar fluxo: criar contrato → enviar para assinatura → receber confirmação

## Agente / Skill / Rotina

`@scroll-docs` (research de opções) + `@apex-architect` (ADR de decisão) + `@bolt-executor` (implantação Docker no Proxmox)

## O que o usuário precisa decidir/fornecer

- DocuSign oficial (tem conta/plano?) vs alternativa open-source
- Servidor Proxmox disponível (IP, credenciais, recursos disponíveis)
- Requisitos mínimos: quantidade de contratos/mês, precisa de auditoria legal?

## Impacto esperado

Assinatura digital de contratos disponível no workspace. Desbloqueio do pipeline comercial (F2-002): proposta → contrato → assinatura → ativação.

## Dependências

- Homelab Proxmox disponível e acessível
- Decisão DocuSign vs alternativa (este item resolve isso)

## Riscos

- Alternativas open-source podem ter validade jurídica limitada no Brasil — mitigação: verificar conformidade com MP 2.200-2/2001 (ICP-Brasil) antes de decidir
- DocuSign MCP pode ter custo por envelope — mitigação: avaliar custo vs volume de contratos

## Agente sugerido pra implementação

| Fase | Agente | Papel |
|---|---|---|
| 1. Research | @scroll-docs | Documentação das opções |
| 2. Decisão | @apex-architect | ADR com recomendação |
| 3. Implantação | @bolt-executor | Deploy no Proxmox |

**Por quê:** item [DECIDIR] com implantação técnica — research + ADR antes de qualquer instalação.

## Status

- [x] Pendente
- [ ] Em progresso
- [ ] Concluído
