import sqlite3


class ITTrendRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def get(self) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT generated_at, expires_at, payload_json FROM it_trend_snapshots WHERE id = 1"
        ).fetchone()

    def save(self, generated_at: str, expires_at: str, payload_json: str) -> None:
        self.conn.execute(
            """
            INSERT INTO it_trend_snapshots(id, generated_at, expires_at, payload_json)
            VALUES (1, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
              generated_at = excluded.generated_at,
              expires_at = excluded.expires_at,
              payload_json = excluded.payload_json,
              updated_at = datetime('now')
            """,
            (generated_at, expires_at, payload_json),
        )
