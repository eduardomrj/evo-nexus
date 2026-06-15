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


# ── Etapas do fluxo ──────────────────────────────────────────────────────────
def upload_documento(pdf_path: Path, titulo: str) -> dict:
    """Etapa 1 — faz upload do PDF e cria o documento no Documenso."""
    print(f"  Enviando PDF para o Documenso...", end=" ", flush=True)

    with open(pdf_path, "rb") as f:
        resp = requests.post(
            f"{API_URL}/api/v1/documents",
            headers=headers(),
            files={"file": (pdf_path.name, f, "application/pdf")},
            data={"title": titulo},
            timeout=30,
        )

    if resp.status_code not in (200, 201):
        print(f"✗ ({resp.status_code})")
        print(f"  Resposta: {resp.text[:300]}")
        sys.exit(1)

    doc = resp.json()
    print(f"ok (id={doc['id']})")
    return doc


def adicionar_signatario(doc_id: int, nome: str, email: str) -> dict:
    """Etapa 2 — adiciona o signatário (cliente) ao documento."""
    print(f"  Adicionando signatário {nome} <{email}>...", end=" ", flush=True)

    resp = requests.post(
        f"{API_URL}/api/v1/documents/{doc_id}/recipients",
        headers={**headers(), "Content-Type": "application/json"},
        json={"name": nome, "email": email, "role": "SIGNER"},
        timeout=15,
    )

    if resp.status_code not in (200, 201):
        print(f"✗ ({resp.status_code})")
        print(f"  Resposta: {resp.text[:300]}")
        sys.exit(1)

    rec = resp.json()
    print(f"ok (recipientId={rec['id']})")
    return rec


def adicionar_copia(doc_id: int, email_cc: str) -> None:
    """Etapa 2b (opcional) — adiciona cópia em CC (sem necessidade de assinar)."""
    print(f"  Adicionando cópia para {email_cc}...", end=" ", flush=True)

    resp = requests.post(
        f"{API_URL}/api/v1/documents/{doc_id}/recipients",
        headers={**headers(), "Content-Type": "application/json"},
        json={"name": "Automação Software", "email": email_cc, "role": "CC"},
        timeout=15,
    )

    if resp.status_code not in (200, 201):
        print(f"✗ ({resp.status_code}) — cópia ignorada")
    else:
        print("ok")


def disparar_envio(doc_id: int) -> dict:
    """Etapa 3 — dispara o e-mail de assinatura para o signatário."""
    print(f"  Disparando e-mail de assinatura...", end=" ", flush=True)

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

    # Etapa 1 — upload
    doc = upload_documento(pdf_path, titulo)
    doc_id = doc["id"]

    # Etapa 2 — signatário
    adicionar_signatario(doc_id, args.nome, args.email)

    # Etapa 2b — cópia (opcional)
    if args.cc:
        adicionar_copia(doc_id, args.cc)

    # Etapa 3 — disparar
    disparar_envio(doc_id)

    # Resultado
    link = f"{API_URL}/documents/{doc_id}"
    print(f"\n✓ Documento enviado com sucesso!")
    print(f"  Link de acompanhamento : {link}")
    print(f"  Status atual           : {status_documento(doc_id)}")
    print(f"  O cliente receberá o e-mail em instantes.\n")

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
