from fastapi import APIRouter, Depends

from api.dependencies import get_docker_image_service
from api.model.models import (
    DockerImageCreate,
    DockerImageListResponse,
    DockerImageResponse,
    DockerImageUpdate,
)
from api.services.docker_image_service import DockerImageService

router = APIRouter(prefix="/docker-images", tags=["docker-images"])


@router.get("", response_model=DockerImageListResponse)
def list_docker_images(service: DockerImageService = Depends(get_docker_image_service)):
    return service.list()


@router.post("", status_code=201, response_model=DockerImageResponse)
def create_docker_image(
    body: DockerImageCreate,
    service: DockerImageService = Depends(get_docker_image_service),
):
    return service.create(body)


@router.post("/refresh", response_model=DockerImageListResponse)
def refresh_docker_images(
    service: DockerImageService = Depends(get_docker_image_service),
):
    return service.refresh_all()


@router.patch("/{image_id}", response_model=DockerImageResponse)
def update_docker_image(
    image_id: int,
    body: DockerImageUpdate,
    service: DockerImageService = Depends(get_docker_image_service),
):
    return service.update(image_id, body)


@router.delete("/{image_id}", status_code=204)
def delete_docker_image(
    image_id: int, service: DockerImageService = Depends(get_docker_image_service)
):
    service.delete(image_id)
