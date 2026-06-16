#!/usr/bin/env python3
"""
Gerador de Contrato TEF — Automação Comercial LTDA
Uso: python3 gerar_contrato_tef.py <cnpj> <modalidade> [--data YYYY-MM-DD]

modalidade: smartpos | pinpad | ambos
"""

import sys
import re
import json
import argparse
from datetime import date
from dateutil.relativedelta import relativedelta
from pathlib import Path

import requests
from jinja2 import Environment, FileSystemLoader
import markdown

# ── Caminhos ──────────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).resolve().parents[3]   # evo-nexus/
TEMPLATE   = BASE_DIR / "workspace/legal/contratos/modelos/contrato-tef-template.md.j2"
OUTPUT_DIR = BASE_DIR / "workspace/legal/contratos/clientes/gerados"
REGISTRO   = Path(__file__).resolve().parent / "contratos_registro.json"

# ── CSS embutido para o PDF ───────────────────────────────────────────────────
CSS_BASE = """
@page {{
  size: A4;
  margin: 2.5cm 2cm 3cm 2cm;
  @bottom-left {{
    content: "Contrato Nº {numero}";
    font-family: Arial, sans-serif;
    font-size: 8pt;
    color: #888;
  }}
  @bottom-center {{
    content: "AUTOMAÇÃO COMERCIAL LTDA. — TEF";
    font-family: Arial, sans-serif;
    font-size: 8pt;
    color: #aaa;
  }}
  @bottom-right {{
    content: counter(page) " / " counter(pages);
    font-family: Arial, sans-serif;
    font-size: 8pt;
    color: #888;
  }}
}}
body {{ font-family: Arial, sans-serif; font-size: 10pt; color: #111; line-height: 1.5; }}
h1 {{ font-size: 13pt; text-align: center; margin-bottom: 4pt; }}
h2 {{ font-size: 11pt; border-bottom: 1px solid #999; padding-bottom: 3pt; margin-top: 18pt; }}
h2.nova-pagina {{ page-break-before: always; padding-top: 8pt; margin-top: 0; }}
h3 {{ font-size: 10pt; margin-top: 12pt; }}
table {{ width: 100%; border-collapse: collapse; margin: 10pt 0; font-size: 9pt; }}
th {{ background: #333; color: #fff; padding: 5pt 7pt; text-align: left; }}
td {{ border: 1px solid #ccc; padding: 4pt 7pt; }}
tr:nth-child(even) td {{ background: #f7f7f7; }}
blockquote {{ border-left: 3px solid #999; margin: 8pt 0; padding: 4pt 10pt; color: #555; font-size: 9pt; }}
pre {{ background: #f4f4f4; padding: 8pt; font-size: 8pt; border: 1px solid #ddd; }}
code {{ background: #f4f4f4; padding: 1pt 3pt; font-size: 8.5pt; }}
strong {{ color: #000; }}
.assinaturas {{ margin-top: 30pt; }}
.assinaturas-partes {{ display: table; width: 100%; margin-bottom: 30pt; }}
.assinatura-bloco {{ display: table-cell; width: 48%; vertical-align: top; padding-right: 4%; }}
.assinatura-bloco:last-child {{ padding-right: 0; }}
.assinatura-empresa {{ font-weight: bold; font-size: 10pt; margin: 0 0 2pt 0; }}
.assinatura-cnpj {{ font-size: 9pt; color: #444; margin: 0 0 32pt 0; }}
.assinatura-linha {{ border-bottom: 1px solid #333; margin-bottom: 6pt; height: 20pt; }}
.assinatura-cargo {{ font-size: 9pt; margin: 0 0 2pt 0; }}
.assinatura-cpf {{ font-size: 9pt; color: #444; margin: 0; }}
.testemunhas-titulo {{ font-weight: bold; font-size: 10pt; margin: 10pt 0 14pt 0; border-top: 1px solid #ccc; padding-top: 14pt; }}
.testemunha-bloco {{ margin-bottom: 22pt; }}
.testemunha-nome-cpf {{ font-size: 9.5pt; margin-bottom: 14pt; }}
.testemunha-nome-cpf span {{ display: inline-block; border-bottom: 1px solid #555; }}
.testemunha-nome-cpf .t-nome {{ width: 58%; }}
.testemunha-nome-cpf .t-cpf  {{ width: 30%; margin-left: 2%; }}
.testemunha-assinatura {{ font-size: 9pt; }}
.testemunha-assinatura span {{ display: inline-block; border-bottom: 1px solid #555; width: 72%; }}
"""


