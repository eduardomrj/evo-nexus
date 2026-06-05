# Customizações pós-update — EvoNexus

Este diretório registra ajustes locais que devem ser revisados/reaplicados após atualizar o EvoNexus.

## Por que existe

Algumas melhorias nascem no workspace antes de entrarem no core do EvoNexus. Se editarmos diretamente arquivos nativos em `.claude/skills/`, `.claude/agents/` ou regras do produto, um `git pull` pode sobrescrever ou conflitar essas mudanças.

Este registro vira a fonte local para lembrar:

- o que foi customizado;
- por que existe;
- quais arquivos nativos seriam afetados;
- como reaplicar após atualização;
- como saber se ainda é necessário.

## Como usar depois de atualizar

1. Ler `customizations/post-update/INDEX.md`.
2. Para cada item com status `active`, abrir o arquivo de detalhe.
3. Verificar se a nova versão do EvoNexus já incorporou a mudança.
4. Se não incorporou, reaplicar manualmente seguindo o patch/instruções.
5. Atualizar o status do item:
   - `active` — ainda precisa reaplicar;
   - `upstreamed` — já entrou no EvoNexus oficial;
   - `retired` — não é mais necessário.

## Customizações ativas

| ID | Status | Título | Arquivo |
|---|---|---|---|
| CUST-2026-05-08-001 | upstreamed | Planos em pasta própria por slug | [CUST-2026-05-08-001-plan-folder-per-slug.md](CUST-2026-05-08-001-plan-folder-per-slug.md) |
