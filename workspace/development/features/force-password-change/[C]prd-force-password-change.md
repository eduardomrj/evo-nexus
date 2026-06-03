# PRD — Force Password Change

**Feature slug:** `force-password-change`
**Projeto:** GO Control ERP
**Owner do PRD:** Compass (Phase 2)
**Data:** 2026-05-24
**Status:** Draft — aguardando aprovação

---

## 1. Problema

Quando um administrador reseta a senha de um usuário pelo backoffice, o backend já marca `User.force_password_change = True` e o endpoint `GET /api/v1/auth/me/` retorna esse flag. **No entanto, o frontend ignora completamente o campo**: o usuário consegue logar com a senha temporária e usar o sistema indefinidamente sem ser obrigado a trocar.

Isso quebra dois requisitos básicos:

1. **Segurança** — uma senha emitida pelo admin pode ficar em uso permanente, conhecida por quem fez o reset.
2. **Compliance / boas práticas** — qualquer ERP que se proponha multi-tenant precisa garantir que credenciais temporárias sejam efêmeras.

## 2. Goals

- G1. Após login, se `force_password_change = True`, o usuário é **bloqueado** em uma página de troca de senha — não consegue navegar para outras rotas até trocar.
- G2. Após trocar a senha com sucesso, o flag vira `False` no banco e o usuário é redirecionado para `/`.
- G3. A solução é compartilhada entre os 4 apps frontend (account, erp, go-message, platform) — uma única implementação em `packages/shared/`, reuso por roteamento em cada app.
- G4. Endpoint backend respeita ADR-001 (view → service → repository), valida força mínima de senha e bloqueia reuso da senha atual.

## 3. Non-goals

- **NG1.** Política completa de expiração de senha (ex.: trocar a cada 90 dias) — fora de escopo.
- **NG2.** Histórico de senhas (impedir reusar as últimas N) — fora de escopo; só validamos contra a senha atual.
- **NG3.** 2FA / MFA — fora de escopo.
- **NG4.** Auto-logout em outras sessões após troca de senha — fora de escopo (pode entrar em fase posterior).
- **NG5.** Tela de "Esqueci minha senha" pública (sem login) — fora de escopo; este PRD cobre apenas troca obrigatória pós-login.

## 4. User stories

### US1 — Usuário com senha resetada pelo admin
> Como usuário do GO Control cuja senha foi resetada pelo admin, quero ser obrigado a definir uma nova senha no primeiro login para que minha conta volte a ser pessoal e segura.

### US2 — Admin resetando senha de usuário
> Como admin que acabou de resetar a senha de um operador, quero ter a garantia de que ele será forçado a trocá-la no próximo login, para que eu não precise comunicar a senha temporária em canais informais.

### US3 — Usuário comum
> Como usuário comum (sem flag), quero que o fluxo de login continue funcionando exatamente como hoje (redirect para `/`), sem nenhuma fricção adicional.

## 5. Acceptance criteria (Given/When/Then)

### AC1 — Login com flag ligado redireciona para troca de senha
**Given** um usuário existe com `force_password_change = True`
**When** ele faz login com sucesso em qualquer um dos 4 apps (account, erp, go-message, platform)
**Then** ao invés de ir para `/`, é redirecionado para `/change-password` e não consegue navegar para outras rotas autenticadas (qualquer tentativa de acessar outra rota o joga de volta para `/change-password`).

### AC2 — Login sem flag funciona normalmente
**Given** um usuário com `force_password_change = False` (ou ausente / null)
**When** ele faz login
**Then** é redirecionado para `/` exatamente como antes — zero regressão no fluxo padrão.

### AC3 — Troca de senha bem-sucedida limpa o flag
**Given** um usuário autenticado na tela `/change-password`
**When** ele submete `new_password` e `confirm_password` iguais e válidos (≥8 chars, não igual à senha atual)
**And** o backend valida e persiste a nova senha via service
**Then** `force_password_change` vira `False` no banco
**And** o frontend recebe 200 OK e navega para `/`
**And** um novo login com a nova senha funciona normalmente.

### AC4 — Validação client-side
**Given** o usuário está em `/change-password`
**When** ele tenta submeter com `new_password` ≠ `confirm_password`, ou senha vazia, ou senha com menos de 8 caracteres
**Then** o submit é bloqueado com mensagem inline (sem chamada de rede).

