---
author: claude
agent: compass-planner
type: work-plan
date: 2026-05-12
plan-name: wizard-nova-licenca
feature: wizard-nova-licenca
project: go-control-erp
status: draft
mode: direct
---

# Work Plan — Wizard de Criação de Licença (Platform Admin)

## Context

PRD aprovado em `[C]prd-wizard-nova-licenca.md`. O wizard substitui o fluxo manual de criação de Conta → Empresa → Licença → Overrides por uma página dedicada de 4 passos, exclusiva para registros novos. Decisões já fechadas pelo usuário: 1 licença por empresa, overrides aplicados a todas as licenças do lote, página dedicada (não sidebar).

## Objectives

- Entregar a rota `/licencas/nova` com a página `PlatformNovaLicencaPage.tsx` funcional.
- Reusar `platform.ts` para todas as chamadas; estender tipos só onde for específico do wizard.
- Garantir resiliência a erro parcial no passo 4 com retry idempotente local.
- Cobrir os 10 critérios de aceitação do PRD com testes unitários (validação de formulário) e um teste de integração feliz (mock do service layer).

## Guardrails

### Must Have

- Reuso de componentes PrimeReact (Steps, InputText, Dropdown, Checkbox, Button, Toast) — sem nova biblioteca.
- Sequência de chamadas idêntica ao PRD: Conta → Empresas extras → GET empresas → Licenças → Overrides.
- Estado do wizard preservado entre passos (componente único, state lifting).
- Validação client-side de CNPJ (DV) e slug (kebab-case + unicidade no envio).
- Painel de progresso textual no passo 4 + painel de erro parcial com botão "Tentar novamente".
- Confirm dialog ao cancelar/sair se houver progresso preenchido.

### Must NOT Have

- Sem alteração no backend (sem novos endpoints ou novos campos).
- Sem transação atômica no backend (não tentar criar uma — usar orquestração frontend).
- Sem override por empresa (mesma config para todas as licenças do lote).
- Sem seleção de Conta/Empresa/Plano existentes (PRD é exclusivo para novos).
- Sem testes E2E nesta entrega (cobertura E2E fica para próxima iteração).
- Sem alteração das páginas atuais de Contas/Empresas/Licenças.

## Task Flow

```
Step 1 (scaffold rota + página) → Step 2 (passos 1 e 2 do wizard) → Step 3 (passo 3: plano + overrides)
                                                                            ↓
Step 6 (testes + verify) ← Step 5 (entry point + navegação) ← Step 4 (passo 4: revisão + execução)
```

## Detailed TODOs

### Step 1 — Scaffold da rota, página e tipos do wizard

- **What:**
  - Criar `pages/PlatformNovaLicencaPage.tsx` com layout base (cabeçalho, componente `<Steps>` do PrimeReact com 4 passos, área de conteúdo, footer com Voltar/Avançar/Cancelar).
  - Registrar rota `/licencas/nova` em `app/router.tsx`.
  - Definir tipo `WizardState` (interno à página) com campos: `conta` (ContaCreatePayload-like), `empresasExtras` (EmpresaCreatePayload[]), `planoId`, `moduleOverrides` (Map<module_code, ativo:bool>), `recursoOverrides` (Map<recurso_id, ativo:bool>), `dataInicio` (string ISO), `status` (string).
  - Definir tipo `WizardProgress` para o passo 4 (lista de etapas com estados `pending | running | done | error`).
- **Owner agent:** `@bolt-executor`
- **Acceptance criteria:**
  - **Given** acesso a `/licencas/nova`, **When** a página monta, **Then** vejo o `Steps` com 4 passos, passo 1 ativo, botão "Avançar" desabilitado por enquanto.
  - Sem regressão em outras rotas (router compila e build passa).
- **Estimated complexity:** LOW

### Step 2 — Passos 1 (Conta + owner) e 2 (Empresas extras)