# ── Numeração de contratos ────────────────────────────────────────────────────
def proximo_numero_contrato(data: date) -> str:
    """Retorna o próximo número no formato TEF-YYYY-NNNN e registra no JSON."""
    ano = data.year
    registro = {"contratos": []}
    if REGISTRO.exists():
        registro = json.loads(REGISTRO.read_text())

    # Filtra contratos do ano atual e pega o maior sequencial
    seq = max(
        (int(c["numero"].split("-")[2]) for c in registro["contratos"]
         if c["numero"].startswith(f"TEF-{ano}-")),
        default=0,
    ) + 1

    numero = f"TEF-{ano}-{seq:04d}"
    return numero


def registrar_contrato(numero: str, cnpj: str, empresa: str,
                       modalidade: str, data: date, output_path: Path) -> None:
    """Salva o contrato gerado no registro JSON."""
    registro = {"contratos": []}
    if REGISTRO.exists():
        registro = json.loads(REGISTRO.read_text())

    registro["contratos"].append({
        "numero":     numero,
        "cnpj":       cnpj,
        "empresa":    empresa,
        "modalidade": modalidade,
        "data":       data.isoformat(),
        "arquivo":    str(output_path.name),
        "status":     "ativo",
    })
    REGISTRO.write_text(json.dumps(registro, ensure_ascii=False, indent=2))


# ── Helpers ───────────────────────────────────────────────────────────────────
def limpar_cnpj(cnpj: str) -> str:
    return re.sub(r"\D", "", cnpj)


def formatar_cnpj(cnpj: str) -> str:
    c = limpar_cnpj(cnpj)
    return f"{c[:2]}.{c[2:5]}.{c[5:8]}/{c[8:12]}-{c[12:]}"


def consultar_cnpj(cnpj: str) -> dict:
    """Consulta BrasilAPI e retorna dados da empresa."""
    cnpj_limpo = limpar_cnpj(cnpj)
    if len(cnpj_limpo) != 14:
        raise ValueError(f"CNPJ inválido: {cnpj}")

    url = f"https://brasilapi.com.br/api/cnpj/v1/{cnpj_limpo}"
    resp = requests.get(url, timeout=10)

    if resp.status_code == 404:
        raise ValueError(f"CNPJ não encontrado na Receita Federal: {formatar_cnpj(cnpj_limpo)}")
    if resp.status_code != 200:
        raise RuntimeError(f"Erro na consulta CNPJ (HTTP {resp.status_code}): {resp.text[:200]}")

    return resp.json()


def montar_endereco(dados: dict) -> str:
    partes = [
        dados.get("logradouro", "").title(),
        dados.get("numero", ""),
        dados.get("complemento", "").title() if dados.get("complemento") else None,
        dados.get("bairro", "").title(),
        f"CEP {dados.get('cep', '')}",
        f"{dados.get('municipio', '').title()}/{dados.get('uf', '')}",
    ]
    return ", ".join(p for p in partes if p)


def valor_extenso(v: float) -> str:
    """Converte valor de transação (centavos) para extenso em pt-BR."""
    centavos = round(v * 100)
    mapa = {
        1: "um centavo", 2: "dois centavos", 3: "três centavos",
        4: "quatro centavos", 5: "cinco centavos", 6: "seis centavos",
        7: "sete centavos", 8: "oito centavos", 9: "nove centavos",
        10: "dez centavos", 11: "onze centavos", 12: "doze centavos",
        13: "treze centavos", 14: "quatorze centavos", 15: "quinze centavos",
        16: "dezesseis centavos", 17: "dezessete centavos", 18: "dezoito centavos",
        19: "dezenove centavos", 20: "vinte centavos", 25: "vinte e cinco centavos",
        30: "trinta centavos", 35: "trinta e cinco centavos",
        40: "quarenta centavos", 45: "quarenta e cinco centavos",
        50: "cinquenta centavos", 55: "cinquenta e cinco centavos",
        60: "sessenta centavos", 70: "setenta centavos",
        75: "setenta e cinco centavos", 80: "oitenta centavos",
        90: "noventa centavos", 99: "noventa e nove centavos",
    }
    if centavos in mapa:
        return mapa[centavos]
    if centavos < 100:
        return f"{centavos} centavos"
    reais = centavos // 100
    cents = centavos % 100
    base = f"{reais} {'real' if reais == 1 else 'reais'}"
    return base if cents == 0 else f"{base} e {cents} centavos"


