#!/usr/bin/env python3
"""
Envio de contrato para assinatura via Documenso self-hosted.

Uso:
  python3 enviar_documenso.py \
    --pdf /caminho/para/CONTRATO_TEF_XXX.pdf \
    --nome "João da Silva" \
    --email "joao@empresa.com.br" \
    [--titulo "Contrato TEF SmartPOS — Empresa XYZ"]
    [--cc "copia@automacaosoftware.com.br"]

Requer no .env:
  DOCUMENSO_API_URL=https://signature.automacaosoftware.com.br
  DOCUMENSO_API_KEY=<token gerado em /settings/tokens>
"""

import sys
import os
import json
import argparse
from pathlib import Path

import requests
from dotenv import load_dotenv

# ── Config ────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parents[3]   # evo-nexus/
load_dotenv(BASE_DIR / ".env")

API_URL = os.getenv("DOCUMENSO_API_URL", "https://signature.automacaosoftware.com.br")
API_KEY = os.getenv("DOCUMENSO_API_KEY", "")


# ── Helpers ───────────────────────────────────────────────────────────────────
def headers() -> dict:
    return {"Authorization": f"Bearer {API_KEY}"}


def checar_config() -> None:
    if not API_KEY:
        print("✗ DOCUMENSO_API_KEY não encontrada no .env")
        print("  Gere o token em: https://signature.automacaosoftware.com.br/settings/tokens")
        print("  Adicione ao .env: DOCUMENSO_API_KEY=<token>")
        sys.exit(1)


# ── Etapas do fluxo (API Documenso v2) ───────────────────────────────────────
# Fluxo correto:
#   1. POST /api/v1/documents  →  cria documento + signatários, retorna uploadUrl + documentId
#   2. PUT <uploadUrl>          →  envia o PDF para o MinIO via URL pré-assinada
#   3. POST /api/v1/documents/{id}/send  →  Documenso envia e-mail ao signatário

ASSINANTE_CONTRATADA = {
    "name":  "Automação Comercial LTDA.",
    "email": "eduardo@automacaosoftware.com.br",
    "role":  "SIGNER",
}


def criar_documento(titulo: str, nome: str, email: str, email_cc: str | None,
                    parceiro_nome: str | None = None,
                    parceiro_email: str | None = None) -> dict:
    """Etapa 1 — cria o documento com signatários em uma única chamada.

    Ordem sempre: CONTRATANTE → (PARCEIRO, se houver) → CONTRATADA
      [0] CONTRATANTE (cliente)       → campo de assinatura no lado direito
      [1] PARCEIRO (revendedor)       → campo na seção de testemunhas  (opcional)
      [-1] CONTRATADA (Automação)     → campo de assinatura no lado esquerdo
    """
    print(f"  Criando documento no Documenso...", end=" ", flush=True)

    recipients = [
        {"name": nome, "email": email, "role": "SIGNER"},
    ]
    if parceiro_nome and parceiro_email:
        recipients.append({"name": parceiro_nome, "email": parceiro_email, "role": "SIGNER"})
    recipients.append(ASSINANTE_CONTRATADA)
    if email_cc:
        recipients.append({"name": "Automação Software", "email": email_cc, "role": "CC"})

    resp = requests.post(
        f"{API_URL}/api/v1/documents",
        headers={**headers(), "Content-Type": "application/json"},
        json={"title": titulo, "recipients": recipients},
        timeout=60,
    )

    if resp.status_code not in (200, 201):
        print(f"✗ ({resp.status_code})")
        print(f"  Resposta: {resp.text[:300]}")
        sys.exit(1)

    doc = resp.json()
    print(f"ok (documentId={doc['documentId']})")
    return doc


def upload_pdf(upload_url: str, pdf_path: Path) -> None:
    """Etapa 2 — envia o PDF para a URL pré-assinada do MinIO."""
    print(f"  Enviando PDF ({pdf_path.name})...", end=" ", flush=True)

    with open(pdf_path, "rb") as f:
        resp = requests.put(
            upload_url,
            data=f,
            headers={"Content-Type": "application/pdf"},
            timeout=60,
        )

    if resp.status_code not in (200, 201, 204):
        print(f"✗ ({resp.status_code})")
        print(f"  Resposta: {resp.text[:300]}")
        sys.exit(1)

    print("ok")


