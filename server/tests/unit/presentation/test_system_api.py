def test_get_storage_paths_returns_resolved_absolute_paths(client, container):
    response = client.get("/api/system/storage-paths")

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {
        "data_dir",
        "uploads_dir",
        "audio_dir",
        "artifacts_dir",
        "render_work_dir",
        "renders_dir",
        "sqlite_db_path",
        "log_dir",
    }
    assert body["data_dir"] == str(container.settings.data_dir.resolve())
    assert body["uploads_dir"] == str(container.settings.resolved_uploads_dir())
