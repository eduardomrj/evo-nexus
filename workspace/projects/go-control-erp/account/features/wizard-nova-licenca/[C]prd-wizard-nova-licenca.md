---
author: claude
agent: compass-planner
type: prd
date: 2026-05-12
feature: wizard-nova-licenca
project: go-control-erp
status: draft
---

# PRD — Wizard de Criação de Licença (Platform Admin)

## Problema

Hoje, criar uma licença completa no Platform Admin do GO Control ERP exige percorrer várias telas manualmente: criar a Conta, depois cada Empresa, depois cada Licença para cada empresa e, por fim, configurar overrides de módulo/recurso uma a uma. O fluxo é repetitivo, propenso a erro humano e cria estados inconsistentes (ex.: Conta criada mas sem licença, ou empresa sem plano). Não há um caminho guiado para o caso mais comum — onboarding de um novo cliente com 1+ empresas no mesmo plano.

## Goals

- Reduzir o onboarding de um novo cliente (Conta + N empresas + N licenças + overrides) a um único fluxo guiado de 4 passos.
- Garantir consistência: ao final do wizard, ou tudo foi criado, ou o usuário sabe exatamente o que faltou.
- Permitir que o operador da plataforma customize quais módulos/recursos do plano serão ativados para o lote de licenças, sem precisar entrar em cada licença depois.

## Non-goals

- **Não** seleciona Conta/Empresa/Plano existentes — o wizard é exclusivo para registros NOVOS. Edição de licenças existentes continua nas páginas atuais.
- **Não** permite override por empresa neste momento — a configuração de módulos/recursos do passo 3 é aplicada igualmente a todas as licenças criadas. (Customização por empresa fica em backlog).
- **Não** substitui as páginas atuais de Contas/Empresas/Licenças — convive com elas.
- **Não** implementa transação atômica no backend — a sequência de chamadas é orquestrada no frontend, com tratamento de erro parcial.
- **Não** envia email/notificação ao owner da conta criada (fica para iteração futura).

## User Stories

- **US-1** — Como operador do Platform Admin, quero criar uma Conta nova com sua empresa matriz e o owner em um único passo, para não precisar navegar entre 3 telas.
- **US-2** — Como operador, quero adicionar empresas extras (filiais ou independentes) à Conta no mesmo fluxo, para cobrir o caso de cliente com múltiplas empresas (matriz + filiais).
- **US-3** — Como operador, quero escolher um plano e marcar exatamente quais módulos/recursos devem ficar ativos, para entregar a licença já configurada conforme o contrato comercial.
- **US-4** — Como operador, quero revisar tudo antes de confirmar e ver o progresso da criação em tempo real, para ter confiança no que está sendo persistido.
- **US-5** — Como operador, se algo falhar no meio do processo, quero ver claramente o que foi criado e o que falhou, para conseguir terminar o trabalho manualmente sem duplicar dados.

## Acceptance Criteria (Given / When / Then)

### AC-1 — Criação completa do caminho feliz (1 empresa)

- **Given** que estou em `/licencas/nova` e nenhum dado da plataforma foi alterado por outro usuário,
- **When** preencho o passo 1 (Conta + owner) com dados válidos, não adiciono empresas extras no passo 2, escolho um plano ativo no passo 3 sem desmarcar nada, e clico em "Criar" no passo 4,
- **Then** o sistema cria 1 Conta, 1 Empresa matriz (criada pelo endpoint de Conta), 1 Licença para a matriz, 0 overrides, e me redireciona para a página de detalhe da conta criada, exibindo um Toast de sucesso.

### AC-2 — Criação completa com múltiplas empresas

- **Given** que estou no passo 2 do wizard e a Conta já foi configurada no passo 1,
- **When** adiciono 2 empresas extras (1 filial e 1 independente) com CNPJs válidos e distintos do CNPJ matriz, e prossigo até finalizar,
- **Then** o sistema cria 1 Conta, 3 Empresas no total (matriz + 2 extras), 3 Licenças (uma por empresa) com o mesmo plano e os mesmos overrides aplicados.

### AC-3 — Customização de módulos/recursos no passo 3

- **Given** que estou no passo 3 e selecionei um plano que tem 5 módulos (cada um com 3 recursos),
- **When** desmarco 1 módulo inteiro e desmarco 2 recursos de outro módulo,
- **Then** ao finalizar, cada licença criada recebe os respectivos `LicencaOverride` (1 override de módulo desativado + 2 overrides de recurso desativado), totalizando `3 × 3 = 9` overrides para o cenário de 3 licenças.

### AC-4 — Validação de slug único

- **Given** que estou no passo 1 e digito um slug que já existe em outra Conta,
- **When** tento avançar para o passo 2,
- **Then** o avanço é bloqueado e vejo uma mensagem de erro no campo `slug` indicando colisão. Sugestão: oferecer um slug alternativo automaticamente.

### AC-5 — Validação de CNPJ

- **Given** que digito um CNPJ inválido no passo 1 ou no passo 2,
- **When** tento avançar de passo,
- **Then** o avanço é bloqueado e o campo exibe erro "CNPJ inválido". CNPJ é validado por algoritmo (DV) e por unicidade dentro do mesmo wizard (não pode ter dois iguais entre matriz e empresas extras).

