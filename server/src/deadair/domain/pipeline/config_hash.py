import hashlib
import json
from collections.abc import Mapping
from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any

from deadair.domain.pipeline.step import STEP_DEPENDENCIES, PipelineStep

STEP_ALGO_VERSION: dict[PipelineStep, str] = {s: "v1" for s in PipelineStep}
STEP_ALGO_VERSION[PipelineStep.BUILD_EDL] = "v3"  # short cuts (e.g. isolated filler words) no longer dropped by padding
# Bump a step's entry here when its internal algorithm changes in a way that
# affects output determinism but isn't captured by a config field (e.g. a
# rewritten silence-merge algorithm) — this forces a hash change without a
# config change.


def _canonicalize(value: Any) -> Any:
    """Recursively turn a config value into a JSON-stable structure: dict
    keys sorted, sets/frozensets -> sorted lists, dataclasses -> dict via
    asdict(), enums -> .value, floats rounded to 6 decimals to avoid
    float-repr noise across platforms/reruns."""
    if is_dataclass(value) and not isinstance(value, type):
        return _canonicalize(asdict(value))
    if isinstance(value, Mapping):
        return {str(k): _canonicalize(v) for k, v in sorted(value.items(), key=lambda kv: str(kv[0]))}
    if isinstance(value, (set, frozenset)):
        return sorted(_canonicalize(v) for v in value)
    if isinstance(value, (list, tuple)):
        return [_canonicalize(v) for v in value]
    if isinstance(value, float):
        return round(value, 6)
    if isinstance(value, Enum):
        return value.value
    return value


def compute_config_hash(
    step: PipelineStep,
    own_config: Any,
    upstream_hashes: Mapping[PipelineStep, str],
) -> str:
    expected = STEP_DEPENDENCIES[step]
    if set(upstream_hashes) != set(expected):
        raise ValueError(
            f"upstream_hashes keys {set(upstream_hashes)} must exactly match "
            f"STEP_DEPENDENCIES[{step}] = {expected}"
        )
    payload = {
        "step": step.value,
        "algo_version": STEP_ALGO_VERSION[step],
        "config": _canonicalize(own_config),
        "upstream": {s.value: upstream_hashes[s] for s in sorted(expected, key=lambda s: s.value)},
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
