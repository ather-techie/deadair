import io


def test_upload_with_correct_field_name_succeeds_and_returns_ids(client):
    response = client.post(
        "/api/videos",
        files={"video": ("clip.mp4", io.BytesIO(b"fake video bytes"), "video/mp4")},
        data={"remove_silence": "true", "remove_filler": "true"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["video_id"]
    assert body["job_id"]


def test_upload_with_neither_option_selected_returns_400(client):
    response = client.post(
        "/api/videos",
        files={"video": ("clip.mp4", io.BytesIO(b"fake video bytes"), "video/mp4")},
        data={"remove_silence": "false", "remove_filler": "false"},
    )
    assert response.status_code == 400


def test_upload_with_speed_up_cuts_and_no_removal_option_returns_400(client):
    response = client.post(
        "/api/videos",
        files={"video": ("clip.mp4", io.BytesIO(b"fake video bytes"), "video/mp4")},
        data={
            "remove_silence": "false",
            "remove_filler": "false",
            "show_result_transcript": "true",
            "speed_up_cuts": "true",
            "speed_multiplier": "4",
        },
    )
    assert response.status_code == 400


def test_upload_with_invalid_speed_multiplier_returns_400(client):
    response = client.post(
        "/api/videos",
        files={"video": ("clip.mp4", io.BytesIO(b"fake video bytes"), "video/mp4")},
        data={
            "remove_silence": "true",
            "remove_filler": "true",
            "speed_up_cuts": "true",
            "speed_multiplier": "3",
        },
    )
    assert response.status_code == 400


def test_upload_with_speed_up_cuts_succeeds_and_job_completes(client):
    response = client.post(
        "/api/videos",
        files={"video": ("clip.mp4", io.BytesIO(b"fake video bytes"), "video/mp4")},
        data={
            "remove_silence": "true",
            "remove_filler": "true",
            "speed_up_cuts": "true",
            "speed_multiplier": "4",
        },
    )
    assert response.status_code == 201
    job_id = response.json()["job_id"]

    status = client.get(f"/api/jobs/{job_id}")
    assert status.json()["status"] == "done"


def test_upload_with_only_show_result_transcript_selected_succeeds(client):
    response = client.post(
        "/api/videos",
        files={"video": ("clip.mp4", io.BytesIO(b"fake video bytes"), "video/mp4")},
        data={"remove_silence": "false", "remove_filler": "false", "show_result_transcript": "true"},
    )
    assert response.status_code == 201


def test_upload_with_wrong_field_name_fails_cleanly(client):
    response = client.post(
        "/api/videos", files={"wrong_field": ("clip.mp4", io.BytesIO(b"data"), "video/mp4")}
    )
    assert response.status_code == 422


def test_job_progresses_to_done_synchronously_with_in_memory_runner(client):
    upload = client.post(
        "/api/videos",
        files={"video": ("clip.mp4", io.BytesIO(b"data"), "video/mp4")},
        data={"remove_silence": "true", "remove_filler": "true"},
    )
    job_id = upload.json()["job_id"]

    status = client.get(f"/api/jobs/{job_id}")
    assert status.status_code == 200
    body = status.json()
    assert body["status"] == "done"
    assert all(s["status"] == "done" for s in body["steps"])


def test_result_endpoint_serves_rendered_file_once_done(client):
    upload = client.post(
        "/api/videos",
        files={"video": ("clip.mp4", io.BytesIO(b"some bytes"), "video/mp4")},
        data={"remove_silence": "true", "remove_filler": "true"},
    )
    video_id = upload.json()["video_id"]

    result = client.get(f"/api/videos/{video_id}/result")
    assert result.status_code == 200
    assert result.content == b"some bytes"


def test_result_endpoint_404s_for_unknown_video(client):
    response = client.get("/api/videos/does-not-exist/result")
    assert response.status_code == 404


def test_get_video_metadata(client):
    upload = client.post(
        "/api/videos",
        files={"video": ("clip.mp4", io.BytesIO(b"data"), "video/mp4")},
        data={"remove_silence": "true", "remove_filler": "true"},
    )
    video_id = upload.json()["video_id"]

    response = client.get(f"/api/videos/{video_id}")
    assert response.status_code == 200
    assert response.json()["id"] == video_id


def test_get_video_metadata_404s_for_unknown_video(client):
    response = client.get("/api/videos/does-not-exist")
    assert response.status_code == 404


def test_list_videos_includes_uploaded_video(client):
    upload = client.post(
        "/api/videos",
        files={"video": ("clip.mp4", io.BytesIO(b"data"), "video/mp4")},
        data={"remove_silence": "true", "remove_filler": "true"},
    )
    video_id = upload.json()["video_id"]

    response = client.get("/api/videos")
    assert response.status_code == 200
    assert video_id in {v["id"] for v in response.json()}


def test_show_original_transcript_runs_transcribe_step_even_without_remove_filler(client):
    upload = client.post(
        "/api/videos",
        files={"video": ("clip.mp4", io.BytesIO(b"data"), "video/mp4")},
        data={"remove_silence": "true", "remove_filler": "false", "show_original_transcript": "true"},
    )
    assert upload.status_code == 201
    job_id = upload.json()["job_id"]

    status = client.get(f"/api/jobs/{job_id}")
    body = status.json()
    assert body["status"] == "done"
    steps = {s["step"]: s["status"] for s in body["steps"]}
    assert "transcribe" in steps
    assert steps["transcribe"] == "done"
    assert "detect_filler" not in steps


def test_show_result_transcript_runs_transcribe_step_even_without_remove_filler(client):
    upload = client.post(
        "/api/videos",
        files={"video": ("clip.mp4", io.BytesIO(b"data"), "video/mp4")},
        data={"remove_silence": "true", "remove_filler": "false", "show_result_transcript": "true"},
    )
    assert upload.status_code == 201
    job_id = upload.json()["job_id"]

    status = client.get(f"/api/jobs/{job_id}")
    body = status.json()
    assert body["status"] == "done"
    steps = {s["step"]: s["status"] for s in body["steps"]}
    assert "transcribe" in steps
    assert steps["transcribe"] == "done"
    assert "detect_filler" not in steps


def test_result_transcript_endpoint_returns_segments_once_requested_and_done(client):
    upload = client.post(
        "/api/videos",
        files={"video": ("clip.mp4", io.BytesIO(b"data"), "video/mp4")},
        data={"remove_silence": "false", "remove_filler": "false", "show_result_transcript": "true"},
    )
    video_id = upload.json()["video_id"]

    response = client.get(f"/api/videos/{video_id}/transcript/result")
    assert response.status_code == 200
    body = response.json()
    assert "segments" in body
    if body["segments"]:
        seg = body["segments"][0]
        assert set(seg) == {"text", "original_start", "original_end", "result_start", "result_end"}


def test_result_transcript_endpoint_409s_when_not_requested(client):
    upload = client.post(
        "/api/videos",
        files={"video": ("clip.mp4", io.BytesIO(b"data"), "video/mp4")},
        data={"remove_silence": "true", "remove_filler": "false", "show_result_transcript": "false"},
    )
    video_id = upload.json()["video_id"]

    response = client.get(f"/api/videos/{video_id}/transcript/result")
    assert response.status_code == 409


def test_result_transcript_endpoint_404s_for_unknown_video(client):
    response = client.get("/api/videos/does-not-exist/transcript/result")
    assert response.status_code == 404


def test_transcript_endpoint_returns_segments_once_requested_and_done(client):
    upload = client.post(
        "/api/videos",
        files={"video": ("clip.mp4", io.BytesIO(b"data"), "video/mp4")},
        data={"remove_silence": "true", "remove_filler": "false", "show_original_transcript": "true"},
    )
    video_id = upload.json()["video_id"]

    response = client.get(f"/api/videos/{video_id}/transcript")
    assert response.status_code == 200
    body = response.json()
    assert body["segments"]
    assert body["segments"][0]["text"]


def test_transcript_endpoint_409s_when_not_requested(client):
    upload = client.post(
        "/api/videos",
        files={"video": ("clip.mp4", io.BytesIO(b"data"), "video/mp4")},
        data={"remove_silence": "true", "remove_filler": "false", "show_original_transcript": "false"},
    )
    video_id = upload.json()["video_id"]

    response = client.get(f"/api/videos/{video_id}/transcript")
    assert response.status_code == 409


def test_transcript_endpoint_404s_for_unknown_video(client):
    response = client.get("/api/videos/does-not-exist/transcript")
    assert response.status_code == 404


def test_transcript_partial_endpoint_returns_segments_and_marks_finished(client):
    upload = client.post(
        "/api/videos",
        files={"video": ("clip.mp4", io.BytesIO(b"data"), "video/mp4")},
        data={"remove_silence": "true", "remove_filler": "false", "show_original_transcript": "true"},
    )
    video_id = upload.json()["video_id"]

    response = client.get(f"/api/videos/{video_id}/transcript/partial", params={"after": -1})
    assert response.status_code == 200
    body = response.json()
    assert body["finished"] is True
    assert body["segments"]
    assert body["segments"][0]["text"]
    assert body["next_after"] >= 0


def test_transcript_partial_endpoint_returns_only_segments_past_the_cursor(client):
    upload = client.post(
        "/api/videos",
        files={"video": ("clip.mp4", io.BytesIO(b"data"), "video/mp4")},
        data={"remove_silence": "true", "remove_filler": "false", "show_original_transcript": "true"},
    )
    video_id = upload.json()["video_id"]

    first = client.get(f"/api/videos/{video_id}/transcript/partial", params={"after": -1})
    next_after = first.json()["next_after"]

    response = client.get(f"/api/videos/{video_id}/transcript/partial", params={"after": next_after})
    assert response.status_code == 200
    assert response.json()["segments"] == []


def test_transcript_partial_endpoint_409s_when_not_requested(client):
    upload = client.post(
        "/api/videos",
        files={"video": ("clip.mp4", io.BytesIO(b"data"), "video/mp4")},
        data={"remove_silence": "true", "remove_filler": "false", "show_original_transcript": "false"},
    )
    video_id = upload.json()["video_id"]

    response = client.get(f"/api/videos/{video_id}/transcript/partial", params={"after": -1})
    assert response.status_code == 409


def test_transcript_partial_endpoint_404s_for_unknown_video(client):
    response = client.get("/api/videos/does-not-exist/transcript/partial", params={"after": -1})
    assert response.status_code == 404
