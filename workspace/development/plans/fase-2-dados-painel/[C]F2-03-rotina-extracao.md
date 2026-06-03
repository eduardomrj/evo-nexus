---
author: claude
agent: oracle
type: work-plan-item
date: 2026-04-26
phase: 2
item-id: F2-03
status: pending
---

# F2-03. Agendamento da rotina diária 17:30

**Fase:** Dados + Painel
**Eixo:** automação
**Tipo:** [ATIVAR]
**Prazo sugerido:** Sem 3 — após F2-01 e F2-02 validados

## O que é

Cadastrar a extração+carga como rotina diária no scheduler do EvoNexus. Com isso, o sistema alimenta o banco sem nenhuma ação humana — toda tarde o robô entra no SIGES, baixa os relatórios e atualiza o painel.

## O que fazer

- Adicionar entrada em `config/routines.yaml`:
  ```yaml
  - name: cpsmq-extract
    schedule: "30 17 * * *"
    script: ADWs/routines/custom/cpsmq/extractor/run.py
    timezone: America/Fortaleza
  ```
- `run.py` orquestra: extract → parse → load → log → notificar Eduardo via Telegram se falhar
- Testar manualmente via `make cpsmq-extract` antes de "ligar" o cron
- Validar log no dashboard de routines do EvoNexus
- Configurar alerta: 2 falhas consecutivas → Telegram para Eduardo

## Agente / Skill / Rotina

`@custom-sysops` (scheduler + cron) + skill `create-routine`

## O que o usuário precisa decidir/fornecer

- **Horário:** 17:30 confirmado? Ou 18:00 com margem para o expediente do SIGES fechar?
- **Fins de semana:** rodar sábado e domingo? (recomendado: sim, para não perder dados)

## Impacto esperado

Automação completa — Elistênio nunca precisa lembrar de extrair. O painel se atualiza sozinho.

## Dependências

F2-01, F2-02.

## Riscos

Falha silenciosa sem alerta → Elistênio percebe que dados estão velhos só na reunião. Mitigação: alerta de falha + indicador "Última atualização" visível no dashboard.

## Agente sugerido pra implementação

**Agente:** @custom-sysops + skill `create-routine`

**Por quê:** item [ATIVAR] — a rotina já existe (F2-01/02), só precisa ser agendada no scheduler do EvoNexus.

## Status

- [x] Pendente
- [ ] Em progresso
- [ ] Concluído
