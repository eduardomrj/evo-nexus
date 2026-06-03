---
author: claude
agent: compass-planner
type: work-plan
date: 2026-05-22
plan-name: plano-wizard
status: draft
mode: direct
---

# Work Plan — Wizard de Criação de Plano (Platform Admin)

## Context

O dono pediu substituir o `Sidebar` simples de criação de plano em `/planos` por um wizard multi-step em `/planos/novo` no Platform Admin do GO Control ERP. O wizard precisa cobrir dados do plano, seleção de módulos e — passo central — configuração de **recursos** com inputs tipados (boolean/inteiro/string/data/mes_ano) e respeito à flag de "editável na ativação". Requer 2 campos novos em `Recurso` (`tipo_valor`, `editavel_na_criacao`), nova orquestração atômica no backend para criar plano + módulos + recursos em uma transação, e uma nova página/feature no frontend.

## Objectives

- Adicionar `tipo_valor` e `editavel_na_criacao` em `platform.Recurso` com migration retrocompatível.
- Expor os novos campos no `RecursoSerializer` e no formulário existente (`ModuloSidebarForm`).
- Estender `PlanoService.criar` (ou criar `criar_completo`) e o endpoint `POST /api/v1/platform/planos/` para aceitar configuração de recursos junto, em uma transação.
- Criar rota `/planos/novo` com wizard de 4 passos (Dados → Módulos → Recursos → Revisão) seguindo padrão de `PlatformNovaLicencaPage`.
- Renderizar inputs tipados no passo de recursos com travamento read-only para recursos não editáveis na ativação.
- Conformidade total com ADR-001.

## Guardrails

### Must Have
- Migration aplica defaults (`tipo_valor='boolean'`, `editavel_na_criacao=true`) sem quebrar recursos legados nem testes existentes.
- Toda lógica de criação em cascata vive em `PlanoService` com `@transaction.atomic` — view permanece thin (≤ 30 linhas por método).
- Frontend: chamadas API exclusivamente em `services/platform.ts` (padrão atual do Platform Admin); página de wizard ≤ 250 linhas (composição) e cada step ≤ 200 linhas.
- `sessionStorage` para sobreviver a F5 (mesmo padrão de `PlatformNovaLicencaPage`).
- Symlinks dos artefatos em `workspace/projects/go-control-erp/` (memória `feedback_go_control_workspace_symlinks`).
- Suíte completa (`pytest backend/apps/`, lint frontend, `tsc --noEmit`) verde antes do PR.

### Must NOT Have
- Nenhum `axios`/`fetch` direto dentro de `.tsx` de página ou step.
- Nenhuma chamada ORM (`Recurso.objects.*`, `PlanoRecurso.objects.*`) fora de `repositories.py`.
- Nenhum `except Exception:` engolindo erros.
- Não remover o `NovoPlanoSidebar` antigo neste ciclo (deprecar apenas).
- Não tocar no fluxo de criação de licença (`PlatformNovaLicencaPage`) — escopo separado.
- Não criar tipo customizado de banco para `mes_ano` — armazenar como string `YYYY-MM` no `params_default` JSON.

## Task Flow

```
Step 1 (model+migration) → Step 2 (serializer+ModuloSidebarForm) → Step 3 (PlanoService extensão + endpoint atômico) → Step 4 (rota+esqueleto wizard+sessionStorage) → Step 5 (Step 1+2 do wizard: Dados+Módulos) → Step 6 (Step 3 do wizard: Recursos com ValueInput tipado) → Step 7 (Step 4 do wizard: Revisão+submit + testes E2E)
```

## Detailed TODOs

