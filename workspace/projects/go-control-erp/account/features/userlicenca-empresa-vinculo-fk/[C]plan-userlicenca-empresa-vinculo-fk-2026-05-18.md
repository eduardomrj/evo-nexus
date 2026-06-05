# Plano — FK `UserLicenca.empresa_vinculo` → `UserEmpresaVinculo`

**Data:** 2026-05-18
**Autor:** @compass-planner
**Projeto:** GO Control ERP (`/home/evonexus/evo-projects/go-control-erp/backend/`)
**Slug:** `userlicenca-empresa-vinculo-fk`
**Owner técnico (handoff):** @bolt-executor

---

## Contexto

O invite de usuário historicamente criava `UserLicenca` sem `UserEmpresaVinculo`, gerando inconsistência: licenças órfãs sem vínculo de empresa. Já existem dois patches em produção mitigando o sintoma:

- `AccountUsuariosInviteView.post()` (`apps/backoffice/account/views.py:259-270`) — agora cria os dois vínculos juntos no convite.
- `AccountUsuarioEmpresasView.get()` (`apps/backoffice/account/views.py:1175-1201`) — auto-repair lazy que cria `UserEmpresaVinculo` faltante ao listar empresas do usuário.

Esses dois fixes resolvem o caminho conhecido, mas **não impedem novas inconsistências em outros pontos de criação** nem corrigem registros antigos no banco. A solução estrutural é uma FK obrigatória que torne o pareamento `UserLicenca ↔ UserEmpresaVinculo` impossível de violar no nível do banco.

## Objetivos (testáveis)

1. **Toda `UserLicenca` referencia exatamente um `UserEmpresaVinculo`** — verificável por `SELECT COUNT(*) FROM platform_user_licenca WHERE empresa_vinculo_id IS NULL` retornar `0` após Passo 4.
2. **Não é possível criar `UserLicenca` sem `UserEmpresaVinculo`** no código de produção — verificável por grep + revisão dos 3 call sites identificados.
3. **Cascata de status (`empresa_vinculo → user_licenca`) usa a FK** em vez de `filter(user_id, licenca_id__in)` — verificável por leitura de `_cascade_status_to_licencas`.
4. **Zero regressão funcional** — todos os fluxos do `account` (invite, listagem, cascata, mudança de papel) continuam passando nos testes (`apps/platform/tests/`, `apps/backoffice/account/tests/` se existir) e em smoke test manual.

## Guardrails

**Must have:**
- Migração reversível (`makemigrations` + `migrate` rodando limpo em SQLite dev e PostgreSQL prod).
- Janela com campo nullable + data migration + transição para NOT NULL — **nunca uma migração única que possa falhar parcialmente em prod**.
- Backup do `db.sqlite3` (dev) e snapshot/dump do PostgreSQL (prod) antes do `migrate` que torna o campo NOT NULL.
- Plano de rollback documentado para cada passo (especialmente o NOT NULL).

**Must NOT have:**
- Não remover o auto-repair de `AccountUsuarioEmpresasView` **até** o Passo 4 estar completo em prod (rede de segurança).
- Não trocar `on_delete=SET_NULL` por `CASCADE` neste plano — mudança semântica de remoção fica em ADR separado.
- Não tocar em `Membership` nem em `PapelLicenca` — escopo fechado em `UserLicenca` + `UserEmpresaVinculo`.

## Passos

### Passo 1 — Adicionar FK nullable + migração de schema

**O que fazer:**
- Em `apps/platform/models.py` (`UserLicenca`, linha 727), adicionar:
  ```python
  empresa_vinculo = models.ForeignKey(
      UserEmpresaVinculo,
      on_delete=models.SET_NULL,
      null=True,
      blank=True,
      related_name='user_licencas',
      verbose_name='vínculo de empresa',
  )
  ```
