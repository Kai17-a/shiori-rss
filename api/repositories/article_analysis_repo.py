import sqlite3


class ArticleAnalysisRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    @staticmethod
    def _filters(
        *, q: str | None, source_type: str | None, status: str | None
    ) -> tuple[str, list[object]]:
        clauses: list[str] = []
        params: list[object] = []
        if q:
            clauses.append(
                "(article_search.title LIKE ? OR article_search.source_title LIKE ? "
                "OR analyses.ai_summary LIKE ?)"
            )
            pattern = f"%{q}%"
            params.extend([pattern, pattern, pattern])
        if source_type:
            clauses.append("analyses.source_type = ?")
            params.append(source_type)
        if status:
            clauses.append("analyses.status = ?")
            params.append(status)
        return (f"WHERE {' AND '.join(clauses)}" if clauses else ""), params

    def count_all(
        self, *, q: str | None, source_type: str | None, status: str | None
    ) -> int:
        where, params = self._filters(q=q, source_type=source_type, status=status)
        row = self.conn.execute(
            f"""
            SELECT COUNT(*) AS total
            FROM article_ai_analyses AS analyses
            JOIN article_search
              ON article_search.source_type = analyses.source_type
             AND CAST(article_search.article_id AS INTEGER) = analyses.article_id
            {where}
            """,
            params,
        ).fetchone()
        return int(row["total"])

    def find_all(
        self,
        *,
        q: str | None,
        source_type: str | None,
        status: str | None,
        limit: int,
        offset: int,
    ) -> list[dict]:
        where, params = self._filters(q=q, source_type=source_type, status=status)
        rows = self.conn.execute(
            f"""
            SELECT analyses.*, CAST(article_search.source_id AS INTEGER) AS source_id,
                   article_search.source_title,
                   article_search.title AS article_title,
                   article_search.url AS article_url,
                   article_search.published AS article_published
            FROM article_ai_analyses AS analyses
            JOIN article_search
              ON article_search.source_type = analyses.source_type
             AND CAST(article_search.article_id AS INTEGER) = analyses.article_id
            {where}
            ORDER BY datetime(analyses.updated_at) DESC, analyses.id DESC
            LIMIT ? OFFSET ?
            """,
            [*params, limit, offset],
        ).fetchall()
        return [dict(row) for row in rows]

    def delete_failed(self) -> int:
        cursor = self.conn.execute(
            "DELETE FROM article_ai_analyses WHERE status = 'failed'"
        )
        return cursor.rowcount
