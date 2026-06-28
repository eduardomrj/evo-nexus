#!/usr/bin/env python3
"""
Envio de contrato para assinatura via Documenso self-hosted — API v2.

Uso:
  python3 enviar_documenso.py \
    --pdf /caminho/para/CONTRATO_TEF_XXX.pdf \
    --nome "João da Silva" \
    --email "joao@empresa.com.br" \
    [--titulo "Contrato TEF SmartPOS — Empresa XYZ"]
    [--cc "copia@automacaosoftware.com.br"]
    [--tipo licenca|tef]
    [--parceiro-nome "Paulo Kleber"] [--parceiro-email "pk@email.com"]
    [--api-key-parceiro-env DOCUMENSO_API_KEY_SOLUTIONTEC]
    [--enviar]

Requer no .env:
  DOCUMENSO_API_URL=https://signature.automacaosoftware.com.br
  DOCUMENSO_API_KEY=<token gerado em /settings/tokens>

Validade e lembretes (configurados via API v2):
  - Validade: 7 dias
  - Lembretes: primeiro após 2 dias, repetir a cada 2 dias
"""

import sys
import os
import re
import json
import argparse
from pathlib import Path

import requests
import fitz  # PyMuPDF
from dotenv import load_dotenv

# ── Config ────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parents[3]   # evo-nexus/
load_dotenv(BASE_DIR / ".env")

API_URL = os.getenv("DOCUMENSO_API_URL", "https://signature.automacaosoftware.com.br")
API_KEY = os.getenv("DOCUMENSO_API_KEY", "")

# Validade e lembretes — configurados via API v2
ENVELOPE_EXPIRATION = {"unit": "day", "amount": 7}
REMINDER_SETTINGS   = {
    "sendAfter":   {"unit": "day", "amount": 1},  # 1º lembrete após 1 dia
    "repeatEvery": {"unit": "day", "amount": 2},  # repetir a cada 2 dias
}


# ── Helpers ───────────────────────────────────────────────────────────────────
def headers() -> dict:
    return {"Authorization": f"Bearer {API_KEY}"}


def checar_config() -> None:
    if not API_KEY:
        print("✗ DOCUMENSO_API_KEY não encontrada no .env")
        print("  Gere o token em: https://signature.automacaosoftware.com.br/settings/tokens")
        print("  Adicione ao .env: DOCUMENSO_API_KEY=<token>")
        sys.exit(1)


# ── Detecção de páginas via PyMuPDF ──────────────────────────────────────────
def pagina_anexo_iii_pdf(pdf_path: Path) -> int | None:
    """Detecta a página do Anexo III buscando 'Contatos Administrativos'.
    Usa âncora específica porque 'Anexo III' aparece múltiplas vezes no corpo
    do contrato (referências ao anexo).
    Retorna o número da página (1-based) ou None se o anexo não existir.
    """
    doc = fitz.open(str(pdf_path))
    for i in range(doc.page_count):
        if "Contatos Administrativos" in doc[i].get_text():
            doc.close()
            return i + 1
    doc.close()
    return None


def posicoes_labels_pdf(pdf_path: Path, pagina: int) -> list[tuple[float, str]]:
    """Retorna lista de (y_percent, label) para cada ocorrência de
    'Nome', 'Telefone' e 'E-mail' na página do Anexo III, ordenada por Y.

    Cada label aparece exatamente 3 vezes na página (uma por seção):
      Adm/Financeiro → Contador → TI  (ordem Y crescente)
    """
    doc = fitz.open(str(pdf_path))
    page = doc[pagina - 1]
    rect = page.rect
    resultado = []
    for label in ("Nome", "Telefone", "E-mail"):
        for r in page.search_for(label):
            y_pct = round((r.y0 / rect.height) * 100, 1)
            resultado.append((y_pct, label))
    doc.close()
    return sorted(resultado)   # ordena por Y crescente


