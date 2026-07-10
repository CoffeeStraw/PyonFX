# PyonFX: An easy way to create KFX (Karaoke Effects) and complex typesetting using the ASS format (Advanced Substation Alpha).
# Copyright (C) 2019-2025 Antonio Strippoli (CoffeeStraw/YellowFlash)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

"""Robust Shapely helpers shared by vector-heavy effects."""

from __future__ import annotations

from collections.abc import Iterator

from shapely.errors import GEOSException, ShapelyError
from shapely.geometry import GeometryCollection, MultiPolygon, Polygon
from shapely.validation import make_valid


def _iter_polygons(geometry: object) -> Iterator[Polygon]:
    if isinstance(geometry, Polygon):
        if not geometry.is_empty:
            yield geometry
        return
    if isinstance(geometry, MultiPolygon):
        yield from (polygon for polygon in geometry.geoms if not polygon.is_empty)
        return
    if isinstance(geometry, GeometryCollection):
        for child in geometry.geoms:
            yield from _iter_polygons(child)


def ensure_multipolygon(geometry: object) -> MultiPolygon:
    """Return all polygonal components of a Shapely geometry as MultiPolygon."""

    if geometry is None or getattr(geometry, "is_empty", False):
        return MultiPolygon()
    if isinstance(geometry, MultiPolygon):
        return geometry
    polygons = list(_iter_polygons(geometry))
    return MultiPolygon(polygons) if polygons else MultiPolygon()


def _coerce_valid_multipolygon(geometry: object) -> MultiPolygon | None:
    """Return a valid MultiPolygon fast path, or None when repair is needed."""

    if geometry is None or getattr(geometry, "is_empty", False):
        return MultiPolygon()
    if isinstance(geometry, MultiPolygon):
        return geometry if geometry.is_valid else None
    if isinstance(geometry, Polygon):
        return MultiPolygon([geometry]) if geometry.is_valid else None
    if isinstance(geometry, GeometryCollection):
        polygons = list(_iter_polygons(geometry))
        if not polygons:
            return MultiPolygon()
        candidate = MultiPolygon(polygons)
        return candidate if candidate.is_valid else None
    return MultiPolygon()


def repair_geometry(geometry: object) -> MultiPolygon:
    """Repair polygonal geometry and return a best-effort valid MultiPolygon.

    Non-polygonal and empty inputs return an empty MultiPolygon. Valid inputs
    use a fast path without calling ``make_valid`` or ``buffer(0)``.
    """

    fast_path = _coerce_valid_multipolygon(geometry)
    if fast_path is not None:
        return fast_path

    repaired = geometry
    try:
        repaired = make_valid(repaired)
    except (GEOSException, ShapelyError, ValueError, TypeError):
        pass

    repaired = ensure_multipolygon(repaired)
    if repaired.is_empty or repaired.is_valid:
        return repaired

    try:
        repaired = ensure_multipolygon(repaired.buffer(0))
    except (GEOSException, ShapelyError, ValueError, TypeError):
        pass
    if repaired.is_empty or repaired.is_valid:
        return repaired

    try:
        repaired = ensure_multipolygon(make_valid(repaired.buffer(0)))
    except (GEOSException, ShapelyError, ValueError, TypeError):
        pass
    return repaired


def bounds_intersect(
    left: tuple[float, float, float, float],
    right: tuple[float, float, float, float],
) -> bool:
    """Return whether two axis-aligned bounds overlap with positive area."""

    return not (
        left[2] <= right[0]
        or right[2] <= left[0]
        or left[3] <= right[1]
        or right[3] <= left[1]
    )


def safe_difference(
    outer_geometry: object,
    inner_geometry: object,
    *,
    shrink_fallback: float | None = None,
) -> MultiPolygon:
    """Compute a robust polygonal difference with repair and fallbacks.

    If all boolean attempts fail, the repaired outer geometry is returned.
    ``shrink_fallback`` is opt-in because changing the inner geometry changes
    the mathematical result and should be an explicit effect decision.
    """

    outer = repair_geometry(outer_geometry)
    inner = repair_geometry(inner_geometry)
    if outer.is_empty:
        return MultiPolygon()
    if inner.is_empty:
        return outer

    try:
        return repair_geometry(outer.difference(inner))
    except (GEOSException, ShapelyError, ValueError, TypeError):
        pass
    try:
        return repair_geometry(outer.buffer(0).difference(inner.buffer(0)))
    except (GEOSException, ShapelyError, ValueError, TypeError):
        pass

    if shrink_fallback is not None:
        try:
            shrunken = repair_geometry(inner.buffer(shrink_fallback))
            if not shrunken.is_empty:
                return repair_geometry(outer.difference(shrunken))
        except (GEOSException, ShapelyError, ValueError, TypeError):
            pass
    return outer


def safe_intersection(geometry: object, mask_geometry: object) -> MultiPolygon:
    """Compute a robust polygonal intersection and normalize its result."""

    try:
        result = geometry.intersection(mask_geometry)
    except (AttributeError, GEOSException, ShapelyError, ValueError, TypeError):
        try:
            geometry_fixed = repair_geometry(geometry)
            mask_fixed = repair_geometry(mask_geometry)
            result = geometry_fixed.buffer(0).intersection(mask_fixed.buffer(0))
        except (GEOSException, ShapelyError, ValueError, TypeError):
            return MultiPolygon()
    fast_path = _coerce_valid_multipolygon(result)
    if fast_path is not None:
        return fast_path
    return repair_geometry(result)
