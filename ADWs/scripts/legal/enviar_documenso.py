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


def criar_documento(titulo: str, nome: str, email: str, email_cc: str | None) -> dict:
    """Etapa 1 — cria o documento com signatários em uma única chamada.

    Sempre inclui dois SIGNERs:
      [0] CONTRATANTE (cliente)       → campo de assinatura no lado direito
      [1] CONTRATADA (Automação)      → campo de assinatura no lado esquerdo
    """
    print(f"  Criando documento no Documenso...", end=" ", flush=True)

    recipients = [
        {"name": nome, "email": email, "role": "SIGNER"},
        ASSINANTE_CONTRATADA,
    ]
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
                               pagina: int = 11) -> None:
    """Etapa 2b — adiciona campos de assinatura para ambos os signatários.

    - CONTRATANTE (cliente)  → lado direito (pageX=55), mesma altura
    - CONTRATADA (Automação) → lado esquerdo (pageX=5), mesma altura
    Coordenadas em % da página (0-100).
    """
    print(f"  Adicionando campos de assinatura (pág. {pagina})...", end=" ", flush=True)

    campos = [
        # CONTRATANTE — lado direito
        {
            "recipientId": recipient_cliente_id,
            "type":        "SIGNATURE",
            "pageNumber":  pagina,
            "pageX":       55,
            "pageY":       32,
            "pageWidth":   38,
            "pageHeight":  9,
        },
        # CONTRATADA — lado esquerdo, mesma altura
        {
            "recipientId": recipient_contratada_id,
            "type":        "SIGNATURE",
            "pageNumber":  pagina,
            "pageX":       5,
            "pageY":       32,
            "pageWidth":   38,
            "pageHeight":  9,
        },
    ]

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

    print(f"ok (cliente=direita, contratada=esquerda)")


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
    parser.add_argument("--cc",               help="E-mail para cópia (ex: copia@automacaosoftware.com.br)")
    parser.add_argument("--pagina-assinatura", type=int, default=None,
                        help="Página onde o campo de assinatura será posicionado "
                             "(padrão: 11 para licença, 8 para TEF — detectado pelo nome do arquivo)")
    parser.add_argument("--tipo", choices=["licenca", "tef"], default=None,
                        help="Tipo do contrato para definir página padrão (licenca=11, tef=8)")
    parser.add_argument("--enviar", action="store_true", default=False,
                        help="Dispara o e-mail de assinatura imediatamente via Documenso. "
                             "Sem esta flag, o documento é criado como DRAFT e o envio "
                             "deve ser feito manualmente pela plataforma.")
    args = parser.parse_args()

    checar_config()

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        print(f"✗ Arquivo não encontrado: {pdf_path}")
        sys.exit(1)

    titulo = args.titulo or pdf_path.stem.replace("_", " ")

    modo = "ENVIO AUTOMÁTICO (e-mail disparado)" if args.enviar else "DRAFT (envio manual pela plataforma)"
    print(f"\n── Documenso — {modo} ─────────────────")
    print(f"  Arquivo   : {pdf_path.name}")
    print(f"  Signatário: {args.nome} <{args.email}>")
    print(f"  Contratada: Automação Comercial LTDA. <eduardo@automacaosoftware.com.br>")
    print(f"  Título    : {titulo}")
    print(f"  Documenso : {API_URL}")
    print(f"────────────────────────────────────────────────────────\n")

    # Etapa 1 — criar documento + signatários
    doc = criar_documento(titulo, args.nome, args.email, args.cc)
    doc_id     = doc["documentId"]
    upload_url = doc["uploadUrl"]

    # Etapa 2 — upload do PDF na URL pré-assinada do MinIO
    upload_pdf(upload_url, pdf_path)

    # Etapa 2b — campos de assinatura para CONTRATANTE e CONTRATADA
    if args.pagina_assinatura:
        pagina = args.pagina_assinatura
    elif args.tipo == "tef" or "TEF" in pdf_path.name:
        pagina = 8
    else:
        pagina = 11   # licença de software (padrão)

    recipient_cliente_id    = doc["recipients"][0]["recipientId"]  # CONTRATANTE
    recipient_contratada_id = doc["recipients"][1]["recipientId"]  # CONTRATADA
    adicionar_campo_assinatura(doc_id, recipient_cliente_id,
                               recipient_contratada_id, pagina=pagina)

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

    registro["envios"].append({
        "pdf":          pdf_path.name,
        "doc_id":       doc_id,
        "titulo":       titulo,
        "signatario":   {"nome": args.nome, "email": args.email},
        "link":         link,
        "enviado_em":   __import__("datetime").date.today().isoformat(),
    })
    registro_path.write_text(json.dumps(registro, ensure_ascii=False, indent=2))
    print(f"  Registro salvo em      : {registro_path}")


if __name__ == "__main__":
    main()
