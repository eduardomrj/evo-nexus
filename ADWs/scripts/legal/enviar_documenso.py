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

def criar_documento(titulo: str, nome: str, email: str, email_cc: str | None) -> dict:
    """Etapa 1 — cria o documento com signatários em uma única chamada."""
    print(f"  Criando documento no Documenso...", end=" ", flush=True)

    recipients = [{"name": nome, "email": email, "role": "SIGNER"}]
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


def adicionar_campo_assinatura(doc_id: int, recipient_id: int, pdf_path: Path) -> None:
    """Etapa 2b — adiciona campo de assinatura na última página (seção de assinaturas)."""
    print(f"  Adicionando campo de assinatura...", end=" ", flush=True)

    from pypdf import PdfReader
    num_paginas = len(PdfReader(str(pdf_path)).pages)

    resp = requests.post(
        f"{API_URL}/api/v1/documents/{doc_id}/fields",
        headers={**headers(), "Content-Type": "application/json"},
        json={
            "recipientId": recipient_id,
            "type":        "SIGNATURE",
            "pageNumber":  num_paginas,
            "pageX":       55,
            "pageY":       55,
            "pageWidth":   40,
            "pageHeight":  10,
        },
        timeout=30,
    )

    if resp.status_code not in (200, 201):
        print(f"✗ ({resp.status_code}) — {resp.text[:200]}")
        sys.exit(1)

    print(f"ok (página {num_paginas})")


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
    parser.add_argument("--cc",     help="E-mail para cópia (ex: copia@automacaosoftware.com.br)")
    args = parser.parse_args()

    checar_config()

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        print(f"✗ Arquivo não encontrado: {pdf_path}")
        sys.exit(1)

    titulo = args.titulo or pdf_path.stem.replace("_", " ")

    print(f"\n── Enviando para assinatura ─────────────────────────────")
    print(f"  Arquivo   : {pdf_path.name}")
    print(f"  Signatário: {args.nome} <{args.email}>")
    print(f"  Título    : {titulo}")
    print(f"  Documenso : {API_URL}")
    print(f"────────────────────────────────────────────────────────\n")

    # Etapa 1 — criar documento + signatários
    doc = criar_documento(titulo, args.nome, args.email, args.cc)
    doc_id     = doc["documentId"]
    upload_url = doc["uploadUrl"]

    # Etapa 2 — upload do PDF na URL pré-assinada do MinIO
    upload_pdf(upload_url, pdf_path)

    # Etapa 2b — campo de assinatura (obrigatório pelo Documenso)
    recipient_id = doc["recipients"][0]["recipientId"]
    adicionar_campo_assinatura(doc_id, recipient_id, pdf_path)

    # Etapa 3 — Documenso dispara e-mail ao signatário
    disparar_envio(doc_id)

    # Resultado
    link = f"{API_URL}/documents/{doc_id}"
    print(f"\n✓ Documento enviado ao Documenso com sucesso!")
    print(f"  Link de acompanhamento : {link}")
    print(f"  Status atual           : {status_documento(doc_id)}")
    print(f"  O Documenso enviará o e-mail ao signatário via signature@automacaosoftware.com.br\n")

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
