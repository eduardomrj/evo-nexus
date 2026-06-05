---
author: claude
agent: oracle
type: work-plan-item
date: 2026-05-25
phase: 1
item-id: F1-01
status: done
---

# F1-01. Criar origem controlada do `evonexus-discord-plus`

**Fase:** Fase 1 — Fork seguro e baseline oficial
**Eixo:** Fundação / Repositório / Segurança de escopo
**Tipo:** [ATIVAR]
**Prazo sugerido:** 0,5 dia

## O que é

Criar a base do projeto `evonexus-discord-plus` a partir do Discord Channel oficial/original, garantindo rastreabilidade e evitando contaminação com o bridge custom atual.

## O que fazer

- Confirmar a fonte local: `/home/evonexus/.openclaude/plugins/marketplaces/claude-plugins-official/external_plugins/discord/`.
- Registrar qual commit/versão/origem foi usada como baseline.
- Criar o fork/repo/pasta de trabalho do `evonexus-discord-plus`.
- Copiar ou clonar somente o conteúdo do plugin oficial Discord.
- Adicionar nota explícita: “não importar código do bridge custom atual no v1”.
- Separar commit inicial ou snapshot “baseline oficial sem alterações”.

## Agente / Skill / Rotina

@oracle coordena; @scout-explorer mapeia a estrutura; @flow-git pode criar repo/commit; @vault-security verifica risco de segredos acidentais no baseline.

## O que o usuário precisa decidir/fornecer

- Destino físico do projeto: repo separado, pasta local temporária ou outro destino.
- Confirmação do nome final: `evonexus-discord-plus`.

## Impacto esperado

Cria uma base limpa, auditável e reversível para evolução do plugin oficial sem misturar com o bridge custom.

## Dependências

Acesso ao plugin oficial local ou remoto e definição do destino do fork.

## Riscos

- Misturar código do bridge custom atual por inércia.
- Perder rastreabilidade da versão oficial usada.
- Copiar arquivos de configuração locais com segredos.

## Agente sugerido pra implementação

**Time:** @oracle → @scout → @flow → @vault

| Fase | Agente | Papel |
|---|---|---|
| 1. Coordenação | @oracle | Confirmar decisões e escopo |
| 2. Mapeamento | @scout | Validar fonte e estrutura |
| 3. Git | @flow | Criar repo/snapshot quando aprovado |
| 4. Segurança | @vault | Checar segredos no baseline |

**Por quê esse time:** item de ativação com impacto de segurança e rastreabilidade; precisa coordenação antes de qualquer escrita.

## Status

- [ ] Pendente
- [ ] Em progresso
- [x] Concluído
