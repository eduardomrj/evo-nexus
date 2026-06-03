# Design Implementation — Async Emission UI (Step 5)

## Aesthetic Direction
- **Purpose:** UI administrativa para monitorar emissões assíncronas de cobrança (operador interno, SRE)
- **Tone:** denso e operacional — sem espaço desperdiçado, informação máxima por pixel
- **Constraints:** sem novos tokens de design; sem padding zerando PrimeReact; sem Inter/Roboto
- **Differentiation:** timeline com duração relativa entre passos (não apenas timestamps absolutos); dot "tempo real" no header do dashboard; polling com intervalos dinâmicos visíveis via badge animado

## Framework
- Detected: React + Vite + TypeScript + TanStack Query v5
- Patterns matched: `useQuery` com `refetchInterval`, `lazy()` routing, `Sidebar` PrimeReact para CRUD, `page-header` + `metric-card` do DS GO Control, `font-mono` para IDs

## Components Created/Modified

### Novos
- `features/payment-intents/components/IntentStatusBadge.tsx` — badge com sub-label de processing_substate + spinner animado
- `features/payment-intents/components/IntentTimeline.tsx` — timeline vertical com duração relativa, ícones coloridos por outcome, timestamp mono
- `features/dashboard/pages/QueueDashboard.tsx` — dashboard com 3 cards (fila, tempo médio, falhas 24h) + tabela de intents em processing

### Modificados
- `features/payment-intents/types.ts` — adicionados `ProcessingSubstate`, `FailureReason`, `QueueStats`, `FailureStats`; campos assíncronos no `PaymentIntent`
- `features/payment-intents/api.ts` — adicionados `getQueueStats()`, `getFailureStats()`
- `features/payment-intents/hooks.ts` — adicionados `useIntentPolling()`, `useQueueStats()`, `useFailureStats()`
- `features/payment-intents/components/PaymentIntentDetailPage.tsx` — integração de `IntentStatusBadge`, `IntentTimeline`, banner de timeout, card de failure_reason, skeleton para Pix/Boleto em processing
- `app/router.tsx` — rota `/dashboard/queue` → `QueueDashboard`

### Backend
- `services/dashboard_service.py` — `get_queue_stats()` + `get_failure_stats(window)` (criado)
- `repositories.py` — `count_by_substate()`, `count_failures_by_code(since)`, `avg_emission_ms(since)` (adicionados ao `PaymentIntentRepository`)
- `views/payment_intents.py` — `QueueStatsView`, `FailureStatsView` (≤30 linhas cada)
- `urls.py` — rotas `payment-intents/queue-stats/` e `payment-intents/failure-stats/` (antes do UUID path para evitar conflito de roteamento Django)

## Design Choices
- **Typography:** IBM Plex Sans (textos) + IBM Plex Mono (timestamps, IDs, durações) — conforme DS §2.1
- **Color:** tokens existentes `--success` / `--warning` / `--error` / `--primary`; badge de processing usa `--warning` com sub-label do substate
- **Motion:** spinner `pi-spin pi-spinner` no badge quando `animated=true`; linha vertical conectora na timeline
- **Layout:** métricas em `.metrics-grid` (3 cards); tabela em `.panel-card` + `.table-wrap`; skeleton em todo `useQuery`

## Polling Strategy (AC-15)
- Intervalos `[2s, 2s, 2s, 5s, 5s, 5s, 10s]` via `refetchInterval` dinâmico
- Para automaticamente em status terminal: `{emitted, failed, paid, partially_paid, expired, cancelled}`
- Timeout 45s → banner âmbar "Está demorando mais que o esperado — recarregue para verificar"
- Usa `useRef` para rastrear índice e `startedAt` sem causar re-renders

## ADR-001 Compliance
- Zero `axios`/`fetch` direto em componente — tudo em `features/*/api.ts`
- Views Django ≤ 30 linhas (delegam para `DashboardService`)
- `DashboardService` sem ORM direto — delega ao `PaymentIntentRepository`
- Novos métodos do repo usando `values().annotate()` e `RawSQL` para JSON extract

## Verification
- TypeScript sem erros (`npx tsc --noEmit` — saída vazia)
- Sintaxe Python válida (`ast.parse` — OK nos 3 arquivos)
- Zero `axios`/`fetch` em componentes (grep limpo)
- Rotas Django com `queue-stats/` e `failure-stats/` registradas ANTES do `<uuid:pk>/` para evitar conflito
- Skeleton + empty state em todos os `useQuery` do `QueueDashboard` e `PaymentIntentDetailPage`
- `padding: 0 !important` não usado em nenhum componente PrimeReact
