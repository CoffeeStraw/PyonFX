"""
Just a test to show pixels in action, this file will be removed as soon as I prepare the new examples.
"""

from pyonfx import *
import math
import random

io = Ass("in.ass")
meta, styles, lines = io.get_data()
io.add_style("p", Ass.PIXEL_STYLE)


def romaji(line, l):
    off = 6

    for syl in Utils.all_non_empty(line.syls):
        # Leadin Effect
        l.layer = 0

        l.start_time = line.start_time - line.leadin / 2
        l.end_time = line.start_time + syl.start_time

        l.text = "{\\an5\\pos(%.3f,%.3f)\\bord0\\fad(%d,0)}%s" % (
            syl.center,
            syl.middle,
            line.leadin / 2,
            syl.text,
        )

        io.write_line(l)

    l.style = "p"
    for syl in Utils.all_non_empty(line.syls):
        # Main Effect
        l.layer = 1

        l.start_time = line.start_time + syl.start_time
        l.end_time = line.start_time + syl.end_time + 300
        dur = l.end_time - l.start_time

        for pixel in Convert.text_to_pixels(syl):
            x, y = math.floor(syl.left) + pixel.x, math.floor(syl.top) + pixel.y
            x2, y2 = x + random.uniform(-off, off), y + random.uniform(-off, off)
            alpha = f"\\1a{pixel.alpha}" if pixel.alpha != "&H00&" else ""

            l.text = "{\\p1\\move(%d,%d,%d,%d)%s\\fad(0,%d)}%s" % (
                x,
                y,
                x2,
                y2,
                alpha,
                dur / 4,
                Shape.PIXEL,
            )
            io.write_line(l)

    l.start_time = line.start_time
    l.end_time = line.end_time

    for pi, pixel in enumerate(Convert.shape_to_pixels(Shape.heart(50))):
        # Random shape heart to pixel effect just to show this function too
        x, y = (
            math.floor(line.left) - 60 + pixel.x,
            math.floor(line.top) + pixel.y,
        )
        x2, y2 = x + 10 * (-1) ** pi, y + 10 * (-1) ** pi
        alpha = "\\1a" + pixel.alpha if pixel.alpha != "&H00&" else ""

        l.text = "{\\p1\\move(%d,%d,%d,%d)%s\\fad(0,%d)}%s" % (
            x,
            y,
            x2,
            y2,
            alpha,
            line.duration / 4,
            Shape.PIXEL,
        )
        io.write_line(l)


for line in lines:
    # Generating lines
    if not line.comment and line.styleref.alignment >= 7 and line.i <= 3:
        romaji(line, line.copy())

io.save()
io.open_aegisub()