- **What:**
  - **Passo 1:** formulário com `nome`, `cnpj_matriz`, `slug`, `razao_social`, `owner_email`, `owner_nome`, `owner_phone`. Auto-sugestão de slug a partir do nome (kebab-case sem acentos), parando quando o usuário editar manualmente. Validações: required em todos, CNPJ por DV, email válido, slug regex `^[a-z0-9-]+$`. Botão "Avançar" só habilita quando o passo é válido.
  - **Passo 2:** lista editable de empresas extras. Botão "+ Adicionar empresa" abre um sub-form com `cnpj`, `razao_social`, `tipo` (Dropdown: filial/independente — matriz já existe via passo 1). Validação: CNPJ válido + distinto do `cnpj_matriz` e dos demais já adicionados no wizard. Permite remover empresa pelo botão de lixeira. "Avançar" sempre habilitado (passo 2 é opcional).
- **Owner agent:** `@bolt-executor` (com `@canvas-designer` se precisar refinar a UX)
- **Acceptance criteria:**
  - **Given** estou no passo 1, **When** digito "Lojas Sigma" em `nome` sem ter tocado em `slug`, **Then** o campo `slug` mostra `lojas-sigma`. **When** edito `slug` para `sigma`, e depois mudo `nome` para "Sigma Brasil", **Then** `slug` continua `sigma` (não sobrescreve).
  - **Given** CNPJ inválido em qualquer campo de CNPJ, **When** tento avançar, **Then** o campo mostra erro e o avanço é bloqueado.
  - **Given** estou no passo 2 e adicionei a empresa "Filial SP" com CNPJ X, **When** tento adicionar outra empresa com o mesmo CNPJ X (ou igual ao `cnpj_matriz`), **Then** vejo erro "CNPJ duplicado" e a empresa não é adicionada.
  - **Given** adicionei 2 empresas no passo 2, **When** volto para o passo 1 e avanço de novo, **Then** as 2 empresas continuam visíveis no passo 2 (estado preservado).
- **Estimated complexity:** MEDIUM

### Step 3 — Passo 3: seleção de plano + grade de módulos/recursos

- **What:**
  - Dropdown com planos ativos (carregar via `platformService.listPlanos({ ativo: true })` — confirmar nome real do service).
  - Ao selecionar plano, carregar `PlanoModuloComRecursos[]` (já existe em `platform.ts`).
  - Renderizar lista de módulos (checkbox por módulo, padrão "ativo" para todos os módulos do plano). Abaixo de cada módulo, lista de recursos com checkbox (padrão "ativo").
  - Estado interno: dois `Map`s (`moduleOverrides`, `recursoOverrides`). Só guarda entradas onde o valor é **diferente** do default do plano (i.e., usuário desativou). Isso simplifica a geração de overrides no passo 4.
  - Adicionar campo `data_inicio` (DatePicker, default = hoje) e Dropdown `status` (default = `pendente`). Resolve OQ-2 e OQ-3 com defaults, deixando o usuário sobrescrever se quiser.
  - "Avançar" só habilita se um plano foi selecionado.
- **Owner agent:** `@bolt-executor`
- **Acceptance criteria:**
  - **Given** selecionei um plano com 5 módulos × 3 recursos, **When** desmarco 1 módulo inteiro e 2 recursos individuais, **Then** o estado tem 1 entrada em `moduleOverrides` (false) e 2 entradas em `recursoOverrides` (false), totalizando 3 overrides a aplicar por licença.
  - **Given** mudo de plano após ter desmarcado coisas, **When** o novo plano é carregado, **Then** os overrides são resetados (não persistem entre planos).
  - **Given** não selecionei plano, **When** tento avançar, **Then** o botão "Avançar" está desabilitado.
- **Estimated complexity:** MEDIUM

### Step 4 — Passo 4: revisão + orquestração da criação com tratamento de erro parcial

