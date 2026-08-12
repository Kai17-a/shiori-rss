import os
from urllib.parse import urlparse

import httpx
from fastapi import HTTPException

from api.database import get_db
from api.model.models import (
    GitHubRepositoryCreate,
    GitHubRepositoryListResponse,
    GitHubRepositoryResponse,
    GitHubRepositoryUpdate,
)
from api.repositories.github_repository_repo import GitHubRepositoryRepository


class GitHubRepositoryService:
    def _verify_webhooks(self, conn, webhook_ids: list[int]) -> None:
        for webhook_id in webhook_ids:
            if conn.execute("SELECT 1 FROM webhook_endpoints WHERE id = ?", (webhook_id,)).fetchone() is None:
                raise HTTPException(status_code=422, detail="Webhook endpoint not found")

    def _parse_url(self, value: str) -> tuple[str, str, str]:
        parsed = urlparse(value)
        if parsed.scheme != "https" or parsed.hostname not in {"github.com", "www.github.com"}:
            raise HTTPException(status_code=422, detail="Enter a valid GitHub repository URL")
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) < 2:
            raise HTTPException(status_code=422, detail="Enter a valid GitHub repository URL")
        owner, repository = parts[0], parts[1].removesuffix(".git")
        if not owner or not repository:
            raise HTTPException(status_code=422, detail="Enter a valid GitHub repository URL")
        return owner, repository, f"https://github.com/{owner}/{repository}"

    def _fetch_latest(self, owner: str, repository: str) -> dict[str, object]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "shiori-feed",
        }
        if token := os.getenv("GITHUB_TOKEN"):
            headers["Authorization"] = f"Bearer {token}"
        try:
            response = httpx.get(
                f"https://api.github.com/repos/{owner}/{repository}/releases/latest",
                headers=headers,
                timeout=10.0,
                follow_redirects=True,
            )
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail="GitHub API is unavailable") from exc
        if response.status_code == 404:
            raise HTTPException(status_code=422, detail="Repository not found or has no published releases")
        if response.status_code >= 400:
            raise HTTPException(status_code=502, detail="Failed to fetch the latest GitHub release")
        data = response.json()
        tag = data.get("tag_name")
        url = data.get("html_url")
        published_at = data.get("published_at")
        if not all(isinstance(value, str) and value for value in (tag, url, published_at)):
            raise HTTPException(status_code=502, detail="GitHub returned an invalid release")
        name = data.get("name")
        body = data.get("body")
        return {
            "latest_release_name": name if isinstance(name, str) and name else tag,
            "latest_release_tag": tag,
            "latest_release_url": url,
            "latest_release_body": body[:20000] if isinstance(body, str) else None,
            "latest_release_published_at": published_at,
        }

    def list(self) -> GitHubRepositoryListResponse:
        with get_db() as conn:
            rows = GitHubRepositoryRepository(conn).find_all()
        items = [GitHubRepositoryResponse(**row) for row in rows]
        return GitHubRepositoryListResponse(items=items, total=len(items))

    def create(self, body: GitHubRepositoryCreate) -> GitHubRepositoryResponse:
        owner, repository, repository_url = self._parse_url(str(body.repository_url))
        release = self._fetch_latest(owner, repository)
        with get_db() as conn:
            repo = GitHubRepositoryRepository(conn)
            if repo.find_by_url(repository_url):
                raise HTTPException(status_code=409, detail="GitHub repository already exists")
            self._verify_webhooks(conn, body.webhook_ids)
            row = repo.insert({"owner": owner, "repository": repository, "repository_url": repository_url, **release})
            repo.set_webhook_ids(int(row["id"]), body.webhook_ids)
            row = repo.find_by_id(int(row["id"]))
            assert row is not None
        return GitHubRepositoryResponse(**row)

    def update(self, repository_id: int, body: GitHubRepositoryUpdate) -> GitHubRepositoryResponse:
        with get_db() as conn:
            repo = GitHubRepositoryRepository(conn)
            if repo.find_by_id(repository_id) is None:
                raise HTTPException(status_code=404, detail="GitHub repository not found")
            self._verify_webhooks(conn, body.webhook_ids)
            repo.set_webhook_ids(repository_id, body.webhook_ids)
            row = repo.find_by_id(repository_id)
            assert row is not None
        return GitHubRepositoryResponse(**row)

    def refresh_all(self) -> GitHubRepositoryListResponse:
        with get_db() as conn:
            repo = GitHubRepositoryRepository(conn)
            rows = repo.find_all()
            refreshed = [repo.update_release(row["id"], self._fetch_latest(row["owner"], row["repository"])) for row in rows]
        items = [GitHubRepositoryResponse(**row) for row in refreshed]
        return GitHubRepositoryListResponse(items=items, total=len(items))

    def delete(self, repository_id: int) -> None:
        with get_db() as conn:
            if not GitHubRepositoryRepository(conn).delete(repository_id):
                raise HTTPException(status_code=404, detail="GitHub repository not found")
