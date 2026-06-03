---
author: claude
agent: oracle
type: work-plan-item
date: 2026-04-26
phase: 2
item-id: F2-01
status: pending
---

# F2-01. Extrator Playwright do SIGES

**Fase:** Dados + Painel
**Eixo:** extração
**Tipo:** [CONSTRUIR NOVO]
**Prazo sugerido:** Sem 2 — Dias 6-8

## O que é

Robô que entra no SIGES via Playwright (headless), baixa os 2 relatórios XLS e salva os originais com nome padronizado. O fluxo de extração já foi validado em outra plataforma e está documentado em `workspace/projects/cpsmq/ref-skill-extracao-siges.md` — este item transforma o fluxo validado em serviço confiável com resiliência, logging e alertas de falha.

## O que fazer

- Criar `extractor/siges_client.py`:
  - Login no SIGES: sistema GUS, unidade POLICLINICA - QUIXADA (código 7405529), módulo AMB
  - Componente validado: `d.c_651001.setValue('7405529')` + `d.c_651001.setShowValue(...)` + `d.c_650998.onclick()`
  - Abrir módulo AMB via `executeSyncJavaRule('GUS', 9170, 'Acesso ao sistema - Montar URL de abertura', ['AMB'])`
  - Gerar relatório `formID=464568178` (Agendamentos por Profissional - Sintético)
  - Gerar relatório `formID=464568165` (Atendimentos por Profissional e Procedimento por Município - Sintético)
  - Capturar sequência: `wfrcore?action=reportOpenExternal` → `openreport.jsp` → `download?...`
- Salvar em `${CPSMQ_DATA_DIR}/reports/raw/{YYYY-MM-DD}/agendamento.xls` e `atendimento.xls`
- Validação dos XLS: verificar header OLE (`d0 cf 11 e0 a1 b1 1a e1`), tamanho > 0
- Retry 3x com backoff exponencial em caso de falha
- Screenshot em caso de erro (para debug)
- Registrar linha em `extracoes` no banco: status, caminhos, timestamp, mensagem de erro
- Logging JSONL em `${CPSMQ_DATA_DIR}/logs/extract-{date}.jsonl`
- Criar `extractor/run.py` — orquestrador que chama client + parser (F2-02) + notify se falhar

## Agente / Skill / Rotina

`@bolt-executor` (implementação) + `@hawk-debugger` (diagnóstico quando o fluxo quebrar) + `@custom-sysops` (instalar Playwright + chromium no LXC)

## O que o usuário precisa decidir/fornecer

- **Credencial SIGES:** usar login nominal do Elistênio ou solicitar conta de serviço dedicada para automação?
- **Fallback de falha:** se SIGES estiver fora às 17:30, retry em 30min automaticamente ou notificar Eduardo via Telegram para extração manual?

## Impacto esperado

Com o extrator funcionando, o sistema alimenta o banco sem nenhuma ação humana. É o coração da automação — sem ele, o produto não tem diferencial.

## Dependências

F1-02 (tabela `extracoes` no banco).

## Riscos

**ALTO.** SIGES pode ter: MFA, captcha, bloqueio por IP, mudança de layout. Mitigação: alertas de falha imediatos (Telegram para Eduardo) + screenshot para debug + fallback de upload manual no painel de extrações (F2-05).

## Agente sugerido pra implementação

**Time:** @bolt-executor → @hawk-debugger → @grid-tester

| Fase | Agente | Papel |
|---|---|---|
| 1. Build | @bolt-executor | Implementação do siges_client.py e run.py |
| 2. Debug | @hawk-debugger | Diagnóstico quando o fluxo quebrar em ambiente real |
| 3. Verify | @grid-tester | Testes de resiliência (retry, falha de rede, XLS inválido) |

**Por quê esse time:** o extrator é o componente de maior risco do projeto — precisa de diagnóstico especializado quando (não "se") o SIGES apresentar comportamento inesperado.

## Status

- [x] Pendente
- [ ] Em progresso
- [ ] Concluído
