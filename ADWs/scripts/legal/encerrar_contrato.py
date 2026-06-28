#!/usr/bin/env python3
"""
Encerramento de contrato por desistência ou cancelamento.

Uso:
  python3 encerrar_contrato.py --contrato TEF-2026-0010 --motivo desistencia
  python3 encerrar_contrato.py --contrato LIC-2026-0011 --motivo cancelamento

Motivos:
  desistencia  → cliente desistiu antes de assinar
                 - status: desistido
                 - Documenso: deleta documento (se existir)
                 - PDF local: deleta
                 - envios_assinatura: remove entrada

  cancelamento → contrato já estava ativo/assinado
                 - status: cancelado
                 - Documenso: deleta documento (se existir)
                 - PDF local: mantém
                 - envios_assinatura: remove entrada

Em ambos os casos, a subscription/cobrança no Asaas NÃO é removida
automaticamente — use --cancelar-asaas para isso (confirmação obrigatória).

Requer no .env:
  DOCUMENSO_API_URL, DOCUMENSO_API_KEY, ASAAS_API_KEY
"""

import sys
import os
import json
import argparse
from pathlib import Path

import requests
from dotenv import load_dotenv

# ── Config ────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parents[3]
load_dotenv(BASE_DIR / ".env")

API_DOCUMENSO     = os.getenv("DOCUMENSO_API_URL", "")
API_KEY_DOCUMENSO = os.getenv("DOCUMENSO_API_KEY", "")
API_KEY_ASAAS     = os.getenv("ASAAS_API_KEY", "")

REGISTRO_PATH = Path(__file__).parent / "contratos_registro.json"
GERADOS_DIR   = BASE_DIR / "workspace/legal/contratos/clientes/gerados"
ENVIOS_PATH   = GERADOS_DIR / "envios_assinatura.json"


# ── Helpers ───────────────────────────────────────────────────────────────────
def carregar_registro() -> dict:
    with open(REGISTRO_PATH, encoding="utf-8") as f:
        return json.load(f)


