import os
import sys
from fractions import Fraction
import pytest_check as check
from pyonfx import *

# Get ass path
dir_path = os.path.dirname(os.path.realpath(__file__))
path_ass = os.path.join(dir_path, "Ass", "in.ass")

# Extract infos from ass file
io = Ass(path_ass)
meta, styles, lines = io.get_data()

# Config
anime_fps = Fraction(24000, 1001)
max_deviation = 3


def test_ms_to_frames():
    # All the outputs were checked with Aegisub DC 9214
    # Test with dummy video
    assert Convert.ms_to_frames(0, 1, True) == 0
    assert Convert.ms_to_frames(0, 1, False) == -1
    assert Convert.ms_to_frames(1, 1, True) == 1
    assert Convert.ms_to_frames(1, 1, False) == 0

    assert Convert.ms_to_frames(1000, 1, True) == 1
    assert Convert.ms_to_frames(1001, 1, True) == 2
    assert Convert.ms_to_frames(1000, 1, False) == 0
    assert Convert.ms_to_frames(1001, 1, False) == 1

    # Test with an anime video at 23.976 fps
    assert Convert.ms_to_frames(0, anime_fps, True) == 0
    assert Convert.ms_to_frames(0, anime_fps, False) == -1
    assert Convert.ms_to_frames(20, anime_fps, True) == 1
    assert Convert.ms_to_frames(60, anime_fps, False) == 1
    assert Convert.ms_to_frames(41690, anime_fps, True) == 1000
    assert Convert.ms_to_frames(41730, anime_fps, False) == 1000


def test_frames_to_ms():
    # All the outputs were checked with Aegisub DC 9214
    # Test with dummy video
    assert (
        Convert.frames_to_ms(0, 1, True) == 0
    )  # Should be -500, but negative ms don't exist
    assert Convert.frames_to_ms(0, 1, False) == 500
    assert Convert.frames_to_ms(1, 1, True) == 500
    assert Convert.frames_to_ms(1, 1, False) == 1500

    # Test with an anime video at 23.976 fps
    assert Convert.frames_to_ms(0, anime_fps, True) == 0
    assert Convert.frames_to_ms(0, anime_fps, False) == 21
    assert Convert.frames_to_ms(1, anime_fps, True) == 21
    assert Convert.frames_to_ms(1, anime_fps, False) == 63
    assert Convert.frames_to_ms(1000, anime_fps, True) == 41687
    assert Convert.frames_to_ms(1000, anime_fps, False) == 41729


def test_move_ms_to_frame():
    # All the outputs were checked with Aegisub DC 9214
    # Test with dummy video
    assert Convert.move_ms_to_frame(0, 1, True) == 0
    assert Convert.move_ms_to_frame(96, 1, True) == 500
    assert Convert.move_ms_to_frame(590, 1, True) == 500
    assert Convert.move_ms_to_frame(1001, 1, True) == 1500

    assert Convert.move_ms_to_frame(0, 1, False) == 0
    assert Convert.move_ms_to_frame(96, 1, False) == 500
    assert Convert.move_ms_to_frame(590, 1, False) == 500
    assert Convert.move_ms_to_frame(1001, 1, False) == 1500


