#!/usr/bin/env python3
"""
memory-extract-hook.py — SubagentStop hook handler.

Responsabilidade: ler payload do stdin, validar escopo, enfileirar job,
disparar extrator em background, sair em < 500ms. Fail-open sempre.
"""

import json
import os
import sys
import subprocess
from datetime import datetime, timezone
from pathlib import Path

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

def main():
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            sys.exit(0)

        payload = json.loads(raw)
        transcript_path = payload.get("transcript_path", "")
        session_id = payload.get("session_id", "")

        if not transcript_path or not session_id:
            sys.exit(0)

        transcript_file = Path(transcript_path)
        if not transcript_file.exists():
            sys.exit(0)

        # Ler primeira linha para extrair agentSetting (slug)
        slug = None
        try:
            with open(transcript_file, "r", encoding="utf-8", errors="replace") as f:
                first_line = f.readline().strip()
            if first_line:
                first_obj = json.loads(first_line)
                slug = first_obj.get("agentSetting")
        except Exception:
            pass

        if not slug or slug not in SCOPE_AGENTS:
            sys.exit(0)

        # Resolver PROJECT_DIR
        project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
        if not project_dir:
            project_dir = str(Path(__file__).resolve().parent.parent.parent)

        project_dir = Path(project_dir)

        # Criar diretório da fila se não existir
        queue_dir = project_dir / "ADWs" / "logs" / "memory-queue"
        queue_dir.mkdir(parents=True, exist_ok=True)

        # Gravar job
        job_file = queue_dir / f"{session_id}.json"
        job = {
            "slug": slug,
            "transcript_path": str(transcript_path),
            "session_id": session_id,
            "queued_at": datetime.now(timezone.utc).isoformat(),
            "status": "pending",
        }
        job_tmp = job_file.with_suffix(".tmp")
        job_tmp.write_text(json.dumps(job, indent=2), encoding="utf-8")
        job_tmp.rename(job_file)

        # Disparar extrator em background (detached)
        extractor = project_dir / "ADWs" / "routines" / "agent_memory_extract.py"
        log_file = project_dir / "ADWs" / "logs" / "memory-extract.log"

        with open(log_file, "a") as log_fh:
            subprocess.Popen(
                [sys.executable, str(extractor), "--job", str(job_file)],
                stdout=log_fh,
                stderr=log_fh,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
            )

    except Exception:
        # Fail-open: nunca propagar exceção para o hook
        pass

    sys.exit(0)


if __name__ == "__main__":
    main()
