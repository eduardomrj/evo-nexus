#!/usr/bin/env python3
"""
Panorama cruzado de contratos de uma empresa: local × Documenso × Asaas.

Filtra contratos_registro.json pelo CNPJ ou nome da empresa informados,
consulta Documenso e Asaas para cada contrato encontrado e retorna JSON
estruturado com o status de cada dimensão.

Uso:
  python3 panorama_contratos.py --cnpj "04.056.245/0001-91"
  python3 panorama_contratos.py --cnpj "04056245000191"
  python3 panorama_contratos.py --nome "Elitanio"
  python3 panorama_contratos.py --cnpj "04056245000191" --output /tmp/panorama.json

Exatamente um de --cnpj ou --nome é obrigatório.
Saída stdout: JSON com lista de registros cruzados.

Requer no .env:
  ASAAS_API_KEY=<token>
  DOCUMENSO_API_URL=https://signature.automacaosoftware.com.br
  DOCUMENSO_API_KEY=<token>
"""

import json
import os
import sys
import argparse
from pathlib import Path
from datetime import datetime

import requests
from dotenv import load_dotenv

# ── Config ────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parents[3]   # evo-nexus/
load_dotenv(BASE_DIR / ".env")

ASAAS_API_KEY    = os.getenv("ASAAS_API_KEY", "")
ASAAS_BASE_URL   = "https://api.asaas.com/v3"

DOCUMENSO_API_URL = os.getenv("DOCUMENSO_API_URL", "https://signature.automacaosoftware.com.br")
DOCUMENSO_API_KEY = os.getenv("DOCUMENSO_API_KEY", "")

REGISTRO_PATH   = Path(__file__).parent / "contratos_registro.json"
PARCEIROS_PATH  = Path(__file__).parent / "parceiros.json"
GERADOS_PATH    = BASE_DIR / "workspace/legal/contratos/clientes/gerados"
ENVIOS_PATH     = GERADOS_PATH / "envios_assinatura.json"


# ── Helpers Asaas ─────────────────────────────────────────────────────────────
def asaas_headers() -> dict:
    return {"access_token": ASAAS_API_KEY, "Content-Type": "application/json"}


def consultar_assinatura_asaas(subscription_id: str) -> dict | None:
    """Consulta uma assinatura pelo ID. Retorna dict com os dados ou None em caso de erro."""
    if not subscription_id or not ASAAS_API_KEY:
        return None
    try:
        r = requests.get(
            f"{ASAAS_BASE_URL}/subscriptions/{subscription_id}",
            headers=asaas_headers(),
            timeout=10,
        )
        if r.status_code == 200:
            return r.json()
        return None
    except Exception:
        return None


# ── Helpers Documenso ─────────────────────────────────────────────────────────
def documenso_headers(api_key: str | None = None) -> dict:
    key = api_key or DOCUMENSO_API_KEY
    return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}


def buscar_documento_por_id(doc_id: int, api_key: str | None = None) -> dict | None:
    """Busca documento no Documenso pelo ID direto. Retorna dict ou None (inclui 404)."""
    key = api_key or DOCUMENSO_API_KEY
    if not key or not DOCUMENSO_API_URL or not doc_id:
        return None
    try:
        r = requests.get(
            f"{DOCUMENSO_API_URL}/api/v1/documents/{doc_id}",
            headers=documenso_headers(key),
            timeout=15,
        )
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None


def buscar_documento_por_titulo(numero_contrato: str, api_key: str | None = None) -> dict | None:
    """Busca documento no Documenso pelo número do contrato no título (fallback).

    O Documenso não tem search por número exato — usamos o campo
    'search' da listagem e filtramos localmente pelo número no título.
    """
    key = api_key or DOCUMENSO_API_KEY
    if not key or not DOCUMENSO_API_URL:
        return None
    try:
        r = requests.get(
            f"{DOCUMENSO_API_URL}/api/v1/documents",
            params={"search": numero_contrato, "perPage": 10},
            headers=documenso_headers(key),
            timeout=15,
        )
        if r.status_code != 200:
            return None
        for doc in r.json().get("documents", []):
            if numero_contrato in doc.get("title", ""):
                return doc
        return None
    except Exception:
        return None


