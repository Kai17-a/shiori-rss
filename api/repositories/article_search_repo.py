import sqlite3

from api.database import load_vec_extension, pack_embedding
from api.repositories.settings_repo import SettingsRepository
from api.services.llm_service import LLM_EMBEDDING_DIM_SETTING_KEY


class ArticleSearchRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    @staticmethod
    def _quote_match_term(term: str) -> str:
        return f'"{term.replace(chr(34), chr(34) * 2)}"'

    @staticmethod
    def _escape_like_term(term: str) -> str:
        return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

    def search(
        self,
        *,
        keywords: list[str],
        source_types: list[str],
        published_after: str | None,
        published_before: str | None,
        limit: int,
        relaxed: bool = False,
    ) -> list[dict]:
        long_terms = [term for term in keywords if len(term) >= 3]
        short_terms = [term for term in keywords if len(term) < 3]
        clauses: list[str] = []
        params: list[object] = []
        search_cte = ""

        if relaxed and keywords:
            like_clauses: list[str] = []
            for term in keywords:
                like_clauses.append(
                    "(article_search.source_title LIKE ? ESCAPE '\\' "
                    "OR article_search.title LIKE ? ESCAPE '\\' "
                    "OR article_search.summary LIKE ? ESCAPE '\\' "
                    "OR analyses.ai_summary LIKE ? ESCAPE '\\' "
                    "OR analyses.key_points_json LIKE ? ESCAPE '\\' "
                    "OR analyses.topics_json LIKE ? ESCAPE '\\' "
                    "OR analyses.keywords_json LIKE ? ESCAPE '\\' "
                    "OR analyses.entities_json LIKE ? ESCAPE '\\' "
                    "OR analyses.search_aliases_json LIKE ? ESCAPE '\\')"
                )
                like = f"%{self._escape_like_term(term)}%"
                params.extend((like,) * 9)
            clauses.append(f"({' OR '.join(like_clauses)})")
        elif long_terms:
            match_query = " OR ".join(
                self._quote_match_term(term) for term in long_terms
            )
            search_cte = """
                WITH matching_articles AS (
                  SELECT source_type, article_id,
                         bm25(article_search, 0, 0, 0, 10, 12, 4, 0, 0, 0) AS relevance
                  FROM article_search
                  WHERE article_search MATCH ?
                  UNION ALL
                  SELECT source_type, article_id,
                         bm25(article_ai_search, 0, 0, 3, 1, 1, 8, 10, 5) AS relevance
                  FROM article_ai_search
                  WHERE article_ai_search MATCH ?
                ), ranked_articles AS (
                  SELECT source_type, article_id, min(relevance) AS relevance
                  FROM matching_articles
                  GROUP BY source_type, article_id
                )
            """
            params.extend((match_query, match_query))
        elif short_terms:
            like_clauses: list[str] = []
            for term in short_terms:
                like_clauses.append(
                    "(article_search.source_title LIKE ? OR article_search.title LIKE ? "
                    "OR article_search.summary LIKE ? OR analyses.ai_summary LIKE ?)"
                )
                like = f"%{term}%"
                params.extend((like, like, like, like))
            clauses.append(f"({' OR '.join(like_clauses)})")

        if source_types:
            placeholders = ", ".join("?" for _ in source_types)
            clauses.append(f"article_search.source_type IN ({placeholders})")
            params.extend(source_types)
        if published_after:
            clauses.append(
                "datetime(coalesce(article_search.published, article_search.created_at)) "
                ">= datetime(?)"
            )
            params.append(published_after)
        if published_before:
            clauses.append(
                "datetime(coalesce(article_search.published, article_search.created_at)) "
                "<= datetime(?)"
            )
            params.append(published_before)

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        matching_join = (
            "JOIN ranked_articles USING (source_type, article_id)"
            if search_cte
            else ""
        )
        relevance = "ranked_articles.relevance" if search_cte else "0"
        rows = self.conn.execute(
            f"""
            {search_cte}
            SELECT article_search.source_type,
                   CAST(article_search.article_id AS INTEGER) AS article_id,
                   CAST(article_search.source_id AS INTEGER) AS source_id,
                   article_search.source_title, article_search.title,
                   article_search.summary, article_search.url,
                   article_search.published, article_search.created_at,
                   analyses.ai_summary, analyses.key_points_json,
                   analyses.topics_json, analyses.keywords_json,
                   analyses.entities_json, analyses.search_aliases_json,
                   {relevance} AS relevance
            FROM article_search
            {matching_join}
            LEFT JOIN article_ai_analyses AS analyses
              ON analyses.source_type = article_search.source_type
             AND analyses.article_id = CAST(article_search.article_id AS INTEGER)
             AND analyses.status = 'completed'
            {where}
            ORDER BY relevance ASC,
                     datetime(coalesce(article_search.published,
                                       article_search.created_at)) DESC,
                     CAST(article_search.article_id AS INTEGER) DESC
            LIMIT ?
            """,
            [*params, limit],
        ).fetchall()
        return [dict(row) for row in rows]

    def vector_search(
        self,
        *,
        query_embedding: list[float],
        source_types: list[str],
        limit: int,
    ) -> list[dict]:
        """Semantic (embedding) KNN search, mirroring search()'s return shape
        exactly (same columns, `relevance` reused as the sort key — lower is
        "better" for both BM25 and this method's cosine/L2 distance) so
        callers can treat rows from either method identically.
        """
        load_vec_extension(self.conn)
        dim = SettingsRepository(self.conn).get_int(
            LLM_EMBEDDING_DIM_SETTING_KEY, len(query_embedding)
        )
        packed = pack_embedding(query_embedding, dim)
        source_type_filter = ""
        params: list[object] = [packed, limit * 4 if source_types else limit]
        if source_types:
            placeholders = ", ".join("?" for _ in source_types)
            source_type_filter = f"AND analyses.source_type IN ({placeholders})"
        rows = self.conn.execute(
            f"""
            WITH knn AS (
              SELECT analysis_id, distance
              FROM article_ai_embeddings
              WHERE embedding MATCH ?
              ORDER BY distance
              LIMIT ?
            )
            SELECT article_search.source_type,
                   CAST(article_search.article_id AS INTEGER) AS article_id,
                   CAST(article_search.source_id AS INTEGER) AS source_id,
                   article_search.source_title, article_search.title,
                   article_search.summary, article_search.url,
                   article_search.published, article_search.created_at,
                   analyses.ai_summary, analyses.key_points_json,
                   analyses.topics_json, analyses.keywords_json,
                   analyses.entities_json, analyses.search_aliases_json,
                   knn.distance AS relevance
            FROM knn
            JOIN article_ai_analyses AS analyses ON analyses.id = knn.analysis_id
            JOIN article_search
              ON article_search.source_type = analyses.source_type
             AND CAST(article_search.article_id AS INTEGER) = analyses.article_id
            WHERE analyses.status = 'completed' {source_type_filter}
            ORDER BY knn.distance ASC
            LIMIT ?
            """,
            [*params, *source_types, limit],
        ).fetchall()
        return [dict(row) for row in rows]
