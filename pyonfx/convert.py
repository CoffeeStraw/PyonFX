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

import re
import math
from .font_utility import Font

class Convert:
    """
    This class is a collection of static methods that will help
    the user to convert everything needed to the ASS format.
    """

    @staticmethod
    def time(ass_ms):
        """Converts between milliseconds and ASS timestamp.

        You can probably ignore that function, you will not make use of it for KFX or typesetting generation.

        Parameters:
            ass_ms (either int or str): If int, than milliseconds are expected, else ASS timestamp as str is expected.

        Returns:
            If milliseconds -> ASS timestamp, else if ASS timestamp -> milliseconds, else ValueError will be raised.
        """
        # Milliseconds?
        if type(ass_ms) is int and ass_ms >= 0:
            return "{:d}:{:02d}:{:02d}.{:02d}".format(
                math.floor(ass_ms / 3600000) % 10,
                math.floor(ass_ms % 3600000 / 60000),
                math.floor(ass_ms % 60000 / 1000),
                math.floor(ass_ms % 1000 / 10))
        # ASS timestamp?
        elif type(ass_ms) is str and re.match(r"^\d:\d+:\d+\.\d+$", ass_ms):
            return int(ass_ms[0]) * 3600000 + int(ass_ms[2:4]) * 60000 + int(ass_ms[5:7]) * 1000 + int(ass_ms[8:10]) * 10
        else:
            raise ValueError("Milliseconds or ASS timestamp expected")

    @staticmethod
    def coloralpha(ass_r_a, g="", b="", a=""):
        """Converts between rgb color &/+ alpha numeric and ASS color &/+ alpha.

        - Passing a string to this function, you want a conversion from ASS color+alpha, ASS color or ASS alpha to integer values;
        - Passing a single number, you want a conversion from ASS alpha value to ASS alpha string;
        - Passing 3 or 4 numbers, you want a conversion from rgb (or rgba) values to ASS color (or ASS color+alpha) string.

        Parameters:
            ass_r_a (int or str): If a str is given, either an ASS color+alpha, ASS color, an ASS alpha string is expected; if an int is given, a value between 0 and 255 (inclusive) is expected.
            g (int, optional): If given, a value between 0 and 255 (inclusive) is expected.
            b (int, optional): If given, a value between 0 and 255 (inclusive) is expected.
            a (int, optional): If given, a value between 0 and 255 (inclusive) is expected.

        Returns:
            According to the parameters, either a tuple containing rgb (or rgba) integer values or a str containing an ASS color+alpha, an ASS color or an ASS alpha.

        Examples:
            ..  code-block:: python3

                print( Convert.coloralpha(0) )
                print( Convert.coloralpha("&HFF&") )

                print( Convert.coloralpha("&H0000FF&") )
                print( Convert.coloralpha(255, 0, 0) )

                print( Convert.coloralpha("&HFF00FF00") )
                print( Convert.coloralpha(0, 255, 0, 255) )

            >>> &H00&
            >>> 255
            >>> (255, 0, 0)
            >>> &H0000FF&
            >>> (0, 255, 0, 255)
            >>> &HFF00FF00
        """
        # Alpha / red numeric?
        if (type(ass_r_a) == int or type(ass_r_a) == float) and ass_r_a >= 0 and ass_r_a <= 255:
            # Green + blue numeric?
            if (type(g) == int or type(g) == float) and g >= 0 and g <= 255 and \
               (type(b) == int or type(b) == float) and b >= 0 and b <= 255:
                # Alpha numeric?
                if (type(a) == int or type(a) == float) and a >= 0 and a <= 255:
                    return f"&H{a:02X}{b:02X}{g:02X}{ass_r_a:02X}"
                else:
                    return f"&H{b:02X}{g:02X}{ass_r_a:02X}&"
            else:
                return f"&H{ass_r_a:02X}&"
        # ASS value?
        elif type(ass_r_a) == str:
            # ASS alpha?
            if re.match(r"^&H[0-9a-fA-F]{2}&$", ass_r_a):
                return int(ass_r_a[2:4], 16)
            # ASS color?
            elif re.match(r"^&H[0-9a-fA-F]{6}&$", ass_r_a):
                return int(ass_r_a[6:8], 16), int(ass_r_a[4:6], 16), int(ass_r_a[2:4], 16)
            # ASS color+alpha (from style definition)?
            elif re.match(r"^&H[0-9a-fA-F]{8}$", ass_r_a):
                return int(ass_r_a[8:10], 16), int(ass_r_a[6:8], 16), int(ass_r_a[4:6], 16), int(ass_r_a[2:4], 16)
            else:
                raise ValueError("Invalid ASS string")
        else:
            raise ValueError("Color, Alpha, Color+Alpha as numeric or ASS expected")

    @staticmethod
    def text_to_shape(obj, fscx=None, fscy=None):
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
                line.text = "{\\\\an7\\\\pos(%.3f,%.3f)\\\\p1}%s" % (line.left, line.top, convert.text_to_shape(line))
                io.write_line(line)
        """
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
    def text_to_clip(obj, an=5, fscx=None, fscy=None):
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
                line.text = "{\\\\an5\\\\pos(%.3f,%.3f)\\\\clip(%s)}%s" % (line.center, line.middle, convert.text_to_clip(line), line.text)
                io.write_line(line)
        """
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
        if an % 3 == 1: # an=1 or an=4 or an=7
            mult_x = 0
        elif an % 3 == 2: # an=2 or an=5 or an=8
            mult_x = 1/2
        else:
            mult_x = 1

        # Setting mult_y based on alignment
        if an < 4:
            mult_y = 1
        elif an < 7:
            mult_y = 1/2
        else:
            mult_y = 0

        # Calculating offsets
        cx = obj.left - obj.width*mult_x * (fscx-obj.styleref.scale_x) / obj.styleref.scale_x
        cy = obj.top - obj.height*mult_y * (fscy-obj.styleref.scale_y) / obj.styleref.scale_y

        return shape.move(cx, cy)

    @staticmethod
    def text_to_pixels(obj, supersampling=8):
        """| Converts text with given style information to a list of pixel data.
        | A pixel data is a dictionary containing 'x' (horizontal position), 'y' (vertical position) and 'alpha' (alpha/transparency).

        It is highly suggested to create a dedicated style for pixels,
        because you will write less tags for line in your pixels, which means less size for your .ass file.

        | The style suggested is:
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

                line = lines[2].copy()
                line.style = "p"
                p_sh = Shape.rectangle()
                for pixel in Convert.text_to_pixels(line):
                    x, y = math.floor(line.left) + pixel['x'], math.floor(line.top) + pixel['y']
                    alpha = "\\alpha" + Convert.coloralpha(pixel['alpha']) if pixel['alpha'] != 255 else ""

                    line.text = "{\\p1\\pos(%d,%d)%s}%s" % (x, y, alpha, p_sh)
                    io.write_line(line)
        """
        shape = Convert.text_to_shape(obj).move(obj.left % 1, obj.top % 1)
        return Convert.shape_to_pixels(shape, supersampling)

    @staticmethod
    def shape_to_pixels(shape, supersampling=8):
        """| Converts a Shape object to a list of pixel data.
        | A pixel data is a dictionary containing 'x' (horizontal position), 'y' (vertical position) and 'alpha' (alpha/transparency).

        It is highly suggested to create a dedicated style for pixels,
        because you will write less tags for line in your pixels, which means less size for your .ass file.

        | The style suggested is:
        | - **an=7 (very important!);**
        | - bord=0;
        | - shad=0;
        | - For Font informations leave whatever the default is;

        **Tips:** *As for text, even shapes can decay!*

        Parameters:
            shape (Shape): An object of class Shape.
            supersampling (int): Value used for supersampling. Higher value means smoother and more precise anti-aliasing (and more computational time for generation).

        Returns:
            A list of dictionaries representing each individual pixel of the input shape.

        Examples:
            ..  code-block:: python3

                line = lines[2].copy()
                line.style = "p"
                p_sh = Shape.rectangle()
                for pixel in Convert.shape_to_pixels(Shape.heart(100)):
                    # Random circle to pixel effect just to show
                    x, y = math.floor(line.left) + pixel['x'], math.floor(line.top) + pixel['y']
                    alpha = "\\alpha" + Convert.coloralpha(pixel['alpha']) if pixel['alpha'] != 255 else ""

                    line.text = "{\\p1\\pos(%d,%d)%s\\fad(0,%d)}%s" % (x, y, alpha, l.dur/4, p_sh)
                    io.write_line(line)
        """
        # Scale values for supersampled rendering
        upscale = supersampling
        downscale = 1 / upscale

        # Upscale shape for later downsampling
        shape.map(lambda x, y: (x*upscale, y*upscale))

        # Bring shape near origin in positive room
        x1, y1, x2, y2 = shape.bounding()
        shift_x, shift_y = -1*(x1 - x1 % upscale), -1*(y1 - y1 % upscale)
        shape.move(shift_x, shift_y)

        # Create image
        width, height = math.ceil((x2 + shift_x) * downscale) * upscale, math.ceil((y2 + shift_y) * downscale) * upscale
        image = [False for i in range(width*height)]

        # Renderer (on binary image with aliasing)
        lines, last_point, last_move = [], {}, {}

        def collect_lines(x, y, typ):
            # Collect lines (points + vectors)
            nonlocal lines, last_point, last_move
            x, y = int(round(x)), int(round(y))  # Use integers to avoid rounding errors

            # Move
            if typ == "m":
                # Close figure with non-horizontal line in image
                if last_move and last_move['y'] != last_point['y'] and not (last_point['y'] < 0 and last_move['y'] < 0) and not (last_point['y'] > height and last_move['y'] > height):
                    lines.append([last_point['x'], last_point['y'], last_move['x'] - last_point['x'], last_move['y'] - last_point['y']])

                last_move = {'x': x, 'y': y}
            # Non-horizontal line in image
            elif last_point and last_point['y'] != y and not (last_point['y'] < 0 and y < 0) and not (last_point['y'] > height and y > height):
                lines.append([last_point['x'], last_point['y'], x - last_point['x'], y - last_point['y']])

            # Remember last point
            last_point = {'x': x, 'y': y}

        shape.flatten().map(collect_lines)

        # Close last figure with non-horizontal line in image
        if last_move and last_move['y'] != last_point['y'] and not (last_point['y'] < 0 and last_move['y'] < 0) and not (last_point['y'] > height and last_move['y'] > height):
            lines.append([last_point['x'], last_point['y'], last_move['x'] - last_point['x'], last_move['y'] - last_point['y']])

        # Calculates line x horizontal line intersection
        def line_x_hline(x, y, vx, vy, y2):
            if vy != 0:
                s = (y2 - y) / vy
                if s >= 0 and s <= 1:
                    return x + s * vx
            return None

        # Scan image rows in shape
        _, y1, _, y2 = shape.bounding()
        for y in range(max(math.floor(y1), 0), min(math.ceil(y2), height)):
            # Collect row intersections with lines
            row_stops = []
            for line in lines:
                cx = line_x_hline(line[0], line[1], line[2], line[3], y + 0.5)
                if cx is not None:
                    row_stops.append([max(0, min(cx, width)), 1 if line[3] > 0 else -1])  # image trimmed stop position & line vertical direction

            # Enough intersections / something to render?
            if len(row_stops) > 1:
                # Sort row stops by horizontal position
                row_stops.sort(key=lambda x: x[0])
                # Render!
                status, row_index = 0, y * width
                for i in range(0, len(row_stops)-1):
                    status = status + row_stops[i][1]
                    if status != 0:
                        for x in range(math.ceil(row_stops[i][0]-0.5), math.floor(row_stops[i+1][0]+0.5)):
                            image[row_index + x] = True

        # Extract pixels from image
        pixels = []
        for y in range(0, height, upscale):
            for x in range(0, width, upscale):
                opacity = 0
                for yy in range(0, upscale):
                    for xx in range(0, upscale):
                        if image[(y+yy) * width + (x+xx)]:
                            opacity = opacity + 255

                if opacity > 0:
                    pixels.append({
                        'alpha': opacity * (downscale * downscale),
                        'x': (x - shift_x) * downscale,
                        'y': (y - shift_y) * downscale
                    })

        return pixels

    @staticmethod
    def image_to_ass(image):
        pass

    @staticmethod
    def image_to_pixels(image):
        pass
