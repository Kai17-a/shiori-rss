import hashlib
import socket
from contextlib import contextmanager

import pytest
from fastapi import HTTPException

from api.database import get_db, initialize_database
from api.model.models import DockerImageCreate, DockerImageUpdate
from api.services.docker_image_service import (
    DockerImageService,
    parse_reference,
    resolve_manifest_digest,
)
import api.services.docker_image_service as service_module


@pytest.fixture(autouse=True)
def public_example_hosts(monkeypatch):
    original = socket.getaddrinfo

    def fake_getaddrinfo(host, port, *args, **kwargs):
        if host.endswith(".example") or host == "registry-1.docker.io":
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port))]
        return original(host, port, *args, **kwargs)

    monkeypatch.setattr(service_module.socket, "getaddrinfo", fake_getaddrinfo)


class RegistryResponse:
    def __init__(self, status_code=200, body=b"{}", headers=None, json_data=None):
        self.status_code = status_code
        self.content = body
        self.headers = headers or {}
        self._json_data = json_data

    def json(self):
        if self._json_data is not None:
            return self._json_data
        import json

        return json.loads(self.content)


def digest(body=b"{}"):
    return f"sha256:{hashlib.sha256(body).hexdigest()}"


def patch_client_get(monkeypatch, get):
    class FakeClient:
        def get(self, *args, **kwargs):
            return get(*args, **kwargs)

        def close(self):
            pass

    monkeypatch.setattr(
        service_module,
        "_registry_client",
        lambda **kwargs: FakeClient(),
    )


@pytest.fixture
def service(tmp_path, monkeypatch):
    database = str(tmp_path / "test.db")
    initialize_database(database)

    @contextmanager
    def patched_get_db():
        with get_db(database) as conn:
            yield conn

    monkeypatch.setattr(service_module, "get_db", patched_get_db)
    patch_client_get(
        monkeypatch,
        lambda *args, **kwargs: RegistryResponse(
            headers={"docker-content-digest": digest()}
        ),
    )
    return DockerImageService()


@pytest.mark.parametrize(
    ("reference", "expected"),
    [
        ("ghcr.io/owner/name:stable", ("ghcr.io", "owner/name", "stable")),
        ("localhost:5000/name:tag", ("localhost:5000", "name", "tag")),
        ("nginx", ("registry-1.docker.io", "library/nginx", "latest")),
        ("docker.io/nginx", ("registry-1.docker.io", "library/nginx", "latest")),
        ("index.docker.io/nginx", ("registry-1.docker.io", "library/nginx", "latest")),
        ("registry-1.docker.io/nginx:1.27", ("registry-1.docker.io", "library/nginx", "1.27")),
        ("owner/name", ("registry-1.docker.io", "owner/name", "latest")),
        ("owner/name:v2", ("registry-1.docker.io", "owner/name", "v2")),
    ],
)
def test_parse_reference(reference, expected):
    assert parse_reference(reference)[:3] == expected


def test_create_list_update_refresh_and_delete(service):
    created = service.create(DockerImageCreate(reference=" nginx "))
    assert created.registry == "registry-1.docker.io"
    assert created.repository == "library/nginx"
    assert created.tag == "latest"
    assert created.latest_digest == digest()
    assert created.webhook_ids == []
    assert service.list().total == 1
    assert (
        service.update(created.id, DockerImageUpdate(webhook_ids=[])).id == created.id
    )
    assert service.refresh_all().total == 1
    service.delete(created.id)
    assert service.list().total == 0


def test_duplicate_image_is_rejected(service):
    body = DockerImageCreate(reference="nginx")
    service.create(body)
    with pytest.raises(HTTPException) as error:
        service.create(body)
    assert error.value.status_code == 409


def test_anonymous_manifest_uses_verified_digest(monkeypatch):
    patch_client_get(
        monkeypatch,
        lambda *args, **kwargs: RegistryResponse(
            headers={"docker-content-digest": digest()}
        ),
    )
    assert (
        resolve_manifest_digest("registry.example", "owner/name", "latest") == digest()
    )


