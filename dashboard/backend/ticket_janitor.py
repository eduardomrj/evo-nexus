"""Ticket janitor — auto-releases timed-out ticket locks every 5 minutes (Feature 1.3)."""

from __future__ import annotations

import json
import os
import threading
import time
import uuid
from datetime import datetime, timezone

JANITOR_INTERVAL_SECONDS = int(os.getenv("TICKET_JANITOR_INTERVAL", "300"))  # 5 min default

_janitor_started = False
_janitor_lock = threading.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def release_expired_locks(app=None) -> int:
    """Find and release all expired ticket locks.

    Returns the number of tickets released.
    Must run inside a Flask app context (pass app for context push, or call
    from an already-active context).
    """
    released = 0
    try:
        from models import db, Ticket, TicketActivity

        # Find all tickets whose lock has expired
        expired = db.session.execute(
            db.text("""
                SELECT id, locked_by, COALESCE(lock_timeout_seconds, 1800) as timeout_secs
                FROM tickets
                WHERE locked_at IS NOT NULL
                  AND datetime(locked_at, '+' || COALESCE(lock_timeout_seconds, 1800) || ' seconds')
                      < datetime('now')
            """)
        ).fetchall()

        now = _now()
        for row in expired:
            ticket_id = row[0]
            locked_by = row[1]

            # Update via raw SQL to avoid SQLAlchemy CHECK constraint issues
            db.session.execute(
                db.text(
                    "UPDATE tickets SET locked_at = NULL, locked_by = NULL, updated_at = :now "
                    "WHERE id = :id AND locked_at IS NOT NULL"
                ),
                {"id": ticket_id, "now": now},
            )

            activity = TicketActivity(
                id=str(uuid.uuid4()),
                ticket_id=ticket_id,
                actor="system:janitor",
                action="auto_release",
                payload=json.dumps({"previously_locked_by": locked_by}),
                created_at=now,
            )
            db.session.add(activity)
            released += 1

        if released > 0:
            db.session.commit()
            print(f"[ticket_janitor] auto-released {released} expired lock(s)", flush=True)

    except Exception as exc:
        try:
            db.session.rollback()
        except Exception:
            pass
        print(f"[ticket_janitor] ERROR in release_expired_locks: {exc}", flush=True)

    return released


def check_deleted_github_issues(app) -> int:
    """Detecta issues deletadas no GitHub (404) e fecha os tickets correspondentes.

    Roda no ciclo do janitor. Limita a 50 checks por ciclo para não estourar rate-limit.
    Retorna número de tickets fechados.
    """
    closed = 0
    try:
        from github_issues import get_issue
        from models import db, Ticket, TicketGithubLink, TicketActivity

        # Tickets sincronizados, não resolvidos/fechados, com last_synced_at > 1h atrás
        cutoff = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        rows = db.session.execute(db.text("""
            SELECT tgl.id, tgl.ticket_id, tgl.github_repo, tgl.issue_number
            FROM ticket_github_links tgl
            JOIN tickets t ON t.id = tgl.ticket_id
            WHERE tgl.issue_number IS NOT NULL
              AND t.status NOT IN ('resolved', 'closed', 'archived')
              AND (
                tgl.last_synced_at IS NULL
                OR datetime(tgl.last_synced_at) < datetime(:cutoff, '-1 hour')
              )
            ORDER BY tgl.last_synced_at ASC NULLS FIRST
            LIMIT 50
        """), {"cutoff": cutoff}).fetchall()

        now = _now()
        for row in rows:
            link_id, ticket_id, github_repo, issue_number = row

            status_code, _ = get_issue(github_repo, issue_number)

            if status_code == 404:
                # Issue deletada — fechar ticket
                db.session.execute(
                    db.text("UPDATE tickets SET status = 'closed', updated_at = :now WHERE id = :id"),
                    {"id": ticket_id, "now": now},
                )
                activity = TicketActivity(
                    id=str(uuid.uuid4()),
                    ticket_id=ticket_id,
                    actor="system:github-janitor",
                    action="auto_closed_issue_deleted",
                    payload=json.dumps({"github_repo": github_repo, "issue_number": issue_number}),
                    created_at=now,
                )
                db.session.add(activity)
                db.session.commit()
                closed += 1
                print(f"[ticket_janitor] closed ticket {ticket_id} — GitHub issue #{issue_number} deleted", flush=True)

            elif status_code == 200:
                # Issue existe — atualizar last_synced_at
                db.session.execute(
                    db.text("UPDATE ticket_github_links SET last_synced_at = :now WHERE id = :id"),
                    {"id": link_id, "now": now},
                )
                db.session.commit()

            # status 0 (network error) ou outros: ignorar silenciosamente

    except ImportError:
        pass  # github_issues não disponível
    except Exception as exc:
        try:
            from models import db
            db.session.rollback()
        except Exception:
            pass
        print(f"[ticket_janitor] ERROR in check_deleted_github_issues: {exc}", flush=True)

    return closed


def _janitor_loop(app):
    """Background loop — reclaims expired ticket AND brain-repo locks.

    Both share the same 5-min cadence because both reclaim "busy" flags that
    should never stay set after a crash or OOM-kill. Keeping them in one
    thread avoids a second daemon with identical semantics.
    """
    while True:
        time.sleep(JANITOR_INTERVAL_SECONDS)
        try:
            with app.app_context():
                release_expired_locks()
        except Exception as exc:
            print(f"[ticket_janitor] loop error: {exc}", flush=True)
        # Brain-repo stale-lock sweep. Runs in the same context; failures are
        # isolated so a broken brain_repo import doesn't stop ticket cleanup.
        try:
            from brain_repo.job_runner import reclaim_stale_locks
            reclaim_stale_locks(app)
        except ImportError:
            pass  # brain_repo not installed / disabled
        except Exception as exc:
            print(f"[ticket_janitor] brain-repo sweep error: {exc}", flush=True)
        try:
            with app.app_context():
                check_deleted_github_issues(app)
        except Exception as exc:
            print(f"[ticket_janitor] github-check error: {exc}", flush=True)


def start_janitor_thread():
    """Start the janitor background thread (idempotent — safe to call multiple times)."""
    global _janitor_started

    with _janitor_lock:
        if _janitor_started:
            return
        _janitor_started = True

    # Import here to avoid circular import at module load
    from flask import current_app
    app = current_app._get_current_object()  # type: ignore[attr-defined]

    t = threading.Thread(
        target=_janitor_loop,
        args=(app,),
        daemon=True,
        name="ticket-janitor",
    )
    t.start()
    print(f"[ticket_janitor] started (interval={JANITOR_INTERVAL_SECONDS}s)", flush=True)
