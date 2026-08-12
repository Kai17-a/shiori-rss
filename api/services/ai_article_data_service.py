import json
from typing import Literal

from api.database import get_db
from api.model.models import (
    AIArticleAnalysisListResponse,
    AIArticleAnalysisDeleteFailedResponse,
    AIArticleAnalysisResponse,
)
from api.repositories.article_analysis_repo import ArticleAnalysisRepository


class AIArticleDataService:
    def list(
        self,
        *,
        q: str | None = None,
        source_type: Literal["rss", "custom"] | None = None,
        status: Literal["completed", "failed"] | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> AIArticleAnalysisListResponse:
        with get_db() as conn:
            repo = ArticleAnalysisRepository(conn)
            total = repo.count_all(q=q, source_type=source_type, status=status)
            failed_total = repo.count_all(q=None, source_type=None, status="failed")
            total_pages = (total + per_page - 1) // per_page if total else 0
            if total_pages and page > total_pages:
                page = total_pages
            rows = repo.find_all(
                q=q,
                source_type=source_type,
                status=status,
                limit=per_page,
                offset=(page - 1) * per_page,
            )
            items = []
            for row in rows:
                row["key_points"] = json.loads(row.pop("key_points_json"))
                row["topics"] = json.loads(row.pop("topics_json"))
                row["keywords"] = json.loads(row.pop("keywords_json"))
                row["entities"] = json.loads(row.pop("entities_json"))
                row.pop("content_hash", None)
                items.append(AIArticleAnalysisResponse(**row))
            return AIArticleAnalysisListResponse(
                items=items,
                total=total,
                failed_total=failed_total,
                page=page,
                per_page=per_page,
                total_pages=total_pages,
            )

    def delete_failed(self) -> AIArticleAnalysisDeleteFailedResponse:
        with get_db() as conn:
            deleted_count = ArticleAnalysisRepository(conn).delete_failed()
        return AIArticleAnalysisDeleteFailedResponse(deleted_count=deleted_count)
