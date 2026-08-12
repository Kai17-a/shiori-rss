from fastapi import APIRouter, Depends

from api.dependencies import get_github_repository_service
from api.model.models import GitHubRepositoryCreate, GitHubRepositoryListResponse, GitHubRepositoryResponse
from api.services.github_repository_service import GitHubRepositoryService

router = APIRouter(prefix="/github-repositories", tags=["github-repositories"])


@router.get("", response_model=GitHubRepositoryListResponse)
def list_github_repositories(service: GitHubRepositoryService = Depends(get_github_repository_service)):
    return service.list()


@router.post("", status_code=201, response_model=GitHubRepositoryResponse)
def create_github_repository(body: GitHubRepositoryCreate, service: GitHubRepositoryService = Depends(get_github_repository_service)):
    return service.create(body)


@router.post("/refresh", response_model=GitHubRepositoryListResponse)
def refresh_github_repositories(service: GitHubRepositoryService = Depends(get_github_repository_service)):
    return service.refresh_all()


@router.delete("/{repository_id}", status_code=204)
def delete_github_repository(repository_id: int, service: GitHubRepositoryService = Depends(get_github_repository_service)):
    service.delete(repository_id)