### Step 1 — Backend: novos campos em `Recurso` + migration
- **What:**
  1. Adicionar em `backend/apps/platform/models.py` (na classe `Recurso`):
     - `TIPO_VALOR_CHOICES` (TextChoices: `BOOLEAN='boolean'`, `INTEIRO='inteiro'`, `STRING='string'`, `DATA='data'`, `MES_ANO='mes_ano'`).
     - `tipo_valor = CharField(max_length=16, choices=TIPO_VALOR_CHOICES.choices, default='boolean')`.
     - `editavel_na_criacao = BooleanField(default=True)`.
  2. Criar migration `apps/platform/migrations/00XX_recurso_tipo_valor_editavel.py` com defaults — retrocompatível.
  3. Rodar `pytest backend/apps/platform/tests/ backend/apps/licencas/tests/` — todos os 80+ testes existentes devem passar.
- **Owner agent:** @bolt-executor
- **Acceptance criteria:**
  - `python manage.py makemigrations platform` gera arquivo sem erros.
  - `python manage.py migrate platform` aplica em dev e em ambiente com recursos pré-existentes (validar com `Recurso.objects.first().tipo_valor == 'boolean'`).
  - Suíte existente 100% verde.
  - `Recurso.clean()` continua proibindo submenu (não alterar comportamento existente).
- **Estimated complexity:** LOW

### Step 2 — Backend serializer + Frontend form (cadastro de Recurso)
- **What:**
  1. Atualizar `RecursoSerializer` em `backend/apps/backoffice/platform/serializers.py:277` adicionando `tipo_valor` e `editavel_na_criacao` em `fields`.
  2. Atualizar `frontend/apps/platform/src/components/ModuloSidebarForm.tsx` para adicionar no formulário de recurso:
     - `Dropdown` para `tipo_valor` com 5 opções (label pt-BR: "Sim/Não", "Inteiro", "Texto", "Data", "Mês/Ano").
     - `Checkbox` "Editável na ativação da licença" para `editavel_na_criacao`.
     - Atualizar `RECURSO_EMPTY` default (linha 173) e edição (linha 199).
  3. Atualizar tipo `RecursoCreatePayload` / `RecursoInfo` em `services/platform.ts` (linha ~585).
- **Owner agent:** @bolt-executor
- **Acceptance criteria:**
  - `GET /api/v1/platform/modulos/{code}/recursos/` retorna `tipo_valor` e `editavel_na_criacao` em cada item.
  - Criar recurso novo via `ModuloSidebarForm` persiste os 2 campos no banco (validar via Django admin ou `psql`).
  - Editar recurso existente no form atualiza os 2 campos.
  - `tsc --noEmit` sem erros novos; lint sem warnings novos.
- **Estimated complexity:** LOW

### Step 3 — Backend: orquestração atômica plano + módulos + recursos
- **What:**
  1. Adicionar `PlanoCreateCompletoSerializer` em `serializers.py` aceitando:
     ```
     { tag, nome, descricao, status, aplicativo_id, is_template, license_model,
       billing_cycle, trial_days, max_devices_default, max_users_default,
       allow_offline_activation, offline_grace_days, requires_activation,
       requires_subscription,
       modulos: [
         { modulo_code, recursos: [ { recurso_id, disponivel, valor } ] }
       ] }
     ```
  2. Estender `PlanoService.criar` (ou adicionar `criar_completo`) em `services/__init__.py` (ou `services/plano_service.py`):
     - Manter `@transaction.atomic`.
     - Após `PlanoRepository.create(...)`, para cada `modulo_code`: chamar `PlanoRepository.add_modulo` (já existe), pegar `PlanoModulo` retornado, e para cada `recurso` na lista: chamar `PlanoRepository.get_or_create_plano_recurso(...)` setando `disponivel` e `params_default={"valor": <valor>}`.
     - Validar que `recurso.modulo_id == modulo.id` (lança `PlanoRecursoNotFoundError` caso contrário).
     - Validar `valor` contra `recurso.tipo_valor` (helper `_coerce_valor(tipo, valor)` no service).
  3. Atualizar `PlanosListView.post` (`views.py:538`) para detectar payload novo (presença de `modulos[].recursos`) e chamar `criar_completo`. Método ≤ 30 linhas.
  4. Testes em `backend/apps/backoffice/platform/tests/test_services.py`:
     - Happy path: cria plano com 2 módulos × 3 recursos cada — verifica 6 `PlanoRecurso` com `params_default["valor"]` correto.
     - Erro: `recurso_id` que não pertence ao módulo → `PlanoRecursoNotFoundError`.
     - Erro: `valor` incompatível com `tipo_valor` → `ValidationError` (ex: string "abc" em recurso `tipo_valor=inteiro`).
     - Atomicidade: simular falha no meio → assert que `Plano` foi rollback (não existe no banco).
