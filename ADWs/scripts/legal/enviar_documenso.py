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
import fitz  # PyMuPDF
from dotenv import load_dotenv

# ── Config ────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parents[3]   # evo-nexus/
load_dotenv(BASE_DIR / ".env")

API_URL = os.getenv("DOCUMENSO_API_URL", "https://signature.automacaosoftware.com.br")
API_KEY = os.getenv("DOCUMENSO_API_KEY", "")


# ── Helpers ───────────────────────────────────────────────────────────────────
def headers() -> dict:
    return {"Authorization": f"Bearer {API_KEY}"}


def pagina_anexo_iii_pdf(pdf_path: Path) -> int | None:
    """Detecta a página do Anexo III buscando 'Anexo III' no texto.
    Retorna o número da página (1-based) ou None se o anexo não existir no PDF.
    """
    doc = fitz.open(str(pdf_path))
    for i in range(doc.page_count):
        if "Anexo III" in doc[i].get_text():
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

    Assinatura SEQUENCIAL:
      Com parceiro   : PARCEIRO (1) → CONTRATANTE (2) → CONTRATADA (3)
      Sem parceiro   : CONTRATANTE (1) → CONTRATADA (2)

    Índices em doc['recipients']:
      [0] PARCEIRO (se houver) ou CONTRATANTE
      [1] CONTRATANTE (se houver parceiro) ou CONTRATADA
      [-1] CONTRATADA (sempre o último SIGNER)
    """
    print(f"  Criando documento no Documenso...", end=" ", flush=True)

    tem_parceiro = bool(parceiro_nome and parceiro_email)

    if tem_parceiro:
        recipients = [
            {"name": parceiro_nome,                    "email": parceiro_email,                    "role": "SIGNER", "signingOrder": 1},
            {"name": nome,                             "email": email,                             "role": "SIGNER", "signingOrder": 2},
            {**ASSINANTE_CONTRATADA,                                                                                  "signingOrder": 3},
        ]
    else:
        recipients = [
            {"name": nome,                             "email": email,                             "role": "SIGNER", "signingOrder": 1},
            {**ASSINANTE_CONTRATADA,                                                                                  "signingOrder": 2},
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
                               pagina: int = 1,
                               recipient_parceiro_id: int | None = None) -> None:
    """Etapa 2b — adiciona campos de assinatura na página dedicada (última página).

    A página de assinaturas é sempre uma página nova isolada (page-break-before no template),
    portanto as coordenadas são fixas independente do tamanho do contrato:

    - CONTRATADA (Automação) → esquerda, y=22%
    - CONTRATANTE (cliente)  → direita,  y=22%
    - PARCEIRO (testemunha)  → esquerda, y=55%  (se houver)

    Coordenadas em % da página (0–100).
    """
    tem_parceiro = recipient_parceiro_id is not None
    info = f"pág. {pagina} (dedicada)" + (", +parceiro" if tem_parceiro else "")
    print(f"  Adicionando campos de assinatura ({info})...", end=" ", flush=True)

    campos = [
        # CONTRATADA — lado esquerdo, y=22%
        {
            "recipientId": recipient_contratada_id,
            "type":        "SIGNATURE",
            "pageNumber":  pagina,
            "pageX":       5,
            "pageY":       22,
            "pageWidth":   38,
            "pageHeight":  7,
        },
        # CONTRATANTE — lado direito, y=22%
        {
            "recipientId": recipient_cliente_id,
            "type":        "SIGNATURE",
            "pageNumber":  pagina,
            "pageX":       55,
            "pageY":       22,
            "pageWidth":   38,
            "pageHeight":  7,
        },
    ]

    # PARCEIRO — testemunha 1, linha abaixo das partes
    if tem_parceiro:
        campos.append({
            "recipientId": recipient_parceiro_id,
            "type":        "SIGNATURE",
            "pageNumber":  pagina,
            "pageX":       5,
            "pageY":       55,
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

    partes_info = "contratada=esquerda, cliente=direita"
    if tem_parceiro:
        partes_info += ", parceiro=testemunha y=55%"
    print(f"ok ({partes_info})")


def adicionar_campos_texto_contato(doc_id: int, recipient_cliente_id: int,
                                   pdf_path: Path, pagina: int) -> None:
    """Adiciona campos TEXT na página do Anexo III para o CONTRATANTE preencher
    Nome/Telefone/E-mail de Adm-Financeiro, Contador e TI durante a assinatura.

    Usa PyMuPDF para detectar a posição Y de cada label na coluna esquerda da
    tabela e posiciona o campo TEXT na coluna direita (~50% a 93% de largura).
    """
    labels_pos = posicoes_labels_pdf(pdf_path, pagina)

    if not labels_pos:
        # Fallback: posições estimadas para A4 com margens padrão do template
        labels_pos = [
            (20.0, "Nome"), (24.0, "Telefone"), (28.0, "E-mail"),   # Adm/Fin
            (46.0, "Nome"), (50.0, "Telefone"), (54.0, "E-mail"),   # Contador
            (68.0, "Nome"), (72.0, "Telefone"), (76.0, "E-mail"),   # TI
        ]
        print(f"  (labels não detectados — usando posições estimadas)")

    n_secoes = ["Adm/Fin", "Contador", "TI"]
    # Agrupar: primeiros 3 resultados de cada label → indexar por ordem Y
    # A lista já está ordenada por Y, então as 3 primeiras ocorrências de 'Nome'
    # correspondem a Adm/Fin, Contador, TI respectivamente.
    info_txt = f"pág. {pagina}, {len(labels_pos)} campos"
    print(f"  Adicionando campos TEXT — Contatos Administrativos ({info_txt})...", end=" ", flush=True)

    for y_pct, label in labels_pos:
        campo = {
            "recipientId": recipient_cliente_id,
            "type":        "TEXT",
            "pageNumber":  pagina,
            "pageX":       50,       # coluna direita da tabela (~50–93%)
            "pageY":       y_pct,
            "pageWidth":   43,
            "pageHeight":  3,
        }
        resp = requests.post(
            f"{API_URL}/api/v1/documents/{doc_id}/fields",
            headers={**headers(), "Content-Type": "application/json"},
            json=campo,
            timeout=30,
        )
        if resp.status_code not in (200, 201):
            print(f"✗ ({resp.status_code}) — {resp.text[:200]}")
            sys.exit(1)

    print("ok")


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
    parser.add_argument("--tipo",                choices=["licenca", "tef"], default=None,
                        help="Tipo do contrato (informativo — página de assinatura detectada automaticamente)")
    parser.add_argument("--enviar",              action="store_true", default=False,
                        help="Dispara o e-mail de assinatura imediatamente via Documenso. "
                             "Sem esta flag, o documento é criado como DRAFT e o envio "
                             "deve ser feito manualmente pela plataforma.")
    # Parceiro/revendedor (opcionais — ambos obrigatórios se um for fornecido)
    parser.add_argument("--parceiro-nome",       help="Nome do representante do parceiro/revendedor")
    parser.add_argument("--parceiro-email",      help="E-mail do parceiro para assinatura eletrônica")
    parser.add_argument("--api-key-parceiro-env", default=None,
                        help="Nome da variável de ambiente com o token da equipe do parceiro no Documenso "
                             "(ex: DOCUMENSO_API_KEY_INFORCELL). Quando fornecido, o documento é criado "
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

    titulo = args.titulo or pdf_path.stem.replace("_", " ")

    modo = "ENVIO AUTOMÁTICO (e-mail disparado)" if args.enviar else "DRAFT (envio manual pela plataforma)"
    print(f"\n── Documenso — {modo} ─────────────────")
    print(f"  Arquivo   : {pdf_path.name}")
    print(f"  Signatário: {args.nome} <{args.email}>")
    if tem_parceiro:
        equipe_info = f" → equipe {args.api_key_parceiro_env}" if args.api_key_parceiro_env else ""
        print(f"  Parceiro  : {args.parceiro_nome} <{args.parceiro_email}>{equipe_info}")
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
    # Detecta a página de assinaturas pelo texto âncora no PDF
    pagina = pagina_assinaturas_pdf(pdf_path)
    print(f"  Página de assinaturas detectada: {pagina}")

    # Índices dependem da presença do parceiro — assinatura sequencial:
    # Com parceiro   : [0]=PARCEIRO (ordem 1), [1]=CONTRATANTE (ordem 2), [-1]=CONTRATADA (ordem 3)
    # Sem parceiro   : [0]=CONTRATANTE (ordem 1), [-1]=CONTRATADA (ordem 2)
    recipients = doc["recipients"]
    signers = [r for r in recipients if r.get("role") == "SIGNER"]

    if tem_parceiro:
        recipient_parceiro_id   = signers[0]["recipientId"]   # PARCEIRO    (ordem 1)
        recipient_cliente_id    = signers[1]["recipientId"]   # CONTRATANTE (ordem 2)
        recipient_contratada_id = signers[2]["recipientId"]   # CONTRATADA  (ordem 3)
    else:
        recipient_parceiro_id   = None
        recipient_cliente_id    = signers[0]["recipientId"]   # CONTRATANTE (ordem 1)
        recipient_contratada_id = signers[1]["recipientId"]   # CONTRATADA  (ordem 2)

    adicionar_campo_assinatura(doc_id, recipient_cliente_id,
                               recipient_contratada_id, pagina=pagina,
                               recipient_parceiro_id=recipient_parceiro_id)

    # Etapa 2c — campos TEXT para Contatos Administrativos (Anexo III, se existir)
    pagina_iii = pagina_anexo_iii_pdf(pdf_path)
    if pagina_iii:
        adicionar_campos_texto_contato(doc_id, recipient_cliente_id, pdf_path, pagina_iii)
    else:
        print("  Anexo III não encontrado — campos de contato não adicionados")

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