- Gerar migração: `python manage.py makemigrations platform` → produz `0028_userlicenca_empresa_vinculo.py`.
- Adicionar `db_index=True` é redundante (FK já indexa), mas confirmar via `sqlmigrate platform 0028`.

**Critério de aceite:**
- `python manage.py migrate platform` roda limpo em SQLite (dev).
- `python manage.py showmigrations platform` lista `0028` como aplicado.
- Modelo importa sem erro; `python manage.py check` retorna `System check identified no issues`.

**Rollback:** `python manage.py migrate platform 0027` reverte sem perda de dados (campo era nullable).

**Complexidade:** baixa.

---

### Passo 2 — Data migration: popular `empresa_vinculo_id` em registros existentes

**O que fazer:**
- Criar `0029_userlicenca_backfill_empresa_vinculo.py` com `RunPython`.
- A função `forwards`:
  1. Para cada `UserLicenca` com `empresa_vinculo_id IS NULL`:
     - Resolver `empresa_id = ul.licenca.empresa_id`.
     - Tentar `UserEmpresaVinculo.objects.get(user_id=ul.user_id, empresa_id=empresa_id)`.
     - Se existir → preencher `ul.empresa_vinculo_id`.
     - Se NÃO existir (caso inconsistente) → criar `UserEmpresaVinculo(user_id, empresa_id, status='active')` e usar o id retornado. Registrar no log da migração quantos foram criados.
  2. Usar `bulk_update` em lotes de 500 para performance.
- A função `reverse` é noop (`migrations.RunPython.noop`) — backfill não precisa ser revertido (campo continua nullable em caso de rollback).
- Usar `apps.get_model('platform', 'UserLicenca')` e `'licencas', 'Licenca'` para historical models — **não importar diretamente**.

**Critério de aceite:**
- Após `migrate`, `SELECT COUNT(*) FROM platform_user_licenca WHERE empresa_vinculo_id IS NULL` → `0` em dev.
- Log da migração imprime: `Backfill: <N> UserLicenca atualizadas, <M> UserEmpresaVinculo criadas` (M = inconsistências reparadas).
- Em SQLite dev, executar antes/depois do backfill e confirmar conta correta.
- Reexecutar `migrate --plan` mostra que a migração é idempotente (nenhum trabalho na segunda corrida).

**Rollback:** `migrate platform 0028` mantém o campo nullable com dados preservados; reverter o efeito é desnecessário pois apenas adicionou referências válidas.

**Complexidade:** média (precisa lidar com inconsistência criando registros).

---

### Passo 3 — Atualizar os 3 call sites para sempre preencher `empresa_vinculo`

**O que fazer:**
- **Call site 1** — `apps/backoffice/account/views.py:259-270` (`AccountUsuariosInviteView.post`):
  - Primeiro criar/obter `UserEmpresaVinculo`, depois criar `UserLicenca` passando `empresa_vinculo=vinculo`.
- **Call site 2** — `apps/backoffice/platform/views.py:1556` (`UserLicencaListView.post`):
  - Antes de `UserLicenca.objects.create(...)`, fazer `vinculo, _ = UserEmpresaVinculo.objects.get_or_create(user=..., empresa_id=licenca.empresa_id, defaults={'status': 'active'})` e incluir `empresa_vinculo=vinculo` no create.
- **Call site 3** — `apps/platform/models.py:858` (signal `seed_papeis_ao_criar_licenca`):
  - Após resolver `membership.user`, fazer `vinculo, _ = UserEmpresaVinculo.objects.get_or_create(user=membership.user, empresa_id=instance.empresa_id, defaults={'status': 'active'})` e incluir `empresa_vinculo=vinculo` no `defaults` do `get_or_create` do `UserLicenca`.
- Envolver os 3 sites em `transaction.atomic()` (já é o caso em alguns; confirmar todos).
- Adicionar/atualizar testes em `apps/platform/tests/` cobrindo: (a) invite cria os dois vínculos e linka; (b) criação via backoffice cria os dois vínculos e linka; (c) signal de licença nova vincula owner com FK preenchida.