def adicionar_campo_assinatura(doc_id: int, recipient_cliente_id: int,
                               recipient_contratada_id: int,
                               pagina: int = 11,
                               page_y: int = 32,
                               recipient_parceiro_id: int | None = None,
                               page_y_parceiro: int | None = None) -> None:
    """Etapa 2b — adiciona campos de assinatura para todos os signatários.

    - CONTRATANTE (cliente)  → lado direito (pageX=55)
    - CONTRATADA (Automação) → lado esquerdo (pageX=5)
    - PARCEIRO (revendedor)  → seção de testemunhas, linha abaixo (pageX=5, y=page_y_parceiro)
    Coordenadas em % da página (0-100).
    page_y padrão por tipo: LIC=29, TEF=22
    page_y_parceiro padrão: LIC=57, TEF=52
    """
    tem_parceiro = recipient_parceiro_id is not None
    info = f"pág. {pagina}, y={page_y}" + (f", parceiro y={page_y_parceiro}" if tem_parceiro else "")
    print(f"  Adicionando campos de assinatura ({info})...", end=" ", flush=True)

    campos = [
        # CONTRATANTE — lado direito
        {
            "recipientId": recipient_cliente_id,
            "type":        "SIGNATURE",
            "pageNumber":  pagina,
            "pageX":       55,
            "pageY":       page_y,
            "pageWidth":   38,
            "pageHeight":  7,
        },
        # CONTRATADA — lado esquerdo, mesma altura
        {
            "recipientId": recipient_contratada_id,
            "type":        "SIGNATURE",
            "pageNumber":  pagina,
            "pageX":       5,
            "pageY":       page_y,
            "pageWidth":   38,
            "pageHeight":  7,
        },
    ]

    # PARCEIRO — testemunha 1, linha abaixo das partes principais
    if tem_parceiro:
        campos.append({
            "recipientId": recipient_parceiro_id,
            "type":        "SIGNATURE",
            "pageNumber":  pagina,
            "pageX":       5,
            "pageY":       page_y_parceiro,
            "pageWidth":   60,
            "pageHeight":  7,
        })

    for campo in campos:
        resp = requests.post(
            f"{API_URL}/api/v1/documents/{doc_id}/fields",
            headers={**headers(), "Content-Type": "application/json"},
            json=campo,
            timeout=30,
        )
        if resp.status_code not in (200, 201):
            print(f"✗ ({resp.status_code}) — {resp.text[:200]}")
            sys.exit(1)

    partes_info = "cliente=direita, contratada=esquerda"
    if tem_parceiro:
        partes_info += ", parceiro=testemunha"
    print(f"ok ({partes_info})")


def disparar_envio(doc_id: int) -> dict:
    """Etapa 3 — instrui o Documenso a iniciar o fluxo de assinatura.
    É o Documenso quem envia o e-mail ao signatário via SMTP configurado."""
    print(f"  Iniciando fluxo de assinatura no Documenso...", end=" ", flush=True)

    resp = requests.post(
        f"{API_URL}/api/v1/documents/{doc_id}/send",
        headers={**headers(), "Content-Type": "application/json"},
        json={"sendEmail": True},
        timeout=15,
    )

    if resp.status_code not in (200, 201):
        print(f"✗ ({resp.status_code})")
        print(f"  Resposta: {resp.text[:300]}")
        sys.exit(1)

    resultado = resp.json()
    print("ok")
    return resultado


