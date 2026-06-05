# Plano — Restrição de Acesso ao Platform Admin (GO Control ERP)

> ⚠️ **SUPERSEDED em 2026-05-29** pelo plano `staff-catalog-auth` em
> `workspace/development/features/staff-catalog-auth/[C]plan-staff-catalog-auth.md`.
>
> A decisão foi mudar de "AccessRestrictedPage + email" para reformulação completa:
> AUTH passa a ser o único autenticador (inclusive do Platform Admin), com
> Staff Catalog dedicado e bloqueio de acesso negado no próprio AUTH. Conteúdo
> abaixo preservado apenas para histórico.

**Slug:** `platform-access-restriction`
**Owner do plano:** @compass-planner
**Data:** 2026-05-29
**Próximo agente sugerido:** @apex-architect (curto ADR de 1 página) → @bolt-executor
**Projeto:** `/home/evonexus/evo-projects/go-control-erp/`

---

## Contexto

O Platform Admin (`frontend/apps/platform/`) é exclusivo de usuários com `is_platform_staff=True`. Hoje, quando um usuário comum obtém um JWT válido e tenta acessar o app:

- `PlatformLayout.tsx:58-69` chama `auth.me()` e, se `!is_platform_staff`, executa `navigate('/login')`.
- O efeito: o usuário volta para a tela de login sem qualquer mensagem clara e a equipe não toma conhecimento da tentativa.

O backend (`backend/apps/platform/views/notifications.py:9-21`) já bloqueia chamadas de API não-staff com HTTP 403, mas a experiência de UI e a observabilidade de tentativa são insuficientes.

Eduardo quer (1) UX clara de "Acesso Restrito" para não-staff, (2) notificação por email para a equipe e (3) destinatário da notificação configurável no Platform Admin.

---

## Objetivos (testáveis)

1. Quando um usuário autenticado mas não-staff acessar qualquer rota do Platform Admin, ele aterrissa em uma página dedicada `AccessRestrictedPage` (NÃO no `/login`).
2. Cada tentativa dispara, no backend, um email para o destinatário configurado (default em DB: `gocontrol@automacaosoftware.com.br`).
3. O destinatário é editável pelo staff via uma seção da tela de Configuração do Platform Admin (página `PlatformNotificacoesPage` já existente).
4. O fluxo segue ADR-001: view ⟶ service ⟶ repository; erros de domínio levantam exceções específicas (não `ValueError`/`Exception` genéricos).
5. Reuso obrigatório de `NotificationService.send()` (HTTP loopback para o GO Message) — não adicionar novo dispatcher.

---

## Guardrails

### Must Have
- Página `AccessRestrictedPage` independente, fora do `PlatformLayout` (sidebar não deve renderizar para não-staff).
- Endpoint backend protegido por staff-check com idempotência por rate-limit simples (não enviar mais de 1 email por usuário a cada 5 min — evita flood se o front re-renderizar).
- Destinatário persistido em `PlatformConfig` (key=`platform.access_alert.email`), seguindo o padrão de `notifications.api_key`.
- Novo evento `PLATFORM_ACCESS_DENIED` na tabela `NotificationEvent` (ou reaproveitamento, ver Open Questions Q1) com template do GO Message.
- Logs estruturados (JSON) com `event=access_denied_attempt`, `user_id`, `email_hash`, `ip`, `user_agent` (curto).

### Must NOT Have
- Bloqueio só por frontend (defesa em profundidade — endpoint sempre valida no backend antes de enviar email).
- Email enviado via `send_mail` direto — usar `NotificationService` (loopback para `/api/v1/go-message/dispatch/`).
- Sidebar/layout do Platform aparecendo na tela de Acesso Restrito.
- Novo modelo Django se `PlatformConfig` chave/valor já resolve.
- Logout automático do usuário (ele continua autenticado — apenas não consegue entrar no Platform Admin).

---

## Steps

### Step 1 — Backend: modelo de configuração e exceção (PlatformConfig)
**Complexidade:** XS
**Owner sugerido:** @bolt-executor

**O que fazer:**
- Adicionar nova chave em `PlatformConfig`: `platform.access_alert.email` (valor = email destinatário).
- Migration de dados: criar a row se não existir, com valor default `gocontrol@automacaosoftware.com.br`.
- Adicionar exceção `AccessRestrictedError(PlatformError)` em `backend/apps/platform/exceptions.py`.
- Adicionar exceção `AccessAlertRateLimitedError(PlatformError)` para o caso de rate-limit (status 429).