**Critério de aceite:**
- `grep -rn "UserLicenca.objects.create\|UserLicenca.objects.update_or_create\|UserLicenca.objects.get_or_create" apps/` retorna **apenas** os 3 sites e cada um passa `empresa_vinculo=`.
- `pytest apps/platform/tests/ apps/backoffice/` passa.
- Smoke test manual: convidar um usuário novo via `/account/usuarios/invite/` → `SELECT empresa_vinculo_id FROM platform_user_licenca WHERE id = ?` retorna não-nulo.

**Rollback:** reverter o commit do passo 3; campo continua nullable do passo 1, então convites antigos (sem FK) ainda funcionam.

**Complexidade:** média (3 arquivos, transação, testes novos).

---

### Passo 4 — Migração para `NOT NULL` + constraint de consistência

**Pré-requisito:** Passos 1-3 em produção há **pelo menos 1 ciclo de deploy estável** (24h+) e `SELECT COUNT(*) FROM platform_user_licenca WHERE empresa_vinculo_id IS NULL` confirmado `0` em prod.

**O que fazer:**
- Alterar `models.py`: remover `null=True, blank=True` da FK.
- Gerar migração `0030_userlicenca_empresa_vinculo_required.py`.
- Adicionar constraint de consistência (Postgres + SQLite suportam via `CheckConstraint` em nível de model ou `RawSQL`):
  ```python
  class Meta:
      constraints = [
          # Já existe unique_together; adicionar:
          models.UniqueConstraint(
              fields=['empresa_vinculo'],
              name='unique_user_licenca_per_empresa_vinculo',
              # Comentário: cada UserEmpresaVinculo pode ter no máximo uma UserLicenca por licenca
              # já garantido por unique_together (licenca, user) + FK; constraint opcional.
          ),
      ]
  ```
  **Decisão:** manter apenas `unique_together = [('licenca', 'user')]` original. A integridade adicional `(empresa_vinculo.empresa_id == licenca.empresa_id)` **não pode ser expressa como CHECK no SQL portátil** — será documentada e validada por testes + assertion em `clean()`.
- Adicionar método `clean()` no modelo:
  ```python
  def clean(self):
      if self.empresa_vinculo and self.licenca_id:
          if self.empresa_vinculo.empresa_id != self.licenca.empresa_id:
              raise ValidationError("empresa_vinculo.empresa deve coincidir com licenca.empresa")
  ```
- Backup obrigatório do banco prod antes do `migrate` (registrar comando e localização do dump em `customizations/post-update/` se aplicável).

**Critério de aceite:**
- Em dev: `migrate` roda limpo e tentar criar `UserLicenca(empresa_vinculo=None)` levanta `IntegrityError`.
- Teste unitário cobrindo: (a) NOT NULL no banco; (b) `clean()` rejeita empresa_vinculo de empresa diferente.
- Em prod: migração aplicada sem downtime perceptível (campo já populado, apenas constraint).

**Rollback:** `migrate platform 0029` re-permite NULL; dados já populados permanecem válidos. Plano de rollback validado em ambiente de staging antes de tocar prod.

**Complexidade:** média (envolve mudança de schema em prod + decisão sobre constraint cross-tabela).

---

### Passo 5 — Refatorar cascata de status para usar a FK

**O que fazer:**
- Em `apps/backoffice/account/views.py:312` (`_cascade_status_to_licencas`), substituir:
  ```python
  user_licencas = UserLicenca.objects.filter(user_id=user_id, licenca_id__in=licenca_ids)
  ```
  por uma assinatura que recebe `empresa_vinculo_ids` e filtra:
  ```python
  user_licencas = UserLicenca.objects.filter(empresa_vinculo_id__in=empresa_vinculo_ids)
  ```
