import hashlib
import ipaddress
import re
import socket
import ssl
from collections.abc import Iterable
from contextlib import closing
from urllib.parse import urljoin, urlparse

import httpcore
import httpx
from fastapi import HTTPException
from httpcore._backends.sync import SyncStream

from api.database import get_db
from api.model.models import (
    DockerImageCreate,
    DockerImageListResponse,
    DockerImageResponse,
    DockerImageUpdate,
)
from api.repositories.docker_image_repo import DockerImageRepository

MANIFEST_ACCEPT = ", ".join(
    (
        "application/vnd.docker.distribution.manifest.v2+json",
        "application/vnd.docker.distribution.manifest.list.v2+json",
        "application/vnd.oci.image.manifest.v1+json",
        "application/vnd.oci.image.index.v1+json",
    )
)


def parse_reference(value: str) -> tuple[str, str, str, str]:
    display_name = value.strip()
    if not display_name or "/" == display_name or "://" in display_name:
        raise HTTPException(
            status_code=422, detail="Enter a valid Docker image reference"
        )
    first, separator, rest = display_name.partition("/")
    explicit_registry = separator and (
        "." in first or ":" in first or first == "localhost"
    )
    registry = first if explicit_registry else "registry-1.docker.io"
    repository_with_tag = rest if explicit_registry else display_name
    if registry in {"docker.io", "index.docker.io", "registry-1.docker.io"}:
        registry = "registry-1.docker.io"
    last_slash = repository_with_tag.rfind("/")
    last_colon = repository_with_tag.rfind(":")
    if last_colon > last_slash:
        repository, tag = (
            repository_with_tag[:last_colon],
            repository_with_tag[last_colon + 1 :],
        )
    else:
        repository, tag = repository_with_tag, "latest"
    if registry == "registry-1.docker.io" and "/" not in repository:
        repository = f"library/{repository}"
    if (
        not registry
        or not repository
        or not tag
        or any(char.isspace() for char in display_name)
    ):
        raise HTTPException(
            status_code=422, detail="Enter a valid Docker image reference"
        )
    return registry, repository, tag, display_name


def _bearer_parameters(value: str) -> dict[str, str] | None:
    match = re.search(r"(?:^|,)\s*Bearer\s+", value, flags=re.IGNORECASE)
    if not match:
        return None
    pos = match.end()
    result: dict[str, str] = {}
    pattern = re.compile(
        r'([!#$%&\'*+.^_`|~0-9A-Za-z-]+)\s*=\s*(?:"((?:\\.|[^"\\])*)"|([^\s,]+))\s*(?:,|$)'
    )
    while pos < len(value):
        item = pattern.match(value, pos)
        if not item:
            break
        result[item.group(1).lower()] = (
            re.sub(r"\\(.)", r"\1", item.group(2))
            if item.group(2) is not None
            else item.group(3)
        )
        pos = item.end()
        if re.match(r"\s*[A-Za-z][!#$%&'*+.^_`|~0-9A-Za-z-]*\s+", value[pos:]):
            break
    return result


def _is_disallowed_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        return _is_disallowed_ip(ip.ipv4_mapped)
    return any(
        (
            ip.is_loopback,
            ip.is_private,
            ip.is_link_local,
            ip.is_multicast,
            ip.is_reserved,
            ip.is_unspecified,
        )
    )


