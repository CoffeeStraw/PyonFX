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
    """A collection of static conversion utilities for ASS formatting.

    It contains a variety of methods to convert between different representations used in the ASS format, such as timestamps, colors, text-to-shape transformations, and pixel generation from shapes and images.
    Although all methods are static, this class is maintained as a single unit for backward compatibility with earlier versions of the library.
    """

    @overload
    @staticmethod
    def time(ass_ms: int) -> str: ...

    @overload
    @staticmethod
    def time(ass_ms: str) -> int: ...

    @staticmethod
    def time(ass_ms: int | str) -> int | str:
        """Convert between milliseconds and ASS timestamp.

        It rounds the milliseconds to the nearest centisecond when formatting an ASS timestamp, following the convention used in Aegisub.
        Typically, you won't use this function directly for KFX or typesetting generation.

        Args:
            ass_ms: An integer representing time in milliseconds (must be non-negative) or a string formatted as an ASS timestamp ("H:MM:SS.CS").

        Returns:
            str or int: If an integer is provided, returns a string representing the converted ASS timestamp. If a string is provided, returns an integer representing the time in milliseconds.

        Examples:
            >>> Convert.time(5000)
            '0:00:05.00'
            >>> Convert.time('0:00:05.00')
            5000
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
        """Convert an ASS alpha string to a decimal value.

        Args:
            alpha_ass: A string with the ASS alpha value in the format '&HXX&'.

        Returns:
            int: The decimal value of the alpha component in the range [0, 255].

        Examples:
            >>> Convert.alpha_ass_to_dec("&HFF&")
            255
        """
        match = re.fullmatch(r"&H([0-9A-F]{2})&", alpha_ass)
        if match is None:
            raise ValueError(
                f"Provided ASS alpha string '{alpha_ass}' is not in the expected format '&HXX&'."
            )
        return int(match.group(1), 16)

    @staticmethod
    def alpha_dec_to_ass(alpha_dec: int | float) -> str:
        """Convert a decimal alpha value to an ASS alpha string.

        Args:
            alpha_dec: An integer or float in the range [0, 255] representing an alpha value.

        Returns:
            str: The corresponding ASS alpha string in the format '&HXX&'.

        Examples:
            >>> Convert.alpha_dec_to_ass(255)
            '&HFF&'
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
        """Convert a color value between different color models.

        It supports various formats such as ASS, RGB, RGBA, HSV, and OKLAB.

        Args:
            c: A color value in the input format. This can be a string or a tuple of numbers.
            input_format: A ColorModel enum indicating the format of the input color.
            output_format: A ColorModel enum indicating the desired format of the output color.
            round_output: A boolean that determines if numerical results should be rounded.

        Returns:
            The color converted to the specified output format, either as a string or as a tuple.

        Examples:
            >>> Convert.color("&H0000FF&", ColorModel.ASS, ColorModel.RGB)
            (255, 0, 0)

        See Also:
            [Convert.color_ass_to_rgb](pyonfx.convert.Convert.color_ass_to_rgb), [Convert.color_rgb_to_ass](pyonfx.convert.Convert.color_rgb_to_ass)
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
                match = re.fullmatch(r"#?([0-9A-Fa-f]{2})" * 3, c)
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
                match = re.fullmatch(r"#?([0-9A-Fa-f]{2})" * 4, c)
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
                r, g, b = Convert.color_oklab_to_rgb(c)
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
                L, a, b = Convert.color_rgb_to_oklab((r, g, b))
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
        """Convert an ASS color string to its RGB representation.

        Args:
            color_ass: A string in the ASS color format "&HBBGGRR&".
            as_str: A boolean flag that, if True, returns the color as a hexadecimal string in the format "#RRGGBB"; otherwise returns a tuple (R, G, B).

        Returns:
            The RGB representation of the color either as a tuple of integers or as a hexadecimal string.

        Examples:
            >>> Convert.color_ass_to_rgb("&HABCDEF&")
            (239, 205, 171)
            >>> Convert.color_ass_to_rgb("&HABCDEF&", as_str=True)
            "#EFCDAB"

        See Also:
            [Convert.color_rgb_to_ass](pyonfx.convert.Convert.color_rgb_to_ass)
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
        """Convert an ASS color string to its HSV representation.

        Args:
            color_ass: A string representing the ASS color (format "&HBBGGRR&").
            round_output: A boolean that determines if numerical results should be rounded.

        Returns:
            A tuple representing the HSV values. The values are integers if round_output is True, or floats otherwise.

        Examples:
            >>> Convert.color_ass_to_hsv("&HABCDEF&")
            (30, 28, 94)
            >>> Convert.color_ass_to_hsv("&HABCDEF&", round_output=False)
            (30.000000000000014, 28.451882845188294, 93.72549019607843)

                print(Convert.color_ass_to_hsv("&HABCDEF&"))
                print(Convert.color_ass_to_hsv("&HABCDEF&", round_output=False))

        See Also:
            [Convert.color_rgb_to_hsv](pyonfx.convert.Convert.color_rgb_to_hsv)
        """
        result = Convert.color(color_ass, ColorModel.ASS, ColorModel.HSV, round_output)
        return cast(tuple[int, int, int] | tuple[float, float, float], result)

    @staticmethod
    def color_ass_to_oklab(color_ass: str) -> tuple[float, float, float]:
        """Convert an ASS color string to its OKLab representation.

        Args:
            color_ass: A string containing the ASS color in the format "&HBBGGRR&".

        Returns:
            A tuple of three floats corresponding to the OKLab color values.

        Examples:
            >>> Convert.color_ass_to_oklab("&HABCDEF&")
            (0.8686973182678561, 0.023239204013187575, 0.054516093943155375)

        See Also:
            [Convert.color_oklab_to_rgb](pyonfx.convert.Convert.color_oklab_to_rgb)
        """
        result = Convert.color(color_ass, ColorModel.ASS, ColorModel.OKLAB, round_output=False)
        return cast(tuple[float, float, float], result)

    @staticmethod
    def color_rgb_to_ass(
        color_rgb: str | tuple[int, int, int],
    ) -> str:
        """Convert an RGB color value to its ASS representation.

        Args:
            color_rgb: An RGB color value as a hexadecimal string or a tuple of three integers.

        Returns:
            str: The ASS color string in the format "&HBBGGRR&".

        Examples:
            >>> Convert.color_rgb_to_ass("#ABCDEF")
            "&HEFCDAB&"

        See Also:
            [Convert.color_ass_to_rgb](pyonfx.convert.Convert.color_ass_to_rgb)
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
        """Convert an RGB color value to its HSV representation.

        Args:
            color_rgb: An RGB color value as a hexadecimal string or a tuple of three numbers.
            round_output: A boolean that determines if numerical results should be rounded.

        Returns:
            A tuple representing the HSV values. If round_output is True, the components are integers; otherwise, they are floats.

        Examples:
            >>> Convert.color_rgb_to_hsv("#ABCDEF")
            (210, 28, 94)
            >>> Convert.color_rgb_to_hsv("#ABCDEF", round_output=False)
            (210.0, 28.45, 93.73)

        See Also:
            [Convert.color_hsv_to_rgb](pyonfx.convert.Convert.color_hsv_to_rgb)
        """
        result = Convert.color(
            color_rgb,
            ColorModel.RGB_STR if isinstance(color_rgb, str) else ColorModel.RGB,
            ColorModel.HSV,
            round_output,
        )
        return cast(tuple[int, int, int] | tuple[float, float, float], result)

    @staticmethod
    def color_rgb_to_oklab(
        color_rgb: tuple[int, int, int],
    ) -> tuple[float, float, float]:
        """Convert an sRGB color value to its OKLab representation.

        Args:
            color_rgb: A tuple (R, G, B) with each value in the range [0, 255].

        Returns:
            A tuple of three floats corresponding to the OKLab values (L, a, b) in the range [0, 1].

        Examples:
            >>> Convert.color_rgb_to_oklab((255, 0, 0))
            (0.6279553606145516, 0.22486306106597398, 0.1258462985307351)

        See Also:
            [Convert.color_oklab_to_rgb](pyonfx.convert.Convert.color_oklab_to_rgb)
        """
        r, g, b = [x / 255 for x in color_rgb]

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

    @staticmethod
    def color_hsv_to_ass(
        color_hsv: tuple[int | float, int | float, int | float],
    ) -> str:
        """Convert an HSV color value to its ASS representation.

        Args:
            color_hsv: A tuple (H, S, V) representing the HSV color.

        Returns:
            str: The ASS color string corresponding to the given HSV value.

        Examples:
            >>> Convert.color_hsv_to_ass((100, 100, 100))
            "&H00FF55&"

        See Also:
            [Convert.color_ass_to_hsv](pyonfx.convert.Convert.color_ass_to_hsv)
        """
        result = Convert.color(color_hsv, ColorModel.HSV, ColorModel.ASS)
        return cast(str, result)

    @staticmethod
    def color_hsv_to_rgb(
        color_hsv: tuple[int | float, int | float, int | float],
        as_str: bool = False,
        round_output: bool = True,
    ) -> str | tuple[int, int, int] | tuple[float, float, float]:
        """Convert an HSV color value to its RGB representation.

        Args:
            color_hsv: A tuple representing the HSV color with H in [0, 360), S and V in [0, 100].
            as_str: A boolean flag that, if True, returns the RGB value as a hexadecimal string "#RRGGBB"; otherwise as a tuple (R, G, B).
            round_output: A boolean that determines if numerical results should be rounded.

        Returns:
            Either a tuple (R, G, B) or a string "#RRGGBB" representing the RGB color.

        Examples:
            >>> Convert.color_hsv_to_rgb((100, 100, 100))
            (85, 255, 0)
            >>> Convert.color_hsv_to_rgb((100, 100, 100), as_str=True)
            "#55FF00"
            >>> Convert.color_hsv_to_rgb((100, 100, 100), round_output=False)
            (84.99999999999999, 255.0, 0.0)

        See Also:
            [Convert.color_rgb_to_hsv](pyonfx.convert.Convert.color_rgb_to_hsv)
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
    def color_oklab_to_rgb(
        color_oklab: tuple[float, float, float],
    ) -> tuple[int, int, int]:
        """Convert an OKLab color value to its sRGB representation.

        Args:
            color_oklab: A tuple (L, a, b) representing the OKLab color, with values typically in the range [0, 1].

        Returns:
            A tuple of three integers (R, G, B) in the range [0, 255] representing the sRGB color.

        Examples:
            >>> Convert.color_oklab_to_rgb((0.627, 0.224, 0.125))
            (255, 0, 0)  # example output

        See Also:
            [Convert.color_rgb_to_oklab](pyonfx.convert.Convert.color_rgb_to_oklab)
        """
        L, a_val, b_val = color_oklab

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
    def color_oklab_to_ass(color_oklab: tuple[float, float, float]) -> str:
        """Convert an OKLab color value to its ASS representation.

        Args:
            color_oklab: A tuple of three floats representing the OKLab color.

        Returns:
            str: The ASS color string in the format "&HBBGGRR&" corresponding to the provided OKLab color.

        Examples:
            >>> Convert.color_oklab_to_ass((0.627, 0.224, 0.125))
            "&H00FF55&"  # example output

        See Also:
            [Convert.color_ass_to_oklab](pyonfx.convert.Convert.color_ass_to_oklab)
        """
        result = Convert.color(color_oklab, ColorModel.OKLAB, ColorModel.ASS)
        return cast(str, result)

    @staticmethod
    def text_to_shape(
        obj: "Line | Word | Syllable | Char",
        fscx: float | None = None,
        fscy: float | None = None,
    ) -> "Shape":
        """Convert text with style information to an ASS shape.

        Converting text to a shape converts the text into a detailed geometry representation,
        exposing individual control points that can be manipulated for precise deformations.

        Args:
            obj: An instance of a Line, Word, Syllable, or Char that contains both text content and style information.
            fscx: Optional; a float representing an override for the style's horizontal scale (scale_x) during conversion.
            fscy: Optional; a float representing an override for the style's vertical scale (scale_y) during conversion.

        Returns:
            Shape: An ASS shape object corresponding to the rendered text with applied style attributes.

        Examples:
            >>> l.text = "{\\an7\\pos(%.3f,%.3f)\\p1}%s" % (line.left, line.top, Convert.text_to_shape(line))
            >>> io.write_line(l)

        Notes:
            A known limitation is that the output line must use '\\an7' and '\\pos(.left, .top)' for accurate displacement.

        See Also:
            [Convert.text_to_clip](pyonfx.convert.Convert.text_to_clip)
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
        """Convert text with style information to an ASS shape for clipping.

        Because a shape used in a clip cannot be directly positioned using the \\pos() command,
        the function applies additional translation and scaling to ensure proper alignment.

        Args:
            obj: An instance of Line, Word, Syllable, or Char that carries text content and associated style information.
            an: An integer specifying the desired alignment for the shape. Must be between 1 and 9.
            fscx: Optional; a float overriding the style's horizontal scale (scale_x) during conversion.
            fscy: Optional; a float overriding the style's vertical scale (scale_y) during conversion.

        Returns:
            Shape: An ASS shape object generated from the text, adjusted for clipping use.

        Examples:
            >>> l.text = "{\\an5\\pos(%.3f,%.3f)\\clip(%s)}%s" % (line.center, line.middle, Convert.text_to_clip(line), Shape.circle(20).move(line.center, line.middle))
            >>> io.write_line(l)

        See Also:
            [Convert.text_to_shape](pyonfx.convert.Convert.text_to_shape)
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
        output_rgba: bool = False,
    ) -> PixelCollection:
        """Convert styled text into a pixel representation.

        This conversion is useful for creating effects like decaying text or light effects.

        Args:
            obj: A text object (Line, Word, Syllable, or Char) containing both content and style data.
            supersampling: An integer supersampling factor that controls the anti-aliasing quality. Higher values yield smoother edges but require more processing time.
            output_rgba: A boolean flag indicating the format of the alpha value. If True, the alpha value for each pixel will be a numeric value between 0 and 255; otherwise, it will be returned as an ASS alpha string.

        Returns:
            PixelCollection: A collection of pixels, where each pixel includes x and y coordinates and an alpha value representing transparency.

        Examples:
            >>> io.add_style("p", Ass.PIXEL_STYLE)
            >>> l.style = "p"
            >>> for pixel in Convert.text_to_pixels(l):
            ...     x, y = l.left + pixel.x, l.top + pixel.y
            ...     alpha = "\\alpha" + str(pixel.alpha) if str(pixel.alpha) != "&HFF&" else ""
            ...     l.text = "{\\p1\\pos(%d,%d)%s}%s" % (x, y, alpha, Shape.PIXEL)
            ...     io.write_line(l)

        Notes:
            To optimize the ASS file size, it is recommended to use a dedicated pixel style.
            A pre-made pixel style ([Ass.PIXEL_STYLE](pyonfx.ass_core.Ass.PIXEL_STYLE)) is provided in the Ass class and can be added to your ASS output using the [add_style](pyonfx.ass_core.Ass.add_style) method.

        See Also:
            [Convert.shape_to_pixels](pyonfx.convert.Convert.shape_to_pixels)
        """
        shape = Convert.text_to_shape(obj).move(obj.left % 1, obj.top % 1)
        return Convert.shape_to_pixels(shape, supersampling, output_rgba)

    @staticmethod
    def shape_to_pixels(
        shape: "Shape", supersampling: int = 8, output_rgba: bool = False
    ) -> PixelCollection:
        """Convert a Shape object into a pixel representation.

        This conversion is useful for creating effects like decaying shapes or light effects.

        Args:
            shape: A Shape object representing the geometric outline to be sampled.
            supersampling: An integer (≥ 1) that controls the anti-aliasing resolution. Higher values yield smoother results but increase processing time.
            output_rgba: A boolean flag indicating the format of the alpha value. If True, the alpha value for each pixel will be a numeric value between 0 and 255; otherwise, it will be returned as an ASS alpha string.

        Returns:
            PixelCollection: A collection of Pixel objects, where each pixel includes x and y coordinates and an alpha value representing transparency.

        Examples:
            >>> io.add_style("p", Ass.PIXEL_STYLE)
            >>> l.style = "p"
            >>> for pixel in Convert.shape_to_pixels(Shape.polygon(4, 20)):
            ...     x, y = l.left + pixel.x, l.top + pixel.y
            ...     alpha = "\\alpha" + str(pixel.alpha) if str(pixel.alpha) != "&HFF&" else ""
            ...     l.text = "{\\p1\\pos(%d,%d)%s}%s" % (x, y, alpha, Shape.PIXEL)
            ...     io.write_line(l)

        Notes:
            To optimize the ASS file size, it is recommended to use a dedicated pixel style.
            A pre-made pixel style ([Ass.PIXEL_STYLE](pyonfx.ass_core.Ass.PIXEL_STYLE)) is provided in the Ass class and can be added to your ASS output using the [add_style](pyonfx.ass_core.Ass.add_style) method.

        See Also:
            [Convert.text_to_pixels](pyonfx.convert.Convert.text_to_pixels)
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
        """Convert an image file to a pixel representation.

        Args:
            image_path: A file path to an image (absolute or relative to the script).
            width: Optional; an integer specifying the target width for rescaling. If None, the original width is used.
            height: Optional; an integer specifying the target height for rescaling. If None, the original height is used. If only one dimension is provided, the aspect ratio is preserved.
            skip_transparent: A boolean flag indicating whether fully transparent pixels (alpha == 0) should be skipped.
            output_rgba: A boolean flag indicating the format of the alpha value. If True, each pixel's alpha value will be a number between 0 and 255 and the color as an RGB tuple; otherwise, the pixel's color is an ASS formatted string and the alpha is an ASS alpha string.

        Returns:
            PixelCollection: A collection of Pixel objects, where each pixel includes x and y coordinates and an alpha value representing transparency.

        Examples:
            >>> pixels = Convert.image_to_pixels("path_to_image/sample.png", width=50)
            >>> for pixel in pixels:
            ...     print(pixel.x, pixel.y, pixel.alpha)

        Notes:
            To optimize the ASS file size, it is recommended to use a dedicated pixel style.
            A pre-made pixel style ([Ass.PIXEL_STYLE](pyonfx.ass_core.Ass.PIXEL_STYLE)) is provided in the Ass class and can be added to your ASS output using the [add_style](pyonfx.ass_core.Ass.add_style) method.

        See Also:
            [pyonfx.pixel.PixelCollection.apply_texture](pyonfx.pixel.PixelCollection.apply_texture)
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
