# PyonFX: An easy way to create KFX (Karaoke Effects) and complex typesetting using the ASS format (Advanced Substation Alpha).
# Copyright (C) 2019-2025 Antonio Strippoli (CoffeeStraw/YellowFlash)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

from __future__ import annotations

import math

from shapely.geometry import (
    GeometryCollection,
    LineString,
    MultiPolygon,
    Point,
    Polygon,
    box,
)

from pyonfx import (
    bounds_intersect,
    ensure_multipolygon,
    repair_geometry,
    safe_difference,
    safe_intersection,
)


def test_ensure_multipolygon_handles_empty_and_none() -> None:
    assert ensure_multipolygon(None).is_empty
    assert ensure_multipolygon(Polygon()).is_empty


def test_ensure_multipolygon_preserves_multipolygon_identity() -> None:
    original = MultiPolygon([box(0, 0, 1, 1)])
    assert ensure_multipolygon(original) is original


def test_ensure_multipolygon_wraps_polygon() -> None:
    result = ensure_multipolygon(box(0, 0, 2, 3))
    assert isinstance(result, MultiPolygon)
    assert math.isclose(result.area, 6.0)


def test_ensure_multipolygon_extracts_nested_collection_polygons() -> None:
    nested = GeometryCollection(
        [
            Point(5, 5),
            box(0, 0, 1, 1),
            GeometryCollection([LineString([(0, 0), (1, 1)]), box(2, 2, 4, 4)]),
        ]
    )
    result = ensure_multipolygon(nested)
    assert len(result.geoms) == 2
    assert math.isclose(result.area, 5.0)


def test_ensure_multipolygon_discards_non_polygon_geometry() -> None:
    assert ensure_multipolygon(LineString([(0, 0), (1, 1)])).is_empty


def test_repair_geometry_fast_path_keeps_valid_geometry() -> None:
    original = MultiPolygon([box(0, 0, 2, 2)])
    assert repair_geometry(original) is original


def test_repair_geometry_repairs_self_intersection() -> None:
    bow_tie = Polygon([(0, 0), (2, 2), (0, 2), (2, 0), (0, 0)])
    assert bow_tie.is_valid is False
    repaired = repair_geometry(bow_tie)
    assert repaired.is_valid
    assert not repaired.is_empty
    assert math.isclose(repaired.area, 2.0)


def test_bounds_intersect_requires_positive_overlap() -> None:
    assert bounds_intersect((0, 0, 2, 2), (1, 1, 3, 3))
    assert not bounds_intersect((0, 0, 1, 1), (1, 0, 2, 1))
    assert not bounds_intersect((0, 0, 1, 1), (2, 2, 3, 3))


def test_safe_difference_returns_expected_area() -> None:
    result = safe_difference(box(0, 0, 10, 10), box(2, 2, 8, 8))
    assert result.is_valid
    assert math.isclose(result.area, 64.0)


def test_safe_difference_with_empty_inner_returns_outer() -> None:
    outer = box(0, 0, 3, 3)
    result = safe_difference(outer, Polygon())
    assert math.isclose(result.area, outer.area)


def test_safe_intersection_returns_expected_area() -> None:
    result = safe_intersection(box(0, 0, 3, 3), box(2, 2, 4, 4))
    assert result.is_valid
    assert math.isclose(result.area, 1.0)


def test_safe_intersection_short_circuits_disjoint_bounds() -> None:
    result = safe_intersection(box(0, 0, 1, 1), box(10, 10, 11, 11))
    assert result.is_empty


def test_safe_intersection_accepts_invalid_input() -> None:
    bow_tie = Polygon([(0, 0), (2, 2), (0, 2), (2, 0), (0, 0)])
    result = safe_intersection(bow_tie, box(0, 0, 1, 2))
    assert result.is_valid
    assert not result.is_empty