**Arquivos:**
- `backend/apps/platform/exceptions.py` (append)
- `backend/apps/platform/migrations/00XX_platform_access_alert_email.py` (nova migration de dados)

**Acceptance criteria:**
- Given a migration nunca rodou, When `python manage.py migrate platform` executa, Then `PlatformConfig` tem uma row com `key='platform.access_alert.email'` e `value='gocontrol@automacaosoftware.com.br'`.
- Given a row já existe, When a migration roda novamente, Then o valor NÃO é sobrescrito (idempotência).
- Given um teste tenta `from apps.platform.exceptions import AccessRestrictedError, AccessAlertRateLimitedError`, Then o import sucede.

---

### Step 2 — Backend: repository + service para o alerta de acesso
**Complexidade:** S
**Owner sugerido:** @bolt-executor

**O que fazer:**
- Em `backend/apps/platform/repositories.py`: adicionar métodos no `PlatformConfigRepository`:
  - `get_access_alert_email()` → str (lê `platform.access_alert.email`)
  - `set_access_alert_email(email, updated_by)` → idêntico ao padrão de `set_notification_api_key`.
- Criar `backend/apps/platform/services/access_alert_service.py` com `AccessAlertService` (uma classe, métodos curtos):
  - `notify_denied_attempt(user, ip, user_agent)`:
    1. Aplica rate-limit por `cache.get/set(f'access_alert:{user.id}', ..., 300)`. Se já houve envio nos últimos 5 min, levanta `AccessAlertRateLimitedError` (a view traduz para 429 mas não loga erro).
    2. Resolve destinatário via repository.
    3. Monta variáveis (`user_email`, `user_nome`, `tentativa_em`, `ip`, `user_agent`).
    4. Chama `NotificationService().send('platform_access_denied', destinatario, variaveis)`.
    5. Loga JSON estruturado.
- Adicionar evento `platform_access_denied` ao seeder de `NotificationEvent` (verificar onde existe o seeder atual — provavelmente `apps/platform/migrations/` ou `apps/platform/services/notification_service.py`).

**Arquivos:**
- `backend/apps/platform/repositories.py` (adiciona métodos no PlatformConfigRepository ou cria `AccessAlertRepository` se preferível por SRP)
- `backend/apps/platform/services/access_alert_service.py` (novo)
- Migration de seed para `NotificationEvent` com code `platform_access_denied`

**Acceptance criteria:**
- Given um usuário não-staff dispara o serviço, When `notify_denied_attempt` é chamado pela primeira vez, Then `NotificationService.send` é invocado com `event_code='platform_access_denied'` e o email retornado pelo repository.
- Given o mesmo `user.id` chama o serviço duas vezes em 5 min, When a segunda chamada acontece, Then levanta `AccessAlertRateLimitedError` e NÃO chama `NotificationService.send`.
- Given a config `platform.access_alert.email` está vazia, When o serviço é chamado, Then levanta `NotificationConfigMissingError` (reusa exceção existente).
- Method ≤ 30 linhas, arquivo ≤ 300 linhas (ADR-001 hard limits).

---

### Step 3 — Backend: endpoint POST `/api/v1/platform/access-denied/` (view)
**Complexidade:** XS
**Owner sugerido:** @bolt-executor

**O que fazer:**
- Em `backend/apps/platform/views/` criar `access_alert.py` (ou anexar em `auth.py`). Uma classe `AccessDeniedAlertView(APIView)`:
  - `authentication_classes = []`, `permission_classes = []` (segue padrão dos outros views do platform).
  - Requer JWT válido (usa `request.jwt_payload`), mas explicitamente NÃO requer staff (o ponto é justamente alertar não-staff).
  - Lê `user.id` do payload, captura `ip` de `request.META.get('HTTP_X_FORWARDED_FOR') or request.META.get('REMOTE_ADDR')` e `user_agent` truncado em 200 chars.
  - Chama `AccessAlertService().notify_denied_attempt(...)`.
  - Trata exceções: `AccessAlertRateLimitedError` → 200 `{detail: 'já notificado recentemente'}` (não vaza para o front como erro); `NotificationConfigMissingError` → 200 `{detail: 'notificação não configurada'}` (não bloqueia UX); `NotificationDispatchError` → 200 `{detail: 'falha temporária'}` + log error.
  - **Importante:** view nunca retorna 4xx/5xx para o front nesse fluxo — o objetivo é "best effort, sempre 200" para que o front exiba a tela mesmo se o email falhar.
- Adicionar rota em `backend/apps/platform/urls.py`: `path('access-denied/', AccessDeniedAlertView.as_view(), name='platform-access-denied')`.

