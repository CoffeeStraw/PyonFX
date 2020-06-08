# -*- coding: utf-8 -*-
# PyonFX: An easy way to do KFX and complex typesetting based on subtitle format ASS (Advanced Substation Alpha).
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
This file contains the Font class definition, which has some functions
to help getting informations from a specific font
"""
import sys
from .shape import Shape

if sys.platform == "win32":
    import win32gui
    import win32ui
    import win32con

# CONFIGURATION
FONT_PRECISION = 64 # Font scale for better precision output from native font system

class Font:
    """
    Font class definition
    """
    def __init__(self, style):
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

        if sys.platform == "win32":
            # Create device context
            self.dc = win32gui.CreateCompatibleDC(None)
            # Set context coordinates mapping mode
            win32gui.SetMapMode(self.dc, win32con.MM_TEXT)
            # Set context backgrounds to transparent
            win32gui.SetBkMode(self.dc, win32con.TRANSPARENT)
            # Create font handle
            font_spec = {
                'height': int(self.size * self.upscale),
                'width': 0,
                'escapement': 0,
                'orientation': 0,
                'weight': win32con.FW_BOLD if self.bold else win32con.FW_NORMAL,
                'italic': int(self.italic),
                'underline': int(self.underline),
                'strike out': int(self.strikeout),
                'charset': win32con.DEFAULT_CHARSET,
                'out precision': win32con.OUT_TT_PRECIS,
                'clip precision': win32con.CLIP_DEFAULT_PRECIS,
                'quality': win32con.ANTIALIASED_QUALITY,
                'pitch and family': win32con.DEFAULT_PITCH + win32con.FF_DONTCARE,
                'name': self.family
            }
            self.pycfont = win32ui.CreateFont(font_spec)
            win32gui.SelectObject(self.dc, self.pycfont.GetSafeHandle())
        else:
            raise NotImplementedError

    def __del__(self):
        win32gui.DeleteObject(self.pycfont.GetSafeHandle())
        win32gui.DeleteDC(self.dc)

    def get_metrics(self):
        if sys.platform == "win32":
            metrics = win32gui.GetTextMetrics(self.dc)

            return (
                #'height': metrics['Height'] * self.downscale * self.yscale,
                metrics['Ascent'] * self.downscale * self.yscale,
                metrics['Descent'] * self.downscale * self.yscale,
                metrics['InternalLeading'] * self.downscale * self.yscale,
                metrics['ExternalLeading'] * self.downscale * self.yscale
            )
        else:
            raise NotImplementedError

    def get_text_extents(self, text):
        if sys.platform == "win32":
            cx, cy = win32gui.GetTextExtentPoint32(self.dc, text)

            return (
                (cx * self.downscale + self.hspace*(len(text)-1)) * self.xscale,
                cy * self.downscale * self.yscale
            )
        else:
            raise NotImplementedError

    def text_to_shape(self, text):
        if sys.platform == "win32":
            # Calcultating distance between origins of character cells (just in case of spacing)
            # TO BE DONE

            # Add path to device context
            win32gui.BeginPath(self.dc)
            win32gui.ExtTextOut(self.dc, 0, 0, 0x0, None, text)
            win32gui.EndPath(self.dc)
            # Getting Path produced by Microsoft API
            points, type_points = win32gui.GetPath(self.dc)

            # Checking for errors
            if len(points) == 0 or len(points) != len(type_points):
                raise RuntimeError("This should never happen: function win32gui.GetPath has returned something unexpected.\nPlease report this to the developer")

            # Defining variables
            shape, last_type = [], None
            mult_x, mult_y = self.downscale*self.xscale, self.downscale*self.yscale

            # Convert points to shape
            i = 0
            while i < len(points):
                cur_point, cur_type = points[i], type_points[i]

                if cur_type == win32con.PT_MOVETO:
                    if last_type != win32con.PT_MOVETO: # Avoid repetition of command tags
                        shape.append("m")
                        last_type = cur_type
                    shape.extend([
                        Shape.format_value(cur_point[0]*mult_x),
                        Shape.format_value(cur_point[1]*mult_y)
                    ])
                    i += 1
                elif cur_type == win32con.PT_LINETO or cur_type == (win32con.PT_LINETO | win32con.PT_CLOSEFIGURE):
                    if last_type != win32con.PT_LINETO: # Avoid repetition of command tags
                        shape.append("l")
                        last_type = cur_type
                    shape.extend([
                        Shape.format_value(cur_point[0]*mult_x),
                        Shape.format_value(cur_point[1]*mult_y)
                    ])
                    i += 1
                elif cur_type == win32con.PT_BEZIERTO or cur_type == (win32con.PT_BEZIERTO | win32con.PT_CLOSEFIGURE):
                    if last_type != win32con.PT_BEZIERTO: # Avoid repetition of command tags
                        shape.append("b")
                        last_type = cur_type
                    shape.extend([
                        Shape.format_value(cur_point[0]*mult_x),
                        Shape.format_value(cur_point[1]*mult_y),
                        Shape.format_value(points[i+1][0]*mult_x),
                        Shape.format_value(points[i+1][1]*mult_y),
                        Shape.format_value(points[i+2][0]*mult_x),
                        Shape.format_value(points[i+2][1]*mult_y)
                    ])
                    i += 3
                else: # If there is an invalid type -> skip, for safeness
                    i += 1

            # Clear device context path
            win32gui.AbortPath(self.dc)

            return Shape(' '.join(shape))
        else:
            raise NotImplementedError