def pagina_assinaturas_pdf(pdf_path: Path) -> int:
    """Detecta a página de assinaturas buscando 'CPF: ___' — linha em branco do
    bloco de assinaturas da CONTRATADA, que só aparece na página de assinaturas.
    Retorna o número da página (1-based).
    Fallback: última página do PDF.
    """
    doc = fitz.open(str(pdf_path))
    fallback = doc.page_count
    for i in range(doc.page_count):
        if "CPF: ___" in doc[i].get_text():
            doc.close()
            return i + 1  # 1-based
    doc.close()
    return fallback


# ── Montagem de campos (sem chamada de API) ───────────────────────────────────
def montar_campos_assinatura(pagina: int,
                             y_partes: float = 36.0,
                             y_parceiro: float = 65.5,
                             tem_parceiro: bool = False) -> dict:
    """Retorna dicionário com listas de campos por papel:
      'contratada', 'cliente', 'parceiro' (vazia se sem parceiro).

    Coordenadas em % da página (0–100).
    """
    # pageY já vem calibrado por tipo (calculado em criar_documento_v2)
    campo_contratada = {
        "type": "SIGNATURE",
        "pageNumber": pagina,
        "pageX": 5,
        "pageY": y_partes,
        "width": 38,
        "height": 7,
    }
    campo_cliente = {
        "type": "SIGNATURE",
        "pageNumber": pagina,
        "pageX": 55,
        "pageY": y_partes,
        "width": 38,
        "height": 7,
    }
    campo_parceiro = {
        "type": "SIGNATURE",
        "pageNumber": pagina,
        "pageX": 5,
        "pageY": y_parceiro,
        "width": 60,
        "height": 7,
    } if tem_parceiro else None

    return {
        "contratada": [campo_contratada],
        "cliente":    [campo_cliente],
        "parceiro":   [campo_parceiro] if campo_parceiro else [],
    }


def montar_campos_texto_contato(pdf_path: Path, pagina: int) -> list[dict]:
    """Monta lista de campos TEXT/EMAIL para o Anexo III (Contatos Administrativos).
    Usa PyMuPDF para detectar posições dos labels na página.
    Retorna lista pronta para inserir em recipient.fields[].
    """
    labels_pos = posicoes_labels_pdf(pdf_path, pagina)

    if not labels_pos:
        labels_pos = [
            (20.0, "Nome"), (24.0, "Telefone"), (28.0, "E-mail"),
            (46.0, "Nome"), (50.0, "Telefone"), (54.0, "E-mail"),
            (68.0, "Nome"), (72.0, "Telefone"), (76.0, "E-mail"),
        ]
        print("  (labels não detectados no PDF — usando posições estimadas)")

    SECOES   = ["Adm/Financeiro", "Contador", "TI"]
    REQUIRED = [True,             True,        False]
    contadores_label: dict[str, int] = {"Nome": 0, "Telefone": 0, "E-mail": 0}
    secao_atual = 0

    campos = []
    for y_pct, label in labels_pos:
        if label == "Nome":
            secao_atual = contadores_label["Nome"]
        contadores_label[label] += 1

        secao    = SECOES[secao_atual]
        required = REQUIRED[secao_atual]

        if label == "E-mail" and secao_atual == 0:
            campo_type = "EMAIL"
            meta_type  = "email"
        else:
            campo_type = "TEXT"
            meta_type  = "text"

        SECAO_SLUG = {"Adm/Financeiro": "adm", "Contador": "contador", "TI": "ti"}
        LABEL_SLUG = {"Nome": "nome", "Telefone": "telefone", "E-mail": "email"}
        field_slug = f"{LABEL_SLUG[label]}_{SECAO_SLUG[secao]}"

        campos.append({
            "type":       campo_type,
            "pageNumber": pagina,
            "pageX":      50,
            "pageY":      round(y_pct + 0.5, 1),
            "width":      43,
            "height":     1.5,
            "fieldMeta": {
                "type":        meta_type,
                "label":       f"{label} — {secao}",
                "placeholder": field_slug,
                "required":    required,
            },
        })

    return campos