**Arquivos:**
- `backend/apps/platform/views/access_alert.py` (novo) — ≤ 30 linhas por método
- `backend/apps/platform/urls.py` (append)

**Acceptance criteria:**
- Given um JWT válido de usuário não-staff, When `POST /api/v1/platform/access-denied/` é chamado, Then retorna 200 e o serviço foi invocado.
- Given JWT ausente/expirado, When o POST é chamado, Then retorna 401.
- Given o serviço levanta qualquer `PlatformError`, When a view processa, Then retorna 200 com `detail` apropriado (nunca 5xx visível ao front).
- View NÃO contém lógica de negócio — apenas valida JWT, monta payload e chama service.

---

### Step 4 — Backend: GET/PUT `/api/v1/platform/access-alert/email/` (CRUD do destinatário)
**Complexidade:** XS
**Owner sugerido:** @bolt-executor

**O que fazer:**
- Adicionar `AccessAlertEmailView(APIView)` em `backend/apps/platform/views/access_alert.py` (ou no mesmo arquivo do Step 3):
  - `GET` retorna `{email: '...'}` (somente staff).
  - `PUT` aceita `{email: '...'}` (somente staff), valida com `EmailField`, salva via repository.
- Reusa o helper `_require_platform_staff(request)` (já em `views/notifications.py:9-21`) — extrair para `views/_helpers.py` se for usado em múltiplos arquivos.
- Serializer `AccessAlertEmailSerializer` em `backend/apps/platform/serializers.py` (apenas `EmailField`).
- Adicionar rota: `path('access-alert/email/', AccessAlertEmailView.as_view(), name='access-alert-email')`.

**Arquivos:**
- `backend/apps/platform/views/access_alert.py` (segunda classe)
- `backend/apps/platform/views/_helpers.py` (opcional — extrair `_require_platform_staff`)
- `backend/apps/platform/serializers.py` (append)
- `backend/apps/platform/urls.py` (append)

**Acceptance criteria:**
- Given staff faz `GET /api/v1/platform/access-alert/email/`, Then retorna 200 com `{email: '<value>'}`.
- Given staff faz `PUT` com `{email: 'novo@dominio.com'}`, Then 200 e a row em `PlatformConfig` reflete o novo valor.
- Given staff faz `PUT` com email inválido (`'naoeemail'`), Then 400 com erro de validação do serializer.
- Given um usuário não-staff faz `GET` ou `PUT`, Then 403.

---

### Step 5 — Frontend: página `AccessRestrictedPage` + redirect no `PlatformLayout`
**Complexidade:** S
**Owner sugerido:** @bolt-executor + revisão @canvas-designer

**O que fazer:**
- Criar `frontend/apps/platform/src/pages/AccessRestrictedPage.tsx`:
  - Layout próprio (sem `PlatformLayout`/sidebar) — segue Design System (IBM Plex, tokens `--bg`/`--surface-a`/`--primary`).
  - Mensagem: "Acesso restrito a administradores da plataforma. Sua tentativa foi registrada."
  - Botão "Sair" → chama `auth.logout()` e `navigate('/login')`.
  - Botão secundário "Voltar ao login" → `navigate('/login')` sem logout.
- Criar `frontend/apps/platform/src/features/access-alert/api.ts`:
  - `postAccessDenied()`: `POST /api/v1/platform/access-denied/`, sem body. Erros silenciados (best-effort).
- Modificar `PlatformLayout.tsx`:
  - Trocar o `navigate('/login')` por `navigate('/access-restricted')` quando `!u.is_platform_staff`.
  - **Antes** de redirecionar, chamar `postAccessDenied()` (fire-and-forget, `.catch(() => {})`).
- Adicionar rota em `app/router.tsx`:
  - `{ path: '/access-restricted', element: <AccessRestrictedPage /> }` — **fora** do `PrivateRoute`, mas com check interno: se `!auth.isAuthenticated()`, redireciona para `/login` (caso contrário a página fica acessível anônima).

**Arquivos:**
- `frontend/apps/platform/src/pages/AccessRestrictedPage.tsx` (novo)
- `frontend/apps/platform/src/features/access-alert/api.ts` (novo)
- `frontend/apps/platform/src/features/access-alert/hooks.ts` (novo, se usar TanStack Query — opcional, fire-and-forget pode dispensar)
- `frontend/apps/platform/src/components/PlatformLayout.tsx` (modificar `useEffect` em `:58-69`)
- `frontend/apps/platform/src/app/router.tsx` (append rota)

