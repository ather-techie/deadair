import io


def test_upload_with_correct_field_name_succeeds_and_returns_ids(client):
    response = client.post(
        "/api/videos", files={"video": ("clip.mp4", io.BytesIO(b"fake video bytes"), "video/mp4")}
    )
    assert response.status_code == 201
    body = response.json()
    assert body["video_id"]
    assert body["job_id"]


def test_upload_with_wrong_field_name_fails_cleanly(client):
    response = client.post(
        "/api/videos", files={"wrong_field": ("clip.mp4", io.BytesIO(b"data"), "video/mp4")}
    )
    assert response.status_code == 422


def test_job_progresses_to_done_synchronously_with_in_memory_runner(client):
    upload = client.post("/api/videos", files={"video": ("clip.mp4", io.BytesIO(b"data"), "video/mp4")})
    job_id = upload.json()["job_id"]

    status = client.get(f"/api/jobs/{job_id}")
    assert status.status_code == 200
    body = status.json()
    assert body["status"] == "done"
    assert all(s["status"] == "done" for s in body["steps"])


def test_result_endpoint_serves_rendered_file_once_done(client):
    upload = client.post(
        "/api/videos", files={"video": ("clip.mp4", io.BytesIO(b"some bytes"), "video/mp4")}
    )
    video_id = upload.json()["video_id"]

    result = client.get(f"/api/videos/{video_id}/result")
    assert result.status_code == 200
    assert result.content == b"some bytes"


def test_result_endpoint_404s_for_unknown_video(client):
    response = client.get("/api/videos/does-not-exist/result")
    assert response.status_code == 404


def test_get_video_metadata(client):
    upload = client.post("/api/videos", files={"video": ("clip.mp4", io.BytesIO(b"data"), "video/mp4")})
    video_id = upload.json()["video_id"]

    response = client.get(f"/api/videos/{video_id}")
    assert response.status_code == 200
    assert response.json()["id"] == video_id


def test_get_video_metadata_404s_for_unknown_video(client):
    response = client.get("/api/videos/does-not-exist")
    assert response.status_code == 404


def test_list_videos_includes_uploaded_video(client):
    upload = client.post("/api/videos", files={"video": ("clip.mp4", io.BytesIO(b"data"), "video/mp4")})
    video_id = upload.json()["video_id"]

    response = client.get("/api/videos")
    assert response.status_code == 200
    assert video_id in {v["id"] for v in response.json()}
