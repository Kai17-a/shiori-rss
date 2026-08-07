import sqlite3


class WebhookEndpointRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def find_all(self) -> list[dict]:
        rows = self.conn.execute(
            """
            SELECT id, name, url, enabled, created_at, updated_at
            FROM webhook_endpoints
            ORDER BY id ASC
            """
        ).fetchall()
        return [dict(row) for row in rows]

    def find_enabled(self) -> list[dict]:
        rows = self.conn.execute(
            """
            SELECT id, name, url, enabled, created_at, updated_at
            FROM webhook_endpoints
            WHERE enabled = 1
            ORDER BY id ASC
            """
        ).fetchall()
        return [dict(row) for row in rows]

    def insert(self, name: str, url: str) -> dict:
        cursor = self.conn.execute(
            "INSERT INTO webhook_endpoints (name, url) VALUES (?, ?)",
            (name, url),
        )
        row = self.conn.execute(
            """
            SELECT id, name, url, enabled, created_at, updated_at
            FROM webhook_endpoints
            WHERE id = ?
            """,
            (cursor.lastrowid,),
        ).fetchone()
        return dict(row)

    def find_by_id(self, webhook_id: int) -> dict | None:
        row = self.conn.execute(
            """
            SELECT id, name, url, enabled, created_at, updated_at
            FROM webhook_endpoints
            WHERE id = ?
            """,
            (webhook_id,),
        ).fetchone()
        return dict(row) if row else None

    def update_enabled(self, webhook_id: int, enabled: bool) -> dict | None:
        cursor = self.conn.execute(
            """
            UPDATE webhook_endpoints
            SET enabled = ?, updated_at = datetime('now')
            WHERE id = ?
            """,
            (int(enabled), webhook_id),
        )
        if cursor.rowcount == 0:
            return None
        return self.find_by_id(webhook_id)

    def delete(self, webhook_id: int) -> bool:
        cursor = self.conn.execute(
            "DELETE FROM webhook_endpoints WHERE id = ?",
            (webhook_id,),
        )
        return cursor.rowcount > 0