**Acceptance criteria:**
- Given um usuário não-staff faz login com JWT válido, When o `PlatformLayout` monta, Then o front chama `POST /api/v1/platform/access-denied/` (fire-and-forget) e navega para `/access-restricted`.
- Given a página `/access-restricted` carrega, Then renderiza sem sidebar do Platform Admin.
- Given o usuário clica em "Sair" na AccessRestrictedPage, Then `auth.logout()` é executado e ele é redirecionado para `/login`.
- Given um usuário anônimo (sem JWT) acessa `/access-restricted` direto na URL, Then é redirecionado para `/login`.
- Given um usuário staff já autenticado acessa `/access-restricted` direto na URL, Then é redirecionado para `/` (não vê a página de bloqueio).
- Nenhum `axios`/`fetch` direto em componente React — toda chamada via `features/access-alert/api.ts` (regra ADR-001 do frontend).

---

### Step 6 — Frontend: campo "Email de alerta de acesso" na tela `PlatformNotificacoesPage`
**Complexidade:** XS
**Owner sugerido:** @bolt-executor

**O que fazer:**
- Em `frontend/apps/platform/src/features/notifications/api.ts`: adicionar `getAccessAlertEmail()` e `putAccessAlertEmail(email)`.
- Em `frontend/apps/platform/src/features/notifications/hooks.ts`: adicionar `useAccessAlertEmail()` (useQuery) e `useUpdateAccessAlertEmail()` (useMutation).
- Criar componente `frontend/apps/platform/src/features/notifications/components/AccessAlertCard.tsx`:
  - Campo `InputText` (PrimeReact) com label "Email para alerta de acesso restrito".
  - Subtítulo: "Recebe notificação quando um usuário não-staff tenta acessar o Platform Admin."
  - Botão "Salvar" que dispara a mutation.
  - Estado de loading + toast de sucesso/erro (padrão `useToast` já presente na página).
- Em `PlatformNotificacoesPage.tsx`: incluir `<AccessAlertCard />` depois de `<ApiKeyCard />` (mesma seção de "Configurações").

**Arquivos:**
- `frontend/apps/platform/src/features/notifications/api.ts` (append)
- `frontend/apps/platform/src/features/notifications/hooks.ts` (append)
- `frontend/apps/platform/src/features/notifications/components/AccessAlertCard.tsx` (novo)
- `frontend/apps/platform/src/pages/PlatformNotificacoesPage.tsx` (1 linha de import + 1 linha de JSX)

**Acceptance criteria:**
- Given staff abre `/notificacoes`, Then o card "Email para alerta de acesso restrito" aparece com o valor atual carregado.
- Given staff edita o email e clica em Salvar, When a mutation conclui, Then toast de sucesso aparece e o `useQuery` é invalidado (próximo render mostra o novo valor).
- Given staff digita email inválido e clica em Salvar, When o backend retorna 400, Then toast de erro com a mensagem do serializer.
- Layout segue Design System (skeleton durante loading, IBM Plex, tokens de cor, botão `.btn.btn-primary` 36px).

---

## Verificação manual (Probe-style — pré-handoff a @oath-verifier)

1. Login como staff → navega para `/notificacoes` → vê o card de Access Alert com email default → edita e salva → recarrega → valor persistiu.
2. Login como usuário não-staff (criar/usar um existente) → ao cair no `/`, é redirecionado para `/access-restricted` (não `/login`).
3. Conferir caixa de entrada do destinatário configurado → email chegou com `user_email`, `ip`, `user_agent`.
4. Tentar de novo com o mesmo usuário não-staff dentro de 5 min → segundo email NÃO chega (rate-limit).
5. Acessar `/access-restricted` deslogado → redireciona para `/login`.
6. Logado como staff, acessar `/access-restricted` direto → redireciona para `/`.

---

## Success criteria (checklist)

- [ ] Migration aplicada com row default em `PlatformConfig`.
- [ ] `AccessAlertService` reutiliza `NotificationService.send()` (zero `send_mail` novo).
- [ ] View `AccessDeniedAlertView` retorna sempre 200 (best-effort).
- [ ] View `AccessAlertEmailView` GET/PUT protegidos por staff (403 se não-staff).
- [ ] `AccessRestrictedPage` renderiza sem sidebar do Platform.
- [ ] Sidebar do `PlatformLayout` não vaza para não-staff em frame algum.
- [ ] Card de Access Alert visível e funcional em `/notificacoes`.
- [ ] Rate-limit de 5 min verificado em teste manual.
- [ ] Logs JSON `access_denied_attempt` aparecem em `platform.notifications`.
- [ ] Nenhuma view contém lógica de negócio; nenhuma chamada ORM fora de repositories (ADR-001).
- [ ] Nenhum arquivo > 300 linhas; nenhum método > 30 linhas.
- [ ] Nenhum `axios`/`fetch` em componente React (frontend ADR-001).
- [ ] Testes: pelo menos 1 teste de serviço (mocking `NotificationService.send`), 1 teste de view (200 best-effort), 1 teste de PUT email (403 sem staff).

