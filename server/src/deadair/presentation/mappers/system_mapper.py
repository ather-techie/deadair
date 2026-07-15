from deadair.config import Settings
from deadair.presentation.dto.system_dto import StoragePathsDTO


def settings_to_storage_paths_dto(settings: Settings) -> StoragePathsDTO:
    return StoragePathsDTO(
        data_dir=str(settings.data_dir.resolve()),
        uploads_dir=str(settings.resolved_uploads_dir()),
        audio_dir=str(settings.resolved_audio_dir()),
        artifacts_dir=str(settings.resolved_artifacts_dir()),
        render_work_dir=str(settings.resolved_render_work_dir()),
        renders_dir=str(settings.resolved_renders_dir()),
        sqlite_db_path=str(settings.resolved_sqlite_db_path()),
        log_dir=str(settings.resolved_log_dir()),
    )
