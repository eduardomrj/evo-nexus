---
title: WS intermitente — wss://.../terminal/ws falha no Traefik
assignee: custom-sysops
priority: medium
status: open
created: 2026-04-17
source: oracle / diagnóstico manual
---

## Problema

Erro intermitente no console do browser Chrome:

```
WebSocket connection to 'wss://nexus.myworkhome.com.br/terminal/ws' failed
(anonymous) @ index-B5vrxVY9.js:11
```

A conexão **não falha sempre** — só ocasionalmente. Setup usa Traefik (não Nginx).

---

## Causa raiz provável

Traefik v2/v3 tem `respondingTimeouts.readTimeout=60s` por padrão nos entrypoints.
Em conexões WebSocket de longa duração com períodos de baixa atividade (sem dados), esse timeout encerra a conexão antes dos pings chegarem ao proxy.

O servidor já envia ping de protocolo WS a cada **30s** (`server.js:383`) e o cliente envia ping de aplicação a cada **25s** (`AgentTerminal.tsx:272`) — mas o Traefik precisa ter os timeouts configurados explicitamente.

---

## Ações necessárias

### 1 — CRÍTICO: Configurar timeouts no Traefik estático

No `traefik.yml` (ou args do container Traefik):

```yaml
entryPoints:
  websecure:
    address: ":443"
    transport:
      respondingTimeouts:
        readTimeout: 0       # 0 = sem timeout
        idleTimeout: 3600s   # 1h para idle
        writeTimeout: 0
```

Ou via command-line args:
```
--entrypoints.websecure.transport.respondingTimeouts.readTimeout=0
--entrypoints.websecure.transport.respondingTimeouts.idleTimeout=3600s
```

### 2 — Adicionar `flushInterval=-1` ao stack

No `evonexus.stack.yml`, nos labels do serviço `evonexus_terminal`, adicionar:
```
- traefik.http.services.evonexus_terminal.loadbalancer.responseForwarding.flushInterval=-1
```
Impede o Traefik de bufferizar frames WebSocket antes de encaminhar.

### 3 — Melhoria: reconexão automática no frontend

`AgentTerminal.tsx` e `AgentChat.tsx` não têm lógica de reconexão automática.
Quando o WS cai, o usuário precisa dar F5.
`useGlobalNotifications.ts` já tem o padrão correto — usar como referência:
- backoff exponencial: 1s → 2s → 4s → ... → 30s
- resubscribe ao reconectar

---

## Arquivos relevantes

| Arquivo | Relevância |
|---|---|
| `evonexus.stack.yml` | Labels Traefik — adicionar flushInterval (ação 2) |
| `dashboard/terminal-server/src/server.js:376-384` | Ping protocolo WS (30s) |
| `dashboard/frontend/src/components/AgentTerminal.tsx:272` | Ping aplicação (25s), sem reconexão |
| `dashboard/frontend/src/components/AgentChat.tsx:151` | WS sem reconexão |
| `dashboard/frontend/src/hooks/useGlobalNotifications.ts:84-141` | Padrão correto de reconexão |
| `dashboard/frontend/src/lib/terminal-url.ts` | Resolução da URL `wss://.../terminal/ws` |

---

## Notas de contexto

- A ação 1 (Traefik estático) exige acesso à infra do Traefik, fora do repo
- A ação 2 (stack.yml) é segura e pode ser feita aqui mesmo
- A ação 3 (frontend) é melhoria de resiliência, não bloqueia