### AC5 — Validação server-side
**Given** o frontend envia `POST /api/v1/auth/change-password/`
**When** o payload viola alguma regra (senha curta, igual à atual, campos faltando, mismatch)
**Then** o backend retorna **400** com `{ "detail": "<mensagem>", "code": "<enum>" }`
**And** a mensagem é exibida no formulário.
**Codes esperados:** `password_too_short`, `password_mismatch`, `password_unchanged`, `missing_field`.

### AC6 — Endpoint exige autenticação
**Given** uma requisição não-autenticada
**When** ela chama `POST /api/v1/auth/change-password/`
**Then** o backend retorna **401**.

### AC7 — Sem regressão no `/auth/me/`
**Given** o endpoint `GET /api/v1/auth/me/` atual
**When** ele é chamado após este feature ser entregue
**Then** o payload continua contendo `force_password_change: bool` e nenhum outro campo foi removido / renomeado.

### AC8 — ADR-001 compliance
**Given** o código de backend deste feature
**When** revisado por Lens / Oath
**Then** toda lógica de troca de senha está em `services.py`, validação em `serializers.py`, persistência em `repositories.py`, view só faz HTTP I/O. Arquivos ≤ 300 linhas, métodos ≤ 30 linhas, nenhum `raise ValueError` para erro de domínio (usa exceção de `exceptions.py`).

### AC9 — Reuso entre os 4 apps
**Given** o componente `ChangePasswordPage` está em `packages/shared/src/components/`
**When** cada app (account, erp, go-message, platform) registra a rota `/change-password`
**Then** todos importam o **mesmo** componente — zero duplicação de código de troca de senha.

## 6. Constraints

- **C1.** Stack obrigatória: Django REST (backend), React + PrimeReact (frontend), sem Tailwind, CSS por módulo.
- **C2.** ADR-001 é lei do projeto — ver `/home/evonexus/evo-projects/go-control-erp/docs/ADR-001-architecture-standards.md`.
- **C3.** Auth library central: `frontend/packages/shared/src/lib/auth.ts` — qualquer mudança no fluxo de login passa por aqui.
- **C4.** O componente shared deve seguir o mesmo padrão visual do `LoginPage.tsx` existente (mesma `LoginPage.css` ou CSS-irmão).
- **C5.** Endpoint segue convenção `/api/v1/auth/<action>/` (consistente com `/login`, `/me`, etc.).

## 7. Open questions

- **OQ1.** Política mínima de senha além de "≥8 caracteres e diferente da atual" — exigir maiúscula/número/símbolo? **Default proposto:** apenas ≥8 chars e diferente da atual; reforço opcional em fase posterior. Risco: baixo.
- **OQ2.** Após trocar a senha, devemos invalidar / rotacionar os tokens JWT atuais? **Default proposto:** manter o token atual válido (a sessão segue), só zera o flag. Risco: médio (sessões antigas com senha velha continuam ativas, mas o atacante teria precisado da senha original — não da nova).
- **OQ3.** O usuário pode "pular" a troca? **Default proposto:** não — bloqueio rígido até trocar. Risco: baixo (alinhado com a intenção do feature).
- **OQ4.** Logout button visível na `/change-password`? **Default proposto:** sim, para o caso de o usuário precisar sair sem trocar. Risco: baixo.
- **OQ5.** Mensagem amigável ao usuário explicando *por que* ele está sendo forçado a trocar? **Default proposto:** sim, banner no topo: "Sua senha foi resetada pelo administrador. Defina uma nova senha para continuar." Risco: nenhum.

> Decisões sobre OQ1–OQ5 podem ser tomadas pelo Eduardo na revisão ou aceitas como defaults para destravar a execução.

---

## 8. Definition of Done

- [ ] Endpoint `POST /api/v1/auth/change-password/` implementado em camadas (view/service/repository/serializer/exception).
- [ ] Componente `ChangePasswordPage` em `packages/shared/src/components/` com CSS dedicado.
- [ ] Hook / lógica em `packages/shared/src/lib/auth.ts` para detectar `force_password_change` após login e redirecionar.
- [ ] Os 4 apps (account, erp, go-message, platform) registram a rota `/change-password` em seus `router.tsx`.
- [ ] Guard: tentativas de acessar outras rotas com flag ligado redirecionam de volta para `/change-password`.
- [ ] Testes backend: pelo menos 1 happy path + 4 erros (senha curta, mismatch, igual à atual, não autenticado).
- [ ] Manual QA documentado em `[C]verification-force-password-change.md`: login com flag → tela aparece → troca → vai pra `/` → flag zerou no DB.
- [ ] Symlinks criados em `workspace/projects/go-control-erp/features/force-password-change/`.
