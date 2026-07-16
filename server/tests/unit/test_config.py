import pytest
from pydantic import ValidationError

from deadair.config import Settings


def _settings(**overrides) -> Settings:
    # _env_file=None: isolate these tests from whatever the developer's local,
    # gitignored server/.env happens to contain.
    return Settings(_env_file=None, ffmpeg_binary_path="/usr/bin/ffmpeg", **overrides)


def test_tuning_params_default_to_none():
    settings = _settings()
    assert settings.noise_floor_db is None
    assert settings.min_silence_duration is None
    assert settings.padding_seconds is None
    assert settings.min_keep_duration is None
    assert settings.filler_words is None
    assert settings.filler_case_sensitive is None
    assert settings.resolved_filler_words() is None


def test_tuning_params_can_be_set():
    settings = _settings(
        noise_floor_db=-40.0,
        min_silence_duration=0.75,
        padding_seconds=0.2,
        min_keep_duration=0.4,
        filler_words="um, like",
        filler_case_sensitive=True,
    )
    assert settings.noise_floor_db == -40.0
    assert settings.min_silence_duration == 0.75
    assert settings.padding_seconds == 0.2
    assert settings.min_keep_duration == 0.4
    assert settings.resolved_filler_words() == frozenset({"um", "like"})
    assert settings.filler_case_sensitive is True


@pytest.mark.parametrize("field", ["min_silence_duration", "padding_seconds", "min_keep_duration"])
def test_negative_tuning_param_raises_validation_error(field):
    with pytest.raises(ValidationError):
        _settings(**{field: -1.0})
