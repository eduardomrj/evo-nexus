---
author: claude
agent: oracle
type: work-plan-item
date: 2026-04-26
phase: 3
item-id: F3-03
status: pending
---

# F3-03. Bot IA WhatsApp para consultas em linguagem natural

**Fase:** IA + WhatsApp
**Eixo:** IA
**Tipo:** [CONSTRUIR NOVO]
**Prazo sugerido:** Sem 4-5

## O que é

Bot que interpreta mensagens do Elistênio em português natural, consulta o banco via tool calling estruturado e responde com dados reais. É o diferencial do produto — em vez de abrir o painel, o gestor pergunta: "Como está Quixeramobim em abril?" e recebe a resposta em segundos.

## O que fazer

- Webhook recebe mensagem → `bot/handler.py`
- Pipeline com Claude API (tool calling):
  - **System prompt:** "Você é o assistente do CPSMQ. Responda somente com base nos dados do banco. Cite sempre a data da última extração. Nunca invente números."
  - **Tools disponíveis:**
    - `query_consolidado(mes, municipio?, especialidade?)` → SQL em `consolidado_mensal`
    - `query_meta_contrato(especialidade?)` → metas do contrato
    - `query_ppi(mes, municipio?)` → programação pactuada
    - `top_faltas(mes, n=3)` → especialidades com mais faltas
    - `comparar_municipios(mes)` → ranking de % utilização
  - Claude escolhe a tool correta, recebe o resultado SQL, sintetiza em pt-BR
- Histórico curto: últimas 5 mensagens da conversa (multi-turn básico)
- Resposta via `whatsapp_client.py`
- Salvar em `bot_conversas`: pergunta, resposta, custo de tokens, latência
- Limite diário de tokens (proteção contra loop/abuso): hard limit configurável
- Fallback: "Não consegui encontrar essa informação. Consulte o painel: [link]"

## Agente / Skill / Rotina

`@apex-architect` (design do RAG e tools) → `@bolt-executor` (implementação) → `@prism-scientist` (validação de acurácia das respostas) → `@grid-tester` (testes de edge cases)

## O que o usuário precisa decidir/fornecer

- **Modelo Claude:** Sonnet 4.6 (custo-benefício, recomendado) ou Opus 4.7 (precisão máxima)?
- **Orçamento mensal Claude API:** $30 / $50 / $100?
- **Quando o bot não souber:** responder "consulte o painel" (recomendado — zero risco de alucinação) ou tentar resposta livre?

## Impacto esperado

O gestor em reunião com prefeitos consegue responder qualquer questionamento sobre desempenho do consórcio em tempo real, pelo WhatsApp, sem laptop. É o principal argumento de venda para os outros 20 consórcios.

## Dependências

F2-02 (dados no banco), F3-01 (canal WhatsApp).

## Riscos

**ALTO.** Alucinação sobre número de meta ou atendimento → decisão errada do gestor → perda de confiança imediata e irreversível. Mitigação: tools com SQL fechado (zero free text sobre números), sempre citar fonte com timestamp da extração, confidence threshold — se Claude hesitar, vai para o fallback.

## Agente sugerido pra implementação

**Time:** @apex-architect → @bolt-executor → @prism-scientist → @grid-tester

| Fase | Agente | Papel |
|---|---|---|
| 1. Solutioning | @apex-architect | ADR do design do bot: tools, system prompt, fallback strategy |
| 2. Build | @bolt-executor | Handler, tools, pipeline Claude API |
| 3. Validação | @prism-scientist | Verificar acurácia das respostas vs dados reais do banco |
| 4. Testes | @grid-tester | Edge cases: pergunta ambígua, mês sem dados, especialidade errada |

**Por quê esse time:** é o componente de maior risco e maior diferencial — Apex define a arquitetura antes de qualquer código, Prism valida que os números estão corretos.

## Status

- [x] Pendente
- [ ] Em progresso
- [ ] Concluído
