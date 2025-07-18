import math

import pytest

from pyonfx.shape import Shape


def test_polygon_invalid_edges():
    with pytest.raises(ValueError):
        Shape.polygon(2, 10)


def test_polygon_side_length_negative():
    with pytest.raises(ValueError):
        Shape.polygon(5, -1)


def test_polygon_basic_properties():
    poly = Shape.polygon(4, 10)
    min_x, min_y, max_x, max_y = poly.bounding(exact=False)
    assert math.isclose(max_x - min_x, 10, abs_tol=1e-3)
    assert math.isclose(max_y - min_y, 10, abs_tol=1e-3)


def test_ellipse_bounding():
    w, h = 20, 10
    ell = Shape.ellipse(w, h)
    min_x, min_y, max_x, max_y = ell.bounding(exact=False)
    assert math.isclose(max_x - min_x, w, abs_tol=1e-3)
    assert math.isclose(max_y - min_y, h, abs_tol=1e-3)


def test_ring_invalid_radii():
    with pytest.raises(ValueError):
        Shape.ring(5, 5)


def test_ring_bounding():
    ring = Shape.ring(10, 5)
    min_x, min_y, max_x, max_y = ring.bounding(exact=False)
    assert math.isclose(max_x - min_x, 20, abs_tol=1e-3)
    assert math.isclose(max_y - min_y, 20, abs_tol=1e-3)
