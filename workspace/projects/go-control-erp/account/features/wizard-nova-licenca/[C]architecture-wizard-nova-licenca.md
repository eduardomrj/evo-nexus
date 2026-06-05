---
author: claude
agent: apex-architect
type: architecture-decision
date: 2026-05-12
topic: wizard-nova-licenca
feature: wizard-nova-licenca
project: go-control-erp
status: proposed
---

# Architecture Decision — Wizard de Criação de Licença (Platform Admin)

## Summary

A orquestração do passo 4 deve ser **serial com paralelização limitada por bucket**, **estado de progresso reativo**, **retry idempotente em memória com persistência opcional em `sessionStorage`**, e **GET defensivo confirmado obrigatório** porque o serializer de resposta do `POST /contas/` não devolve a empresa matriz. O modelo de overrides do passo 3 deve mudar de "diff Map" para "snapshot completo + função pura de derivação" — diffs sobre default do plano são frágeis quando o usuário troca de plano ou edita um valor para o mesmo do default.

## Context

O plano (`[C]plan-wizard-nova-licenca.md` Step 4) orquestra 5 chamadas sequenciais no frontend: `POST /contas/` → N× `POST .../empresas/` → `GET .../empresas/` → N× `POST .../licencas/` → N×M× `POST .../overrides/`. Para um cliente com 3 empresas e 9 overrides isso são **1 + 3 + 1 + 3 + 27 = 35 requests** em série. Em série, a 90s percentile total fica próxima de `35 × p90(latência)`, o que viola a métrica de sucesso do PRD ("<90s"). Em paralelo descontrolado, o operador perde feedback granular de progresso e o backend pode receber rajada que estoure rate limit / pool de conexões.

Além disso, **não existe transação cross-recurso no backend**: `ContasListView.post` em `backend/apps/backoffice/platform/views.py:90-115` faz transação atômica só dentro da criação `Conta + matriz + owner`; cada `EmpresasListView.post` (linha 227), `LicencasListView.post` (linha 758) e `LicencaOverridesListView.post` (linha 890) são endpoints independentes. Qualquer erro parcial deixa entidades órfãs persistidas — recuperação é responsabilidade do frontend.

E há um detalhe que o plano assume otimisticamente: o `ContaAdminSerializer` (`backend/apps/backoffice/platform/serializers.py:24-32`) **não retorna a empresa matriz** no payload de resposta do `POST /contas/`. O plano em Step 4 sub-item 1 diz "Guarda `conta.id` e `empresaMatriz.id` (assumir que o endpoint retorna a matriz; se não, fazer GET)". Esse "se não" já foi resolvido pelo código: **é obrigatório o GET** — não é defensivo, é parte funcional do fluxo.

## Options Considered

### Q1. Orquestração no passo 4 — serial vs. paralelo

| Opção | Pros | Cons | Notas |
|---|---|---|---|
| **A. Serial puro (plano atual)** | Progresso textual trivial (`i de N`); fácil de debugar; nunca estoura backend | Lento: 35 requests × p90 = pode passar de 90s; UX dolorosa em lotes grandes | Status atual do plano |
| **B. Paralelo total via `Promise.all` em cada bucket** | Rápido (~5 round-trips totais); cabe nos 90s | Progresso textual indireto (precisa contador atômico); rajada pode estourar gunicorn workers; erro parcial vira `Promise.allSettled` com agrupamento custoso | Risco real: Django+gunicorn padrão tem `workers=3..5`; 27 overrides paralelos serializam no backend mesmo assim |
| **C. Serial por bucket, paralelo limitado dentro do bucket (escolhida)** | Buckets `empresas`, `licenças`, `overrides` paralelos com concorrência limitada (p.ex. 4); progresso reportado por callback após cada `Promise.resolve`; backend protegido | Implementação um pouco mais complexa (`p-limit` ou pool manual) | Equilibra throughput, controle e UX |

### Q2. Tratamento de erro parcial — retry idempotente

| Opção | Pros | Cons | Notas |
|---|---|---|---|
| **A. Retry estado-em-memória apenas (plano atual)** | Zero mudança backend; rápido de implementar | Se usuário recarregar a aba, IDs criados são perdidos → duplicatas se ele recomeçar (CNPJ duplicado em `EmpresasListView.post` views.py:236-240 protege empresas, mas conta nova com slug diferente não) | OQ-4 do PRD diz "risco baixo" — concordo no caso feliz, **discordo no caso de F5/erro de rede longo** |
| **B. `Idempotency-Key` no header + dedup no backend** | Robusto a refresh, dupla submissão, retry agressivo | Exige mudança backend (fora do escopo do PRD); precisa de TTL + storage | Recomendado para v2, **fora do escopo** |
| **C. Estado em memória + snapshot em `sessionStorage` por wizard-run (escolhida)** | Sobrevive a F5 acidental; sem mudança backend; limpo ao concluir/cancelar | Não cobre fechamento de aba seguido de mudança de máquina, mas isso é caso degenerado | Boa relação custo/benefício para v1 |

