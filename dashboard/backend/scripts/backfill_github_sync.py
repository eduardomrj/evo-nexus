#!/usr/bin/env python3
"""
Backfill retroativo: sincroniza tickets com github_repo configurado que ainda não
possuem uma entrada em ticket_github_links.

Uso: python backfill_github_sync.py [--dry-run]

Output por linha:
  [OK]  ticket_id → repo#N
  [DRY] ticket_id → repo
  [ERR] ticket_id → mensagem de erro

Idempotente: se rodar de novo com links já existentes, reporta "0 tickets elegíveis".
"""
import sys
import os
import time
import argparse
from pathlib import Path

# Resolver path para poder importar módulos do backend
_backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_backend_dir))

# Carregar .env
try:
    from dotenv import load_dotenv as _load_dotenv
    _load_dotenv(Path(__file__).resolve().parent.parent.parent.parent / ".env")
except ImportError:
    pass

# Importar o app para ter contexto Flask + banco
from app import app  # noqa: E402
from models import db, Ticket, TicketGithubLink  # noqa: E402


def _find_eligible_tickets():
    """Retorna tickets com github_repo definido e sem TicketGithubLink correspondente."""
    rows = db.session.execute(db.text("""
        SELECT t.id, t.github_repo
        FROM tickets t
        WHERE t.github_repo IS NOT NULL
          AND t.github_repo != ''
          AND NOT EXISTS (
              SELECT 1 FROM ticket_github_links tgl
              WHERE tgl.ticket_id = t.id
          )
        ORDER BY t.created_at ASC
    """)).fetchall()
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill retroativo GitHub sync")
    parser.add_argument("--dry-run", action="store_true", help="Listar tickets sem sincronizar")
    args = parser.parse_args()

    dry_run = args.dry_run

    with app.app_context():
        eligible = _find_eligible_tickets()

        if not eligible:
            print("0 tickets elegíveis — nada a sincronizar.")
            return

        print(f"{'[DRY-RUN] ' if dry_run else ''}Encontrados {len(eligible)} ticket(s) elegível(is).")

        ok = errors = skipped = 0

        for ticket_id, github_repo in eligible:
            if dry_run:
                print(f"[DRY] {ticket_id} → {github_repo}")
                skipped += 1
                continue

            try:
                from github_issues import sync_ticket_to_github
                sync_ticket_to_github(ticket_id)

                # Verificar se o link foi criado e obter o issue_number
                link = TicketGithubLink.query.filter_by(ticket_id=ticket_id).first()
                if link and link.issue_number:
                    print(f"[OK] {ticket_id} → {github_repo}#{link.issue_number}", flush=True)
                else:
                    print(f"[OK] {ticket_id} → {github_repo} (sem issue_number ainda)", flush=True)
                ok += 1

            except Exception as exc:
                print(f"[ERR] {ticket_id} → {exc}", flush=True)
                errors += 1

            # Rate-limit entre chamadas
            time.sleep(0.5)

        print(f"\nResumo: OK={ok} | DRY={skipped} | ERR={errors}")
        if errors:
            sys.exit(1)


if __name__ == "__main__":
    main()
