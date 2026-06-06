#!/usr/bin/env python3
"""
agent_memory_extract.py — Extrator de memória de sub-agentes.

Interface:
  python3 agent_memory_extract.py --job /path/to/job.json
  python3 agent_memory_extract.py --slug bolt-executor --transcript /path/to/transcript.jsonl
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

PROJECT_DIR = Path(os.environ.get("CLAUDE_PROJECT_DIR", "")).resolve()
if not PROJECT_DIR or not PROJECT_DIR.exists():
    PROJECT_DIR = Path(__file__).resolve().parent.parent.parent

MEMORY_BASE = PROJECT_DIR / ".claude" / "agent-memory"
LOG_FILE = PROJECT_DIR / "ADWs" / "logs" / "memory-extract.log"

# Tokens aproximados (~4 chars/token) — teto de ~6000 tokens
MAX_TRANSCRIPT_CHARS = 24_000

# Padrões de segredo para redigir
SECRET_PATTERNS = [
    re.compile(r"(sk-[A-Za-z0-9_\-]{20,})", re.IGNORECASE),
    re.compile(r"(ghp_[A-Za-z0-9]{36,})", re.IGNORECASE),
    re.compile(r"(Bearer\s+[A-Za-z0-9\-._~+/]{20,})", re.IGNORECASE),
    re.compile(r"(ANTHROPIC_API_KEY\s*[=:]\s*\S+)", re.IGNORECASE),
    re.compile(r"(OPENAI_API_KEY\s*[=:]\s*\S+)", re.IGNORECASE),
    re.compile(r"(password\s*[=:]\s*\S+)", re.IGNORECASE),
    re.compile(r"(token\s*[=:]\s*['\"]?[A-Za-z0-9_\-]{20,}['\"]?)", re.IGNORECASE),
]

EXTRACTION_PROMPT = """Você é um extrator de memória para o agente {slug} do EvoNexus.

Analise a conversa abaixo e extraia SOMENTE fatos que devem persistir entre sessões.

TIPOS DE MEMÓRIA:
- feedback: correções de approach, confirmações de padrão ("não fazer X", "sempre usar Y")
- project: decisões de projeto, gotchas descobertos, padrões validados de arquitetura/implementação
- user: contexto sobre o usuário que muda como o agente colabora
- reference: ponteiros para recursos externos (Linear, docs, dashboards)

NÃO EXTRAIR: código, git history, fix recipes, estado efêmero, conteúdo de CLAUDE.md, segredos.

CRITÉRIO: só extrair se for não-óbvio e reutilizável em sessões futuras.

Responda SOMENTE com JSON válido, nenhum texto fora do JSON:
[
  {{
    "name": "kebab-case-slug",
    "description": "uma linha, máx 150 chars, específico o suficiente para decidir relevância",
    "type": "feedback|project|user|reference",
    "body": "conteúdo em markdown. Para feedback/project: incluir linha **Why:** e **How to apply:**"
  }}
]

Se não houver nada relevante, responda: []

