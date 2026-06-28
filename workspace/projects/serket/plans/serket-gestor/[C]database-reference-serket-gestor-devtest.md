# Referência de Banco de Dados — SERKET Gestor Dev/Test

## Objetivo

Registrar onde ficam os parâmetros de conexão do ambiente de desenvolvimento/testes do SERKET Gestor para consultas diretas ao banco, sem expor senhas ou credenciais em documentação.

## Escopo

Ambiente informado pelo Eduardo:

```text
Servidor: LXC230 homelab
Aplicação: /var/www/apps/serket/demo/_src
Config dev/test: /var/www/apps/serket/demo/_src/app/config
```

Nesta sessão, o caminho remoto `/var/www/apps/serket/demo/_src/app/config` não está montado localmente. A referência abaixo foi mapeada a partir do repositório local equivalente:

```text
/home/evonexus/evo-projects/serket-gestor/_src/app/config
```

Antes de qualquer consulta real no LXC230, confirmar que os arquivos remotos têm o mesmo conteúdo/nomes.

---

## Arquivos PHP de conexão localizados

### 1. Banco principal

```text
/home/evonexus/evo-projects/serket-gestor/_src/app/config/main.php
```

Uso esperado: conexão principal da aplicação.

Parâmetros identificados:

```text
type: mysql
host: localhost
port: 3306
user: definido no arquivo, não documentar senha
name: serket_demo_main
```

### 2. Banco de permissões

```text
/home/evonexus/evo-projects/serket-gestor/_src/app/config/permission.php
```

Uso esperado: autenticação, usuários, grupos, permissões e controle de acesso.

Parâmetros identificados:

```text
type: mysql
host: localhost
port: 3306
user: definido no arquivo, não documentar senha
name: serket_demo_permission
```

### 3. Banco de comunicação

```text
/home/evonexus/evo-projects/serket-gestor/_src/app/config/communication.php
```

Uso esperado: recursos de comunicação/notificações do framework/aplicação.

Parâmetros identificados:

```text
type: mysql
host: localhost
port: 3306
user: definido no arquivo, não documentar senha
name: serket_demo_communication
```

### 4. Banco de logs

```text
/home/evonexus/evo-projects/serket-gestor/_src/app/config/log.php
```

Uso esperado: logs estruturados da aplicação/framework.

Parâmetros identificados:

```text
type: mysql
host: localhost
port: 3306
user: definido no arquivo, não documentar senha
name: serket_demo_log
```

---

## Arquivos auxiliares relacionados

### `application.ini`

```text
/home/evonexus/evo-projects/serket-gestor/_src/app/config/application.ini
```

Contém referências de configuração geral, incluindo banco principal e modo multi-database.

Chaves relevantes identificadas:

```text
main_database
multi_database
```

### `install.ini`

```text
/home/evonexus/evo-projects/serket-gestor/_src/app/config/install.ini
```

Contém lista de bancos usados no processo de instalação/configuração.

Chaves relevantes identificadas:

```text
databases[]
main_database
```

### `serket.ini`

```text
/home/evonexus/evo-projects/serket-gestor/_src/app/config/serket.ini
```

Contém seção de banco de dados específica do SERKET.

Chave relevante identificada:

```text
[database]
main_database
```

---

## Regra de segurança

Não documentar senhas, tokens ou credenciais em arquivos do workspace.

Quando precisar consultar o banco, ler a senha diretamente do arquivo de configuração no ambiente dev/test ou usar um helper temporário que carregue a configuração em runtime, sem imprimir o valor.

---

## Modelo seguro para consulta direta

### Opção A — consultar usando parâmetros lidos manualmente no servidor

No LXC230, dentro do ambiente dev/test, usar os arquivos de configuração apenas como fonte local dos parâmetros.

Exemplo conceitual:

```bash
mysql \
  --host=<host_do_arquivo> \
  --port=<porta_do_arquivo> \
  --user=<usuario_do_arquivo> \
  --password \
  <nome_do_banco>
```

O parâmetro `--password` sem valor evita registrar a senha no histórico do shell.

### Opção B — consulta via script PHP temporário seguro

Se for necessário automatizar uma consulta, preferir um script PHP temporário no próprio servidor que:

1. carregue o arquivo de configuração desejado;
2. abra conexão PDO;
3. execute apenas SQL de leitura quando o objetivo for inspeção;
4. não imprima senha, DSN completo com senha, nem variáveis sensíveis;
5. seja removido após o uso se não fizer parte do projeto.

---

## Bancos conhecidos no ambiente dev/test

```text
serket_demo_main
serket_demo_permission
serket_demo_communication
serket_demo_log
```

---

## Checklist antes de consulta direta

Antes de consultar o banco diretamente:

- Confirmar se a consulta será em dev/test, não produção.
- Confirmar qual banco será consultado.
- Usar somente leitura por padrão.
- Evitar `UPDATE`, `DELETE`, `INSERT`, `TRUNCATE`, `DROP`, `ALTER` sem aprovação explícita.
- Não imprimir credenciais no terminal, logs ou documentação.
- Se a consulta servir para diagnóstico de bug, registrar depois o achado no artefato da feature/ticket correspondente.

---

## Status

- Documentado em 2026-06-28.
- Referência criada para consultas futuras no ambiente dev/test do SERKET Gestor.
