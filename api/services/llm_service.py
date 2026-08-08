"""LLM provider integration for connection testing and news page analysis."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
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

LLM_SETTING_KEYS = (
    LLM_PROVIDER_SETTING_KEY,
    LLM_BASE_URL_SETTING_KEY,
    LLM_API_KEY_SETTING_KEY,
    LLM_MODEL_SETTING_KEY,
)

MAX_HTML_CHARS = 50000
LOG_PREVIEW_CHARS = 500

LLMOperation = Literal["connection_test", "news_site_analysis", "chat_completion"]

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
    )


def save_llm_config(repo, config: LLMConfig) -> None:
    repo.set(LLM_PROVIDER_SETTING_KEY, config.provider)
    repo.set(LLM_BASE_URL_SETTING_KEY, config.base_url)
    repo.set(LLM_API_KEY_SETTING_KEY, config.api_key or "")
    repo.set(LLM_MODEL_SETTING_KEY, config.model)


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
    timeout: float = 60.0,
    operation: LLMOperation = "chat_completion",
    reference_id: str | None = None,
) -> str:
    reference_id = reference_id or new_diagnostic_reference()
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
            "temperature": 0,
        }

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


def test_llm_connection(config: LLMConfig) -> str:
    """Run a minimal completion to verify the LLM endpoint, model, and credentials."""
    return chat_completion(
        config,
        [{"role": "user", "content": "Reply with: pong"}],
        max_tokens=8,
        timeout=60.0,
        operation="connection_test",
    )


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
        timeout=90.0,
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
