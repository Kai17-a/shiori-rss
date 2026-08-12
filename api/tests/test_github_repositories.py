from contextlib import contextmanager

import pytest

from api.database import get_db, initialize_database
from api.model.models import GitHubRepositoryCreate
from api.services.github_repository_service import GitHubRepositoryService
import api.services.github_repository_service as service_module


class GitHubResponse:
    status_code = 200

    def json(self):
        return {
            "name": "Version 1.2.3",
            "tag_name": "v1.2.3",
            "html_url": "https://github.com/acme/tool/releases/tag/v1.2.3",
            "body": "Release notes",
            "published_at": "2026-08-12T01:00:00Z",
        }


@pytest.fixture
def service(tmp_path, monkeypatch):
    database = str(tmp_path / "test.db")
    initialize_database(database)

    @contextmanager
    def patched_get_db():
        with get_db(database) as conn:
            yield conn

    monkeypatch.setattr(service_module, "get_db", patched_get_db)
    monkeypatch.setattr(service_module.httpx, "get", lambda *args, **kwargs: GitHubResponse())
    return GitHubRepositoryService()


def test_create_lists_and_normalizes_repository_url(service):
    created = service.create(
        GitHubRepositoryCreate.model_validate(
            {"repository_url": "https://github.com/acme/tool/releases"}
        )
    )

    assert created.repository_url == "https://github.com/acme/tool"
    assert created.latest_release_tag == "v1.2.3"
    assert service.list().total == 1


def test_duplicate_repository_is_rejected(service):
    body = GitHubRepositoryCreate.model_validate(
        {"repository_url": "https://github.com/acme/tool"}
    )
    service.create(body)

    with pytest.raises(Exception) as error:
        service.create(body)

    assert getattr(error.value, "status_code", None) == 409


def test_refresh_and_delete(service):
    created = service.create(
        GitHubRepositoryCreate.model_validate(
            {"repository_url": "https://github.com/acme/tool"}
        )
    )
    assert service.refresh_all().total == 1

    service.delete(created.id)
    assert service.list().total == 0
