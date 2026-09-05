import sqlite3


class DockerImageRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def find_all(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM docker_images ORDER BY registry, repository, tag, id"
        ).fetchall()
        return [self._with_webhook_ids(dict(row)) for row in rows]

    def find_by_id(self, image_id: int) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM docker_images WHERE id = ?", (image_id,)
        ).fetchone()
        return self._with_webhook_ids(dict(row)) if row else None

    def find_by_reference(
        self, registry: str, repository: str, tag: str
    ) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM docker_images WHERE registry = ? AND repository = ? AND tag = ?",
            (registry, repository, tag),
        ).fetchone()
        return self._with_webhook_ids(dict(row)) if row else None

    def insert(self, values: dict[str, object]) -> dict:
        cursor = self.conn.execute(
            """
            INSERT INTO docker_images (
                registry, repository, tag, display_name, latest_digest,
                latest_notified_digest
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                values["registry"],
                values["repository"],
                values["tag"],
                values["display_name"],
                values["latest_digest"],
                values["latest_digest"],
            ),
        )
        assert cursor.lastrowid is not None
        row = self.find_by_id(cursor.lastrowid)
        assert row is not None
        return row

    def update_digest(self, image_id: int, digest: str) -> dict:
        self.conn.execute(
            """
            UPDATE docker_images SET latest_digest = ?,
                fetched_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now'),
                updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
            WHERE id = ?
            """,
            (digest, image_id),
        )
        row = self.find_by_id(image_id)
        assert row is not None
        return row

    def delete(self, image_id: int) -> bool:
        return (
            self.conn.execute(
                "DELETE FROM docker_images WHERE id = ?", (image_id,)
            ).rowcount
            > 0
        )

    def find_webhook_ids(self, image_id: int) -> list[int]:
        rows = self.conn.execute(
            "SELECT webhook_id FROM docker_image_webhooks WHERE image_id = ? ORDER BY webhook_id",
            (image_id,),
        ).fetchall()
        return [int(row["webhook_id"]) for row in rows]

    def set_webhook_ids(self, image_id: int, webhook_ids: list[int]) -> None:
        self.conn.execute(
            "DELETE FROM docker_image_webhooks WHERE image_id = ?", (image_id,)
        )
        self.conn.executemany(
            "INSERT INTO docker_image_webhooks (image_id, webhook_id) VALUES (?, ?)",
            [(image_id, webhook_id) for webhook_id in webhook_ids],
        )

    def _with_webhook_ids(self, row: dict) -> dict:
        row["webhook_ids"] = self.find_webhook_ids(int(row["id"]))
        return row
