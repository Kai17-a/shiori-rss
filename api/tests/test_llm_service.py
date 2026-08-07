"""Unit tests for supported LLM wire protocols."""

import logging

import pytest
from fastapi import HTTPException

from api.services.llm_service import (
    LLMConfig,
    analyze_news_page,
    chat_completion,
    parse_analysis_reply,
)


@pytest.mark.parametrize(
    ("provider", "base_url", "expected_url", "response_body"),
    [
        (
            "ollama",
            "http://127.0.0.1:11434",
            "http://127.0.0.1:11434/api/chat",
            {"message": {"content": "pong"}},
        ),
        (
            "vllm",
            "http://127.0.0.1:8000/v1",
            "http://127.0.0.1:8000/v1/chat/completions",
            {"choices": [{"message": {"content": "pong"}}]},
        ),
        (
            "openai",
            "https://llm.example.com/v1",
            "https://llm.example.com/v1/chat/completions",
            {"choices": [{"message": {"content": "pong"}}]},
        ),
    ],
)
def test_chat_completion_supports_initial_providers(
    monkeypatch, provider, base_url, expected_url, response_body
):
    import api.services.llm_service as llm_module

    captured = {}

    class Response:
        status_code = 200

        def json(self):
            return response_body

    def fake_post(url, *, json, headers, timeout):
        captured.update(url=url, json=json, headers=headers, timeout=timeout)
        return Response()

    monkeypatch.setattr(llm_module.httpx, "post", fake_post)
    config = LLMConfig(
        provider=provider,
        base_url=base_url,
        api_key="test-key",
        model="test-model",
    )

    reply = chat_completion(
        config,
        [{"role": "user", "content": "ping"}],
        max_tokens=8,
    )

    assert reply == "pong"
    assert captured["url"] == expected_url
    assert captured["json"]["model"] == "test-model"
    assert captured["headers"] == {"Authorization": "Bearer test-key"}


def test_analysis_reply_accepts_optional_summary_selector():
    parsed = parse_analysis_reply(
        """{
          "site_title": "Example",
          "item_selector": "article",
          "title_selector": "h2",
          "link_selector": "a",
          "link_attribute": "href",
          "published_selector": null,
          "published_attribute": null,
          "summary_selector": ".summary"
        }"""
    )

    assert parsed["summary_selector"] == ".summary"


def test_chat_completion_reports_upstream_rejection_without_logging_api_key(
    monkeypatch, caplog
):
    import api.services.llm_service as llm_module

    class Response:
        status_code = 413
        text = "context length exceeded"

    monkeypatch.setattr(llm_module.httpx, "post", lambda *args, **kwargs: Response())
    config = LLMConfig(
        provider="ollama",
        base_url="http://127.0.0.1:11434",
        api_key="secret-key-must-not-be-logged",
        model="small-model",
    )

    with caplog.at_level(logging.ERROR), pytest.raises(HTTPException) as exc_info:
        chat_completion(
            config,
            [{"role": "user", "content": "analyze"}],
            max_tokens=1024,
            operation="news_site_analysis",
            reference_id="upstream123",
        )

    assert exc_info.value.detail.startswith("LLM upstream error:")
    assert "context window" in exc_info.value.detail
    assert "upstream HTTP 413" in exc_info.value.detail
    assert "Reference ID: upstream123" in exc_info.value.detail
    assert "llm_request_rejected" in caplog.text
    assert "context length exceeded" in caplog.text
    assert "secret-key-must-not-be-logged" not in caplog.text


def test_news_analysis_reports_invalid_llm_recipe_with_diagnostics(monkeypatch, caplog):
    import api.services.llm_service as llm_module

    monkeypatch.setattr(
        llm_module,
        "chat_completion",
        lambda *args, **kwargs: "I need more information instead of JSON.",
    )
    config = LLMConfig(
        provider="ollama",
        base_url="http://127.0.0.1:11434",
        api_key=None,
        model="small-model",
    )

    with caplog.at_level(logging.ERROR), pytest.raises(HTTPException) as exc_info:
        analyze_news_page(
            config,
            page_url="https://example.com/news?secret=query",
            html="<html><article>News</article></html>",
            reference_id="analysis123",
        )

    assert exc_info.value.detail.startswith("LLM analysis error:")
    assert "target site was fetched successfully" in exc_info.value.detail
    assert "required JSON scraping configuration" in exc_info.value.detail
    assert "Reference ID: analysis123" in exc_info.value.detail
    assert "llm_analysis_invalid" in caplog.text
    assert "https://example.com/news" in caplog.text
    assert "secret=query" not in caplog.text
    assert "I need more information" in caplog.text


def test_news_analysis_includes_failed_selector_diagnostics_on_retry(monkeypatch):
    import api.services.llm_service as llm_module

    captured_messages = []

    def complete(_config, messages, **kwargs):
        captured_messages.extend(messages)
        return """{
          "site_title": "Example",
          "item_selector": "article",
          "title_selector": "h1",
          "link_selector": "a.article-link",
          "link_attribute": "href",
          "published_selector": null,
          "published_attribute": null,
          "summary_selector": null
        }"""

    monkeypatch.setattr(llm_module, "chat_completion", complete)
    analyze_news_page(
        LLMConfig(
            provider="ollama",
            base_url="http://127.0.0.1:11434",
            api_key=None,
            model="small-model",
        ),
        page_url="https://example.com/news",
        html="<article><h1>News</h1></article>",
        retry_context={
            "previous_scrape_config": {
                "item_selector": "article",
                "title_selector": "h2 a",
                "link_selector": "a",
            },
            "item_matches": 1,
            "title_matches": 0,
            "link_matches": 0,
        },
    )

    retry_prompt = captured_messages[1]["content"]
    assert "previous scraping recipe extracted zero" in retry_prompt
    assert '"title_selector": "h2 a"' in retry_prompt
    assert '"item_matches": 1' in retry_prompt
    assert "Do not return the same selector recipe unchanged" in retry_prompt
