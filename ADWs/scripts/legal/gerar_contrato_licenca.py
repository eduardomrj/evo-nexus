#!/usr/bin/env python3
"""
Gerador de Contrato de Licença de Software — Automação Comercial LTDA
Uso: python3 gerar_contrato_licenca.py --input contrato.json

O script NÃO tem modo interativo. Quem coleta os dados é a skill
legal-gerar-contrato-licenca via conversa com Claude.
"""

import sys
import re
import json
import argparse
from datetime import date, timedelta
from pathlib import Path

import requests
from jinja2 import Environment, FileSystemLoader
import markdown

# ── Caminhos ──────────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).resolve().parents[3]   # evo-nexus/
TEMPLATE   = BASE_DIR / "workspace/legal/contratos/modelos/contrato-licenca-template.md.j2"
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
    content: "AUTOMAÇÃO COMERCIAL LTDA. — LICENÇA DE SOFTWARE";
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
.assinatura-cnpj {{ font-size: 9pt; color: #444; margin: 0 0 52pt 0; }}
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
def proximo_numero_contrato(data: date, prefixo: str = "LIC") -> str:
    """Retorna o próximo número no formato {prefixo}-YYYY-NNNN."""
    ano = data.year
    registro = {"contratos": []}
    if REGISTRO.exists():
        registro = json.loads(REGISTRO.read_text())

    seq = max(
        (int(c["numero"].split("-")[2]) for c in registro["contratos"]
         if c["numero"].startswith(f"{prefixo}-{ano}-")),
        default=0,
    ) + 1

    return f"{prefixo}-{ano}-{seq:04d}"


def registrar_contrato(numero: str, cnpj: str, empresa: str,
                       tipo: str, data: date, output_path: Path,
                       vencimento: int | None = None,
                       softwares: list | None = None,
                       total_mensal: float | None = None,
                       parceiro: dict | None = None) -> None:
    """Salva o contrato gerado no registro JSON."""
    registro = {"contratos": []}
    if REGISTRO.exists():
        registro = json.loads(REGISTRO.read_text())

    entrada: dict = {
        "numero":  numero,
        "cnpj":    cnpj,
        "empresa": empresa,
        "tipo":    tipo,
        "data":    data.isoformat(),
        "arquivo": str(output_path.name),
        "status":  "ativo",
    }
    if vencimento is not None:
        entrada["vencimento_dia"] = vencimento
    if softwares:
        entrada["softwares"] = [s["nome"] for s in softwares]
    if total_mensal is not None:
        entrada["total_mensal"] = round(total_mensal, 2)
    if parceiro:
        entrada["parceiro"] = {
            "empresa":       parceiro["empresa"],
            "representante": parceiro["representante"],
            "cpf":           parceiro["cpf"],
        }

    registro["contratos"].append(entrada)
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


MESES_PT = ["", "janeiro", "fevereiro", "março", "abril", "maio", "junho",
            "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]


def formatar_data_extenso(d: date) -> str:
    return f"{d.day:02d} de {MESES_PT[d.month]} de {d.year}"


def formatar_brl(valor: float) -> str:
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# ── Validações ────────────────────────────────────────────────────────────────
def validar_cpf(cpf: str) -> bool:
    """Valida CPF pelos dígitos verificadores."""
    nums = re.sub(r"\D", "", cpf)
    if len(nums) != 11 or len(set(nums)) == 1:
        return False
    for i in range(2):
        peso = range(10 + i, 1, -1)
        soma = sum(int(d) * p for d, p in zip(nums, peso))
        digito = (soma * 10 % 11) % 10
        if digito != int(nums[9 + i]):
            return False
    return True


def validar_entrada(dados: dict) -> None:
    """Valida todos os campos obrigatórios do JSON de entrada."""
    erros = []

    cnpj_limpo = limpar_cnpj(dados.get("cnpj", ""))
    if len(cnpj_limpo) != 14:
        erros.append("CNPJ deve ter 14 dígitos numéricos")

    vencimento = dados.get("vencimento")
    if vencimento not in (5, 10, 15, 20):
        erros.append(f"vencimento deve ser 5, 10, 15 ou 20 (recebido: {vencimento!r})")

    sig = dados.get("signatario", {})
    if not validar_cpf(sig.get("cpf", "")):
        erros.append(f"CPF do signatário inválido: {sig.get('cpf', '')!r}")

    for campo in ("nome", "cargo", "email", "telefone"):
        if not sig.get(campo, "").strip():
            erros.append(f"signatario.{campo} é obrigatório")

    softwares = dados.get("softwares", [])
    if not softwares:
        erros.append("softwares não pode estar vazio")
    for i, s in enumerate(softwares):
        if not s.get("nome", "").strip():
            erros.append(f"softwares[{i}].nome é obrigatório")
        if not isinstance(s.get("qtd"), (int, float)) or s.get("qtd", 0) <= 0:
            erros.append(f"softwares[{i}].qtd deve ser positivo")
        if not isinstance(s.get("valor_mensal"), (int, float)) or s.get("valor_mensal", 0) < 0:
            erros.append(f"softwares[{i}].valor_mensal deve ser >= 0")

    servicos = dados.get("servicos", [])
    if not servicos:
        erros.append("servicos deve ter ao menos 1 item (Seção 2 nunca renderiza vazia)")
    for i, s in enumerate(servicos):
        if not s.get("nome", "").strip():
            erros.append(f"servicos[{i}].nome é obrigatório")
        if not isinstance(s.get("valor"), (int, float)) or s.get("valor", 0) < 0:
            erros.append(f"servicos[{i}].valor deve ser >= 0")

    # Parceiro (opcional) — se fornecido, valida campos obrigatórios
    parceiro = dados.get("parceiro")
    if parceiro is not None:
        for campo in ("empresa", "representante", "cpf"):
            if not parceiro.get(campo, "").strip():
                erros.append(f"parceiro.{campo} é obrigatório quando parceiro está presente")
        if parceiro.get("cpf") and not validar_cpf(parceiro["cpf"]):
            erros.append(f"CPF do parceiro inválido: {parceiro.get('cpf', '')!r}")

    if erros:
        print("\nErros de validação encontrados:", file=sys.stderr)
        for e in erros:
            print(f"  - {e}", file=sys.stderr)
        sys.exit(1)


# ── Geração ───────────────────────────────────────────────────────────────────
def gerar_contrato(caminho_json: str) -> Path:
    # 1. Ler e validar JSON
    path_json = Path(caminho_json)
    if not path_json.exists():
        print(f"Arquivo não encontrado: {caminho_json}", file=sys.stderr)
        sys.exit(1)

    dados = json.loads(path_json.read_text())
    validar_entrada(dados)

    cnpj_raw    = dados["cnpj"]
    cnpj_limpo  = limpar_cnpj(cnpj_raw)
    vencimento  = dados["vencimento"]
    signatario  = dados["signatario"]
    softwares   = dados["softwares"]
    servicos    = dados["servicos"]
    desc_lic    = float(dados.get("desconto_licenca", 0.0))
    desc_srv    = float(dados.get("desconto_servicos", 0.0))
    data_str    = dados.get("data")
    data        = date.fromisoformat(data_str) if data_str else date.today()
    parceiro    = dados.get("parceiro")   # opcional: {empresa, representante, cpf}

    # 2. Consultar CNPJ (ou usar dados manuais se fornecidos no JSON)
    empresa_nome_override = dados.get("empresa_nome")
    empresa_endereco_override = dados.get("empresa_endereco")

    if empresa_nome_override and empresa_endereco_override:
        print(f"Usando dados manuais para CNPJ {formatar_cnpj(cnpj_limpo)} (sem consulta BrasilAPI)")
        empresa_nome = empresa_nome_override
        endereco     = empresa_endereco_override
    else:
        print(f"Consultando CNPJ {formatar_cnpj(cnpj_limpo)}...", end=" ", flush=True)
        dados_cnpj   = consultar_cnpj(cnpj_limpo)
        print("ok")
        empresa_nome = empresa_nome_override or (dados_cnpj.get("razao_social") or "").title()
        endereco     = empresa_endereco_override or montar_endereco(dados_cnpj)

    # 3. Calcular valores
    subtotal_licenca    = sum(float(s["valor_mensal"]) for s in softwares)
    tem_desconto_lic    = desc_lic > 0
    total_mensal        = subtotal_licenca - desc_lic
    total_anual         = total_mensal * 12

    subtotal_servicos   = sum(float(s["valor"]) for s in servicos)
    tem_desconto_srv    = desc_srv > 0
    total_servicos      = subtotal_servicos - desc_srv
    total_contrato      = total_anual + total_servicos

    data_validade       = data + timedelta(days=15)

    # 4. Enriquecer listas com campos _fmt
    softwares_fmt = [
        {**s, "valor_mensal_fmt": formatar_brl(float(s["valor_mensal"]))}
        for s in softwares
    ]
    servicos_fmt = [
        {**s, "valor_fmt": formatar_brl(float(s["valor"]))}
        for s in servicos
    ]

    # 5. Gerar número do contrato
    numero_contrato = proximo_numero_contrato(data, prefixo="LIC")

    # 6. Resumo para confirmação
    print(f"\n── Contrato {numero_contrato} ───────────────────────────────────────")
    print(f"  Empresa   : {empresa_nome}")
    print(f"  CNPJ      : {formatar_cnpj(cnpj_limpo)}")
    print(f"  Endereço  : {endereco}")
    print(f"  Softwares : {len(softwares)} módulo(s) — R$ {formatar_brl(subtotal_licenca)}/mês")
    if tem_desconto_lic:
        print(f"  Desconto  : R$ {formatar_brl(desc_lic)}/mês")
    print(f"  Total mês : R$ {formatar_brl(total_mensal)}/mês → R$ {formatar_brl(total_anual)}/ano")
    print(f"  Implantação: R$ {formatar_brl(total_servicos)} (única)")
    print(f"  Total anual: R$ {formatar_brl(total_contrato)}")
    print(f"  Vencimento : dia {vencimento} de cada mês")
    print(f"  Signatário : {signatario['nome']} — {signatario['cargo']}")
    if parceiro:
        print(f"  Parceiro   : {parceiro['empresa']} — {parceiro['representante']} (CPF: {parceiro['cpf']})")
    print(f"  Data       : {formatar_data_extenso(data)}")
    print("─" * 52)

    resposta = input("\nConfirma a geração do contrato? [s/N] ").strip().lower()
    if resposta not in ("s", "sim", "y", "yes"):
        print("Geração cancelada.")
        sys.exit(0)

    # 7. Renderizar template Jinja2
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE.parent)),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template(TEMPLATE.name)

    md_content = template.render(
        numero_contrato         = numero_contrato,
        empresa_nome            = empresa_nome,
        cnpj_formatado          = formatar_cnpj(cnpj_limpo),
        endereco                = endereco,
        vencimento              = vencimento,
        data_assinatura         = formatar_data_extenso(data),
        data_validade           = formatar_data_extenso(data_validade),
        signatario              = signatario,
        softwares               = softwares_fmt,
        servicos                = servicos_fmt,
        subtotal_licenca_fmt    = formatar_brl(subtotal_licenca),
        tem_desconto_licenca    = tem_desconto_lic,
        desconto_licenca_fmt    = formatar_brl(desc_lic),
        total_mensal_fmt        = formatar_brl(total_mensal),
        total_anual_fmt         = formatar_brl(total_anual),
        subtotal_servicos_fmt   = formatar_brl(subtotal_servicos),
        tem_desconto_servicos   = tem_desconto_srv,
        desconto_servicos_fmt   = formatar_brl(desc_srv),
        total_servicos_fmt      = formatar_brl(total_servicos),
        total_contrato_fmt      = formatar_brl(total_contrato),
        parceiro                = parceiro,
    )

    # 8. Markdown → HTML → PDF
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
    output_path = OUTPUT_DIR / f"CONTRATO_LIC_{numero_contrato}_{cnpj_limpo}.pdf"

    from weasyprint import HTML
    HTML(string=html_full).write_pdf(str(output_path))

    registrar_contrato(
        numero_contrato, cnpj_limpo, empresa_nome, "licenca", data, output_path,
        vencimento=dados["vencimento"],
        softwares=dados["softwares"],
        total_mensal=total_mensal,
        parceiro=parceiro,
    )

    print(f"\n✓ PDF gerado: {output_path}")
    return output_path


# ── CLI ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gera contrato de licença de software em PDF")
    parser.add_argument(
        "--input", required=True,
        help="Caminho para o arquivo JSON com os dados do contrato",
    )
    args = parser.parse_args()
    gerar_contrato(args.input)