- Ajustar `_cascade_status_to_empresa` (linha 282) para passar `empresa_vinculo_ids` em vez de `licenca_ids`.
- Mantém logs de `UserStatusLog` idênticos.
- Atualizar testes de cascata.

**Critério de aceite:**
- Mudança de status em `UserEmpresaVinculo` propaga para `UserLicenca` corretas — testado com cenário 2 empresas / 2 licenças por empresa.
- `grep -n "_cascade_status_to_licencas" apps/` mostra apenas chamadas com a nova assinatura.
- `pytest apps/backoffice/account/` passa.

**Rollback:** reverter commit; cascata volta a usar `user_id + licenca_id` (continua funcionando, só é menos preciso).

**Complexidade:** baixa (refactor isolado).

---

### Passo 6 — Cleanup: remover auto-repair lazy

**Pré-requisito:** Passo 4 em prod por **pelo menos 7 dias** com zero `UserLicenca.empresa_vinculo_id IS NULL` em logs/queries.

**O que fazer:**
- Em `apps/backoffice/account/views.py:1175-1201` (`AccountUsuarioEmpresasView.get`), remover o bloco "Empresas inferidas via UserLicenca sem vínculo direto — auto-repair".
- A view passa a confiar apenas em `UserEmpresaVinculo` diretos (que agora é a única fonte de verdade graças à FK NOT NULL).
- Manter o select_related para performance.

**Critério de aceite:**
- View retorna o mesmo payload de antes para todos os usuários ativos.
- Smoke test: listar empresas de 3 usuários distintos (owner, gerente convidado, operador) — todos retornam dados esperados.
- Código de auto-repair removido (grep confirma).

**Rollback:** reverter commit; auto-repair volta a funcionar como rede de segurança.

**Complexidade:** baixa (deleção de código).

---

## Critérios de Sucesso (checklist final)

- [ ] FK `UserLicenca.empresa_vinculo` existe, é NOT NULL em prod, tem `on_delete=SET_NULL` documentado (revisar se faz sentido manter SET_NULL com NOT NULL — ver Open Question abaixo).
- [ ] Zero registros com `empresa_vinculo_id IS NULL` em prod por 7+ dias consecutivos.
- [ ] Todos os 3 call sites de criação passam `empresa_vinculo=` explicitamente.
- [ ] Cascata de status (`empresa → licença`) usa a FK.
- [ ] Auto-repair lazy removido.
- [ ] `pytest` verde em todo o backend.
- [ ] Migrações reversíveis testadas em staging.

## Open Questions

- [ ] **`on_delete` final** — `SET_NULL` é incompatível com NOT NULL. Opções: (a) `CASCADE` — deletar `UserEmpresaVinculo` deleta `UserLicenca` (semântica forte mas elimina órfãs); (b) `PROTECT` — bloqueia delete de `UserEmpresaVinculo` enquanto houver `UserLicenca`. Decisão recomendada: **`CASCADE`**, mas confirmar com Eduardo antes do Passo 4. — Risco: médio.
- [ ] **Cleanup do `convidado_por` e do `papel` em casos de re-invite** — não é escopo deste plano, mas vale anotar se aparecer durante o backfill (Passo 2).
- [ ] **Validação cross-tabela (`empresa_vinculo.empresa_id == licenca.empresa_id`)** — implementada via `clean()` (não no banco). Aceitável? Ou queremos CHECK constraint custom para Postgres (e ignorar SQLite)? — Risco: baixo (dados criados pelos call sites sempre satisfazem; risco só em escrita manual ao DB).

## Handoff

- **Próximo agente:** `@bolt-executor`
- **Onde iniciar:** Passo 1 (FK nullable + migração de schema).
- **Bloqueio antes de Passo 4:** confirmar resposta da Open Question sobre `on_delete`.
- **Verificação final:** `@oath-verifier` deve validar evidências para cada critério de sucesso após Passo 6.