---

## Open Questions

- [ ] **Q1 — Reuso de evento `password_reset`?** O `NotificationEvent` `platform_access_denied` deve ser um evento novo (com seu próprio template) ou reusamos um genérico? Recomendo evento NOVO para permitir customização de template independente. **Risco: baixo.** *Decidir antes do Step 2.*
- [ ] **Q2 — Rate-limit por usuário ou por IP?** Plano usa `user.id`. Se um único usuário malicioso só quer floodar a equipe de email, isso resolve. Mas se múltiplos usuários não-staff distintos tentarem em sequência (improvável), cada um gera 1 email. **Recomendo manter por user.id; risco: baixo.**
- [ ] **Q3 — Capturar geolocalização do IP?** Adicionaria valor ao email ("tentativa de São Paulo, IP X"). Implica chamada externa (ipinfo.io ou similar). **Recomendo deferir para v2; risco: baixo.**
- [ ] **Q4 — Página `/access-restricted` deve permitir solicitar acesso?** Por exemplo, um link "Solicitar acesso de administrador" que dispara outro tipo de email. **Fora do escopo desta v1.** Marcar como follow-up.
- [ ] **Q5 — Notificar também via canal `discord` ou `telegram`?** Já que `NotificationService` suporta multi-canal via `canal_code`. **Sim, viável** — o staff pode editar `NotificationConfig` para o evento `platform_access_denied` e escolher o canal. Não exige código extra; só treinamento.

Estas perguntas devem ser respondidas (ou explicitamente deferidas) antes do hand-off para Bolt. Anexar também em `workspace/development/plans/[C]open-questions.md`.

---

## Handoff

- **Próximo:** @apex-architect (ADR curto — 1 página — sobre estratégia de fail-open vs. fail-closed na view do Step 3, e justificativa do rate-limit em cache vs. DB) → @bolt-executor para os 6 steps.
- **Source artifact:** `workspace/development/features/platform-access-restriction/[C]plan-platform-access-restriction.md`
- **What's open:** Q1 a Q5 acima.
- **Expected output do Bolt:** todos os 6 steps implementados + testes + commits atômicos por step + auto-verificação `pytest backend/apps/platform/tests/` e `npm run build` no frontend platform.

---

## Referências do codebase

- `frontend/apps/platform/src/components/PlatformLayout.tsx:58-69` — ponto onde está o redirect atual.
- `frontend/apps/platform/src/app/router.tsx:43-48` — `PrivateRoute` (modelo para gate de rota).
- `frontend/apps/platform/src/pages/PlatformNotificacoesPage.tsx` — host do novo card.
- `frontend/apps/platform/src/features/notifications/components/ApiKeyCard.tsx` — modelo de card de config a clonar.
- `backend/apps/platform/views/notifications.py:9-21` — helper `_require_platform_staff` a extrair/reusar.
- `backend/apps/platform/services/platform_config_service.py` — modelo de `get_cached`/`set_and_invalidate` para chave em `PlatformConfig`.
- `backend/apps/platform/services/notification_service.py` — `NotificationService.send(event_code, destinatario, variaveis)` é o ponto único de despacho.
- `backend/apps/platform/models/misc.py:54+` — `PlatformConfig` model.
- `backend/apps/platform/exceptions.py:41-49` — modelo de `NotificationConfigMissingError`/`NotificationDispatchError`.
- `backend/apps/platform/urls.py:31-35` — padrão de rotas a seguir.

---

## Regras ADR-001 que este plano respeita

- View HTTP-only: `AccessDeniedAlertView` e `AccessAlertEmailView` apenas validam JWT/serializer e delegam ao service.
- Service para regras: `AccessAlertService` orquestra rate-limit + resolução + dispatch.
- Repository para ORM: `PlatformConfigRepository` mantém o acesso a `PlatformConfig`.
- Exceções de domínio: `AccessRestrictedError`, `AccessAlertRateLimitedError` em `exceptions.py` (nada de `raise ValueError`).
- Frontend feature folder: `features/access-alert/api.ts` e `features/notifications/api.ts` isolam todas as chamadas HTTP.
- Hard limits: nenhum dos arquivos novos previstos passa de 150 linhas; nenhum método passa de 30.
