# PyonFX: An easy way to create KFX (Karaoke Effects) and complex typesetting using the ASS format (Advanced Substation Alpha).
# Copyright (C) 2019 Antonio Strippoli (CoffeeStraw/YellowFlash)
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

from __future__ import annotations
import functools
import math
from typing import Callable, cast, Literal
from inspect import signature

import numpy as np
from pyquaternion import Quaternion
from shapely.geometry import (
    LinearRing,
    Point,
    MultiPoint,
    LineString,
    Polygon,
    MultiPolygon,
    JOIN_STYLE,
)
from shapely.ops import unary_union
from scipy.optimize import linear_sum_assignment
from shapely.affinity import scale as affine_scale


class ShapeElement:
    """Represents a single drawing command with its associated coordinates."""

    command: str
    """The drawing command (one of "m", "n", "l", "p", "b", "s", "c")."""
    coordinates: list[Point]
    """List of (x, y) coordinate pairs for this command."""

    def __init__(self, command: str, coordinates: list[Point]):
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
    def from_ass_drawing_cmd(cls, command: str, *args: str) -> list[ShapeElement]:
        """Parses a drawing command and its arguments from an ASS drawing string.

        Since some commands can be implicit, this method can return more than one element.

        Args:
            command (str): The drawing command (one of "m", "n", "l", "p", "b", "s", "c").
            *args (str): The arguments for the command.

        Returns:
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
    """High-level wrapper around ASS drawing commands.

    A :class:`Shape` instance stores and manipulates the vector outlines that you
    would normally place in a ``{\\p}`` override tag.

    Internally the outline is represented as a list of :class:`pyonfx.shape.ShapeElement` objects exposed through :py:attr:`elements`.
    The textual ASS representation returned by the read-only :py:attr:`drawing_cmds` property
    is generated *on-the-fly* from that list, so it can never fall out of sync with the actual geometry.

    The class provides a rich tool-set to work with shapes: bounding-box
    calculation, geometric transformations, curve flattening, segmentations and more.
    Most methods mutate the instance and return ``self`` so they can be *chained*.

    ``Shape`` also implements :py:meth:`__iter__`, therefore you can simply write::

        >>> for element in shape:
        >>>     ...

    The iterator yields the underlying :class:`ShapeElement` objects **in the
    same order** they appear in the ASS drawing string.  Every explicit command
    (``m``, ``n``, ``l``, ``p``, ``b``, ``s``, ``c``) is returned one-to-one.
    In addition, *implicit* continuations after a command - for example extra
    coordinate pairs that follow an ``l`` or ``b`` - are split so that each
    segment becomes its own :class:`ShapeElement`::

        >>> shape = Shape("m 0 0 l 10 0 10 10")
        >>> list(shape)
        [ShapeElement('m', [Point(0, 0)]),
         ShapeElement('l', [Point(10, 0)]),
         ShapeElement('l', [Point(10, 10)])]
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

    def __eq__(self, other: Shape):
        return type(other) is type(self) and self.drawing_cmds == other.drawing_cmds

    def __iter__(self):
        return iter(self.elements)

    @property
    def drawing_cmds(self) -> str:
        """The shape's drawing commands in ASS format as a string."""
        return Shape._elements_to_cmds(self.elements)

    @staticmethod
    def _cmds_to_elements(drawing_cmds: str) -> list[ShapeElement]:
        """
        Parses the drawing commands string and updates the internal list of ShapeElement objects.
        """
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
        """Converts shape to a Shapely MultiPolygon with proper shell-hole relationships.

        Polygons don't have curves, so :func:`Shape.flatten` is automatically called with the given tolerance.

        Parameters:
            tolerance (float): Angle in degree to define a curve as flat (increasing it will boost performance during reproduction, but lower accuracy)

        Returns:
            A MultiPolygon where each polygon represents a compound with outer shell and holes.
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
    ) -> Shape:
        """Creates a Shape from a Shapely MultiPolygon.

        Parameters:
            multipolygon (MultiPolygon): The MultiPolygon to convert.
            min_point_spacing (float): Per-axis spacing threshold - a vertex is kept only if both `|Δx|` and `|Δy|` from the previous vertex are ≥ this value (increasing it will boost performance during reproduction, but lower accuracy).

        Returns:
            A new Shape instance representing the MultiPolygon.
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
        """Calculates shape bounding box.

        **Tips:** *Using this you can get more precise information about a shape (width, height, position).*

        Parameters:
            exact (bool): Whether the calculation of the bounding box should be exact, which is more precise for Bézier curves.

        Returns:
            A tuple (x0, y0, x1, y1) containing coordinates of the bounding box.

        Examples:
            ..  code-block:: python3

                print( "Left-top: %d %d\\nRight-bottom: %d %d" % ( Shape("m 10 5 l 25 5 25 42 10 42").bounding() ) )
                print( Shape("m 313 312 b 254 287 482 38 277 212 l 436 269 b 378 388 461 671 260 481").bounding() )
                print( Shape("m 313 312 b 254 287 482 38 277 212 l 436 269 b 378 388 461 671 260 481").bounding(exact=True) )

            >>> Left-top: 10 5
            >>> Right-bottom: 25 42
            >>> (254.0, 38.0, 482.0, 671.0)
            >>> (260.0, 150.67823683425252, 436.0, 544.871772934194)
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
    ) -> Shape:
        """Return the boolean combination between *self* and *other*.

        The two shapes are converted to Shapely ``MultiPolygon`` objects (curves are
        automatically *flattened* with the given *tolerance* just like in
        :py:meth:`to_multipolygon`). The requested boolean operation is performed
        and the resulting geometry is converted back to a :class:`Shape`.

        Parameters:
            other: The other shape to combine with *self*.
            op: One of `union`, `intersection`, `difference` or `xor` (symmetric difference).
            tolerance: Angle in degrees used when flattening Bézier curves (see :py:meth:`flatten`).
            min_point_spacing: Per-axis spacing threshold passed to :py:meth:`from_multipolygon`.

        Returns:
            A **new** shape representing the result of the boolean operation.
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

        # Convert back to Shape and return.
        return Shape.from_multipolygon(result_geom, min_point_spacing)

    def map(
        self,
        fun: (
            Callable[[float, float], tuple[float, float]]
            | Callable[[float, float, str], tuple[float, float]]
        ),
    ) -> Shape:
        """Sends every point of a shape through given transformation function to change them.

        **Tips:** *Working with outline points can be used to deform the whole shape and make f.e. a wobble effect.*

        Parameters:
            fun (function): A function with two (or optionally three) parameters. It will define how each coordinate will be changed. The first two parameters represent the x and y coordinates of each point. The third optional it represents the type of each point (move, line, bezier...).

        Returns:
            A pointer to the current object.

        Examples:
            ..  code-block:: python3

                original = Shape("m 0 0 l 20 0 20 10 0 10")
                print ( original.map(lambda x, y: (x+10, y+5) ) )

            >>> m 10 5 l 30 5 30 15 10 15
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

        # Update the shape with transformed elements
        self.elements = transformed_elements
        return self

    def move(self, x: float, y: float) -> Shape:
        """Moves shape coordinates in given direction.

        | This function is a high level function, it just uses Shape.map, which is more advanced.

        Parameters:
            x (int or float): Displacement along the x-axis.
            y (int or float): Displacement along the y-axis.

        Returns:
            A pointer to the current object.

        Examples:
            ..  code-block:: python3

                print( Shape("m 0 0 l 30 0 30 20 0 20").move(-5, 10) )

            >>> m -5 10 l 25 10 25 30 -5 30
        """
        if x == 0 and y == 0:
            return self

        return self.map(lambda cx, cy: (cx + x, cy + y))

    def align(self, an: int = 5, anchor: int | None = None) -> Shape:
        """Moves the outline so that a chosen **pivot inside the shape** coincides
        with the point that will be used for ``\\pos`` when the line is rendered
        with a given ``{\\an..}`` tag.

        | If no argument for anchor is passed, it will automatically center the shape.

        Parameters:
            an (int): Alignment of the subtitle line (``{\\an1}`` … ``{\\an9}``).
            anchor (int, optional): Pivot inside the shape - uses the same keypad convention.  Defaults to *an*.

        Returns:
            A pointer to the current object.

        Examples:
            ..  code-block:: python3

                print( Shape("m 10 10 l 30 10 30 20 10 20").align() )

            >>> m 0 0 l 20 0 20 10 0 10
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
    ) -> Shape:
        """Scales shape coordinates horizontally and vertically, similar to ASS \\fscx and \\fscy tags.

        Parameters:
            fscx (int or float): Horizontal scale factor as percentage (100 = normal, 200 = double width, 50 = half width).
            fscy (int or float): Vertical scale factor as percentage (100 = normal, 200 = double height, 50 = half height).
            origin (tuple[float, float], optional): The pivot point around which the scaling is applied.

        Returns:
            A pointer to the current object.

        Examples:
            ..  code-block:: python3

                # Double the width, keep height the same
                print( Shape("m 0 50 l 0 0 50 0 50 50").scale(fscx=200) )

                # Scale to half size
                print( Shape("m 0 50 l 0 0 50 0 50 50").scale(fscx=50, fscy=50) )

            >>> m 0 50 l 0 0 100 0 100 50
            >>> m 0 25 l 0 0 25 0 25 25
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
        """Rotates the shape mimicking the behaviour of \\frx, \\fry and \\frz tags.

        Parameters:
            frx, fry, frz: Rotation angles in **degrees** around, respectively, the X, Y and Z axes.
            origin: Pivot around which the rotation is applied.

        Returns:
            A pointer to the current object.
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
        """Applies a shear (aka slant/skew) transformation to the shape, mimicking the \\fax and \\fay tags.

        Parameters:
            fax: Horizontal shear factor. Positive values slant the top of the shape to the right, negative to the left.
            fay: Vertical shear factor. Positive values slant the right side of the shape downwards, negative upwards.
            origin: Pivot around which the shear is applied.

        Returns:
            A pointer to the current object.
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

    def flatten(self, tolerance: float = 1.0) -> Shape:
        """Splits shape's bezier curves into lines.

        | This is a low level function. Instead, you should use :func:`split` which already calls this function.

        Parameters:
            tolerance (float): Angle in degree to define a curve as flat (increasing it will boost performance during reproduction, but lower accuracy)

        Returns:
            A pointer to the current object.

        Returns:
            The shape as a string, with bezier curves converted to lines.
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

        # Update shape with flattened elements
        self.elements = flattened_elements
        return self

    def split(self, max_len: float = 16, tolerance: float = 1.0) -> Shape:
        """Splits shape bezier curves into lines and splits lines into shorter segments with maximum given length.

        **Tips:** *You can call this before using :func:`map` to work with more outline points for smoother deforming.*

        Parameters:
            max_len (int or float): The max length that you want all the lines to be.
            tolerance (float): Angle in degree to define a bezier curve as flat (increasing it will boost performance during reproduction, but lower accuracy).

        Returns:
            A pointer to the current object.

        Examples:
            ..  code-block:: python3

                print( Shape("m -100.5 0 l 100 0 b 100 100 -100 100 -100.5 0 c").split() )

            >>> m -100.5 0 l -100 0 -90 0 -80 0 -70 0 -60 0 -50 0 -40 0 -30 0 -20 0 -10 0 0 0 10 0 20 0 30 0 40 0 50 0 60 0 70 0 80 0 90 0 100 0 l 99.964 2.325 99.855 4.614 99.676 6.866 99.426 9.082 99.108 11.261 98.723 13.403 98.271 15.509 97.754 17.578 97.173 19.611 96.528 21.606 95.822 23.566 95.056 25.488 94.23 27.374 93.345 29.224 92.403 31.036 91.405 32.812 90.352 34.552 89.246 36.255 88.086 37.921 86.876 39.551 85.614 41.144 84.304 42.7 82.945 44.22 81.54 45.703 80.088 47.15 78.592 48.56 77.053 49.933 75.471 51.27 73.848 52.57 72.184 53.833 70.482 55.06 68.742 56.25 66.965 57.404 65.153 58.521 63.307 59.601 61.427 60.645 59.515 61.652 57.572 62.622 55.599 63.556 53.598 64.453 51.569 65.314 49.514 66.138 47.433 66.925 45.329 67.676 43.201 68.39 41.052 69.067 38.882 69.708 36.692 70.312 34.484 70.88 32.259 71.411 27.762 72.363 23.209 73.169 18.61 73.828 13.975 74.341 9.311 74.707 4.629 74.927 -0.062 75 -4.755 74.927 -9.438 74.707 -14.103 74.341 -18.741 73.828 -23.343 73.169 -27.9 72.363 -32.402 71.411 -34.63 70.88 -36.841 70.312 -39.033 69.708 -41.207 69.067 -43.359 68.39 -45.49 67.676 -47.599 66.925 -49.683 66.138 -51.743 65.314 -53.776 64.453 -55.782 63.556 -57.759 62.622 -59.707 61.652 -61.624 60.645 -63.509 59.601 -65.361 58.521 -67.178 57.404 -68.961 56.25 -70.707 55.06 -72.415 53.833 -74.085 52.57 -75.714 51.27 -77.303 49.933 -78.85 48.56 -80.353 47.15 -81.811 45.703 -83.224 44.22 -84.59 42.7 -85.909 41.144 -87.178 39.551 -88.397 37.921 -89.564 36.255 -90.68 34.552 -91.741 32.812 -92.748 31.036 -93.699 29.224 -94.593 27.374 -95.428 25.488 -96.205 23.566 -96.92 21.606 -97.575 19.611 -98.166 17.578 -98.693 15.509 -99.156 13.403 -99.552 11.261 -99.881 9.082 -100.141 6.866 -100.332 4.614 -100.452 2.325 -100.5 0
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
        self.elements = split_elements
        return self

    def buffer(
        self,
        dist_xy: float,
        dist_y: float | None = None,
        *,
        kind: Literal["fill", "border"] = "border",
        join: Literal["round", "bevel", "mitre"] = "round",
    ) -> Shape:
        """Return a *buffered* version of the shape.

        A *buffer* is the set of points whose distance from the original geometryis <= to *dist*.
        You could use this to create a shape representing the border you usually get with ``{\\bord}``,
        or to expand/contract the shape.

        Parameters:
            dist_xy (float): Horizontal buffer distance.  Positive values "expand" the shape, negative values "contract" it.
            dist_y (float | None, optional): Vertical buffer distance.  If *None* the same value as *dist_xy* is used.  The sign **must** match that of *dist_xy*.
            kind ({"fill", "border"}, optional): "fill" ⇒ return the filled buffered geometry, "border" ⇒ return only the ring between the original shape and the buffered geometry (external or internal border).
            join ({"round", "bevel", "mitre"}, optional): Corner-join style.
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
        src_cmds: str,
        tgt_cmds: str,
        max_len: float,
        tolerance: float,
        w_dist: float,
        w_area: float,
        w_overlap: float,
        cost_threshold: float,
        ensure_shell_pairs: bool = False,
    ) -> tuple[
        list[tuple[LinearRing, LinearRing, bool]],
        list[tuple[LinearRing, Point, bool]],
        list[tuple[LinearRing, Point, bool]],
    ]:
        """Prepare the morphing process by decomposing the shapes into compounds and pairing them.

        Returns:
            A tuple containing:
            - A list of (src, tgt, is_hole) ring pairs
            - A list of (src, dest, is_hole) unmatched source rings
            - A list of (tgt, origin, is_hole) unmatched target rings
        """

        def _pair_compounds(
            src_compounds: MultiPolygon,
            tgt_compounds: MultiPolygon,
            w_dist: float = 0.55,
            w_area: float = 0.35,
            w_overlap: float = 0.1,
            cost_threshold: float = 2.5,
            ensure_shell_pairs: bool = False,
        ) -> tuple[
            list[tuple[LinearRing, LinearRing, bool]],
            list[tuple[LinearRing, Point, bool]],
            list[tuple[LinearRing, Point, bool]],
        ]:
            """
            Pair source and target polygon rings (exteriors and interiors) based on centroid distance,
            area similarity, and overlap, avoiding shell-hole mismatches.

            Any ring left without a counterpart is matched to the closest centroid so that downstream
            morphing logic can decide whether it is *appearing* or *disappearing*.
            """

            def _extract_rings(
                multipolygon: MultiPolygon,
            ) -> list[tuple[Polygon, bool]]:
                out: list[tuple[Polygon, bool]] = []
                for poly in multipolygon.geoms:
                    out.append((Polygon(poly.exterior), False))
                    out.extend((Polygon(inter), True) for inter in poly.interiors)
                return out

            src_rings = _extract_rings(src_compounds)
            tgt_rings = _extract_rings(tgt_compounds)

            matched = []
            unmatched_src = []
            unmatched_tgt = []

            # Global centroid arrays (used for nearest-neighbour fallback)
            all_src_centroids = np.array(
                [poly.centroid.coords[0] for poly, _ in src_rings]
            )
            all_tgt_centroids = np.array(
                [poly.centroid.coords[0] for poly, _ in tgt_rings]
            )

            # Match separately for shells (False) and holes (True)
            for is_hole in (False, True):
                cur_src = [poly for (poly, flag) in src_rings if flag == is_hole]
                cur_tgt = [poly for (poly, flag) in tgt_rings if flag == is_hole]
                n_src, n_tgt = len(cur_src), len(cur_tgt)

                if n_src == 0 and n_tgt == 0:
                    continue
                if n_src == 0:
                    for poly in cur_tgt:
                        unmatched_tgt.append((poly.exterior, poly.centroid, is_hole))
                    continue
                if n_tgt == 0:
                    for poly in cur_src:
                        unmatched_src.append((poly.exterior, poly.centroid, is_hole))
                    continue

                src_centroids = np.array([poly.centroid.coords[0] for poly in cur_src])
                tgt_centroids = np.array([poly.centroid.coords[0] for poly in cur_tgt])
                src_areas = np.array([poly.area for poly in cur_src])
                tgt_areas = np.array([poly.area for poly in cur_tgt])

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
                    poly_i = cur_src[i]
                    area_i = src_areas[i]
                    for j in cols:
                        poly_j = cur_tgt[j]
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
                            (cur_src[i].exterior, cur_tgt[j].exterior, is_hole)
                        )
                        used_src.add(i)
                        used_tgt.add(j)

                # 5) Handle still-unmatched rings.
                unmatched_src_idx = set(range(n_src)) - used_src
                unmatched_tgt_idx = set(range(n_tgt)) - used_tgt

                # Optionally force-pair shells so that they always morph into something.
                if ensure_shell_pairs and not is_hole and n_src > 0 and n_tgt > 0:
                    # Pair every remaining source shell with its minimum-cost target shell
                    for i in list(unmatched_src_idx):
                        j = int(np.argmin(costs[i]))
                        matched.append(
                            (cur_src[i].exterior, cur_tgt[j].exterior, is_hole)
                        )
                        unmatched_src_idx.remove(i)

                    # Pair every remaining target shell with its minimum-cost source shell
                    for j in list(unmatched_tgt_idx):
                        i = int(np.argmin(costs[:, j]))
                        matched.append(
                            (cur_src[i].exterior, cur_tgt[j].exterior, is_hole)
                        )
                        unmatched_tgt_idx.remove(j)

                # Any ring still left unmatched will be matched to the closest centroid.
                for idx in unmatched_src_idx:
                    poly = cur_src[idx]
                    src_cent = src_centroids[idx]
                    nn = np.argmin(np.linalg.norm(all_tgt_centroids - src_cent, axis=1))
                    unmatched_src.append(
                        (poly.exterior, Point(all_tgt_centroids[nn]), is_hole)
                    )

                for idx in unmatched_tgt_idx:
                    poly = cur_tgt[idx]
                    tgt_cent = tgt_centroids[idx]
                    nn = np.argmin(np.linalg.norm(all_src_centroids - tgt_cent, axis=1))
                    unmatched_tgt.append(
                        (poly.exterior, Point(all_src_centroids[nn]), is_hole)
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
        # 0) Flatten and split into short lines to have more points to work with
        src_shape = Shape(src_cmds).split(max_len, tolerance)
        tgt_shape = Shape(tgt_cmds).split(max_len, tolerance)

        # 1) Decompose into compounds (shell with holes)
        src_compounds = src_shape.to_multipolygon()
        tgt_compounds = tgt_shape.to_multipolygon()

        # 2) Pair individual rings extracted from those compounds
        paired_rings, src_unmatched, tgt_unmatched = _pair_compounds(
            src_compounds,
            tgt_compounds,
            w_dist,
            w_area,
            w_overlap,
            cost_threshold,
            ensure_shell_pairs,
        )

        # 3) Resample each paired ring so that both have the same vertex count
        resampled_pairs: list[tuple[LinearRing, LinearRing, bool]] = []

        for src_ring, tgt_ring, is_hole in paired_rings:
            # Decide target vertex count (at least 4 and large enough to accommodate both rings)
            n_src = len(src_ring.coords) - 1  # exclude duplicate closing vertex
            n_tgt = len(tgt_ring.coords) - 1
            n_points = max(n_src, n_tgt, 4)

            res_src = _resample_loop(src_ring, n_points)
            res_tgt = _resample_loop(tgt_ring, n_points)

            resampled_pairs.append((res_src, res_tgt, is_hole))

        return resampled_pairs, src_unmatched, tgt_unmatched

    def morph(
        self,
        target: Shape,
        t: float,
        max_len: float = 16.0,
        tolerance: float = 1.0,
        min_point_spacing: float = 0.5,
        w_dist: float = 0.55,
        w_area: float = 0.35,
        w_overlap: float = 0.1,
        cost_threshold: float = 2.5,
        ensure_shell_pairs: bool = True,
    ) -> Shape:
        """Interpolates the current shape towards *target*, returning a new `Shape` that represents the intermediate state at fraction *t*.

        Parameters:
            target (Shape): Destination shape.
            t (float): Interpolation factor (0 ≤ t ≤ 1).
            max_len (int or float): The max length that you want all the lines to be.
            tolerance (float): Angle in degree to define a bezier curve as flat (increasing it will boost performance during reproduction, but lower accuracy)
            min_point_spacing (float): Per-axis spacing threshold - a vertex is kept only if both `|Δx|` and `|Δy|` from the previous vertex are ≥ this value (increasing it will boost performance during reproduction, but lower accuracy).
            w_dist (float, optional): Weight for the centroid-distance term (higher values make proximity more important).
            w_area (float, optional): Weight for the relative area-difference term (higher values make size similarity more important).
            w_overlap (float, optional): Weight for the overlap / IoU term that penalises pairs with little spatial intersection.
            cost_threshold (float, optional): Maximum acceptable cost for a pairing. Pairs whose cost is above this threshold are treated as unmatched and will grow/shrink to the closest centroid.
            ensure_shell_pairs (bool, optional): If ``True`` *shell* rings that would otherwise remain unmatched will be force-paired with the shell that yields the minimum cost. This guarantees that every visible contour morphs into something, at the price of allowing the same shell to be reused multiple times.

        Returns:
            A **new** `Shape` instance representing the morph at *t*.

        Note:
            Shapes are first decomposed into compounds (outer shells with holes).
            Then, individual loops are matched based on:
            - Centroid distance (preferring loops with closer centers);
            - Area similarity (preferring loops of similar size);
            - Overlap (preferring loops that share space);
            - Shell/hole role (avoiding matching shells with holes).

            The matched loops are interpolated. The unmatched ones are either shrunk or grown.
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
        paired, src_unmatched, tgt_unmatched = Shape._prepare_morph(
            self.drawing_cmds,
            target.drawing_cmds,
            max_len=max_len,
            tolerance=tolerance,
            w_dist=w_dist,
            w_area=w_area,
            w_overlap=w_overlap,
            cost_threshold=cost_threshold,
            ensure_shell_pairs=ensure_shell_pairs,
        )

        # 2) Interpolate matched rings
        result_rings: list[tuple[LinearRing, bool]] = [
            (_interpolate_rings(src, tgt, t), is_hole) for src, tgt, is_hole in paired
        ]

        # 3) Handle disappearing / appearing rings
        for ring, dest_pt, is_hole in src_unmatched:
            result_rings.append(
                (_morph_transition(ring, dest_pt, t, appearing=False), is_hole)
            )
        for ring, origin_pt, is_hole in tgt_unmatched:
            result_rings.append(
                (_morph_transition(ring, origin_pt, t, appearing=True), is_hole)
            )

        # 4) Convert back to Shape and return
        return Shape.from_multipolygon(
            _rings_to_multipolygon(result_rings), min_point_spacing
        )

    @staticmethod
    def polygon(edges: int, side_length: float) -> Shape:
        """Returns a shape representing a regular *n*-sided polygon.

        Parameters:
            edges (int): Number of sides.
            side_length (float): Length of each side.

        Returns:
            A shape representing the polygon.
        """
        if edges < 3:
            raise ValueError("Edges must be ≥ 3")
        if side_length <= 0:
            raise ValueError("Side length must be positive")

        # Calculate circumradius from side length
        radius = side_length / (2 * math.sin(math.pi / edges))

        f = Shape.format_value
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
        return Shape(" ".join(cmd_parts)).align()

    @staticmethod
    def ellipse(w: float, h: float) -> Shape:
        """Returns a shape object of an ellipse with given width and height, centered around (0,0).

        **Tips:** *You could use that to create rounded stribes or arcs in combination with blurring for light effects.*

        Parameters:
            w (int or float): The width for the ellipse.
            h (int or float): The height for the ellipse.

        Returns:
            A shape object representing an ellipse.
        """
        try:
            w2, h2 = w / 2, h / 2
        except TypeError:
            raise TypeError("Number(s) expected")

        f = Shape.format_value

        return Shape(
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

    @staticmethod
    def ring(out_r: float, in_r: float) -> Shape:
        """Returns a shape object of a ring with given inner and outer radius, centered around (0,0).

        **Tips:** *A ring with increasing inner radius, starting from 0, can look like an outfading point.*

        Parameters:
            out_r (int or float): The outer radius for the ring.
            in_r (int or float): The inner radius for the ring.

        Returns:
            A shape object representing a ring.
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

        f = Shape.format_value
        return Shape(
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

    @staticmethod
    def heart(size: float, offset: float = 0) -> Shape:
        """Returns a shape object of a heart object with given size (width&height) and vertical offset of center point, centered around (0,0).

        **Tips:** *An offset=size*(2/3) results in a splitted heart.*

        Parameters:
            size (int or float): The width&height for the heart.
            offset (int or float): The vertical offset of center point.

        Returns:
            A shape object representing an heart.
        """
        try:
            mult = size / 30
        except TypeError:
            raise TypeError("Size parameter must be a number")
        # Build shape from template
        shape = Shape(
            "m 15 30 b 27 22 30 18 30 14 30 8 22 0 15 10 8 0 0 8 0 14 0 18 3 22 15 30"
        ).map(lambda x, y: (x * mult, y * mult))

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

    @staticmethod
    def _glance_or_star(
        edges: int, inner_size: float, outer_size: float, g_or_s: str
    ) -> Shape:
        """
        General function to create a shape object representing star or glance.
        """
        # Alias for utility functions
        f = Shape.format_value

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

        shape = Shape(" ".join(shape))

        # Return result centered
        return shape.align()

    @staticmethod
    def star(edges: int, inner_size: float, outer_size: float) -> Shape:
        """Returns a shape object of a star object with given number of outer edges and sizes, centered around (0,0).

        **Tips:** *Different numbers of edges and edge distances allow individual n-angles.*

        Parameters:
            edges (int): The number of edges of the star.
            inner_size (int or float): The inner edges distance from center.
            outer_size (int or float): The outer edges distance from center.

        Returns:
            A shape object as a string representing a star.
        """
        return Shape._glance_or_star(edges, inner_size, outer_size, "l")

    @staticmethod
    def glance(edges: int, inner_size: float, outer_size: float) -> Shape:
        """Returns a shape object of a glance object with given number of outer edges and sizes, centered around (0,0).

        **Tips:** *Glance is similar to Star, but with curves instead of inner edges between the outer edges.*

        Parameters:
            edges (int): The number of edges of the star.
            inner_size (int or float): The inner edges distance from center.
            outer_size (int or float): The control points for bezier curves between edges distance from center.

        Returns:
            A shape object as a string representing a glance.
        """
        return Shape._glance_or_star(edges, inner_size, outer_size, "b")
