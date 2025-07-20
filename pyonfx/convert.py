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

import colorsys
import math
import os
import re
import sys
from enum import Enum
from typing import TYPE_CHECKING, cast, overload

import numpy as np
from PIL import Image
from shapely.affinity import scale as _shapely_scale
from shapely.affinity import translate as _shapely_translate
from shapely.vectorized import contains as _shapely_contains

from .font import Font
from .pixel import Pixel, PixelCollection

if TYPE_CHECKING:
    from .ass_core import Char, Line, Syllable, Word
    from .shape import Shape


class ColorModel(Enum):
    ASS = "&HBBGGRR&"
    ASS_STYLE = "&HAABBGGRR"
    RGB = "(r, g, b)"
    RGB_STR = "#RRGGBB"
    RGBA = "(r, g, b, a)"
    RGBA_STR = "#RRGGBBAA"
    HSV = "(h, s, v)"
    OKLAB = "(L, a, b)"


class Convert:
    """
    This class is a collection of static methods that will help
    the user to convert everything needed to the ASS format.
    """

    @overload
    @staticmethod
    def time(ass_ms: int) -> str: ...

    @overload
    @staticmethod
    def time(ass_ms: str) -> int: ...

    @staticmethod
    def time(ass_ms: int | str) -> int | str:
        """Converts between milliseconds and ASS timestamp.

        You can probably ignore that function, you will not make use of it for KFX or typesetting generation.

        Parameters:
            ass_ms (int or str): If int, than milliseconds are expected, else ASS timestamp as str is expected.

        Returns:
            If milliseconds -> ASS timestamp, else if ASS timestamp -> milliseconds, else ValueError will be raised.
        """
        # Milliseconds?
        if isinstance(ass_ms, int) and ass_ms >= 0:
            # It round ms to cs. From https://github.com/Aegisub/Aegisub/blob/6f546951b4f004da16ce19ba638bf3eedefb9f31/libaegisub/include/libaegisub/ass/time.h#L32
            # Ex: 49 ms to 50 ms
            ass_ms = (ass_ms + 5) - (ass_ms + 5) % 10

            return "{:d}:{:02d}:{:02d}.{:02d}".format(
                math.floor(ass_ms / 3600000) % 10,
                math.floor(ass_ms % 3600000 / 60000),
                math.floor(ass_ms % 60000 / 1000),
                math.floor(ass_ms % 1000 / 10),
            )
        # ASS timestamp?
        elif isinstance(ass_ms, str) and re.fullmatch(r"\d:\d+:\d+\.\d+", ass_ms):
            return (
                int(ass_ms[0]) * 3600000
                + int(ass_ms[2:4]) * 60000
                + int(ass_ms[5:7]) * 1000
                + int(ass_ms[8:10]) * 10
            )
        else:
            raise ValueError("Milliseconds or ASS timestamp expected")

    @staticmethod
    def alpha_ass_to_dec(alpha_ass: str) -> int:
        """Converts from ASS alpha string to corresponding decimal value.

        Parameters:
            alpha_ass (str): A string in the format '&HXX&'.

        Returns:
            A decimal in [0, 255] representing ``alpha_ass`` converted.

        Examples:
            ..  code-block:: python3

                print(Convert.alpha_ass_to_dec("&HFF&"))

            >>> 255
        """
        match = re.fullmatch(r"&H([0-9A-F]{2})&", alpha_ass)
        if match is None:
            raise ValueError(
                f"Provided ASS alpha string '{alpha_ass}' is not in the expected format '&HXX&'."
            )
        return int(match.group(1), 16)

    @staticmethod
    def alpha_dec_to_ass(alpha_dec: int | float) -> str:
        """Converts from decimal value to corresponding ASS alpha string.

        Parameters:
            alpha_dec (int or float): Decimal in [0, 255] representing an alpha value.

        Returns:
            A string in the format '&HXX&' representing ``alpha_dec`` converted.

        Examples:
            ..  code-block:: python3

                print(Convert.alpha_dec_to_ass(255))
                print(Convert.alpha_dec_to_ass(255.0))

            >>> "&HFF&"
            >>> "&HFF&"
        """
        try:
            if not 0 <= alpha_dec <= 255:
                raise ValueError(
                    f"Provided alpha decimal '{alpha_dec}' is out of the range [0, 255]."
                )
        except TypeError as e:
            raise TypeError(
                f"Provided alpha decimal was expected of type 'int' or 'float', but you provided a '{type(alpha_dec)}'."
            ) from e
        return f"&H{round(alpha_dec):02X}&"

    @staticmethod
    def color(
        c: (
            str
            | tuple[int, int, int]
            | tuple[int, int, int, int]
            | tuple[float, float, float]
            | tuple[float, float, float, float]
        ),
        input_format: ColorModel,
        output_format: ColorModel,
        round_output: bool = True,
    ) -> (
        str
        | tuple[int, int, int]
        | tuple[int, int, int, int]
        | tuple[float, float, float]
    ):
        """Converts a provided color from a color model to another.

        Parameters:
            c (str or tuple of int or tuple of float): A color in the format ``input_format``.
            input_format (ColorModel): The color format of ``c``.
            output_format (ColorModel): The color format for the output.
            round_output (bool): A boolean to determine whether the output should be rounded or not.

        Returns:
            A color in the format ``output_format``.

        Examples:
            ..  code-block:: python3

                print(Convert.color("&H0000FF&", ColorModel.ASS, ColorModel.RGB))

            >>> (255, 0, 0)
        """
        try:
            # Text for exception if input is out of ranges
            input_range_e = f"Provided input '{c}' has value(s) out of the range "

            # Parse input, obtaining its corresponding (r,g,b,a) values
            if input_format == ColorModel.ASS:
                if not isinstance(c, str):
                    raise TypeError("ASS color format requires string input")
                match = re.fullmatch(r"&H([0-9A-F]{2})([0-9A-F]{2})([0-9A-F]{2})&", c)
                if match is None:
                    raise ValueError(f"Invalid ASS color format: {c}")
                (b, g, r), a = map(lambda x: int(x, 16), match.groups()), 255
            elif input_format == ColorModel.ASS_STYLE:
                if not isinstance(c, str):
                    raise TypeError("ASS_STYLE color format requires string input")
                match = re.fullmatch("&H" + r"([0-9A-F]{2})" * 4, c)
                if match is None:
                    raise ValueError(f"Invalid ASS_STYLE color format: {c}")
                a, b, g, r = map(lambda x: int(x, 16), match.groups())
            elif input_format == ColorModel.RGB:
                if not isinstance(c, tuple) or len(c) != 3:
                    raise TypeError("RGB color format requires tuple of 3 values")
                if not all(0 <= n <= 255 for n in c):
                    raise ValueError(input_range_e + "[0, 255].")
                (r, g, b), a = map(int, c), 255
            elif input_format == ColorModel.RGB_STR:
                if not isinstance(c, str):
                    raise TypeError("RGB_STR color format requires string input")
                match = re.fullmatch("#" + r"([0-9A-F]{2})" * 3, c)
                if match is None:
                    raise ValueError(f"Invalid RGB_STR color format: {c}")
                (r, g, b), a = map(lambda x: int(x, 16), match.groups()), 255
            elif input_format == ColorModel.RGBA:
                if not isinstance(c, tuple) or len(c) != 4:
                    raise TypeError("RGBA color format requires tuple of 4 values")
                if not all(0 <= n <= 255 for n in c):
                    raise ValueError(input_range_e + "[0, 255].")
                r, g, b, a = map(int, c)
            elif input_format == ColorModel.RGBA_STR:
                if not isinstance(c, str):
                    raise TypeError("RGBA_STR color format requires string input")
                match = re.fullmatch("#" + r"([0-9A-F]{2})" * 4, c)
                if match is None:
                    raise ValueError(f"Invalid RGBA_STR color format: {c}")
                r, g, b, a = map(lambda x: int(x, 16), match.groups())
            elif input_format == ColorModel.HSV:
                if not isinstance(c, tuple) or len(c) != 3:
                    raise TypeError("HSV color format requires tuple of 3 values")
                h, s, v = c
                if not (0 <= h < 360 and 0 <= s <= 100 and 0 <= v <= 100):
                    raise ValueError(
                        input_range_e + "( [0, 360), [0, 100], [0, 100] )."
                    )
                h, s, v = h / 360, s / 100, v / 100
                (r, g, b), a = (
                    map(lambda x: int(255 * x), colorsys.hsv_to_rgb(h, s, v)),
                    255,
                )
            elif input_format == ColorModel.OKLAB:
                if not (isinstance(c, tuple) and len(c) == 3):
                    raise TypeError("OKLAB color format requires tuple of 3 values")
                r, g, b = Convert.oklab_to_rgb(c)
                a = 255
        except (AttributeError, ValueError, TypeError) as e:
            # AttributeError -> re.fullmatch failed
            # ValueError     -> too many values to unpack
            # TypeError      -> in case the provided tuple is not a list of numbers
            raise ValueError(
                f"Provided input '{c}' is not in the format '{input_format}'."
            ) from e

        # Convert (r,g,b,a) to the desired output_format
        try:
            if output_format == ColorModel.ASS:
                return f"&H{round(b):02X}{round(g):02X}{round(r):02X}&"
            elif output_format == ColorModel.ASS_STYLE:
                return f"&H{round(a):02X}{round(b):02X}{round(g):02X}{round(r):02X}"
            elif output_format == ColorModel.RGB:
                return (r, g, b)
            elif output_format == ColorModel.RGB_STR:
                return f"#{round(r):02X}{round(g):02X}{round(b):02X}"
            elif output_format == ColorModel.RGBA:
                return (r, g, b, a)
            elif output_format == ColorModel.RGBA_STR:
                return f"#{round(r):02X}{round(g):02X}{round(b):02X}{round(a):02X}"
            elif output_format == ColorModel.HSV:
                method = round if round_output else float
                h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
                return cast(
                    tuple[float, float, float],
                    (method(h * 360) % 360, method(s * 100), method(v * 100)),
                )
            elif output_format == ColorModel.OKLAB:
                method = round if round_output else float
                L, a, b = Convert.rgb_to_oklab((r, g, b))
                return cast(
                    tuple[float, float, float],
                    (method(L), method(a), method(b)),
                )
            else:
                raise ValueError(f"Unsupported output_format: {output_format}")
        except NameError as e:
            raise ValueError(f"Unsupported input_format ('{input_format}').") from e

    @staticmethod
    def color_ass_to_rgb(
        color_ass: str, as_str: bool = False
    ) -> str | tuple[int, int, int]:
        """Converts from ASS color string to corresponding RGB color.

        Parameters:
            color_ass (str): A string in the format '&HBBGGRR&'.
            as_str (bool): A boolean to determine the output type format.

        Returns:
            The output represents ``color_ass`` converted. If ``as_str`` = False, the output is a tuple of integers in range *[0, 255]*.
            Else, the output is a string in the format '#RRGGBB'.

        Examples:
            ..  code-block:: python3

                print(Convert.color_ass_to_rgb("&HABCDEF&"))
                print(Convert.color_ass_to_rgb("&HABCDEF&", as_str=True))

            >>> (239, 205, 171)
            >>> "#EFCDAB"
        """
        result = Convert.color(
            color_ass, ColorModel.ASS, ColorModel.RGB_STR if as_str else ColorModel.RGB
        )
        if as_str:
            return cast(str, result)
        return cast(tuple[int, int, int], result)

    @staticmethod
    def color_ass_to_hsv(
        color_ass: str, round_output: bool = True
    ) -> tuple[int, int, int] | tuple[float, float, float]:
        """Converts from ASS color string to corresponding HSV color.

        Parameters:
            color_ass (str): A string in the format '&HBBGGRR&'.
            round_output (bool): A boolean to determine whether the output should be rounded or not.

        Returns:
            The output represents ``color_ass`` converted. If ``round_output`` = True, the output is a tuple of integers in range *( [0, 360), [0, 100], [0, 100] )*.
            Else, the output is a tuple of floats in range *( [0, 360), [0, 100], [0, 100] )*.

        Examples:
            ..  code-block:: python3

                print(Convert.color_ass_to_hsv("&HABCDEF&"))
                print(Convert.color_ass_to_hsv("&HABCDEF&", round_output=False))

            >>> (30, 28, 94)
            >>> (30.000000000000014, 28.451882845188294, 93.72549019607843)
        """
        result = Convert.color(color_ass, ColorModel.ASS, ColorModel.HSV, round_output)
        return cast(tuple[int, int, int] | tuple[float, float, float], result)

    @staticmethod
    def color_rgb_to_ass(
        color_rgb: str | tuple[int | float, int | float, int | float],
    ) -> str:
        """Converts from RGB color to corresponding ASS color.

        Parameters:
            color_rgb (str or tuple of int or tuple of float): Either a string in the format '#RRGGBB' or a tuple of three integers (or floats) in the range *[0, 255]*.

        Returns:
            A string in the format '&HBBGGRR&' representing ``color_rgb`` converted.

        Examples:
            ..  code-block:: python3

                print(Convert.color_rgb_to_ass("#ABCDEF"))

            >>> "&HEFCDAB&"
        """
        result = Convert.color(
            color_rgb,
            ColorModel.RGB_STR if isinstance(color_rgb, str) else ColorModel.RGB,
            ColorModel.ASS,
        )
        return cast(str, result)

    @staticmethod
    def color_rgb_to_hsv(
        color_rgb: str | tuple[int | float, int | float, int | float],
        round_output: bool = True,
    ) -> tuple[int, int, int] | tuple[float, float, float]:
        """Converts from RGB color to corresponding HSV color.

        Parameters:
            color_rgb (str or tuple of int or tuple of float): Either a string in the format '#RRGGBB' or a tuple of three integers (or floats) in the range *[0, 255]*.
            round_output (bool): A boolean to determine whether the output should be rounded or not.

        Returns:
            The output represents ``color_rgb`` converted. If ``round_output`` = True, the output is a tuple of integers in range *( [0, 360), [0, 100], [0, 100] )*.
            Else, the output is a tuple of floats in range *( [0, 360), [0, 100], [0, 100] )*.

        Examples:
            ..  code-block:: python3

                print(Convert.color_rgb_to_hsv("#ABCDEF"))
                print(Convert.color_rgb_to_hsv("#ABCDEF"), round_output=False)

            >>> (210, 28, 94)
            >>> (210.0, 28.451882845188294, 93.72549019607843)
        """
        result = Convert.color(
            color_rgb,
            ColorModel.RGB_STR if isinstance(color_rgb, str) else ColorModel.RGB,
            ColorModel.HSV,
            round_output,
        )
        return cast(tuple[int, int, int] | tuple[float, float, float], result)

    @staticmethod
    def color_hsv_to_ass(
        color_hsv: tuple[int | float, int | float, int | float],
    ) -> str:
        """Converts from HSV color string to corresponding ASS color.

        Parameters:
            color_hsv (tuple of int/float): A tuple of three integers (or floats) in the range *( [0, 360), [0, 100], [0, 100] )*.

        Returns:
            A string in the format '&HBBGGRR&' representing ``color_hsv`` converted.

        Examples:
            ..  code-block:: python3

                print(Convert.color_hsv_to_ass((100, 100, 100)))

            >>> "&H00FF55&"
        """
        result = Convert.color(color_hsv, ColorModel.HSV, ColorModel.ASS)
        return cast(str, result)

    @staticmethod
    def color_hsv_to_rgb(
        color_hsv: tuple[int | float, int | float, int | float],
        as_str: bool = False,
        round_output: bool = True,
    ) -> str | tuple[int, int, int] | tuple[float, float, float]:
        """Converts from HSV color string to corresponding RGB color.

        Parameters:
            color_hsv (tuple of int/float): A tuple of three integers (or floats) in the range *( [0, 360), [0, 100], [0, 100] )*.
            as_str (bool): A boolean to determine the output type format.
            round_output (bool): A boolean to determine whether the output should be rounded or not.

        Returns:
            The output represents ``color_hsv`` converted. If ``as_str`` = False, the output is a tuple
            ( also, if ``round_output`` = True, the output is a tuple of integers in range *( [0, 360), [0, 100], [0, 100] )*, else a tuple of float in range *( [0, 360), [0, 100], [0, 100] ) )*.
            Else, the output is a string in the format '#RRGGBB'.

        Examples:
            ..  code-block:: python3

                print(Convert.color_hsv_to_rgb((100, 100, 100)))
                print(Convert.color_hsv_to_rgb((100, 100, 100), as_str=True))
                print(Convert.color_hsv_to_rgb((100, 100, 100), round_output=False))

            >>> (85, 255, 0)
            >>> "#55FF00"
            >>> (84.99999999999999, 255.0, 0.0)
        """
        result = Convert.color(
            color_hsv,
            ColorModel.HSV,
            ColorModel.RGB_STR if as_str else ColorModel.RGB,
            round_output,
        )
        if as_str:
            return cast(str, result)
        return cast(tuple[int, int, int] | tuple[float, float, float], result)

    @staticmethod
    def text_to_shape(
        obj: "Line | Word | Syllable | Char",
        fscx: float | None = None,
        fscy: float | None = None,
    ) -> "Shape":
        """Converts text with given style information to an ASS shape.

        **Tips:** *You can easily create impressive deforming effects.*

        Parameters:
            obj (Line, Word, Syllable or Char): An object of class Line, Word, Syllable or Char.
            fscx (float, optional): The scale_x value for the shape.
            fscy (float, optional): The scale_y value for the shape.

        Returns:
            A Shape object, representing the text with the style format values of the object.

        Examples:
            ..  code-block:: python3

                line = Line.copy(lines[1])
                line.text = "{\\\\an7\\\\pos(%.3f,%.3f)\\\\p1}%s" % (line.left, line.top, Convert.text_to_shape(line))
                io.write_line(line)
        """
        if obj.styleref is None:
            raise ValueError("Object must have a style reference and text content")

        # Obtaining information and editing values of style if requested
        original_scale_x = obj.styleref.scale_x
        original_scale_y = obj.styleref.scale_y

        # Editing temporary the style to properly get the shape
        if fscx is not None:
            obj.styleref.scale_x = fscx
        if fscy is not None:
            obj.styleref.scale_y = fscy

        # Obtaining font information from style and obtaining shape
        font = Font(obj.styleref)
        shape = font.text_to_shape(obj.text)
        # Clearing resources to not let overflow errors take over
        del font

        # Restoring values of style and returning the shape converted
        if fscx is not None:
            obj.styleref.scale_x = original_scale_x
        if fscy is not None:
            obj.styleref.scale_y = original_scale_y
        return shape

    @staticmethod
    def text_to_clip(
        obj: "Line | Word | Syllable | Char",
        an: int = 5,
        fscx: float | None = None,
        fscy: float | None = None,
    ) -> "Shape":
        """Converts text with given style information to an ASS shape, applying some translation/scaling to it since
        it is not possible to position a shape with \\pos() once it is in a clip.

        This is an high level function since it does some additional operations, check text_to_shape for further infromations.

        **Tips:** *You can easily create text masks even for growing/shrinking text without too much effort.*

        Parameters:
            obj (Line, Word, Syllable or Char): An object of class Line, Word, Syllable or Char.
            an (integer, optional): The alignment wanted for the shape.
            fscx (float, optional): The scale_x value for the shape.
            fscy (float, optional): The scale_y value for the shape.

        Returns:
            A Shape object, representing the text with the style format values of the object.

        Examples:
            ..  code-block:: python3

                line = Line.copy(lines[1])
                line.text = "{\\\\an5\\\\pos(%.3f,%.3f)\\\\clip(%s)}%s" % (line.center, line.middle, Convert.text_to_clip(line), line.text)
                io.write_line(line)
        """
        if obj.styleref is None:
            raise ValueError("Object must have a style reference")

        # Checking for errors
        if an < 1 or an > 9:
            raise ValueError("Alignment value must be an integer between 1 and 9")

        # Setting default values
        if fscx is None:
            fscx = obj.styleref.scale_x
        if fscy is None:
            fscy = obj.styleref.scale_y

        # Obtaining text converted to shape
        shape = Convert.text_to_shape(obj, fscx, fscy)

        # Setting mult_x based on alignment
        if an % 3 == 1:  # an=1 or an=4 or an=7
            mult_x = 0
        elif an % 3 == 2:  # an=2 or an=5 or an=8
            mult_x = 1 / 2
        else:
            mult_x = 1

        # Setting mult_y based on alignment
        if an < 4:
            mult_y = 1
        elif an < 7:
            mult_y = 1 / 2
        else:
            mult_y = 0

        # Calculating offsets
        cx = (
            obj.left
            - obj.width * mult_x * (fscx - obj.styleref.scale_x) / obj.styleref.scale_x
        )
        cy = (
            obj.top
            - obj.height * mult_y * (fscy - obj.styleref.scale_y) / obj.styleref.scale_y
        )

        return shape.move(cx, cy)

    @staticmethod
    def text_to_pixels(
        obj: "Line | Word | Syllable | Char",
        supersampling: int = 8,
    ) -> PixelCollection:
        """| Converts text with given style information to a PixelCollection.
        | A pixel data is a dictionary containing 'x' (horizontal position), 'y' (vertical position) and 'alpha' (alpha/transparency).

        It is highly suggested to create a dedicated style for pixels,
        because you will write less tags for line in your pixels, which means less size for your .ass file.

        | The style suggested (named "p" in the example) is:
        | - **an=7 (very important!);**
        | - bord=0;
        | - shad=0;
        | - For Font informations leave whatever the default is;

        **Tips:** *It allows easy creation of text decaying or light effects.*

        Parameters:
            obj (Line, Word, Syllable or Char): An object of class Line, Word, Syllable or Char.
            supersampling (int): Value used for supersampling. Higher value means smoother and more precise anti-aliasing (and more computational time for generation).

        Returns:
            A list of dictionaries representing each individual pixel of the input text styled.

        Examples:
            ..  code-block:: python3

                l.style = "p"
                p_sh = Shape.polygon(4, 1)
                for pixel in Convert.text_to_pixels(l):
                    x, y = math.floor(l.left) + pixel.x, math.floor(l.top) + pixel.y
                    alpha = "\\alpha" + Convert.alpha_dec_to_ass(pixel.alpha) if pixel.alpha != 0 else ""

                    l.text = "{\\p1\\pos(%d,%d)%s}%s" % (x, y, alpha, p_sh)
                    io.write_line(l)
        """
        shape = Convert.text_to_shape(obj).move(obj.left % 1, obj.top % 1)
        return Convert.shape_to_pixels(shape, supersampling)

    @staticmethod
    def shape_to_pixels(
        shape: "Shape", supersampling: int = 8, output_rgba: bool = False
    ) -> PixelCollection:
        """Converts a Shape object to a PixelCollection.

        It is highly suggested to use a dedicated style for pixels,
        because you will write less tags for line in your pixels, which means less size for your .ass file.

        PyonFX provides ``io.insert_pixel_style()`` to take care of this for you,
        so be sure to call it before using this function.

        **Tips:** *As for text, even shapes can decay!*

        Parameters:
            shape (Shape): An object of class Shape.
            supersampling (int): Supersampling factor (≥ 1). Higher values mean smoother anti-aliasing but slower generation.
            output_rgba (bool): If True, output RGBA values instead of ASS color and alpha.

        Returns:
            A ``PixelCollection`` containing ``Pixel`` objects, representing each individual pixel of the input shape.
            Each pixel contains 'x' (horizontal position), 'y' (vertical position) and 'alpha' (alpha/transparency).
        """
        # Validate input
        if supersampling < 1 or not isinstance(supersampling, int):
            raise ValueError(
                "supersampling must be a positive integer (got %r)" % supersampling
            )

        # Convert to Shapely geometry
        multipolygon = shape.to_multipolygon()
        if multipolygon.is_empty:
            return PixelCollection([])

        # Upscale and shift so the bbox is in +ve quadrant
        multipolygon = _shapely_scale(
            multipolygon, xfact=supersampling, yfact=supersampling, origin=(0.0, 0.0)
        )

        min_x, min_y, max_x, max_y = multipolygon.bounds
        shift_x = -1 * (min_x - (min_x % supersampling))
        shift_y = -1 * (min_y - (min_y % supersampling))
        multipolygon = _shapely_translate(multipolygon, xoff=shift_x, yoff=shift_y)

        # Compute high-res grid size (multiple of supersampling)
        _, _, max_x, max_y = multipolygon.bounds
        high_w = int(math.ceil(max_x))
        high_h = int(math.ceil(max_y))
        if high_w % supersampling:
            high_w += supersampling - (high_w % supersampling)
        if high_h % supersampling:
            high_h += supersampling - (high_h % supersampling)

        # Mark which high-res pixels fall inside the geometry (centre sampling)
        xs = np.arange(0.5, high_w + 0.5, 1.0, dtype=np.float64)
        ys = np.arange(0.5, high_h + 0.5, 1.0, dtype=np.float64)
        X, Y = np.meshgrid(xs, ys)
        mask = _shapely_contains(multipolygon, X, Y)

        # Downsample mask to screen resolution
        low_h = high_h // supersampling
        low_w = high_w // supersampling
        mask_rs = mask.reshape(low_h, supersampling, low_w, supersampling)
        coverage_cnt = mask_rs.sum(axis=(1, 3))

        # Convert coverage to alpha
        denom = supersampling * supersampling
        alpha_arr = np.rint((denom - coverage_cnt) * 255 / denom).astype(np.int16)

        # Build output PixelCollection, skipping fully transparent pixels using vectorized selection
        downscale = 1 / supersampling
        shift_x_low = shift_x * downscale
        shift_y_low = shift_y * downscale

        non_transparent = np.argwhere(alpha_arr < 255)
        pixels = [
            Pixel(
                x=int(xi - shift_x_low),
                y=int(yi - shift_y_low),
                alpha=(
                    int(alpha_arr[yi, xi])
                    if output_rgba
                    else Convert.alpha_dec_to_ass(int(alpha_arr[yi, xi]))
                ),
            )
            for yi, xi in non_transparent
        ]

        return PixelCollection(pixels)

    @staticmethod
    def image_to_pixels(
        image_path: str,
        width: int | None = None,
        height: int | None = None,
        skip_transparent: bool = True,
        output_rgba: bool = False,
    ) -> PixelCollection:
        """Converts an image to a PixelCollection.

        Parameters:
            image_path (str): A file path to an image (either absolute or relative to the script).
            width (int, optional): Target width for rescaling. If None, original width is used.
            height (int, optional): Target height for rescaling. If None, original height is used.
                                 If only one dimension is specified, aspect ratio is maintained.
            skip_transparent (bool): If True, skip fully transparent pixels (i.e. alpha == 255).
            output_rgba (bool): If True, output RGBA values instead of ASS color and alpha.

        Returns:
            A ``PixelCollection`` containing ``Pixel`` objects, each containing x, y, color, alpha values.
        """
        dirname = os.path.dirname(os.path.abspath(sys.argv[0]))
        if not os.path.isabs(image_path):
            image_path = os.path.join(dirname, image_path)
        try:
            img = Image.open(image_path)
        except Exception as e:
            raise ValueError(f"Could not open image at '{image_path}': {e}")
        if img.mode != "RGBA":
            img = img.convert("RGBA")

        # Rescale image if width or height is specified
        if width is not None or height is not None:
            try:
                # If only one dimension is specified, maintain aspect ratio
                original_width, original_height = img.size
                if width is not None and height is None:
                    ratio = width / original_width
                    height = int(original_height * ratio)
                elif height is not None and width is None:
                    ratio = height / original_height
                    width = int(original_width * ratio)

                if width is not None and height is not None:
                    img = img.resize((width, height), Image.Resampling.LANCZOS)
            except Exception as e:
                raise ValueError(f"Error resizing image: {e}")

        width, height = img.size
        pixels_data = list(img.getdata())  # type: ignore[arg-type]

        pixels = []
        for i, (r, g, b, a) in enumerate(pixels_data):
            if skip_transparent and a == 0:
                continue
            x = i % width
            y = i // width
            if output_rgba:
                pixel_color = (r, g, b)
                pixel_alpha = 255 - a
            else:
                pixel_color = Convert.color_rgb_to_ass((r, g, b))
                pixel_alpha = Convert.alpha_dec_to_ass(255 - a)
            pixels.append(Pixel(x=x, y=y, color=pixel_color, alpha=pixel_alpha))

        return PixelCollection(pixels)

    @staticmethod
    def oklab_to_rgb(oklab: tuple[float, float, float]) -> tuple[int, int, int]:
        """Converts an OKLab color to sRGB color.

        For more information, see: https://bottosson.github.io/posts/oklab/

        Params:
            oklab (tuple[float, float, float]): An OKLab tuple (L, a, b).

        Returns:
            A tuple of integers representing the RGB color (0-255).
        """
        L, a_val, b_val = oklab

        # OKLab to LMS
        l_ = L + 0.3963377774 * a_val + 0.2158037573 * b_val
        m_ = L - 0.1055613458 * a_val - 0.0638541728 * b_val
        s_ = L - 0.0894841775 * a_val - 1.2914855480 * b_val

        # LMS to linear RGB
        L_lin = l_**3
        M_lin = m_**3
        S_lin = s_**3

        def linear_to_srgb(u: float) -> float:
            if u <= 0.0031308:
                return 12.92 * u
            else:
                return 1.055 * (u ** (1 / 2.4)) - 0.055

        # Linear RGB to sRGB
        r = linear_to_srgb(
            4.0767416621 * L_lin - 3.3077115913 * M_lin + 0.2309699292 * S_lin
        )
        g = linear_to_srgb(
            -1.2684380046 * L_lin + 2.6097574011 * M_lin - 0.3413193965 * S_lin
        )
        b = linear_to_srgb(
            -0.0041960863 * L_lin - 0.7034186147 * M_lin + 1.7076147010 * S_lin
        )

        # Clamp and convert to 8-bit
        r = max(0.0, min(1.0, r))
        g = max(0.0, min(1.0, g))
        b = max(0.0, min(1.0, b))

        return (round(r * 255), round(g * 255), round(b * 255))

    @staticmethod
    def rgb_to_oklab(rgb: tuple[int, int, int]) -> tuple[float, float, float]:
        """Converts an sRGB color to OKLab color.

        For more information, see: https://bottosson.github.io/posts/oklab/

        Params:
            rgb (tuple[int, int, int]): An RGB tuple (0-255).

        Returns:
            A tuple of floats representing the OKLab color (0-1).
        """
        r, g, b = [x / 255 for x in rgb]

        def srgb_to_linear(u: float) -> float:
            if u <= 0.04045:
                return u / 12.92
            else:
                return ((u + 0.055) / 1.055) ** 2.4

        r_lin = srgb_to_linear(r)
        g_lin = srgb_to_linear(g)
        b_lin = srgb_to_linear(b)

        # Linear sRGB to LMS
        L_val = 0.4122214708 * r_lin + 0.5363325363 * g_lin + 0.0514459929 * b_lin
        M_val = 0.2119034982 * r_lin + 0.6806995451 * g_lin + 0.1073969566 * b_lin
        S_val = 0.0883024619 * r_lin + 0.2817188376 * g_lin + 0.6299787005 * b_lin

        # Non-linear adaptation (cube root)
        L_cbrt = L_val ** (1 / 3)
        M_cbrt = M_val ** (1 / 3)
        S_cbrt = S_val ** (1 / 3)

        # LMS to OKLab
        L_ok = 0.2104542553 * L_cbrt + 0.7936177850 * M_cbrt - 0.0040720468 * S_cbrt
        a_ok = 1.9779984951 * L_cbrt - 2.4285922050 * M_cbrt + 0.4505937099 * S_cbrt
        b_ok = 0.0259040371 * L_cbrt + 0.7827717662 * M_cbrt - 0.8086757660 * S_cbrt

        return (L_ok, a_ok, b_ok)
