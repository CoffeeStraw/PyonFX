import os
import sys
import pytest_check as check
from pyonfx import *

# Get ass path used for tests
dir_path = os.path.dirname(os.path.realpath(__file__))
path_ass = os.path.join(dir_path, "Ass", "ass_core.ass")

# Extract infos from ass file
io = Ass(path_ass, vertical_kanji=True)
meta, styles, lines = io.get_data()

# Config
max_deviation = 0.75


def test_meta_values():
    # Tests if all the meta values are taken correctly
    # check.equal(meta.wrap_style, 0)                     # -> not in this .ass, so let's comment this
    # check.equal(meta.scaled_border_and_shadow, True)  # -> not in this .ass, so let's comment this
    check.equal(meta.play_res_x, 1280)
    check.equal(meta.play_res_y, 720)
    # check.equal(meta.audio, "")                         # -> not in this .ass, so let's comment this
    check.equal(meta.video, "?dummy:23.976000:2250:1920:1080:11:135:226:c")


def test_line_values():
    # Comment recognition
    check.equal(lines[0].comment, True)
    check.equal(lines[1].comment, False)

    # Line fields
    check.equal(lines[0].layer, 42)
    check.equal(lines[1].layer, 0)

    check.equal(lines[0].style, "Default")
    check.equal(lines[1].style, "Normal")

    check.equal(lines[0].actor, "Test")
    check.equal(lines[1].actor, "")

    check.equal(lines[0].effect, "Test; Wow")
    check.equal(lines[1].effect, "")

    check.equal(lines[0].margin_l, 1)
    check.equal(lines[1].margin_l, 0)

    check.equal(lines[0].margin_r, 2)
    check.equal(lines[1].margin_r, 0)

    check.equal(lines[0].margin_v, 3)
    check.equal(lines[1].margin_v, 50)

    check.equal(lines[1].start_time, Convert.time("0:00:00.00"))
    check.equal(lines[1].end_time, Convert.time("0:00:09.99"))
    check.equal(
        lines[1].duration, Convert.time("0:00:09.99") - Convert.time("0:00:00.00")
    )

    check.equal(
        lines[11].raw_text,
        "{\\k56}{\\1c&HFFFFFF&}su{\\k13}re{\\k22}chi{\\k36}ga{\\k48}u {\\k25\\-Pyon}{\\k34}ko{\\k33}to{\\k50}ba {\\k15}no {\\k17}u{\\k34}ra {\\k46}ni{\\k33} {\\k28}to{\\k36}za{\\k65}sa{\\1c&HFFFFFF&\\k33\\1c&HFFFFFF&\\k30\\1c&HFFFFFF&}re{\\k51\\-FX}ta{\\k16} {\\k33}ko{\\k33}ko{\\k78}ro {\\k15}no {\\k24}ka{\\k95}gi",
    )
    check.equal(lines[11].text, "surechigau kotoba no ura ni tozasareta kokoro no kagi")

    # Normal style (no bold, italic and with a normal fs)
    check.almost_equal(lines[1].width, 437.75, abs=max_deviation)
    check.almost_equal(lines[1].height, 48.0, abs=max_deviation)
    check.almost_equal(lines[1].ascent, 36.984375, abs=max_deviation)
    check.almost_equal(lines[1].descent, 11.015625, abs=max_deviation)
    if sys.platform == "win32":
        check.equal(lines[1].internal_leading, 13.59375)
        check.equal(lines[1].external_leading, 3.09375)
    check.almost_equal(lines[1].x, lines[1].center, abs=max_deviation)
    check.almost_equal(lines[1].y, lines[1].top, abs=max_deviation)
    check.almost_equal(lines[1].left, 421.125, abs=max_deviation)
    check.almost_equal(lines[1].center, 640.0, abs=max_deviation)
    check.almost_equal(lines[1].right, 858.875, abs=max_deviation)
    check.almost_equal(lines[1].top, 50.0, abs=max_deviation)
    check.almost_equal(lines[1].middle, 74.0, abs=max_deviation)
    check.almost_equal(lines[1].bottom, 98.0, abs=max_deviation)

    # Bold style
    check.almost_equal(lines[2].width, 461.609375, abs=max_deviation)
    check.almost_equal(lines[2].height, 48.0, abs=max_deviation)

    # Italic style
    check.almost_equal(lines[3].width, 437.75, abs=max_deviation)
    check.almost_equal(lines[3].height, 48.0, abs=max_deviation)

    # Bold-italic style
    check.almost_equal(lines[4].width, 461.609375, abs=max_deviation)
    check.almost_equal(lines[4].height, 48.0, abs=max_deviation)

    # Normal-spaced style
    check.almost_equal(lines[5].width, 572.75, abs=max_deviation)
    check.almost_equal(lines[5].height, 48.0, abs=max_deviation)

    # Normal - fscx style
    check.almost_equal(lines[6].width, 612.8499999999999, abs=max_deviation)
    check.almost_equal(lines[6].height, 48.0, abs=max_deviation)

    # Normal - fscy style
    check.almost_equal(lines[7].width, 437.75, abs=max_deviation)
    check.almost_equal(lines[7].height, 67.19999999999999, abs=max_deviation)

    # Normal - Big FS
    check.almost_equal(lines[8].width, 820.796875, abs=max_deviation)
    check.almost_equal(lines[8].height, 90.0, abs=max_deviation)

    # Normal - Big FS - Spaced
    check.almost_equal(lines[9].width, 1090.796875, abs=max_deviation)
    check.almost_equal(lines[9].height, 90.0, abs=max_deviation)

    # Bold - Text with non latin characters (kanji)
    check.almost_equal(lines[10].width, 309.65625, abs=max_deviation)
    check.almost_equal(lines[10].height, 48.0, abs=max_deviation)

    # Bold - Text with some tags
    check.almost_equal(lines[11].width, 941.703125, abs=max_deviation)
    check.almost_equal(lines[11].height, 48.0, abs=max_deviation)

    # Bold - Vertical Text
    check.almost_equal(lines[12].width, 31.546875, abs=max_deviation)
    check.almost_equal(lines[12].height, 396.0, abs=max_deviation)
