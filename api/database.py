import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DEFAULT_DATABASE_PATH = Path(__file__).resolve().parents[1] / "data" / "data.db"
DATABASE_URL = os.getenv("DATABASE_URL", str(DEFAULT_DATABASE_PATH))
DEFAULT_MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "db" / "migrations"


def _resolve_sqlite_path(database_url: str) -> Path:
    path = Path(database_url)
    if path.is_absolute():
        return path
    return Path(".") / path


def _read_up_migration(migration_path: Path) -> list[str]:
    up_lines: list[str] = []
    reading_up = False
    for raw_line in migration_path.read_text().splitlines():
        line = raw_line.strip()
        if line.startswith("-- migrate:up"):
            reading_up = True
            continue
        if line.startswith("-- migrate:down"):
            break
        if reading_up:
            up_lines.append(raw_line)

    statements: list[str] = []
    pending: list[str] = []
    for line in up_lines:
        pending.append(line)
        candidate = "\n".join(pending).strip()
        if candidate and sqlite3.complete_statement(candidate):
            statements.append(candidate)
            pending = []

    if any(line.strip() for line in pending):
        raise ValueError(f"Incomplete SQL statement in {migration_path}")
    return statements


def initialize_database(
    database_url: str | None = None,
    migrations_dir: Path | None = None,
) -> None:
    """Create or migrate the configured SQLite database before serving requests."""
    database_path = _resolve_sqlite_path(database_url or DATABASE_URL)
    migration_root = migrations_dir or Path(
        os.getenv("MIGRATIONS_DIR", str(DEFAULT_MIGRATIONS_DIR))
    )
    migration_paths = sorted(migration_root.glob("*.sql"))
    if not migration_paths:
        raise FileNotFoundError(f"No database migrations found in {migration_root}")

    database_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(database_path)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations "
            "(version VARCHAR(128) PRIMARY KEY)"
        )
        conn.commit()
        applied_versions = {
            str(row[0])
            for row in conn.execute("SELECT version FROM schema_migrations").fetchall()
        }

        for migration_path in migration_paths:
            version = migration_path.stem.split("_", 1)[0]
            if version in applied_versions:
                continue
            try:
                for statement in _read_up_migration(migration_path):
                    conn.execute(statement)
                conn.execute(
                    "INSERT INTO schema_migrations (version) VALUES (?)",
                    (version,),
                )
                conn.commit()
            except Exception:
                conn.rollback()
                raise
    finally:
        conn.close()


@contextmanager
def get_db(database_url: str = DATABASE_URL):
    """Yield a SQLite connection with foreign keys enabled and auto commit/rollback."""
    database_path = _resolve_sqlite_path(database_url)
    database_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(database_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