MESES_PT = ["", "janeiro", "fevereiro", "março", "abril", "maio", "junho",
            "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]

MESES_PT_ABREV = ["", "jan", "fev", "mar", "abr", "mai", "jun",
                  "jul", "ago", "set", "out", "nov", "dez"]


def formatar_data_extenso(d: date) -> str:
    return f"{d.day:02d} de {MESES_PT[d.month]} de {d.year}"


def formatar_brl(valor: float) -> str:
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def gerar_cronograma(
    data_ativacao: date,
    mensalidade_mensal: float,
    taxa_transacao: float,
    volume_mensal: int,
    meses: int = 12,
) -> list[dict]:
    """Gera cronograma de vencimentos. Competência = mês M, vencimento = dia 5 de M+1."""
    cronograma = []
    # Primeira competência: mês da ativação
    competencia = data_ativacao.replace(day=1)
    for _ in range(meses):
        vencimento = (competencia + relativedelta(months=1)).replace(day=5)
        transacoes = taxa_transacao * volume_mensal
        total = mensalidade_mensal + transacoes
        nome_mes = f"{MESES_PT_ABREV[competencia.month].capitalize()}/{competencia.year}"
        cronograma.append({
            "competencia": nome_mes,
            "vencimento":  f"05/{vencimento.month:02d}/{vencimento.year}",
            "mensalidade": formatar_brl(mensalidade_mensal),
            "transacoes":  formatar_brl(transacoes),
            "total":       formatar_brl(total),
        })
        competencia += relativedelta(months=1)
    return cronograma


# ── Geração ───────────────────────────────────────────────────────────────────
PRECO_PADRAO = {
    "smartpos": {"adesao": 150.00, "mensalidade": 49.90, "transacao": 0.25},
    "pinpad":   {"adesao": 360.00, "mensalidade": 140.00, "transacao": 0.14},
}


def gerar_contrato(
    cnpj: str,
    modalidade: str,
    qtd_smartpos: int = 1,
    qtd_pinpad: int = 1,
    volume_smartpos: int = 0,
    volume_pinpad: int = 0,
    data: date | None = None,
    # Preços customizáveis — None = usa o padrão
    adesao_smartpos: float | None = None,
    mensalidade_smartpos: float | None = None,
    transacao_smartpos: float | None = None,
    adesao_pinpad: float | None = None,
    mensalidade_pinpad: float | None = None,
    transacao_pinpad: float | None = None,
) -> Path:
    if modalidade not in ("smartpos", "pinpad", "ambos"):
        raise ValueError("modalidade deve ser: smartpos | pinpad | ambos")

    data = data or date.today()

    # 1. Consultar CNPJ
    print(f"Consultando CNPJ {formatar_cnpj(cnpj)}...", end=" ", flush=True)
    dados = consultar_cnpj(cnpj)
    print("ok")

    empresa_nome = (dados.get("razao_social") or "").title()
    endereco     = montar_endereco(dados)

    # 2. Resolver preços (custom ou padrão)
    p_adesao_sp   = adesao_smartpos      if adesao_smartpos      is not None else PRECO_PADRAO["smartpos"]["adesao"]
    p_mensal_sp   = mensalidade_smartpos if mensalidade_smartpos is not None else PRECO_PADRAO["smartpos"]["mensalidade"]
    p_trans_sp    = transacao_smartpos   if transacao_smartpos   is not None else PRECO_PADRAO["smartpos"]["transacao"]
    p_adesao_pp   = adesao_pinpad        if adesao_pinpad        is not None else PRECO_PADRAO["pinpad"]["adesao"]
    p_mensal_pp   = mensalidade_pinpad   if mensalidade_pinpad   is not None else PRECO_PADRAO["pinpad"]["mensalidade"]
    p_trans_pp    = transacao_pinpad     if transacao_pinpad     is not None else PRECO_PADRAO["pinpad"]["transacao"]

    # Calcular mensalidades totais
    val_mensal_smartpos = qtd_smartpos * p_mensal_sp
    val_mensal_pinpad   = qtd_pinpad   * p_mensal_pp
    str_mensalidade_smartpos = formatar_brl(val_mensal_smartpos)
    str_mensalidade_pinpad   = formatar_brl(val_mensal_pinpad)

    # Cronograma consolidado
    if modalidade == "smartpos":
        mensalidade_total = val_mensal_smartpos
        taxa_transacao    = p_trans_sp
        volume_total      = volume_smartpos
    elif modalidade == "pinpad":
        mensalidade_total = val_mensal_pinpad
        taxa_transacao    = p_trans_pp
        volume_total      = volume_pinpad
    else:  # ambos
        mensalidade_total = val_mensal_smartpos + val_mensal_pinpad
        volume_total      = volume_smartpos + volume_pinpad
        taxa_transacao    = (
            (p_trans_sp * volume_smartpos + p_trans_pp * volume_pinpad) / volume_total
            if volume_total > 0 else p_trans_sp
        )

    cronograma = gerar_cronograma(data, mensalidade_total, taxa_transacao, volume_total)

    # Variáveis do DEE
    val_trans_smartpos    = round(volume_smartpos * p_trans_sp, 2)
    val_trans_pinpad      = round(volume_pinpad   * p_trans_pp, 2)
    val_adesao_smartpos   = p_adesao_sp if modalidade in ("smartpos", "ambos") else 0
    val_adesao_pinpad     = p_adesao_pp if modalidade in ("pinpad",   "ambos") else 0
    val_adesao_total      = val_adesao_smartpos + val_adesao_pinpad
    val_mensal_recorrente = mensalidade_total + (val_trans_smartpos if modalidade in ("smartpos", "ambos") else 0) + (val_trans_pinpad if modalidade in ("pinpad", "ambos") else 0)

    # Exemplo para cláusula de vencimento (mês seguinte ao da ativação)
    mes_exemplo     = data.replace(day=1)
    venc_exemplo    = (mes_exemplo + relativedelta(months=1)).replace(day=5)
    ex_competencia  = f"{MESES_PT_ABREV[mes_exemplo.month].capitalize()}/{mes_exemplo.year}"
    ex_vencimento   = f"05/{venc_exemplo.month:02d}/{venc_exemplo.year}"

    # 3. Gerar número do contrato
    numero_contrato = proximo_numero_contrato(data)

    # 4. Exibir resumo para confirmação
    modal_label = {"smartpos": "TEF SmartPOS", "pinpad": "TEF Pinpad", "ambos": "SmartPOS + Pinpad"}
    print("\n── Dados encontrados ───────────────────────────────")
    print(f"  Nº Contrato: {numero_contrato}")
    print(f"  Empresa   : {empresa_nome}")
    print(f"  CNPJ      : {formatar_cnpj(cnpj)}")
    print(f"  Endereço  : {endereco}")
    print(f"  Modalidade: {modal_label[modalidade]}")
    if modalidade in ("smartpos", "ambos"):
        print(f"  SmartPOS  : {qtd_smartpos} equip. — R$ {str_mensalidade_smartpos}/mês + R$ {formatar_brl(p_trans_sp)}/transação | ~{volume_smartpos} transações/mês")
        if p_adesao_sp != PRECO_PADRAO["smartpos"]["adesao"] or p_mensal_sp != PRECO_PADRAO["smartpos"]["mensalidade"] or p_trans_sp != PRECO_PADRAO["smartpos"]["transacao"]:
            print(f"  ⚠ SmartPOS preço customizado (adesão R$ {formatar_brl(p_adesao_sp)}, mensal R$ {formatar_brl(p_mensal_sp)}, transação R$ {formatar_brl(p_trans_sp)})")
    if modalidade in ("pinpad", "ambos"):
        print(f"  Pinpad    : {qtd_pinpad} equip. — R$ {str_mensalidade_pinpad}/mês + R$ {formatar_brl(p_trans_pp)}/transação | ~{volume_pinpad} transações/mês")
        if p_adesao_pp != PRECO_PADRAO["pinpad"]["adesao"] or p_mensal_pp != PRECO_PADRAO["pinpad"]["mensalidade"] or p_trans_pp != PRECO_PADRAO["pinpad"]["transacao"]:
            print(f"  ⚠ Pinpad preço customizado (adesão R$ {formatar_brl(p_adesao_pp)}, mensal R$ {formatar_brl(p_mensal_pp)}, transação R$ {formatar_brl(p_trans_pp)})")
    print(f"  Data      : {formatar_data_extenso(data)}")
    print("────────────────────────────────────────────────────\n")

    resposta = input("Confirma a geração do contrato? [s/N] ").strip().lower()
    if resposta not in ("s", "sim", "y", "yes"):
        print("Geração cancelada.")
        sys.exit(0)

    # 4. Renderizar template Jinja2
    env = Environment(loader=FileSystemLoader(str(TEMPLATE.parent)), trim_blocks=True, lstrip_blocks=True)
    template = env.get_template(TEMPLATE.name)

    md_content = template.render(
        empresa_nome             = empresa_nome,
        cnpj_formatado           = formatar_cnpj(cnpj),
        endereco                 = endereco,
        modalidade               = modalidade,
        qtd_smartpos             = qtd_smartpos,
        qtd_pinpad               = qtd_pinpad,
        mensalidade_smartpos     = str_mensalidade_smartpos,
        mensalidade_pinpad       = str_mensalidade_pinpad,
        volume_smartpos          = volume_smartpos,
        volume_pinpad            = volume_pinpad,
        preco_mensal_smartpos    = formatar_brl(p_mensal_sp),
        preco_mensal_pinpad      = formatar_brl(p_mensal_pp),
        preco_trans_smartpos     = formatar_brl(p_trans_sp),
        preco_trans_pinpad       = formatar_brl(p_trans_pp),
        valor_transacao          = formatar_brl(p_trans_sp if modalidade != "pinpad" else p_trans_pp),
        valor_transacao_extenso  = valor_extenso(p_trans_sp if modalidade != "pinpad" else p_trans_pp),
        data_assinatura          = formatar_data_extenso(data),
        cronograma                = cronograma,
        exemplo_competencia       = ex_competencia,
        exemplo_vencimento        = ex_vencimento,
        val_trans_smartpos        = formatar_brl(val_trans_smartpos),
        val_trans_pinpad          = formatar_brl(val_trans_pinpad),
        val_adesao_smartpos       = formatar_brl(val_adesao_smartpos),
        val_adesao_pinpad         = formatar_brl(val_adesao_pinpad),
        val_adesao_total          = formatar_brl(val_adesao_total),
        val_mensal_recorrente     = formatar_brl(val_mensal_recorrente),
        numero_contrato           = numero_contrato,
    )

    # 4. Markdown → HTML → PDF
    html_body = markdown.markdown(
        md_content,
        extensions=["tables", "nl2br", "sane_lists"],
    )
    # Anexos sempre iniciam em página nova
    html_body = html_body.replace('<h2>Anexo', '<h2 class="nova-pagina">Anexo')

    css = CSS_BASE.format(numero=numero_contrato)

    html_full = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <style>{css}</style>
</head>
<body>{html_body}</body>
</html>"""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    cnpj_limpo  = limpar_cnpj(cnpj)
    output_path = OUTPUT_DIR / f"CONTRATO_TEF_{numero_contrato}_{cnpj_limpo}.pdf"

    from weasyprint import HTML
    HTML(string=html_full).write_pdf(str(output_path))

    registrar_contrato(numero_contrato, cnpj_limpo, empresa_nome, modalidade, data, output_path)

    print(f"\n✓ PDF gerado: {output_path}")
    return output_path


# ── CLI ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gera contrato TEF em PDF")
    parser.add_argument("cnpj",          help="CNPJ do cliente (com ou sem formatação)")
    parser.add_argument("modalidade",    choices=["smartpos", "pinpad", "ambos"],
                        help="Modalidade contratada")
    parser.add_argument("--smartpos",        type=int, default=1,
                        help="Quantidade de equipamentos SmartPOS (padrão: 1)")
    parser.add_argument("--pinpad",          type=int, default=1,
                        help="Quantidade de equipamentos Pinpad (padrão: 1)")
    parser.add_argument("--vol-smartpos",      type=int,   default=500,
                        help="Volume estimado de transações SmartPOS/mês (padrão: 500)")
    parser.add_argument("--vol-pinpad",        type=int,   default=500,
                        help="Volume estimado de transações Pinpad/mês (padrão: 500)")
    parser.add_argument("--data",              help="Data da assinatura (YYYY-MM-DD), padrão: hoje")
    # Preços customizáveis (opcionais — omitir usa o padrão)
    parser.add_argument("--adesao-smartpos",   type=float, help="Taxa de adesão SmartPOS (padrão: 150,00)")
    parser.add_argument("--mensal-smartpos",   type=float, help="Mensalidade SmartPOS por equip. (padrão: 49,90)")
    parser.add_argument("--trans-smartpos",    type=float, help="Preço por transação SmartPOS (padrão: 0,25)")
    parser.add_argument("--adesao-pinpad",     type=float, help="Taxa de adesão Pinpad (padrão: 360,00)")
    parser.add_argument("--mensal-pinpad",     type=float, help="Mensalidade Pinpad por equip. (padrão: 140,00)")
    parser.add_argument("--trans-pinpad",      type=float, help="Preço por transação Pinpad (padrão: 0,14)")
    args = parser.parse_args()

    data_assinatura = date.fromisoformat(args.data) if args.data else None
    gerar_contrato(
        args.cnpj, args.modalidade,
        args.smartpos, args.pinpad,
        args.vol_smartpos, args.vol_pinpad,
        data_assinatura,
        adesao_smartpos      = args.adesao_smartpos,
        mensalidade_smartpos = args.mensal_smartpos,
        transacao_smartpos   = args.trans_smartpos,
        adesao_pinpad        = args.adesao_pinpad,
        mensalidade_pinpad   = args.mensal_pinpad,
        transacao_pinpad     = args.trans_pinpad,
    )