- **Owner agent:** @bolt-executor
- **Acceptance criteria:**
  - `POST /api/v1/platform/planos/` aceita payload novo e cria tudo em uma transação.
  - Payload antigo (sem `recursos`) continua funcionando — sem regressão.
  - Os 4 testes novos passam; suíte global verde.
  - Arquivo `views.py` continua ≤ 1184 linhas (sem crescer descontroladamente); `services.py` ≤ 1000 linhas (se passar, dividir em `services/plano_service.py`).
- **Estimated complexity:** MEDIUM

### Step 4 — Frontend: rota, esqueleto do wizard e sessionStorage
- **What:**
  1. Adicionar rota em `frontend/apps/platform/src/app/router.tsx`: `{ path: 'planos/novo', element: <PlatformNovoPlanoPage /> }` (antes ou depois de `'planos'`).
  2. Criar `frontend/apps/platform/src/features/plano-wizard/` com:
     - `types.ts` — `PlanoWizardState`, `PlanoWizardStep1Data`, `Step2Data` (lista de `modulo_code`), `Step3Data` (map `recurso_id → { disponivel, valor }`), `Step4Data` (combined).
     - `api.ts` — wrapper sobre `platform.ts` se necessário (ou usar `platformService` direto).
     - `hooks.ts` — `useNovoPlanoMutation`, `useModulosByAplicativo`, `useRecursosByModulo`.
     - `pages/PlatformNovoPlanoPage.tsx` — composição: header + `Steps` + render do step ativo + botões Voltar/Próximo. ≤ 250 linhas.
     - `components/StepDados.tsx`, `StepModulos.tsx`, `StepRecursos.tsx`, `StepRevisao.tsx`, `ValueInput.tsx`.
  3. Implementar `sessionStorage` (key `wizard-plano-run:{uuid}`) — mesmo padrão de `PlatformNovaLicencaPage:952-958`.
  4. Adicionar botão "Novo plano (wizard)" em `PlatformPlanosPage` ao lado do "Novo plano" atual, link para `/planos/novo`. Não remover o Sidebar antigo.
- **Owner agent:** @bolt-executor (UI com base em padrão existente) / @canvas-designer (consultar se variação visual significativa)
- **Acceptance criteria:**
  - `/planos/novo` carrega sem erro, mostra `Steps` com 4 passos, passo 1 ativo.
  - F5 no meio do fluxo restaura o estado.
  - Botão "Voltar" funciona; botão "Próximo" desabilitado se passo não validado.
  - `tsc --noEmit` limpo.
- **Estimated complexity:** MEDIUM

### Step 5 — Frontend: Step 1 (Dados) + Step 2 (Módulos)
- **What:**
  1. `StepDados.tsx`: replicar campos do `NovoPlanoSidebar` (linhas 80-296 de `PlatformPlanosPage.tsx`): tag (slug), nome, descrição, aplicativo (`Dropdown`), status, is_template, license_model, billing_cycle, trial_days, max_devices_default, max_users_default, allow_offline_activation, offline_grace_days, requires_activation, requires_subscription. Validação client-side: tag/nome/aplicativo obrigatórios.
  2. `StepModulos.tsx`:
     - Carregar `Modulo.objects.filter(aplicativos__id=aplicativo_id, tipo__in=['modulo','tela'])` via endpoint existente (ou criar `GET /api/v1/platform/aplicativos/{id}/modulos/?tipos=modulo,tela` se não existir).
     - Renderizar como lista com `Checkbox` por módulo, com `descricao` em texto secundário.
     - Validação: ao menos 1 módulo selecionado para avançar.
