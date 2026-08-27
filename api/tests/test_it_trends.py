from datetime import UTC, datetime

from api.model.models import ITTrendItem, ITTrendLink, ITTrendResponse
import sqlite3

from api.repositories.it_trend_repo import ITTrendRepository
from api.routers.it_trends import get_it_trends, research_it_trends
from api.services.it_trend_service import ITTrendService


class FakeITTrendService(ITTrendService):
    def __init__(self) -> None:
        self.get_calls = 0
        self.research_calls = 0

    def _response(self) -> ITTrendResponse:
        return ITTrendResponse(
            generated_at=datetime(2026, 8, 27, 3, tzinfo=UTC),
            window_hours=24,
            region="Global",
            sources=["GitHub", "Hacker News"],
            ai_summarized=True,
            stale=False,
            items=[
                ITTrendItem(
                    id="trend-1",
                    rank=1,
                    title="AIエージェント開発",
                    summary="複数の開発者コミュニティで関心が高まっています。",
                    category="AI",
                    momentum="surging",
                    score=92,
                    source_count=2,
                    mention_count=180,
                    sources=["GitHub", "Hacker News"],
                    related_links=[
                        ITTrendLink(
                            title="Example", url="https://example.com", source="GitHub"
                        )
                    ],
                )
            ],
        )

    def get(self) -> ITTrendResponse:
        self.get_calls += 1
        return self._response()

    def research(self) -> ITTrendResponse:
        self.research_calls += 1
        return self._response()


def test_it_trends_get_and_research_are_separate_actions():
    service = FakeITTrendService()
    response = get_it_trends(service)
    researched = research_it_trends(service)

    assert response.items[0].title == "AIエージェント開発"
    assert researched.ai_summarized is True
    assert service.get_calls == 1
    assert service.research_calls == 1


def test_get_without_a_saved_result_does_not_start_external_research(monkeypatch):
    service = ITTrendService()
    monkeypatch.setattr(service, "_load_cache", lambda: None)
    monkeypatch.setattr(service, "_fetch_hacker_news", lambda _now: (_ for _ in ()).throw(AssertionError))

    response = service.get()

    assert response.generated_at is None
    assert response.items == []


def test_saving_research_results_overwrites_the_single_snapshot():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE it_trend_snapshots (id INTEGER PRIMARY KEY, generated_at TEXT, "
        "expires_at TEXT, payload_json TEXT, updated_at TEXT DEFAULT CURRENT_TIMESTAMP)"
    )
    repo = ITTrendRepository(conn)

    repo.save("first", "first", '{"value": 1}')
    repo.save("second", "second", '{"value": 2}')

    row = repo.get()
    assert row is not None
    assert row["generated_at"] == "second"
    assert row["payload_json"] == '{"value": 2}'
    assert conn.execute("SELECT COUNT(*) FROM it_trend_snapshots").fetchone()[0] == 1
