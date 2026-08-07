import sqlite3


class RSSFeedRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def _has_column(self, table: str, column: str) -> bool:
        rows = self.conn.execute(f"PRAGMA table_info({table})").fetchall()
        return any(row["name"] == column for row in rows)

    def _with_webhook_ids(self, row: dict) -> dict:
        row["webhook_ids"] = self.find_webhook_ids(int(row["id"]))
        return row

    def find_webhook_ids(self, feed_id: int) -> list[int]:
        rows = self.conn.execute(
            """
            SELECT webhook_id FROM rss_feed_webhooks
            WHERE feed_id = ?
            ORDER BY webhook_id ASC
            """,
            (feed_id,),
        ).fetchall()
        return [int(row["webhook_id"]) for row in rows]

    def set_webhook_ids(self, feed_id: int, webhook_ids: list[int]) -> None:
        self.conn.execute(
            "DELETE FROM rss_feed_webhooks WHERE feed_id = ?",
            (feed_id,),
        )
        self.conn.executemany(
            "INSERT INTO rss_feed_webhooks (feed_id, webhook_id) VALUES (?, ?)",
            [(feed_id, webhook_id) for webhook_id in webhook_ids],
        )

    def insert(
        self,
        url: str,
        title: str,
        description: str | None,
        notify_webhook_enabled: bool,
    ) -> dict:
        cursor = self.conn.execute(
            """
            INSERT INTO rss_feeds (url, title, description, notify_webhook_enabled)
            VALUES (?, ?, ?, ?)
            """,
            (url, title, description, int(notify_webhook_enabled)),
        )
        row = self.conn.execute(
            "SELECT * FROM rss_feeds WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
        return self._with_webhook_ids(dict(row))

    def count_all(self, q: str | None = None) -> int:
        query = "SELECT COUNT(*) AS total FROM rss_feeds"
        params: list = []
        if q is not None:
            query += " WHERE (title LIKE ? OR url LIKE ?)"
            like = f"%{q}%"
            params.extend([like, like])
        row = self.conn.execute(query, params).fetchone()
        return int(row["total"]) if row else 0

    def find_all(self, q: str | None, limit: int, offset: int) -> list[dict]:
        query = "SELECT * FROM rss_feeds"
        params: list = []
        if q is not None:
            query += " WHERE (title LIKE ? OR url LIKE ?)"
            like = f"%{q}%"
            params.extend([like, like])
        query += " ORDER BY title ASC, id ASC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        rows = self.conn.execute(query, params).fetchall()
        return [self._with_webhook_ids(dict(row)) for row in rows]

    def find_by_id(self, feed_id: int) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM rss_feeds WHERE id = ?", (feed_id,)
        ).fetchone()
        return self._with_webhook_ids(dict(row)) if row else None

    def find_by_url(self, url: str) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM rss_feeds WHERE url = ?", (url,)
        ).fetchone()
        return dict(row) if row else None

    def update(self, feed_id: int, fields: dict) -> dict | None:
        if not fields:
            return self.find_by_id(feed_id)
        set_clauses = ", ".join(f"{key} = ?" for key in fields)
        set_clauses += ", updated_at = strftime('%Y-%m-%d %H:%M:%f', 'now')"
        params = list(fields.values()) + [feed_id]
        cursor = self.conn.execute(
            f"UPDATE rss_feeds SET {set_clauses} WHERE id = ?", params
        )
        if cursor.rowcount == 0:
            return None
        return self.find_by_id(feed_id)

    def delete(self, feed_id: int) -> bool:
        cursor = self.conn.execute("DELETE FROM rss_feeds WHERE id = ?", (feed_id,))
        return cursor.rowcount > 0

    def find_articles_by_feed_id(self, feed_id: int) -> list[dict]:
        has_published = self._has_column("rss_feed_articles", "published")
        published_select = ", published" if has_published else ", NULL AS published"
        query = f"""
            SELECT id, feed_id, url, title{published_select}, created_at
            FROM rss_feed_articles
            WHERE feed_id = ?
            ORDER BY published IS NULL ASC, published DESC, id DESC
            """
        rows = self.conn.execute(query, (feed_id,)).fetchall()
        return [dict(row) for row in rows]

    def count_articles_by_feed_id(self, feed_id: int) -> int:
        return self.count_articles_by_feed_id_filtered(feed_id)

    def count_articles_by_feed_id_filtered(
        self,
        feed_id: int,
        published_from: str | None = None,
        published_to: str | None = None,
    ) -> int:
        clauses = ["feed_id = ?"]
        params: list = [feed_id]
        clauses, params = self._append_article_date_filters(clauses, params, published_from, published_to)
        row = self.conn.execute(
            f"SELECT COUNT(*) AS total FROM rss_feed_articles WHERE {' AND '.join(clauses)}",
            params,
        ).fetchone()
        return int(row["total"]) if row else 0

    def find_articles_by_feed_id_paginated(
        self,
        feed_id: int,
        limit: int,
        offset: int,
        published_from: str | None = None,
        published_to: str | None = None,
    ) -> list[dict]:
        has_published = self._has_column("rss_feed_articles", "published")
        published_select = ", published" if has_published else ", NULL AS published"
        clauses = ["feed_id = ?"]
        params: list = [feed_id]
        clauses, params = self._append_article_date_filters(clauses, params, published_from, published_to)
        query = f"""
            SELECT id, feed_id, url, title{published_select}, created_at
            FROM rss_feed_articles
            WHERE {' AND '.join(clauses)}
            ORDER BY published IS NULL ASC, published DESC, id DESC
            LIMIT ? OFFSET ?
            """
        rows = self.conn.execute(query, [*params, limit, offset]).fetchall()
        return [dict(row) for row in rows]

    def _append_article_date_filters(
        self,
        clauses: list[str],
        params: list,
        published_from: str | None,
        published_to: str | None,
    ) -> tuple[list[str], list]:
        if published_from:
            clauses.append("substr(coalesce(published, created_at), 1, 10) >= ?")
            params.append(published_from)
        if published_to:
            clauses.append("substr(coalesce(published, created_at), 1, 10) <= ?")
            params.append(published_to)
        return clauses, params