- **Owner agent:** @bolt-executor
- **Acceptance criteria:**
  - Step 1 valida e impede avanço se campos obrigatórios vazios; mensagens de erro inline.
  - Step 2 só mostra `tipo IN ('modulo','tela')` — submenus não aparecem.
  - Trocar aplicativo no Step 1 (se voltar) reseta seleções do Step 2.
  - Estado persistido em sessionStorage entre passos.
- **Estimated complexity:** MEDIUM

### Step 6 — Frontend: Step 3 (Recursos) com `ValueInput` tipado
- **What:**
  1. `ValueInput.tsx`: componente polimórfico que recebe `tipo_valor` e renderiza:
     - `boolean` → `Checkbox`
     - `inteiro` → `InputNumber` (mode='decimal', sem casas decimais)
     - `string` → `InputText`
     - `data` → `Calendar` (dateFormat="dd/mm/yy", value como ISO string YYYY-MM-DD)
     - `mes_ano` → `Calendar` (view="month", dateFormat="mm/yy", value como string YYYY-MM)
     - Se `editavel_na_criacao=false`: adicionar `<Tag value="Fixo na ativação" severity="info" />` ao lado e setar `disabled={true}` (ou `readOnly`).
  2. `StepRecursos.tsx`:
     - Para cada módulo selecionado no Step 2, carregar `GET /api/v1/platform/modulos/{code}/recursos/` (endpoint já existe).
     - Renderizar como `Accordion` (1 painel por módulo, expandido por padrão) com tabela/lista de recursos.
     - Cada recurso: `InputSwitch` para `disponivel` (default `true`) + `<ValueInput>` para o valor (default conforme `tipo_valor`).
     - Estado: map `{ [recurso_id]: { disponivel, valor } }`.
  3. Não exibir recursos cujo módulo pai não foi marcado no Step 2.
- **Owner agent:** @bolt-executor
- **Acceptance criteria:**
  - Cada `tipo_valor` mostra o input correto.
  - Recursos com `editavel_na_criacao=false` ficam visivelmente travados (badge + disabled).
  - Mudar valor / toggle persiste no estado do wizard.
  - Voltar para Step 2 e desmarcar módulo remove os recursos correspondentes do estado.
  - Página `StepRecursos.tsx` ≤ 200 linhas (extrair sub-componentes se passar).
- **Estimated complexity:** HIGH (mais lógica de UI; ValueInput é o ponto que mais erra na primeira tentativa)

### Step 7 — Step 4 (Revisão), submit + testes E2E + symlinks + verificação
- **What:**
  1. `StepRevisao.tsx`:
     - Resumo dos dados (Step 1) em `Fieldset`.
     - Lista de módulos selecionados (Step 2) com badge "incluído".
     - Tabela de recursos (Step 3): colunas `Módulo | Recurso | Disponível | Valor | Editável na ativação`.
     - Botão "Criar plano" (primary) e "Voltar" (secondary).
  2. Submit: montar payload do `PlanoCreateCompletoSerializer` (Step 3 backend) e chamar `platformService.criarPlanoCompleto(payload)` (novo método em `services/platform.ts`).
     - Em sucesso: limpar sessionStorage, `toast.show` sucesso, `navigate(/planos/${tag})`.
     - Em erro: `toast.show` com `extractError`, manter usuário no Step 4.
  3. Smoke E2E manual (documentar passos no arquivo de verificação):
     - Criar plano completo com 2 módulos × 3 recursos cada via wizard.
     - Verificar `psql`: `SELECT count(*) FROM licencas_plano_modulo WHERE plano_id=... → 2`; `SELECT count(*) FROM licencas_plano_recurso WHERE plano_modulo_id IN (...) → 6`.
     - Abrir plano criado em `/planos/{tag}` e validar visualização.
  4. Criar symlinks em `evo-nexus/workspace/projects/go-control-erp/`:
     - `[C]prd-plano-wizard.md` → `../../development/features/plano-wizard/[C]prd-plano-wizard.md`
     - `[C]plan-plano-wizard.md` → idem
     - `[C]verification-plano-wizard.md` → idem
  5. Acionar `@oath-verifier` para conferir todos os ACs do PRD com evidências.
