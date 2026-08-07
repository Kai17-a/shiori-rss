from api.model.models import FolderCreate, FolderResponse, FolderUpdate
from fastapi import APIRouter, Depends

from api.dependencies import get_folder_service
from api.services.folder_service import FolderService

router = APIRouter(prefix="/folders", tags=["folders"])


@router.post("", status_code=201, response_model=FolderResponse)
def create_folder(
    body: FolderCreate, service: FolderService = Depends(get_folder_service)
):
    return service.create(body)


@router.get("", status_code=200, response_model=list[FolderResponse])
def list_folders(service: FolderService = Depends(get_folder_service)):
    return service.list()


@router.get(
    "/{folder_id}",
    status_code=200,
    response_model=FolderResponse,
)
def get_folder(folder_id: int, service: FolderService = Depends(get_folder_service)):
    return service.get(folder_id)


@router.patch("/{folder_id}", response_model=FolderResponse)
def update_folder(
    folder_id: int,
    body: FolderUpdate,
    service: FolderService = Depends(get_folder_service),
):
    return service.update(folder_id, body)


@router.delete("/{folder_id}", status_code=204)
def delete_folder(folder_id: int, service: FolderService = Depends(get_folder_service)):
    service.delete(folder_id)
