"""LLM provider integration for connection testing and news page analysis."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from collections.abc import Iterator
from typing import Literal
from urllib.parse import urlparse
from uuid import uuid4

import httpx
from fastapi import HTTPException

logger = logging.getLogger(__name__)

LLM_PROVIDER_SETTING_KEY = "llm_provider"
LLM_BASE_URL_SETTING_KEY = "llm_base_url"
LLM_API_KEY_SETTING_KEY = "llm_api_key"
LLM_MODEL_SETTING_KEY = "llm_model"
LLM_EMBEDDING_MODEL_SETTING_KEY = "embedding_model"
# The currently configured embedding model's native vector dimension.
# Derived (not user-set) by settings_service whenever embedding_model is
# saved, from the actual length of a test embedding call. Read by
# article_search_repo.vector_search() and by the Rust batch to size/pack
# vectors consistently with the article_ai_embeddings table's current width.
LLM_EMBEDDING_DIM_SETTING_KEY = "embedding_dim"

# Whether the configured model accepts a custom `temperature`. Some
# OpenAI-compatible reasoning models (o1/o3/gpt-5 series, etc.) reject any
# `temperature` other than their fixed default and return HTTP 400 on every
# single request. Derived (not user-set) by settings_service via
# probe_temperature_support() whenever the LLM connection is saved or
# tested, so chat_completion can omit the field on every subsequent call
# instead of paying a failing request on every one of them.
LLM_TEMPERATURE_SUPPORTED_SETTING_KEY = "llm_temperature_supported"

# Applies to every HTTP call this module makes to the LLM server (chat,
# streaming chat, embeddings, connection tests, news-site analysis). Default
# matches the longest timeout any of those calls used before this setting
# existed (news-site analysis, which sends a full page of HTML and asks for
# a generated scraping recipe) so making it configurable doesn't shrink
# anyone's existing timeout.
LLM_TIMEOUT_SETTING_KEY = "llm_request_timeout_seconds"
LLM_DEFAULT_TIMEOUT_SECONDS = 90
LLM_MIN_TIMEOUT_SECONDS = 5
LLM_MAX_TIMEOUT_SECONDS = 600

# provider/base_url/model are required for an LLMConfig to exist at all
# (see load_llm_config). embedding_model is deliberately NOT in this tuple:
# it's an optional add-on to an already-configured chat LLM connection, not
# part of what makes the connection valid.
LLM_SETTING_KEYS = (
    LLM_PROVIDER_SETTING_KEY,
    LLM_BASE_URL_SETTING_KEY,
    LLM_API_KEY_SETTING_KEY,
    LLM_MODEL_SETTING_KEY,
)

MAX_HTML_CHARS = 50000
LOG_PREVIEW_CHARS = 500

LLMOperation = Literal[
    "connection_test", "news_site_analysis", "chat_completion", "embedding"
]

ANALYSIS_SYSTEM_PROMPT = """You analyze the HTML of a news site and design a scraping recipe.
Return ONLY a JSON object with these keys:
- "site_title": human-readable name of the site (string)
- "item_selector": CSS selector matching each news article container (string)
- "title_selector": CSS selector for the article title inside one item (string)
- "link_selector": CSS selector for the article link inside one item (string)
- "link_attribute": attribute that holds the article URL, usually "href" (string)
- "published_selector": CSS selector for the publish date inside one item (string or null)
- "published_attribute": attribute holding the date, or null to use the element text (string or null)
- "summary_selector": CSS selector for an article summary inside one item (string or null)
Selectors must be relative to one item element. Do not include explanations or code fences."""

SCRAPE_CONFIG_REQUIRED_KEYS = (
    "site_title",
    "item_selector",
    "title_selector",
    "link_selector",
    "link_attribute",
)


@dataclass
class LLMConfig:
    provider: str
    base_url: str
    api_key: str | None
    model: str
    embedding_model: str | None = None
    timeout_seconds: int = LLM_DEFAULT_TIMEOUT_SECONDS
    supports_temperature: bool = True


def new_diagnostic_reference() -> str:
    return uuid4().hex[:12]


def _safe_url(value: str) -> str:
    parsed = urlparse(value)
    hostname = parsed.hostname or "unknown-host"
    try:
        port = f":{parsed.port}" if parsed.port else ""
    except ValueError:
        port = ""
    return f"{parsed.scheme}://{hostname}{port}{parsed.path}"


def _safe_preview(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()[:LOG_PREVIEW_CHARS]


def _operation_label(operation: LLMOperation) -> str:
    return {
        "connection_test": "LLM connection test",
        "news_site_analysis": "news-site analysis",
        "chat_completion": "LLM request",
        "embedding": "embedding request",
    }[operation]


def _upstream_error_detail(
    status_code: int, operation: LLMOperation, reference_id: str
) -> str:
    label = _operation_label(operation)
    if status_code in {401, 403}:
        reason = "LLM authentication failed. Check the saved API key."
    elif status_code == 404:
        reason = "The LLM endpoint or model was not found. Check the base URL and model name."
    elif status_code == 429:
        reason = (
            "The LLM server is busy or rate-limited. Retry after it becomes available."
        )
    elif status_code in {400, 413, 422}:
        if operation == "news_site_analysis":
            reason = (
                "The LLM server rejected the request. The HTML may exceed the model "
                "context window."
            )
        else:
            reason = (
                "The LLM server rejected the request. Check the provider, model, and "
                "request settings."
            )
    else:
        reason = "The LLM server failed while processing the request."
    return (
        f"LLM upstream error: {reason} Stage: {label}; upstream HTTP {status_code}. "
        f"Reference ID: {reference_id}."
    )


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
        embedding_model=repo.get(LLM_EMBEDDING_MODEL_SETTING_KEY) or None,
        timeout_seconds=repo.get_int(LLM_TIMEOUT_SETTING_KEY, LLM_DEFAULT_TIMEOUT_SECONDS),
        supports_temperature=repo.get_bool(
            LLM_TEMPERATURE_SUPPORTED_SETTING_KEY, default=True
        ),
    )


def save_llm_config(repo, config: LLMConfig) -> None:
    repo.set(LLM_PROVIDER_SETTING_KEY, config.provider)
    repo.set(LLM_BASE_URL_SETTING_KEY, config.base_url)
    repo.set(LLM_API_KEY_SETTING_KEY, config.api_key or "")
    repo.set(LLM_MODEL_SETTING_KEY, config.model)
    repo.set(LLM_EMBEDDING_MODEL_SETTING_KEY, config.embedding_model or "")
    repo.set(LLM_TIMEOUT_SETTING_KEY, str(config.timeout_seconds))
    repo.set_bool(LLM_TEMPERATURE_SUPPORTED_SETTING_KEY, config.supports_temperature)


def _extract_reply_content(provider: str, data: dict) -> str | None:
    if provider == "ollama":
        message = data.get("message")
        if isinstance(message, dict):
            content = message.get("content")
            return str(content) if isinstance(content, str) else None
        return None
    choices = data.get("choices")
    if isinstance(choices, list) and choices:
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        if isinstance(message, dict):
            content = message.get("content")
            return str(content) if isinstance(content, str) else None
    return None


def chat_completion(
    config: LLMConfig,
    messages: list[dict],
    *,
    max_tokens: int,
    timeout: float | None = None,
    operation: LLMOperation = "chat_completion",
    reference_id: str | None = None,
) -> str:
    reference_id = reference_id or new_diagnostic_reference()
    timeout = timeout if timeout is not None else config.timeout_seconds
    base_url = config.base_url.rstrip("/")
    if config.provider == "ollama":
        url = f"{base_url}/api/chat"
        payload: dict = {
            "model": config.model,
            "messages": messages,
            "stream": False,
        }
    else:
        url = f"{base_url}/chat/completions"
        payload = {
            "model": config.model,
            "messages": messages,
            "max_tokens": max_tokens,
        }
        if config.supports_temperature:
            payload["temperature"] = 0

    headers = {"Authorization": f"Bearer {config.api_key}"} if config.api_key else None
    try:
        response = httpx.post(url, json=payload, headers=headers, timeout=timeout)
    except httpx.HTTPError as exc:
        logger.error(
            "llm_connection_failed reference_id=%s operation=%s provider=%s model=%s "
            "endpoint=%s exception=%s",
            reference_id,
            operation,
            config.provider,
            config.model,
            _safe_url(url),
            type(exc).__name__,
        )
        raise HTTPException(
            status_code=502,
            detail=(
                f"LLM connection error: Could not connect to the LLM server during "
                f"{_operation_label(operation)}. "
                f"Check the base URL and network path. Reference ID: {reference_id}."
            ),
        ) from exc

    if response.status_code >= 400:
        logger.error(
            "llm_request_rejected reference_id=%s operation=%s provider=%s model=%s "
            "endpoint=%s upstream_status=%s response_preview=%r",
            reference_id,
            operation,
            config.provider,
            config.model,
            _safe_url(url),
            response.status_code,
            _safe_preview(getattr(response, "text", "")),
        )
        raise HTTPException(
            status_code=502,
            detail=_upstream_error_detail(
                response.status_code, operation, reference_id
            ),
        )

    try:
        data = response.json()
    except ValueError as exc:
        logger.error(
            "llm_protocol_invalid reference_id=%s operation=%s provider=%s model=%s "
            "endpoint=%s response_preview=%r",
            reference_id,
            operation,
            config.provider,
            config.model,
            _safe_url(url),
            _safe_preview(getattr(response, "text", "")),
        )
        raise HTTPException(
            status_code=502,
            detail=(
                f"LLM protocol error: The server returned a non-JSON response during "
                f"{_operation_label(operation)}. Check the provider type and base URL. "
                f"Reference ID: {reference_id}."
            ),
        ) from exc

    content = _extract_reply_content(config.provider, data)
    if content is None or not content.strip():
        logger.error(
            "llm_content_missing reference_id=%s operation=%s provider=%s model=%s "
            "endpoint=%s response_preview=%r",
            reference_id,
            operation,
            config.provider,
            config.model,
            _safe_url(url),
            _safe_preview(getattr(response, "text", "")),
        )
        raise HTTPException(
            status_code=502,
            detail=(
                f"LLM response error: No message content was returned during "
                f"{_operation_label(operation)}. Check the provider type and model response. "
                f"Reference ID: {reference_id}."
            ),
        )
    return content


def chat_completion_stream(
    config: LLMConfig,
    messages: list[dict],
    *,
    max_tokens: int,
    timeout: float | None = None,
) -> Iterator[str]:
    reference_id = new_diagnostic_reference()
    timeout = timeout if timeout is not None else config.timeout_seconds
    base_url = config.base_url.rstrip("/")
    if config.provider == "ollama":
        url = f"{base_url}/api/chat"
        payload: dict = {
            "model": config.model,
            "messages": messages,
            "stream": True,
        }
    else:
        url = f"{base_url}/chat/completions"
        payload = {
            "model": config.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "stream": True,
        }
        if config.supports_temperature:
            payload["temperature"] = 0
    headers = {"Authorization": f"Bearer {config.api_key}"} if config.api_key else None

    try:
        with httpx.stream(
            "POST", url, json=payload, headers=headers, timeout=timeout
        ) as response:
            if response.status_code >= 400:
                response.read()
                raise HTTPException(
                    status_code=502,
                    detail=_upstream_error_detail(
                        response.status_code, "chat_completion", reference_id
                    ),
                )
            for line in response.iter_lines():
                if not line:
                    continue
                if config.provider == "ollama":
                    data = json.loads(line)
                    content = _extract_reply_content(config.provider, data)
                else:
                    if not line.startswith("data:"):
                        continue
                    event = line.removeprefix("data:").strip()
                    if event == "[DONE]":
                        break
                    data = json.loads(event)
                    choices = data.get("choices")
                    delta = choices[0].get("delta") if choices else None
                    content = delta.get("content") if isinstance(delta, dict) else None
                if isinstance(content, str) and content:
                    yield content
    except HTTPException:
        raise
    except (httpx.HTTPError, json.JSONDecodeError) as exc:
        logger.error(
            "llm_stream_failed reference_id=%s provider=%s model=%s endpoint=%s exception=%s",
            reference_id,
            config.provider,
            config.model,
            _safe_url(url),
            type(exc).__name__,
        )
        raise HTTPException(
            status_code=502,
            detail=(
                "LLM streaming error: The streamed response was interrupted or invalid. "
                f"Reference ID: {reference_id}."
            ),
        ) from exc


def test_llm_connection(config: LLMConfig) -> str:
    """Run a minimal completion to verify the LLM endpoint, model, and credentials."""
    return chat_completion(
        config,
        [{"role": "user", "content": "Reply with: pong"}],
        max_tokens=8,
        operation="connection_test",
    )


def probe_temperature_support(config: LLMConfig) -> bool:
    """Detect whether the configured model accepts a custom `temperature`.

    Called once from settings_service whenever the LLM connection is saved
    or tested, so the result can be cached on LLMConfig.supports_temperature
    and every later chat_completion call can skip the field outright instead
    of failing and retrying on each one. Any failure other than a clear
    temperature rejection is left for the real connection-test call right
    after this to surface with full error handling and logging.
    """
    if config.provider == "ollama":
        return True
    base_url = config.base_url.rstrip("/")
    url = f"{base_url}/chat/completions"
    payload = {
        "model": config.model,
        "messages": [{"role": "user", "content": "Reply with: pong"}],
        "max_tokens": 8,
        "temperature": 0,
    }
    headers = {"Authorization": f"Bearer {config.api_key}"} if config.api_key else None
    try:
        response = httpx.post(
            url, json=payload, headers=headers, timeout=config.timeout_seconds
        )
    except httpx.HTTPError:
        return True
    if response.status_code == 400 and "temperature" in response.text.lower():
        return False
    return True


def _extract_embedding_vector(provider: str, data: dict) -> list[float] | None:
    if provider == "ollama":
        # Ollama's newer /api/embed endpoint returns a batch shape
        # ({"embeddings": [[...], ...]}) even for a single input.
        vectors = data.get("embeddings")
        if isinstance(vectors, list) and vectors and isinstance(vectors[0], list):
            return [float(value) for value in vectors[0]]
        return None
    items = data.get("data")
    if isinstance(items, list) and items and isinstance(items[0], dict):
        vector = items[0].get("embedding")
        if isinstance(vector, list):
            return [float(value) for value in vector]
    return None


def embeddings(
    config: LLMConfig,
    text: str,
    *,
    timeout: float | None = None,
    reference_id: str | None = None,
) -> list[float]:
    """Embed `text` using the configured embedding model.

    Structured like `chat_completion` (same error-handling/logging
    conventions), but for the separate, optional embedding model rather than
    the required chat model. Raises if no embedding model is configured.
    """
    if not config.embedding_model:
        raise HTTPException(
            status_code=409, detail="An embedding model is not configured."
        )
    reference_id = reference_id or new_diagnostic_reference()
    timeout = timeout if timeout is not None else config.timeout_seconds
    base_url = config.base_url.rstrip("/")
    if config.provider == "ollama":
        url = f"{base_url}/api/embed"
        payload: dict = {"model": config.embedding_model, "input": text}
    else:
        url = f"{base_url}/embeddings"
        payload = {"model": config.embedding_model, "input": [text]}

    headers = {"Authorization": f"Bearer {config.api_key}"} if config.api_key else None
    try:
        response = httpx.post(url, json=payload, headers=headers, timeout=timeout)
    except httpx.HTTPError as exc:
        logger.error(
            "llm_connection_failed reference_id=%s operation=embedding provider=%s "
            "model=%s endpoint=%s exception=%s",
            reference_id,
            config.provider,
            config.embedding_model,
            _safe_url(url),
            type(exc).__name__,
        )
        raise HTTPException(
            status_code=502,
            detail=(
                "LLM connection error: Could not connect to the LLM server during "
                f"{_operation_label('embedding')}. Check the base URL and network "
                f"path. Reference ID: {reference_id}."
            ),
        ) from exc

    if response.status_code >= 400:
        logger.error(
            "llm_request_rejected reference_id=%s operation=embedding provider=%s "
            "model=%s endpoint=%s upstream_status=%s response_preview=%r",
            reference_id,
            config.provider,
            config.embedding_model,
            _safe_url(url),
            response.status_code,
            _safe_preview(getattr(response, "text", "")),
        )
        raise HTTPException(
            status_code=502,
            detail=_upstream_error_detail(response.status_code, "embedding", reference_id),
        )

    try:
        data = response.json()
    except ValueError as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                "LLM protocol error: The server returned a non-JSON response during "
                f"{_operation_label('embedding')}. Reference ID: {reference_id}."
            ),
        ) from exc

    vector = _extract_embedding_vector(config.provider, data)
    if not vector:
        raise HTTPException(
            status_code=502,
            detail=(
                "LLM response error: No embedding vector was returned during "
                f"{_operation_label('embedding')}. Reference ID: {reference_id}."
            ),
        )
    return vector


def test_embedding_connection(config: LLMConfig) -> list[float]:
    """Run a minimal embedding call to verify the embedding model and credentials."""
    return embeddings(config, "connection test")


def sanitize_html_for_analysis(html: str) -> str:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "template", "svg"]):
        tag.decompose()
    text = str(soup)
    text = re.sub(r"\s+", " ", text)
    return text[:MAX_HTML_CHARS]


def parse_analysis_reply(reply: str) -> dict:
    candidate = reply.strip()
    fence_match = re.search(r"```(?:json)?\s*(.*?)```", candidate, re.DOTALL)
    if fence_match:
        candidate = fence_match.group(1).strip()
    object_match = re.search(r"\{.*\}", candidate, re.DOTALL)
    if object_match:
        candidate = object_match.group(0)
    try:
        data = json.loads(candidate)
    except ValueError as exc:
        raise HTTPException(
            status_code=502, detail="LLM returned an invalid analysis"
        ) from exc
    if not isinstance(data, dict):
        raise HTTPException(status_code=502, detail="LLM returned an invalid analysis")

    config: dict = {}
    for key in SCRAPE_CONFIG_REQUIRED_KEYS:
        value = data.get(key)
        if not isinstance(value, str) or not value.strip():
            raise HTTPException(
                status_code=502, detail="LLM returned an invalid analysis"
            )
        config[key] = value.strip()
    for key in ("published_selector", "published_attribute", "summary_selector"):
        value = data.get(key)
        config[key] = (
            value.strip() if isinstance(value, str) and value.strip() else None
        )
    return config


def analyze_news_page(
    config: LLMConfig,
    *,
    page_url: str,
    html: str,
    reference_id: str | None = None,
    retry_context: dict[str, object] | None = None,
) -> dict:
    """Ask the LLM to design a scraping recipe for a news site HTML page."""
    reference_id = reference_id or new_diagnostic_reference()
    cleaned_html = sanitize_html_for_analysis(html)
    retry_instructions = ""
    if retry_context is not None:
        retry_instructions = (
            "\n\nThe previous scraping recipe extracted zero complete articles. "
            "Correct the selectors using the HTML below. Do not return the same "
            "selector recipe unchanged.\nPrevious attempt diagnostics:\n"
            f"{json.dumps(retry_context, ensure_ascii=False)}"
        )
    reply = chat_completion(
        config,
        [
            {"role": "system", "content": ANALYSIS_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"URL: {page_url}{retry_instructions}\n\nHTML:\n{cleaned_html}"
                ),
            },
        ],
        max_tokens=1024,
        operation="news_site_analysis",
        reference_id=reference_id,
    )
    try:
        return parse_analysis_reply(reply)
    except HTTPException as exc:
        logger.error(
            "llm_analysis_invalid reference_id=%s provider=%s model=%s target_url=%s "
            "html_chars=%s sanitized_chars=%s reply_chars=%s "
            "reply_preview=%r",
            reference_id,
            config.provider,
            config.model,
            _safe_url(page_url),
            len(html),
            len(cleaned_html),
            len(reply),
            _safe_preview(reply),
        )
        raise HTTPException(
            status_code=502,
            detail=(
                "LLM analysis error: The target site was fetched successfully, but the "
                "LLM did not return the required JSON scraping configuration. Try another "
                "model or inspect "
                f"the server log. Reference ID: {reference_id}."
            ),
        ) from exc