### Q3. Estado dos overrides no passo 3 — diff vs. snapshot

| Opção | Pros | Cons | Notas |
|---|---|---|---|
| **A. Diff-based (plano atual: `Map<id, bool>` só armazena divergências)** | Geração de payload trivial; menos memória | **Bug latente:** se usuário marca→desmarca→marca, fica diff vazio quando deveria estar no default; se troca de plano e o default mudou para o mesmo recurso, o diff fica "errado" porque foi computado contra o plano antigo | Não é seguro com troca de plano |
| **B. Snapshot completo (escolhida): `Map<id, {ativo: bool, source: 'plano'\|'usuario'}>` mais derivação por função pura no passo 4** | Estado é verdade absoluta; reset de plano é re-popular; geração de override é função pura `derive(snapshot, planoDefault)` | Mais memória (irrelevante: dezenas a centenas de chaves) | Robusto, testável, igual aos defaults é trivial |
| C. Apenas array de objetos override prontos | Simples de enviar | Não dá pra desfazer/exibir UI sem reconstruir | UI fica difícil |

### Q4. GET defensivo após criar empresas extras

| Opção | Pros | Cons | Notas |
|---|---|---|---|
| **A. Sempre fazer GET (plano atual)** | Garantia de consistência; protege contra deriva | 1 round-trip extra | **Obrigatório**, não defensivo, dado o serializer atual |
| **B. Confiar no que `POST .../empresas/` retorna + matriz do Step 1** | 1 round-trip a menos | Matriz precisa vir de um GET de qualquer jeito (Conta serializer não devolve) | Não economiza nada |

Opção A vence porque o GET seria necessário só para descobrir o `id` da matriz — aproveitar para confirmar a lista completa é grátis.

### Q5. Endpoint batch / atomicidade no backend

| Opção | Pros | Cons |
|---|---|---|
| Criar `POST /contas/wizard/` que faz tudo numa transação | Atomicidade real; 1 request | **Fora do escopo do PRD** ("Sem alteração no backend" no plano `## Guardrails`). Recomendado para v2. |

## Decision

1. **Orquestração** — Serial entre buckets, paralelo limitado (`concurrency=4`) dentro de cada bucket de empresas, licenças e overrides. Implementar com helper local `runBatch<T, R>(items, fn, { concurrency, onProgress })` que retorna `{ results: R[], errors: Array<{item: T, error}> }` mas **interrompe ao primeiro erro** (modo "fail fast" para v1, mais simples para retry).
2. **Erro parcial** — Estado de orquestração persistido em `sessionStorage` sob chave `wizard-licenca-run:{runId}`. Limpo ao concluir (sucesso) ou ao confirmar cancelamento. Retry idempotente lê o estado e pula etapas já marcadas `done`.
3. **Overrides** — Snapshot completo (`Map<id, {ativo, source}>`) no passo 3. Função pura `buildOverridePayloads(snapshot, planoModulos)` derivada no passo 4, gerando 1 entrada por divergência.
4. **GET defensivo** — Promovido a etapa obrigatória da orquestração (sub-passo 1.5), com mensagem de progresso "Confirmando empresas criadas...". Documentar no código: serializer de `POST /contas/` não retorna matriz.
5. **`POST /contas/` retorno** — confirmado em `backend/apps/backoffice/platform/serializers.py:24-32` que `ContaAdminSerializer` só expõe `id, nome, cnpj_matriz, slug, status, ativo, …`. **Nenhuma referência à empresa matriz.** O GET é a única via.

## Consequences

- **Positive:**
  - Latência do passo 4 cai de `35 × p90` para algo próximo de `5 × p90 + 4 × (N/4) × p90` — viável para a meta de <90s do PRD.
  - Erro parcial recupera após F5 acidental.
  - Snapshot de overrides elimina classe de bugs de diff stale.
  - GET defensivo documentado explicitamente — futuro mantenedor não vai "otimizar" removendo.
