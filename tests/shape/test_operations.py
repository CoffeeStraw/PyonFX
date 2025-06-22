import pytest
import math
from copy import copy

from pyonfx.shape import Shape

from .fixtures import *


def test_map():
    """Test the map method."""
    original = Shape("m 0 0 l 20 0 20 10 0 10")
    dest = Shape("m 10 5 l 30 5 30 15 10 15")
    assert original.map(lambda x, y: (x + 10, y + 5)) == dest

    original = Shape("m -100.5 0 l 100 0 b 100 100 -100 100 -100.5 0 c")
    dest = Shape("m -10.05 0 l 10 0 b 10 200 -10 200 -10.05 0 c")
    assert original.map(lambda x, y: (x / 10, y * 2)) == dest

    original = Shape("m 0.5 0.4 l 20.5 0.6 20.7 10.1 0.6 10.4")
    dest = Shape("m 0 0 l 20 1 21 10 1 10")
    assert original.map(lambda x, y: (round(x), round(y))) == dest

    with pytest.raises(ValueError):
        Shape("m 0 0 l 20 0 20 10 0 10 22").map(lambda x, y: (x, y))

    # Type-aware mapping
    def translate_moves(x, y, typ):
        return (x + 10, y + 5) if typ == "m" else (x, y)

    assert Shape("m 0 0 l 20 0 20 10 0 10").map(translate_moves) == Shape(
        "m 10 5 l 20 0 20 10 0 10"
    )


def test_bounding():
    original = Shape("m -100.5 0 l 100 0 b 100 100 -100 100 -100.5 0 c")
    assert original.bounding(exact=False) == (-100.5, 0, 100, 100)

    original = Shape("m 0 0 l 20 0 20 10 0 10")
    assert original.bounding(exact=True) == (0.0, 0.0, 20.0, 10.0)

    original = Shape("m 0 0 l 20 0 20 10 0 10")
    assert original.bounding(exact=False) == (0.0, 0.0, 20.0, 10.0)

    original = Shape(
        "m 313 312 b 255 275 482 38 277 212 l 436 269 b 378 388 461 671 260 481 235 431 118 430 160 282"
    )
    assert original.bounding(exact=True) == (
        150.98535796762013,
        148.88438545593218,
        436.0,
        544.871772934194,
    )

    original = Shape(
        "m 313 312 b 254 287 482 38 277 212 l 436 269 b 378 388 461 671 260 481"
    )
    assert original.bounding(exact=True) == (
        260.0,
        150.67823683425252,
        436.0,
        544.871772934194,
    )
    assert original.bounding(exact=False) == (254.0, 38.0, 482.0, 671.0)


def test_move():
    original = Shape("m -100.5 0 l 100 0 b 100 100 -100 100 -100.5 0 c")
    dest = Shape("m -95.5 -2 l 105 -2 b 105 98 -95 98 -95.5 -2 c")
    assert original.move(5, -2) == dest
    assert original.move(0, 0) == original


