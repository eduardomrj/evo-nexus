# ADR — Modelo `Conta`: status lifecycle + separação de responsabilidades

**Feature:** go-control-conta-status  
**Data:** 2026-05-09  
**Projeto:** GO Control ERP  
**Agente:** @apex-architect  
**Status:** Decisão aprovada por Eduardo Martins

---

## Contexto

O modelo `Conta` (`apps/platform/models.py:123-178`) mistura quatro responsabilidades:

| Responsabilidade | Campos |
|---|---|
| Identidade do tenant | `id`, `slug`, `cnpj_matriz`, `nome`, `schema_name`, `created_at` |
| Estado operacional | `ativo` (boolean — inadequado) |
| Billing legal | `razao_social_billing`, `cnpj_billing` |
| Assinatura comercial | `plano`, `forma_pagamento` |

Problema imediato: `ativo=True/False` não consegue distinguir três situações clinicamente diferentes — conta pendente de ativação, conta operacional, conta cancelada.

---

## Decisão

### 1. `ativo` → `status` (3 estados)

```python
class Status(models.TextChoices):
    PENDENTE  = 'pendente',  'Pendente'
    ATIVADA   = 'ativada',   'Ativada'
    SUSPENSA  = 'suspensa',  'Suspensa'
    CANCELADA = 'cancelada', 'Cancelada'

status = models.CharField(
    max_length=20,
    choices=Status.choices,
    default=Status.PENDENTE,
    db_index=True,
)
```

**Ciclo de vida:**
- `pendente` — conta criada, schema provisionado, aguardando ativação/pagamento
- `ativada` — conta operacional
- `cancelada` — encerrada (schema preservado para auditoria/LGPD, acesso bloqueado)

**Data migration:**
- `ativo=True` → `status='ativada'`
- `ativo=False` → `status='cancelada'`
- Novas contas entram como `pendente`

**Remoção de `ativo`:** duas etapas — migration N adiciona `status`, migration N+1 (sprint seguinte) remove `ativo`.

### 2. Adicionar audit trail

```python
activated_at  = models.DateTimeField(null=True, blank=True)
cancelled_at  = models.DateTimeField(null=True, blank=True)
```

### 3. Centralizar transições em métodos do modelo

```python
def ativar(self): ...
def cancelar(self): ...
```

Nunca espalhar `conta.status = 'ativada'` pelo código.

### 4. `plano` e `forma_pagamento` — ficam no `Conta` por ora

**Decisão:** manter no `Conta` no early stage. Motivo: extrair para `ContaAssinatura` agora seria overhead sem ganho concreto. O problema reportado pelo produto ("não quero na tela básica") é de UI, não de schema.

**Quando migrar para `ContaAssinatura`:** quando aparecer o segundo campo de billing que não cabe no `Conta` (ex: `next_billing_date`, `subscription_status`, `provider_customer_id`).

**UI:** `plano` e `forma_pagamento` saem do painel de edição básica e vão para seção "Faturamento" separada.

### 5. `razao_social_billing` / `cnpj_billing` — ficam no `Conta`

Fazem sentido lá — holding pode ter CNPJ diferente do tenant. Adicionar properties para fallback:

```python
@property
def cnpj_para_nf(self) -> str:
    return self.cnpj_billing or self.cnpj_matriz

@property
def razao_social_para_nf(self) -> str:
    return self.razao_social_billing or self.nome
```

---

## Alternativas rejeitadas

| Alternativa | Por que rejeitada |
|---|---|
| Extrair `ContaAssinatura` agora | Overhead sem ganho concreto no piloto; nada para popular além do plano atual |
| Manter `ativo` como boolean | Não distingue pendente/ativada/cancelada — dor real do produto |
| `status` sem audit trail | Perde rastreabilidade de quando a conta foi ativada/cancelada |

---

## Riscos

1. **Buraco de segurança pré-existente:** nenhum middleware bloqueia tenant com `ativo=False` hoje. Migrar para `status` **não corrige isso sozinho** — requer middleware de enforcement (sprint futura).
2. **Default mudando para `PENDENTE`:** auditar factories/fixtures que criam `Conta()` sem argumentos — vão mudar comportamento.
3. **`setup_demo.py` seta `ativo=True`:** precisa ser atualizado para `status='ativada'`.

---

## Impacto nos arquivos

| Arquivo | Mudança |
|---|---|
| `apps/platform/models.py` | Adicionar `status`, `activated_at`, `cancelled_at`, methods, properties |
| `apps/platform/migrations/0008_conta_status.py` | Migration + data migration |
| `apps/backoffice/platform/serializers.py` | Expor `status` em `ContaAdminSerializer` |
| `apps/backoffice/platform/views.py` | `ContaDetailView.patch` aceita `status` |
| `apps/platform/management/commands/setup_demo.py` | Atualizar para `status='ativada'` |
| `frontend/apps/platform/src/pages/PlatformContasPage.tsx` | Painel de edição: remover plano/pagamento, adicionar status; badge na tabela |
| `frontend/apps/platform/src/services/platform.ts` | Adicionar `status` ao tipo `ContaInfo` |

---

## Próximos passos

1. Migration backend: `status` + audit trail + data migration
2. Serializer + view: expor e aceitar `status`
3. Frontend: painel de edição atualizado + badge de status
4. Sprint seguinte: migration N+1 remove `ativo`
5. Futuro: middleware de enforcement de tenant inativo
