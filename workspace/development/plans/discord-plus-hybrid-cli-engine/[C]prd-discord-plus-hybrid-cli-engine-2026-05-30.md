---
author: compass-planner
agent: compass-planner
type: prd
date: 2026-05-30
plan-name: discord-plus-hybrid-cli-engine
status: draft
mode: direct
---

# PRD — Discord Plus modo híbrido C: engine CLI OpenClaude por thread/canal

## Problema

O Discord Plus já mantém gateway Discord próprio, policy, threads e replies seguros, mas o engine atual baseado em SDK v2 não entrega um agente principal real. O prompt padrão de Oracle ajuda na personalidade, porém não equivale a executar o OpenClaude com `--agent oracle`.

Eduardo explicitamente não aceita alterar o core do OpenClaude. Portanto, a solução precisa usar a superfície pública da CLI (`openclaude --agent ...`) para obter o agente real, preservando o Discord Plus como camada de transporte/policy/reply e sem reativar o plugin Discord oficial como gateway duplicado.

## Objetivos

- Permitir que o Discord Plus execute sessões por canal/thread via CLI pública do OpenClaude.
- Configurar o engine por ambiente, inicialmente com `EVONEXUS_DISCORD_PLUS_SESSION_ENGINE=cli` ou nome equivalente.
- Usar agente padrão configurável, inicialmente `oracle`, sem hardcode irreversível.
- Preservar session key por canal/thread/DM e continuidade quando houver suporte público da CLI (`--continue`, session id ou mecanismo equivalente).
- Manter replies e side effects passando pelo mecanismo seguro do Plus, com policy revalidada no gateway.
- Não alterar o core OpenClaude nem duplicar gateway Discord.

## Não objetivos

- Não modificar código do OpenClaude core.
- Não depender do plugin Discord oficial ativo para receber ou enviar mensagens.
- Não ampliar permissões Discord, scopes, intents ou allowlists.
- Não substituir policy, pairing, thread handling ou reply executor do Plus.
- Não resolver definitivamente flags desconhecidas da CLI sem investigação factual.
- Não redesenhar o Discord Plus inteiro; a mudança deve encaixar no supervisor/runner existente.

## Usuários

- **Eduardo / operadores do workspace:** querem conversar no Discord com agentes reais do EvoNexus, especialmente Oracle, com contexto por thread/canal.
- **Agentes EvoNexus acessados via CLI:** devem receber mensagens por sessão correta e responder de forma roteável pelo Plus.
- **Mantenedores do Discord Plus:** precisam de rollback simples para SDK atual/fallback sem tocar o core OpenClaude.

## UX Discord esperada

- Usuário envia mensagem em canal, thread ou DM autorizado.
- Discord Plus aplica policy atual antes de encaminhar qualquer input ao OpenClaude.
- O canal/thread define a sessão lógica.
- A resposta aparece no mesmo local correto, usando o reply seguro do Plus.
- Em thread, a resposta deve respeitar a policy herdada/parent channel já corrigida.
- Se o engine CLI estiver indisponível ou falhar, o usuário recebe erro operacional seguro, sem stack trace nem segredo.
- Com rollback para SDK atual, o comportamento anterior deve voltar sem migração destrutiva.

## Requisitos funcionais

1. Adicionar configuração de engine de sessão:
   - valor atual/legado: SDK;
   - novo valor: CLI;
   - default seguro deve preservar produção atual, salvo decisão explícita de flip.
2. Adicionar configuração de agente padrão:
   - valor inicial desejado: `oracle`;
   - permitir override por env, ex. `EVONEXUS_DISCORD_PLUS_DEFAULT_AGENT=oracle`.
3. Implementar um runner CLI acoplável ao `SessionSupervisor` existente, sem remover o runner SDK.
4. Construir comandos OpenClaude usando apenas interface pública, ex. `openclaude --agent oracle`, com flags de continuidade investigadas antes da implementação final.
5. Mapear `sessionKey` por channel/thread/DM para estado local do Plus.
6. Persistir session ids quando a CLI expuser mecanismo público de continuidade; caso contrário, documentar fallback sem continuidade cross-process.
7. Capturar saída do processo CLI e transformá-la em intents/replies via gateway seguro do Plus, sem o plugin Discord oficial enviar mensagens diretamente.
8. Garantir que o gateway Discord continue único.
9. Manter suporte aos commits locais informados como base operacional: fallback opt-in, reply via parent channel policy, workspace cwd e default agent prompt.

## Requisitos de segurança

