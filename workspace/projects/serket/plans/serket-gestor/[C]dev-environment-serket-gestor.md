# Ambiente de Desenvolvimento/Testes — SERKET Gestor

## Definição oficial

O servidor da homelab no **LXC230** é o ambiente de **desenvolvimento/testes** do `serket-gestor`.

Ele **não é produção**. Deve ser usado para validar build, dependências, telas, APIs, integrações e fluxos reais antes de qualquer entrega produtiva.

## Caminhos

### Repositório local de trabalho

```text
/home/evonexus/evo-projects/serket-gestor
```

### App executável no ambiente dev/test

```text
/var/www/apps/serket/demo/_src
```

## Regra operacional

O código é trabalhado no repositório externo local e o ambiente executável de validação fica no LXC230.

Agentes não devem assumir que rodar apenas em:

```text
/home/evonexus/evo-projects/serket-gestor/_src
```

equivale ao ambiente real de teste. A validação relevante deve considerar o destino:

```text
/var/www/apps/serket/demo/_src
```

## Build/deploy de desenvolvimento

O build/deploy para testes deve acontecer no ambiente da homelab, dentro do LXC230, usando o caminho executável acima.

Antes de qualquer cópia, sincronização ou comando com efeito no LXC230, o agente deve mostrar exatamente o que pretende executar e pedir aprovação do Eduardo.

## Proteções obrigatórias

Não sobrescrever sem confirmação explícita:

```text
/var/www/apps/serket/demo/_src/app/config/
```

Essa pasta pode conter credenciais, conexões de banco e ajustes específicos do ambiente dev/test.

Também evitar copiar ou versionar:

- `.env`
- dumps de banco
- logs
- caches
- `_src/vendor/`, quando a estratégia for instalar dependências no próprio servidor
- arquivos gerados em runtime

## Validações esperadas

Após um build/deploy no LXC230, validar conforme o escopo da tarefa:

- sintaxe PHP dos arquivos alterados;
- dependências Composer, se afetadas;
- logs PHP do ambiente dev/test;
- tela ou fluxo web afetado;
- endpoint REST afetado, quando aplicável;
- ausência de exposição de segredos em logs ou output.

## Status

- Registrado em 2026-06-26.
- Ambiente definido por Eduardo como desenvolvimento/testes, não produção.
