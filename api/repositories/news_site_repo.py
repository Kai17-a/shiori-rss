import sqlite3


class NewsSiteRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def _with_webhook_ids(self, row: dict) -> dict:
        row["webhook_ids"] = self.find_webhook_ids(int(row["id"]))
        row["icon_uploaded"] = row.get("icon_data") is not None
        row.pop("icon_data", None)
        row.pop("icon_media_type", None)
        return row

    def find_icon(self, site_id: int) -> tuple[bytes, str] | None:
        row = self.conn.execute(
            "SELECT icon_data, icon_media_type FROM news_sites WHERE id = ?", (site_id,)
        ).fetchone()
        if row is None or row["icon_data"] is None:
            return None
        return bytes(row["icon_data"]), str(row["icon_media_type"])

    def find_webhook_ids(self, site_id: int) -> list[int]:
        rows = self.conn.execute(
            """
            SELECT webhook_id FROM news_site_webhooks
            WHERE site_id = ?
            ORDER BY webhook_id ASC
            """,
            (site_id,),
        ).fetchall()
        return [int(row["webhook_id"]) for row in rows]

    def set_webhook_ids(self, site_id: int, webhook_ids: list[int]) -> None:
        self.conn.execute(
            "DELETE FROM news_site_webhooks WHERE site_id = ?", (site_id,)
        )
        self.conn.executemany(
            "INSERT INTO news_site_webhooks (site_id, webhook_id) VALUES (?, ?)",
            [(site_id, webhook_id) for webhook_id in webhook_ids],
        )

    def insert(
        self,
        *,
        url: str,
        title: str,
        description: str | None,
        scrape_config: str,
        icon_url: str | None,
    ) -> dict:
        cursor = self.conn.execute(
            """
            INSERT INTO news_sites (url, title, description, scrape_config, icon_url)
            VALUES (?, ?, ?, ?, ?)
            """,
            (url, title, description, scrape_config, icon_url),
        )
        assert cursor.lastrowid is not None
        row = self.find_by_id(cursor.lastrowid)
        assert row is not None
        return row

    def find_by_id(self, site_id: int) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM news_sites WHERE id = ?", (site_id,)
        ).fetchone()
        return self._with_webhook_ids(dict(row)) if row else None

    def find_by_url(self, url: str) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM news_sites WHERE url = ?", (url,)
        ).fetchone()
        return self._with_webhook_ids(dict(row)) if row else None

    def find_all_ids(self) -> list[dict]:
        """Lightweight listing for the periodic batch: just enough per site
        (id, notify flag) to decide whether to run it and whether webhook
        notification should fire, without the full row/webhook-id lookup
        `find_all` does for the paginated UI listing.
        """
        rows = self.conn.execute(
            "SELECT id, notify_webhook_enabled FROM news_sites ORDER BY id ASC"
        ).fetchall()
        return [dict(row) for row in rows]

    def count_all(self, q: str | None = None) -> int:
        query = "SELECT COUNT(*) AS total FROM news_sites"
        params: list[object] = []
        if q is not None and q.strip():
            query += " WHERE title LIKE ? OR url LIKE ?"
            like = f"%{q.strip()}%"
            params.extend([like, like])
        row = self.conn.execute(query, params).fetchone()
        return int(row["total"]) if row else 0

    def find_all(self, q: str | None, limit: int, offset: int) -> list[dict]:
        query = "SELECT * FROM news_sites"
        params: list[object] = []
        if q is not None and q.strip():
            query += " WHERE title LIKE ? OR url LIKE ?"
            like = f"%{q.strip()}%"
            params.extend([like, like])
        query += " ORDER BY title ASC, id ASC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        rows = self.conn.execute(query, params).fetchall()
        return [self._with_webhook_ids(dict(row)) for row in rows]

    def update(self, site_id: int, fields: dict[str, object]) -> dict | None:
        if not fields:
            return self.find_by_id(site_id)
        set_clauses = ", ".join(f"{key} = ?" for key in fields)
        set_clauses += ", updated_at = strftime('%Y-%m-%d %H:%M:%f', 'now')"
        cursor = self.conn.execute(
            f"UPDATE news_sites SET {set_clauses} WHERE id = ?",
            [*fields.values(), site_id],
        )
        return self.find_by_id(site_id) if cursor.rowcount else None

    def delete(self, site_id: int) -> bool:
        cursor = self.conn.execute("DELETE FROM news_sites WHERE id = ?", (site_id,))
        return cursor.rowcount > 0

    def count_articles(
        self,
        site_id: int,
        *,
        q: str | None = None,
        published_from: str | None = None,
        published_to: str | None = None,
    ) -> int:
        clauses, params = self._article_filters(
            site_id, q=q, published_from=published_from, published_to=published_to
        )
        row = self.conn.execute(
            f"SELECT COUNT(*) AS total FROM news_site_articles WHERE {' AND '.join(clauses)}",
            params,
        ).fetchone()
        return int(row["total"]) if row else 0

    def find_articles(
        self,
        site_id: int,
        *,
        q: str | None,
        published_from: str | None,
        published_to: str | None,
        limit: int,
        offset: int,
    ) -> list[dict]:
        clauses, params = self._article_filters(
            site_id, q=q, published_from=published_from, published_to=published_to
        )
        rows = self.conn.execute(
            f"""
            SELECT id, site_id, url, title, summary, published,
                   webhook_notified, created_at
            FROM news_site_articles
            WHERE {" AND ".join(clauses)}
            ORDER BY published IS NULL ASC, published DESC, id DESC
            LIMIT ? OFFSET ?
            """,
            [*params, limit, offset],
        ).fetchall()
        return [dict(row) for row in rows]

    def _article_filters(
        self,
        site_id: int,
        *,
        q: str | None,
        published_from: str | None,
        published_to: str | None,
    ) -> tuple[list[str], list[object]]:
        clauses = ["site_id = ?"]
        params: list[object] = [site_id]
        if q is not None and q.strip():
            clauses.append("title LIKE ?")
            params.append(f"%{q.strip()}%")
        if published_from:
            clauses.append("substr(coalesce(published, created_at), 1, 10) >= ?")
            params.append(published_from)
        if published_to:
            clauses.append("substr(coalesce(published, created_at), 1, 10) <= ?")
            params.append(published_to)
        return clauses, params

    def load_sent_article_urls(self, site_id: int) -> set[str]:
        rows = self.conn.execute(
            "SELECT url FROM news_site_articles WHERE site_id = ?", (site_id,)
        ).fetchall()
        return {str(row["url"]) for row in rows}

    def record_articles(self, site_id: int, articles: list[dict[str, object]]) -> None:
        self.conn.executemany(
            """
            INSERT OR IGNORE INTO news_site_articles
                (site_id, url, title, summary, published, webhook_notified)
            VALUES (?, ?, ?, ?, ?, 0)
            """,
            [
                (
                    site_id,
                    article["url"],
                    article.get("title"),
                    article.get("summary"),
                    article.get("published"),
                )
                for article in articles
            ],
        )

    def find_pending_articles(self, site_id: int) -> list[dict]:
        rows = self.conn.execute(
            """
            SELECT url, title, summary, published
            FROM news_site_articles
            WHERE site_id = ? AND webhook_notified = 0
            ORDER BY datetime(coalesce(published, created_at)) DESC, id DESC
            """,
            (site_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def mark_articles_notified(self, site_id: int, articles: list[dict]) -> None:
        self.conn.executemany(
            """
            UPDATE news_site_articles SET webhook_notified = 1
            WHERE site_id = ? AND url = ?
            """,
            [(site_id, article["url"]) for article in articles],
        )
