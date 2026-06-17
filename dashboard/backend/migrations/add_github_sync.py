"""
Migração: adiciona github_repo em tickets e cria ticket_github_links.
Idempotente — pode ser executada múltiplas vezes sem efeito colateral.
"""
import sqlite3
import os


def run(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # 1. Adicionar coluna github_repo em tickets (idempotente)
    existing = [row[1] for row in cur.execute("PRAGMA table_info(tickets)").fetchall()]
    if "github_repo" not in existing:
        cur.execute("ALTER TABLE tickets ADD COLUMN github_repo TEXT")
        print("[migration] added column tickets.github_repo")
    else:
        print("[migration] tickets.github_repo already exists — skip")

    # 2. Criar tabela ticket_github_links
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ticket_github_links (
            id TEXT PRIMARY KEY,
            ticket_id TEXT NOT NULL UNIQUE REFERENCES tickets(id) ON DELETE CASCADE,
            github_repo TEXT NOT NULL,
            issue_number INTEGER,
            issue_url TEXT,
            project_item_id TEXT,
            last_synced_at TEXT,
            sync_error TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS ix_tgl_ticket_id ON ticket_github_links(ticket_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_tgl_sync_error ON ticket_github_links(sync_error) WHERE sync_error IS NOT NULL")
    print("[migration] ticket_github_links OK")

    conn.commit()
    conn.close()


if __name__ == "__main__":
    import sys
    db = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("DATABASE_URL", "dashboard.db")
    run(db)
