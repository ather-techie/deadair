from fastapi import APIRouter, Depends

from deadair.container import Container
from deadair.presentation.api.deps import get_container
from deadair.presentation.dto.system_dto import StoragePathsDTO
from deadair.presentation.mappers.system_mapper import settings_to_storage_paths_dto

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/storage-paths")
def get_storage_paths(container: Container = Depends(get_container)) -> StoragePathsDTO:
    return settings_to_storage_paths_dto(container.settings)