# ── API v2 — Fluxo principal ──────────────────────────────────────────────────
# Fluxo v2:
#   1. POST /api/v2/document/create  (multipart: payload JSON + file PDF)
#      → retorna { id: int, envelopeId: str }
#   2. POST /api/v2/document/distribute  (JSON: documentId + meta)
#      → Documenso envia e-mail ao signatário

ASSINANTE_CONTRATADA = {
    "name":  "Automação Comercial LTDA.",
    "email": "eduardo@automacaosoftware.com.br",
    "role":  "SIGNER",
}


def criar_documento_v2(titulo: str,
                       nome: str, email: str, email_cc: str | None,
                       pdf_path: Path,
                       tipo: str | None,
                       parceiro_nome: str | None = None,
                       parceiro_email: str | None = None) -> dict:
    """Etapa 1 — cria documento via API v2 (multipart/form-data).

    PDF + payload JSON em uma única chamada.
    Campos de assinatura e texto já embutidos nos recipients.

    Ordem de assinatura SEQUENCIAL:
      Com parceiro   : PARCEIRO (1) → CONTRATANTE (2) → CONTRATADA (3)
      Sem parceiro   : CONTRATANTE (1) → CONTRATADA (2)
    """
    print(f"  Detectando páginas no PDF...", end=" ", flush=True)
    pagina_assin = pagina_assinaturas_pdf(pdf_path)
    pagina_iii   = pagina_anexo_iii_pdf(pdf_path)
    print(f"assinaturas=pág.{pagina_assin}"
          + (f", Anexo III=pág.{pagina_iii}" if pagina_iii else ", sem Anexo III"))

    # Posições calibradas por tipo de contrato.
    # y_partes  = posição Y dos campos CONTRATANTE e CONTRATADA
    # y_parceiro = posição Y do campo PARCEIRO
    # Offset aplicado para alinhar o campo com a linha de assinatura no PDF:
    #   licença : subir 100% da altura (field_height=7) → y - 7.0
    #   tef     : subir 20% da altura                  → y - 1.4  (parceiro: subir 100%)
    if tipo == "tef":
        y_partes,    y_parceiro_pos = 24.8 - 1.4, 54.3 - 7.0   # → 23.4,  47.3
    else:
        y_partes,    y_parceiro_pos = 36.0 - 7.0, 65.5 - 7.0   # → 29.0,  58.5

    tem_parceiro = bool(parceiro_nome and parceiro_email)
    campos = montar_campos_assinatura(
        pagina=pagina_assin,
        y_partes=y_partes,
        y_parceiro=y_parceiro_pos,
        tem_parceiro=tem_parceiro,
    )

    # Campos texto do Anexo III (apenas para o cliente)
    campos_contato = []
    if pagina_iii:
        print(f"  Montando campos de contato (pág. {pagina_iii})...", end=" ", flush=True)
        campos_contato = montar_campos_texto_contato(pdf_path, pagina_iii)
        print(f"ok ({len(campos_contato)} campos)")

    # Montar recipients com campos embutidos
    if tem_parceiro:
        recipients = [
            {
                "name":  parceiro_nome,
                "email": parceiro_email,
                "role":  "SIGNER",
                "signingOrder": 1,
                "fields": campos["parceiro"],
            },
            {
                "name":  nome,
                "email": email,
                "role":  "SIGNER",
                "signingOrder": 2,
                "fields": campos["cliente"] + campos_contato,
            },
            {
                **ASSINANTE_CONTRATADA,
                "signingOrder": 3,
                "fields": campos["contratada"],
            },
        ]
    else:
        recipients = [
            {
                "name":  nome,
                "email": email,
                "role":  "SIGNER",
                "signingOrder": 1,
                "fields": campos["cliente"] + campos_contato,
            },
            {
                **ASSINANTE_CONTRATADA,
                "signingOrder": 2,
                "fields": campos["contratada"],
            },
        ]

    if email_cc:
        recipients.append({
            "name":  "Automação Software",
            "email": email_cc,
            "role":  "CC",
            "fields": [],
        })

    payload = {
        "title": titulo,
        "envelopeExpirationPeriod": ENVELOPE_EXPIRATION,
        "reminderSettings":         REMINDER_SETTINGS,
        "recipients": recipients,
    }

    print(f"  Criando documento no Documenso (v2)...", end=" ", flush=True)

    with open(pdf_path, "rb") as pdf_file:
        resp = requests.post(
            f"{API_URL}/api/v2/document/create",
            headers=headers(),
            files={
                "file":    (pdf_path.name, pdf_file, "application/pdf"),
                "payload": (None, json.dumps(payload), "application/json"),
            },
            timeout=120,
        )

    if resp.status_code not in (200, 201):
        print(f"✗ ({resp.status_code})")
        print(f"  Resposta: {resp.text[:400]}")
        sys.exit(1)

    doc = resp.json()
    print(f"ok (documentId={doc['id']})")
    return doc