### AC-6 — Erro parcial no passo 4

- **Given** que iniciei a criação no passo 4 e a Conta foi criada com sucesso, mas a criação da segunda empresa retornou erro (ex.: 500),
- **When** o erro é capturado,
- **Then** o wizard mostra um painel de status com check verde para "Conta criada" + "Empresa matriz criada" + "Empresa filial X criada", erro vermelho para "Empresa filial Y", e bloqueia o restante. Oferece dois botões: "Tentar novamente a partir do erro" (retry idempotente do ponto que falhou) e "Sair e finalizar manualmente" (redireciona para a Conta criada).

### AC-7 — Progresso visível durante a criação

- **Given** que cliquei em "Criar" no passo 4,
- **When** o wizard inicia a sequência de chamadas,
- **Then** vejo um indicador de progresso textual que atualiza em tempo real conforme cada chamada completa: "Criando conta..." → "Criando empresa 2 de 3..." → "Criando licença 1 de 3..." → "Aplicando overrides (1/9)..." → "Concluído". Botões de navegação ficam desabilitados durante a execução.

### AC-8 — Auto-sugestão de slug

- **Given** que estou digitando o `nome` no passo 1,
- **When** o campo `slug` ainda não foi tocado manualmente,
- **Then** o slug é sugerido automaticamente a partir do nome (kebab-case, sem acentos, sem caracteres especiais). Após o usuário editar o slug manualmente, a auto-sugestão para de sobrescrever.

### AC-9 — Navegação entre passos preserva estado

- **Given** que preenchi o passo 1 e adicionei 2 empresas no passo 2,
- **When** volto para o passo 1, edito o nome da Conta, e avanço novamente para o passo 2,
- **Then** as 2 empresas extras que adicionei continuam lá. O estado do wizard é local ao componente e não é perdido até que eu saia da rota ou clique em "Cancelar".

### AC-10 — Cancelamento

- **Given** que tenho dados preenchidos em qualquer passo do wizard,
- **When** clico em "Cancelar" ou tento sair da rota,
- **Then** vejo um confirm dialog "Descartar progresso?" antes de perder o estado. Se confirmo, sou redirecionado para `/licencas` (ou rota anterior).

## Constraints

- **Stack frontend:** React + TypeScript + PrimeReact (Steps, Sidebar, InputText, Dropdown, Checkbox, Button, Toast) — não introduzir nova biblioteca de UI.
- **Service layer:** reusar `platform.ts` existente; criar tipos novos apenas se forem específicos do wizard (ex.: `WizardState`).
- **Idempotência:** não há transação atômica no backend; o frontend orquestra. Em caso de retry após erro parcial, **não** recriar entidades já criadas (guardar IDs retornados em memória).
- **Ordem das chamadas** (fixa, sequencial):
  1. `POST /contas/` → recebe `conta.id` + `empresa.matriz.id`
  2. Para cada empresa extra: `POST /contas/{id}/empresas/`
  3. `GET /contas/{id}/empresas/` para obter lista completa (matriz + extras)
  4. Para cada empresa: `POST /contas/{id}/empresas/{empresa_id}/licencas/`
  5. Para cada licença + cada override do passo 3: `POST .../licencas/{id}/overrides/`
- **Padrão de wizard:** seguir o estilo do `LicencaWizardSidebar` existente (referência), mas em página dedicada (não sidebar).
- **Acessibilidade:** componentes do PrimeReact já cobrem keyboard navigation; manter labels e `aria-*` corretos.
- **i18n:** pt-BR (consistente com o restante da plataforma).

## Open Questions

- [x] **OQ-1** — ~~Receita/Bling~~ — Validação local: CNPJ numérico → formato (14 dígitos) + DV; CNPJ alfanumérico (novo formato) → apenas formato (14 chars). Em ambos os casos, checar unicidade contra o backend no avanço do passo 1/2.
- [ ] **OQ-2** — Qual `data_inicio` padrão usar para as licenças? Hoje? Próximo dia útil? Permitir o usuário escolher uma data global no passo 3?  Risco: baixo (default = hoje resolve 90% dos casos).
- [x] **OQ-3** — ~~`ativa`~~ — Status inicial = `pendente`.
- [ ] **OQ-4** — Em caso de erro parcial, o botão "Tentar novamente" precisa de uma chamada idempotente real (ex.: `PUT` com `idempotency_key`) ou basta reusar o estado local e pular as etapas já feitas?  Risco: baixo — solução local é suficiente para v1.
- [ ] **OQ-5** — O wizard precisa exigir permissão específica (`platform:licencas:create`) ou usa a mesma permissão de criar Conta?

## Métricas de sucesso

- Tempo médio de onboarding de um cliente novo cai de ~5min (fluxo manual) para <90s (medido em ambiente interno).
- Zero contas órfãs (sem licença) criadas via Platform Admin em uma semana após release.
- Erro parcial com painel de retry consegue completar a criação em ≥80% dos casos sem suporte manual ao DB.

## Handoff

- **Próximo agente:** `@compass-planner` produz o plano de implementação (próximo arquivo).
- **Após plano aprovado:** `@apex-architect` valida a sequência de chamadas e o tratamento de erro parcial (Phase 3 — Solutioning).
- **Após arquitetura:** `@bolt-executor` implementa (Phase 4 — Build).
