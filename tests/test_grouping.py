from caption_gen import group_words


def _w(word, start, end):
    return {"word": word, "start": start, "end": end}


def test_basic_grouping_under_max():
    words = [_w("a", 0, 0.2), _w("b", 0.3, 0.5), _w("c", 0.6, 0.8)]
    pages = group_words(words)
    assert len(pages) == 1
    assert len(pages[0]) == 3


def test_splits_at_max_words():
    words = [_w(f"w{i}", i * 0.3, i * 0.3 + 0.2) for i in range(8)]
    pages = group_words(words)
    assert len(pages[0]) == 5
    assert len(pages[1]) == 3


def test_splits_at_gap():
    words = [
        _w("a", 0.0, 0.2),
        _w("b", 0.3, 0.5),
        _w("c", 1.0, 1.2),
        _w("d", 1.3, 1.5),
    ]
    pages = group_words(words)
    assert len(pages) == 2
    assert [w["word"] for w in pages[0]] == ["a", "b"]
    assert [w["word"] for w in pages[1]] == ["c", "d"]


def test_single_word_does_not_split():
    words = [
        _w("a", 0.0, 0.2),
        _w("b", 0.8, 1.0),
        _w("c", 1.1, 1.3),
    ]
    pages = group_words(words)
    assert len(pages) == 1
    assert len(pages[0]) == 3


def test_trailing_single_word_merges_backward():
    words = [
        _w("a", 0.0, 0.2),
        _w("b", 0.3, 0.5),
        _w("c", 0.6, 0.8),
        _w("d", 0.9, 1.1),
        _w("e", 1.2, 1.4),
        _w("f", 1.5, 1.7),
    ]
    pages = group_words(words)
    assert len(pages) == 1
    total = sum(len(p) for p in pages)
    assert total == 6


def test_two_words():
    words = [_w("a", 0.0, 0.2), _w("b", 0.3, 0.5)]
    pages = group_words(words)
    assert len(pages) == 1
    assert len(pages[0]) == 2


def test_single_word_input():
    words = [_w("a", 0.0, 0.2)]
    pages = group_words(words)
    assert len(pages) == 1
    assert len(pages[0]) == 1


def test_empty_input():
    assert group_words([]) == []
