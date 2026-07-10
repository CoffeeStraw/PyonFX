from __future__ import annotations

import pytest

from pyonfx.effect import retime_line, retime_start_to_syllable, retime_syllable


@pytest.mark.parametrize(
    ("arguments", "expected"),
    [
        ((1000, 200, 500, 0, 0), (1200, 1500)),
        ((1000, 200, 500, -300, 400), (900, 1900)),
        ((100, 0, 50, -500, -300), (0, 0)),
        ((0, 0, 0, 0, 0), (0, 0)),
        ((5000, 1000, 2500, -1000, -500), (5000, 7000)),
    ],
)
def test_retime_syllable(arguments: tuple[int, ...], expected: tuple[int, int]) -> None:
    assert retime_syllable(*arguments) == expected


@pytest.mark.parametrize(
    ("arguments", "expected"),
    [
        ((1000, 200, -300, 500), (900, 1700)),
        ((0, 100, -500, -200), (0, 0)),
        ((5000, 1500, 0, 300), (6500, 6800)),
    ],
)
def test_retime_start_to_syllable(
    arguments: tuple[int, ...], expected: tuple[int, int]
) -> None:
    assert retime_start_to_syllable(*arguments) == expected


@pytest.mark.parametrize(
    ("arguments", "expected"),
    [
        ((1000, 5000, 0, 0), (1000, 5000)),
        ((1000, 5000, -2000, 500), (0, 5500)),
        ((1000, 2000, 2000, -2000), (3000, 3000)),
        ((0, 0, -100, -200), (0, 0)),
    ],
)
def test_retime_line(arguments: tuple[int, ...], expected: tuple[int, int]) -> None:
    assert retime_line(*arguments) == expected
