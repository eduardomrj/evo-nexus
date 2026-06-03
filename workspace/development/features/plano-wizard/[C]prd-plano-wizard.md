---
author: claude
agent: compass-planner
type: prd
date: 2026-05-22
feature: plano-wizard
status: draft
---

# PRD — Wizard de Criação de Plano (Platform Admin)

## 1. Problema

A criação de planos no Platform Admin do GO Control ERP é feita hoje através de um `Sidebar` simples (`NovoPlanoSidebar` em `PlatformPlanosPage.tsx:80-296`) que coleta apenas dados básicos do plano (tag, nome, aplicativo, descrição, status, billing). Em seguida, o operador precisa abrir o plano criado e configurar módulos e recursos um a um, em fluxos separados — sem visão consolidada do que estará "ligado" para o cliente final.

Falta um wizard multi-step que conduza o operador através de:
1. Dados do plano
2. Seleção de módulos
3. Configuração de **recursos** (parametrização real do que o cliente recebe — valores default, disponibilidade, edição na ativação)
4. Revisão antes de confirmar

Adicionalmente, o modelo `Recurso` (`platform.models.Recurso`) hoje só tem `parametros: JSONField`, sem tipagem nem indicação se o valor é editável no momento da ativação de uma licença. Sem esses metadados, o wizard não consegue renderizar inputs corretos nem travar campos read-only.

## 2. Objetivos (testáveis)

1. Operador consegue criar um plano completo (dados + módulos + recursos configurados) em uma única jornada `/planos/novo`, sem precisar editar o plano depois para terminar a configuração.
2. Cadastro de `Recurso` (em `ModuloSidebarForm`) passa a definir **tipo do valor** (`boolean | inteiro | string | data | mes_ano`) e **se é editável no momento de criar uma licença** (`editavel_na_criacao: bool`).
3. Wizard renderiza, no passo de recursos, o input adequado por `tipo_valor` e trava o campo (read-only com badge "Não editável na ativação") quando `editavel_na_criacao=false`.
4. Plano criado pelo wizard fica funcionalmente equivalente a um plano criado pelo fluxo antigo + edições subsequentes (mesmos `PlanoModulo` e `PlanoRecurso` no banco).
5. Conformidade total com ADR-001: nenhuma regra de negócio em `views.py`, nenhum `axios` direto em componente, métodos ≤ 30 linhas, arquivos ≤ 300 linhas (views) / 250 (páginas).

## 3. Não-objetivos

- **Não** redesenhar o fluxo de criação de **licença** (já existe `PlatformNovaLicencaPage`).
- **Não** substituir a aba de edição detalhada do plano (continua valendo para ajustes pós-criação).
- **Não** implementar herança/clonagem de planos no wizard (já existe rota `clonar/`).
- **Não** suportar recursos do tipo `submenu` (`Modulo.tipo='submenu'` continua proibido, conforme `Recurso.clean()`).
- **Não** criar fluxo de migração para preencher `tipo_valor` em recursos legados — default `'boolean'` aplica e operador ajusta sob demanda.
- **Não** alterar contrato dos endpoints já consumidos por `PlatformPlanosPage` (Sidebar antigo continua funcional como fallback até ser removido em fase posterior).

## 4. User stories

### US-1 — Operador cria plano completo em uma jornada
Como operador da Automação Software, quero criar um plano novo em um fluxo guiado que cobre dados, módulos e parametrização de recursos, para evitar idas e voltas entre telas e garantir que o plano sai "pronto para vender".

### US-2 — Operador define se um recurso é configurável na ativação
Como operador, ao cadastrar um recurso (ex: "dia de vencimento da fatura"), quero marcá-lo como `editavel_na_criacao` para que, durante a ativação de uma licença real, o vendedor consiga sobrescrever o valor padrão; quando o recurso é fixo (ex: "permite emitir NF-e"), quero deixar travado.

### US-3 — Operador vê tipos de valor corretos no wizard
Como operador, ao chegar no passo de recursos, quero ver um `Checkbox` para boolean, `InputNumber` para inteiro, `InputText` para string, `Calendar` para data e um seletor de mês/ano para mes_ano — não um JSON cru — para parametrizar sem errar de sintaxe.

### US-4 — Operador revisa antes de confirmar
Como operador, antes de salvar, quero ver um resumo (dados do plano + módulos incluídos + recursos configurados com seus valores) para detectar erros antes que o plano vá ao ar.

## 5. Critérios de aceitação (Given/When/Then)

### AC-1 — Cadastro de Recurso com novos campos

