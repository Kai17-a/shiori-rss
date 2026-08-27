from __future__ import annotations

import json
import logging
import math
import os
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlparse

import httpx
from fastapi import HTTPException

from api.database import get_db
from api.model.models import ITTrendItem, ITTrendLink, ITTrendResponse
from api.repositories.it_trend_repo import ITTrendRepository
from api.repositories.settings_repo import SettingsRepository
from api.services.llm_service import chat_completion, load_llm_config

logger = logging.getLogger(__name__)

WINDOW_HOURS = 24
MAX_CANDIDATES_PER_SOURCE = 20


@dataclass
class TrendCandidate:
    key: str
    title: str
    description: str
    url: str
    source: str
    engagement: int
    published_at: datetime

    def prompt_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "title": self.title,
            "description": self.description[:300],
            "source": self.source,
            "engagement": self.engagement,
        }


class ITTrendService:
    def get(self) -> ITTrendResponse:
        cached = self._load_cache()
        if cached is None:
            return self._empty_response()
        generated_at = cached.generated_at
        if generated_at is None or generated_at.astimezone().date() != datetime.now().astimezone().date():
            return self._empty_response()
        return cached

    def research(self) -> ITTrendResponse:
        now = datetime.now(UTC)
        try:
            candidates = self._fetch_hacker_news(now) + self._fetch_github(now)
            if not candidates:
                raise HTTPException(
                    status_code=502, detail="Trend sources returned no recent items"
                )
            response = self._build_response(candidates, now)
            self._save_cache(response, now + timedelta(days=1))
            return response
        except Exception as exc:
            if isinstance(exc, HTTPException):
                raise
            logger.exception("it_trends_research_failed")
            raise HTTPException(
                status_code=502, detail="Could not research IT trends"
            ) from exc

    def _empty_response(self) -> ITTrendResponse:
        return ITTrendResponse(
            generated_at=None,
            window_hours=WINDOW_HOURS,
            region="Global",
            sources=[],
            ai_summarized=False,
            stale=False,
            items=[],
        )

    def _load_cache(self) -> ITTrendResponse | None:
        with get_db() as conn:
            row = ITTrendRepository(conn).get()
        if row is None:
            return None
        try:
            return ITTrendResponse.model_validate_json(row["payload_json"])
        except (ValueError, TypeError):
            logger.warning("invalid_it_trend_cache", exc_info=True)
            return None

    def _save_cache(self, response: ITTrendResponse, expires_at: datetime) -> None:
        if response.generated_at is None:
            raise ValueError("A researched trend response must have generated_at")
        with get_db() as conn:
            ITTrendRepository(conn).save(
                response.generated_at.isoformat(),
                expires_at.isoformat(),
                response.model_dump_json(),
            )

    def _fetch_hacker_news(self, now: datetime) -> list[TrendCandidate]:
        try:
            ids_response = httpx.get(
                "https://hacker-news.firebaseio.com/v0/topstories.json",
                timeout=10.0,
                follow_redirects=True,
            )
            ids_response.raise_for_status()
            ids = ids_response.json()
            def fetch_item(item_id: int) -> dict[str, Any] | None:
                try:
                    response = httpx.get(
                        f"https://hacker-news.firebaseio.com/v0/item/{item_id}.json",
                        timeout=10.0,
                        follow_redirects=True,
                    )
                    response.raise_for_status()
                    item = response.json()
                    return item if isinstance(item, dict) else None
                except (httpx.HTTPError, ValueError):
                    return None

            selected_ids = ids[:MAX_CANDIDATES_PER_SOURCE]
            with ThreadPoolExecutor(max_workers=8) as executor:
                fetched_items = executor.map(fetch_item, selected_ids)

            candidates: list[TrendCandidate] = []
            for item_id, item in zip(selected_ids, fetched_items, strict=True):
                if (
                    item is None
                    or item.get("type") != "story"
                    or not item.get("title")
                ):
                    continue
                published_at = datetime.fromtimestamp(int(item.get("time", 0)), UTC)
                if published_at < now - timedelta(hours=WINDOW_HOURS):
                    continue
                candidates.append(
                    TrendCandidate(
                        key=f"hn-{item_id}",
                        title=str(item["title"]),
                        description="",
                        url=self._safe_url(
                            item.get("url"),
                            f"https://news.ycombinator.com/item?id={item_id}",
                        ),
                        source="Hacker News",
                        engagement=max(0, int(item.get("score", 0)))
                        + max(0, int(item.get("descendants", 0))),
                        published_at=published_at,
                    )
                )
            return candidates
        except (httpx.HTTPError, ValueError, TypeError):
            logger.warning("hacker_news_trend_fetch_failed", exc_info=True)
            return []

    def _safe_url(self, value: object, fallback: str) -> str:
        if isinstance(value, str):
            parsed = urlparse(value)
            if parsed.scheme in {"http", "https"} and parsed.hostname:
                return value
        return fallback

    def _fetch_github(self, now: datetime) -> list[TrendCandidate]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "shiori-feed",
        }
        if token := os.getenv("GITHUB_TOKEN"):
            headers["Authorization"] = f"Bearer {token}"
        created_after = (now - timedelta(hours=WINDOW_HOURS)).date().isoformat()
        try:
            response = httpx.get(
                "https://api.github.com/search/repositories",
                params={
                    "q": f"created:>={created_after} stars:>=5",
                    "sort": "stars",
                    "order": "desc",
                    "per_page": MAX_CANDIDATES_PER_SOURCE,
                },
                headers=headers,
                timeout=10.0,
                follow_redirects=True,
            )
            response.raise_for_status()
            items = response.json().get("items", [])
            candidates = []
            for item in items:
                if (
                    not isinstance(item, dict)
                    or not item.get("full_name")
                    or not item.get("html_url")
                ):
                    continue
                published_at = datetime.fromisoformat(
                    str(item["created_at"]).replace("Z", "+00:00")
                )
                candidates.append(
                    TrendCandidate(
                        key=f"gh-{item.get('id')}",
                        title=str(item["full_name"]),
                        description=str(item.get("description") or ""),
                        url=str(item["html_url"]),
                        source="GitHub",
                        engagement=max(0, int(item.get("stargazers_count", 0))),
                        published_at=published_at,
                    )
                )
            return candidates
        except (httpx.HTTPError, ValueError, TypeError, AttributeError):
            logger.warning("github_trend_fetch_failed", exc_info=True)
            return []

    def _build_response(
        self, candidates: list[TrendCandidate], now: datetime
    ) -> ITTrendResponse:
        groups = self._summarize_with_ai(candidates)
        ai_summarized = bool(groups)
        items = (
            self._items_from_groups(candidates, groups)
            if groups
            else self._fallback_items(candidates)
        )
        return ITTrendResponse(
            generated_at=now,
            window_hours=WINDOW_HOURS,
            region="Global",
            sources=sorted({candidate.source for candidate in candidates}),
            ai_summarized=ai_summarized,
            stale=False,
            items=items,
        )

    def _summarize_with_ai(
        self, candidates: list[TrendCandidate]
    ) -> list[dict[str, Any]] | None:
        with get_db() as conn:
            config = load_llm_config(SettingsRepository(conn))
        if config is None:
            return None
        prompt = (
            "以下は直近24時間のIT関連候補です。重複・同一テーマを統合し、重要度順に最大10件を日本語で返してください。"
            "候補にない事実を追加せず、summaryは80文字以内にしてください。JSONオブジェクトのみを返し、形式は"
            '{"trends":[{"title":"...","summary":"...","category":"AI|Security|Development|Data|Cloud|Other",'
            '"candidate_keys":["..."]}]} です。\n候補:\n'
            + json.dumps(
                [candidate.prompt_dict() for candidate in candidates],
                ensure_ascii=False,
            )
        )
        try:
            reply = chat_completion(
                config,
                [
                    {
                        "role": "system",
                        "content": "You are an IT trend analyst. Return valid JSON only.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=1800,
            )
            match = re.search(r"\{.*\}", reply, re.DOTALL)
            data = json.loads(match.group(0) if match else reply)
            trends = data.get("trends")
            return trends if isinstance(trends, list) else None
        except (HTTPException, ValueError, TypeError, json.JSONDecodeError):
            logger.warning("it_trend_ai_summary_failed", exc_info=True)
            return None

    def _items_from_groups(
        self, candidates: list[TrendCandidate], groups: list[dict[str, Any]]
    ) -> list[ITTrendItem]:
        by_key = {candidate.key: candidate for candidate in candidates}
        prepared: list[tuple[float, dict[str, Any], list[TrendCandidate]]] = []
        for group in groups[:10]:
            if not isinstance(group, dict):
                continue
            members = [
                by_key[key] for key in group.get("candidate_keys", []) if key in by_key
            ]
            title, summary = group.get("title"), group.get("summary")
            if (
                not members
                or not isinstance(title, str)
                or not isinstance(summary, str)
            ):
                continue
            prepared.append(
                (sum(self._candidate_score(item) for item in members), group, members)
            )
        prepared.sort(key=lambda row: row[0], reverse=True)
        return [
            self._make_item(rank, score, group, members)
            for rank, (score, group, members) in enumerate(prepared, 1)
        ]

    def _fallback_items(self, candidates: list[TrendCandidate]) -> list[ITTrendItem]:
        ranked = sorted(candidates, key=self._candidate_score, reverse=True)[:10]
        return [
            self._make_item(
                rank,
                self._candidate_score(candidate),
                {
                    "title": candidate.title,
                    "summary": candidate.description
                    or f"{candidate.source}で注目を集めている新しいITトピックです。",
                    "category": "Other",
                },
                [candidate],
            )
            for rank, candidate in enumerate(ranked, 1)
        ]

    def _candidate_score(self, candidate: TrendCandidate) -> float:
        age_hours = max(
            0.0, (datetime.now(UTC) - candidate.published_at).total_seconds() / 3600
        )
        return math.log1p(candidate.engagement) * max(0.25, 1 - age_hours / 32)

    def _make_item(
        self,
        rank: int,
        raw_score: float,
        group: dict[str, Any],
        members: list[TrendCandidate],
    ) -> ITTrendItem:
        score = min(100, max(1, round(raw_score * 12)))
        return ITTrendItem(
            id=f"trend-{rank}-{members[0].key}",
            rank=rank,
            title=str(group["title"])[:160],
            summary=str(group["summary"])[:400],
            category=str(group.get("category") or "Other")[:40],
            momentum="surging"
            if score >= 80
            else "rising"
            if score >= 50
            else "steady",
            score=score,
            source_count=len({member.source for member in members}),
            mention_count=sum(member.engagement for member in members),
            sources=sorted({member.source for member in members}),
            related_links=[
                ITTrendLink(title=member.title, url=member.url, source=member.source)
                for member in members[:3]
            ],
        )
