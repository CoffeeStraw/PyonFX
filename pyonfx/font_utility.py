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
"""
This module contains the Font class definition, which has some functions
to help getting informations from a specific font
"""
from __future__ import annotations
import sys
import html
from typing import Any, TYPE_CHECKING

from .shape import Shape

if sys.platform == "win32":
    import win32gui  # type: ignore
    import win32ui  # type: ignore
    import win32con  # type: ignore
elif sys.platform in ["linux", "darwin"] and not "sphinx" in sys.modules:
    import cairo  # type: ignore
    import gi  # type: ignore

    gi.require_version("Pango", "1.0")
    gi.require_version("PangoCairo", "1.0")

    from gi.repository import Pango, PangoCairo  # type: ignore

if TYPE_CHECKING:
    from .ass_core import Style

# CONFIGURATION
FONT_PRECISION = 64  # Font scale for better precision output from native font system
LIBASS_FONTHACK = True  # Scale font data to fontsize? (no effect on windows)
PANGO_SCALE = 1024  # The PANGO_SCALE macro represents the scale between dimensions used for Pango distances and device units.


class Font:
    """
    Font class definition
    """

    def __init__(self, style: Style):
        self.family = style.fontname
        self.bold = style.bold
        self.italic = style.italic
        self.underline = style.underline
        self.strikeout = style.strikeout
        self.size = style.fontsize
        self.xscale = style.scale_x / 100
        self.yscale = style.scale_y / 100
        self.hspace = style.spacing
        self.upscale = FONT_PRECISION
        self.downscale = 1 / FONT_PRECISION

        # Platform-specific attributes (for type checking)
        self.dc: int = 0
        self.pycfont: Any = None
        self.metrics: Any = None
        self.context: Any = None
        self.layout: Any = None
        self.fonthack_scale: float = 0.0

        if sys.platform == "win32":
            # Create device context
            self.dc = win32gui.CreateCompatibleDC(None)
            # Set context coordinates mapping mode
            win32gui.SetMapMode(self.dc, win32con.MM_TEXT)
            # Set context backgrounds to transparent
            win32gui.SetBkMode(self.dc, win32con.TRANSPARENT)
            # Create font handle
            font_spec = {
                "height": int(self.size * self.upscale),
                "width": 0,
                "escapement": 0,
                "orientation": 0,
                "weight": win32con.FW_BOLD if self.bold else win32con.FW_NORMAL,
                "italic": int(self.italic),
                "underline": int(self.underline),
                "strike out": int(self.strikeout),
                "charset": win32con.DEFAULT_CHARSET,
                "out precision": win32con.OUT_TT_PRECIS,
                "clip precision": win32con.CLIP_DEFAULT_PRECIS,
                "quality": win32con.ANTIALIASED_QUALITY,
                "pitch and family": win32con.DEFAULT_PITCH + win32con.FF_DONTCARE,
                "name": self.family,
            }
            self.pycfont = win32ui.CreateFont(font_spec)
            win32gui.SelectObject(self.dc, self.pycfont.GetSafeHandle())
            # Calculate metrics
            self.metrics = win32gui.GetTextMetrics(self.dc)  # type: ignore
        elif sys.platform == "linux" or sys.platform == "darwin":
            surface = cairo.ImageSurface(cairo.Format.A8, 1, 1)

            self.context = cairo.Context(surface)
            self.layout = PangoCairo.create_layout(self.context)

            font_description = Pango.FontDescription()
            font_description.set_family(self.family)
            font_description.set_absolute_size(self.size * self.upscale * PANGO_SCALE)
            font_description.set_weight(
                Pango.Weight.BOLD if self.bold else Pango.Weight.NORMAL
            )
            font_description.set_style(
                Pango.Style.ITALIC if self.italic else Pango.Style.NORMAL
            )

            self.layout.set_font_description(font_description)
            self.metrics = Pango.Context.get_metrics(
                self.layout.get_context(), self.layout.get_font_description()
            )

            if LIBASS_FONTHACK:
                self.fonthack_scale = self.size / (
                    (self.metrics.get_ascent() + self.metrics.get_descent())
                    / PANGO_SCALE
                    * self.downscale
                )
            else:
                self.fonthack_scale = 1
        else:
            raise NotImplementedError

    def __del__(self):
        if sys.platform == "win32":
            win32gui.DeleteObject(self.pycfont.GetSafeHandle())
            win32gui.DeleteDC(self.dc)

    def get_metrics(self) -> tuple[float, float, float, float]:
        if sys.platform == "win32":
            const = self.downscale * self.yscale
            return (
                # 'height': self.metrics['Height'] * const,
                self.metrics["Ascent"] * const,
                self.metrics["Descent"] * const,
                self.metrics["InternalLeading"] * const,
                self.metrics["ExternalLeading"] * const,
            )
        elif sys.platform == "linux" or sys.platform == "darwin":
            const = self.downscale * self.yscale * self.fonthack_scale / PANGO_SCALE
            return (
                # 'height': (self.metrics.get_ascent() + self.metrics.get_descent()) * const,
                self.metrics.get_ascent() * const,
                self.metrics.get_descent() * const,
                0.0,
                self.layout.get_spacing() * const,
            )
        else:
            raise NotImplementedError

    def get_text_extents(self, text: str) -> tuple[float, float]:
        if sys.platform == "win32":
            cx, cy = win32gui.GetTextExtentPoint32(self.dc, text)

            return (
                (cx * self.downscale + self.hspace * len(text)) * self.xscale,
                cy * self.downscale * self.yscale,
            )
        elif sys.platform == "linux" or sys.platform == "darwin":
            if not text:
                return 0.0, 0.0

            def get_rect(new_text):
                self.layout.set_markup(
                    f"<span "
                    f'strikethrough="{str(self.strikeout).lower()}" '
                    f'underline="{"single" if self.underline else "none"}"'
                    f">"
                    f"{html.escape(new_text)}"
                    f"</span>",
                    -1,
                )
                return self.layout.get_pixel_extents()[1]

            width = 0
            for char in text:
                width += get_rect(char).width

            return (
                (width * self.downscale * self.fonthack_scale + self.hspace * len(text))
                * self.xscale,
                get_rect(text).height
                * self.downscale
                * self.yscale
                * self.fonthack_scale,
            )
        else:
            raise NotImplementedError

    def text_to_shape(self, text: str) -> Shape:
        """Convert text to a shape in libass format."""
        if sys.platform not in ("win32", "linux", "darwin"):
            raise NotImplementedError(f"Platform {sys.platform} not supported")

        shape_parts = []
        last_cmd = None

        def add_command(cmd):
            nonlocal last_cmd
            if last_cmd != cmd:
                shape_parts.append(cmd)
                last_cmd = cmd

        def format_point(x, y, x_off=0):
            return (
                Shape.format_value(x * self.xscale * self.downscale + x_off),
                Shape.format_value(y * self.yscale * self.downscale),
            )

        def process_win32_text(text, x_off):
            """Process Windows text using GDI path API."""
            # Create a path in the device context by rendering text
            win32gui.BeginPath(self.dc)
            win32gui.ExtTextOut(self.dc, 0, 0, 0x0, None, text)  # type: ignore
            win32gui.EndPath(self.dc)

            # Extract the path as points and curve types
            points, types = win32gui.GetPath(self.dc)
            win32gui.AbortPath(self.dc)  # Clear the path from DC

            cmd_map = {
                win32con.PT_MOVETO: "m",
                win32con.PT_LINETO: "l",
                win32con.PT_BEZIERTO: "b",
            }

            i = 0
            while i < len(points):
                # Remove close figure flag to get base point type
                pt_type = types[i] & ~win32con.PT_CLOSEFIGURE

                if pt_type in cmd_map:
                    add_command(cmd_map[pt_type])

                    if pt_type in (win32con.PT_MOVETO, win32con.PT_LINETO):
                        shape_parts.extend(
                            format_point(points[i][0], points[i][1], x_off)
                        )
                    elif pt_type == win32con.PT_BEZIERTO:
                        # Bezier curves use 3 consecutive points
                        if i + 2 >= len(points):
                            raise RuntimeError("Unexpected end of BEZIERTO points")
                        for j in range(3):
                            shape_parts.extend(
                                format_point(points[i + j][0], points[i + j][1], x_off)
                            )
                        i += 2  # Skip next 2 points as we processed them
                i += 1

        def process_unix_text(text, x_off):
            """Process Unix text using Pango/Cairo rendering."""
            # Create markup with styling attributes
            markup = (
                f'<span strikethrough="{str(self.strikeout).lower()}" '
                f'underline="{"single" if self.underline else "none"}">'
                f"{html.escape(text)}</span>"
            )

            self.layout.set_markup(markup, -1)

            # Apply scaling and render text to Cairo path
            scale = self.downscale * self.fonthack_scale
            self.context.save()
            self.context.scale(scale * self.xscale, scale * self.yscale)
            PangoCairo.layout_path(self.context, self.layout)  # type: ignore
            self.context.restore()

            # Extract the path data
            path = self.context.copy_path()
            self.context.new_path()  # Clear the path

            # Cairo path types: 0=MOVE_TO, 1=LINE_TO, 2=CURVE_TO
            cmd_map = {0: "m", 1: "l", 2: "b"}

            for path_type, coords in path:
                if path_type in cmd_map:
                    add_command(cmd_map[path_type])

                    if path_type in (0, 1):  # MOVE_TO, LINE_TO
                        shape_parts.extend(
                            [
                                Shape.format_value(coords[0] + x_off),
                                Shape.format_value(coords[1]),
                            ]
                        )
                    elif (
                        path_type == 2
                    ):  # CURVE_TO (cubic bezier with 3 control points)
                        shape_parts.extend(
                            [
                                Shape.format_value(coords[0] + x_off),
                                Shape.format_value(coords[1]),
                                Shape.format_value(coords[2] + x_off),
                                Shape.format_value(coords[3]),
                                Shape.format_value(coords[4] + x_off),
                                Shape.format_value(coords[5]),
                            ]
                        )

        # Process text segments
        process_text = (
            process_win32_text if sys.platform == "win32" else process_unix_text
        )

        if sys.platform == "win32" and not self.hspace:
            # Windows: render entire text at once when no horizontal spacing needed
            process_text(text, 0.0)
        else:
            # Character-by-character processing with proper spacing
            x_pos = 0.0
            for char in text:
                process_text(char, x_pos)
                x_pos += self.get_text_extents(char)[0]

        return Shape(" ".join(shape_parts))
