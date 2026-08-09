import sqlite3


class ArticleSearchRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    @staticmethod
    def _quote_match_term(term: str) -> str:
        return f'"{term.replace(chr(34), chr(34) * 2)}"'

    def search(
        self,
        *,
        keywords: list[str],
        source_types: list[str],
        published_after: str | None,
        published_before: str | None,
        limit: int,
    ) -> list[dict]:
        long_terms = [term for term in keywords if len(term) >= 3]
        short_terms = [term for term in keywords if len(term) < 3]
        clauses: list[str] = []
        params: list[object] = []

        if long_terms:
            clauses.append("article_search MATCH ?")
            params.append(
                " OR ".join(self._quote_match_term(term) for term in long_terms)
            )
        elif short_terms:
            like_clauses: list[str] = []
            for term in short_terms:
                like_clauses.append(
                    "(source_title LIKE ? OR title LIKE ? OR summary LIKE ?)"
                )
                like = f"%{term}%"
                params.extend((like, like, like))
            clauses.append(f"({' OR '.join(like_clauses)})")

        if source_types:
            placeholders = ", ".join("?" for _ in source_types)
            clauses.append(f"source_type IN ({placeholders})")
            params.extend(source_types)
        if published_after:
            clauses.append("datetime(coalesce(published, created_at)) >= datetime(?)")
            params.append(published_after)
        if published_before:
            clauses.append("datetime(coalesce(published, created_at)) <= datetime(?)")
            params.append(published_before)

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rank = "bm25(article_search, 0, 0, 0, 3, 8, 4, 0, 0, 0)" if long_terms else "0"
        rows = self.conn.execute(
            f"""
            SELECT source_type, CAST(article_id AS INTEGER) AS article_id,
                   CAST(source_id AS INTEGER) AS source_id, source_title, title,
                   summary, url, published, created_at, {rank} AS relevance
            FROM article_search
            {where}
            ORDER BY relevance ASC,
                     datetime(coalesce(published, created_at)) DESC,
                     article_id DESC
            LIMIT ?
            """,
            [*params, limit],
        ).fetchall()
        return [dict(row) for row in rows]
