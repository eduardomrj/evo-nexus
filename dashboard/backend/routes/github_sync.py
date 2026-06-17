"""
Routes de observabilidade para sincronização GitHub.
Blueprint: github_sync_bp, prefixo /api/github-sync
"""
from flask import Blueprint, jsonify, current_app
from datetime import datetime, timezone

bp = Blueprint("github_sync", __name__)


@bp.route("/api/github-sync/status", methods=["GET"])
def github_sync_status():
    """Resumo de saúde da sincronização GitHub."""
    from models import db, TicketGithubLink

    total = db.session.execute(db.text("SELECT COUNT(*) FROM ticket_github_links")).scalar() or 0
    errors = db.session.execute(
        db.text("SELECT COUNT(*) FROM ticket_github_links WHERE sync_error IS NOT NULL")
    ).scalar() or 0
    last_sync = db.session.execute(
        db.text("SELECT MAX(last_synced_at) FROM ticket_github_links")
    ).scalar()
    oldest_unsynced = db.session.execute(
        db.text("""
            SELECT MIN(created_at) FROM ticket_github_links
            WHERE last_synced_at IS NULL OR issue_number IS NULL
        """)
    ).scalar()

    # Verificar se o project node_id está cacheado
    try:
        from github_issues import _project_node_id_cache
        node_id_cached = _project_node_id_cache is not None
    except Exception:
        node_id_cached = False

    return jsonify({
        "total_linked": total,
        "sync_errors": errors,
        "last_sync_at": last_sync,
        "oldest_pending_sync": oldest_unsynced,
        "project_node_id_cached": node_id_cached,
    })


@bp.route("/api/github-sync/errors", methods=["GET"])
def github_sync_errors():
    """Lista tickets com erro de sincronização (máx. 50)."""
    from models import db

    rows = db.session.execute(db.text("""
        SELECT ticket_id, github_repo, issue_number, sync_error, last_synced_at
        FROM ticket_github_links
        WHERE sync_error IS NOT NULL
        ORDER BY last_synced_at ASC NULLS FIRST
        LIMIT 50
    """)).fetchall()

    return jsonify([
        {
            "ticket_id": r[0],
            "github_repo": r[1],
            "issue_number": r[2],
            "sync_error": r[3],
            "last_synced_at": r[4],
        }
        for r in rows
    ])


@bp.route("/api/github-sync/retry/<string:ticket_id>", methods=["POST"])
def github_sync_retry(ticket_id: str):
    """Força re-sync imediato de um ticket específico."""
    import threading
    from models import Ticket

    ticket = Ticket.query.get(ticket_id)
    if not ticket:
        return jsonify({"error": "not_found"}), 404
    if not ticket.github_repo:
        return jsonify({"error": "ticket has no github_repo configured"}), 400

    app = current_app._get_current_object()

    def _run():
        try:
            with app.app_context():
                from github_issues import sync_ticket_to_github
                sync_ticket_to_github(ticket_id)
        except Exception as exc:
            import logging
            logging.getLogger(__name__).error("github sync retry failed for %s: %s", ticket_id, exc)

    t = threading.Thread(target=_run, daemon=True, name=f"gh-retry-{ticket_id[:8]}")
    t.start()

    return jsonify({"queued": True, "ticket_id": ticket_id}), 202
