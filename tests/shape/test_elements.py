import pytest
from shapely import Point

from pyonfx.shape import Shape, ShapeElement


def test_iter():
    """Basic iteration over Shape elements."""
    # Test basic iteration with single commands
    shape = Shape("m 10 20")
    elements = list(shape)
    assert len(elements) == 1
    assert elements[0].command == "m"
    assert elements[0].coordinates == [Point(10.0, 20.0)]

    shape = Shape("n 30 40")
    elements = list(shape)
    assert len(elements) == 1
    assert elements[0].command == "n"
    assert elements[0].coordinates == [Point(30.0, 40.0)]

    shape = Shape("p 50 60")
    elements = list(shape)
    assert len(elements) == 1
    assert elements[0].command == "p"
    assert elements[0].coordinates == [Point(50.0, 60.0)]

    shape = Shape("c")
    elements = list(shape)
    assert len(elements) == 1
    assert elements[0].command == "c"
    assert elements[0].coordinates == []

    # Test line command with multiple points
    shape = Shape("l 10 20 30 40 50 60")
    elements = list(shape)
    assert len(elements) == 3
    assert elements[0].command == "l"
    assert elements[0].coordinates == [Point(10.0, 20.0)]
    assert elements[1].command == "l"
    assert elements[1].coordinates == [Point(30.0, 40.0)]
    assert elements[2].command == "l"
    assert elements[2].coordinates == [Point(50.0, 60.0)]

    # Test single bezier curve
    shape = Shape("b 10 20 30 40 50 60")
    elements = list(shape)
    assert len(elements) == 1
    assert elements[0].command == "b"
    assert elements[0].coordinates == [
        Point(10.0, 20.0),
        Point(30.0, 40.0),
        Point(50.0, 60.0),
    ]

    # Test multiple bezier curves (implicit continuation)
    shape = Shape("b 10 20 30 40 50 60 70 80 90 100 110 120")
    elements = list(shape)
    assert len(elements) == 2
    assert elements[0].command == "b"
    assert elements[0].coordinates == [
        Point(10.0, 20.0),
        Point(30.0, 40.0),
        Point(50.0, 60.0),
    ]
    assert elements[1].command == "b"
    assert elements[1].coordinates == [
        Point(70.0, 80.0),
        Point(90.0, 100.0),
        Point(110.0, 120.0),
    ]

    # Test spline command with minimum points
    shape = Shape("s 10 20 30 40 50 60")
    elements = list(shape)
    assert len(elements) == 1
    assert elements[0].command == "s"
    assert elements[0].coordinates == [
        Point(10.0, 20.0),
        Point(30.0, 40.0),
        Point(50.0, 60.0),
    ]

    # Test spline command with more points
    shape = Shape("s 10 20 30 40 50 60 70 80")
    elements = list(shape)
    assert len(elements) == 1
    assert elements[0].command == "s"
    assert elements[0].coordinates == [
        Point(10.0, 20.0),
        Point(30.0, 40.0),
        Point(50.0, 60.0),
        Point(70.0, 80.0),
    ]

    # Test complex shape with multiple commands
    shape = Shape("m 0 0 l 10 0 10 10 b 10 10 20 20 30 10 c")
    elements = list(shape)
    assert len(elements) == 5
    assert elements[0].command == "m"
    assert elements[0].coordinates == [Point(0.0, 0.0)]
    assert elements[1].command == "l"
    assert elements[1].coordinates == [Point(10.0, 0.0)]
    assert elements[2].command == "l"
    assert elements[2].coordinates == [Point(10.0, 10.0)]
    assert elements[3].command == "b"
    assert elements[3].coordinates == [
        Point(10.0, 10.0),
        Point(20.0, 20.0),
        Point(30.0, 10.0),
    ]
    assert elements[4].command == "c"  # This is a zero-argument command
    assert elements[4].coordinates == []

    # Test empty shape
    shape = Shape("")
    elements = list(shape)
    assert len(elements) == 0

    # Test whitespace-only shape
    shape = Shape("   ")
    elements = list(shape)
    assert len(elements) == 0

    # Test floating point coordinates
    shape = Shape("m 10.5 20.25")
    elements = list(shape)
    assert len(elements) == 1
    assert elements[0].command == "m"
    assert elements[0].coordinates == [Point(10.5, 20.25)]

    # Test negative coordinates
    shape = Shape("m -10 -20")
    elements = list(shape)
    assert len(elements) == 1
    assert elements[0].command == "m"
    assert elements[0].coordinates == [Point(-10.0, -20.0)]

    # Test mixed positive and negative coordinates
    shape = Shape("l -10.5 20 30.25 -40")
    elements = list(shape)
    assert len(elements) == 2
    assert elements[0].command == "l"
    assert elements[0].coordinates == [Point(-10.5, 20.0)]
    assert elements[1].command == "l"
    assert elements[1].coordinates == [Point(30.25, -40.0)]


