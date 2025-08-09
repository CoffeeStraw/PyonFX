"""
Tutorial: Frame-by-frame animations

This tutorial demonstrates how to build frame-by-frame effects using:
• FrameUtility for iterating per-frame and easing progress
• Quadratic Bezier curves (via the `bezier` library) for smooth motion paths
• Color and alpha interpolation for subtle highlights and fades

Exercise:
• Tweak Bezier control points to adjust the arc shape
• Try different easing (e.g., "in_quart", "out_cubic") for entry/exit timing
• Increase jitter amplitude or change color targets to vary highlight intensity
"""

import random

import bezier

from pyonfx import Ass, FrameUtility, Line, Syllable, Utils

io = Ass("../../ass/romaji_kanji_translation.ass", vertical_kanji=True)
meta, styles, lines = io.get_data()


@io.track
def leadin_effect(line: Line, syl: Syllable, l: Line):
    # Control points (start above-left, curve, end at syllable center)
    x0, y0 = syl.center - 60.0, syl.middle - 20.0
    x1, y1 = syl.center - 20.0, syl.middle - 50.0
    x2, y2 = syl.center, syl.middle
    curve = bezier.Curve([[x0, x1, x2], [y0, y1, y2]], degree=2)

    # Frame-by-frame movement
    fu = FrameUtility(
        line.start_time - line.leadin // 2, line.start_time, meta.timestamps
    )
    for s, e, i, n in fu:
        l.layer = 0
        l.start_time = s
        l.end_time = e

        # Position (evaluate Bezier curve)
        pct = Utils.accelerate(i / n, "out_quart")
        curve_point = curve.evaluate(pct)
        x, y = float(curve_point[0][0]), float(curve_point[1][0])

        # Alpha (fade-in)
        alpha = fu.interpolate(0, fu.duration, "&HFF&", "&H00&", "out_quart")

        tags = rf"\an5\pos({x:.3f},{y:.3f})\alpha{alpha}"
        l.text = f"{{{tags}}}{syl.text}"

        io.write_line(l)

    # Static until syllable start
    l.layer = 0
    l.start_time = line.start_time
    l.end_time = line.start_time + syl.start_time

    tags = rf"\an5\pos({syl.center:.3f},{syl.middle:.3f})"
    l.text = f"{{{tags}}}{syl.text}"
    io.write_line(l)


@io.track
def highlight_effect(line: Line, syl: Syllable, l: Line):
    # Max amplitude
    max_amp = 5.0

    # Original style values
    style_c1 = line.styleref.color1
    style_c3 = line.styleref.color3

    # Target values
    target_c1 = "&HFFFFFF&"
    target_c3 = "&HABABAB&"

    fu = FrameUtility(
        line.start_time + syl.start_time,
        line.start_time + syl.end_time,
        meta.timestamps,
    )
    for s, e, i, n in fu:
        l.layer = 1
        l.start_time = s
        l.end_time = e

        # Position (jitter)
        amp = fu.add(0, fu.duration / 2, max_amp)
        amp += fu.add(fu.duration / 2, fu.duration, -max_amp)
        pos_x = syl.center + random.uniform(-amp, amp)
        pos_y = syl.middle + random.uniform(-amp, amp)

        # Color
        t1_c1 = fu.interpolate(0, fu.duration / 2, style_c1, target_c1)
        t1_c3 = fu.interpolate(0, fu.duration / 2, style_c3, target_c3)
        t2_c1 = fu.interpolate(fu.duration / 2, fu.duration, t1_c1, style_c1)
        t2_c3 = fu.interpolate(fu.duration / 2, fu.duration, t1_c3, style_c3)

        tags = rf"\an5\pos({pos_x:.3f},{pos_y:.3f})\1c{t2_c1}\3c{t2_c3}"
        l.text = f"{{{tags}}}{syl.text}"

        io.write_line(l)


@io.track
def leadout_effect(line: Line, syl: Syllable, l: Line):
    # Static from syllable end until line end
    l.layer = 0
    l.start_time = line.start_time + syl.end_time
    l.end_time = line.end_time
    tags = rf"\an5\pos({syl.center:.3f},{syl.middle:.3f})"
    l.text = f"{{{tags}}}{syl.text}"
    io.write_line(l)

    # Control points (start at syllable center, curve going downwards)
    x0, y0 = syl.center, syl.middle
    x1, y1 = syl.center - 20.0, syl.middle + 50.0
    x2, y2 = syl.center - 60.0, syl.middle + 20.0
    curve = bezier.Curve([[x0, x1, x2], [y0, y1, y2]], degree=2)

    # Frame-by-frame movement after line end, fading out towards the end
    fu = FrameUtility(line.end_time, line.end_time + line.leadout // 2, meta.timestamps)
    for s, e, i, n in fu:
        l.layer = 0
        l.start_time = s
        l.end_time = e

        # Position (evaluate Bezier curve)
        pct = Utils.accelerate(i / n, "in_quart")
        curve_point = curve.evaluate(pct)
        x, y = float(curve_point[0][0]), float(curve_point[1][0])

        # Alpha (fade-out)
        alpha = fu.interpolate(0, fu.duration, "&H00&", "&HFF&", "in_quart")

        tags = rf"\an5\pos({x:.3f},{y:.3f})\alpha{alpha}"
        l.text = f"{{{tags}}}{syl.text}"

        io.write_line(l)


@io.track
def romaji(line: Line, l: Line):
    for syl in Utils.all_non_empty(line.syls):
        leadin_effect(line, syl, l)
        highlight_effect(line, syl, l)
        leadout_effect(line, syl, l)


# Generating lines
for line in Utils.all_non_empty(lines):
    l = line.copy()
    if line.styleref.alignment >= 7:
        romaji(line, l)

io.save()
io.open_aegisub()
