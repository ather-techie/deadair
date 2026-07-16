import string
from collections.abc import Sequence
from dataclasses import dataclass

from deadair.domain.entities.transcript import Word
from deadair.domain.value_objects.time_range import TimeRange

DEFAULT_FILLER_WORDS: frozenset[str] = frozenset(
    {"um", "uh", "uhh", "umm", "hm", "hmm", "like", "actually",
     "basically", "so", "literally", "right", "okay", "well"}
)


@dataclass(frozen=True, slots=True)
class FillerWordConfig:
    words: frozenset[str] = DEFAULT_FILLER_WORDS
    case_sensitive: bool = False


def parse_filler_words(raw: str) -> frozenset[str]:
    return frozenset(w.strip() for w in raw.split(",") if w.strip())


def is_filler_word(word: Word, config: FillerWordConfig) -> bool:
    text = word.text.strip(string.punctuation)
    if not config.case_sensitive:
        text = text.lower()
        vocab = {w.lower() for w in config.words}
    else:
        vocab = config.words
    return text in vocab


def find_filler_words(words: Sequence[Word], config: FillerWordConfig) -> list[Word]:
    return [w for w in words if is_filler_word(w, config)]


def filler_words_to_ranges(filler_words: Sequence[Word]) -> list[TimeRange]:
    return [TimeRange(w.start, w.end) for w in filler_words]
