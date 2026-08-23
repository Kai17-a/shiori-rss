import logging
import os
import sqlite3
import struct
from contextlib import contextmanager
from pathlib import Path

DEFAULT_DATABASE_PATH = Path(__file__).resolve().parents[1] / "data" / "data.db"
DATABASE_URL = os.getenv("DATABASE_URL", str(DEFAULT_DATABASE_PATH))
DEFAULT_MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "db" / "migrations"

# Inert placeholder width for article_ai_embeddings before any embedding
# model has ever been configured (the table is empty, so its width doesn't
# matter yet). Once a real model is saved, settings_service recreates the
# table at that model's actual dimension — see recreate_vector_search_schema
# and llm_service.LLM_EMBEDDING_DIM_SETTING_KEY.
PLACEHOLDER_VECTOR_EMBEDDING_DIM = 8

_logger = logging.getLogger("uvicorn.error")


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
        ensure_vector_search_schema(conn)
    finally:
        conn.close()


def load_vec_extension(conn: sqlite3.Connection) -> None:
    """Load the sqlite-vec extension into `conn` so vec0 tables can be used.

    Deliberately not called from `get_db()` (used by nearly every request) so
    connections that never touch vector search pay no extension-load cost.
    Call this only from code paths that actually query/write a vec0 table.
    """
    import sqlite_vec

    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)


def pack_embedding(vector: list[float], target_dim: int | None = None) -> bytes:
    """Pack `vector` into the little-endian float32 layout sqlite-vec's
    `float[N]` columns expect, zero-padding (or rejecting, if too long) to
    `target_dim` if given. Mirrors batch/src/analysis.rs's `pack_embedding`.

    `target_dim` should normally be the current article_ai_embeddings width
    (the embedding_dim setting), which always matches the configured
    embedding model's native dimension — so in practice this is a passthrough
    and padding never triggers. It stays generic/paddable because Rust's
    equivalent does too, and it makes the boundary behavior explicit and
    testable.
    """
    target_dim = target_dim if target_dim is not None else len(vector)
    if len(vector) > target_dim:
        raise ValueError(
            f"Embedding has {len(vector)} dimensions, which exceeds the "
            f"expected {target_dim}."
        )
    padded = list(vector) + [0.0] * (target_dim - len(vector))
    return struct.pack(f"<{target_dim}f", *padded)


def _create_vector_search_table(conn: sqlite3.Connection, dim: int) -> None:
    conn.execute(
        f"""
        CREATE VIRTUAL TABLE IF NOT EXISTS article_ai_embeddings USING vec0(
          analysis_id INTEGER PRIMARY KEY,
          embedding FLOAT[{dim}]
        )
        """
    )


def ensure_vector_search_schema(
    conn: sqlite3.Connection, dim: int = PLACEHOLDER_VECTOR_EMBEDDING_DIM
) -> None:
    """Idempotently create the article_ai_embeddings vec0 virtual table.

    This can't live in a normal db/migrations/*.sql file: dbmate's sqlite
    driver has no sqlite-vec extension loaded, so a `CREATE VIRTUAL TABLE
    ... USING vec0(...)` statement fails migration application with "no such
    module: vec0". Instead it's created here, once, on a connection that has
    the extension loaded. Failure is logged and swallowed rather than raised
    so a broken/missing sqlite-vec install never prevents the app (whose
    core features don't depend on embeddings) from starting.

    Only creates the table if missing (does not resize an existing one) —
    see recreate_vector_search_schema for changing an already-configured
    model's dimension.
    """
    try:
        load_vec_extension(conn)
        _create_vector_search_table(conn, dim)
        conn.commit()
    except Exception:
        conn.rollback()
        _logger.exception(
            "Failed to prepare article_ai_embeddings vector search table; "
            "semantic search will be unavailable until this is resolved."
        )


def recreate_vector_search_schema(conn: sqlite3.Connection, dim: int) -> None:
    """Drop and recreate article_ai_embeddings at a new width.

    Called when the configured embedding model's dimension changes (first
    time it's set, or switched to a differently-sized model). Any existing
    rows are for the old model's vector space anyway and are already treated
    as stale by the embedding_model staleness check, so dropping them here is
    safe — the next analysis run regenerates them at the new width.
    """
    load_vec_extension(conn)
    conn.execute("DROP TABLE IF EXISTS article_ai_embeddings")
    _create_vector_search_table(conn, dim)
    conn.commit()


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
