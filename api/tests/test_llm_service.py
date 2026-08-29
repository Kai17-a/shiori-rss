import pytest
from fastapi import HTTPException

from api.services.llm_service import (
    LLMConfig,
    chat_completion,
    chat_completion_stream,
    probe_temperature_support,
    test_llm_connection as check_connection,
)


@pytest.mark.parametrize(
    ("provider", "expected_path", "response"),
    [
        ("ollama", "/api/chat", {"message": {"content": "pong"}}),
        ("vllm", "/chat/completions", {"choices": [{"message": {"content": "pong"}}]}),
        (
            "openai",
            "/chat/completions",
            {"choices": [{"message": {"content": "pong"}}]},
        ),
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


def test_chat_completion_sends_temperature_zero_by_default(monkeypatch):
    captured = {}

    class Result:
        status_code = 200

        def json(self):
            return {"choices": [{"message": {"content": "pong"}}]}

    def fake_post(url, **kwargs):
        captured["payload"] = kwargs["json"]
        return Result()

    monkeypatch.setattr("api.services.llm_service.httpx.post", fake_post)
    chat_completion(
        LLMConfig("openai", "https://llm.example.com/v1", None, "model"),
        [{"role": "user", "content": "hi"}],
        max_tokens=8,
    )

    assert captured["payload"]["temperature"] == 0


def test_chat_completion_omits_temperature_when_unsupported(monkeypatch):
    captured = {}

    class Result:
        status_code = 200

        def json(self):
            return {"choices": [{"message": {"content": "pong"}}]}

    def fake_post(url, **kwargs):
        captured["payload"] = kwargs["json"]
        return Result()

    monkeypatch.setattr("api.services.llm_service.httpx.post", fake_post)
    chat_completion(
        LLMConfig(
            "openai",
            "https://llm.example.com/v1",
            None,
            "o3",
            supports_temperature=False,
        ),
        [{"role": "user", "content": "hi"}],
        max_tokens=8,
    )

    assert "temperature" not in captured["payload"]


def test_probe_temperature_support_detects_a_temperature_rejection(monkeypatch):
    class Result:
        status_code = 400
        text = (
            '{"error": {"message": "Unsupported value: \'temperature\' does not '
            'support 0 with this model. Only the default (1) value is supported."}}'
        )

    monkeypatch.setattr(
        "api.services.llm_service.httpx.post", lambda *args, **kwargs: Result()
    )

    assert probe_temperature_support(
        LLMConfig("openai", "https://llm.example.com/v1", None, "o3")
    ) is False


def test_probe_temperature_support_defaults_to_true_on_other_failures(monkeypatch):
    class Result:
        status_code = 401
        text = '{"error": {"message": "Invalid API key"}}'

    monkeypatch.setattr(
        "api.services.llm_service.httpx.post", lambda *args, **kwargs: Result()
    )

    assert probe_temperature_support(
        LLMConfig("openai", "https://llm.example.com/v1", None, "model")
    ) is True


def test_probe_temperature_support_skips_the_network_call_for_ollama(monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("should not make a network call for ollama")

    monkeypatch.setattr("api.services.llm_service.httpx.post", fail_if_called)

    assert probe_temperature_support(
        LLMConfig("ollama", "https://llm.example.com/v1", None, "model")
    ) is True


def test_connection_rejects_missing_message_content(monkeypatch):
    class Result:
        status_code = 200

        def json(self):
            return {"choices": []}

    monkeypatch.setattr(
        "api.services.llm_service.httpx.post", lambda *args, **kwargs: Result()
    )

    with pytest.raises(HTTPException) as exc:
        check_connection(
            LLMConfig("openai", "https://llm.example.com/v1", None, "model")
        )

    assert exc.value.status_code == 502
    assert "No message content" in exc.value.detail


@pytest.mark.parametrize(
    ("provider", "lines"),
    [
        (
            "openai",
            [
                'data: {"choices":[{"delta":{"content":"Hello "}}]}',
                'data: {"choices":[{"delta":{"content":"world"}}]}',
                "data: [DONE]",
            ],
        ),
        (
            "ollama",
            [
                '{"message":{"content":"Hello "},"done":false}',
                '{"message":{"content":"world"},"done":true}',
            ],
        ),
    ],
)
def test_chat_completion_stream_yields_provider_deltas(monkeypatch, provider, lines):
    class StreamResult:
        status_code = 200

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def iter_lines(self):
            return iter(lines)

    monkeypatch.setattr(
        "api.services.llm_service.httpx.stream",
        lambda *args, **kwargs: StreamResult(),
    )

    deltas = list(
        chat_completion_stream(
            LLMConfig(provider, "https://llm.example.com/v1", None, "model"),
            [{"role": "user", "content": "Hi"}],
            max_tokens=20,
        )
    )

    assert deltas == ["Hello ", "world"]
