#!/usr/bin/env python3
"""
Merge terminal-server session stores (~/.claude-code-web/sessions.json) into one user.

The Node SessionStore uses os.homedir(); running the terminal-server as root writes
to /root/.claude-code-web/ while the evonexus service uses /home/evonexus/.claude-code-web/.
This script merges extra JSON files into the target user's file by session id (newer
lastActivity wins on conflict).

Usage (as root, so /root/.claude-code-web is readable):
  sudo python3 scripts/migrate_claude_code_web_sessions.py \\
    --target /home/evonexus/.claude-code-web/sessions.json \\
    --merge /root/.claude-code-web/sessions.json

Stop the terminal-server before running to avoid a race with its 30s autosave.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _parse_ts(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value) if value > 1e12 else float(value) * 1000
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
    except (TypeError, ValueError):
        return None


def _session_sort_key(s: dict[str, Any]) -> float:
    for key in ("lastActivity", "lastAccessed", "created"):
        t = _parse_ts(s.get(key))
        if t is not None:
            return t
    return 0.0


def load_store(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"version": "1.0", "savedAt": None, "sessions": []}
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict) or not isinstance(data.get("sessions"), list):
        raise SystemExit(f"Invalid sessions file format: {path}")
    data.setdefault("version", "1.0")
    return data


def merge_sessions(target: dict[str, Any], sources: list[Path]) -> dict[str, Any]:
    by_id: dict[str, dict[str, Any]] = {}
    order: list[str] = []

    def add_session(sess: dict[str, Any]) -> None:
        sid = sess.get("id")
        if not sid:
            return
        if sid not in by_id:
            by_id[sid] = dict(sess)
            order.append(sid)
            return
        existing = by_id[sid]
        if _session_sort_key(sess) >= _session_sort_key(existing):
            by_id[sid] = dict(sess)

    for s in target.get("sessions", []):
        if isinstance(s, dict):
            add_session(s)

    for src in sources:
        if not src.is_file():
            continue
        data = load_store(src)
        for s in data.get("sessions", []):
            if isinstance(s, dict):
                add_session(s)

    merged = {
        "version": "1.0",
        "savedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "sessions": [by_id[i] for i in order if i in by_id],
    }
    return merged


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    text = json.dumps(payload, indent=2, ensure_ascii=False)
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--target",
        type=Path,
        default=Path("/home/evonexus/.claude-code-web/sessions.json"),
        help="Destination sessions.json (default: evonexus)",
    )
    ap.add_argument(
        "--merge",
        type=Path,
        action="append",
        default=[],
        help="Additional sessions.json to merge (repeatable). Default: /root if exists.",
    )
    ap.add_argument(
        "--chown-uid",
        type=int,
        default=None,
        help="chown target file to this uid after write (default: owner of target parent home)",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Print counts only; do not write",
    )
    args = ap.parse_args()

    merge_paths = list(args.merge)
    root_sessions = Path("/root/.claude-code-web/sessions.json")
    if root_sessions.is_file() and root_sessions.resolve() != args.target.resolve():
        if root_sessions not in merge_paths and not args.merge:
            merge_paths.append(root_sessions)

    target_data = load_store(args.target)
    before_tgt = len(target_data.get("sessions", []))

    merged = merge_sessions(target_data, merge_paths)
    after = len(merged["sessions"])

    print(f"Target before: {before_tgt} sessions")
    for p in merge_paths:
        if p.is_file():
            n = len(load_store(p).get("sessions", []))
            print(f"  merge from {p}: {n} sessions")
        else:
            print(f"  skip missing {p}")
    print(f"Merged total: {after} sessions (dedupe by id)")

    if args.dry_run:
        return

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if args.target.is_file():
        bak = args.target.with_suffix(args.target.suffix + f".bak.{ts}")
        shutil.copy2(args.target, bak)
        print(f"Backup: {bak}")

    atomic_write_json(args.target, merged)

    uid = args.chown_uid
    gid = None
    if uid is None and args.target.parent.name == ".claude-code-web":
        home = args.target.parent.parent
        try:
            st = home.stat()
            uid, gid = st.st_uid, st.st_gid
        except OSError:
            pass
    if uid is not None:
        os.chown(args.target, uid, gid if gid is not None else uid)
        print(f"chown {uid}:{gid if gid is not None else uid} {args.target}")


if __name__ == "__main__":
    main()