**Given** estou em `Platform Admin → Módulos → {módulo} → aba Recursos`
**When** clico em "Novo recurso" e preencho code, nome, descrição, `tipo_valor=inteiro`, `editavel_na_criacao=false`
**Then** o recurso é salvo com os dois novos campos persistidos no banco e aparece na listagem com badges indicando tipo e edição.

### AC-2 — Migration aplica defaults sem quebrar recursos existentes

**Given** existem recursos legados em `platform_recurso` sem `tipo_valor`/`editavel_na_criacao`
**When** rodo `python manage.py migrate platform`
**Then** todos os recursos legados recebem `tipo_valor='boolean'` e `editavel_na_criacao=true` por default, e os 80+ testes existentes continuam verdes.

### AC-3 — Rota /planos/novo abre wizard

**Given** estou autenticado no Platform Admin como staff
**When** acesso `http://localhost:5175/planos/novo` (ou clico em "Novo plano" na lista `/planos`)
**Then** vejo um `Steps` PrimeReact com 4 passos: "Dados", "Módulos", "Recursos", "Revisão" — passo 1 ativo.

### AC-4 — Passo 1 valida dados básicos

**Given** estou no passo "Dados" do wizard
**When** clico "Próximo" sem preencher tag/nome/aplicativo
**Then** vejo mensagens de erro inline e o passo não avança; quando preencho campos obrigatórios e clico "Próximo", avanço para o passo "Módulos".

### AC-5 — Passo 2 lista módulos do aplicativo escolhido

**Given** escolhi `aplicativo=Emporion Desktop` no passo 1
**When** chego no passo "Módulos"
**Then** vejo apenas módulos com `tipo IN ('modulo', 'tela')` vinculados ao aplicativo (consulta `Modulo.aplicativos.filter(id=...)`), cada um com um `Checkbox` de inclusão. Submenus não aparecem.

### AC-6 — Passo 3 agrupa recursos por módulo incluído

**Given** marquei 3 módulos no passo 2
**When** chego no passo "Recursos"
**Then** vejo os 3 módulos como `Accordion`/`Fieldset`, cada um listando seus recursos (`Recurso.objects.filter(modulo=m)`). Para cada recurso:
- Toggle "disponível" controla `PlanoRecurso.disponivel`
- Campo de valor renderiza conforme `tipo_valor` (Checkbox/InputNumber/InputText/Calendar/MonthYear)
- Se `editavel_na_criacao=false`, o campo de valor mostra badge "Fixo na ativação" e fica `disabled`/`readOnly`

### AC-7 — Passo 4 resume e cria

**Given** estou no passo "Revisão"
**When** vejo o resumo (dados + lista de módulos + tabela de recursos com seus valores)
**Then** clico "Criar plano" e o wizard:
1. Chama `POST /api/v1/platform/planos/` com tag/nome/descricao/aplicativo + lista `recursos[]` (ou faz N+1 calls atômicos no client — ver Open Questions)
2. Em sucesso, navega para `/planos/{tag}` mostrando o plano criado com todos os módulos+recursos populados conforme o wizard
3. Em erro, mostra `toast` com `extractError` e mantém o usuário no passo de revisão (estado preservado em `sessionStorage`)

### AC-8 — Estado do wizard sobrevive a F5

**Given** estou no passo 3 com seleções feitas
**When** dou F5 acidentalmente
**Then** ao recarregar, o wizard restaura passo + dados via `sessionStorage` (mesmo padrão de `PlatformNovaLicencaPage`).

### AC-9 — Conformidade ADR-001

**Given** o PR está aberto
**When** code review roda o checklist do ADR-001 §7.4
**Then**:
- Nenhum método em `views.py` > 30 linhas; nenhuma view chama `Model.objects.create/get_or_create` direto
- Lógica de criação composta (plano + módulos + recursos) vive em `PlanoService.criar_completo(...)` com `@transaction.atomic`
- Frontend: chamadas HTTP em `services/platform.ts` (padrão atual do app), nada de `axios` direto em `.tsx`
- Página `PlatformNovoPlanoPage.tsx` ≤ 250 linhas (composição); steps extraídos em `components/wizard-plano/Step*.tsx`

## 6. Constraints