def test_loopback_registry_is_rejected_before_http_request(monkeypatch):
    monkeypatch.setattr(
        service_module.socket,
        "socket",
        lambda *args, **kwargs: pytest.fail("TCP socket must not be created"),
    )
    with pytest.raises(HTTPException) as error:
        resolve_manifest_digest("127.0.0.1:12345", "owner/name", "latest")
    assert error.value.status_code == 422
    assert error.value.detail == "Registry host resolves to a disallowed network address"


def test_network_backend_dials_the_single_validated_resolution(monkeypatch):
    resolutions = 0
    connected_to = None

    def fake_getaddrinfo(host, port, **kwargs):
        nonlocal resolutions
        resolutions += 1
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port))]

    class FakeSocket:
        def settimeout(self, timeout):
            pass

        def setsockopt(self, *option):
            pass

        def connect(self, address):
            nonlocal connected_to
            connected_to = address

        def close(self):
            pass

    monkeypatch.setattr(service_module.socket, "getaddrinfo", fake_getaddrinfo)
    monkeypatch.setattr(service_module.socket, "socket", lambda *args: FakeSocket())

    service_module._PublicNetworkBackend().connect_tcp("registry.example", 443)

    assert resolutions == 1
    assert connected_to == ("93.184.216.34", 443)


def test_bearer_token_retry_accepts_access_token(monkeypatch):
    calls = []

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        if url == "https://auth.example/token":
            return RegistryResponse(json_data={"access_token": "secret"})
        if len(calls) == 1:
            return RegistryResponse(
                401,
                headers={
                    "www-authenticate": 'Basic realm="legacy", Bearer realm="https://auth.example/token",service="registry.example",scope="repository:owner/name:pull"'
                },
            )
        assert kwargs["headers"]["Authorization"] == "Bearer secret"
        return RegistryResponse(headers={"docker-content-digest": digest()})

    patch_client_get(monkeypatch, fake_get)
    assert (
        resolve_manifest_digest("registry.example", "owner/name", "latest") == digest()
    )


def test_cross_host_redirect_does_not_leak_authorization(monkeypatch):
    calls = []

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        if url == "https://auth.example/token":
            return RegistryResponse(json_data={"token": "secret"})
        if len(calls) == 1:
            return RegistryResponse(
                401,
                headers={
                    "www-authenticate": 'Bearer realm="https://auth.example/token"'
                },
            )
        if url.startswith("https://registry.example"):
            assert kwargs["headers"]["Authorization"] == "Bearer secret"
            return RegistryResponse(
                307, headers={"location": "https://storage.example/manifest"}
            )
        assert "Authorization" not in kwargs["headers"]
        return RegistryResponse(headers={"docker-content-digest": digest()})

    patch_client_get(monkeypatch, fake_get)
    assert (
        resolve_manifest_digest("registry.example", "owner/name", "latest") == digest()
    )


def test_missing_digest_header_uses_computed_hash(monkeypatch):
    body = b'{"schemaVersion":2}'
    patch_client_get(
        monkeypatch, lambda *args, **kwargs: RegistryResponse(body=body)
    )
    assert resolve_manifest_digest(
        "registry.example", "owner/name", "latest"
    ) == digest(body)


@pytest.mark.parametrize(
    "response",
    [
        RegistryResponse(headers={"docker-content-digest": "sha256:wrong"}),
        RegistryResponse(body=b"not-json"),
        RegistryResponse(status_code=429),
    ],
)
def test_invalid_rate_limited_or_mismatched_manifest_is_a_fetch_failure(
    monkeypatch, response
):
    patch_client_get(monkeypatch, lambda *args, **kwargs: response)
    with pytest.raises(HTTPException) as error:
        resolve_manifest_digest("registry.example", "owner/name", "latest")
    assert error.value.status_code == 502
