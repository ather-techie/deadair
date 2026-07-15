from pydantic import BaseModel


class StoragePathsDTO(BaseModel):
    data_dir: str
    uploads_dir: str
    audio_dir: str
    artifacts_dir: str
    render_work_dir: str
    renders_dir: str
    sqlite_db_path: str
    log_dir: str