- **Plataforma**: Django 5 + DRF (backend), React 18 + Vite + TypeScript + PrimeReact + React Query (frontend Platform Admin :5175).
- **ADR-001 é lei** (`/home/evonexus/evo-projects/go-control-erp/docs/ADR-001-architecture-standards.md`). Toda nova lógica em `backend/apps/backoffice/platform/services.py`, queries em `repositories.py`.
- **Convenção do projeto**: o agente Bolt deve criar symlinks de PRD/plano/architecture em `evo-nexus/workspace/projects/go-control-erp/` (memória `feedback_go_control_workspace_symlinks`).
- **Backend já tem** layering correto (`views.py`, `services.py`, `repositories.py`, `exceptions.py`, `serializers.py` separados em `backoffice/platform/`). Aproveitar.
- **Endpoint existente** `POST /api/v1/platform/planos/` (`PlanosListView` em `views.py:538`) já chama `PlanoService().criar(modulos_input=...)`. Estender contrato em vez de criar novo endpoint sempre que possível.
- **`auto_popular_plano`** (`apps/licencas/services.py:200-239`) cria `PlanoRecurso` automaticamente para recursos vinculados aos módulos incluídos quando não se passa `modulos_input`. Avaliar se reaproveita esse caminho ou se o wizard passa lista explícita.
- **Tipos de valor**: usar `models.TextChoices` para `tipo_valor` — choices: `boolean`, `inteiro`, `string`, `data`, `mes_ano`.
- **`mes_ano`**: representação no JSONField como string `YYYY-MM` (não criar tipo customizado no banco).

## 7. Métricas de sucesso

- Operador cria plano completo (dados + 5 módulos + 10 recursos parametrizados) em ≤ 3 minutos sem trocar de tela.
- 100% dos novos planos criados via wizard têm `PlanoModulo` e `PlanoRecurso` consistentes (sem necessidade de "completar" depois pela tela antiga).
- Zero regressão: suíte `apps/licencas/tests/` e `apps/backoffice/platform/tests/` continua verde.
- Adicional: testes novos cobrem `PlanoService.criar_completo` (happy path + 3 erros) com fakes de repository.

## 8. Open questions

- [ ] **Endpoint único vs múltiplos calls?** O endpoint atual `POST /planos/` aceita `modulos_input=[{modulo_code}]` mas **não** aceita configuração de `PlanoRecurso`. Duas opções:
  - **A) Estender o payload** de `POST /planos/` para aceitar `modulos: [{modulo_code, recursos: [{recurso_id, disponivel, valor}]}]` e fazer tudo em uma transaction no service. Mais limpo, atômico.
  - **B) Orquestrar no frontend**: chamar `POST /planos/` + N `POST /planos/{tag}/modulos/{pm_id}/recursos/` em sequência, fazendo rollback manual em caso de falha (deletar plano). Mais simples no backend, mais frágil no frontend.

  **Recomendação Compass:** opção A (atômica). Risco: baixo — `PlanoService.criar` já abre `@transaction.atomic`. Risco de regressão sobre clientes existentes do endpoint: nulo se o novo campo `modulos[].recursos` for opcional.

- [ ] **Onde armazenar o `valor` do `PlanoRecurso`?** Hoje `PlanoRecurso.params_default` é um `JSONField`. Convenção proposta: chave `"valor"` dentro do JSON (`{"valor": 5}` para inteiro, `{"valor": "2026-06-15"}` para data, `{"valor": true}` para boolean, `{"valor": "2026-06"}` para mes_ano, `{"valor": "abc"}` para string). Alternativa: criar um campo `valor` typed no `PlanoRecurso` — **não recomendado** (mistura schema com semântica volátil). **Decidir antes do Step 1.**

- [ ] **Validação client-side do `valor` por `tipo_valor`**: usar PrimeReact built-ins (`InputNumber`, `Calendar`) é suficiente, ou criar `ValueInput` wrapper polimórfico? **Recomendação:** wrapper em `components/wizard-plano/ValueInput.tsx` para concentrar a regra (custos baixos, ganho de DRY).

- [ ] **Onde a flag `editavel_na_criacao` será efetivamente honrada?** Aqui o wizard de plano só *registra* a flag no Recurso e a *exibe* no passo 3. O **comportamento real** (campo travado durante criação de licença) acontece no `PlatformNovaLicencaPage`, fora do escopo deste PRD. Confirmar se Eduardo quer que este PRD inclua também a aplicação no wizard de licença (provável feature paralela em outro ciclo).

- [ ] **Remover o `NovoPlanoSidebar` antigo?** Sugestão Compass: **manter no primeiro PR** (não-disruptivo); adicionar botão "Novo plano (wizard)" e marcar o Sidebar antigo como deprecated. Remover em ciclo seguinte. Confirmar.
