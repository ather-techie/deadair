from deadair.domain.entities.transcript import Word
from deadair.domain.policies.filler_policy import (
    FillerWordConfig,
    filler_words_to_ranges,
    find_filler_words,
    is_filler_word,
)
from deadair.domain.value_objects.time_range import TimeRange


def test_is_filler_word_case_insensitive_by_default():
    config = FillerWordConfig()
    assert is_filler_word(Word(text="Um", start=0, end=0.2), config) is True
    assert is_filler_word(Word(text="UM", start=0, end=0.2), config) is True


def test_is_filler_word_strips_punctuation():
    config = FillerWordConfig()
    assert is_filler_word(Word(text="um,", start=0, end=0.2), config) is True


def test_is_filler_word_case_sensitive_mismatch():
    config = FillerWordConfig(case_sensitive=True, words=frozenset({"um"}))
    assert is_filler_word(Word(text="Um", start=0, end=0.2), config) is False
    assert is_filler_word(Word(text="um", start=0, end=0.2), config) is True


def test_non_filler_word_returns_false():
    config = FillerWordConfig()
    assert is_filler_word(Word(text="hello", start=0, end=0.2), config) is False


def test_find_filler_words_filters_list():
    words = [Word(text="um", start=0, end=0.2), Word(text="hello", start=0.2, end=0.6)]
    result = find_filler_words(words, FillerWordConfig())
    assert result == [words[0]]


def test_filler_words_to_ranges():
    words = [Word(text="um", start=0.1, end=0.3), Word(text="uh", start=1.0, end=1.2)]
    assert filler_words_to_ranges(words) == [TimeRange(0.1, 0.3), TimeRange(1.0, 1.2)]