CONVERSA:
{transcript_text}"""


# ---------------------------------------------------------------------------
# Utilitários
# ---------------------------------------------------------------------------

def _log(record: dict):
    """Acrescenta linha JSONL ao log central."""
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _update_job(job_file: Path, status: str):
    """Atualiza status do job atomicamente."""
    try:
        job = json.loads(job_file.read_text(encoding="utf-8"))
        job["status"] = status
        job["updated_at"] = datetime.now(timezone.utc).isoformat()
        tmp = job_file.with_suffix(".tmp")
        tmp.write_text(json.dumps(job, indent=2), encoding="utf-8")
        tmp.rename(job_file)
    except Exception:
        pass


def _redact_secrets(text: str) -> str:
    """Substitui valores de segredos por [REDACTED]."""
    for pattern in SECRET_PATTERNS:
        text = pattern.sub("[REDACTED]", text)
    return text


# ---------------------------------------------------------------------------
# Leitura do transcript
# ---------------------------------------------------------------------------

def _read_transcript(transcript_path: Path) -> str:
    """
    Lê o JSONL do Claude Code e extrai mensagens assistant/user legíveis.
    Retorna string de no máximo MAX_TRANSCRIPT_CHARS chars.
    """
    lines_text = []
    try:
        with open(transcript_path, "r", encoding="utf-8", errors="replace") as f:
            for raw_line in f:
                raw_line = raw_line.strip()
                if not raw_line:
                    continue
                try:
                    obj = json.loads(raw_line)
                except json.JSONDecodeError:
                    continue

                # Tipos relevantes: mensagens de conversa
                msg_type = obj.get("type", "")
                role = obj.get("role", "")

                if msg_type == "message" or role in ("assistant", "user"):
                    content = obj.get("content", "")
                    if isinstance(content, list):
                        # Array de blocos — extrair texto
                        parts = []
                        for block in content:
                            if isinstance(block, dict):
                                btype = block.get("type", "")
                                if btype == "text":
                                    parts.append(block.get("text", ""))
                                # Ignorar tool_use, tool_result, image
                        content = "\n".join(parts)
                    if isinstance(content, str) and content.strip():
                        speaker = role or "unknown"
                        lines_text.append(f"[{speaker.upper()}]: {content.strip()}")

    except Exception:
        pass

    full_text = "\n\n".join(lines_text)

    # Truncar mantendo início e fim se passar do limite
    if len(full_text) > MAX_TRANSCRIPT_CHARS:
        half = MAX_TRANSCRIPT_CHARS // 2 - 200
        beginning = full_text[:half]
        ending = full_text[-half:]
        full_text = beginning + "\n\n[... TRANSCRIPT TRUNCADO ...]\n\n" + ending

    return full_text


# ---------------------------------------------------------------------------
# Chamada ao modelo
# ---------------------------------------------------------------------------

def _call_model(slug: str, transcript_text: str) -> list:
    """Chama Claude Haiku via CLI e retorna lista de entradas de memória."""
    redacted = _redact_secrets(transcript_text)
    prompt = EXTRACTION_PROMPT.format(slug=slug, transcript_text=redacted)

    try:
        result = subprocess.run(
            [
                "claude",
                "--model", "claude-haiku-4-5",
                "--max-turns", "1",
                "--output-format", "text",
                "-p", prompt,
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError("model call timed out after 60s")
    except FileNotFoundError:
        raise RuntimeError("claude CLI not found in PATH")

    output = result.stdout.strip()
    if not output:
        return []

    # Extrair JSON da resposta (pode ter texto antes/depois)
    # Tentar encontrar array JSON diretamente
    json_match = re.search(r"\[.*\]", output, re.DOTALL)
    if not json_match:
        if output.strip() == "[]":
            return []
        raise RuntimeError(f"no JSON array found in model output: {output[:200]!r}")

    entries = json.loads(json_match.group())
    if not isinstance(entries, list):
        raise RuntimeError("model returned non-list JSON")

    return entries


# ---------------------------------------------------------------------------
# Deduplicação
# ---------------------------------------------------------------------------

def _load_existing_memory(slug: str) -> tuple[list[str], list[str]]:
    """
    Lê MEMORY.md e retorna (names, descriptions) já registrados.
    """
    memory_md = MEMORY_BASE / slug / "MEMORY.md"
    names = []
    descriptions = []
    if not memory_md.exists():
        return names, descriptions

    content = memory_md.read_text(encoding="utf-8")
    for line in content.splitlines():
        # Linha de entrada: `- [description](filename.md) — ...`
        m = re.match(r"^\s*-\s+\[([^\]]+)\]\(([^)]+)\)", line)
        if m:
            descriptions.append(m.group(1).lower())
            # Extrair name do filename: type_name.md → name
            fname = m.group(2)
            if "_" in fname:
                name_part = fname.rsplit(".", 1)[0]  # remove .md
                name_part = re.sub(r"^[a-z]+_", "", name_part)  # remove type_
                names.append(name_part.lower())

    return names, descriptions


def _is_duplicate(entry: dict, existing_names: list[str], existing_descriptions: list[str]) -> bool:
    name = entry.get("name", "").lower()
    description = entry.get("description", "").lower()

    if name in existing_names:
        return True

    # Verificar substring bidirecional de description
    for existing_desc in existing_descriptions:
        if description and existing_desc:
            if description in existing_desc or existing_desc in description:
                return True

    return False


# ---------------------------------------------------------------------------
# Escrita atômica
# ---------------------------------------------------------------------------

def _write_entry(slug: str, entry: dict) -> bool:
    """
    Escreve arquivo de memória e atualiza MEMORY.md atomicamente.
    Retorna True se escreveu, False se entrada inválida.
    """
    name = entry.get("name", "").strip()
    description = entry.get("description", "").strip()
    mem_type = entry.get("type", "").strip()
    body = entry.get("body", "").strip()

    # Validar campos obrigatórios
    if not name or not description or not mem_type or not body:
        return False

    valid_types = {"feedback", "project", "user", "reference"}
    if mem_type not in valid_types:
        return False

    # Sanitizar name para uso em filename
    safe_name = re.sub(r"[^a-z0-9\-]", "-", name.lower())
    safe_name = re.sub(r"-+", "-", safe_name).strip("-")
    if not safe_name:
        return False

    agent_dir = MEMORY_BASE / slug
    agent_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{mem_type}_{safe_name}.md"
    mem_file = agent_dir / filename

    # Conteúdo do arquivo de memória
    file_content = f"""---