def test_align():
    # Test centering
    original = Shape("m 0 0 l 20 0 20 10 0 10")
    assert copy(original).align() == original
    assert copy(original).move(10, 400).align() == original

    # Test an
    original = Shape("m 0 0 l 500 0 500 200 0 200")
    assert copy(original).align(anchor=5, an=5) == original
    dest1 = Shape("m -250 100 l 250 100 250 300 -250 300")
    assert original.align(anchor=5, an=1) == dest1
    dest2 = Shape("m 0 100 l 500 100 500 300 0 300")
    assert original.align(anchor=5, an=2) == dest2
    dest3 = Shape("m 250 100 l 750 100 750 300 250 300")
    assert original.align(anchor=5, an=3) == dest3
    dest4 = Shape("m -250 0 l 250 0 250 200 -250 200")
    assert original.align(anchor=5, an=4) == dest4
    dest6 = Shape("m 250 0 l 750 0 750 200 250 200")
    assert original.align(anchor=5, an=6) == dest6
    dest7 = Shape("m -250 -100 l 250 -100 250 100 -250 100")
    assert original.align(anchor=5, an=7) == dest7
    dest8 = Shape("m 0 -100 l 500 -100 500 100 0 100")
    assert original.align(anchor=5, an=8) == dest8
    dest9 = Shape("m 250 -100 l 750 -100 750 100 250 100")
    assert original.align(anchor=5, an=9) == dest9

    original = Shape(
        "m 411.87 306.36 b 385.63 228.63 445.78 147.2 536.77 144.41 630.18 147.77 697 236.33 665.81 310.49 591.86 453.18 437.07 395.59 416 316.68"
    )
    dest3 = Shape(
        "m 183.614 344.04 b 157.374 266.31 217.524 184.88 308.514 182.09 401.924 185.45 468.744 274.01 437.554 348.17 363.604 490.86 208.814 433.27 187.744 354.36"
    )
    assert original.align(anchor=5, an=3) == dest3
    dest5 = Shape(
        "m 27.929 189.655 b 1.689 111.925 61.839 30.495 152.829 27.705 246.239 31.065 313.059 119.625 281.869 193.785 207.919 336.475 53.129 278.885 32.059 199.975"
    )
    assert original.align(anchor=5, an=5) == dest5
    dest7 = Shape(
        "m -127.756 35.27 b -153.996 -42.46 -93.846 -123.89 -2.856 -126.68 90.554 -123.32 157.374 -34.76 126.184 39.4 52.234 182.09 -102.556 124.5 -123.626 45.59"
    )
    assert original.align(anchor=5, an=7) == dest7

    # Test anchor
    original = Shape("m 0 0 l 500 0 500 200 0 200")
    dest1 = Shape("m 250 -100 l 750 -100 750 100 250 100")
    assert original.align(anchor=1, an=5) == dest1
    dest2 = Shape("m 0 -100 l 500 -100 500 100 0 100")
    assert original.align(anchor=2, an=5) == dest2
    dest3 = Shape("m -250 -100 l 250 -100 250 100 -250 100")
    assert original.align(anchor=3, an=5) == dest3
    dest4 = Shape("m 250 0 l 750 0 750 200 250 200")
    assert original.align(anchor=4, an=5) == dest4
    dest5 = Shape("m 0 0 l 500 0 500 200 0 200")
    assert original.align(anchor=5, an=5) == dest5
    dest6 = Shape("m -250 0 l 250 0 250 200 -250 200")
    assert original.align(anchor=6, an=5) == dest6
    dest7 = Shape("m 250 100 l 750 100 750 300 250 300")
    assert original.align(anchor=7, an=5) == dest7
    dest8 = Shape("m 0 100 l 500 100 500 300 0 300")
    assert original.align(anchor=8, an=5) == dest8
    dest9 = Shape("m -250 100 l 250 100 250 300 -250 300")
    assert original.align(anchor=9, an=5) == dest9

    # Test anchor + an
    original = Shape("m 342 352 l 338 544 734 536 736 350 b 784 320 1157 167 930 232")
    dest_anchor_7_an_5 = Shape(
        "m 413.5 324.427 l 409.5 516.427 805.5 508.427 807.5 322.427 b 855.5 292.427 1228.5 139.427 1001.5 204.427"
    )
    assert original.align(anchor=7, an=5) == dest_anchor_7_an_5
    dest_anchor_9_an_1 = Shape(
        "m -660.664 512.927 l -664.664 704.927 -268.664 696.927 -266.664 510.927 b -218.664 480.927 154.336 327.927 -72.664 392.927"
    )
    assert original.align(anchor=9, an=1) == dest_anchor_9_an_1
    dest_anchor_9_an_5 = Shape(
        "m -251.164 324.427 l -255.164 516.427 140.836 508.427 142.836 322.427 b 190.836 292.427 563.836 139.427 336.836 204.427"
    )
    assert original.align(anchor=9, an=5) == dest_anchor_9_an_5
    dest_anchor_9_an_9 = Shape(
        "m 158.336 135.927 l 154.336 327.927 550.336 319.927 552.336 133.927 b 600.336 103.927 973.336 -49.073 746.336 15.927"
    )
    assert original.align(anchor=9, an=9) == dest_anchor_9_an_9
    dest_anchor_3_an_5 = Shape(
        "m -251.164 -3.5 l -255.164 188.5 140.836 180.5 142.836 -5.5 b 190.836 -35.5 563.836 -188.5 336.836 -123.5"
    )
    assert original.align(anchor=3, an=5) == dest_anchor_3_an_5
    dest_anchor_5_an_5 = Shape(
        "m 81.168 160.464 l 77.168 352.464 473.168 344.464 475.168 158.464 b 523.168 128.464 896.168 -24.536 669.168 40.464"
    )
    assert original.align(anchor=5, an=5) == dest_anchor_5_an_5


