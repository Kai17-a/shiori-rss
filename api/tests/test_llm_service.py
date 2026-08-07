import pytest
from fastapi import HTTPException

from api.services.llm_service import LLMConfig, test_llm_connection as check_connection


@pytest.mark.parametrize(
    ("provider", "expected_path", "response"),
    [
        ("ollama", "/api/chat", {"message": {"content": "pong"}}),
        ("vllm", "/chat/completions", {"choices": [{"message": {"content": "pong"}}]}),
        ("openai", "/chat/completions", {"choices": [{"message": {"content": "pong"}}]}),
    ],
)
def test_connection_supports_configured_providers(
    monkeypatch, provider, expected_path, response
):
    captured = {}

    class Result:
        status_code = 200

        def json(self):
            return response

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured["kwargs"] = kwargs
        return Result()

    monkeypatch.setattr("api.services.llm_service.httpx.post", fake_post)
    reply = check_connection(
        LLMConfig(provider, "https://llm.example.com/v1", "secret", "model")
    )

    assert reply == "pong"
    assert captured["url"].endswith(expected_path)
    assert captured["kwargs"]["headers"] == {"Authorization": "Bearer secret"}


def test_connection_rejects_missing_message_content(monkeypatch):
    class Result:
        status_code = 200

        def json(self):
            return {"choices": []}

    monkeypatch.setattr(
        "api.services.llm_service.httpx.post", lambda *args, **kwargs: Result()
    )

    with pytest.raises(HTTPException) as exc:
        check_connection(LLMConfig("openai", "https://llm.example.com/v1", None, "model"))

    assert exc.value.status_code == 502
    assert "No message content" in exc.value.detail
