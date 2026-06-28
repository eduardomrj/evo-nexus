# Skill: nex-gerar-proposta

Gera uma Proposta Comercial em PDF a partir de uma entrevista com o usuário.
O PDF é salvo em `workspace/legal/propostas/` e pode ser enviado ao cliente.

## Quando usar

Sempre que o usuário pedir para criar ou gerar uma proposta comercial.

Exemplos de trigger:
- "cria uma proposta para o cliente X"
- "gera proposta de licença + TEF para fulano"
- "quero mandar uma proposta para a empresa Y"
- "proposta comercial para o Sr. João"

---

## Template

Existe um único template ativo: **proposta-v1** (creme/industrial).
Arquivo de dados deve ser nomeado `proposta-v1-data.json` → script usa `proposta-v1-template.html.j2`.

Futuras versões seguirão a convenção: `proposta-v2-data.json` → `proposta-v2-template.html.j2`.

---

## Pré-requisito

```bash
pip install jinja2 weasyprint   # já instalado no ambiente
```

---

## Fluxo de execução

### 1. Quem vai apresentar a proposta?

Pergunta obrigatória — determina os dados de consultor.

**Opções:**
- **Automação Software** → consultor = Eduardo Martins (ou outro definido pelo usuário)
- **Parceiro** → listar parceiros ativos de `ADWs/scripts/legal/parceiros.json`; consultor = representante do parceiro

Se parceiro, exibir a lista numerada e aguardar escolha. Dados do consultor preenchidos automaticamente pelo cadastro.

### 2. Coletar dados essenciais (um bloco por vez)

**Bloco A — Cliente**

| Campo | Pergunta |
|---|---|
| `cliente_nome` | "Nome do cliente ou responsável? (Ex: Sr. João, Dra. Ana)" |
| `tipo_negocio` | "Qual o ramo do negócio? (Ex: mercantil, farmácia, supermercado, loja de roupas…)" — usado para personalizar o texto de apresentação |

**Bloco B — Produto (Licença)**

| Campo | Pergunta |
|---|---|
| `qtd_caixas` | "Quantos caixas/PDVs? (Ex: 01 Caixa, 02 Caixas)" |
| `softwares` | "Quais módulos estão incluídos?" — oferecer a lista de módulos comuns abaixo para o usuário escolher |
| `implantacao_valor` | "Valor de implantação? (Ex: R$ 850,00)" |
| `mensalidade_valor` | "Valor da mensalidade? (Ex: R$ 180,00/mês)" |

**Módulos comuns para facilitar a escolha:**
```
1. Emporion PDV (básico)
2. Emporion PDV Fiscal
3. Emporion Manager
4. Emporion NFe
5. Emporion Plus
6. PDV Recovery
7. Hércules Assistência Técnica
```
O usuário pode escolher pelo número, digitar os nomes ou dizer "pacote completo". Não é obrigatório listá-los na proposta — a skill usa esse dado para contextualizar o texto de apresentação.

**Bloco C — TEF**

"A proposta vai incluir TEF SmartPOS?"

Se sim:

| Campo | Pergunta |
|---|---|
| `tef_taxa_adesao` | "Taxa de adesão TEF? (Ex: R$ 150,00 ou R$ 300,00)" |
| `tef_mensalidade` | "Mensalidade TEF? (Ex: R$ 49,70/mês ou R$ 90,00/mês)" |
| `tef_transacao` | "Valor por transação? (Ex: R$ 0,25 ou R$ 0,50 por venda)" |
| `tef_qtd` | "Quantos terminais SmartPOS? (Ex: 01 Terminal)" |

**Bloco D — Consultor** (pular se parceiro — já preenchido)

| Campo | Pergunta |
|---|---|
| `consultor_nome` | "Nome do consultor?" |
| `consultor_cargo` | "Cargo? (Ex: Consultor Comercial, Representante Comercial)" |
| `consultor_whatsapp` | "WhatsApp do consultor? (Ex: (88) 99999-9999)" |

