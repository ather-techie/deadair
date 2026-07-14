from deadair.domain.pipeline.result import Failure, Ok


def test_ok_is_ok():
    result = Ok(artifact_ref="ref-1")
    assert result.is_ok() is True
    assert result.is_failure() is False
    assert result.artifact_ref == "ref-1"


def test_failure_is_failure():
    result = Failure(reason="bad file", retryable=False)
    assert result.is_ok() is False
    assert result.is_failure() is True
    assert result.reason == "bad file"
    assert result.retryable is False


def test_failure_defaults_to_retryable():
    assert Failure(reason="transient").retryable is True


def test_pattern_matching_ok_vs_failure():
    def describe(result):
        match result:
            case Ok(artifact_ref=ref):
                return f"ok:{ref}"
            case Failure(reason=r, retryable=rt):
                return f"failure:{r}:{rt}"

    assert describe(Ok(artifact_ref="x")) == "ok:x"
    assert describe(Failure(reason="y", retryable=True)) == "failure:y:True"