name: {safe_name}
description: {description}
metadata:
  type: {mem_type}
---

{body}
"""

    # Escrita atômica do arquivo de memória
    tmp_mem = mem_file.with_suffix(".tmp")
    tmp_mem.write_text(file_content, encoding="utf-8")
    tmp_mem.rename(mem_file)

    # Atualizar MEMORY.md
    memory_md = agent_dir / "MEMORY.md"
    if not memory_md.exists():
        memory_md.write_text("# Memory Index\n\n", encoding="utf-8")

    # Truncar description para linha do índice
    index_desc = description[:100] + ("..." if len(description) > 100 else "")
    new_line = f"- [{description}]({filename}) — {index_desc}\n"

    # Escrita atômica do MEMORY.md (append)
    existing = memory_md.read_text(encoding="utf-8")
    updated = existing.rstrip("\n") + "\n" + new_line

    tmp_md = memory_md.with_suffix(".tmp")
    tmp_md.write_text(updated, encoding="utf-8")
    tmp_md.rename(memory_md)

    return True


# ---------------------------------------------------------------------------
# Fluxo principal
# ---------------------------------------------------------------------------

def extract(slug: str, transcript_path: Path, session_id: str, job_file: Path | None = None):
    ts = datetime.now(timezone.utc).isoformat()
    log_record = {
        "ts": ts,
        "slug": slug,
        "session_id": session_id,
        "entries_extracted": 0,
        "entries_skipped_dedup": 0,
        "status": "pending",
    }

    try:
        # Leitura do transcript
        transcript_text = _read_transcript(transcript_path)

        if not transcript_text.strip():
            log_record["status"] = "ok"
            log_record["entries_extracted"] = 0
            _log(log_record)
            if job_file:
                _update_job(job_file, "done")
            return

        # Chamada ao modelo
        entries = _call_model(slug, transcript_text)

        if not entries:
            log_record["status"] = "ok"
            log_record["entries_extracted"] = 0
            _log(log_record)
            if job_file:
                _update_job(job_file, "done")
            return

        # Deduplicação
        existing_names, existing_descriptions = _load_existing_memory(slug)
        written = 0
        skipped = 0

        for entry in entries:
            if _is_duplicate(entry, existing_names, existing_descriptions):
                skipped += 1
                continue

            if _write_entry(slug, entry):
                written += 1
                # Atualizar listas de dedup para evitar duplicatas dentro do mesmo batch
                name = entry.get("name", "").lower()
                description = entry.get("description", "").lower()
                existing_names.append(name)
                existing_descriptions.append(description)
            else:
                skipped += 1

        log_record["entries_extracted"] = written
        log_record["entries_skipped_dedup"] = skipped
        log_record["status"] = "ok"
        _log(log_record)

        if job_file:
            _update_job(job_file, "done")

    except Exception as e:
        log_record["status"] = "failed"
        log_record["error"] = str(e)[:500]
        _log(log_record)
        if job_file:
            _update_job(job_file, "failed")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Agent memory extractor")
    parser.add_argument("--job", help="Path to job JSON file")
    parser.add_argument("--slug", help="Agent slug (direct mode)")
    parser.add_argument("--transcript", help="Path to transcript JSONL (direct mode)")
    args = parser.parse_args()

    if args.job:
        job_file = Path(args.job)
        try:
            job = json.loads(job_file.read_text(encoding="utf-8"))
        except Exception:
            sys.exit(0)

        slug = job.get("slug", "")
        transcript_path = Path(job.get("transcript_path", ""))
        session_id = job.get("session_id", "")

        if not slug or not transcript_path or not session_id:
            sys.exit(0)

        if not transcript_path.exists():
            _update_job(job_file, "failed")
            sys.exit(0)

        extract(slug, transcript_path, session_id, job_file)

    elif args.slug and args.transcript:
        transcript_path = Path(args.transcript)
        session_id = transcript_path.stem  # usar nome do arquivo como session_id

        if not transcript_path.exists():
            sys.exit(0)

        extract(args.slug, transcript_path, session_id, job_file=None)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