- **Owner agent:** @bolt-executor (build) + @oath-verifier (verify)
- **Acceptance criteria:**
  - Submit funciona end-to-end; plano aparece em `/planos` e tem todos os módulos+recursos no banco.
  - F5 no Step 4 restaura estado.
  - Symlinks criados e apontando para os arquivos corretos.
  - `[C]verification-plano-wizard.md` produzido pelo Oath com PASS em todos os ACs.
  - Lint + `tsc --noEmit` + `pytest` verdes.
- **Estimated complexity:** MEDIUM

## Success Criteria

- [ ] Migration aplicada; recursos legados recebem defaults sem regressão.
- [ ] `ModuloSidebarForm` permite cadastrar/editar `tipo_valor` e `editavel_na_criacao`.
- [ ] `POST /api/v1/platform/planos/` aceita payload com `modulos[].recursos[]` em uma transação atômica.
- [ ] Rota `/planos/novo` funcional com 4 passos navegáveis e estado persistido em sessionStorage.
- [ ] Step 3 do wizard renderiza inputs corretos por `tipo_valor` e trava recursos `editavel_na_criacao=false`.
- [ ] Step 4 cria plano completo via 1 request atômico; navega para detalhe do plano.
- [ ] Suíte backend (`pytest backend/apps/`) verde; frontend (`tsc --noEmit`, lint) verde.
- [ ] `[C]verification-plano-wizard.md` produzido por @oath-verifier com PASS em todos os 9 ACs do PRD.
- [ ] Symlinks em `workspace/projects/go-control-erp/` criados.
- [ ] Conformidade ADR-001 confirmada em code review (`@lens-reviewer`).

## Open Questions

- [ ] **Endpoint atômico (A) vs orquestração no client (B)** — **Recomendação Compass:** A (atômica via `criar_completo`). Risco baixo, mais limpo, segue ADR-001. Aguardar decisão de Eduardo antes de Step 3.
- [ ] **Armazenamento do `valor` no `PlanoRecurso.params_default`** — **Recomendação:** chave `"valor"` no JSON existente (sem schema change). Confirmar antes de Step 3.
- [ ] **`ValueInput` polimórfico vs inputs inline** — **Recomendação:** wrapper `ValueInput.tsx`. Confirmar antes de Step 6.
- [ ] **Honrar `editavel_na_criacao` no wizard de licença** — fora de escopo deste plano; criar feature `licenca-wizard-recursos-readonly` em ciclo separado. Confirmar.
- [ ] **Remover o `NovoPlanoSidebar` antigo** — **Recomendação:** manter neste ciclo (rotular como deprecated); remover em ciclo seguinte após validar o wizard em produção. Confirmar.

> As open questions ficam registradas também em `workspace/development/plans/[C]open-questions.md` (append).

## Handoff

- **Próximo agente:** `@apex-architect` (Phase 3 — Solutioning) para emitir ADR opcional sobre o contrato do endpoint atômico (`PlanoCreateCompletoSerializer`) e a convenção de `params_default["valor"]`.
- **Caso Eduardo dispense ADR** (mudança encaixa em padrão existente): pular direto para `@bolt-executor` (Phase 4) começando pelo Step 1.
- **Verify:** `@oath-verifier` ao final, com base nos 9 ACs do PRD.
- **Code review:** `@lens-reviewer` com checklist do ADR-001 §7.4 antes do merge.

## Pré-condições antes de iniciar

1. Eduardo aprova explicitamente este plano (Compass não delega sem "proceed").
2. Eduardo responde as 5 Open Questions (ou aceita as recomendações Compass) — fundamentalmente as duas primeiras (endpoint atômico + storage do valor) destravam o Step 3.
3. Branch dedicada: `feature/plano-wizard` no repo `go-control-erp` (Bolt cria via `@flow-git`).