def test_iter_error_handling():
    """Invalid drawing strings raise helpful errors."""
    with pytest.raises(ValueError, match="Unexpected command 'x'"):
        Shape("x 10 20")

    with pytest.raises(ValueError):
        Shape("m 10")  # odd args

    with pytest.raises(ValueError):
        Shape("l")

    with pytest.raises(ValueError):
        Shape("b 10 20")

    with pytest.raises(ValueError):
        Shape("s 10 20")

    with pytest.raises(ValueError):
        Shape("m abc def")

    with pytest.raises(ValueError):
        Shape("l 10 20 abc def")


def test_iter_roundtrip_with_from_elements():
    """Re-constructing via elements must keep geometry intact."""
    # Test simple shape
    original = Shape("m 10 20 l 30 40")
    elements = list(original)
    reconstructed = Shape(elements=elements)

    # Check that the shapes are functionally equivalent
    original_elements = list(original)
    reconstructed_elements = list(reconstructed)
    assert len(original_elements) == len(reconstructed_elements)
    for orig, recon in zip(original_elements, reconstructed_elements):
        assert orig.command == recon.command
        assert orig.coordinates == recon.coordinates

    # Test complex shape with multiple command types
    original = Shape("m 0 0 l 10 0 10 10 b 10 10 20 20 30 10 c")
    elements = list(original)
    reconstructed = Shape(elements=elements)

    original_elements = list(original)
    reconstructed_elements = list(reconstructed)
    assert len(original_elements) == len(reconstructed_elements)
    for orig, recon in zip(original_elements, reconstructed_elements):
        assert orig.command == recon.command
        assert orig.coordinates == recon.coordinates

    # Test bezier with implicit continuations
    original = Shape("b 10 20 30 40 50 60 70 80 90 100 110 120")
    elements = list(original)
    reconstructed = Shape(elements=elements)

    original_elements = list(original)
    reconstructed_elements = list(reconstructed)
    assert len(original_elements) == len(reconstructed_elements)
    for orig, recon in zip(original_elements, reconstructed_elements):
        assert orig.command == recon.command
        assert orig.coordinates == recon.coordinates


def test_shape_element_equality_and_repr():
    """Test ShapeElement equality and representation."""
    # Test equality
    elem1 = ShapeElement("m", [Point(10.0, 20.0)])
    elem2 = ShapeElement("m", [Point(10.0, 20.0)])
    elem3 = ShapeElement("l", [Point(10.0, 20.0)])
    elem4 = ShapeElement("m", [Point(30.0, 40.0)])

    assert elem1 == elem2
    assert elem1 != elem3  # Different command
    assert elem1 != elem4  # Different coordinates
    assert elem1 != "not a shape element"  # Different type

    # Test string representation
    elem = ShapeElement("m", [Point(10.0, 20.0)])
    expected_repr = "ShapeElement('m', [Point(10.0, 20.0)])"
    assert repr(elem) == expected_repr

    # Test with multiple coordinates
    elem = ShapeElement("l", [Point(10.0, 20.0), Point(30.0, 40.0)])
    expected_repr = "ShapeElement('l', [Point(10.0, 20.0), Point(30.0, 40.0)])"
    assert repr(elem) == expected_repr

    # Test with no coordinates
    elem = ShapeElement("c", [])
    expected_repr = "ShapeElement('c', [])"
    assert repr(elem) == expected_repr


def test_shape_element_validation():
    """Test ShapeElement validation."""
    for cmd in ["m", "n", "l", "p", "b", "s", "c"]:
        assert ShapeElement(cmd, []).command == cmd

    with pytest.raises(ValueError):
        ShapeElement("x", [])