def test_coloralpha():
    # -- Test alpha conversion functions --
    assert Convert.alpha_ass_to_dec("&HFF&") == 255
    assert Convert.alpha_dec_to_ass(255) == "&HFF&"

    # -- Test conversion from and to rgba --
    assert Convert.color((0, 255, 0, 255), ColorModel.RGBA, ColorModel.RGBA) == (
        0,
        255,
        0,
        255,
    )
    assert (
        Convert.color("#00FF00FF", ColorModel.RGBA_STR, ColorModel.RGBA_STR)
        == "#00FF00FF"
    )

    # -- Test conversion to rgba --
    # Test ass (bgr) -> rgba conversion
    assert Convert.color("&H00FF00&", ColorModel.ASS, ColorModel.RGBA) == (
        0,
        255,
        0,
        255,
    )
    assert (
        Convert.color("&H00FF00&", ColorModel.ASS, ColorModel.RGBA_STR) == "#00FF00FF"
    )

    # Test ass (abgr) -> rgba conversion
    assert Convert.color("&HFF00FF00", ColorModel.ASS_STYLE, ColorModel.RGBA) == (
        0,
        255,
        0,
        255,
    )
    assert (
        Convert.color("&HFF00FF00", ColorModel.ASS_STYLE, ColorModel.RGBA_STR)
        == "#00FF00FF"
    )

    # Test rgb -> rgba conversion
    assert Convert.color((0, 255, 0), ColorModel.RGB, ColorModel.RGBA) == (
        0,
        255,
        0,
        255,
    )
    assert (
        Convert.color("#00FF00", ColorModel.RGB_STR, ColorModel.RGBA_STR) == "#00FF00FF"
    )

    # Test hsv -> rgba conversion
    assert Convert.color((0, 100, 100), ColorModel.HSV, ColorModel.RGBA) == (
        255,
        0,
        0,
        255,
    )
    assert (
        Convert.color((0, 100, 100), ColorModel.HSV, ColorModel.RGBA_STR) == "#FF0000FF"
    )
    assert Convert.color((0, 50, 100), ColorModel.HSV, ColorModel.RGBA) == (
        255,
        128,
        128,
        255,
    )
    assert (
        Convert.color((0, 50, 100), ColorModel.HSV, ColorModel.RGBA_STR) == "#FF8080FF"
    )
    assert Convert.color(
        (0, 50, 100), ColorModel.HSV, ColorModel.RGBA, round_output=False
    ) == (255.0, 127.5, 127.5, 255.0)

    # -- Test conversion from rgba --
    # Test rgba -> ass (bgr) conversion
    assert (
        Convert.color((0, 255, 0, 255), ColorModel.RGBA, ColorModel.ASS) == "&H00FF00&"
    )
    assert (
        Convert.color("#00FF00FF", ColorModel.RGBA_STR, ColorModel.ASS) == "&H00FF00&"
    )

    # Test rgba -> ass (abgr) conversion
    assert (
        Convert.color((0, 255, 0, 255), ColorModel.RGBA, ColorModel.ASS_STYLE)
        == "&HFF00FF00"
    )
    assert (
        Convert.color("#00FF00FF", ColorModel.RGBA_STR, ColorModel.ASS_STYLE)
        == "&HFF00FF00"
    )

    # Test rgba -> rgba conversion
    assert Convert.color((0, 255, 0, 255), ColorModel.RGBA, ColorModel.RGB) == (
        0,
        255,
        0,
    )
    assert (
        Convert.color("#00FF00FF", ColorModel.RGBA_STR, ColorModel.RGB_STR) == "#00FF00"
    )

    # Test rgba -> hsv conversion
    assert Convert.color((255, 0, 0, 255), ColorModel.RGBA, ColorModel.HSV) == (
        0,
        100,
        100,
    )
    assert Convert.color("#FF0000FF", ColorModel.RGBA_STR, ColorModel.HSV) == (
        0,
        100,
        100,
    )
    assert Convert.color(
        (0, 255 / 64, 255 / 64, 255), ColorModel.RGBA, ColorModel.HSV
    ) == (180, 100, 2)
    assert Convert.color(
        (0, 255 / 64, 255 / 64, 255),
        ColorModel.RGBA,
        ColorModel.HSV,
        round_output=False,
    ) == (180.0, 100.0, 1.5625)

    # -- Test color helper functions --
    # Test ass (bgr) -> rgb conversion
    assert Convert.color_ass_to_rgb("&H0000FF&") == (255, 0, 0)
    assert Convert.color_ass_to_rgb("&H0000FF&", as_str=True) == "#FF0000"

    # Test ass (bgr) -> hsv conversion
    assert Convert.color_ass_to_hsv("&H0000FF&") == (0, 100, 100)

    # Test rgb -> ass (bgr) conversion
    assert Convert.color_rgb_to_ass((255, 0, 0)) == "&H0000FF&"
    assert Convert.color_rgb_to_ass("#FF0000") == "&H0000FF&"

    # Test rgb -> hsv conversion
    assert Convert.color_rgb_to_hsv((255, 0, 0)) == (0, 100, 100)
    assert Convert.color_rgb_to_hsv("#FF0000") == (0, 100, 100)
    assert Convert.color_rgb_to_hsv((0, 255 / 64, 255 / 64)) == (180, 100, 2)
    assert Convert.color_rgb_to_hsv((0, 255 / 64, 255 / 64), round_output=False) == (
        180.0,
        100.0,
        1.5625,
    )

    # Test hsv -> ass (bgr) conversion
    assert Convert.color_hsv_to_ass((0, 100, 100)) == "&H0000FF&"

    # Test hsv -> rgb conversion
    assert Convert.color_hsv_to_rgb((0, 100, 100)) == (255, 0, 0)
    assert Convert.color_hsv_to_rgb((0, 100, 100), as_str=True) == "#FF0000"
    assert Convert.color_hsv_to_rgb((0, 50, 100)) == (255, 128, 128)
    assert Convert.color_hsv_to_rgb((0, 50, 100), as_str=True) == "#FF8080"
    assert Convert.color_hsv_to_rgb((0, 50, 100), round_output=False) == (
        255.0,
        127.5,
        127.5,
    )