def salvar_registro(data: dict) -> None:
    with open(REGISTRO_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def carregar_envios() -> dict:
    if ENVIOS_PATH.exists():
        with open(ENVIOS_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {"envios": []}


def salvar_envios(data: dict) -> None:
    with open(ENVIOS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def confirmar(msg: str) -> bool:
    resp = input(f"{msg} [s/N] ").strip().lower()
    return resp == "s"


def documenso_headers(api_key: str | None = None) -> dict:
    return {"Authorization": f"Bearer {api_key or API_KEY_DOCUMENSO}",
            "Content-Type": "application/json"}


# ── Ações ─────────────────────────────────────────────────────────────────────
def deletar_no_documenso(doc_id: int) -> None:
    print(f"  Deletando doc #{doc_id} no Documenso...", end=" ", flush=True)
    resp = requests.post(
        f"{API_DOCUMENSO}/api/v2/document/delete",
        headers=documenso_headers(),
        json={"documentId": doc_id},
        timeout=15,
    )
    if resp.status_code == 200:
        print("ok")
    else:
        print(f"✗ ({resp.status_code}) — {resp.text[:200]}")


def deletar_pdf_local(pdf_path: Path) -> None:
    print(f"  Deletando PDF local ({pdf_path.name})...", end=" ", flush=True)
    if pdf_path.exists():
        pdf_path.unlink()
        print("ok")
    else:
        print("arquivo não encontrado (ignorado)")


def cancelar_subscription_asaas(sub_id: str, contrato_num: str) -> None:
    print(f"  Cancelando subscription {sub_id} no Asaas...", end=" ", flush=True)
    resp = requests.delete(
        f"https://api.asaas.com/v3/subscriptions/{sub_id}",
        headers={"access_token": API_KEY_ASAAS},
        timeout=15,
    )
    if resp.status_code in (200, 204):
        print("ok")
    else:
        print(f"✗ ({resp.status_code}) — {resp.text[:200]}")


def cancelar_cobranca_asaas(payment_id: str) -> None:
    print(f"  Cancelando cobrança {payment_id} no Asaas...", end=" ", flush=True)
    resp = requests.post(
        f"https://api.asaas.com/v3/payments/{payment_id}/cancel",
        headers={"access_token": API_KEY_ASAAS},
        timeout=15,
    )
    if resp.status_code in (200, 204):
        print("ok")
    else:
        print(f"✗ ({resp.status_code}) — {resp.text[:200]}")


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Encerra contrato por desistência ou cancelamento"
    )
    parser.add_argument("--contrato",       required=True,
                        help="Número do contrato (ex: TEF-2026-0010)")
    parser.add_argument("--motivo",         required=True,
                        choices=["desistencia", "cancelamento"],
                        help="desistencia = antes de assinar | cancelamento = já assinado")
    parser.add_argument("--cancelar-asaas", action="store_true", default=False,
                        help="Remove subscription/cobrança de adesão do Asaas (requer confirmação)")
    args = parser.parse_args()

    numero = args.contrato.upper()
    motivo = args.motivo

    # ── Localizar contrato ───────────────────────────────────────────────────
    registro = carregar_registro()
    contrato = next((c for c in registro["contratos"] if c["numero"] == numero), None)

    if not contrato:
        print(f"✗ Contrato {numero} não encontrado no registro.")
        sys.exit(1)

    status_atual = contrato.get("status", "?")
    novo_status  = "desistido" if motivo == "desistencia" else "cancelado"

    # ── Localizar envio no Documenso ─────────────────────────────────────────
    envios = carregar_envios()
    pdf_arquivo = contrato.get("arquivo", "")
    envio = next(
        (e for e in envios["envios"] if e.get("pdf") == pdf_arquivo),
        None,
    )
    doc_id  = envio.get("doc_id") if envio else None
    pdf_path = GERADOS_DIR / pdf_arquivo if pdf_arquivo else None

    # ── Resumo e confirmação ─────────────────────────────────────────────────
    print(f"\n── Encerramento de Contrato ─────────────────────────────────")
    print(f"  Contrato  : {numero}")
    print(f"  Empresa   : {contrato.get('empresa')}")
    print(f"  Tipo      : {contrato.get('tipo')}")
    print(f"  Status    : {status_atual} → {novo_status}")
    print(f"  Motivo    : {motivo}")
    print(f"")
    print(f"  Ações a executar:")
    print(f"    [1] Atualizar status no registro   : {status_atual} → {novo_status}")

    if doc_id:
        print(f"    [2] Deletar doc #{doc_id} no Documenso")
    else:
        print(f"    [2] Documenso: nenhum envio registrado (ignorado)")

    if motivo == "desistencia":
        if pdf_path and pdf_path.exists():
            print(f"    [3] Deletar PDF local             : {pdf_arquivo}")
        else:
            print(f"    [3] PDF local: não encontrado (ignorado)")
        print(f"    [4] envios_assinatura.json        : remove entrada (fluxo não concluído)")
    else:
        print(f"    [3] PDF local                     : MANTIDO (cancelamento)")
        print(f"    [4] envios_assinatura.json        : MANTIDO (histórico preservado)")

    if args.cancelar_asaas:
        sub_id     = contrato.get("asaas_subscription_id")
        payment_id = contrato.get("asaas_adesao_payment_id")
        if sub_id:
            print(f"    [4] Cancelar subscription Asaas   : {sub_id}")
        if payment_id:
            print(f"    [5] Cancelar cobrança adesão Asaas: {payment_id}")
        if not sub_id and not payment_id:
            print(f"    [4] Asaas: sem subscription/cobrança registrada")
    else:
        print(f"    [4] Asaas                         : NÃO alterado")
    print(f"──────────────────────────────────────────────────────────────")

    if not confirmar("\nConfirma o encerramento?"):
        print("Operação cancelada.")
        sys.exit(0)

    print()

    # ── Executar ações ───────────────────────────────────────────────────────

    # [1] Atualizar status no registro
    print(f"  Atualizando status no registro...", end=" ", flush=True)
    for c in registro["contratos"]:
        if c["numero"] == numero:
            c["status"] = novo_status
            break
    salvar_registro(registro)
    print("ok")

    # [2] Deletar no Documenso
    if doc_id:
        deletar_no_documenso(doc_id)

    # Entrada no envios_assinatura:
    #   desistência  → remove (fluxo não foi concluído)
    #   cancelamento → mantém (histórico: foi enviado, assinado e depois cancelado)
    if motivo == "desistencia" and envio:
        envios["envios"] = [e for e in envios["envios"] if e.get("pdf") != pdf_arquivo]
        salvar_envios(envios)
        print(f"  Entrada removida do envios_assinatura.json")

    # [3] PDF local
    if motivo == "desistencia" and pdf_path:
        deletar_pdf_local(pdf_path)

    # [4/5] Asaas — só se --cancelar-asaas for passado
    if args.cancelar_asaas:
        sub_id     = contrato.get("asaas_subscription_id")
        payment_id = contrato.get("asaas_adesao_payment_id")
        if sub_id:
            cancelar_subscription_asaas(sub_id, numero)
        if payment_id:
            cancelar_cobranca_asaas(payment_id)

    print(f"\n✓ Contrato {numero} encerrado como '{novo_status}'.")
    print()


if __name__ == "__main__":
    main()
