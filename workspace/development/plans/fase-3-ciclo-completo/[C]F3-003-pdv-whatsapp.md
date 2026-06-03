---
author: claude
agent: oracle
type: work-plan-item
date: 2026-04-17
phase: 3
item-id: F3-003
status: pending
---

# F3-003. PDV Integrado ao WhatsApp — Discovery + Protótipo

**Fase:** 3 — Ciclo Completo
**Eixo:** Produto / Engineering
**Tipo:** [CONSTRUIR NOVO]
**Prazo sugerido:** Sem 17-24

## O que é

O produto mais inovador da visão da Automação Software: PDV operado via WhatsApp. Um agente (humano ou IA) faz atendimento pelo WhatsApp, registra o pedido em tempo real, envia link de pagamento, e coordena a entrega — tudo em um fluxo contínuo. Eduardo acredita que não existe no mercado da forma que imaginou. Este item começa com discovery profundo e protótipo de 1 fluxo.

## O que fazer

- Deep interview com skill `dev-deep-interview`: definir o caso de uso exato (quem opera: humano ou agente IA? lojista usa como terminal de PDV? ou cliente faz pedido diretamente?)
- Discovery de viabilidade com @echo-analyst: análise técnica (Evolution Go + PDV + checkout + pipeline de entrega)
- Wireframes da experiência conversacional com @canvas-designer: como fica a conversa no WhatsApp para o operador? e para o cliente?
- Arquitetura com @apex-architect: como integrar WhatsApp → PDV → fiscal → pagamento → entrega
- MVP de 1 fluxo end-to-end com @bolt-executor: pedido via WhatsApp → checkout → confirmação

## Agente / Skill / Rotina

`dev-deep-interview` + `@echo-analyst` + `@canvas-designer` + `@apex-architect` + `@bolt-executor` + `int-evolution-go`

## O que o usuário precisa decidir/fornecer

- Caso de uso principal: **A)** vendedor usa WhatsApp como terminal de PDV ou **B)** cliente faz pedido pelo WhatsApp direto?
- Escopo do MVP: só pedido? pedido + pagamento? pedido + pagamento + NFCe?
- Persona prioritária: lojista de varejo? vendedor ambulante? restaurante? delivery?
- 1 cliente piloto identificado para validar o conceito antes de investir pesado

## Impacto esperado

Produto diferenciado no mercado. Potencial viral se bem executado. Âncora da proposta de valor da Plataforma GO para varejo moderno.

## Dependências

- F2-004 (stack da Plataforma GO definida)
- F3-002 (PDV web como base técnica)
- Evolution Go configurado e estável

## Riscos

- **ALTO** — conceito inovador sem validação de mercado. Mitigação obrigatória: 1 cliente piloto confirmado antes de investir mais de 2 semanas de desenvolvimento
- Limitações da API do WhatsApp Business (rate limits, formatos de mensagem, botões interativos) — mitigação: protótipo técnico antes de qualquer design final
- Complexidade de integração fiscal (NFCe via WhatsApp) — mitigação: deixar fiscal para v1.1, MVP foca em pedido + pagamento

## Agente sugerido pra implementação

| Fase | Agente | Papel |
|---|---|---|
| 1. Deep Interview | dev-deep-interview (skill) | Definir caso de uso com Eduardo |
| 2. Discovery | @echo-analyst | Viabilidade técnica + gaps |
| 3. UI Conversacional | @canvas-designer | Wireframes da experiência WhatsApp |
| 4. Arquitetura | @apex-architect | ADR de integração |
| 5. MVP | @bolt-executor | 1 fluxo end-to-end |
| 6. Piloto | @probe-qa + Eduardo | Testar com cliente real |

**Por quê:** produto inovador sem precedente claro — discovery profundo antes de qualquer código.

## Status

- [x] Pendente
- [ ] Em progresso
- [ ] Concluído