def test_scale():
    # Test no scaling
    original = Shape("m 10 10 l 20 10 20 20 10 20")
    assert original.scale(fscx=100, fscy=100) == original

    # Test horizontal scaling only
    rect = Shape("m 0 0 l 10 0 10 10 0 10")
    scaled_x = rect.scale(fscx=200, fscy=100)
    expected_x = Shape("m 0 0 l 20 0 20 10 0 10")
    assert scaled_x == expected_x

    # Test vertical scaling only
    rect = Shape("m 0 0 l 10 0 10 10 0 10")
    scaled_y = rect.scale(fscx=100, fscy=200)
    expected_y = Shape("m 0 0 l 10 0 10 20 0 20")
    assert scaled_y == expected_y

    # Test both horizontal and vertical scaling
    rect = Shape("m 0 0 l 10 0 10 10 0 10")
    scaled_both = rect.scale(fscx=150, fscy=200)
    expected_both = Shape("m 0 0 l 15 0 15 20 0 20")
    assert scaled_both == expected_both

    # Test scaling down
    rect = Shape("m 0 0 l 20 0 20 20 0 20")
    scaled_down = rect.scale(fscx=50, fscy=25)
    expected_down = Shape("m 0 0 l 10 0 10 5 0 5")
    assert scaled_down == expected_down

    # Test scaling with negative coordinates
    shape = Shape("m -10 -10 l 10 -10 10 10 -10 10")
    scaled_neg = shape.scale(fscx=200, fscy=50)
    expected_neg = Shape("m -20 -5 l 20 -5 20 5 -20 5")
    assert scaled_neg == expected_neg

    # Test method chaining
    original = Shape("m 0 0 l 10 0 10 10 0 10")
    chained = original.scale(fscx=200, fscy=100).move(5, 5)
    expected_chained = Shape("m 5 5 l 25 5 25 15 5 15")
    assert chained == expected_chained

    # Test with bezier curves
    bezier = Shape("m 0 0 b 10 0 10 10 0 10")
    scaled_bezier = bezier.scale(fscx=200, fscy=150)
    expected_bezier = Shape("m 0 0 b 20 0 20 15 0 15")
    assert scaled_bezier == expected_bezier


def test_flatten():
    original = Shape(FLATTEN_CIRCLE_ORIGINAL)
    dest = Shape(FLATTEN_CIRCLE_DEST)
    assert original.flatten() == dest

    original = Shape(FLATTEN_RECT_ORIGINAL)
    dest = Shape(FLATTEN_RECT_DEST)
    assert original.flatten() == dest

    # Difficult cases
    original = Shape(FLATTEN_COMPLEX1_ORIGINAL)
    dest = Shape(FLATTEN_COMPLEX1_DEST)
    assert original.flatten() == dest

    original = Shape(FLATTEN_COMPLEX2_ORIGINAL)
    dest = Shape(FLATTEN_COMPLEX2_DEST)
    assert original.flatten() == dest