- **What:**
  - Renderizar resumo: nome da Conta + slug, lista de empresas (matriz destacada + extras), plano selecionado, contagem de overrides (`N módulos desativados, M recursos desativados`), data de início, status.
  - Botão "Criar" inicia a função `executeWizard(state, setProgress)`:
    1. `POST /contas/` com payload do passo 1. Guarda `conta.id` e `empresaMatriz.id` (assumir que o endpoint retorna a matriz; se não, fazer GET).
    2. Para cada `empresaExtra` em `state.empresasExtras`, sequencialmente: `POST /contas/{id}/empresas/`. Guarda IDs criados.
    3. `GET /contas/{id}/empresas/` para confirmar a lista completa de empresas (defensivo — garante consistência com o backend).
    4. Para cada empresa, sequencialmente: `POST /contas/{id}/empresas/{empresa_id}/licencas/` com `plano_id`, `status`, `data_inicio`. Guarda IDs criados.
    5. Para cada licença criada × cada override (`moduleOverrides` + `recursoOverrides`): `POST .../licencas/{id}/overrides/`.
  - `setProgress` atualiza a UI a cada chamada com mensagem textual ("Criando empresa 2 de 3...", "Aplicando overrides 5 de 9...").
  - **Tratamento de erro:**
    - Cada `await` é envolvido em try/catch. Em erro, marca a etapa atual como `error`, guarda a mensagem, e **interrompe** a sequência.
    - Exibe painel com check verde para etapas concluídas + erro vermelho na que falhou + cinza nas pendentes.
    - Botão "Tentar novamente": reusa o estado local (IDs já guardados) e retoma a partir da etapa que falhou. **Não** recria entidades já criadas.
    - Botão "Sair e finalizar manualmente": redireciona para `/contas/{slug}` da Conta criada (se já criada) ou volta para `/licencas`.
  - **Sucesso:** Toast verde "Licença(s) criada(s) com sucesso" + redireciona para `/contas/{slug}`.
- **Owner agent:** `@bolt-executor` (com revisão de `@apex-architect` antes da implementação por causa da resiliência a erro parcial)
- **Acceptance criteria:**
  - **AC-1 (caminho feliz, 1 empresa):** 1 Conta + 1 Licença + 0 overrides criados; redireciona para `/contas/{slug}`.
  - **AC-2 (3 empresas):** 1 Conta + 3 Empresas + 3 Licenças + (3 × N) overrides criados.
  - **AC-6 (erro parcial):** simular falha 500 no POST da 2ª empresa extra. **Then** vejo painel com Conta✅ + Matriz✅ + Filial1✅ + Filial2❌ + restante cinza. Botões "Tentar novamente" e "Sair" visíveis.
  - **AC-7 (progresso visível):** mensagens textuais atualizam pelo menos uma vez por etapa.
- **Estimated complexity:** HIGH

### Step 5 — Entry points: botão "Nova licença" e navegação

- **What:**
  - Adicionar botão primário "+ Nova licença" no header de `/licencas` que navega para `/licencas/nova`.
  - Adicionar item no menu lateral do Platform Admin (se houver) apontando para `/licencas/nova` (opcional — confirmar com Eduardo).
  - Implementar confirm dialog ao tentar sair da rota com state preenchido (`useBlocker` ou similar do react-router).
- **Owner agent:** `@bolt-executor`
- **Acceptance criteria:**
  - **Given** estou em `/licencas`, **When** clico em "+ Nova licença", **Then** sou levado a `/licencas/nova` com wizard zerado.
  - **Given** preenchi o passo 1 e tento navegar para outra rota, **When** o confirm aparece e clico "Cancelar" (do confirm), **Then** permaneço no wizard. **When** clico "Descartar", **Then** sou redirecionado e o estado é perdido.
- **Estimated complexity:** LOW

### Step 6 — Testes + verify

- **What:**
  - Testes unitários (Vitest/Jest, o que estiver em uso no `apps/platform`):
    - Validador de CNPJ (DV correto/incorreto, formato).
    - Auto-sugestão de slug (acentos, espaços, caracteres especiais, parada após edição manual).
    - Cálculo de overrides finais a partir do estado do passo 3.
  - Teste de integração leve (com `msw` ou mocks do `platformService`):
    - Caminho feliz AC-1 (1 empresa, 0 overrides).
    - Erro parcial AC-6 (falha na 2ª empresa) — verifica que retry retoma do ponto certo.
  - Rodar `dev-verify` para garantir que o build passa, lint passa, e a página carrega no dev server.
  - Capturar 2 screenshots (passo 1 vazio + passo 4 com resumo) para anexar ao PR.