def _carregar_mapa_parceiros() -> dict[str, str]:
    """Retorna mapa email_parceiro -> api_key_env_var lido de parceiros.json."""
    if not PARCEIROS_PATH.exists():
        return {}
    with open(PARCEIROS_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return {
        p["email"]: p["documenso_api_key_env"]
        for p in data.get("parceiros", [])
        if p.get("email") and p.get("documenso_api_key_env") and p.get("ativo", True)
    }


# Carregado uma vez na inicialização
_PARCEIROS_MAP: dict[str, str] = _carregar_mapa_parceiros()


def _api_key_parceiro(envio: dict) -> str | None:
    """Dado um registro de envio com campo 'parceiro', retorna a API key do parceiro
    lida do .env, ou None se não encontrada."""
    parceiro = envio.get("parceiro", {})
    email = parceiro.get("email", "")
    env_var = _PARCEIROS_MAP.get(email)
    if not env_var:
        return None
    return os.getenv(env_var)


# ── Helpers locais ────────────────────────────────────────────────────────────
def carregar_registro() -> list[dict]:
    with open(REGISTRO_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("contratos", [])


def carregar_envios() -> dict[str, dict]:
    """Retorna mapa arquivo_pdf -> registro de envio (último por arquivo, preferindo o mais recente)."""
    if not ENVIOS_PATH.exists():
        return {}
    with open(ENVIOS_PATH, encoding="utf-8") as f:
        data = json.load(f)
    # Pode haver duplicatas (reenvios) — usar o último para cada PDF
    mapa: dict[str, dict] = {}
    for envio in data.get("envios", []):
        pdf = envio.get("pdf", "")
        mapa[pdf] = envio   # sobrescreve com o mais recente
    return mapa


def arquivo_existe(nome_arquivo: str) -> bool:
    return (GERADOS_PATH / nome_arquivo).exists()


# ── Lógica de valor contrato ──────────────────────────────────────────────────
def valor_contrato_local(contrato: dict) -> float | None:
    """Extrai o valor mensal esperado do contrato local.

    Para LIC: campo total_mensal.
    Para TEF/smartpos: campo smartpos.mensalidade.
    """
    tipo = contrato.get("tipo")
    if tipo == "licenca":
        return contrato.get("total_mensal")
    if tipo == "tef":
        smartpos = contrato.get("smartpos", {})
        return smartpos.get("mensalidade")
    return None


# ── Match de valor ────────────────────────────────────────────────────────────
TOLERANCIA = 0.01   # R$ — diferença mínima para considerar divergência


def avaliar_match_valor(valor_local: float | None, valor_asaas: float | None) -> str:
    if valor_local is None and valor_asaas is None:
        return "sem_dados"
    if valor_asaas is None:
        return "sem_assinatura"
    if valor_local is None:
        return "sem_valor_local"
    if abs(valor_local - valor_asaas) <= TOLERANCIA:
        return "OK"
    return "DIVERGENTE"


# ── Status legível Documenso ──────────────────────────────────────────────────
STATUS_DOCUMENSO_MAP = {
    "DRAFT":     "RASCUNHO",
    "PENDING":   "PENDENTE",
    "COMPLETED": "ASSINADO",
}


def traduzir_status_documenso(status: str | None) -> str:
    if status is None:
        return "nao_encontrado"
    return STATUS_DOCUMENSO_MAP.get(status.upper(), status)


# ── Processamento principal ───────────────────────────────────────────────────
def processar_contrato(contrato: dict, envios_map: dict[str, dict]) -> dict:
    numero   = contrato["numero"]
    arquivo  = contrato.get("arquivo", "")
    empresa  = contrato.get("empresa", "")
    cnpj     = contrato.get("cnpj", "")
    tipo     = contrato.get("tipo", "")

    # 1. Status local
    pdf_existe = arquivo_existe(arquivo)
    envio      = envios_map.get(arquivo)

    # 2. Status Documenso
    # Estratégia: ID direto (conta principal) → ID direto (conta parceiro)
    #             → busca por título (conta principal) → busca por título (conta parceiro)
    doc_id       = envio.get("doc_id") if envio else None
    parceiro_key = _api_key_parceiro(envio) if (envio and envio.get("parceiro")) else None

    doc_api = None
    doc_removido = False  # True quando o doc_id consta no envio mas retorna 404

    if doc_id:
        doc_api = buscar_documento_por_id(doc_id)
        if doc_api is None and parceiro_key:
            doc_api = buscar_documento_por_id(doc_id, api_key=parceiro_key)
        if doc_api is None and envio:
            # doc_id registrado mas não encontrado em nenhuma conta → foi deletado
            doc_removido = True

    if doc_api is None and not doc_removido:
        doc_api = buscar_documento_por_titulo(numero)
        if doc_api is None and parceiro_key:
            doc_api = buscar_documento_por_titulo(numero, api_key=parceiro_key)

    if doc_api is not None:
        doc_status_raw = doc_api.get("status")
        doc_titulo     = doc_api.get("title", "")
        doc_link       = f"{DOCUMENSO_API_URL}/documents/{doc_api.get('id', '')}"
    elif envio:
        doc_status_raw = None
        doc_titulo     = envio.get("titulo", "")
        doc_link       = envio.get("link", "")
    else:
        doc_status_raw = None
        doc_titulo     = ""
        doc_link       = ""

    if doc_removido:
        doc_status = "documento_removido"
    else:
        doc_status = traduzir_status_documenso(doc_status_raw)
        if doc_status == "nao_encontrado" and envio:
            doc_status = "enviado_sem_status"

    # 3. Status Asaas
    subscription_id = contrato.get("asaas_subscription_id")
    valor_local     = valor_contrato_local(contrato)
    sub_data        = consultar_assinatura_asaas(subscription_id) if subscription_id else None

    if sub_data:
        asaas_status = sub_data.get("status", "DESCONHECIDO")
        asaas_valor  = sub_data.get("value")
        asaas_ciclo  = sub_data.get("cycle")
        asaas_next   = sub_data.get("nextDueDate")
    else:
        asaas_status = "sem_assinatura" if not subscription_id else "erro_consulta"
        asaas_valor  = None
        asaas_ciclo  = None
        asaas_next   = None

    match_valor = avaliar_match_valor(valor_local, asaas_valor)

    return {
        "numero":          numero,
        "empresa":         empresa,
        "cnpj":            cnpj,
        "tipo":            tipo,
        "data_contrato":   contrato.get("data"),
        # Local
        "arquivo":         arquivo,
        "pdf_existe":      pdf_existe,
        # Documenso
        "documenso_status":    doc_status,
        "documenso_doc_id":    doc_id,
        "documenso_titulo":    doc_titulo,
        "documenso_link":      doc_link,
        "documenso_enviado_em": envio.get("enviado_em") if envio else None,
        # Asaas
        "asaas_subscription_id": subscription_id,
        "asaas_status":          asaas_status,
        "asaas_valor":           asaas_valor,
        "asaas_ciclo":           asaas_ciclo,
        "asaas_proxima_cobranca": asaas_next,
        # Cruzamento
        "valor_contrato_local": valor_local,
        "match_valor":          match_valor,
    }


def gerar_resumo(resultados: list[dict]) -> dict:
    total = len(resultados)
    pdf_ok        = sum(1 for r in resultados if r["pdf_existe"])
    assinados     = sum(1 for r in resultados if r["documenso_status"] == "ASSINADO")
    pendentes     = sum(1 for r in resultados if r["documenso_status"] in ("PENDENTE", "enviado_sem_status"))
    nao_enviados  = sum(1 for r in resultados if r["documenso_status"] == "nao_encontrado")
    match_ok      = sum(1 for r in resultados if r["match_valor"] == "OK")
    divergentes   = sum(1 for r in resultados if r["match_valor"] == "DIVERGENTE")
    sem_assinatura= sum(1 for r in resultados if r["match_valor"] in ("sem_assinatura", "erro_consulta"))

    return {
        "total_contratos":     total,
        "pdf_local_ok":        pdf_ok,
        "pdf_local_ausente":   total - pdf_ok,
        "documenso_assinados": assinados,
        "documenso_pendentes": pendentes,
        "documenso_nao_enviados": nao_enviados,
        "asaas_match_ok":      match_ok,
        "asaas_divergentes":   divergentes,
        "asaas_sem_assinatura":sem_assinatura,
    }


# ── Filtro por empresa ────────────────────────────────────────────────────────
def limpar_cnpj(cnpj: str) -> str:
    """Remove formatação de CNPJ: pontos, barras, hífens."""
    return "".join(c for c in cnpj if c.isdigit())


def filtrar_contratos(contratos: list[dict], cnpj: str | None, nome: str | None) -> list[dict]:
    """Filtra a lista de contratos pelo CNPJ exato ou busca parcial case-insensitive no nome."""
    if cnpj:
        cnpj_limpo = limpar_cnpj(cnpj)
        return [c for c in contratos if limpar_cnpj(c.get("cnpj", "")) == cnpj_limpo]
    if nome:
        nome_lower = nome.lower()
        return [c for c in contratos if nome_lower in c.get("empresa", "").lower()]
    return []


def resolver_empresa(contratos_filtrados: list[dict]) -> tuple[str, str]:
    """Extrai empresa e CNPJ representativos da lista filtrada (primeiro registro)."""
    if not contratos_filtrados:
        return "", ""
    primeiro = contratos_filtrados[0]
    return primeiro.get("empresa", ""), primeiro.get("cnpj", "")


def main():
    parser = argparse.ArgumentParser(
        description="Panorama cruzado de contratos de uma empresa"
    )
    filtro = parser.add_mutually_exclusive_group(required=True)
    filtro.add_argument("--cnpj", help="CNPJ da empresa (com ou sem formatação)")
    filtro.add_argument("--nome", help="Nome ou parte do nome da empresa (busca parcial)")
    parser.add_argument("--output", help="Caminho para salvar resultado JSON (opcional)")
    args = parser.parse_args()

    todos_contratos = carregar_registro()
    contratos       = filtrar_contratos(todos_contratos, args.cnpj, args.nome)

    if not contratos:
        criterio = f"CNPJ={args.cnpj}" if args.cnpj else f"nome={args.nome}"
        print(
            json.dumps(
                {"erro": f"Nenhum contrato encontrado para {criterio}"},
                ensure_ascii=False,
                indent=2,
            )
        )
        sys.exit(1)

    empresa, cnpj_encontrado = resolver_empresa(contratos)
    envios_map = carregar_envios()

    resultados = []
    erros      = []
    for contrato in contratos:
        try:
            resultado = processar_contrato(contrato, envios_map)
            resultados.append(resultado)
        except Exception as e:
            erros.append({"numero": contrato.get("numero", "?"), "erro": str(e)})

    saida = {
        "gerado_em":  datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "empresa":    empresa,
        "cnpj":       cnpj_encontrado,
        "criterio":   {"cnpj": args.cnpj, "nome": args.nome},
        "resumo":     gerar_resumo(resultados),
        "contratos":  resultados,
        "erros":      erros,
    }

    output_json = json.dumps(saida, ensure_ascii=False, indent=2)

    if args.output:
        Path(args.output).write_text(output_json, encoding="utf-8")
        print(f"Resultado salvo em: {args.output}", file=sys.stderr)

    print(output_json)


if __name__ == "__main__":
    main()