### 3. Exibir resumo e pedir confirmação

Antes de gerar, mostrar um resumo compacto:

```
── Proposta Comercial ─────────────────────────────────────
  Apresentada por : Automação Software  (ou nome do parceiro)
  Cliente         : Sr. João da Silva
  Negócio         : Mercantil
  Produto         : 01 Caixa — R$ 850,00 implantação + R$ 180,00/mês
  Módulos         : PDV Fiscal, Manager, NFe
  TEF             : SmartPOS — R$ 150,00 adesão + R$ 49,70/mês + R$ 0,25/tx
  Consultor       : Eduardo Martins — (88) 99999-9999
  Template        : Escuro (Automação Software)
  Saída           : workspace/legal/propostas/PROPOSTA_JOAO_20260625.pdf
───────────────────────────────────────────────────────────
Confirma? [s/N]
```

Só gerar após confirmação explícita. Se o usuário corrigir algo, atualizar antes de prosseguir.

### 4. Montar o JSON de dados

Salvar em `/tmp/proposta-v1-data.json`.

**Estrutura completa (proposta-v1):**

```json
{
  "cliente_nome": "<nome do cliente>",
  "data": "<data por extenso — ex: 25 de Junho de 2026>",

  "apresentacao_paragrafos": [
    "<parágrafo 1 personalizado com tipo de negócio e empresa apresentadora>",
    "Nossa plataforma integra todas as áreas em um único sistema: vendas, estoque, financeiro e emissão fiscal — totalmente preparada para as exigências da SEFAZ."
  ],

  "funcionalidades": [
    "Frente de Caixa (PDV)",
    "Emissão de NFC-e",
    "Relatórios Gerenciais",
    "Cadastro de Clientes",
    "Controle de Estoque",
    "Backup Automático",
    "Cadastro de Produtos",
    "Integração com Cartão",
    "Controle de Compras",
    "Integração TEF SmartPOS",
    "Contas a Receber e Pagar",
    "Conformidade SEFAZ-CE"
  ],

  "beneficios": [
    { "icone": "clock",        "titulo": "Atendimento mais rápido.",       "cor": "orange" },
    { "icone": "users",        "titulo": "Redução de filas no caixa.",     "cor": "red"    },
    { "icone": "box",          "titulo": "Controle preciso do estoque.",   "cor": "blue"   },
    { "icone": "trending-down","titulo": "Menos perdas e divergências.",   "cor": "green"  },
    { "icone": "shield",       "titulo": "Segurança fiscal garantida.",    "cor": "purple" },
    { "icone": "dollar",       "titulo": "Gestão financeira organizada.",  "cor": "cyan"   },
    { "icone": "chart",        "titulo": "Relatórios para decisão.",       "cor": "yellow" },
    { "icone": "refresh",      "titulo": "Sistema sempre atualizado.",     "cor": "indigo" },
    { "icone": "headphones",   "titulo": "Suporte técnico especializado.", "cor": "pink"   },
    { "icone": "rocket",       "titulo": "Pronto para o crescimento.",     "cor": "orange" }
  ],

  "implantacao_valor": "<valor>",
  "mensalidade_valor": "<valor>/mês",
  "qtd_caixas": "<N> Caixa(s)",

  "mostrar_tef": true,
  "tef_taxa_adesao": "<valor>",
  "tef_mensalidade": "<valor>/mês",
  "tef_transacao": "R$ <valor> por venda",

  "consultor_nome": "<nome>",
  "consultor_cargo": "<cargo>",
  "consultor_whatsapp": "<whatsapp>",

  "validade": "7 dias"
}
```

Se `mostrar_tef` for `false`, omitir os campos `tef_*`.

### 5. Executar o script

