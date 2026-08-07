"""Compatibility shims for the local test environment.

The installed FastAPI/Starlette TestClient stack is not functional in this
runtime, so we provide a small sync client that exercises the ASGI app through
httpx's async transport.
"""

from __future__ import annotations

from contextlib import AbstractContextManager
from typing import Any

import anyio
import httpx


class _CompatTestClient(AbstractContextManager):
    def __init__(self, app, base_url: str = "http://testserver", **kwargs: Any) -> None:
        self.app = app
        self.base_url = base_url
        self.kwargs = kwargs
        self._client: httpx.AsyncClient | None = None

    def __enter__(self):
        anyio.run(self.app.router.startup)
        transport = httpx.ASGITransport(app=self.app, raise_app_exceptions=True)
        self._client = httpx.AsyncClient(
            transport=transport,
            base_url=self.base_url,
            follow_redirects=True,
        )
        return self

    def __exit__(self, exc_type, exc, tb):
        async def _close() -> None:
            assert self._client is not None
            await self._client.aclose()
            await self.app.router.shutdown()

        anyio.run(_close)
        self._client = None
        return False

    def request(self, method: str, url: str, **kwargs: Any):
        async def _request():
            assert self._client is not None
            return await self._client.request(method, url, **kwargs)

        return anyio.run(_request)

    def get(self, url: str, **kwargs: Any):
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs: Any):
        return self.request("POST", url, **kwargs)

    def patch(self, url: str, **kwargs: Any):
        return self.request("PATCH", url, **kwargs)

    def delete(self, url: str, **kwargs: Any):
        return self.request("DELETE", url, **kwargs)


def _patch_testclient() -> None:
    try:
        import fastapi.testclient as fastapi_testclient
    except Exception:
        return

    fastapi_testclient.TestClient = _CompatTestClient


_patch_testclient()
