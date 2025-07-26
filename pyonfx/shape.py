# PyonFX: An easy way to create KFX (Karaoke Effects) and complex typesetting using the ASS format (Advanced Substation Alpha).
# Copyright (C) 2019-2025 Antonio Strippoli (CoffeeStraw/YellowFlash)
#                         and contributors (https://github.com/CoffeeStraw/PyonFX/graphs/contributors)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyonFX is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program. If not, see http://www.gnu.org/licenses/.

import functools
import math
from inspect import signature
from typing import Callable, Literal, NamedTuple, cast

import numpy as np
from pyquaternion import Quaternion
from scipy.optimize import linear_sum_assignment
from shapely.affinity import scale as affine_scale
from shapely.geometry import (
    JOIN_STYLE,
    LinearRing,
    LineString,
    MultiPoint,
    MultiPolygon,
    Point,
    Polygon,
)
from shapely.ops import unary_union


class ShapeElement:
    """Represents a single ASS drawing command and its associated coordinates.

    This class encapsulates a drawing command used in the ASS format and stores the related coordinates
    as `shapely.geometry.Point` objects. It validates the command against allowed values ("m", "n", "l", "p", "b", "s", "c")
    and provides utility methods for creating and representing these commands.

    Attributes:
        command: The drawing command (e.g., "m", "n", "l", "p", "b", "s", "c").
        coordinates: A list of `Point` objects representing the coordinate pairs.

    See Also:
        [`Shape`][pyonfx.shape.Shape]
    """

    command: str
    """The drawing command (one of "m", "n", "l", "p", "b", "s", "c")."""
    coordinates: list[Point]
    """List of `Point` objects representing the coordinate pairs for this command."""

    def __init__(self, command: str, coordinates: list[Point]):
        """Initialize a ShapeElement instance.

        Args:
            command: The ASS drawing command. Allowed values are "m", "n", "l", "p", "b", "s", "c".
            coordinates: A list of `Point` objects representing the coordinate pairs.
        """
        if command not in {"m", "n", "l", "p", "b", "s", "c"}:
            raise ValueError(f"Invalid command '{command}'")
        self.command = command
        self.coordinates = coordinates

    def __repr__(self):
        coord_strs = [f"Point({c.x}, {c.y})" for c in self.coordinates]
        return f"ShapeElement('{self.command}', [{', '.join(coord_strs)}])"

    def __eq__(self, other):
        return (
            isinstance(other, ShapeElement)
            and self.command == other.command
            and self.coordinates == other.coordinates
        )

    @classmethod
    def from_ass_drawing_cmd(cls, command: str, *args: str) -> list["ShapeElement"]:
        """Parse an ASS drawing command into one or more ShapeElement instances.

        Since some commands can be implicit, this method can return more than one element.

        Args:
            command: The ASS drawing command. Must be one of "m", "n", "l", "p", "b", "s", "c".
            *args: A sequence of string arguments representing numeric values for coordinates.

        Returns:
            list[ShapeElement]: A list of ShapeElement instances created from the command.

        Notes:
            - Command 'c' does not accept any arguments.
            - Command 'l' returns one element for each encountered coordinate.
            - Command 'b' groups coordinates into sets of three.
        """
        if len(args) % 2 != 0:
            raise ValueError(
                f"Every ASS drawing command requires an even number of arguments (got {len(args)})"
            )

        try:
            coords = [
                Point(float(args[i]), float(args[i + 1]))
                for i in range(0, len(args), 2)
            ]
        except ValueError:
            raise ValueError(
                f"Invalid arguments (expected floats) for command '{command}': {args}"
            )

        match command:
            case "c":
                if len(args) != 0:
                    raise ValueError(f"Command 'c' does not take any arguments")
                return [cls(command, [])]

            case "m" | "n" | "p":
                if len(coords) != 1:
                    raise ValueError(
                        f"Command '{command}' requires exactly 1 coordinate pair"
                    )
                return [cls(command, coords)]

            case "s":
                if len(coords) < 3:
                    raise ValueError(
                        f"Command 's' requires at least 3 coordinate pairs"
                    )
                return [cls(command, coords)]

            case "l":
                if not coords:
                    raise ValueError("Command 'l' requires at least 1 coordinate pair")
                return [cls(command, [c]) for c in coords]

            case "b":
                if len(coords) % 3 != 0 or not coords:
                    raise ValueError(
                        "Command 'b' requires a number of coordinate pairs multiple of 3"
                    )

                return [
                    cls(command, coords[i : i + 3]) for i in range(0, len(coords), 3)
                ]

            case _:
                raise ValueError(f"Unexpected command '{command}'")


