import os
import sys
import pytest_check as check
from fractions import Fraction
from pyonfx import *
from video_timestamps import FPSTimestamps, RoundingMethod

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
        "{\\k56}{\\1c&HFFFFFF&}su{\\k13}re{\\k22}chi{\\k36}ga{\\k48}u {\\k25\\-Pyon}{\\k34}ko{\\-Pyon\\k33}to{\\k50}ba {\\k15}no {\\k17}u{\\k34}ra {\\k46}ni{\\k33} {\\k28}to{\\k36}za{\\k65}sa{\\1c&HFFFFFF&\\k33\\1c&HFFFFFF&\\k30\\1c&HFFFFFF&}re{\\k51\\-FX}ta{\\k16} {\\k33}ko{\\k33}ko{\\k78}ro {\\k15}no {\\k24}ka{\\k95}gi",
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
    check.almost_equal(lines[5].width, 577.546875, abs=max_deviation)
    check.almost_equal(lines[5].height, 48.0, abs=max_deviation)
    check.almost_equal(lines[5].x, lines[5].center, abs=max_deviation)
    check.almost_equal(lines[5].y, lines[5].top, abs=max_deviation)
    check.almost_equal(lines[5].left, 351.2265625, abs=max_deviation)
    check.almost_equal(lines[5].center, 640.0, abs=max_deviation)
    check.almost_equal(lines[5].right, 928.7734375, abs=max_deviation)
    check.almost_equal(lines[5].top, 250, abs=max_deviation)
    check.almost_equal(lines[5].middle, 274.0, abs=max_deviation)
    check.almost_equal(lines[5].bottom, 298.0, abs=max_deviation)

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
    check.almost_equal(lines[9].width, 1100.34375, abs=max_deviation)
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


def test_syllable_values():
    # Test syllable parsing and field values for a line with karaoke (lines[11])
    syls = lines[11].syls

    # Check number of syllables
    check.equal(len(syls), 27)

    # Check syllables sub-division, including tags and inline_fx
    expected = [
        ("\\k56\\1c&HFFFFFF&", "", "su"),
        ("\\k13", "", "re"),
        ("\\k22", "", "chi"),
        ("\\k36", "", "ga"),
        ("\\k48", "", "u"),
        ("\\k25\\-Pyon", "Pyon", ""),
        ("\\k34", "", "ko"),
        ("\\-Pyon\\k33", "Pyon", "to"),
        ("\\k50", "", "ba"),
        ("\\k15", "", "no"),
        ("\\k17", "", "u"),
        ("\\k34", "", "ra"),
        ("\\k46", "", "ni"),
        ("\\k33", "", ""),
        ("\\k28", "", "to"),
        ("\\k36", "", "za"),
        ("\\k65", "", "sa"),
        ("\\1c&HFFFFFF&\\k33\\1c&HFFFFFF&", "", ""),
        ("\\k30\\1c&HFFFFFF&", "", "re"),
        ("\\k51\\-FX", "FX", "ta"),
        ("\\k16", "", ""),
        ("\\k33", "", "ko"),
        ("\\k33", "", "ko"),
        ("\\k78", "", "ro"),
        ("\\k15", "", "no"),
        ("\\k24", "", "ka"),
        ("\\k95", "", "gi"),
    ]
    actual = [(syl.tags, syl.inline_fx, syl.text) for syl in syls]
    assert (
        actual == expected
    ), f"Syllable parsing mismatch:\nExpected: {expected}\nActual: {actual}"

    # Check first syllable in detail
    syl = syls[0]
    check.equal(syl.i, 0)
    check.equal(syl.word_i, 0)
    check.equal(syl.start_time, 0)
    check.equal(syl.end_time, 560)
    check.equal(syl.duration, 560)
    check.equal(syl.styleref, styles[lines[11].style])
    check.equal(syl.text, "su")
    check.equal(syl.tags, "\\k56\\1c&HFFFFFF&")
    check.equal(syl.inline_fx, "")
    check.equal(syl.prespace, 0)
    check.equal(syl.postspace, 0)
    check.almost_equal(syl.width, 38.359, abs=max_deviation)
    check.almost_equal(syl.height, 48.0, abs=max_deviation)
    check.almost_equal(syl.x, syl.center, abs=max_deviation)
    check.almost_equal(syl.y, syl.top, abs=max_deviation)
    check.almost_equal(syl.left, 169.007, abs=max_deviation)
    check.almost_equal(syl.center, 188.187, abs=max_deviation)
    check.almost_equal(syl.right, 207.367, abs=max_deviation)
    check.almost_equal(syl.top, 650.0, abs=max_deviation)
    check.almost_equal(syl.middle, 674.0, abs=max_deviation)
    check.almost_equal(syl.bottom, 698.0, abs=max_deviation)

    # Check a syllable with inline_fx (e.g., 7th syllable: {\k33\-Pyon}to)
    syl_fx = syls[7]
    check.equal(syl_fx.i, 7)
    check.equal(syl_fx.word_i, 1)
    check.equal(syl_fx.start_time, 2340)
    check.equal(syl_fx.end_time, 2670)
    check.equal(syl_fx.duration, 330)
    check.equal(syl_fx.styleref, styles[lines[11].style])
    check.equal(syl_fx.text, "to")
    check.equal(syl_fx.tags, "\\-Pyon\\k33")
    check.equal(syl_fx.inline_fx, "Pyon")
    check.equal(syl_fx.prespace, 0)
    check.equal(syl_fx.postspace, 0)
    check.almost_equal(syl_fx.width, 38.468, abs=max_deviation)
    check.almost_equal(syl_fx.height, 48.0, abs=max_deviation)


def test_ass_values():
    check.is_true(os.path.samefile(io.path_input, path_ass))
    check.equal(
        os.path.realpath(io.path_output),
        os.path.realpath(
            os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "Output.ass")
        ),
    )
    # io.meta is tested in test_meta_values()
    # io.styles is tested in test_line_values()
    # io.lines is tested in test_line_values()
    check.equal(
        io.input_timestamps,
        FPSTimestamps(RoundingMethod.ROUND, Fraction(1000), Fraction("23.976000")),
    )
