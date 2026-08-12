from __future__ import annotations

from urllib.parse import urlparse

import httpx
from fastapi import HTTPException


EMBED_TITLE_MAX = 256
# Keep summaries short enough that a 10-embed chunk stays below Discord's
# 6000-character per-message total (title + description per embed) and below
# Slack's 3000-character section block text limit.
NOTIFICATION_SUMMARY_MAX = 300


def _truncate(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 1].rstrip() + "…"


def _is_teams_webhook(hostname: str, path: str) -> bool:
    legacy_webhook = hostname.endswith(".webhook.office.com") and path.startswith(
        "/webhookb2/"
    )
    workflow_webhook = hostname.endswith(".logic.azure.com") and path.startswith(
        "/workflows/"
    )
    power_platform_webhook = (
        hostname.endswith(".api.powerplatform.com")
        and "/workflows/" in path
        and "/triggers/" in path
    )
    return legacy_webhook or workflow_webhook or power_platform_webhook


def detect_webhook_service(webhook_url: str) -> str:
    parsed = urlparse(webhook_url)
    hostname = parsed.hostname or ""
    path = parsed.path

    discord_hosts = {
        "discord.com",
        "www.discord.com",
        "discordapp.com",
        "www.discordapp.com",
    }
    if (
        parsed.scheme in {"http", "https"}
        and hostname in discord_hosts
        and path.startswith("/api/webhooks/")
    ):
        return "discord"

    if (
        parsed.scheme in {"http", "https"}
        and hostname == "hooks.slack.com"
        and path.startswith("/services/")
    ):
        parts = [part for part in path.split("/") if part]
        if len(parts) == 4 and parts[0] == "services":
            return "slack"

    if parsed.scheme == "https" and _is_teams_webhook(hostname, path):
        return "teams"

    raise HTTPException(
        status_code=422,
        detail="Webhook URL must be a Discord, Slack, or Microsoft Teams webhook URL",
    )


def _build_teams_card(body: list[dict[str, object]]) -> dict[str, object]:
    return {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "contentUrl": None,
                "content": {
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "type": "AdaptiveCard",
                    "version": "1.2",
                    "body": body,
                },
            }
        ],
    }


def build_webhook_payload(webhook_service: str, *, content: str) -> dict[str, object]:
    if webhook_service == "discord":
        return {"username": "Shiori Feed", "content": content}
    if webhook_service == "slack":
        return {
            "username": "Shiori Feed",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": content,
                    },
                }
            ],
        }
    if webhook_service == "teams":
        return _build_teams_card(
            [{"type": "TextBlock", "text": content, "weight": "Bolder"}]
        )
    raise ValueError(f"Unsupported webhook service: {webhook_service}")


def build_rss_notification_payload(
    webhook_service: str,
    *,
    feed_title: str,
    articles: list[dict[str, object]],
    total_articles: int | None = None,
    chunk_index: int = 1,
    chunk_count: int = 1,
    include_summary: bool = True,
    icon_url: str | None = None,
) -> dict[str, object]:
    if webhook_service == "discord":
        article_count = total_articles if total_articles is not None else len(articles)
        embeds = [
            {
                "title": _truncate(str(article["title"]), EMBED_TITLE_MAX),
                "url": str(article["url"]),
                **(
                    {
                        "description": _truncate(
                            str(article["summary"]), NOTIFICATION_SUMMARY_MAX
                        )
                    }
                    if include_summary and article.get("summary")
                    else {}
                ),
            }
            for article in articles
        ]
        content = f"**{feed_title}** - **New articles** ({article_count} items)"
        if chunk_count > 1:
            content = f"{content} [{chunk_index}]"
        return {
            "username": "Shiori Feed",
            "content": content,
            "embeds": embeds,
            **({"avatar_url": icon_url} if icon_url else {}),
        }

    if webhook_service == "slack":
        article_count = total_articles if total_articles is not None else len(articles)
        header_text = f"📰 {feed_title} - 新着ニュース ({article_count}件)"
        if chunk_count > 1:
            header_text = f"{header_text} [{chunk_index}]"
        blocks: list[dict[str, object]] = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": header_text,
                },
            }
        ]
        for article in articles:
            title = _truncate(str(article["title"]), EMBED_TITLE_MAX)
            url = str(article["url"])
            summary = article.get("summary")
            text = f"• <{url}|{title}>"
            if include_summary and summary:
                text = f"{text}\n{_truncate(str(summary), NOTIFICATION_SUMMARY_MAX)}"
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": text,
                    },
                }
            )
        return {"username": "Shiori Feed", "blocks": blocks}

    if webhook_service == "teams":
        article_count = total_articles if total_articles is not None else len(articles)
        header_text = f"{feed_title} - New articles ({article_count} items)"
        if chunk_count > 1:
            header_text = f"{header_text} [{chunk_index}]"
        body: list[dict[str, object]] = [
            {
                "type": "TextBlock",
                "text": header_text,
                "size": "Medium",
                "weight": "Bolder",
                "wrap": True,
            }
        ]
        for article in articles:
            title = _truncate(str(article["title"]), EMBED_TITLE_MAX)
            url = str(article["url"])
            article_body: list[dict[str, object]] = [
                {
                    "type": "TextBlock",
                    "text": f"- [{title}]({url})",
                    "weight": "Bolder",
                    "wrap": True,
                }
            ]
            if include_summary and article.get("summary"):
                article_body.append(
                    {
                        "type": "TextBlock",
                        "text": _truncate(
                            str(article["summary"]), NOTIFICATION_SUMMARY_MAX
                        ),
                        "spacing": "Small",
                        "wrap": True,
                        "isSubtle": True,
                    }
                )
            body.append(
                {
                    "type": "Container",
                    "spacing": "Medium",
                    "items": article_body,
                }
            )
        return _build_teams_card(body)

    raise ValueError(f"Unsupported webhook service: {webhook_service}")


def send_webhook(webhook_url: str, payload: dict[str, object]) -> httpx.Response:
    return httpx.post(webhook_url, json=payload, timeout=5.0)
