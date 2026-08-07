"""LLM provider integration used to validate saved connection settings."""

from dataclasses import dataclass
from urllib.parse import urlparse
from uuid import uuid4

import httpx
from fastapi import HTTPException

LLM_PROVIDER_SETTING_KEY = "llm_provider"
LLM_BASE_URL_SETTING_KEY = "llm_base_url"
LLM_API_KEY_SETTING_KEY = "llm_api_key"
LLM_MODEL_SETTING_KEY = "llm_model"

LLM_SETTING_KEYS = (
    LLM_PROVIDER_SETTING_KEY,
    LLM_BASE_URL_SETTING_KEY,
    LLM_API_KEY_SETTING_KEY,
    LLM_MODEL_SETTING_KEY,
)


@dataclass
class LLMConfig:
    provider: str
    base_url: str
    api_key: str | None
    model: str


def load_llm_config(repo) -> LLMConfig | None:
    provider = repo.get(LLM_PROVIDER_SETTING_KEY)
    base_url = repo.get(LLM_BASE_URL_SETTING_KEY)
    model = repo.get(LLM_MODEL_SETTING_KEY)
    if not provider or not base_url or not model:
        return None
    return LLMConfig(
        provider=provider,
        base_url=base_url,
        api_key=repo.get(LLM_API_KEY_SETTING_KEY) or None,
        model=model,
    )


def save_llm_config(repo, config: LLMConfig) -> None:
    repo.set(LLM_PROVIDER_SETTING_KEY, config.provider)
    repo.set(LLM_BASE_URL_SETTING_KEY, config.base_url)
    repo.set(LLM_API_KEY_SETTING_KEY, config.api_key or "")
    repo.set(LLM_MODEL_SETTING_KEY, config.model)


def _extract_reply_content(provider: str, data: dict) -> str | None:
    if provider == "ollama":
        message = data.get("message")
        if isinstance(message, dict) and isinstance(message.get("content"), str):
            return str(message["content"])
        return None
    choices = data.get("choices")
    if isinstance(choices, list) and choices and isinstance(choices[0], dict):
        message = choices[0].get("message")
        if isinstance(message, dict) and isinstance(message.get("content"), str):
            return str(message["content"])
    return None


def _safe_endpoint(value: str) -> str:
    parsed = urlparse(value)
    return f"{parsed.scheme}://{parsed.hostname or 'unknown-host'}{parsed.path}"


def test_llm_connection(config: LLMConfig) -> str:
    reference_id = uuid4().hex[:12]
    base_url = config.base_url.rstrip("/")
    if config.provider == "ollama":
        url = f"{base_url}/api/chat"
        payload = {
            "model": config.model,
            "messages": [{"role": "user", "content": "Reply with: pong"}],
            "stream": False,
        }
    else:
        url = f"{base_url}/chat/completions"
        payload = {
            "model": config.model,
            "messages": [{"role": "user", "content": "Reply with: pong"}],
            "max_tokens": 8,
            "temperature": 0,
        }
    headers = {"Authorization": f"Bearer {config.api_key}"} if config.api_key else None
    try:
        response = httpx.post(url, json=payload, headers=headers, timeout=60.0)
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                "LLM connection error: Could not connect to the LLM server. "
                f"Check {_safe_endpoint(url)}. Reference ID: {reference_id}."
            ),
        ) from exc
    if response.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail=(
                "LLM upstream error: Check the provider, model, and credentials. "
                f"Upstream HTTP {response.status_code}. Reference ID: {reference_id}."
            ),
        )
    try:
        data = response.json()
    except ValueError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"LLM protocol error: Expected JSON. Reference ID: {reference_id}.",
        ) from exc
    content = _extract_reply_content(config.provider, data)
    if content is None or not content.strip():
        raise HTTPException(
            status_code=502,
            detail=f"LLM response error: No message content. Reference ID: {reference_id}.",
        )
    return content