- **Negative:**
  - Helper `runBatch` adiciona ~40 linhas de utilidade que precisam de teste unitário próprio.
  - `sessionStorage` exige cuidado com PII (CNPJ, email do owner) — limpar ao concluir.
  - Concorrência 4 ainda pode estourar backend se houver query lenta no `POST .../licencas/` (unique check em `LicencasListView.post` views.py:772-780); medir em dev antes de subir.
- **Neutral:**
  - Cliente médio (1-3 empresas) verá pouca diferença vs. serial puro; ganho aparece em lotes grandes.
  - O backend continua sem transação cross-recurso — recomendação para v2 não bloqueia v1.

## Trade-offs Acknowledged

- **Concorrência 4 vs. progresso linear:** com paralelismo dentro do bucket, o contador `i de N` salta de 4 em 4 às vezes. Aceitável; UX continua honesta porque cada `onProgress` reporta a soma corrente.
- **`sessionStorage` vs. `Idempotency-Key`:** opção B é objetivamente melhor para resiliência, mas exige mudança backend que o PRD declarou fora de escopo. Aceito a dívida.
- **Fail-fast em lote vs. continue-on-error:** continue-on-error em buckets de licença/override deixaria o operador com painel mais rico, mas embaralha a recuperação (várias frentes para "retomar"). Fail-fast é mais simples e suficiente para v1; documentar como follow-up.
- **Snapshot completo de overrides usa mais memória:** irrelevante na prática (planos com 50 módulos × 20 recursos = 1000 chaves booleanas — 1KB).

## Recomendações para `@bolt-executor`

1. **Helper `runBatch` isolado em `src/lib/runBatch.ts`** com assinatura:
   ```ts
   async function runBatch<T, R>(
     items: T[],
     fn: (item: T, index: number) => Promise<R>,
     opts: { concurrency: number; onProgress: (done: number, total: number) => void; signal?: AbortSignal },
   ): Promise<{ results: Array<R | { __error: Error; item: T }>; firstError?: { item: T; error: Error; index: number } }>
   ```
   Modo fail-fast: ao primeiro erro, aguarda só os já em vôo e retorna. Testar com `Promise.reject` no meio do batch.

2. **Hook `useWizardOrchestrator`** que encapsula o estado:
   ```ts
   type Step = 'create-conta' | 'create-empresas' | 'verify-empresas' | 'create-licencas' | 'create-overrides';
   type StepState = { status: 'pending'|'running'|'done'|'error'; message?: string; error?: string };
   type RunState = {
     runId: string;
     contaId?: string;
     empresaIds: string[];            // matriz primeiro
     licencaIds: Record<string, string>; // empresaId → licencaId
     overridesCreated: number;
     overridesTotal: number;
     steps: Record<Step, StepState>;
   };
   ```
   Persistir em `sessionStorage` via `useEffect` com debounce 300ms. Limpar em `onUnmount` quando `steps[*].status === 'done'`.

3. **Snapshot de overrides** em `WizardState`:
   ```ts
   type OverrideSnapshot = {
     modulos: Map<string /* modulo_code */, { ativo: boolean; source: 'plano'|'usuario' }>;
     recursos: Map<string /* recurso_id */, { ativo: boolean; source: 'plano'|'usuario' }>;
   };
   ```
   Função pura para derivar overrides a aplicar:
   ```ts
   function buildOverridePayloads(snap: OverrideSnapshot, planoModulos: PlanoModuloComRecursos[]): Array<{ modulo_code?: string; recurso_id?: string; ativo: boolean }> {
     // só emite se source==='usuario' E ativo difere do default do plano
   }
   ```
   Testar com troca de plano (snapshot precisa ser repopulado, não mesclado).

4. **GET defensivo** explícito na sequência em `executeWizard`:
   ```ts
   // 1. POST /contas/
   const conta = await platformService.createConta(payload1);
   // 1.5. GET /contas/{id}/empresas/ — OBRIGATÓRIO: ContaAdminSerializer não retorna matriz
   //      (ver backend/apps/backoffice/platform/serializers.py:24-32)
   let empresas = await platformService.listEmpresas(conta.id);
   // 2. criar empresas extras...
   // 2.5. GET novamente para confirmar lista completa
   empresas = await platformService.listEmpresas(conta.id);
   ```
   Comentário com referência ao arquivo:linha do backend é mandatório — protege contra "otimização" futura.

5. **Concurrency 4 fixo em constante exportada** (`WIZARD_CONCURRENCY = 4`) para fácil ajuste após medir.

6. **`AbortController` no `useWizardOrchestrator`** — se usuário clica "Cancelar" durante execução, abortar requests em vôo. Reaproveitar o `signal` no Axios via `api.post(..., { signal })`.