- Não imprimir tokens, env completo, headers ou payloads sensíveis em logs.
- Não passar token Discord ao processo CLI salvo se estritamente necessário e documentado; preferir CLI sem canal Discord/plugin ativo.
- Revalidar policy antes de side effects reais (`reply`, `react`, `edit`, `fetch`, `download`).
- Tratar conteúdo Discord como input não confiável.
- Evitar shell interpolation; spawn com array de argumentos.
- Limitar cwd ao workspace/repo configurado e já validado.
- Timeouts e limites de concorrência devem impedir explosão de processos por spam em canais.
- Falhas da CLI devem retornar mensagens operacionais redigidas.

## Critérios de aceitação

### Engine CLI configurável

**Given** o Discord Plus está iniciado com `EVONEXUS_DISCORD_PLUS_SESSION_ENGINE=cli` e `EVONEXUS_DISCORD_PLUS_DEFAULT_AGENT=oracle`  
**When** uma mensagem autorizada chega em um canal permitido  
**Then** o Plus deve criar/usar uma sessão para a `sessionKey` daquele canal/thread e invocar a CLI pública do OpenClaude com agente Oracle ou agente configurado.

### Sem alteração no core OpenClaude

**Given** a implementação foi concluída  
**When** a diff é revisada  
**Then** nenhum arquivo fora do repo `/home/evonexus/evo-projects/evonexus-discord-plus` deve ter sido alterado para suportar o modo CLI.

### Gateway único

**Given** o modo CLI está ativo  
**When** uma mensagem Discord é processada  
**Then** somente o gateway do Discord Plus deve estar logado no Discord, e a CLI não deve iniciar `--channels plugin:discord@...` nem outro client Discord.

### Policy preservada

**Given** um usuário/canal não autorizado envia mensagem  
**When** o modo CLI está ativo  
**Then** a mensagem deve ser bloqueada antes de chamar a CLI.

### Replies via Plus

**Given** o agente real retorna uma resposta  
**When** o Plus publica a resposta no Discord  
**Then** a publicação deve usar o mecanismo seguro já existente do Plus, com policy/target revalidados, e não side effects diretos do plugin oficial.

### Continuidade por thread/canal

**Given** duas mensagens são enviadas na mesma thread autorizada  
**When** a CLI suportar continuidade por `--continue`/session id ou equivalente  
**Then** a segunda mensagem deve reutilizar a continuidade associada à mesma `sessionKey`.

**Given** a CLI não expõe continuidade pública verificável  
**When** duas mensagens chegam na mesma thread  
**Then** o Plus deve usar fallback documentado, com limitação explícita de continuidade cross-process e sem inventar flags privadas.

### Isolamento entre sessões

**Given** mensagens chegam em dois canais/threads distintos  
**When** ambas são processadas no modo CLI  
**Then** cada uma deve usar `sessionKey` e estado separados, sem misturar histórico.

### Rollback

**Given** o modo CLI apresenta falha operacional  
**When** `EVONEXUS_DISCORD_PLUS_SESSION_ENGINE` volta ao valor SDK/legado  
**Then** o Plus deve voltar ao comportamento anterior sem migração destrutiva de dados.

## Riscos

- Flags reais da CLI para stdin, modo headless, continuidade e agent podem divergir do esperado.
- A CLI pode não oferecer streaming/JSON estável, exigindo parser conservador de stdout.
- Se a CLI só responder via transcript textual, a conversão para reply seguro precisa ser bem delimitada para não duplicar resposta.
- Processos por canal/thread podem aumentar custo e consumo de recursos.
- Continuidade pode ficar limitada se a CLI não expuser session ids públicos.
- O mecanismo atual SDK possui tools passivas; CLI pública pode não permitir o mesmo contrato de tool passiva sem canal/MCP adicional.

## Rollback

1. Manter SDK como engine legado disponível.
2. Fazer o modo CLI entrar atrás de flag/env, sem flip irreversível.
3. Se smoke real falhar, desabilitar `EVONEXUS_DISCORD_PLUS_SESSION_ENGINE=cli` e reiniciar somente o serviço Discord Plus.
4. Preservar arquivos de estado CLI em namespace separado para evitar corromper estado SDK.
5. Não alterar tokens, policy store, pairing store ou configuração Discord durante o rollout.

## Decisões pendentes

- Confirmar flags públicas reais do OpenClaude para uso não interativo: input por stdin/arg, saída capturável, `--agent`, `--continue` e session ids.
- Decidir se o default de produção permanece SDK até smoke real PASS ou se CLI entra como default em ambiente de teste.
- Definir formato de persistência de session id por `sessionKey` após confirmar a CLI.
