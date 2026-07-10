# PyonFX: An easy way to create KFX (Karaoke Effects) and complex typesetting using the ASS format (Advanced Substation Alpha).
# Copyright (C) 2019-2025 Antonio Strippoli (CoffeeStraw/YellowFlash)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

from __future__ import annotations

from pyonfx import Shape

DRAWING = "m 0 0 l 100 0 100 100 0 100"


def test_repeated_polygonization_uses_cache() -> None:
    Shape._cached_multipolygon.cache_clear()
    shape = Shape(DRAWING)

    first = shape.to_multipolygon()
    second = shape.to_multipolygon()
    info = Shape._cached_multipolygon.cache_info()

    assert first.equals(second)
    assert info.misses == 1
    assert info.hits == 1


def test_shape_mutation_changes_cache_key() -> None:
    Shape._cached_multipolygon.cache_clear()
    shape = Shape(DRAWING)
    original = shape.to_multipolygon()

    shape.move(50, 25)
    moved = shape.to_multipolygon()
    info = Shape._cached_multipolygon.cache_info()

    assert original.bounds != moved.bounds
    assert info.misses == 2


def test_tolerance_is_part_of_cache_key() -> None:
    Shape._cached_multipolygon.cache_clear()
    shape = Shape("m 0 0 b 100 0 100 100 0 100")

    shape.to_multipolygon(1.0)
    shape.to_multipolygon(5.0)

    assert Shape._cached_multipolygon.cache_info().misses == 2


def test_cache_is_bounded() -> None:
    Shape._cached_multipolygon.cache_clear()
    for index in range(140):
        Shape(f"m {index} 0 l {index + 1} 0 {index + 1} 1 {index} 1").to_multipolygon()

    info = Shape._cached_multipolygon.cache_info()
    assert info.maxsize == 128
    assert info.currsize == 128
