from enum import Enum


class PipelineStep(str, Enum):
    """Declaration order is intentionally a valid topological order of
    STEP_DEPENDENCIES below — enforced by a unit test."""

    EXTRACT_AUDIO = "extract_audio"
    TRANSCRIBE = "transcribe"
    DETECT_SILENCE = "detect_silence"
    DETECT_FILLER = "detect_filler"
    BUILD_EDL = "build_edl"
    RENDER = "render"
    CHAPTERS = "chapters"
    SUBTITLES = "subtitles"


STEP_DEPENDENCIES: dict[PipelineStep, frozenset[PipelineStep]] = {
    PipelineStep.EXTRACT_AUDIO: frozenset(),
    PipelineStep.TRANSCRIBE: frozenset({PipelineStep.EXTRACT_AUDIO}),
    PipelineStep.DETECT_SILENCE: frozenset({PipelineStep.EXTRACT_AUDIO}),
    PipelineStep.DETECT_FILLER: frozenset({PipelineStep.TRANSCRIBE}),
    PipelineStep.BUILD_EDL: frozenset({PipelineStep.DETECT_SILENCE, PipelineStep.DETECT_FILLER}),
    PipelineStep.RENDER: frozenset({PipelineStep.BUILD_EDL}),
    PipelineStep.CHAPTERS: frozenset({PipelineStep.BUILD_EDL, PipelineStep.TRANSCRIBE}),
    PipelineStep.SUBTITLES: frozenset({PipelineStep.TRANSCRIBE, PipelineStep.BUILD_EDL}),
}


def upstream_of(step: PipelineStep) -> frozenset[PipelineStep]:
    """Transitive closure of dependencies."""
    result: set[PipelineStep] = set()
    frontier = set(STEP_DEPENDENCIES[step])
    while frontier:
        result |= frontier
        frontier = set().union(*(STEP_DEPENDENCIES[f] for f in frontier)) - result
    return frozenset(result)


def downstream_of(step: PipelineStep) -> frozenset[PipelineStep]:
    """All steps transitively depending on `step` — i.e. everything that must
    be invalidated when `step`'s config (or algorithm) changes."""
    return frozenset(s for s in PipelineStep if step in upstream_of(s))