class _PublicNetworkBackend(httpcore.SyncBackend):
    """Resolve, validate, and dial the same address set for each connection."""

    def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options: Iterable[tuple] | None = None,
    ) -> httpcore.NetworkStream:
        try:
            addresses = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        except OSError as exc:
            raise httpcore.ConnectError(str(exc)) from exc
        if not addresses:
            raise httpcore.ConnectError("registry host did not resolve")
        if any(_is_disallowed_ip(ipaddress.ip_address(item[4][0])) for item in addresses):
            raise httpcore.ConnectError(
                "registry host resolves to a disallowed network address"
            )

        last_error: OSError | None = None
        for family, socktype, proto, _, sockaddr in addresses:
            sock = socket.socket(family, socktype, proto)
            try:
                sock.settimeout(timeout)
                if local_address is not None:
                    bind_address = (
                        (local_address, 0, 0, 0)
                        if family == socket.AF_INET6
                        else (local_address, 0)
                    )
                    sock.bind(bind_address)
                for option in socket_options or ():
                    sock.setsockopt(*option)
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                sock.connect(sockaddr)
                return SyncStream(sock)
            except socket.timeout as exc:
                sock.close()
                raise httpcore.ConnectTimeout(str(exc)) from exc
            except OSError as exc:
                sock.close()
                last_error = exc
        assert last_error is not None
        raise httpcore.ConnectError(str(last_error)) from last_error


class _PublicHTTPTransport(httpx.HTTPTransport):
    def __init__(self) -> None:
        super().__init__(verify=True, trust_env=False)
        self._pool.close()
        self._pool = httpcore.ConnectionPool(
            ssl_context=ssl.create_default_context(),
            network_backend=_PublicNetworkBackend(),
        )


def _registry_client(*, allow_private_addresses: bool) -> httpx.Client:
    transport = None if allow_private_addresses else _PublicHTTPTransport()
    return httpx.Client(transport=transport, timeout=10.0, follow_redirects=False)


def _get_with_redirects(
    client: httpx.Client, url: str, headers: dict[str, str], *, allow_http: bool = False
) -> httpx.Response:
    current = url
    current_headers = dict(headers)
    for _ in range(6):
        response = client.get(current, headers=current_headers)
        if response.status_code not in {301, 302, 303, 307, 308}:
            return response
        location = response.headers.get("location")
        if not location:
            raise HTTPException(
                status_code=502, detail="Registry returned an invalid redirect"
            )
        target = urljoin(current, location)
        parsed = urlparse(target)
        if parsed.scheme != "https" and not (allow_http and parsed.scheme == "http"):
            raise HTTPException(
                status_code=502, detail="Registry redirected to an insecure URL"
            )
        if urlparse(current).netloc != parsed.netloc:
            current_headers.pop("Authorization", None)
        current = target
    raise HTTPException(status_code=502, detail="Registry returned too many redirects")


def resolve_manifest_digest(
    registry: str, repository: str, tag: str, *, base_url: str | None = None
) -> str:
    base = base_url or f"https://{registry}"
    manifest_url = f"{base.rstrip('/')}/v2/{repository}/manifests/{tag}"
    allow_http = base.startswith("http://")
    headers = {
        "Accept": MANIFEST_ACCEPT,
        "Accept-Encoding": "identity",
        "User-Agent": "shiori-feed",
    }
    try:
        with closing(_registry_client(allow_private_addresses=allow_http)) as client:
            response = _get_with_redirects(
                client, manifest_url, headers, allow_http=allow_http
            )
            if response.status_code == 401:
                params = _bearer_parameters(response.headers.get("www-authenticate", ""))
                realm = params.get("realm") if params else None
                if not realm or (
                    not realm.startswith("https://")
                    and not (allow_http and realm.startswith("http://"))
                ):
                    raise HTTPException(
                        status_code=502,
                        detail="Registry returned an invalid authentication challenge",
                    )
                assert params is not None
                query = {key: params[key] for key in ("service", "scope") if key in params}
                token_response = client.get(realm, params=query)
                if token_response.status_code >= 400:
                    raise HTTPException(
                        status_code=502, detail="Registry authentication failed"
                    )
                token_data = token_response.json()
                token = token_data.get("token") or token_data.get("access_token")
                if not isinstance(token, str) or not token:
                    raise HTTPException(
                        status_code=502, detail="Registry returned an invalid token"
                    )
                response = _get_with_redirects(
                    client,
                    manifest_url,
                    {**headers, "Authorization": f"Bearer {token}"},
                    allow_http=allow_http,
                )
    except HTTPException:
        raise
    except (httpx.HTTPError, OSError, ValueError) as exc:
        if "registry host resolves to a disallowed network address" in str(exc):
            raise HTTPException(
                status_code=422,
                detail="Registry host resolves to a disallowed network address",
            ) from exc
        raise HTTPException(
            status_code=502, detail="Container registry is unavailable"
        ) from exc
    if response.status_code == 429:
        raise HTTPException(
            status_code=502, detail="Container registry rate limit exceeded"
        )
    if response.status_code == 404:
        raise HTTPException(status_code=422, detail="Docker image or tag not found")
    if response.status_code >= 400:
        raise HTTPException(
            status_code=502, detail="Failed to fetch Docker image manifest"
        )
    try:
        manifest = response.json()
    except ValueError as exc:
        raise HTTPException(
            status_code=502, detail="Registry returned an invalid manifest"
        ) from exc
    if not isinstance(manifest, dict):
        raise HTTPException(
            status_code=502, detail="Registry returned an invalid manifest"
        )
    computed = f"sha256:{hashlib.sha256(response.content).hexdigest()}"
    advertised = response.headers.get("docker-content-digest")
    if advertised and advertised != computed:
        raise HTTPException(
            status_code=502, detail="Registry manifest digest verification failed"
        )
    return advertised or computed