def test_text_to_shape():
    shape = Convert.text_to_shape(lines[1].syls[0])

    if sys.platform == "win32":
        assert shape == Shape(
            "m 14.938 23.422 b 13.031 22.562 11.156 22.125 9.328 22.125 7.219 22.125 6.156 22.734 6.156 23.984 6.156 24.578 6.391 25.031 6.844 25.359 7.312 25.672 8.109 25.922 9.25 26.078 11.797 26.422 13.625 27.078 14.719 28.047 15.828 29 16.375 30.328 16.375 32 16.375 33.625 15.734 34.922 14.453 35.891 13.172 36.844 11.375 37.328 9.078 37.328 6.312 37.328 3.844 36.75 1.688 35.609 l 2.547 32.234 b 4.5 33.359 6.594 33.922 8.844 33.922 10.844 33.922 11.828 33.266 11.828 31.922 11.828 31.312 11.625 30.844 11.219 30.516 10.797 30.203 10 29.938 8.812 29.766 6.234 29.328 4.422 28.641 3.375 27.734 2.297 26.797 1.75 25.516 1.75 23.906 1.781 22.312 2.406 21.047 3.641 20.125 4.891 19.203 6.703 18.75 9.078 18.75 11.469 18.75 13.703 19.188 15.797 20.062 l 14.938 23.422 m 24.672 19.094 l 24.672 29.766 b 24.672 31.297 24.875 32.344 25.312 32.906 25.734 33.469 26.453 33.75 27.484 33.75 28.5 33.75 29.422 33.25 30.25 32.219 31.062 31.203 31.484 30 31.484 28.625 l 31.484 19.094 35.953 19.094 35.953 36.984 31.797 36.984 31.688 34.469 31.625 34.469 b 30.938 35.375 30.078 36.062 29.078 36.578 28.062 37.078 27.016 37.328 25.938 37.328 24 37.328 22.562 36.781 21.641 35.656 20.719 34.547 20.266 32.734 20.266 30.203 l 20.266 19.094 24.672 19.094"
        )
    elif sys.platform == "linux" or sys.platform == "darwin":
        i = 0
        expectedShape = Shape(
            "m 14.938 23.621 b 13.031 22.758 11.16 22.324 9.328 22.324 7.211 22.324 6.156 22.918 6.156 24.105 6.156 24.691 6.383 25.137 6.844 25.449 7.301 25.762 8.102 25.992 9.25 26.137 11.801 26.48 13.625 27.117 14.719 28.043 15.82 28.961 16.375 30.23 16.375 31.855 16.375 33.418 15.734 34.668 14.453 35.605 13.172 36.535 11.379 36.996 9.078 36.996 6.305 36.996 3.844 36.43 1.688 35.293 l 2.547 32.027 b 4.492 33.102 6.594 33.637 8.844 33.637 10.832 33.637 11.828 32.992 11.828 31.699 11.828 31.105 11.617 30.66 11.203 30.355 10.797 30.043 10 29.801 8.812 29.621 6.238 29.195 4.426 28.539 3.375 27.652 2.289 26.746 1.75 25.523 1.75 23.98 1.781 22.43 2.41 21.211 3.641 20.324 4.879 19.441 6.691 18.996 9.078 18.996 11.461 18.996 13.703 19.43 15.797 20.293 m 24.676 18.996 l 24.676 29.527 b 24.676 31.039 24.883 32.074 25.301 32.637 25.727 33.191 26.457 33.465 27.489 33.465 28.496 33.465 29.414 32.961 30.239 31.949 31.071 30.941 31.489 29.758 31.489 28.402 l 31.489 18.996 35.957 18.996 35.957 36.996 31.801 36.996 31.692 34.246 31.629 34.246 b 30.942 35.113 30.09 35.789 29.082 36.277 28.071 36.758 27.024 36.996 25.942 36.996 23.993 36.996 22.559 36.449 21.645 35.355 20.727 34.254 20.27 32.457 20.27 29.965 l 20.27 18.996"
        )
        expectedList = []

        expectedShape.map(lambda x, y: expectedList.extend([x, y]))

        def equal(x, y):
            nonlocal i
            check.almost_equal(x, expectedList[i], abs=max_deviation)
            check.almost_equal(y, expectedList[i + 1], abs=max_deviation)
            i += 2

        shape.map(equal)
    else:
        raise NotImplementedError
