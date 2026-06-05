# [C] Discovery — SERKET AI Gateway

**Status:** Em preparação — aguardando complemento de informações do SERKET  
**Data de início:** 2026-04-18  
**Owner:** Oracle → Compass (quando pronto para planejar)

---

## Contexto do Projeto

Integrar o sistema SERKET (gestão de saúde municipal) ao EvoNexus através de um **AI Gateway multi-usuário via Telegram** (e futuramente WhatsApp e Discord), permitindo que diferentes perfis de usuários interajam com agentes especializados de forma isolada e segura.

---

## O que já sabemos

### Stack do SERKET
- **Exposição:** API REST
- **Banco:** MySQL
- **Canais previstos:** Telegram (fase 1), WhatsApp (principal, fase 2), Discord (fase 3)

### Papéis de usuário mapeados

| Papel | Capacidades esperadas |
|---|---|
| **Admin** | Intervenções no banco, alteração de código fonte, deploy |
| **Gerente de Unidade de Saúde** | Pesquisar pacientes, tratamentos, renovar/criar tratamentos, dashboards dinâmicos |
| **Gestor da Secretaria de Saúde** | Informações estratégicas e administrativas (visão macro) |
| **Paciente** | Consultar próprio tratamento, perguntas sobre medicamentos, agendamentos, mensagens ao gerente com resposta automatizada |
| **Médico** | Tratamentos, pacientes, protocolos disponíveis no município, estoque de medicamentos |

### Decisões de design já tomadas
- Tabela de usuários do SERKET receberá campo `telegram_id` (e futuramente `whatsapp_number`, `discord_id`)
- Tabela de usuários terá campo de **perfil/papel** para controle de acesso
- Cada usuário terá **sessão isolada** no gateway (sem vazamento entre usuários)
- Controle de permissão em **duas camadas**: system prompt do agente + ferramentas disponíveis por papel

---

## Arquitetura prevista

```
Canais externos (Telegram / WhatsApp / Discord)
    ↓
[SERKET AI Gateway]
    ├── identifica usuário pelo ID do canal
    ├── GET /api/users/{canal}/{id} → papel + contexto
    ├── cria/reutiliza sessão isolada por usuário
    └── roteia para agente especializado
           ↓
    custom-serket-admin
    custom-serket-gerente
    custom-serket-secretaria
    custom-serket-paciente
    custom-serket-medico
           ↓
    [SERKET MCP Tools]
    Wraps da API REST do SERKET por papel
           ↓
    MySQL
```

### Componentes a construir

| Componente | Descrição | Fase |
|---|---|---|
| `serket-gateway` | Processo Python multi-usuário, roteamento por canal+papel | 1 |
| `serket-mcp-server` | MCP custom com tools da API SERKET | 1 |
| `custom-serket-paciente` | Agente para pacientes (leitura, agendamento, dúvidas) | 1 |
| `custom-serket-medico` | Agente para médicos (protocolos, estoque, pacientes) | 2 |
| `custom-serket-gerente` | Agente para gerentes de unidade (operacional + dashboards) | 2 |
| `custom-serket-secretaria` | Agente para gestão estratégica | 3 |
| `custom-serket-admin` | Agente admin com confirmação dupla em operações destrutivas | 3 |
| Canal WhatsApp | Adaptação do gateway para Evolution API | 2 |
| Canal Discord | Adaptação do gateway para Discord API | 3 |

---

## Fases de implementação

### Fase 1 — Fundação
- [ ] Adicionar campos de canal na tabela de usuários do SERKET (`telegram_id`, futuramente `whatsapp_number`, `discord_id`, `perfil_ai`)
- [ ] Documentar endpoints da API SERKET relevantes por papel
- [ ] Construir `serket-gateway` (Telegram) com roteamento e sessão isolada
- [ ] Construir `serket-mcp-server` (read-only: pacientes, tratamentos, medicamentos)
- [ ] Criar e testar `custom-serket-paciente`

### Fase 2 — Papéis operacionais
- [ ] Expandir MCP para operações de escrita (agendamentos, tratamentos)
- [ ] Criar `custom-serket-medico` e `custom-serket-gerente`
- [ ] Dashboards dinâmicos (gerados pelo @dex, enviados como imagem/PDF pelo Telegram)
- [ ] Adaptar gateway para WhatsApp via Evolution API

### Fase 3 — Papéis privilegiados e multi-canal
- [ ] `custom-serket-secretaria` (visão estratégica consolidada)
- [ ] `custom-serket-admin` (operações destrutivas com confirmação dupla + audit log)
- [ ] Auditoria de acessos (LGPD — quem acessou dados de quais pacientes, quando)
- [ ] Canal Discord

---

## Perguntas em aberto (aguardando Eduardo)

### Sobre a API do SERKET
- [ ] A API tem autenticação por papel (tokens distintos por nível) ou é uma única API com todas as rotas?
- [ ] Quais são os principais endpoints disponíveis hoje? (pacientes, tratamentos, agendamentos, medicamentos, relatórios)
- [ ] Existe documentação (Swagger/Postman) da API?
- [ ] A API suporta paginação e filtros? (importante para buscas do tipo "pacientes com tratamento ativo")
- [ ] Quais operações de escrita a API já suporta?

### Sobre o banco de dados
- [ ] Estrutura das principais tabelas: `usuarios`, `pacientes`, `tratamentos`, `medicamentos`, `agendamentos`
- [ ] Há tabela de log/auditoria de operações já existente?
- [ ] O SERKET tem ambiente de homologação separado do produção?

### Sobre os usuários
- [ ] O campo de perfil na tabela de usuários já existe ou precisa ser criado do zero?
- [ ] O vínculo Telegram ID → usuário será feito pelo próprio usuário (bot solicita CPF/código) ou pela administração?
- [ ] Haverá usuários que são ao mesmo tempo médico e admin? (hierarquia de perfis)

### Sobre os canais
- [ ] WhatsApp: será via Evolution API já integrada ao EvoNexus, ou outro provedor?
- [ ] Discord: é para uso interno da equipe ou também para pacientes?
- [ ] Haverá SLA de resposta (ex: bot deve responder em até X segundos)?

### Sobre segurança e compliance
- [ ] O SERKET processa dados de saúde sensíveis — há requisito de log de auditoria por acesso a dados de pacientes?
- [ ] Existe política de retenção de histórico de conversas?
- [ ] A secretaria de saúde é esfera municipal? Há auditoria do TCE/TCU que exija rastreabilidade?

---

## Próximos passos quando Eduardo retornar

1. Eduardo responde as perguntas em aberto acima
2. Oracle complementa este discovery com as respostas
3. Compass planeja as fases em detalhe (PRD + plano executável)
4. Bolt implementa fase a fase com verificação do Oath

---

## Referências internas

- `.claude/agents/` — onde serão criados os `custom-serket-*`
- `docs/integrations/telegram.md` — referência do canal Telegram
- `docs/guides/channels.md` — arquitetura de canais
- `ADWs/` — onde o `serket-gateway` será implantado como processo
