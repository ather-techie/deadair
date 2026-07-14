from deadair.domain.entities.transcript import Segment, Transcript, Word
from deadair.domain.value_objects.ids import VideoId


def test_all_words_flattens_segments_in_order():
    w1 = Word(text="hello", start=0.0, end=0.5)
    w2 = Word(text="world", start=0.5, end=1.0)
    w3 = Word(text="again", start=1.0, end=1.5)
    seg1 = Segment(words=(w1, w2), start=0.0, end=1.0, text="hello world")
    seg2 = Segment(words=(w3,), start=1.0, end=1.5, text="again")
    transcript = Transcript(video_id=VideoId.new(), segments=(seg1, seg2), language="en")

    assert list(transcript.all_words()) == [w1, w2, w3]


def test_all_words_empty_segments():
    transcript = Transcript(video_id=VideoId.new(), segments=(), language="en")
    assert list(transcript.all_words()) == []
