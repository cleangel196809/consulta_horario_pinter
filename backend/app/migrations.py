from pathlib import Path

from sqlalchemy import text

from .database import engine


MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "scripts" / "migrations"


def run_migrations():
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE IF NOT EXISTS schema_migrations "
            "(version VARCHAR(255) PRIMARY KEY, aplicado_en TIMESTAMP DEFAULT NOW())"
        ))
        applied = {
            row[0] for row in conn.execute(text("SELECT version FROM schema_migrations"))
        }
        for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
            if path.name in applied:
                continue
            conn.exec_driver_sql(path.read_text(encoding="utf-8"))
            conn.execute(
                text("INSERT INTO schema_migrations (version) VALUES (:version)"),
                {"version": path.name},
            )