def atualizar_documento(doc_id: int) -> None:
    """Etapa 1b — aplica validade, lembretes e ordem de assinatura via /document/update.

    Esses campos não são aceitos pelo /document/create (multipart),
    mas são suportados pelo /document/update (JSON).
    """
    print(f"  Aplicando validade e lembretes...", end=" ", flush=True)

    resp = requests.post(
        f"{API_URL}/api/v2/document/update",
        headers={**headers(), "Content-Type": "application/json"},
        json={
            "documentId": doc_id,
            "meta": {
                "signingOrder": "SEQUENTIAL",
                "timezone":     "America/Fortaleza",
                "dateFormat":   "dd/MM/yyyy",
                "language":     "pt-BR",
            },
            "envelopeExpirationPeriod": ENVELOPE_EXPIRATION,
            "reminderSettings":         REMINDER_SETTINGS,
        },
        timeout=30,
    )

    if resp.status_code not in (200, 201):
        print(f"✗ ({resp.status_code})")
        print(f"  Resposta: {resp.text[:300]}")
        sys.exit(1)

    print("ok")


def distribuir_documento(doc_id: int) -> dict:
    """Etapa 2 — instrui o Documenso a iniciar o fluxo de assinatura via e-mail."""
    print(f"  Iniciando fluxo de assinatura no Documenso...", end=" ", flush=True)

    resp = requests.post(
        f"{API_URL}/api/v2/document/distribute",
        headers={**headers(), "Content-Type": "application/json"},
        json={
            "documentId": doc_id,
            "meta": {
                "distributionMethod": "EMAIL",
                "timezone":   "America/Fortaleza",
                "dateFormat": "dd/MM/yyyy",
            },
        },
        timeout=30,
    )

    if resp.status_code not in (200, 201):
        print(f"✗ ({resp.status_code})")
        print(f"  Resposta: {resp.text[:300]}")
        sys.exit(1)

    resultado = resp.json()
    print("ok")
    return resultado