def status_documento(doc_id: int) -> str:
    """Consulta o status atual do documento."""
    resp = requests.get(
        f"{API_URL}/api/v1/documents/{doc_id}",
        headers=headers(),
        timeout=10,
    )
    if resp.status_code == 200:
        return resp.json().get("status", "DESCONHECIDO")
    return "ERRO AO CONSULTAR"


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(description="Envia contrato PDF para assinatura via Documenso")
    parser.add_argument("--pdf",    required=True, help="Caminho absoluto do PDF a enviar")
    parser.add_argument("--nome",   required=True, help="Nome completo do signatário (cliente)")
    parser.add_argument("--email",  required=True, help="E-mail do signatário (cliente)")
    parser.add_argument("--titulo", help="Título do documento no Documenso (padrão: nome do arquivo)")
    parser.add_argument("--cc",                  help="E-mail para cópia (ex: copia@automacaosoftware.com.br)")
    parser.add_argument("--pagina-assinatura",   type=int, default=None,
                        help="Página onde o campo de assinatura será posicionado "
                             "(padrão: 11 para licença, 8 para TEF — detectado pelo nome do arquivo)")
    parser.add_argument("--tipo",                choices=["licenca", "tef"], default=None,
                        help="Tipo do contrato para definir página padrão (licenca=11, tef=8)")
    parser.add_argument("--enviar",              action="store_true", default=False,
                        help="Dispara o e-mail de assinatura imediatamente via Documenso. "
                             "Sem esta flag, o documento é criado como DRAFT e o envio "
                             "deve ser feito manualmente pela plataforma.")
    # Parceiro/revendedor (opcionais — ambos obrigatórios se um for fornecido)
    parser.add_argument("--parceiro-nome",       help="Nome do representante do parceiro/revendedor")
    parser.add_argument("--parceiro-email",      help="E-mail do parceiro para assinatura eletrônica")
    parser.add_argument("--y-parceiro",          type=int, default=None,
                        help="pageY (0-100) do campo de assinatura do parceiro na seção de testemunhas "
                             "(padrão: 52 para TEF, 57 para LIC — ajuste se necessário)")
    args = parser.parse_args()

    checar_config()

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        print(f"✗ Arquivo não encontrado: {pdf_path}")
        sys.exit(1)

    # Validar parceiro — os dois campos são obrigatórios juntos
    tem_parceiro = bool(args.parceiro_nome or args.parceiro_email)
    if tem_parceiro and not (args.parceiro_nome and args.parceiro_email):
        print("✗ --parceiro-nome e --parceiro-email devem ser fornecidos juntos")
        sys.exit(1)

    titulo = args.titulo or pdf_path.stem.replace("_", " ")

    modo = "ENVIO AUTOMÁTICO (e-mail disparado)" if args.enviar else "DRAFT (envio manual pela plataforma)"
    print(f"\n── Documenso — {modo} ─────────────────")
    print(f"  Arquivo   : {pdf_path.name}")
    print(f"  Signatário: {args.nome} <{args.email}>")
    if tem_parceiro:
        print(f"  Parceiro  : {args.parceiro_nome} <{args.parceiro_email}>")
    print(f"  Contratada: Automação Comercial LTDA. <eduardo@automacaosoftware.com.br>")
    print(f"  Título    : {titulo}")
    print(f"  Documenso : {API_URL}")
    print(f"────────────────────────────────────────────────────────\n")

    # Etapa 1 — criar documento + signatários
    doc = criar_documento(titulo, args.nome, args.email, args.cc,
                          parceiro_nome=args.parceiro_nome if tem_parceiro else None,
                          parceiro_email=args.parceiro_email if tem_parceiro else None)
    doc_id     = doc["documentId"]
    upload_url = doc["uploadUrl"]

    # Etapa 2 — upload do PDF na URL pré-assinada do MinIO
    upload_pdf(upload_url, pdf_path)

    # Etapa 2b — campos de assinatura
    is_tef = args.tipo == "tef" or "TEF" in pdf_path.name

    if args.pagina_assinatura:
        pagina = args.pagina_assinatura
    elif is_tef:
        pagina = 8
    else:
        pagina = 11   # licença de software

    # pageY por tipo: TEF=22, LIC=29
    page_y = 22 if is_tef else 29

    # Índices dependem da presença do parceiro
    # Ordem dos recipients: [0]=CONTRATANTE, [1]=PARCEIRO (se houver), [-1]=CONTRATADA
    recipients = doc["recipients"]
    recipient_cliente_id    = recipients[0]["recipientId"]   # CONTRATANTE
    recipient_contratada_id = recipients[-1]["recipientId"]  # CONTRATADA (sempre o último)

    recipient_parceiro_id = None
    page_y_parceiro       = None
    if tem_parceiro:
        recipient_parceiro_id = recipients[1]["recipientId"]   # PARCEIRO
        # pageY padrão da seção de testemunhas: TEF=52, LIC=57 (ajustável via --y-parceiro)
        page_y_parceiro = args.y_parceiro if args.y_parceiro else (52 if is_tef else 57)

    adicionar_campo_assinatura(doc_id, recipient_cliente_id,
                               recipient_contratada_id, pagina=pagina, page_y=page_y,
                               recipient_parceiro_id=recipient_parceiro_id,
                               page_y_parceiro=page_y_parceiro)

    # Etapa 3 — disparar e-mail (opcional)
    if args.enviar:
        disparar_envio(doc_id)

    # Resultado
    link = f"{API_URL}/documents/{doc_id}"
    print(f"\n✓ Documento criado no Documenso com sucesso!")
    print(f"  Link de acompanhamento : {link}")
    print(f"  Status atual           : {status_documento(doc_id)}")
    if args.enviar:
        print(f"  E-mail disparado pelo Documenso via signature@automacaosoftware.com.br")
    else:
        print(f"  Documento em DRAFT — acesse a plataforma para revisar e enviar manualmente:")
        print(f"  {link}")
    print()

    # Salvar referência local (JSON na mesma pasta dos contratos gerados)
    registro_path = pdf_path.parent / "envios_assinatura.json"
    registro = {"envios": []}
    if registro_path.exists():
        registro = json.loads(registro_path.read_text())

    envio: dict = {
        "pdf":        pdf_path.name,
        "doc_id":     doc_id,
        "titulo":     titulo,
        "signatario": {"nome": args.nome, "email": args.email},
        "link":       link,
        "enviado_em": __import__("datetime").date.today().isoformat(),
    }
    if tem_parceiro:
        envio["parceiro"] = {"nome": args.parceiro_nome, "email": args.parceiro_email}
    registro["envios"].append(envio)
    registro_path.write_text(json.dumps(registro, ensure_ascii=False, indent=2))
    print(f"  Registro salvo em      : {registro_path}")


if __name__ == "__main__":
    main()
