# SOLID Principles in deadair

This document explains the five SOLID design principles and maps each one to concrete code
in this repository. Read it before adding a new port, adapter, domain entity behavior, or
pipeline step — the goal is to extend the codebase without eroding the properties described
below.

The backend (`server/src/deadair/`) is a strict hexagonal / ports-and-adapters architecture
(see `CLAUDE.md`), which already embodies most of SOLID by construction. This doc makes that
explicit so it stays true as the codebase grows.

## S — Single Responsibility Principle

**Definition:** a class or module should have one reason to change — one responsibility,
owned in one place.

**In this repo:** [`domain/entities/job.py`](server/src/deadair/domain/entities/job.py) —
`Job` is the single place that computes aggregate `JobStatus` from per-step `StepStatus`es
(`_derive_status`, line 47) and enforces transition legality (`with_step_updated`, line 105;
`cancel`, line 139 — both raise `InvalidJobTransitionError` once the job is terminal). No
other layer re-derives or overrides job status. `Job`'s per-job pipeline-tuning fields
(`noise_floor_db`, `min_silence_duration`, `padding_seconds`, `min_keep_duration`,
`filler_words`, `filler_case_sensitive` — all `None` by default) are plain data threaded
through by `_step_configs_for` in `run_pipeline_job.py`; `Job` itself has no opinion on their
meaning, keeping this single responsibility intact.

**Do:** keep status-derivation and transition-validity logic inside `Job`.
**Don't:** let API/DTO/mapper code compute or infer job/step status independently — call
into `Job`'s methods instead.

## O — Open/Closed Principle

**Definition:** software entities should be open for extension but closed for modification —
add new behavior without editing existing, working code.

**In this repo:** [`domain/pipeline/step.py`](server/src/deadair/domain/pipeline/step.py) —
`STEP_DEPENDENCIES` (line 18) is a declarative dict mapping each `PipelineStep` to its
`frozenset` of dependencies; `upstream_of`/`downstream_of` (lines 30, 40) compute transitive
closure generically over whatever the dict contains. Adding a new step means adding one enum
member to `PipelineStep` plus one entry to `STEP_DEPENDENCIES` — no existing function needs
to change. `CHAPTERS`/`SUBTITLES` (lines 14-15) already exist as declared-but-unimplemented
steps, skipped explicitly in `run_pipeline_job.py`'s step loop (`if step not in
configs: continue`, where `configs = _step_configs_for(job)`) — a live example of an extension
point waiting to be filled in.

**Do:** extend `STEP_DEPENDENCIES` (and the enum, keeping declaration order topologically
valid — asserted by `tests/unit/domain/test_step_graph.py`) for new steps.
**Don't:** hardcode step ordering elsewhere, or special-case a new step's name inside
unrelated functions instead of extending the dependency graph.

## L — Liskov Substitution Principle

**Definition:** subtypes must be behaviorally substitutable for their base type — any code
written against the abstraction should work unmodified against every implementation.

**In this repo:** [`tests/contract/`](server/tests/contract/) holds one shared behavioral
contract per port — `JobRepositoryContractTests`, `VideoRepositoryContractTests`,
`ArtifactRepositoryContractTests`, `ProgressReporterContractTests`. Every concrete adapter
(sqlite, in-memory, disk) subclasses the matching contract instead of writing bespoke
assertions, e.g. a sqlite job-repository test subclasses `JobRepositoryContractTests` and
only supplies its own `repo` fixture. This guarantees any adapter behind a port is truly
interchangeable, not just type-compatible.

**Do:** when adding a new adapter for an existing port, subclass its contract test in
`tests/contract/` rather than writing fresh assertions.
**Don't:** let one adapter silently behave differently from another in ways callers would
need to know about (e.g. different error types for the same failure, different ordering
guarantees) — that difference belongs in the contract test, and every adapter must satisfy it.

## I — Interface Segregation Principle

**Definition:** prefer several small, client-specific interfaces over one broad, general
one — no client should depend on methods it doesn't use.

**In this repo:** [`application/ports/`](server/src/deadair/application/ports/) defines ten
narrow, single-purpose ABCs, each with 1-4 focused methods: `AudioExtractor.extract`,
`Transcriber.transcribe`, `SilenceDetector.detect_candidate_gaps`, `VideoRenderer.render`,
`JobRunner.enqueue`/`cancel`, `ProgressReporter.report`/`get`, `ArtifactRepository.get`/
`put`/`exists`/`invalidate_video`, `TranscriptSegmentSink.append`/`list_after` (incremental
mid-transcription segments, distinct from `ArtifactRepository`'s whole-`Transcript` caching),
`JobRepository`'s CRUD-style methods, and `VideoRepository`'s. Each also raises its own
domain-specific errors rather than leaking storage/adapter-specific exceptions.

**Do:** add a new, narrow port when a use case needs a new capability.
**Don't:** bundle unrelated capabilities into one broad interface (e.g. a single
"MediaService" covering extraction, transcription, and rendering) — that would force
adapters and callers to depend on methods they don't need.

## D — Dependency Inversion Principle

**Definition:** high-level policy should depend on abstractions, not on low-level detail;
concrete implementations should be wired in from the outside.

**In this repo:** [`container.py`](server/src/deadair/container.py) is the single
composition root — `Container` (line 30) is typed entirely in terms of port ABCs, and
`build_container()` (line 48) is the *only* place concrete infrastructure classes
(`SqliteJobRepository`, `FfmpegAudioExtractor`, `FasterWhisperTranscriber`, `RQJobRunner`,
`SqliteTranscriptSegmentSink`, ...) are imported and instantiated. `run_pipeline_job.py`'s
orchestrator calls only `container.audio_extractor.extract(...)`,
`container.transcriber.transcribe(...)`, etc. — never imports an infrastructure module
directly.

**Do:** wire new adapters exclusively inside `build_container()`.
**Don't:** import anything from `infrastructure/` inside `domain/`, `application/`, or
`presentation/` — those layers should only ever see port ABCs.

## Checklist for adding new functionality

1. New capability needed? Add a narrow port in `application/ports/` (**ISP**) — don't grow
   an existing port with unrelated methods.
2. Wire the concrete adapter only in `container.py`'s `build_container()` (**DIP**) — never
   import infrastructure from domain/application/presentation.
3. New adapter for an existing port? Subclass its contract test in `tests/contract/`
   (**LSP**) instead of writing standalone assertions.
4. New pipeline step or entity behavior? Extend `STEP_DEPENDENCIES` / add a new transition
   method rather than modifying existing dependency or status logic (**OCP**/**SRP**).