def test_split():
    # distance between consecutive 'l' should be ≤10
    s = Shape("m 0 0 l 100 0")
    parts = s.split(max_len=10)
    pts = [e.coordinates[0] for e in parts if e.command == "l"]
    for p1, p2 in zip(pts, pts[1:]):
        assert ((p2.x - p1.x) ** 2 + (p2.y - p1.y) ** 2) ** 0.5 <= 10

        # Complex shape with curves (flatten+split)
        original = Shape(TEST_SPLIT_COMPLEX1_ORIGINAL)
    dest = Shape(TEST_SPLIT_COMPLEX1_DEST)
    assert original.split() == dest


def test_rotate():
    """Test the rotate method (Z-axis / frz rotation)."""
    # Rectangle 10x10 whose bottom-left corner is at the origin
    original = Shape("m 0 0 l 10 0 10 10 0 10")

    # 90° clockwise rotation around the origin (\frz=90)
    dest_90 = Shape("m 0 0 l 0 -10 10 -10 10 0")
    assert copy(original).rotate(frz=90) == dest_90

    # 180° rotation should flip both axes
    dest_180 = Shape("m 0 0 l -10 -0 -10 -10 0 -10")
    assert copy(original).rotate(frz=180) == dest_180

    # 90° rotation around X axis collapses Y coordinate to 0
    dest_frx = Shape("m 0 0 l 10 0 10 0 0 0")
    assert copy(original).rotate(frx=90) == dest_frx

    # 90° rotation around Y axis collapses X coordinate to 0 (use a vertical rectangle for clarity)
    vert = Shape("m 10 0 l 10 10 10 20 10 30")
    dest_fry = Shape("m 0 0 l 0 10 0 20 0 30")
    assert copy(vert).rotate(fry=90) == dest_fry

    # -90° (counter-clockwise) rotation around Z axis
    dest_ccw = Shape("m 0 0 l 0 10 -10 10 -10 0")
    assert copy(original).rotate(frz=-90) == dest_ccw

    # 90° rotation around the centre (5,5) keeps rectangle within first quadrant but rotated
    dest_origin = Shape("m 0 10 l 0 0 10 0 10 10")
    assert copy(original).rotate(frz=90, origin=(5, 5)) == dest_origin


def test_shear():
    """Test the shear method (fax / fay)."""
    rect = Shape("m 0 0 l 10 0 10 10 0 10")

    # Horizontal shear (fax)
    dest_fax = Shape("m 0 0 l 10 0 20 10 10 10")
    assert copy(rect).shear(fax=1) == dest_fax

    # Vertical shear (fay)
    dest_fay = Shape("m 0 0 l 10 10 10 20 0 10")
    assert copy(rect).shear(fay=1) == dest_fay

    # Combined shear (fax and fay)
    dest_both = Shape("m 0 0 l 10 10 20 20 10 10")
    assert copy(rect).shear(fax=1, fay=1) == dest_both


def test_boolean_basic_areas():
    """Union / intersection / difference / xor should have expected areas."""

    s1 = Shape.polygon(4, 10)  # spans [0,10]×[0,10]
    s2 = Shape.polygon(4, 10).move(5, 0)  # spans [5,15]×[0,10] → overlap is 5×10

    union = s1.boolean(s2, "union")
    inter = s1.boolean(s2, "intersection")
    diff = s1.boolean(s2, "difference")
    xor = s1.boolean(s2, "xor")

    assert math.isclose(union.to_multipolygon().area, 150, abs_tol=1e-6)
    assert math.isclose(inter.to_multipolygon().area, 50, abs_tol=1e-6)
    assert math.isclose(diff.to_multipolygon().area, 50, abs_tol=1e-6)
    assert math.isclose(xor.to_multipolygon().area, 100, abs_tol=1e-6)


def test_boolean_invalid_input():
    s1 = Shape.polygon(4, 10)  # spans [0,10]×[0,10]
    s2 = Shape.polygon(4, 10).move(5, 0)  # spans [5,15]×[0,10] → overlap is 5×10

    with pytest.raises(ValueError):
        s1.boolean(s2, "foo")  # type: ignore[arg-type]

    with pytest.raises(TypeError):
        s1.boolean("not a shape", "union")  # type: ignore[arg-type]
