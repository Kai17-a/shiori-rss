import sqlite3


class SettingsRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def get(self, key: str) -> str | None:
        row = self.conn.execute(
            "SELECT value FROM app_settings WHERE key = ?",
            (key,),
        ).fetchone()
        return str(row["value"]) if row else None

    def get_int(self, key: str, default: int) -> int:
        value = self.get(key)
        try:
            return int(value) if value is not None else default
        except ValueError:
            return default

    def set(self, key: str, value: str) -> str:
        self.conn.execute(
            """
            INSERT INTO app_settings (key, value, updated_at)
            VALUES (?, ?, strftime('%Y-%m-%d %H:%M:%f', 'now'))
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = excluded.updated_at
            """,
            (key, value),
        )
        stored = self.conn.execute(
            "SELECT value FROM app_settings WHERE key = ?",
            (key,),
        ).fetchone()
        assert stored is not None
        return str(stored["value"])

    def delete(self, key: str) -> None:
        self.conn.execute(
            "DELETE FROM app_settings WHERE key = ?",
            (key,),
        )

    def get_bool(self, key: str, default: bool = False) -> bool:
        row = self.conn.execute(
            "SELECT rss_periodic_execution_enabled FROM app_settings WHERE key = ?",
            (key,),
        ).fetchone()
        return bool(row["rss_periodic_execution_enabled"]) if row else default

    def set_bool(self, key: str, enabled: bool) -> bool:
        value = "1" if enabled else "0"
        flag = 1 if enabled else 0
        self.conn.execute(
            """
            INSERT INTO app_settings (
                key,
                value,
                rss_periodic_execution_enabled,
                updated_at
            )
            VALUES (?, ?, ?, strftime('%Y-%m-%d %H:%M:%f', 'now'))
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                rss_periodic_execution_enabled = excluded.rss_periodic_execution_enabled,
                updated_at = excluded.updated_at
            """,
            (key, value, flag),
        )
        stored = self.conn.execute(
            "SELECT rss_periodic_execution_enabled FROM app_settings WHERE key = ?",
            (key,),
        ).fetchone()
        assert stored is not None
        return bool(stored["rss_periodic_execution_enabled"])
