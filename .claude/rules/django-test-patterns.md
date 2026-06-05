# Django Test Patterns — Regras Obrigatórias

Aplica-se a **todos os agentes** (Grid, Bolt, Hawk, Oath, Lens, etc.) que escrevem ou revisam testes Django/DRF no projeto go-control-erp (e qualquer projeto com Django + DRF).

---

## REGRA CRÍTICA — MagicMock + DRF DateTimeField causa OOM

### O problema

`DateTimeField.enforce_timezone()` do DRF tenta chamar `.astimezone()` em qualquer valor que não seja um datetime real. Quando o valor é um `MagicMock`, `.astimezone()` retorna outro `MagicMock`, que retorna outro, indefinidamente. Isso **não é recursão de stack** (não aciona `RecursionError`) — é um loop de heap que aloca objetos sem parar até consumir toda a RAM disponível.

**Cascata real que aconteceu neste projeto:**
1. Teste com `MagicMock` sem `datetime_field = None` → pytest consome 10+ GB
2. pytest roda dentro do serviço `evonexus-discord-plus` (ferramenta do Claude)
3. Serviço atinge `MemoryMax` → OOM-kill derruba o Bun server inteiro
4. Sessões ativas são perdidas, usuário vê bot travado

### A regra

> **Todo `MagicMock` que representa uma instância de model Django e será passado a um serializer DRF deve ter TODOS os campos `DateTimeField` explicitamente definidos como `None`.**

Isso inclui:
- O mock de **entrada** (passado ao service/view que processa a request)
- O mock de **resposta** (retornado pelo service/view e serializado na response)

### Padrão ERRADO

```python
# ❌ Só seta os campos que o teste usa — DateTimeFields ficam como MagicMock
intent = MagicMock()
intent.id = uuid.uuid4()
intent.status = 'processing'
intent.method = 'pix'
# created_at, updated_at, enqueued_at, emitted_at, expires_at... são MagicMock → OOM

# ❌ MagicMock inline sem proteção de datetime
enqueued = MagicMock(status='processing', method='boleto', processing_substate='queued')
# enqueued.enqueued_at é MagicMock → OOM quando serializado
```

### Padrão CORRETO

```python
# ✅ Helper que protege TODOS os DateTimeFields do modelo
def _make_intent_mock(*, status='requires_emission', method='pix',
                      empresa_id=None, payer_address=None):
    intent = MagicMock()
    intent.id = uuid.uuid4()
    intent.empresa_id = empresa_id or uuid.uuid4()
    intent.status = status
    intent.method = method
    intent.payer_address = payer_address
    intent.processing_substate = 'queued'
    # Previne DRF DateTimeField.enforce_timezone(MagicMock) loop infinito de heap
    intent.due_date = None
    intent.expires_at = None
    intent.chargeback_received_at = None
    intent.cancel_attempted_at = None
    intent.enqueued_at = None
    intent.emitted_at = None
    intent.created_at = None
    intent.updated_at = None
    return intent

# ✅ Mock inline também precisa de proteção
enqueued = MagicMock(status='processing', method='boleto', processing_substate='queued')
enqueued.enqueued_at = None  # evita DateTimeField.enforce_timezone(MagicMock) loop
```

### Como identificar os DateTimeFields que precisam de proteção

Antes de criar o mock, leia o modelo:

```python
# No models.py — cada DateTimeField deve virar = None no mock
class PaymentIntent(models.Model):
    due_date = models.DateTimeField(...)       # → mock.due_date = None
    expires_at = models.DateTimeField(...)     # → mock.expires_at = None
    enqueued_at = models.DateTimeField(...)    # → mock.enqueued_at = None
    emitted_at = models.DateTimeField(...)     # → mock.emitted_at = None
    created_at = models.DateTimeField(...)     # → mock.created_at = None
    updated_at = models.DateTimeField(...)     # → mock.updated_at = None
```

### Como detectar o problema em review

Se você estiver revisando um teste e vir qualquer `MagicMock()` que:
1. Representa um model com `DateTimeField`
2. Será passado a um serializer DRF (direto ou via view)
3. Não tem os campos DateTime explicitamente definidos como `None`

**→ Isso é um bug crítico. Rejeite ou corrija antes de aprovar.**

---

## REGRA 2 — Não mockar DateTimeField com `MagicMock()` diretamente

```python
# ❌ NUNCA faça isso
intent.created_at = MagicMock()  # mesmo resultado que não setar

# ✅ Sempre None, datetime real, ou timezone-aware datetime
intent.created_at = None
intent.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
```

---

## REGRA 3 — Verificar ambos os mocks: entrada E saída

O erro mais comum é proteger apenas o mock de entrada e esquecer o mock de resposta (que também passa pelo serializer):

```python
# Teste que protege entrada mas esquece a saída — ainda causa OOM
intent_in = _make_intent_mock(...)   # ✅ protegido pelo helper

enqueued = MagicMock()               # ❌ mock de saída sem proteção
enqueued.status = 'processing'
# enqueued.enqueued_at é MagicMock — o serializer vai causar OOM aqui
```

---

## Referência de campos por modelo (go-control-erp)

| Modelo | DateTimeFields que precisam de `= None` |
|---|---|
| `PaymentIntent` | `due_date`, `expires_at`, `chargeback_received_at`, `cancel_attempted_at`, `enqueued_at`, `emitted_at`, `created_at`, `updated_at` |
| `EmpresaMirror` | `created_at`, `updated_at` |
| `ApiKey` | `expires_at`, `rotated_at`, `created_at`, `updated_at` |
| `PaymentAttempt` | `started_at`, `finished_at`, `created_at`, `updated_at` |
| Qualquer model Django | Rode `grep -n 'DateTimeField' apps/*/models.py` e proteja todos |

---

## Histórico

Este padrão causou pelo menos 3 incidentes de OOM no projeto go-control-erp entre maio e junho de 2026, levando ao travamento do serviço Discord Plus e perda de sessões ativas. A causa-raiz em todos os casos foi `MagicMock` sem `datetime_field = None` em testes DRF.
