import pytest

from deadair.domain.pipeline.config_hash import compute_config_hash
from deadair.domain.pipeline.step import PipelineStep
from deadair.domain.pipeline.step_configs import ExtractAudioConfig, TranscribeConfig
from deadair.domain.policies.filler_policy import FillerWordConfig


def test_same_inputs_produce_same_hash():
    h1 = compute_config_hash(PipelineStep.EXTRACT_AUDIO, ExtractAudioConfig(), {})
    h2 = compute_config_hash(PipelineStep.EXTRACT_AUDIO, ExtractAudioConfig(), {})
    assert h1 == h2


def test_own_config_change_changes_hash():
    h1 = compute_config_hash(PipelineStep.EXTRACT_AUDIO, ExtractAudioConfig(sample_rate=16000), {})
    h2 = compute_config_hash(PipelineStep.EXTRACT_AUDIO, ExtractAudioConfig(sample_rate=44100), {})
    assert h1 != h2


def test_mismatched_upstream_hash_keys_raise():
    with pytest.raises(ValueError):
        compute_config_hash(PipelineStep.TRANSCRIBE, TranscribeConfig(), {})


def test_upstream_hash_change_propagates_to_downstream_hash():
    extract_h1 = compute_config_hash(PipelineStep.EXTRACT_AUDIO, ExtractAudioConfig(sample_rate=16000), {})
    extract_h2 = compute_config_hash(PipelineStep.EXTRACT_AUDIO, ExtractAudioConfig(sample_rate=44100), {})

    transcribe_h1 = compute_config_hash(
        PipelineStep.TRANSCRIBE, TranscribeConfig(), {PipelineStep.EXTRACT_AUDIO: extract_h1}
    )
    transcribe_h2 = compute_config_hash(
        PipelineStep.TRANSCRIBE, TranscribeConfig(), {PipelineStep.EXTRACT_AUDIO: extract_h2}
    )
    assert transcribe_h1 != transcribe_h2


def test_sibling_step_config_change_does_not_affect_unrelated_step_hash():
    extract_h = compute_config_hash(PipelineStep.EXTRACT_AUDIO, ExtractAudioConfig(), {})

    transcribe_h = compute_config_hash(
        PipelineStep.TRANSCRIBE, TranscribeConfig(), {PipelineStep.EXTRACT_AUDIO: extract_h}
    )

    detect_filler_h1 = compute_config_hash(
        PipelineStep.DETECT_FILLER,
        FillerWordConfig(words=frozenset({"um"})),
        {PipelineStep.TRANSCRIBE: transcribe_h},
    )
    detect_filler_h2 = compute_config_hash(
        PipelineStep.DETECT_FILLER,
        FillerWordConfig(words=frozenset({"um", "uh"})),
        {PipelineStep.TRANSCRIBE: transcribe_h},
    )
    assert detect_filler_h1 != detect_filler_h2

    # Changing DETECT_FILLER's config must not change its upstream TRANSCRIBE hash.
    transcribe_h_again = compute_config_hash(
        PipelineStep.TRANSCRIBE, TranscribeConfig(), {PipelineStep.EXTRACT_AUDIO: extract_h}
    )
    assert transcribe_h == transcribe_h_again


def test_float_rounding_avoids_repr_noise():
    h1 = compute_config_hash(PipelineStep.EXTRACT_AUDIO, {"threshold": 0.1 + 0.2}, {})
    h2 = compute_config_hash(PipelineStep.EXTRACT_AUDIO, {"threshold": 0.3}, {})
    assert h1 == h2