class Shape:
    """High-level container for ASS drawing commands.

    This class represents a vector outline for ASS subtitles, storing its geometry as a sequence of [`ShapeElement`][pyonfx.shape.ShapeElement] objects.
    It dynamically generates an ASS drawing command string from its internal elements, ensuring consistency between the geometry and its textual representation.
    The `Shape` class provides numerous methods for geometric transformations (e.g., move, scale, rotate, shear), analysis (e.g., bounding box computation), boolean operations, and morphing.

    Attributes:
        elements: List of drawing command elements representing the shape outline.
        drawing_cmds: The dynamically generated ASS drawing command string derived from `elements`.

    Examples:
        >>> shape = Shape("m 0 0 l 10 0 10 10")
        >>> shape.move(5, 5)
        'm 5 5 l 15 5 15 15'
        >>> for element in shape:
        ...     print(element)

    Notes:
        Transformations typically return a new `Shape` instance to allow method chaining.

    See Also:
        [`ShapeElement`][pyonfx.shape.ShapeElement]
    """

    elements: list[ShapeElement]
    """The shape's elements as a list of :class:`ShapeElement` objects."""

    def __init__(self, drawing_cmds: str = "", elements: list[ShapeElement] = []):
        # Assure that drawing_cmds is a string
        if drawing_cmds and elements:
            raise ValueError("Cannot pass both drawing_cmds and elements.")
        if drawing_cmds:
            self.elements = Shape._cmds_to_elements(drawing_cmds)
        else:
            self.elements = elements

    def __repr__(self):
        # We return drawing commands as a string rapresentation of the object
        return self.drawing_cmds

    def __eq__(self, other: "Shape"):
        return type(other) is type(self) and self.drawing_cmds == other.drawing_cmds

    def __iter__(self):
        return iter(self.elements)

    @property
    def drawing_cmds(self) -> str:
        """The shape's drawing commands in ASS format as a string."""
        return Shape._elements_to_cmds(self.elements)

    @staticmethod
    def _cmds_to_elements(drawing_cmds: str) -> list[ShapeElement]:
        """Parses the drawing commands string and updates the internal list of ShapeElement objects."""
        cmds_and_points = drawing_cmds.split()
        if not cmds_and_points:
            return []

        elements = []
        all_commands = {"m", "n", "l", "p", "b", "s", "c"}

        i = 0
        while i < len(cmds_and_points):
            command = cmds_and_points[i]
            if command not in all_commands:
                raise ValueError(f"Unexpected command '{command}'")

            i += 1
            start_args = i
            while i < len(cmds_and_points) and cmds_and_points[i] not in all_commands:
                i += 1

            args = cmds_and_points[start_args:i]

            for element in ShapeElement.from_ass_drawing_cmd(command, *args):
                elements.append(element)

        return elements

    @staticmethod
    def _elements_to_cmds(elements: list[ShapeElement]) -> str:
        """Create a Shape string from a list of ShapeElement objects."""
        if not elements:
            return "m 0 0"

        parts = []
        prev_command = None

        for element in elements:
            if element.command in {"c"}:
                # Commands with no coordinates
                parts.append(element.command)
                prev_command = element.command
            else:
                # Commands with coordinates
                coord_strs = []
                for p in element.coordinates:
                    coord_strs.extend(
                        [Shape.format_value(p.x), Shape.format_value(p.y)]
                    )

                # Check if we can use implicit command (for consecutive "l" or "b" commands)
                if (
                    element.command in {"l", "b"}
                    and element.command == prev_command
                    and coord_strs
                ):
                    parts.append(" ".join(coord_strs))
                else:
                    parts.append(f"{element.command} {' '.join(coord_strs)}")

                prev_command = element.command

        return " ".join(parts)

    @staticmethod
    def format_value(x: float, prec: int = 3) -> str:
        # Utility function to properly format values for shapes also returning them as a string
        result = f"{x:.{prec}f}".rstrip("0").rstrip(".")
        return "0" if result == "-0" else result

    def to_multipolygon(self, tolerance: float = 1.0) -> MultiPolygon:
        """Convert the shape to a Shapely MultiPolygon.

        It processes the shape into individual closed loops that are then assembled into polygons with proper shell-hole relationships.
        It automatically calls [`flatten`][pyonfx.shape.Shape.flatten] to convert curves into straight line segments.

        Args:
            tolerance: The tolerance angle in degrees used to determine when a bezier curve is considered flat. Higher values yield lower accuracy but faster processing.

        Returns:
            MultiPolygon: A MultiPolygon where each polygon consists of an outer shell (and optional holes) representing distinct contours of the shape.

        Examples:
            >>> shape = Shape("m 0 0 l 10 0 10 10 l 0 10 c")
            >>> mp = shape.to_multipolygon(tolerance=1.0)
        """
        # Work on a copy to avoid modifying the original shape
        shape_copy = Shape(self.drawing_cmds)

        # 1. Ensure the outline is fully linear by flattening Béziers.
        shape_copy.flatten(tolerance)

        # 2. Extract individual closed loops (contours).
        loops: list[list[Point]] = []
        current_loop: list[Point] = []

        for element in shape_copy:
            cmd = element.command
            if cmd == "m":
                if current_loop:
                    loops.append(current_loop)
                current_loop = [element.coordinates[0]]
            elif cmd in {"l", "n"}:
                current_loop.append(element.coordinates[0])

        if current_loop:
            loops.append(current_loop)

        # 3. Convert loops to Shapely polygons (without holes yet).
        loop_polys: list[Polygon] = []
        for pts in loops:
            if len(pts) < 3:
                # Degenerate loop – ignore.
                continue
            loop_polys.append(Polygon(pts))

        if not loop_polys:
            return MultiPolygon([])

        # 4. Sort by descending area magnitude so that larger shells are processed first.
        loop_polys.sort(key=lambda p: abs(p.area), reverse=True)

        shells: list[Polygon] = []
        holes_map: dict[Polygon, set[Polygon]] = {}

        for loop_poly in loop_polys:
            # Try to place the loop as a hole inside an existing shell.
            for shell in shells:
                if shell.contains(loop_poly):
                    holes_map[shell].add(loop_poly)
                    break
            else:
                # It's a new outer shell.
                shells.append(loop_poly)
                holes_map[loop_poly] = set()

        # 5. Build compound polygons with their holes.
        compounds: list[Polygon] = []
        for shell in shells:
            holes = holes_map[shell]
            if holes:
                compound = Polygon(shell.exterior, [h.exterior for h in holes])
            else:
                compound = shell
            compounds.append(compound)

        return MultiPolygon(compounds)

    @classmethod
    def from_multipolygon(
        cls, multipolygon: MultiPolygon, min_point_spacing: float = 0.5
    ) -> "Shape":
        """Create a Shape instance from a Shapely MultiPolygon.

        Args:
            multipolygon: The Shapely MultiPolygon geometry to convert.
            min_point_spacing: Per-axis spacing threshold - a vertex is kept only if both `|Δx|` and `|Δy|` from the previous vertex are ≥ this value (increasing it will boost performance during reproduction, but lower accuracy).

        Returns:
            Shape: A new Shape instance representing the geometry of the provided MultiPolygon.

        Examples:
            >>> from shapely.geometry import MultiPolygon, Polygon
            >>> mp = MultiPolygon([Polygon([(0,0), (10,0), (10,10), (0,10)])])
            >>> shape = Shape.from_multipolygon(mp, min_point_spacing=0.5)

        See Also:
            [`to_multipolygon`][pyonfx.shape.Shape.to_multipolygon]
        """
        if not isinstance(multipolygon, MultiPolygon):
            raise TypeError("Expected a MultiPolygon instance")

        elements: list[ShapeElement] = []

        def _linear_ring_to_elements(linear_ring: LinearRing, is_hole: bool = False):
            nonlocal elements

            coords = list(linear_ring.coords)
            if not coords:
                return

            # Remove duplicate closing point if present
            if len(coords) > 1 and coords[0] == coords[-1]:
                coords.pop()

            # Normalize orientation (outer = CW, inner = CCW)
            if is_hole and not linear_ring.is_ccw:
                coords = coords[::-1]
            elif not is_hole and linear_ring.is_ccw:
                coords = coords[::-1]

            # Consecutive "m" commands are overriden, drop last one
            if elements and elements[-1].command == "m":
                elements.pop()

            first_point = last_point = coords[0]
            elements.append(ShapeElement("m", [Point(first_point[0], first_point[1])]))
            if len(coords) > 1:
                for x, y in coords[1:]:
                    if (
                        abs(last_point[0] - x) >= min_point_spacing
                        or abs(last_point[1] - y) >= min_point_spacing
                    ):
                        elements.append(ShapeElement("l", [Point(x, y)]))
                        last_point = (x, y)

        for polygon in multipolygon.geoms:
            if not isinstance(polygon, Polygon) or polygon.is_empty:
                continue
            _linear_ring_to_elements(polygon.exterior, is_hole=False)
            for interior in polygon.interiors:
                _linear_ring_to_elements(interior, is_hole=True)

        # Ending with "m" command is not VSFilter compatible, drop it
        if elements and elements[-1].command == "m":
            elements.pop()

        return cls(elements=elements)

    def bounding(self, exact: bool = False) -> tuple[float, float, float, float]:
        """Calculate the bounding box of the shape.

        Args:
            exact: If True, perform an exact calculation by considering curve details; if False, use a faster approximation (libass).

        Returns:
            tuple[float, float, float, float]: A tuple (x_min, y_min, x_max, y_max) representing the bounding coordinates of the shape.

        Examples:
            >>> shape = Shape("m 10 5 l 25 5 25 42 10 42")
            >>> shape.bounding()
            (10.0, 5.0, 25.0, 42.0)  # left, top, right, bottom
        """
        all_points = [coord for element in self for coord in element.coordinates]

        if not exact:
            return MultiPoint(all_points).bounds

        def _cubic_bezier_bounds(
            p0: Point,
            p1: Point,
            p2: Point,
            p3: Point,
        ) -> tuple[float, float, float, float]:
            """Axis-aligned bounds of a cubic Bézier curve.

            Implementation adapted from https://stackoverflow.com/a/14429749
            taking care of degenerate cases (coincident control points).
            """

            def _axis_bounds(c0, c1, c2, c3):
                # Solve derivative 3*at^2 + 2*bt + c for roots in (0,1)
                a = -3 * c0 + 9 * c1 - 9 * c2 + 3 * c3
                b = 6 * c0 - 12 * c1 + 6 * c2
                c = 3 * (c1 - c0)

                ts: list[float] = []

                if abs(a) < 1e-12:  # Quadratic (or linear) case
                    if abs(b) > 1e-12:
                        t = -c / b
                        if 0 < t < 1:
                            ts.append(t)
                else:  # Cubic case
                    disc = b * b - 4 * a * c
                    if disc >= 0:
                        sqrt_disc = math.sqrt(disc)
                        for sign in (1, -1):
                            t = (-b + sign * sqrt_disc) / (2 * a)
                            if 0 < t < 1:
                                ts.append(t)

                # extrema candidates are the end-points and the roots above
                vals = [c0, c3]
                for t in ts:
                    mt = 1 - t
                    vals.append(
                        mt * mt * mt * c0
                        + 3 * mt * mt * t * c1
                        + 3 * mt * t * t * c2
                        + t * t * t * c3
                    )

                return min(vals), max(vals)

            xmin, xmax = _axis_bounds(p0.x, p1.x, p2.x, p3.x)
            ymin, ymax = _axis_bounds(p0.y, p1.y, p2.y, p3.y)
            return xmin, ymin, xmax, ymax

        x_min, y_min = math.inf, math.inf
        x_max, y_max = -math.inf, -math.inf

        def _update(pt: Point):
            nonlocal x_min, y_min, x_max, y_max
            x_min = min(x_min, pt.x)
            y_min = min(y_min, pt.y)
            x_max = max(x_max, pt.x)
            y_max = max(y_max, pt.y)

        prev_element: ShapeElement | None = None

        for element in self:
            match element.command:
                case "m" | "n":
                    prev_element = element
                case "l":
                    if prev_element is not None and prev_element.command in {"m", "n"}:
                        _update(prev_element.coordinates[-1])
                    for c in element.coordinates:
                        _update(c)
                    prev_element = element
                case "b":
                    if prev_element is None:
                        raise ValueError(
                            "Bezier command found without an initial point."
                        )
                    bx_min, by_min, bx_max, by_max = _cubic_bezier_bounds(
                        prev_element.coordinates[-1], *element.coordinates
                    )
                    _update(Point(bx_min, by_min))
                    _update(Point(bx_max, by_max))
                    prev_element = element
                case "c":
                    pass
                case _:
                    raise NotImplementedError(
                        f"Drawing command '{element.command}' not handled by bounding()."
                    )

        if math.inf in (x_min, y_min) or -math.inf in (x_max, y_max):
            raise ValueError("Invalid or empty shape - could not determine bounds.")

        return x_min, y_min, x_max, y_max

    def boolean(
        self,
        other: "Shape",
        op: Literal["union", "intersection", "difference", "xor"],
        *,
        tolerance: float = 1.0,
        min_point_spacing: float = 0.5,
    ) -> "Shape":
        """Perform a boolean operation between two shapes.

        This method converts both shapes to Shapely MultiPolygon objects (flattening any Bézier curves with the provided tolerance)
        and performs the specified boolean operation (union, intersection, difference, or symmetric difference).
        The result is converted back into a Shape instance.

        Args:
            other: The other shape to combine with this shape.
            op: The boolean operation to perform. Use "union" for combined area, "intersection" for overlapping area, "difference" for subtraction, or "xor" for symmetric difference.
            tolerance: The tolerance angle in degrees used for flattening curves. Higher tolerance reduces processing time but lowers accuracy.
            min_point_spacing: The minimum spacing between consecutive points when converting back from polygons to a shape.

        Returns:
            Shape: A new Shape instance representing the resulting shape after the boolean operation.

        Examples:
            >>> shape1 = Shape("m 0 0 l 10 0 10 10 0 10")
            >>> shape2 = Shape("m 5 5 l 15 5 15 15 5 15")
            >>> shape1.boolean(shape2, op="intersection", tolerance=1.0, min_point_spacing=0.5)
            m 10 10 l 10 5 5 5 5 10

        See Also:
            [`to_multipolygon`][pyonfx.shape.Shape.to_multipolygon]
            [`from_multipolygon`][pyonfx.shape.Shape.from_multipolygon]
        """
        if not isinstance(other, Shape):
            raise TypeError("other must be a Shape instance")

        if op not in {"union", "intersection", "difference", "xor"}:
            raise ValueError(
                "op must be one of 'union', 'intersection', 'difference', or 'xor'"
            )

        # Convert both shapes to MultiPolygon (this flattens curves).
        mp_self = self.to_multipolygon(tolerance)
        mp_other = other.to_multipolygon(tolerance)

        # Perform the requested boolean operation.
        if op == "union":
            result_geom = mp_self.union(mp_other)
        elif op == "intersection":
            result_geom = mp_self.intersection(mp_other)
        elif op == "difference":
            result_geom = mp_self.difference(mp_other)
        else:  # op == "xor"
            result_geom = mp_self.symmetric_difference(mp_other)

        # Normalise to MultiPolygon
        if isinstance(result_geom, Polygon):
            result_geom = MultiPolygon([result_geom])
        elif not isinstance(result_geom, MultiPolygon):
            # No overlapping geometry – return an empty shape.
            return Shape()

        # Convert back to Shape.
        return Shape.from_multipolygon(result_geom, min_point_spacing)

    def map(
        self,
        fun: (
            Callable[[float, float], tuple[float, float]]
            | Callable[[float, float, str], tuple[float, float]]
        ),
    ) -> "Shape":
        """Sends every point of the shape through a transformation function.

        This method applies a user-provided transformation function to each coordinate of the shape's elements, allowing for arbitrary deformations or adjustments.
        The function can accept two parameters (x and y) or three parameters (x, y, and the command type), providing flexibility in the transformation logic.

        Args:
            fun: A function that takes the x and y coordinates (and optionally the drawing command as the third argument) and returns a tuple with the transformed (x, y) coordinates.

        Returns:
            Shape: A new Shape instance with each point transformed according to the provided function.

        Examples:
            >>> original = Shape("m 0 0 l 20 0 20 10 0 10")
            >>> original.map(lambda x, y: (x + 10, y + 5))
            m 10 5 l 30 5 30 15 10 15
        """
        if not callable(fun):
            raise TypeError("(Lambda) function expected")

        # Determine the arity of the transformation function
        n_params = len(signature(fun).parameters)
        if n_params not in (2, 3):
            raise ValueError("Function must have 2 or 3 parameters")

        # Create a wrapper function accepting always 3 parameters
        if n_params == 3:
            fun = cast(Callable[[float, float, str], tuple[float, float]], fun)
            _apply = lambda px, py, cmd: fun(px, py, cmd)
        else:
            fun = cast(Callable[[float, float], tuple[float, float]], fun)
            _apply = lambda px, py, _: fun(px, py)

        # Apply the transformation to each element
        transformed_elements: list[ShapeElement] = []
        for element in self:
            if not element.coordinates:
                transformed_elements.append(element)
                continue

            transformed_coords = [
                Point(*_apply(p.x, p.y, element.command)) for p in element.coordinates
            ]
            transformed_elements.append(
                ShapeElement(element.command, transformed_coords)
            )

        return Shape(elements=transformed_elements)

    def move(self, x: float, y: float) -> "Shape":
        """Move the shape by the specified x and y offsets.

        This method translates every point in the shape by adding the given x and y offsets to the corresponding coordinates.

        Args:
            x: The displacement along the x-axis.
            y: The displacement along the y-axis.

        Returns:
            Shape: A new Shape instance with the coordinates moved by the specified offsets.

        Examples:
            >>> shape = Shape("m 0 0 l 30 0 30 20 0 20")
            >>> shape.move(-5, 10)
            m -5 10 l 25 10 25 30 -5 30
        """
        if x == 0 and y == 0:
            return self

        return self.map(lambda cx, cy: (cx + x, cy + y))

    def align(self, an: int = 5, anchor: int | None = None) -> "Shape":
        """Align the shape based on a specified alignment code and pivot.

        This method adjusts the shape's position so that a chosen pivot inside the shape
        coincides with the position used for rendering (i.e., the \\pos point in ASS).

        Args:
            an: The alignment of the subtitle line (e.g., 1 through 9 corresponding to positions such as bottom-left, center, top-right, etc.).
            anchor: The pivot inside the shape to be used for alignment. If not provided, defaults to the value of 'an'.

        Returns:
            Shape: A new Shape instance with the shape aligned according to the specified parameters.

        Examples:
            >>> shape = Shape("m 10 10 l 30 10 30 20 10 20")
            >>> shape.align()
            m 0 0 l 20 0 20 10 0 10
        """
        if anchor is None:
            anchor = an

        if an < 1 or an > 9:
            raise ValueError("Alignment value must be an integer between 1 and 9")

        if anchor < 1 or anchor > 9:
            raise ValueError("Anchor value must be an integer between 1 and 9")

        # Keypad decomposition (0: left / bottom, 1: centre, 2: right / top)
        pivot_row, pivot_col = divmod(anchor - 1, 3)
        line_row, line_col = divmod(an - 1, 3)

        # Bounding boxes (exact vs. libass)
        left, top, right, bottom = self.bounding(exact=True)
        l_left, l_top, l_right, l_bottom = self.bounding(exact=False)

        width, height = right - left, bottom - top

        x_move = -left
        y_move = -top

        # Centre according to line alignment (libass corrections included)
        if line_col == 0:  # left
            x_move -= width / 2
        elif line_col == 1:  # centre
            x_move -= width / 2 - (l_right - l_left) / 2
        elif line_col == 2:  # right
            x_move += width / 2 - (width - (l_right - l_left))

        if line_row == 0:  # bottom
            y_move += height / 2 - (height - (l_bottom - l_top))
        elif line_row == 1:  # middle
            y_move -= height / 2 - (l_bottom - l_top) / 2
        elif line_row == 2:  # top
            y_move -= height / 2

        # Finally shift so that requested pivot is the reference point
        if pivot_col == 0:  # left
            x_move += width / 2
        elif pivot_col == 2:  # right
            x_move -= width / 2

        if pivot_row == 0:  # bottom
            y_move -= height / 2
        elif pivot_row == 2:  # top
            y_move += height / 2

        return self.move(x_move, y_move)

    def scale(
        self,
        fscx: float = 100,
        fscy: float = 100,
        origin: tuple[float, float] = (0.0, 0.0),
    ) -> "Shape":
        """Scale the shape by specified horizontal and vertical scale factors, optionally around a given origin.

        This method scales the shape's coordinates relative to a specified origin point, which serves as the pivot for the scaling transformation.

        Args:
            fscx: The horizontal scaling factor as a percentage (100 means no change).
            fscy: The vertical scaling factor as a percentage (100 means no change).
            origin: The pivot point (x, y) around which scaling is performed. Default is (0.0, 0.0).

        Returns:
            Shape: A new Shape instance with the coordinates scaled accordingly.

        Examples:
            >>> shape = Shape("m 0 50 l 0 0 50 0 50 50")
            >>> shape.scale(fscx=200)
            m 0 50 l 0 0 100 0 100 50
        """
        if fscx == 100.0 and fscy == 100.0:
            return self

        scale_x = fscx / 100.0
        scale_y = fscy / 100.0

        ox, oy = origin

        return self.map(lambda x, y: ((x - ox) * scale_x + ox, (y - oy) * scale_y + oy))

    def rotate(
        self,
        *,
        frx: float = 0.0,
        fry: float = 0.0,
        frz: float = 0.0,
        origin: tuple[float, float] = (0.0, 0.0),
    ) -> "Shape":
        """Rotate the shape by specified angles about given axes around a pivot point.

        This method applies rotation transformations to the shape's coordinates based on the provided angles for the x, y, and z axes, in degrees.
        The pivot point around which the rotation is applied is specified by the 'origin' parameter.

        Args:
            frx: The rotation angle around the x-axis (in degrees).
            fry: The rotation angle around the y-axis (in degrees).
            frz: The rotation angle around the z-axis (in degrees).
            origin: The pivot point (x, y) for the rotation.

        Returns:
            Shape: A new Shape instance with the coordinates rotated as specified.

        Examples:
            >>> shape = Shape("m 0 0 l 30 0 30 20 0 20")
            >>> shape.rotate(frx=0, fry=0, frz=45, origin=(15,10))
            m -2.678 13.536 l 18.536 -7.678 32.678 6.464 11.464 27.678

        Notes:
            The rotation is applied in the order: X-axis, then Y-axis, then Z-axis.
        """
        if frx == 0 and fry == 0 and frz == 0:
            return self

        # Normalise the origin
        ox, oy = origin

        # Pre-compute sines/cosines
        # (Mathematical convention is counter-clockwise, but ASS uses clockwise, *sigh*)
        rx = math.radians(-frx)
        ry = math.radians(-fry)
        rz = math.radians(-frz)
        cosx, sinx = math.cos(rx), math.sin(rx)
        cosy, siny = math.cos(ry), math.sin(ry)
        cosz, sinz = math.cos(rz), math.sin(rz)

        def _transform(px: float, py: float) -> tuple[float, float]:
            # Translate to origin
            x = px - ox
            y = py - oy
            z = 0.0

            # Rotation around X (pitch)
            y1 = y * cosx - z * sinx
            z1 = y * sinx + z * cosx
            x1 = x

            # Rotation around Y (yaw)
            x2 = x1 * cosy + z1 * siny
            z2 = -x1 * siny + z1 * cosy
            y2 = y1

            # Rotation around Z (roll)
            x3 = x2 * cosz - y2 * sinz
            y3 = x2 * sinz + y2 * cosz
            z3 = z2

            # Translate back
            return x3 + ox, y3 + oy

        # Apply transformation to every point in the shape
        return self.map(lambda x, y: _transform(x, y))

    def shear(
        self,
        *,
        fax: float = 0.0,
        fay: float = 0.0,
        origin: tuple[float, float] = (0.0, 0.0),
    ) -> "Shape":
        """Apply a shear transformation to the shape.

        This method deforms the shape by applying a shear transformation relative to a specified origin, which acts as the pivot.

        Args:
            fax: The horizontal shear factor. Positive values slant the top of the shape to the right, negative values slant to the left.
            fay: The vertical shear factor. Positive values slant the right side of the shape downward, negative values slant upward.
            origin: The pivot point (x, y) for the shear transformation.

        Returns:
            Shape: A new Shape instance with the coordinates sheared accordingly.

        Examples:
            >>> shape = Shape("m 0 0 l 30 0 30 20 0 20")
            >>> shape.shear(fax=0.5, fay=0, origin=(15,10))
            m -5 0 l 25 0 35 20 5 20
        """
        if fax == 0.0 and fay == 0.0:
            return self

        ox, oy = origin

        def _shear(px: float, py: float) -> tuple[float, float]:
            # Translate to origin
            x_rel = px - ox
            y_rel = py - oy

            # Apply shear matrix [[1, fax], [fay, 1]]
            new_x_rel = x_rel + fax * y_rel
            new_y_rel = fay * x_rel + y_rel

            # Translate back
            return new_x_rel + ox, new_y_rel + oy

        return self.map(lambda x, y: _shear(x, y))

    def flatten(self, tolerance: float = 1.0) -> "Shape":
        """Flatten the shape's Bézier curves into line segments.

        This method processes the shape by subdividing Bézier curves into multiple straight line segments.
        The subdivision is controlled by the tolerance parameter, which defines the threshold angle (in degrees) at which a curve is considered flat.
        This conversion is useful for operations that require linear segments, such as detailed transformations or morphing.

        Args:
            tolerance: The angle in degrees used to determine when a Bézier curve is flat enough to be approximated by a straight line. Higher values yield fewer segments and faster processing but lower accuracy.

        Returns:
            Shape: A new Shape instance with the curves converted into line segments.

        Notes:
            Flattening curves may significantly increase the number of points, which can impact performance for subsequent operations.
        """
        if tolerance < 0:
            raise ValueError("Tolerance must be a positive number")

        # Convert tolerance to radians once to avoid repeated conversions
        tolerance_rad = math.radians(tolerance)

        def _subdivide_bezier(p0x, p0y, p1x, p1y, p2x, p2y, p3x, p3y, t=0.5):
            """De Casteljau subdivision of cubic bezier curve using raw coordinates."""
            # First level
            q0x = p0x + t * (p1x - p0x)
            q0y = p0y + t * (p1y - p0y)
            q1x = p1x + t * (p2x - p1x)
            q1y = p1y + t * (p2y - p1y)
            q2x = p2x + t * (p3x - p2x)
            q2y = p2y + t * (p3y - p2y)

            # Second level
            r0x = q0x + t * (q1x - q0x)
            r0y = q0y + t * (q1y - q0y)
            r1x = q1x + t * (q2x - q1x)
            r1y = q1y + t * (q2y - q1y)

            # Final point
            sx = r0x + t * (r1x - r0x)
            sy = r0y + t * (r1y - r0y)

            return (
                (p0x, p0y, q0x, q0y, r0x, r0y, sx, sy),
                (sx, sy, r1x, r1y, q2x, q2y, p3x, p3y),
            )

        def _is_bezier_flat(p0x, p0y, p1x, p1y, p2x, p2y, p3x, p3y):
            """Check if bezier curve is flat enough based on angle tolerance."""
            points = [(p0x, p0y), (p1x, p1y), (p2x, p2y), (p3x, p3y)]

            vectors = []
            for i in range(1, len(points)):
                dx = points[i][0] - points[i - 1][0]
                dy = points[i][1] - points[i - 1][1]
                if dx != 0 or dy != 0:
                    vectors.append((dx, dy))

            if len(vectors) < 2:
                return True

            # Check angle between consecutive vectors
            for i in range(1, len(vectors)):
                v1, v2 = vectors[i - 1], vectors[i]

                angle = math.atan2(
                    v1[0] * v2[1] - v1[1] * v2[0], v1[0] * v2[0] + v1[1] * v2[1]
                )

                if abs(angle) > tolerance_rad:
                    return False

            return True

        def _bezier_to_lines(p0, p1, p2, p3):
            """Convert bezier curve to line segments."""
            stack = [(p0.x, p0.y, p1.x, p1.y, p2.x, p2.y, p3.x, p3.y)]

            line_points = []
            while stack:
                coords = stack.pop()

                if _is_bezier_flat(*coords):
                    # End point
                    line_points.append(Point(coords[6], coords[7]))
                else:
                    # Subdivide and add both halves to stack
                    left, right = _subdivide_bezier(*coords)
                    stack.append(right)  # Process right first (stack order)
                    stack.append(left)

            return (
                line_points[:-1] if line_points else []
            )  # Exclude last to avoid duplication

        # Process elements
        flattened_elements = []
        current_point = None

        for element in self:
            if element.command == "b":
                if current_point is None:
                    raise ValueError("Bezier curve found without a starting point")

                # Convert bezier to line segments
                p0 = current_point
                p1, p2, p3 = element.coordinates

                line_points = _bezier_to_lines(p0, p1, p2, p3)

                # Add line segments
                for point in line_points:
                    flattened_elements.append(ShapeElement("l", [point]))

                # Add final point
                flattened_elements.append(ShapeElement("l", [p3]))
                current_point = p3

            elif element.command == "c":
                # Bezier curves are already converted to lines
                pass

            else:
                # Keep other commands as-is and track current point
                flattened_elements.append(element)
                if element.coordinates:
                    current_point = element.coordinates[-1]

        # Return shape with flattened elements
        return Shape(elements=flattened_elements)

    def split(self, max_len: float = 16, tolerance: float = 1.0) -> "Shape":
        """Split the shape into smaller segments.

        This method first flattens any Bézier curves in the shape, then subdivides the resulting line segments so that no segment exceeds the specified maximum length.
        This process increases the number of points in the shape, which can be useful for detailed deformations or morphing.

        Args:
            max_len: The maximum allowed length for any line segment. Segments longer than this value will be subdivided.
            tolerance: The tolerance angle in degrees used to flatten Bézier curves before splitting.

        Returns:
            Shape: A new Shape instance with the split line segments.

        Examples:
            >>> shape = Shape("m 0 50 l 0 0 50 0 50 50")
            >>> shape.split()
            m 0 50 l 0 48 0 32 0 16 0 0 2 0 18 0 34 0 50 0 50 2 50 18 50 34 50 50 48 50 32 50 16 50 0 50
        """
        if max_len <= 0:
            raise ValueError(
                "The length of segments must be a positive and non-zero value"
            )

        def _split_line_segment(p1: Point, p2: Point) -> list[Point]:
            """Split a line segment *p1→p2* into shorter segments of length ``<= max_len``"""
            line = LineString([p1, p2])
            distance = line.length

            # If already short enough, just return the end point
            if distance <= max_len:
                return [Point(p2.x, p2.y)]

            # Split the line into segments of max_len, with possibly shorter first segment
            segments: list[Point] = []
            distance_rest = distance % max_len
            cur_distance = distance_rest if distance_rest > 0 else max_len

            while cur_distance <= distance:
                point = line.interpolate(cur_distance)
                segments.append(Point(point.x, point.y))
                cur_distance += max_len

            return segments

        def _close_contour_if_needed(current_pt, first_move_pt):
            """Helper to close a contour by splitting the closing line if needed."""
            if current_pt is None or first_move_pt is None:
                return []

            if (current_pt.x, current_pt.y) == (first_move_pt.x, first_move_pt.y):
                return []

            closing_points = _split_line_segment(current_pt, first_move_pt)
            return [ShapeElement("l", [pt]) for pt in closing_points]

        # First flatten the shape to convert bezier curves to lines
        flattened_shape = Shape(self.drawing_cmds).flatten(tolerance)

        # Process elements
        split_elements = []
        current_point = None
        first_move_point = None

        for element in flattened_shape:
            if element.command == "m":
                # Close previous contour if needed
                split_elements.extend(
                    _close_contour_if_needed(current_point, first_move_point)
                )

                # Start new contour
                split_elements.append(element)
                current_point = element.coordinates[0]
                first_move_point = current_point

            elif element.command == "l":
                if current_point is None:
                    raise ValueError("Line command found without a starting point")

                # Split the line segment
                line_points = _split_line_segment(current_point, element.coordinates[0])

                # Add each segment as a separate line element
                for point in line_points:
                    split_elements.append(ShapeElement("l", [point]))

                # Update current point
                current_point = (
                    line_points[-1] if line_points else element.coordinates[0]
                )

            elif element.command == "c":
                # Close current contour
                split_elements.extend(
                    _close_contour_if_needed(current_point, first_move_point)
                )

                # Reset state for next contour
                current_point = None
                first_move_point = None

            else:
                split_elements.append(element)
                if element.coordinates:
                    current_point = element.coordinates[-1]

        # Close the final contour if needed
        split_elements.extend(_close_contour_if_needed(current_point, first_move_point))

        # Update shape with split elements
        return Shape(elements=split_elements)

    def buffer(
        self,
        dist_xy: float,
        dist_y: float | None = None,
        *,
        kind: Literal["fill", "border"] = "border",
        join: Literal["round", "bevel", "mitre"] = "round",
    ) -> "Shape":
        """Return a buffered version of the shape.

        It makes a thicker or thinner version of the original shape by adding or removing space around it, based on the distances you specify.
        The "kind" option decides if you get the whole new shape filled in or just the edge line.

        Args:
            dist_xy: Horizontal buffer distance. Positive values expand the shape, and negative values contract it.
            dist_y: Vertical buffer distance. If None, the same value as dist_xy is used. The sign must match that of dist_xy.
            kind: Determines whether to return the filled buffered geometry ("fill") or just the border ("border").
            join: The corner join style to use on buffered corners.

        Returns:
            Shape: A new Shape instance representing the buffered shape.

        Examples:
            >>> shape = Shape("m 0 0 l 100 0 100 50 0 50")
            >>> shape.buffer(5, kind="border", join="round")
            m -3.333 50 l -3.269 50.65 (...)
        """
        if join not in ("round", "bevel", "mitre"):
            raise ValueError("join must be one of 'round', 'bevel', or 'mitre'")
        if kind not in ("fill", "border"):
            raise ValueError("kind must be either 'fill' or 'border'")
        if dist_y is None:
            dist_y = dist_xy
        if dist_xy == 0 and dist_y == 0:
            return Shape() if kind == "border" else self

        # Validate signs: both distances must have the same sign (or be zero)
        if dist_xy * dist_y < 0:
            raise ValueError("dist_xy and dist_y must have the same sign")
        sign = 1 if dist_xy >= 0 else -1

        # Build Shapely geometry
        multipoly = self.to_multipolygon()

        # Apply libass hack
        _LIBASS_HACK = 2 / 3
        dist_xy *= _LIBASS_HACK
        dist_y *= _LIBASS_HACK

        # Anisotropic scaling so that the buffer distance is uniform
        width = max(abs(dist_xy), abs(dist_y))

        _EPS = 1e-9  # Avoid division-by-zero
        xscale = abs(dist_xy) / width if abs(dist_xy) > 0 else _EPS
        yscale = abs(dist_y) / width if abs(dist_y) > 0 else _EPS

        inv_xscale = 1.0 / xscale
        inv_yscale = 1.0 / yscale
        scaled_geom = affine_scale(
            multipoly, xfact=inv_xscale, yfact=inv_yscale, origin=(0, 0)
        )

        # Apply buffer (positive ⇒ outward, negative ⇒ inward)
        buffered_scaled = scaled_geom.buffer(
            sign * width, join_style=getattr(JOIN_STYLE, join)
        )

        if kind == "fill":
            # Grown/shrunk geometry
            result_scaled = buffered_scaled
        else:
            if sign > 0:
                # External border: grow and subtract original
                result_scaled = buffered_scaled.difference(scaled_geom)
            else:
                # Internal border: shrink original and subtract new interior
                result_scaled = scaled_geom.difference(buffered_scaled)

        # Scale back to the original coordinate system
        result_geom = affine_scale(
            result_scaled, xfact=xscale, yfact=yscale, origin=(0, 0)
        )

        # Craft MultiPolygon
        if isinstance(result_geom, MultiPolygon):
            mp = result_geom
        elif isinstance(result_geom, Polygon):
            mp = MultiPolygon([result_geom])
        else:
            raise ValueError(f"Invalid stroke geometry type: {type(result_geom)}")

        # Convert back to Shape
        return Shape.from_multipolygon(mp)

    @functools.lru_cache(maxsize=1024)
    @staticmethod
    def _prepare_morph(
        source_ids_and_cmds: tuple[tuple[str, str], ...],
        target_ids_and_cmds: tuple[tuple[str, str], ...],
        max_len: float,
        tolerance: float,
        w_dist: float,
        w_area: float,
        w_overlap: float,
        cost_threshold: float,
        ensure_shell_pairs: bool = False,
    ) -> tuple[
        list[tuple[LinearRing, LinearRing, bool, str, str]],
        list[tuple[LinearRing, Point, bool, str]],
        list[tuple[LinearRing, Point, bool, str]],
    ]:
        """Prepare the morphing process by decomposing the shapes into compounds and pairing them.

        Returns:
            A tuple containing:
            - A list of (src, tgt, is_hole, src_id, tgt_id) ring pairs.
            - A list of (src, ref, is_hole, src_id) unmatched source rings.
            - A list of (tgt, ref, is_hole, tgt_id) unmatched target rings.
        """

        def _pair_rings(
            source_rings_meta: list[tuple[Polygon, bool, str]],
            target_rings_meta: list[tuple[Polygon, bool, str]],
            w_dist: float,
            w_area: float,
            w_overlap: float,
            cost_threshold: float,
            ensure_shell_pairs: bool,
        ) -> tuple[
            list[tuple[LinearRing, LinearRing, bool, str, str]],
            list[tuple[LinearRing, Point, bool, str]],
            list[tuple[LinearRing, Point, bool, str]],
        ]:
            """
            Pair source and target polygon rings (exteriors and interiors) based on centroid distance,
            area similarity, and overlap, avoiding shell-hole mismatches.

            Any ring left without a counterpart is matched to the closest centroid so that downstream
            morphing logic can decide whether it is *appearing* or *disappearing*.
            """
            matched: list[tuple[LinearRing, LinearRing, bool, str, str]] = []
            unmatched_src: list[tuple[LinearRing, Point, bool, str]] = []
            unmatched_tgt: list[tuple[LinearRing, Point, bool, str]] = []

            # Global centroid arrays (used for nearest-neighbour fallback)
            all_src_centroids = np.array(
                [poly.centroid.coords[0] for poly, _, _ in source_rings_meta]
            )
            all_tgt_centroids = np.array(
                [poly.centroid.coords[0] for poly, _, _ in target_rings_meta]
            )

            # Match separately for shells (False) and holes (True)
            for is_hole in (False, True):
                cur_src = [
                    (poly, sid)
                    for poly, hole, sid in source_rings_meta
                    if hole == is_hole
                ]
                cur_tgt = [
                    (poly, sid)
                    for poly, hole, sid in target_rings_meta
                    if hole == is_hole
                ]
                n_src, n_tgt = len(cur_src), len(cur_tgt)

                if n_src == 0 and n_tgt == 0:
                    continue
                if n_src == 0:
                    for poly, did in cur_tgt:
                        ref = (
                            Point(all_src_centroids[0])
                            if all_src_centroids.size
                            else poly.centroid
                        )
                        unmatched_tgt.append((poly.exterior, ref, is_hole, did))
                    continue
                if n_tgt == 0:
                    for poly, sid in cur_src:
                        ref = (
                            Point(all_tgt_centroids[0])
                            if all_tgt_centroids.size
                            else poly.centroid
                        )
                        unmatched_src.append((poly.exterior, ref, is_hole, sid))
                    continue

                src_areas = np.array([p.area for p, _ in cur_src])
                tgt_areas = np.array([p.area for p, _ in cur_tgt])
                src_centroids = np.array([p.centroid.coords[0] for p, _ in cur_src])
                tgt_centroids = np.array([p.centroid.coords[0] for p, _ in cur_tgt])

                # 1) Centroid distance (normalised)
                diff = src_centroids[:, None, :] - tgt_centroids[None, :, :]
                dist = np.linalg.norm(diff, axis=2)
                size_norm = np.sqrt(np.maximum(src_areas[:, None], tgt_areas[None, :]))
                centroid_term = dist / (size_norm + 1e-8)

                # 2) Relative area difference
                area_term = np.abs(src_areas[:, None] - tgt_areas[None, :]) / (
                    np.maximum(src_areas[:, None], tgt_areas[None, :]) + 1e-8
                )

                costs = w_dist * centroid_term + w_area * area_term

                # 3) Add overlap term for top 8 promising pairs only
                k = min(8, n_tgt)
                candidate_cols = np.argpartition(costs, kth=k - 1, axis=1)[:, :k]

                for i, cols in enumerate(candidate_cols):
                    poly_i = cur_src[i][0]
                    area_i = src_areas[i]
                    for j in cols:
                        poly_j = cur_tgt[j][0]
                        inter_area = 0.0
                        if poly_i.intersects(poly_j):
                            inter_area = poly_i.intersection(poly_j).area
                        min_area = min(area_i, tgt_areas[j])
                        if min_area:
                            iou_term = 1.0 - (inter_area / min_area)
                            costs[i, j] += w_overlap * iou_term

                # 4) Solve assignment (Hungarian algorithm)
                row_ind, col_ind = linear_sum_assignment(costs)

                used_src: set[int] = set()
                used_tgt: set[int] = set()

                for i, j in zip(row_ind, col_ind):
                    if cost_threshold is None or costs[i, j] <= cost_threshold:
                        matched.append(
                            (
                                cur_src[i][0].exterior,
                                cur_tgt[j][0].exterior,
                                is_hole,
                                cur_src[i][1],
                                cur_tgt[j][1],
                            )
                        )
                        used_src.add(i)
                        used_tgt.add(j)

                # 5) Handle still-unmatched rings.
                unmatched_src_idx = set(range(n_src)) - used_src
                unmatched_tgt_idx = set(range(n_tgt)) - used_tgt

                # Optionally force-pair shells so that they always morph into something.
                if ensure_shell_pairs and not is_hole and n_src > 0 and n_tgt > 0:
                    # Pair every remaining source shell with its minimum-cost target shell
                    for i in unmatched_src_idx:
                        j = int(np.argmin(costs[i]))
                        matched.append(
                            (
                                cur_src[i][0].exterior,
                                cur_tgt[j][0].exterior,
                                is_hole,
                                cur_src[i][1],
                                cur_tgt[j][1],
                            )
                        )
                        used_src.add(i)
                    for j in unmatched_tgt_idx:
                        i = int(np.argmin(costs[:, j]))
                        matched.append(
                            (
                                cur_src[i][0].exterior,
                                cur_tgt[j][0].exterior,
                                is_hole,
                                cur_src[i][1],
                                cur_tgt[j][1],
                            )
                        )
                        used_tgt.add(j)

                # Any ring still left unmatched will be matched to the closest centroid.
                un_src_idx = set(range(n_src)) - used_src
                un_tgt_idx = set(range(n_tgt)) - used_tgt

                for idx in un_src_idx:
                    poly, source_id = cur_src[idx]
                    src_cent = src_centroids[idx]
                    nn = np.argmin(np.linalg.norm(all_tgt_centroids - src_cent, axis=1))
                    unmatched_src.append(
                        (
                            poly.exterior,
                            Point(all_tgt_centroids[nn]),
                            is_hole,
                            source_id,
                        )
                    )
                for idx in un_tgt_idx:
                    poly, target_id = cur_tgt[idx]
                    tgt_cent = tgt_centroids[idx]
                    nn = np.argmin(np.linalg.norm(all_src_centroids - tgt_cent, axis=1))
                    unmatched_tgt.append(
                        (
                            poly.exterior,
                            Point(all_src_centroids[nn]),
                            is_hole,
                            target_id,
                        )
                    )

            return matched, unmatched_src, unmatched_tgt

        def _resample_loop(loop: LinearRing, n_points: int) -> LinearRing:
            """Return *loop* resampled to *n_points* evenly spaced vertices along its perimeter, while preserving all the original loop points if *preserve_original_points* is True."""

            if n_points < 3:
                raise ValueError("n_points must be at least 3 for a valid LinearRing.")

            # Ensure the loop is closed and get coordinates
            coords = np.asarray(loop.coords)
            if not np.allclose(coords[0], coords[-1]):
                raise ValueError("Input LinearRing must be closed.")
            coords = coords[:-1]  # remove duplicate endpoint

            if n_points < len(coords):
                raise ValueError(
                    "n_points must be >= number of original vertices when preserve_original_points=True."
                )
            if n_points == len(coords):
                return loop

            extra = n_points - len(coords)

            # Compute segment lengths and cumulative lengths
            deltas = np.diff(coords, axis=0, append=[coords[0]])
            segment_lengths = np.linalg.norm(deltas, axis=1)
            total_length = segment_lengths.sum()

            # Ideal (floating point) allocation of extra vertices per segment
            ideal_alloc = segment_lengths / total_length * extra

            # Initial integer allocation (floor) and compute how many vertices are still unassigned
            int_alloc = np.floor(ideal_alloc).astype(int)
            allocated = int_alloc.sum()
            remaining = extra - allocated

            # Distribute the remaining vertices to the segments with the largest fractional parts
            if remaining > 0:
                frac_parts = ideal_alloc - int_alloc
                # Indices of segments sorted by descending fractional part
                order = np.argsort(-frac_parts)
                for idx in order[:remaining]:
                    int_alloc[idx] += 1

            # Build the new coordinate list
            new_coords = []
            for i, start_pt in enumerate(coords):
                end_pt = coords[(i + 1) % len(coords)]
                new_coords.append(tuple(start_pt))  # always keep the original vertex
                k = int_alloc[i]
                if k == 0:
                    continue
                # Insert *k* equally spaced points *strictly inside* the segment
                for j in range(1, k + 1):
                    ratio = j / (k + 1)
                    interp_pt = start_pt + ratio * (end_pt - start_pt)
                    new_coords.append(tuple(interp_pt))

            new_coords.append(new_coords[0])  # close the ring
            return LinearRing(new_coords)

        # --- Execute the pipeline ---
        # 1) Flatten and split each shape into short lines to have more points to work with,
        #    then convert to polygons and extract rings.
        source_rings_meta: list[tuple[Polygon, bool, str]] = []
        target_rings_meta: list[tuple[Polygon, bool, str]] = []

        for source_id, source_cmds in source_ids_and_cmds:
            shape_mp = Shape(source_cmds).split(max_len, tolerance).to_multipolygon()
            for poly in shape_mp.geoms:
                source_rings_meta.append((Polygon(poly.exterior), False, source_id))
                source_rings_meta.extend(
                    (Polygon(inter), True, source_id) for inter in poly.interiors
                )

        for target_id, target_cmds in target_ids_and_cmds:
            shape_mp = Shape(target_cmds).split(max_len, tolerance).to_multipolygon()
            for poly in shape_mp.geoms:
                target_rings_meta.append((Polygon(poly.exterior), False, target_id))
                target_rings_meta.extend(
                    (Polygon(inter), True, target_id) for inter in poly.interiors
                )

        # 2) Pair individual rings extracted from those compounds
        matched, unmatched_src, unmatched_tgt = _pair_rings(
            source_rings_meta,
            target_rings_meta,
            w_dist,
            w_area,
            w_overlap,
            cost_threshold,
            ensure_shell_pairs,
        )

        # 3) Resample each paired ring so that both have the same vertex count
        resampled: list[tuple[LinearRing, LinearRing, bool, str, str]] = []
        for src_r, tgt_r, is_hole, source_id, target_id in matched:
            n_src = len(src_r.coords) - 1
            n_tgt = len(tgt_r.coords) - 1
            n_pts = max(n_src, n_tgt, 4)
            resampled.append(
                (
                    _resample_loop(src_r, n_pts),
                    _resample_loop(tgt_r, n_pts),
                    is_hole,
                    source_id,
                    target_id,
                )
            )

        return resampled, unmatched_src, unmatched_tgt

    def morph(
        self,
        target: "Shape",
        t: float,
        max_len: float = 16.0,
        tolerance: float = 1.0,
        min_point_spacing: float = 0.5,
        w_dist: float = 0.55,
        w_area: float = 0.35,
        w_overlap: float = 0.1,
        cost_threshold: float = 2.5,
        ensure_shell_pairs: bool = True,
    ) -> "Shape":
        """Interpolate the current shape toward a target shape.

        This method computes an intermediate shape by morphing the current shape into a target shape based on an interpolation factor t (where 0 corresponds to the source shape and 1 corresponds to the target shape).
        The morph is performed by decomposing both shapes into closed ring segments and matching corresponding rings based on spatial properties. Matched rings are linearly interpolated, and unmatched rings are processed to appear or disappear gradually.

        Args:
            target: The target shape to morph into.
            t: Interpolation factor between 0 and 1, where 0 returns the original shape and 1 returns the target shape.
            max_len: The maximum allowed length for any line segment when splitting curves before morphing.
            tolerance: The tolerance angle in degrees used when flattening curves.
            min_point_spacing: Per-axis spacing threshold - a vertex is kept only if both `|Δx|` and `|Δy|` from the previous vertex are ≥ this value (increasing it will boost performance during reproduction, but lower accuracy).
            w_dist: Weight for the centroid-distance term (higher values make proximity more important).
            w_area: Weight for the relative area-difference term (higher values make size similarity more important).
            w_overlap: Weight for the overlap / IoU term that penalises pairs with little spatial intersection.
            cost_threshold: Maximum acceptable cost for a pairing. Pairs whose cost is above this threshold are treated as unmatched and will grow/shrink to the closest centroid.
            ensure_shell_pairs: If `True`, shell rings that would otherwise remain unmatched will be force-paired with the shell that yields the minimum cost. This guarantees that every visible contour morphs into something, at the price of allowing the same shell to be reused multiple times.

        Returns:
            Shape: A new Shape instance representing the intermediate morph state.

        Examples:
            >>> source = Shape("m 0 0 l 100 0 100 100 0 100 c")
            >>> target = Shape("m 50 50 l 150 50 150 150 50 150 c")
            >>> morph = source.morph(target, t=0.5)
        """

        # Fast-path validations
        if not isinstance(target, Shape):
            raise TypeError("Target must be a Shape instance")
        if not 0 <= t <= 1:
            raise ValueError("t must be between 0 and 1")
        if t == 0:
            return self
        if t == 1:
            return target

        # Use the multi-shape morphing routine to get intermediate geometries.
        morphs = Shape.morph_multi(
            {"_": self},
            {"_": target},
            t,
            max_len=max_len,
            tolerance=tolerance,
            min_point_spacing=min_point_spacing,
            w_dist=w_dist,
            w_area=w_area,
            w_overlap=w_overlap,
            cost_threshold=cost_threshold,
            ensure_shell_pairs=ensure_shell_pairs,
        )

        shapes = list(morphs.values())
        combined_shape = shapes[0]
        for shape in shapes[1:]:
            combined_shape = combined_shape.boolean(
                shape,
                op="union",
                tolerance=tolerance,
                min_point_spacing=min_point_spacing,
            )

        return combined_shape

    @staticmethod
    def morph_multi(
        src_shapes: dict[str, "Shape"],
        tgt_shapes: dict[str, "Shape"],
        t: float,
        *,
        max_len: float = 16.0,
        tolerance: float = 1.0,
        min_point_spacing: float = 0.5,
        w_dist: float = 0.55,
        w_area: float = 0.35,
        w_overlap: float = 0.1,
        cost_threshold: float = 2.5,
        ensure_shell_pairs: bool = True,
    ) -> dict[tuple[str | None, str | None], "Shape"]:
        """Interpolate multiple shapes simultaneously.

        This class method performs a multi-shape morphing operation by interpolating between collections of source and target shapes.
        It decomposes each shape into rings, matches corresponding rings across the source and target collections based on spatial relationships, and computes intermediate shapes at a given interpolation factor t.
        The output is a dictionary mapping source-target identifier tuples to the resulting interpolated Shape.

        Args:
            src_shapes: A dictionary mapping source shape identifiers to their corresponding Shape instances.
            tgt_shapes: A dictionary mapping target shape identifiers to their corresponding Shape instances.
            t: Interpolation factor between 0 and 1. A value of 0 returns the source shapes and 1 returns the target shapes.
            max_len: Maximum allowed length for any line segment after splitting curves.
            tolerance: The tolerance angle in degrees used when flattening curves.
            min_point_spacing: Per-axis spacing threshold - a vertex is kept only if both `|Δx|` and `|Δy|` from the previous vertex are ≥ this value (increasing it will boost performance during reproduction, but lower accuracy).
            w_dist: Weight for the centroid-distance term (higher values make proximity more important).
            w_area: Weight for the relative area-difference term (higher values make size similarity more important).
            w_overlap: Weight for the overlap / IoU term that penalises pairs with little spatial intersection.
            cost_threshold: Maximum acceptable cost for a pairing. Pairs whose cost is above this threshold are treated as unmatched and will grow/shrink to the closest centroid.
            ensure_shell_pairs: If `True`, shell rings that would otherwise remain unmatched will be force-paired with the shell that yields the minimum cost. This guarantees that every visible contour morphs into something, at the price of allowing the same shell to be reused multiple times.

        Returns:
            dict[tuple[str | None, str | None], Shape]: A dictionary mapping tuples of source and target identifiers to the corresponding interpolated Shape. A source identifier of None indicates an appearing shape, while a target identifier of None indicates a disappearing shape.

        Examples:
            >>> src = { 'A': Shape.star(5, 20, 40), 'B': Shape.ellipse(50, 30).move(100, 0) }
            >>> tgt = { 'X': Shape.polygon(6, 45) }
            >>> morphs = Shape.morph_multi(src, tgt, t=0.5)
            >>> for (src_id, tgt_id), shape in morphs.items():
            ...     print(f"{src_id} -> {tgt_id}: {shape}")
        """
        # Basic validation
        if not 0 <= t <= 1:
            raise ValueError("t must be between 0 and 1")
        if any(not isinstance(s, Shape) for s in src_shapes.values()):
            raise TypeError("All src_shapes values must be Shape instances")
        if any(not isinstance(s, Shape) for s in tgt_shapes.values()):
            raise TypeError("All tgt_shapes values must be Shape instances")

        # Fast-paths
        if t == 0:
            return {(k, None): v for k, v in src_shapes.items()}
        if t == 1:
            return {(None, k): v for k, v in tgt_shapes.items()}

        def _morph_transition(
            ring: LinearRing,
            ref_pt: Point,
            t: float,
            appearing: bool,
        ) -> LinearRing:
            """Morphism helper shared by *appearing* and *disappearing* rings."""
            if (t == 0 and not appearing) or (t == 1 and appearing):
                return ring

            coords = np.asarray(ring.coords[:-1], dtype=float)

            if appearing:
                # Grow *ring* from *ref_pt*
                origin = np.array([ref_pt.x, ref_pt.y])
                new_coords = origin + (coords - origin) * t
            else:
                # Shrink *ring* towards *ref_pt*
                centroid = np.array(ring.centroid.coords[0])
                dest = np.array([ref_pt.x, ref_pt.y])
                new_coords = (
                    centroid + (coords - centroid) * (1 - t) + (dest - centroid) * t
                )

            new_coords = np.vstack([new_coords, new_coords[0]])  # close ring
            return LinearRing(new_coords)

        def _interpolate_rings(
            src_ring: LinearRing, tgt_ring: LinearRing, t: float
        ) -> LinearRing:
            """Linear interpolation between two rings with optimal vertex correspondence."""
            if t == 0:
                return src_ring
            if t == 1:
                return tgt_ring
            if len(src_ring.coords) != len(tgt_ring.coords):
                raise ValueError(
                    "Rings must have the same number of vertices: "
                    f"{len(src_ring.coords)} != {len(tgt_ring.coords)}"
                )

            src_coords = np.asarray(src_ring.coords[:-1], dtype=float)
            tgt_coords = np.asarray(tgt_ring.coords[:-1], dtype=float)

            # Ensure orientation consistency
            if src_ring.is_ccw != tgt_ring.is_ccw:
                tgt_coords = tgt_coords[::-1]

            # Find optimal alignment by minimizing total vertex distances
            n_vertices = len(src_coords)
            min_total_distance = float("inf")
            best_shift = 0

            # Try all possible rotations and find the one with minimum total distance
            for shift in range(n_vertices):
                shifted_tgt = np.roll(tgt_coords, -shift, axis=0)
                total_distance = np.sum(
                    np.linalg.norm(src_coords - shifted_tgt, axis=1)
                )

                if total_distance < min_total_distance:
                    min_total_distance = total_distance
                    best_shift = shift

            # Apply the best alignment
            if best_shift > 0:
                tgt_coords = np.roll(tgt_coords, -best_shift, axis=0)

            # Perform linear interpolation between corresponding vertices
            interp_coords = (1 - t) * src_coords + t * tgt_coords

            # Close the ring
            interp_coords = np.vstack([interp_coords, interp_coords[0]])
            return LinearRing(interp_coords)

        def _rings_to_multipolygon(
            rings: list[tuple[LinearRing, bool]],
        ) -> MultiPolygon:
            """Convert a collection of `(ring, is_hole)` tuples to a `MultiPolygon`."""

            # Gather polygons (shells and holes)
            shell_polys: list[Polygon] = []
            hole_polys: list[Polygon] = []

            for lr, is_hole in rings:
                poly = Polygon(lr).buffer(0)
                if poly.is_empty or not poly.is_valid:
                    continue
                (hole_polys if is_hole else shell_polys).append(poly)

            # Union the shells and holes
            shell_union = unary_union(shell_polys) if shell_polys else None
            hole_union = unary_union(hole_polys) if hole_polys else None

            # Subtract the holes from the shells (if any)
            if shell_union and hole_union:
                combined = shell_union.difference(hole_union)
            elif shell_union:
                combined = shell_union
            elif hole_union:
                combined = hole_union
            else:
                return MultiPolygon()

            if isinstance(combined, MultiPolygon):
                return combined
            elif isinstance(combined, Polygon):
                return MultiPolygon([combined])
            else:
                raise ValueError("Combined geometry is not a Polygon or MultiPolygon")

        # 1) Retrieve pairing & resampling information (cached)
        src_cmds = tuple(sorted((k, s.drawing_cmds) for k, s in src_shapes.items()))
        dst_cmds = tuple(sorted((k, s.drawing_cmds) for k, s in tgt_shapes.items()))

        paired, src_unmatched, tgt_unmatched = Shape._prepare_morph(
            src_cmds,
            dst_cmds,
            max_len,
            tolerance,
            w_dist,
            w_area,
            w_overlap,
            cost_threshold,
            ensure_shell_pairs,
        )

        # 2) Interpolate matched rings
        result_rings: list[tuple[LinearRing, bool, str | None, str | None]] = [
            (_interpolate_rings(src, tgt, t), is_hole, src_id, tgt_id)
            for src, tgt, is_hole, src_id, tgt_id in paired
        ]

        # 3) Handle disappearing / appearing rings
        for ring, dest_pt, is_hole, src_id in src_unmatched:
            result_rings.append(
                (
                    _morph_transition(ring, dest_pt, t, appearing=False),
                    is_hole,
                    src_id,
                    None,
                )
            )
        for ring, origin_pt, is_hole, tgt_id in tgt_unmatched:
            result_rings.append(
                (
                    _morph_transition(ring, origin_pt, t, appearing=True),
                    is_hole,
                    None,
                    tgt_id,
                )
            )

        # 4) Group by (shape_id, target_id)
        #    Holes coming from / going to *None* (i.e. appearing/disappearing) must be
        #    subtracted from *every* shape – they are collected in `global_holes` and
        #    later injected into every flow.

        global_holes: list[tuple[LinearRing, bool]] = []  # always [(ring, True)]
        flows: dict[tuple[str | None, str | None], list[tuple[LinearRing, bool]]] = {}

        for ring, is_hole, src_id, tgt_id in result_rings:
            # If the ring is a hole and one side of the morph is missing, treat it as
            # a *global* hole that has to be removed from every resulting geometry.
            if is_hole and (src_id is None or tgt_id is None):
                global_holes.append((ring, True))
                continue

            flows.setdefault((src_id, tgt_id), []).append((ring, is_hole))

        # Inject global holes into every shape flow so they are diffed out.
        if global_holes:
            for ring_list in flows.values():
                ring_list.extend(global_holes)

        # 5) Convert back to Shape and return as dictionary
        result: dict[tuple[str | None, str | None], Shape] = {}
        for (src_id, tgt_id), ring_list in flows.items():
            mp = _rings_to_multipolygon(ring_list)
            result[(src_id, tgt_id)] = Shape.from_multipolygon(mp, min_point_spacing)
        return result

    PIXEL: str = "m 0 1 l 0 0 1 0 1 1"
    """A string representing a pixel."""

    @classmethod
    def triangle(cls, width: float, height: float) -> "Shape":
        """Creates a triangle centered at the origin with the specified width and height.

        The triangle is defined by three vertices:
        - Top vertex at (0, height/2).
        - Bottom-left vertex at (-width/2, -height/2).
        - Bottom-right vertex at (width/2, -height/2).

        Args:
            width: The width of the triangle base (must be positive).
            height: The height of the triangle (must be positive).

        Returns:
            Shape: A new Shape instance representing the triangle.
        """
        if width <= 0 or height <= 0:
            raise ValueError("Width and height must be positive")

        # Calculate vertices
        half_w = width / 2
        half_h = height / 2
        vertices = [
            (0, half_h),  # Top vertex
            (-half_w, -half_h),  # Bottom-left vertex
            (half_w, -half_h),  # Bottom-right vertex
        ]

        # Build ASS path command
        f = cls.format_value
        path_parts = [f"m {f(vertices[0][0])} {f(vertices[0][1])}"]

        for vertex in vertices[1:]:
            path_parts.append(f"l {f(vertex[0])} {f(vertex[1])}")

        return cls(" ".join(path_parts)).align()

    @classmethod
    def rectangle(cls, width: float, height: float) -> "Shape":
        """Creates a rectangle shape with the specified width and height.

        Args:
            width: The width of the rectangle (must be positive).
            height: The height of the rectangle (must be positive).

        Returns:
            Shape: A new Shape instance representing the rectangle.
        """
        if width <= 0 or height <= 0:
            raise ValueError("Width and height must be positive")

        f = cls.format_value
        return cls(
            "m 0 0 l %s 0 %s %s 0 %s 0 0" % (f(width), f(width), f(height), f(height))
        )

    @classmethod
    def square(cls, size: float) -> "Shape":
        """Creates a square shape with the given side length.

        Args:
            size: The side length of the square (must be positive).

        Returns:
            Shape: A new Shape instance representing the square.
        """
        return cls.rectangle(size, size)

    @classmethod
    def rounded_rectangle(cls, width: float, height: float, radius: float) -> "Shape":
        """Creates a rounded rectangle shape.

        Args:
            width: Rectangle width in pixels (must be positive).
            height: Rectangle height in pixels (must be positive).
            radius: Corner radius in pixels (must be <= min(width/2, height/2)).

        Returns:
            Shape: A rounded rectangle with origin at top-left (0,0), extending to (width, height).
        """
        if width <= 0 or height <= 0:
            raise ValueError("Width and height must be positive")
        if radius < 0:
            raise ValueError("Radius must be non-negative")
        if radius > min(width / 2, height / 2):
            raise ValueError("Radius is too large for the given dimensions")

        f = cls.format_value
        k = 0.5522847498 * radius  # Bezier approximation constant
        w, h, r = width, height, radius

        # Each tuple: (line_end_x, line_end_y, bezier_c1x, c1y, c2x, c2y, end_x, end_y)
        segments = [
            (w - r, 0, w - r + k, 0, w, k, w, r),  # Top edge + top-right corner
            (
                w,
                h - r,
                w,
                h - r + k,
                w - k,
                h,
                w - r,
                h,
            ),  # Right edge + bottom-right corner
            (r, h, r - k, h, 0, h - k, 0, h - r),  # Bottom edge + bottom-left corner
            (0, r, 0, r - k, k, 0, r, 0),  # Left edge + top-left corner
        ]

        cmd = [f"m {f(r)} {f(0)}"]
        for lx, ly, c1x, c1y, c2x, c2y, ex, ey in segments:
            cmd.extend(
                [
                    f"l {f(lx)} {f(ly)}",
                    f"b {f(c1x)} {f(c1y)} {f(c2x)} {f(c2y)} {f(ex)} {f(ey)}",
                ]
            )

        return cls(" ".join(cmd))

    @classmethod
    def polygon(cls, edges: int, side_length: float) -> "Shape":
        """Creates a regular n-sided polygon shape.

        Args:
            edges: Number of sides for the polygon (must be at least 3).
            side_length: The length of each side (must be positive).

        Returns:
            Shape: A Shape object representing the polygon.
        """
        if edges < 3:
            raise ValueError("Edges must be ≥ 3")
        if side_length <= 0:
            raise ValueError("Side length must be positive")

        # Calculate circumradius from side length
        radius = side_length / (2 * math.sin(math.pi / edges))

        f = cls.format_value
        pts = []
        # Rotate to get a more natural orientation (flat bottom when possible)
        angle_offset = math.pi / 2 + math.pi / edges

        for i in range(edges):
            angle = 2 * math.pi * i / edges + angle_offset
            x = radius * math.cos(angle)
            y = radius * math.sin(angle)
            pts.append((f(x), f(y)))

        cmd_parts = [f"m {pts[0][0]} {pts[0][1]} l"]
        cmd_parts.extend(f"{x} {y}" for x, y in pts[1:])
        return cls(" ".join(cmd_parts)).align()

    @classmethod
    def ellipse(cls, w: float, h: float) -> "Shape":
        """Creates an ellipse shape centered at the origin.

        Args:
            w: The width of the ellipse.
            h: The height of the ellipse.

        Returns:
            Shape: A Shape object representing the ellipse.
        """
        try:
            w2, h2 = w / 2, h / 2
        except TypeError:
            raise TypeError("Number(s) expected")

        f = cls.format_value

        return cls(
            "m 0 %s "
            "b 0 %s 0 0 %s 0 "
            "%s 0 %s 0 %s %s "
            "%s %s %s %s %s %s "
            "%s %s 0 %s 0 %s"
            % (
                f(h2),  # move
                f(h2),
                f(w2),  # curve 1
                f(w2),
                f(w),
                f(w),
                f(h2),  # curve 2
                f(w),
                f(h2),
                f(w),
                f(h),
                f(w2),
                f(h),  # curve 3
                f(w2),
                f(h),
                f(h),
                f(h2),  # curve 4
            )
        )

    @classmethod
    def circle(cls, radius: float) -> "Shape":
        """Creates a circle shape with the given radius.

        Args:
            radius: The radius of the circle (must be positive).

        Returns:
            Shape: A new Shape instance representing the circle.
        """
        return cls.ellipse(2 * radius, 2 * radius)

    @classmethod
    def ring(cls, out_r: float, in_r: float) -> "Shape":
        """Creates a ring shape with specified inner and outer radii centered at the origin.

        Args:
            out_r: The outer radius of the ring.
            in_r: The inner radius of the ring (must be less than out_r).

        Returns:
            Shape: A Shape object representing the ring.
        """
        try:
            out_r2, in_r2 = out_r * 2, in_r * 2
            off = out_r - in_r
            off_in_r = off + in_r
            off_in_r2 = off + in_r2
        except TypeError:
            raise TypeError("Number(s) expected")

        if in_r >= out_r:
            raise ValueError(
                "Valid number expected. Inner radius must be less than outer radius"
            )

        f = cls.format_value
        return cls(
            "m 0 %s "
            "b 0 %s 0 0 %s 0 "
            "%s 0 %s 0 %s %s "
            "%s %s %s %s %s %s "
            "%s %s 0 %s 0 %s "
            "m %s %s "
            "b %s %s %s %s %s %s "
            "%s %s %s %s %s %s "
            "%s %s %s %s %s %s "
            "%s %s %s %s %s %s"
            % (
                f(out_r),  # outer move
                f(out_r),
                f(out_r),  # outer curve 1
                f(out_r),
                f(out_r2),
                f(out_r2),
                f(out_r),  # outer curve 2
                f(out_r2),
                f(out_r),
                f(out_r2),
                f(out_r2),
                f(out_r),
                f(out_r2),  # outer curve 3
                f(out_r),
                f(out_r2),
                f(out_r2),
                f(out_r),  # outer curve 4
                f(off),
                f(off_in_r),  # inner move
                f(off),
                f(off_in_r),
                f(off),
                f(off_in_r2),
                f(off_in_r),
                f(off_in_r2),  # inner curve 1
                f(off_in_r),
                f(off_in_r2),
                f(off_in_r2),
                f(off_in_r2),
                f(off_in_r2),
                f(off_in_r),  # inner curve 2
                f(off_in_r2),
                f(off_in_r),
                f(off_in_r2),
                f(off),
                f(off_in_r),
                f(off),  # inner curve 3
                f(off_in_r),
                f(off),
                f(off),
                f(off),
                f(off),
                f(off_in_r),  # inner curve 4
            )
        )

    @classmethod
    def heart(cls, size: float, offset: float = 0) -> "Shape":
        """Creates a heart shape with specified dimensions and vertical offset.

        Args:
            size: The width and height of the heart.
            offset: The vertical offset for the heart's center point (default is 0).

        Returns:
            Shape: A Shape object representing the heart.
        """
        try:
            mult = 100 * size / 30
        except TypeError:
            raise TypeError("Size parameter must be a number")
        # Build shape from template
        shape = cls(
            "m 15 30 b 27 22 30 18 30 14 30 8 22 0 15 10 8 0 0 8 0 14 0 18 3 22 15 30"
        ).scale(mult)

        # Shift mid point of heart vertically
        count = 0

        def shift_mid_point(x, y):
            nonlocal count
            count += 1

            if count == 7:
                try:
                    return x, y + offset
                except TypeError:
                    raise TypeError("Offset parameter must be a number")
            return x, y

        # Return result
        return shape.map(shift_mid_point)

    @classmethod
    def _glance_or_star(
        cls, edges: int, inner_size: float, outer_size: float, g_or_s: str
    ) -> "Shape":
        """Generates a shape for a star or glance based on provided parameters.

        Args:
            edges: The number of edges in the shape.
            inner_size: The size used for the inner vertex or control points.
            outer_size: The size used for the outer vertex.
            g_or_s: Flag to determine the style ('l' for star with lines, 'b' for glance with curves).

        Returns:
            Shape: A Shape object representing the generated star or glance.
        """
        # Alias for utility functions
        f = cls.format_value

        def rotate_on_axis_z(point, theta):
            # Internal function to rotate a point around z axis by a given angle.
            theta = math.radians(theta)
            return Quaternion(axis=[0, 0, 1], angle=theta).rotate(point)

        # Building shape
        shape = [f"m 0 {-outer_size} {g_or_s}"]
        inner_p, outer_p = 0, 0

        for i in range(1, edges + 1):
            # Inner edge
            inner_p = rotate_on_axis_z([0, -inner_size, 0], ((i - 0.5) / edges) * 360)
            # Outer edge
            outer_p = rotate_on_axis_z([0, -outer_size, 0], (i / edges) * 360)
            # Add curve / line
            if g_or_s == "l":
                shape.append(
                    "%s %s %s %s"
                    % (f(inner_p[0]), f(inner_p[1]), f(outer_p[0]), f(outer_p[1]))
                )
            else:
                shape.append(
                    "%s %s %s %s %s %s"
                    % (
                        f(inner_p[0]),
                        f(inner_p[1]),
                        f(inner_p[0]),
                        f(inner_p[1]),
                        f(outer_p[0]),
                        f(outer_p[1]),
                    )
                )

        shape = cls(" ".join(shape))

        # Return result centered
        return shape.align()

    @classmethod
    def star(cls, edges: int, inner_size: float, outer_size: float) -> "Shape":
        """Creates a star shape centered at the origin.

        Args:
            edges: The number of edges for the star.
            inner_size: The distance from the center to the inner vertices.
            outer_size: The distance from the center to the outer vertices.

        Returns:
            Shape: A Shape object representing the star.
        """
        return cls._glance_or_star(edges, inner_size, outer_size, "l")

    @classmethod
    def glance(cls, edges: int, inner_size: float, outer_size: float) -> "Shape":
        """Creates a glance shape with curved transitions between edges.

        Args:
            edges: The number of edges for the glance.
            inner_size: The distance from the center to the inner control points.
            outer_size: The control point distance for the curves between outer edges.

        Returns:
            Shape: A Shape object representing the glance.
        """
        return cls._glance_or_star(edges, inner_size, outer_size, "b")
