from datetime import UTC, datetime

from api.model.models import ITTrendItem, ITTrendLink, ITTrendResponse
from api.routers.it_trends import get_it_trends, refresh_it_trends
from api.services.it_trend_service import ITTrendService


class FakeITTrendService(ITTrendService):
    def __init__(self) -> None:
        self.force_values: list[bool] = []

    def get(self, *, force: bool = False) -> ITTrendResponse:
        self.force_values.append(force)
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


def test_it_trends_get_and_force_refresh():
    service = FakeITTrendService()
    response = get_it_trends(service)
    refreshed = refresh_it_trends(service)

    assert response.items[0].title == "AIエージェント開発"
    assert refreshed.ai_summarized is True
    assert service.force_values == [False, True]
