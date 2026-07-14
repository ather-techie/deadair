import pytest

from deadair.domain.pipeline.step_configs import TranscribeConfig
from deadair.domain.value_objects.ids import VideoId
from deadair.infrastructure.media.faster_whisper_transcriber import FasterWhisperTranscriber

pytestmark = pytest.mark.slow


def test_transcribes_real_speech_with_word_level_timestamps(fixture_speech_path):
    transcriber = FasterWhisperTranscriber(device="cpu", compute_type="int8")
    video_id = VideoId.new()

    transcript = transcriber.transcribe(fixture_speech_path, video_id, TranscribeConfig(model_name="tiny"))

    assert transcript.video_id == video_id
    words = list(transcript.all_words())
    assert words, "expected at least one transcribed word"
    for word in words:
        assert word.start < word.end
    joined = " ".join(w.text for w in words).lower()
    assert "hello" in joined


def test_reports_progress_during_transcription(fixture_speech_path):
    transcriber = FasterWhisperTranscriber(device="cpu", compute_type="int8")
    reported = []

    transcriber.transcribe(
        fixture_speech_path,
        VideoId.new(),
        TranscribeConfig(model_name="tiny"),
        on_progress=reported.append,
    )

    assert reported
    assert reported[-1] == pytest.approx(1.0)
