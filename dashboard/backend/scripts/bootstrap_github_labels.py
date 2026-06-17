#!/usr/bin/env python3
"""
Bootstrap de labels de status e prioridade nos 12 repos do go-control.
Idempotente: status 422 (already_exists) é tratado como sucesso.

Uso: python bootstrap_github_labels.py
"""
import sys
import os
from pathlib import Path

# Resolver path para poder importar github_issues
_backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_backend_dir))

from github_issues import REPOS_ALLOWLIST, _post, _token  # noqa: E402

LABELS = [
    {"name": "status:in-progress", "color": "0075ca", "description": "Em andamento"},
    {"name": "status:blocked",     "color": "d93f0b", "description": "Bloqueado"},
    {"name": "status:review",      "color": "e4e669", "description": "Em revisão"},
    {"name": "priority:urgent",    "color": "b60205", "description": "Urgente"},
    {"name": "priority:high",      "color": "d93f0b", "description": "Alta prioridade"},
    {"name": "priority:medium",    "color": "f9d0c4", "description": "Média prioridade"},
    {"name": "priority:low",       "color": "c2e0c6", "description": "Baixa prioridade"},
]


def main() -> None:
    # Garantir que o token existe antes de iniciar
    try:
        _token()
    except RuntimeError as exc:
        print(f"ERRO: {exc}")
        sys.exit(1)

    total = ok = already = errors = 0
    for repo in sorted(REPOS_ALLOWLIST):
        for label in LABELS:
            total += 1
            url = f"https://api.github.com/repos/{repo}/labels"
            status, body = _post(url, {
                "name": label["name"],
                "color": label["color"],
                "description": label["description"],
            })
            if status == 201:
                ok += 1
                print(f"[OK] {repo} → {label['name']}")
            elif status == 422:
                already += 1
                print(f"[already_exists] {repo} → {label['name']}")
            else:
                errors += 1
                print(f"[ERROR {status}] {repo} → {label['name']} — {body}")

    print(f"\nTotal: {total} | OK: {ok} | already_exists: {already} | errors: {errors}")
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
