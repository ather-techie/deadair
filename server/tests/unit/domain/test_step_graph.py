from deadair.domain.pipeline.step import STEP_DEPENDENCIES, PipelineStep, downstream_of, upstream_of


def test_extract_audio_has_no_dependencies():
    assert STEP_DEPENDENCIES[PipelineStep.EXTRACT_AUDIO] == frozenset()


def test_enum_declaration_order_is_a_valid_topological_order():
    steps = list(PipelineStep)
    seen: set[PipelineStep] = set()
    for step in steps:
        deps = STEP_DEPENDENCIES[step]
        assert deps <= seen, f"{step} declared before its dependency {deps - seen}"
        seen.add(step)


def test_upstream_of_build_edl_includes_all_ancestors():
    assert upstream_of(PipelineStep.BUILD_EDL) == frozenset(
        {
            PipelineStep.EXTRACT_AUDIO,
            PipelineStep.TRANSCRIBE,
            PipelineStep.DETECT_SILENCE,
            PipelineStep.DETECT_FILLER,
        }
    )


def test_upstream_of_extract_audio_is_empty():
    assert upstream_of(PipelineStep.EXTRACT_AUDIO) == frozenset()


def test_downstream_of_detect_filler_matches_dag():
    assert downstream_of(PipelineStep.DETECT_FILLER) == frozenset(
        {
            PipelineStep.BUILD_EDL,
            PipelineStep.RENDER,
            PipelineStep.CHAPTERS,
            PipelineStep.SUBTITLES,
        }
    )


def test_downstream_of_detect_filler_excludes_transcribe_and_detect_silence():
    downstream = downstream_of(PipelineStep.DETECT_FILLER)
    assert PipelineStep.TRANSCRIBE not in downstream
    assert PipelineStep.DETECT_SILENCE not in downstream


def test_downstream_of_render_is_empty():
    assert downstream_of(PipelineStep.RENDER) == frozenset()


def test_every_step_has_a_dependency_entry():
    assert set(STEP_DEPENDENCIES.keys()) == set(PipelineStep)