- **Owner agent:** `@grid-tester` (testes) + `@oath-verifier` (verify final)
- **Acceptance criteria:**
  - Todos os testes unitários e de integração passam.
  - `pnpm build` (ou equivalente) no `apps/platform` passa sem warnings novos.
  - Lint passa.
  - Screenshots anexados no PR.
- **Estimated complexity:** MEDIUM

## Success Criteria

- [ ] Rota `/licencas/nova` acessível e renderiza wizard de 4 passos.
- [ ] Caminho feliz com 1 empresa cria Conta + 1 Licença em <90s no ambiente de dev.
- [ ] Caminho com 3 empresas cria 1 Conta + 3 Empresas + 3 Licenças + overrides aplicados igualmente.
- [ ] Customização de módulos/recursos no passo 3 gera os `LicencaOverride` corretos para cada licença.
- [ ] Erro parcial mostra painel claro + botão "Tentar novamente" funcional (não duplica entidades).
- [ ] Validações de CNPJ (DV + unicidade) e slug (formato + unicidade no envio) funcionam.
- [ ] Estado do wizard preservado entre passos; descartado apenas via confirm explícito.
- [ ] Build, lint e testes passam.
- [ ] Screenshots anexados ao PR (passo 1 + passo 4).

## Open Questions

(Replicadas do PRD — Eduardo decide ou difere para o `@apex-architect` no Phase 3.)

- [x] **OQ-1** — Validação local: numérico → formato (14 dígitos) + DV; alfanumérico (novo CNPJ) → formato (14 chars). Unicidade verificada via backend ao avançar passo.
- [ ] **OQ-2** — `data_inicio` default: hoje, próximo dia útil, ou pedir ao usuário? — *Plano assume "hoje" com opção de editar no passo 3.* Risco: baixo.
- [x] **OQ-3** — Status inicial: `pendente`. Fixo no wizard.
- [ ] **OQ-4** — Retry idempotente: estado local (proposto neste plano) é suficiente, ou backend precisa de `idempotency_key`? — Risco: baixo para v1.
- [ ] **OQ-5** — Permissão específica `platform:licencas:create`? — Risco: baixo (default = usa a mesma da criação de Conta).

## Risks & mitigations

| Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|
| Erro parcial deixa Conta órfã sem licença | Média | Alto | Painel de retry no passo 4 + redirect para `/contas/{slug}` para o operador finalizar manualmente |
| Cascata de chamadas serial lenta (3 empresas × 3 overrides = 18 calls) | Média | Médio | Considerar `Promise.all` por bucket (todas as licenças em paralelo, todos os overrides de uma licença em paralelo) — fica como otimização, não como guardrail |
| `POST /contas/` não retornar a empresa matriz no payload | Baixa | Médio | Defensivo: sempre fazer `GET /contas/{id}/empresas/` antes de criar licenças |
| Auto-sugestão de slug colidir com slug existente | Média | Baixo | Validação ao avançar do passo 1 (já no PRD) — mostra erro, sugere alternativa |
| `LicencaWizardSidebar` existente confundir o operador (dois wizards) | Baixa | Baixo | Mantém os dois; menu deixa claro "Nova licença completa" vs "Adicionar licença a empresa existente" |

## Handoff

- **Próximo agente:** `@apex-architect` (Phase 3 — Solutioning) — validar a sequência de chamadas, o tratamento de erro parcial, e produzir ADR sobre orquestração frontend vs. backend transacional.
- **Após arquitetura aprovada:** `@bolt-executor` (Phase 4 — Build) executa Steps 1-5; `@grid-tester` cobre Step 6; `@oath-verifier` faz verify final.
- **Next skill:** `dev-plan` está fechado; próximo é o `@apex-architect` produzir `[C]architecture-wizard-nova-licenca.md` no mesmo feature folder.