```bash
# Garantir que a pasta de saída existe
mkdir -p /home/evonexus/evo-nexus/workspace/legal/propostas

# Gerar o PDF — paleta padrão (creme industrial)
python3 /home/evonexus/evo-nexus/workspace/projects/evo-nexus/features/proposta-comercial/gerar_proposta.py \
  /tmp/proposta-v1-data.json \
  "/home/evonexus/evo-nexus/workspace/legal/propostas/PROPOSTA_<CLIENTE_SLUG>_<YYYYMMDD>.pdf"

# Gerar com paleta alternativa
python3 /home/evonexus/evo-nexus/workspace/projects/evo-nexus/features/proposta-comercial/gerar_proposta.py \
  /tmp/proposta-v1-data.json \
  "/home/evonexus/evo-nexus/workspace/legal/propostas/PROPOSTA_<CLIENTE_SLUG>_<YYYYMMDD>.pdf" \
  --paleta azul
```

**Paletas disponíveis** (em `paletas/*.json`):
| Nome | Estilo |
|---|---|
| `padrao` | Creme industrial — fundo creme, header escuro, acento vermelho (padrão) |
| `azul` | Corporativo — fundo azul-claro, header azul marinho, acento azul |

Para criar uma nova paleta: copiar `paletas/padrao.json`, alterar os 6 campos de cor e salvar com novo nome.

Variáveis da paleta injetadas no template:
- `cor_fundo` — fundo principal da página
- `cor_fundo_sec` — barras, rodapé
- `cor_fundo_card` — fundo de itens/cards
- `cor_escuro` — header, seções escuras
- `cor_acento` — destaque (bordas, números, ícones SVG)
- `cor_borda` — bordas e separadores

**Convenção de nome do PDF:**
- `PROPOSTA_<CLIENTE_SLUG>_<YYYYMMDD>.pdf`
- Exemplo: `PROPOSTA_SR_JOAO_DA_SILVA_20260625.pdf`
- Slug: maiúsculas, espaços → `_`, remover acentos e caracteres especiais

### 6. Reportar resultado

Ao final:
- ✓ Caminho completo do PDF gerado
- ✓ Qual template foi usado
- Oferecer próximos passos: "Quer que eu também gere o contrato de licença e TEF para esse cliente?"

---

## Dados padrão da Automação Software

Usar quando a proposta for apresentada pela Automação Software:

| Campo | Valor |
|---|---|
| `empresa_nome` | `Automação Software` |
| `empresa_nome_curto` | `AUTOMAÇÃO` |
| `empresa_divisao` | `SOFTWARE` |
| `empresa_slogan` | `Tecnologia que simplifica. Resultados que aparecem.` |
| `consultor_cargo` | `Consultor Comercial` |
| `consultor_whatsapp` | perguntar ao usuário |

---

## Arquivos envolvidos

| Arquivo | Função |
|---|---|
| `workspace/projects/evo-nexus/features/proposta-comercial/gerar_proposta.py` | Script gerador (aceita `--paleta`) |
| `workspace/projects/evo-nexus/features/proposta-comercial/proposta-v1-template.html.j2` | Template ativo (layout sem cores fixas) |
| `workspace/projects/evo-nexus/features/proposta-comercial/proposta-v1-data.json` | Referência dos campos / exemplo |
| `workspace/projects/evo-nexus/features/proposta-comercial/paletas/padrao.json` | Paleta padrão (creme industrial) |
| `workspace/projects/evo-nexus/features/proposta-comercial/paletas/azul.json` | Paleta azul corporativo (exemplo) |
| `ADWs/scripts/legal/parceiros.json` | Cadastro de parceiros |
| `workspace/legal/propostas/` | Saída dos PDFs gerados |

---

## Erros comuns

| Erro | Causa | Ação |
|---|---|---|
| `ModuleNotFoundError: weasyprint` | WeasyPrint não instalado | `pip install weasyprint` |
| `Template not found` | Nome do arquivo de dados errado | Verificar convenção do nome (-data.json) |
| `KeyError: icone_codigo` | JSON com `icone` no template escuro (ou vice-versa) | Usar `icone_codigo` para escuro, `icone` para colorido |
| PDF em branco / campos faltando | Campo obrigatório ausente no JSON | Verificar todos os campos da estrutura completa |