7. **Status default `pendente`** — alinhado com `LicencaCreateSerializer` (serializers.py:269) que aceita o choice e evita conflict de licença ativa em `LicencasListView.post` views.py:772-780.

8. **Validação client-side de CNPJ alfanumérico** — espelhar a regra do serializer (`backend/apps/backoffice/platform/serializers.py:46-53` e `:157-161`): 14 chars alfanuméricos após `.upper()` e remoção de máscara. **Não inventar validação DV se o backend não exige** — ficou no PRD como OQ-1 resolvido mas o serializer atual valida só comprimento. Confirmar com Eduardo se quer DV no frontend ou se mantém paridade com backend.

## References

- `backend/apps/backoffice/platform/views.py:90-115` — `ContasListView.post`, atômico só dentro de Conta+matriz+owner; retorna `ContaAdminSerializer`
- `backend/apps/backoffice/platform/serializers.py:24-32` — `ContaAdminSerializer` **não inclui empresa matriz** (origem do GET obrigatório)
- `backend/apps/backoffice/platform/serializers.py:35-58` — `ContaCreateSerializer`; CNPJ aceita 14 chars alfanuméricos, sem DV
- `backend/apps/backoffice/platform/views.py:210-259` — `EmpresasListView`; `POST` rejeita CNPJ duplicado por conta (views.py:236-240) — protege retry naïve
- `backend/apps/backoffice/platform/serializers.py:150-161` — `EmpresaCreateSerializer`; mesma regra de CNPJ
- `backend/apps/backoffice/platform/views.py:758-794` — `LicencasListView.post`; unique check `(empresa, aplicativo, status='ativa')` linha 772-780, IntegrityError 409 linha 789-793
- `backend/apps/backoffice/platform/serializers.py:267-276` — `LicencaCreateSerializer`; default `status='pendente'`
- `backend/apps/backoffice/platform/views.py:890-911` — `LicencaOverridesListView.post`; 1 override por request
- `backend/apps/backoffice/platform/serializers.py:336-348` — `LicencaOverrideCreateSerializer`; `XOR(modulo_code, recurso_id)` obrigatório
- `backend/apps/backoffice/platform/views.py:1027-1041` — `PlanoRecursosView`; usado no passo 3 para popular o snapshot
- `frontend/apps/platform/src/services/platform.ts:339-342` — `createConta` retorna `ContaInfo` (sem matriz)
- `frontend/apps/platform/src/services/platform.ts:438-441` — `listEmpresas(contaId)` — chamada do GET obrigatório
- `frontend/apps/platform/src/services/platform.ts:443-446` — `createEmpresa(contaId, payload)`
- `frontend/apps/platform/src/services/platform.ts:488` — `listPlanos()`
- `frontend/apps/platform/src/services/platform.ts:523, 571` — `createLicenca` e `createLicencaOverride`

## Open Questions

- [ ] **OQ-A (médio)** — A unique constraint de licença ativa no backend (`views.py:772-780`) só dispara quando `status='ativa'`. Com default `pendente`, retry naïve não dá conflito. Mas se Eduardo quiser que o wizard crie já como `ativa`, o retry após erro parcial vai bater no 409 ao retomar. Decidir: default `pendente` é definitivo no wizard ou opcional?
- [ ] **OQ-B (baixo)** — Validação DV de CNPJ no cliente: o backend só valida formato (`len==14` alfanumérico). PRD OQ-1 diz "DV para numérico". Implementar DV só no frontend cria divergência cliente/servidor. Recomendação: paridade com backend (só formato) — pedir confirmação.
- [ ] **OQ-C (médio)** — `Idempotency-Key` no backend para v2: vale criar issue?
- [ ] **OQ-D (baixo)** — Endpoint `POST .../wizard/` atômico no backend: vale criar issue para v2?

## Follow-ups

- [ ] **(Bolt)** Implementar `runBatch` + testes unitários antes de plugar no orquestrador
- [ ] **(Bolt)** Snapshot completo de overrides + função pura de derivação + testes
- [ ] **(Bolt)** Persistência `sessionStorage` com cleanup ao concluir
- [ ] **(Bolt)** Comentar no `executeWizard` a referência a `serializers.py:24-32` justificando o GET obrigatório
- [ ] **(Oath)** Verificar latência total em dev com 3 empresas × 9 overrides para validar a meta <90s
- [ ] **(Raven, opcional)** Crítica adversarial focada em concorrência e race conditions no `runBatch` antes da implementação
- [ ] **(Apex futuro)** ADR de v2 cobrindo `Idempotency-Key` + endpoint batch atômico no backend