class DockerImageService:
    def _verify_webhooks(self, conn, webhook_ids: list[int]) -> None:
        for webhook_id in webhook_ids:
            if (
                conn.execute(
                    "SELECT 1 FROM webhook_endpoints WHERE id = ?", (webhook_id,)
                ).fetchone()
                is None
            ):
                raise HTTPException(
                    status_code=422, detail="Webhook endpoint not found"
                )

    def list(self) -> DockerImageListResponse:
        with get_db() as conn:
            rows = DockerImageRepository(conn).find_all()
        items = [DockerImageResponse(**row) for row in rows]
        return DockerImageListResponse(items=items, total=len(items))

    def create(self, body: DockerImageCreate) -> DockerImageResponse:
        registry, repository, tag, display_name = parse_reference(body.reference)
        digest = resolve_manifest_digest(registry, repository, tag)
        with get_db() as conn:
            repo = DockerImageRepository(conn)
            if repo.find_by_reference(registry, repository, tag):
                raise HTTPException(
                    status_code=409, detail="Docker image already exists"
                )
            self._verify_webhooks(conn, body.webhook_ids)
            row = repo.insert(
                {
                    "registry": registry,
                    "repository": repository,
                    "tag": tag,
                    "display_name": display_name,
                    "latest_digest": digest,
                }
            )
            repo.set_webhook_ids(int(row["id"]), body.webhook_ids)
            row = repo.find_by_id(int(row["id"]))
            assert row is not None
        return DockerImageResponse(**row)

    def update(self, image_id: int, body: DockerImageUpdate) -> DockerImageResponse:
        with get_db() as conn:
            repo = DockerImageRepository(conn)
            if repo.find_by_id(image_id) is None:
                raise HTTPException(status_code=404, detail="Docker image not found")
            self._verify_webhooks(conn, body.webhook_ids)
            repo.set_webhook_ids(image_id, body.webhook_ids)
            row = repo.find_by_id(image_id)
            assert row is not None
        return DockerImageResponse(**row)

    def refresh_all(self) -> DockerImageListResponse:
        with get_db() as conn:
            repo = DockerImageRepository(conn)
            rows = repo.find_all()
            refreshed = [
                repo.update_digest(
                    row["id"],
                    resolve_manifest_digest(
                        row["registry"], row["repository"], row["tag"]
                    ),
                )
                for row in rows
            ]
        items = [DockerImageResponse(**row) for row in refreshed]
        return DockerImageListResponse(items=items, total=len(items))

    def delete(self, image_id: int) -> None:
        with get_db() as conn:
            if not DockerImageRepository(conn).delete(image_id):
                raise HTTPException(status_code=404, detail="Docker image not found")
