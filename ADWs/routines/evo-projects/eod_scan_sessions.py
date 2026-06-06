#!/usr/bin/env python3
"""
eod_scan_sessions.py — Varre as sessões Claude Code do dia e produz um mapa de agentes ativos.

Retorno (stdout JSON):
{
  "date": "2026-06-05",
  "sessions_total": 12,
  "agents": {
    "bolt-executor": {
      "session_ids": ["abc", "def"],
      "transcript_paths": ["/home/evonexus/.claude/projects/.../abc.jsonl"],
      "has_memory_today": false
    },
    ...
  },
  "agents_out_of_scope": ["oracle", "compass-planner"]
}

Uso:
  python3 eod_scan_sessions.py
  python3 eod_scan_sessions.py --date 2026-06-04   # data específica (para testes)
"""

import argparse
import json
import os
import sys
from datetime import datetime, date, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

SESSIONS_DIR = Path("/home/evonexus/.claude/projects/-home-evonexus-evo-nexus")

PROJECT_DIR = Path(os.environ.get("CLAUDE_PROJECT_DIR", "")).resolve()
if not PROJECT_DIR or not PROJECT_DIR.exists():
    PROJECT_DIR = Path(__file__).resolve().parent.parent.parent

MEMORY_BASE = PROJECT_DIR / ".claude" / "agent-memory"

SCOPE_AGENTS = {
    "bolt-executor",
    "apex-architect",
    "hawk-debugger",
    "lens-reviewer",
    "grid-tester",
    "flow-git",
    "oath-verifier",
    "clawdia-assistant",
    "flux-finance",
    "atlas-project",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_agent_slug(jsonl_path: Path) -> str | None:
    """
    Lê a primeira linha do JSONL e extrai agentSetting.
    Retorna None se não encontrado ou erro de parse.
    """
    try:
        with open(jsonl_path, "r", encoding="utf-8", errors="replace") as f:
            first_line = f.readline().strip()
        if not first_line:
            return None
        obj = json.loads(first_line)
        if obj.get("type") == "agent-setting":
            slug = obj.get("agentSetting", "")
            return slug if slug else None
    except Exception:
        pass
    return None


def _has_memory_today(slug: str, target_date: date) -> bool:
    """
    Retorna True se existe algum arquivo em .claude/agent-memory/{slug}/
    com mtime >= hoje 00:00 (horário local).
    """
    agent_dir = MEMORY_BASE / slug
    if not agent_dir.is_dir():
        return False

    today_start = datetime.combine(target_date, datetime.min.time()).timestamp()

    try:
        for entry in agent_dir.iterdir():
            if entry.is_file():
                try:
                    if entry.stat().st_mtime >= today_start:
                        return True
                except OSError:
                    pass
    except OSError:
        pass

    return False


def _file_mtime_date(path: Path) -> date | None:
    """Retorna a data local do mtime do arquivo."""
    try:
        ts = path.stat().st_mtime
        return datetime.fromtimestamp(ts).date()
    except OSError:
        return None


# ---------------------------------------------------------------------------
# Scan principal
# ---------------------------------------------------------------------------

def scan(target_date: date) -> dict:
    """
    Varre as sessões do dia e retorna o mapa de agentes.
    Fail-open: qualquer erro parcial é silenciado, estrutura vazia retornada em erro total.
    """
    result = {
        "date": target_date.isoformat(),
        "sessions_total": 0,
        "agents": {},
        "agents_out_of_scope": [],
    }

    if not SESSIONS_DIR.is_dir():
        print(
            f"[eod_scan_sessions] SESSIONS_DIR not found: {SESSIONS_DIR}",
            file=sys.stderr,
        )
        return result

    # Listar arquivos JSONL com mtime de hoje
    today_files: list[Path] = []
    try:
        for path in SESSIONS_DIR.glob("*.jsonl"):
            if _file_mtime_date(path) == target_date:
                today_files.append(path)
    except Exception as e:
        print(f"[eod_scan_sessions] error listing sessions: {e}", file=sys.stderr)
        return result

    result["sessions_total"] = len(today_files)

    # Mapear slug → {session_ids, transcript_paths}
    slug_map: dict[str, dict] = {}
    out_of_scope_set: set[str] = set()

    for path in today_files:
        slug = _parse_agent_slug(path)
        if slug is None:
            continue

        session_id = path.stem  # nome do arquivo sem .jsonl

        if slug not in slug_map:
            slug_map[slug] = {
                "session_ids": [],
                "transcript_paths": [],
                "has_memory_today": False,
            }
        slug_map[slug]["session_ids"].append(session_id)
        slug_map[slug]["transcript_paths"].append(str(path))

    # Separar in-scope vs out-of-scope; preencher has_memory_today
    for slug, data in slug_map.items():
        if slug in SCOPE_AGENTS:
            data["has_memory_today"] = _has_memory_today(slug, target_date)
            result["agents"][slug] = data
        else:
            out_of_scope_set.add(slug)

    result["agents_out_of_scope"] = sorted(out_of_scope_set)

    return result


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Scan Claude Code sessions for EOD memory coverage report"
    )
    parser.add_argument(
        "--date",
        help="Target date YYYY-MM-DD (default: today)",
        default=None,
    )
    args = parser.parse_args()

    if args.date:
        try:
            target_date = date.fromisoformat(args.date)
        except ValueError as e:
            print(f"[eod_scan_sessions] invalid date: {e}", file=sys.stderr)
            # Fail-open: usar hoje
            target_date = date.today()
    else:
        target_date = date.today()

    try:
        result = scan(target_date)
    except Exception as e:
        print(f"[eod_scan_sessions] unexpected error: {e}", file=sys.stderr)
        result = {
            "date": target_date.isoformat(),
            "sessions_total": 0,
            "agents": {},
            "agents_out_of_scope": [],
        }

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