def status_documento(doc_id: int) -> str:
    """Consulta o status atual do documento via API v1 (compatível)."""
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
    parser = argparse.ArgumentParser(description="Envia contrato PDF para assinatura via Documenso v2")
    parser.add_argument("--pdf",    required=True, help="Caminho absoluto do PDF a enviar")
    parser.add_argument("--nome",   required=True, help="Nome completo do signatário (cliente)")
    parser.add_argument("--email",  required=True, help="E-mail do signatário (cliente)")
    parser.add_argument("--titulo", help="Título do documento no Documenso (padrão: gerado do nome do arquivo)")
    parser.add_argument("--cc",     help="E-mail para cópia (ex: copia@automacaosoftware.com.br)")
    parser.add_argument("--tipo",   choices=["licenca", "tef"], default=None,
                        help="Tipo do contrato — afeta posição Y dos campos de assinatura")
    parser.add_argument("--enviar", action="store_true", default=False,
                        help="Dispara o e-mail de assinatura imediatamente via Documenso. "
                             "Sem esta flag, o documento é criado como DRAFT.")
    parser.add_argument("--parceiro-nome",        help="Nome do representante do parceiro/revendedor")
    parser.add_argument("--parceiro-email",       help="E-mail do parceiro para assinatura eletrônica")
    parser.add_argument("--api-key-parceiro-env", default=None,
                        help="Nome da variável de ambiente com o token da equipe do parceiro no Documenso "
                             "(ex: DOCUMENSO_API_KEY_SOLUTIONTEC). Quando fornecido, o documento é criado "
                             "na equipe do parceiro.")
    args = parser.parse_args()

    checar_config()

    # Sobrescrever API_KEY com a da equipe do parceiro, se fornecida
    if args.api_key_parceiro_env:
        parceiro_key = os.getenv(args.api_key_parceiro_env)
        if not parceiro_key:
            print(f"✗ Variável {args.api_key_parceiro_env} não encontrada no .env")
            sys.exit(1)
        global API_KEY
        API_KEY = parceiro_key

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        print(f"✗ Arquivo não encontrado: {pdf_path}")
        sys.exit(1)

    # Validar parceiro — os dois campos são obrigatórios juntos
    tem_parceiro = bool(args.parceiro_nome or args.parceiro_email)
    if tem_parceiro and not (args.parceiro_nome and args.parceiro_email):
        print("✗ --parceiro-nome e --parceiro-email devem ser fornecidos juntos")
        sys.exit(1)

    def _fmt_cnpj(c: str) -> str:
        c = re.sub(r"\D", "", c)
        return f"{c[:2]}.{c[2:5]}.{c[5:8]}/{c[8:12]}-{c[12:14]}" if len(c) == 14 else c

    if args.titulo:
        titulo = args.titulo
    else:
        _m = re.match(r"CONTRATO_(?:LIC|TEF)_(.+)_(\d{14})$", pdf_path.stem)
        if _m:
            titulo = f"{_fmt_cnpj(_m.group(2))} - {args.nome} - {_m.group(1)}"
        else:
            titulo = pdf_path.stem.replace("_", " ")

    modo = "ENVIO AUTOMÁTICO (e-mail disparado)" if args.enviar else "DRAFT (envio manual pela plataforma)"
    print(f"\n── Documenso v2 — {modo} ─────────────────")
    print(f"  Arquivo   : {pdf_path.name}")
    print(f"  Signatário: {args.nome} <{args.email}>")
    if tem_parceiro:
        equipe_info = f" → equipe {args.api_key_parceiro_env}" if args.api_key_parceiro_env else ""
        print(f"  Parceiro  : {args.parceiro_nome} <{args.parceiro_email}>{equipe_info}")
    print(f"  Contratada: Automação Comercial LTDA. <eduardo@automacaosoftware.com.br>")
    print(f"  Título    : {titulo}")
    print(f"  Validade  : {ENVELOPE_EXPIRATION['amount']} {ENVELOPE_EXPIRATION['unit']}(s)")
    print(f"  Lembrete  : após {REMINDER_SETTINGS['sendAfter']['amount']} dia(s), "
          f"repetir a cada {REMINDER_SETTINGS['repeatEvery']['amount']} dia(s)")
    print(f"  Documenso : {API_URL}")
    print(f"────────────────────────────────────────────────────────\n")

    # Etapa 1 — criar documento + PDF + campos em uma única chamada
    doc = criar_documento_v2(
        titulo=titulo,
        nome=args.nome,
        email=args.email,
        email_cc=args.cc,
        pdf_path=pdf_path,
        tipo=args.tipo,
        parceiro_nome=args.parceiro_nome if tem_parceiro else None,
        parceiro_email=args.parceiro_email if tem_parceiro else None,
    )
    doc_id = doc["id"]

    # Etapa 1b — aplicar validade, lembretes e signingOrder SEQUENTIAL
    atualizar_documento(doc_id)

    # Etapa 2 — disparar e-mail (opcional)
    if args.enviar:
        distribuir_documento(doc_id)

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

    # Salvar referência local
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
