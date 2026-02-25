"""
Unit tests — Braille Classifier
================================

Validates Grade 1 expansions (digits, punctuation, contractions, indicators).
"""

from dataclasses import dataclass

from core.braille.braille_classifier import BrailleClassifier


@dataclass
class FakeCell:
    row: int
    col: int
    dots: list[bool]


def _dots_to_bool(dot_numbers: list[int]) -> list[bool]:
    dots = [False] * 6
    for dot in dot_numbers:
        dots[dot - 1] = True
    return dots


def _cell(dot_numbers: list[int], col: int) -> FakeCell:
    return FakeCell(row=0, col=col, dots=_dots_to_bool(dot_numbers))


def _classify_chars(cells: list[FakeCell]) -> str:
    clf = BrailleClassifier()
    chars = clf.classify_sequence(cells)
    return "".join(ch.char for ch in chars)


def test_digits_1_through_9() -> None:
    cells = [
        _cell([3, 4, 5, 6], 0),
        _cell([1], 1),
        _cell([1, 2], 2),
        _cell([1, 4], 3),
        _cell([1, 4, 5], 4),
        _cell([1, 5], 5),
        _cell([1, 2, 4], 6),
        _cell([1, 2, 4, 5], 7),
        _cell([1, 2, 5], 8),
        _cell([2, 4], 9),
    ]
    assert _classify_chars(cells) == "123456789"


def test_digit_0() -> None:
    cells = [_cell([3, 4, 5, 6], 0), _cell([2, 4, 5], 1)]
    assert _classify_chars(cells) == "0"


def test_capital_indicator() -> None:
    cells = [_cell([6], 0), _cell([1], 1)]
    assert _classify_chars(cells) == "A"


def test_punctuation_period() -> None:
    cells = [_cell([2, 5, 6], 0)]
    assert _classify_chars(cells) == "."


def test_punctuation_question() -> None:
    cells = [_cell([2, 3, 6], 0)]
    assert _classify_chars(cells) == "?"


def test_number_mode_resets_on_space() -> None:
    cells = [
        _cell([3, 4, 5, 6], 0),
        _cell([1], 1),
        _cell([], 2),
        _cell([1], 3),
    ]
    assert _classify_chars(cells) == "1 a"


def test_mixed_sequence() -> None:
    cells = [
        _cell([1], 0),
        _cell([3, 4, 5, 6], 1),
        _cell([1, 2], 2),
        _cell([2, 4, 5], 3),
        _cell([2, 5, 6], 4),
    ]
    assert _classify_chars(cells) == "a20."


def test_contraction_the() -> None:
    cells = [_cell([2, 3, 4, 6], 0)]
    assert _classify_chars(cells) == "the"
