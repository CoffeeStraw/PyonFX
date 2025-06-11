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
import math
from typing import Callable, cast
from pyquaternion import Quaternion
from inspect import signature


class ShapeElement:
    """
    Represents a single drawing command with its associated coordinates.

    Attributes:
        command (str): The drawing command (one of "m", "n", "l", "p", "b", "s", "c").
        coordinates (list[tuple[float, float]]): List of (x, y) coordinate pairs for this command.
    """

    def __init__(self, command: str, coordinates: list[tuple[float, float]]):
        if command not in {"m", "n", "l", "p", "b", "s", "c"}:
            raise ValueError(f"Invalid command '{command}'")
        self.command = command
        self.coordinates = coordinates

    def __repr__(self):
        coord_strs = [f"({x}, {y})" for x, y in self.coordinates]
        return f"ShapeElement('{self.command}', [{', '.join(coord_strs)}])"

    def __eq__(self, other):
        return (
            isinstance(other, ShapeElement)
            and self.command == other.command
            and self.coordinates == other.coordinates
        )


class Shape:
    """
    This class can be used to define a Shape object (by passing its drawing commands)
    and then apply functions to it in order to accomplish some tasks, like analyzing its bounding box, apply transformations, splitting curves into segments...

    Args:
        drawing_cmds (str): The shape's drawing commands in ASS format as a string.
    """

    def __init__(self, drawing_cmds: str):
        # Assure that drawing_cmds is a string
        if not isinstance(drawing_cmds, str):
            raise TypeError(
                f"A string containing the shape's drawing commands is expected, but you passed a {type(drawing_cmds)}"
            )
        self.drawing_cmds = drawing_cmds

    def __repr__(self):
        # We return drawing commands as a string rapresentation of the object
        return self.drawing_cmds

    def __eq__(self, other: Shape):
        return type(other) is type(self) and self.drawing_cmds == other.drawing_cmds

    def __iter__(self):
        """
        Iterate over the shape, yielding ShapeElement objects for each drawing command.

        Yields:
            ShapeElement: Objects containing the command and its associated coordinates.
        """
        cmds_and_points = self.drawing_cmds.split()
        if not cmds_and_points:
            return

        all_commands = {"m", "n", "l", "p", "b", "s", "c"}

        i = 0
        n = len(cmds_and_points)

        while i < n:
            token = cmds_and_points[i]

            # Check if this token is a command
            if token not in all_commands:
                raise ValueError(f"Unexpected command '{token}'")

            # Handle command with no coordinates
            if token == "c":
                yield ShapeElement(token, [])
                i += 1
                continue

            # Extract coordinates for this command
            coordinates = []
            coord_start = i + 1

            if token in {"m", "n", "p"}:
                # These commands take exactly 1 coordinate pair
                if coord_start + 1 >= n:
                    raise ValueError(
                        f"Unexpected end of shape while parsing command '{token}'"
                    )

                try:
                    x = float(cmds_and_points[coord_start])
                    y = float(cmds_and_points[coord_start + 1])
                    coordinates.append((x, y))
                except ValueError:
                    raise ValueError(
                        f"Invalid coordinate values for command '{token}': {cmds_and_points[coord_start]}, {cmds_and_points[coord_start + 1]}"
                    )

                i = coord_start + 2

            elif token == "b":
                # Bezier curve takes exactly 3 coordinate pairs, but can have implicit continuations
                coord_idx = coord_start

                # Read sets of 3 coordinate pairs until we can't anymore
                while coord_idx + 6 <= n:
                    # Check if we have 6 consecutive numeric values (3 coordinate pairs)
                    try:
                        coordinates = []
                        for pair_idx in range(3):
                            x = float(cmds_and_points[coord_idx + pair_idx * 2])
                            y = float(cmds_and_points[coord_idx + pair_idx * 2 + 1])
                            coordinates.append((x, y))

                        # Successfully parsed 3 coordinate pairs, yield this bezier
                        yield ShapeElement("b", coordinates)
                        coord_idx += 6

                        # Check if the next token is a command - if so, we're done with bezier sequences
                        if coord_idx < n and cmds_and_points[coord_idx] in all_commands:
                            break

                    except (ValueError, IndexError):
                        # Can't parse more coordinates, we're done
                        break

                # If we didn't parse any coordinates at all, that's an error
                if coord_idx == coord_start:
                    raise ValueError(
                        f"Command '{token}' requires at least 3 coordinate pairs"
                    )

                i = coord_idx
                continue  # Skip the normal yield since we already yielded in the loop

            elif token == "l":
                # Line command takes variable number of coordinate pairs
                coord_idx = coord_start

                # Read coordinate pairs until we hit another command or end of data
                while coord_idx + 2 <= n:
                    # Check if the next token is a command
                    if cmds_and_points[coord_idx] in all_commands:
                        break

                    # Try to parse as coordinate pair
                    try:
                        x = float(cmds_and_points[coord_idx])
                        y = float(cmds_and_points[coord_idx + 1])

                        # Yield a separate ShapeElement for each coordinate pair
                        yield ShapeElement("l", [(x, y)])
                        coord_idx += 2

                    except (ValueError, IndexError):
                        break

                # If we didn't parse any coordinates at all, that's an error
                if coord_idx == coord_start:
                    raise ValueError(f"Command 'l' requires at least 1 coordinate pair")

                i = coord_idx
                continue  # Skip the normal yield since we already yielded in the loop

            elif token == "s":
                # Spline command takes variable number of coordinate pairs (minimum 3)
                # All coordinate pairs are grouped into a single ShapeElement
                coord_idx = coord_start

                # Read coordinates until we hit another command or end of data
                while coord_idx + 1 < n:
                    # Check if the next token is a command
                    if cmds_and_points[coord_idx] in all_commands:
                        break

                    # Try to parse as coordinate pair
                    try:
                        x = float(cmds_and_points[coord_idx])
                        y = float(cmds_and_points[coord_idx + 1])
                        coordinates.append((x, y))
                        coord_idx += 2
                    except (ValueError, IndexError):
                        break

                # Validate minimum coordinate pairs for spline
                if len(coordinates) < 3:
                    raise ValueError(
                        f"Command 's' requires at least 3 coordinate pairs, got {len(coordinates)}"
                    )

                i = coord_idx

            yield ShapeElement(token, coordinates)

    @classmethod
    def from_elements(cls, elements: list[ShapeElement]) -> Shape:
        """
        Create a Shape from a list of ShapeElement objects.

        Parameters:
            elements (list[ShapeElement]): List of shape elements to convert to a shape string.

        Returns:
            Shape: A new Shape object created from the elements.
        """
        if not elements:
            return cls("m 0 0")

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
                for x, y in element.coordinates:
                    coord_strs.extend([cls.format_value(x), cls.format_value(y)])

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

        return cls(" ".join(parts))

    @staticmethod
    def format_value(x: float, prec: int = 3) -> str:
        # Utility function to properly format values for shapes also returning them as a string
        return f"{x:.{prec}f}".rstrip("0").rstrip(".")

    def has_error(self) -> bool | str:
        """Utility function that checks if the shape is valid.

        Returns:
            False if no error has been found, else a string with the first error encountered.
        """
        try:
            list(self)
            return False
        except ValueError as e:
            return str(e)
        except Exception as e:
            return f"Unexpected error: {str(e)}"

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

        transformed_elements = []
        for element in self:
            if not element.coordinates:
                # Commands like 'c' with no coordinates - keep as-is
                transformed_elements.append(element)
                continue

            # Transform each coordinate pair in this element
            transformed_coords = []
            for x, y in element.coordinates:
                if len(signature(fun).parameters) == 3:
                    fun = cast(Callable[[float, float, str], tuple[float, float]], fun)
                    new_x, new_y = fun(x, y, element.command)
                else:
                    fun = cast(Callable[[float, float], tuple[float, float]], fun)
                    new_x, new_y = fun(x, y)
                transformed_coords.append((new_x, new_y))

            transformed_elements.append(
                ShapeElement(element.command, transformed_coords)
            )

        # Reconstruct the shape from transformed elements
        transformed_shape = Shape.from_elements(transformed_elements)
        self.drawing_cmds = transformed_shape.drawing_cmds
        return self

    def bounding(self) -> tuple[float, float, float, float]:
        """Calculates shape bounding box.

        **Tips:** *Using this you can get more precise information about a shape (width, height, position).*

        Returns:
            A tuple (x0, y0, x1, y1) containing coordinates of the bounding box.

        Examples:
            ..  code-block:: python3

                print("Left-top: %d %d\\nRight-bottom: %d %d" % ( Shape("m 10 5 l 25 5 25 42 10 42").bounding() ) )

            >>> Left-top: 10 5
            >>> Right-bottom: 25 42
        """

        # Bounding data
        x0 = y0 = float("-inf")
        x1 = y1 = float("inf")

        # Calculate minimal and maximal coordinates
        for element in self:
            for x, y in element.coordinates:
                if x0 != float("-inf"):
                    x0 = min(x0, x)
                    y0 = min(y0, y)
                    x1 = max(x1, x)
                    y1 = max(y1, y)
                else:
                    x0, y0, x1, y1 = x, y, x, y

        return x0, y0, x1, y1

    def move(self, x: float | None = None, y: float | None = None) -> Shape:
        """Moves shape coordinates in given direction.

        | If neither x and y are passed, it will automatically center the shape to the origin (0,0).
        | This function is an high level function, it just uses Shape.map, which is more advanced. Additionally, it is an easy way to center a shape.

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
        if x is None and y is None:
            x, y = (-1 * el for el in self.bounding()[0:2])
        if x is None:
            x = 0
        if y is None:
            y = 0

        # Update shape
        self.map(lambda cx, cy: (cx + x, cy + y))
        return self

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
        # TO DO: Make this function iterative, recursion is bad.
        if tolerance < 0:
            raise ValueError("Tolerance must be a positive number")

        # Inner functions definitions
        # 4th degree curve subdivider (De Casteljau)
        def curve4_subdivide(
            x0,
            y0,
            x1,
            y1,
            x2,
            y2,
            x3,
            y3,
            pct,
        ):
            # Calculate points on curve vectors
            x01, y01, x12, y12, x23, y23 = (
                (x0 + x1) * pct,
                (y0 + y1) * pct,
                (x1 + x2) * pct,
                (y1 + y2) * pct,
                (x2 + x3) * pct,
                (y2 + y3) * pct,
            )
            x012, y012, x123, y123 = (
                (x01 + x12) * pct,
                (y01 + y12) * pct,
                (x12 + x23) * pct,
                (y12 + y23) * pct,
            )
            x0123, y0123 = (x012 + x123) * pct, (y012 + y123) * pct
            # Return new 2 curves
            return (
                x0,
                y0,
                x01,
                y01,
                x012,
                y012,
                x0123,
                y0123,
                x0123,
                y0123,
                x123,
                y123,
                x23,
                y23,
                x3,
                y3,
            )

        # Check flatness of 4th degree curve with angles
        def curve4_is_flat(
            x0,
            y0,
            x1,
            y1,
            x2,
            y2,
            x3,
            y3,
        ):
            # Pack curve vectors (only ones non zero)
            vecs = [[x1 - x0, y1 - y0], [x2 - x1, y2 - y1], [x3 - x2, y3 - y2]]
            vecs = [el for el in vecs if not (el[0] == 0 and el[1] == 0)]

            # Inner functions to calculate degrees between two 2d vectors
            def dotproduct(v1, v2):
                return sum((a * b) for a, b in zip(v1, v2))

            def length(v):
                return math.sqrt(dotproduct(v, v))

            def get_angle(v1, v2):
                calc = max(
                    min(dotproduct(v1, v2) / (length(v1) * length(v2)), 1), -1
                )  # Clamping value to prevent errors
                angle = math.degrees(math.acos(calc))
                if (v1[0] * v2[1] - v1[1] * v2[0]) < 0:
                    return -angle
                return angle

            # Check flatness on vectors
            for i in range(1, len(vecs)):
                if abs(get_angle(vecs[i - 1], vecs[i])) > tolerance:
                    return False
            return True

        # Inner function to convert 4th degree curve to line points
        def curve4_to_lines(
            x0,
            y0,
            x1,
            y1,
            x2,
            y2,
            x3,
            y3,
        ):
            # Line points buffer
            line_points = []

            # Conversion in recursive processing
            def convert_recursive(x0, y0, x1, y1, x2, y2, x3, y3):
                if curve4_is_flat(x0, y0, x1, y1, x2, y2, x3, y3):
                    line_points.append((x3, y3))
                    return

                (
                    x10,
                    y10,
                    x11,
                    y11,
                    x12,
                    y12,
                    x13,
                    y13,
                    x20,
                    y20,
                    x21,
                    y21,
                    x22,
                    y22,
                    x23,
                    y23,
                ) = curve4_subdivide(x0, y0, x1, y1, x2, y2, x3, y3, 0.5)
                convert_recursive(x10, y10, x11, y11, x12, y12, x13, y13)
                convert_recursive(x20, y20, x21, y21, x22, y22, x23, y23)

            # Splitting curve recursively until we're not satisfied (angle <= tolerance)
            convert_recursive(x0, y0, x1, y1, x2, y2, x3, y3)
            # Return resulting points, excluding the last point to avoid duplication
            return line_points[:-1] if line_points else []

        # Process elements
        flattened_elements = []
        last_point = None

        for element in self:
            match element.command:
                case "b":
                    if last_point is None:
                        raise ValueError("Bezier curve found without a starting point")
                    
                    x0, y0 = last_point
                    (x1, y1), (x2, y2), (x3, y3) = element.coordinates
                    
                    # Convert curve to line points
                    line_points = curve4_to_lines(x0, y0, x1, y1, x2, y2, x3, y3)
                    
                    # Add all line points as individual line elements
                    for x, y in line_points:
                        flattened_elements.append(ShapeElement("l", [(x, y)]))
                    
                    # Add the final point
                    flattened_elements.append(ShapeElement("l", [(x3, y3)]))
                    last_point = (x3, y3)
                case "c":
                    pass
                case _:
                    # Keep other commands as is and track last point
                    flattened_elements.append(element)
                    if element.coordinates:
                        last_point = element.coordinates[-1]

        # Reconstruct the shape from flattened elements
        flattened_shape = Shape.from_elements(flattened_elements)
        self.drawing_cmds = flattened_shape.drawing_cmds
        return self

    def split(self, max_len: float = 16, tolerance: float = 1.0) -> Shape:
        """Splits shape bezier curves into lines and splits lines into shorter segments with maximum given length.

        **Tips:** *You can call this before using :func:`map` to work with more outline points for smoother deforming.*

        Parameters:
            max_len (int or float): The max length that you want all the lines to be
            tolerance (float): Angle in degree to define a bezier curve as flat (increasing it will boost performance during reproduction, but lower accuracy)

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

        # Internal function to help splitting a line
        def line_split(x0: float, y0: float, x1: float, y1: float) -> list[tuple[float, float]]:
            # Line direction & length
            rel_x, rel_y = x1 - x0, y1 - y0
            distance = math.sqrt(rel_x * rel_x + rel_y * rel_y)
            
            # If the line is too short, return just the end point
            if distance <= max_len:
                return [(x1, y1)]
            
            # Split the line into segments
            segments = []
            distance_rest = distance % max_len
            cur_distance = distance_rest if distance_rest > 0 else max_len

            while cur_distance <= distance:
                pct = cur_distance / distance
                x = x0 + rel_x * pct
                y = y0 + rel_y * pct
                segments.append((x, y))
                cur_distance += max_len

            return segments

        # First flatten the shape to convert bezier curves to lines
        flattened_shape = Shape(self.drawing_cmds).flatten(tolerance)
        
        # Process elements using the iterator
        split_elements = []
        current_point = None
        first_move_point = None
        
        for element in flattened_shape:
            match element.command:
                case "m":
                    # Close previous contour if needed (implicit closing behavior)
                    if current_point is not None and first_move_point is not None:
                        x0, y0 = current_point
                        x1, y1 = first_move_point
                        
                        # Only add closing line if points are different
                        if (x0, y0) != (x1, y1):
                            line_segments = line_split(x0, y0, x1, y1)
                            for x, y in line_segments:
                                split_elements.append(ShapeElement("l", [(x, y)]))
                    
                    # Move command - start new contour
                    split_elements.append(element)
                    current_point = element.coordinates[0]
                    first_move_point = current_point
                    
                case "l":
                    # Line command - split if necessary
                    if current_point is None:
                        raise ValueError("Line command found without a starting point")
                    
                    x0, y0 = current_point
                    x1, y1 = element.coordinates[0]
                    
                    # Split the line into smaller segments
                    line_segments = line_split(x0, y0, x1, y1)
                    
                    # Add each segment as a separate line element
                    for x, y in line_segments:
                        split_elements.append(ShapeElement("l", [(x, y)]))
                    
                    # Update current point to the last segment endpoint
                    current_point = line_segments[-1] if line_segments else (x1, y1)
                    
                case "c":
                    # Close command - connect back to first move point if needed
                    if current_point is not None and first_move_point is not None:
                        x0, y0 = current_point
                        x1, y1 = first_move_point
                        
                        # Only add closing line if points are different
                        if (x0, y0) != (x1, y1):
                            line_segments = line_split(x0, y0, x1, y1)
                            for x, y in line_segments:
                                split_elements.append(ShapeElement("l", [(x, y)]))
                    
                    # Reset state for next contour
                    current_point = None
                    first_move_point = None
                    
                case _:
                    # Other commands (n, p, s) - keep as is and update current point
                    split_elements.append(element)
                    if element.coordinates:
                        current_point = element.coordinates[-1]

        # Close the last contour if needed
        if current_point is not None and first_move_point is not None:
            x0, y0 = current_point
            x1, y1 = first_move_point
            
            if (x0, y0) != (x1, y1):
                line_segments = line_split(x0, y0, x1, y1)
                for x, y in line_segments:
                    split_elements.append(ShapeElement("l", [(x, y)]))

        # Reconstruct the shape from split elements
        split_shape = Shape.from_elements(split_elements)
        self.drawing_cmds = split_shape.drawing_cmds
        return self

    def __to_outline(self, bord_xy: float, bord_y: float, mode: str = "round") -> Shape:
        """Converts shape command for filling to a shape command for stroking.

        **Tips:** *You could use this for border textures.*

        Parameters:
            shape (str): The shape in ASS format as a string.

        Returns:
            A pointer to the current object.

        Returns:
            A new shape as string, representing the border of the input.
        """
        raise NotImplementedError

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
    def __glance_or_star(
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
        return shape.move()

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
        return Shape.__glance_or_star(edges, inner_size, outer_size, "l")

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
        return Shape.__glance_or_star(edges, inner_size, outer_size, "b")

    @staticmethod
    def rectangle(w: float = 1.0, h: float = 1.0) -> Shape:
        """Returns a shape object of a rectangle with given width and height, centered around (0,0).

        **Tips:** *A rectangle with width=1 and height=1 is a pixel.*

        Parameters:
            w (int or float): The width for the rectangle.
            h (int or float): The height for the rectangle.

        Returns:
            A shape object representing an rectangle.
        """
        try:
            f = Shape.format_value
            return Shape(f"m 0 0 l {f(w)} 0 {f(w)} {f(h)} 0 {f(h)} 0 0")
        except TypeError:
            raise TypeError("Number(s) expected")

    @staticmethod
    def triangle(size: float) -> Shape:
        """Returns a shape object of an equilateral triangle with given side length, centered around (0,0).

        Parameters:
            size (int or float): The side length for the triangle.

        Returns:
            A shape object representing an triangle.
        """
        try:
            h = math.sqrt(3) * size / 2
            base = -h / 6
        except TypeError:
            raise TypeError("Number expected")

        f = Shape.format_value
        return Shape(
            "m %s %s l %s %s 0 %s %s %s"
            % (
                f(size / 2),
                f(base),
                f(size),
                f(base + h),
                f(base + h),
                f(size / 2),
                f(base),
            )
        )
