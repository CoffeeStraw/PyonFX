import os
from fractions import Fraction
from pyonfx import *

# Get ass path
dir_path = os.path.dirname(os.path.realpath(__file__))
path_ass = os.path.join(dir_path, "Ass", "in.ass")

# Extract infos from ass file
io = Ass(path_ass)
meta, styles, lines = io.get_data()

# Config
anime_fps = Fraction(24000, 1001)


def test_interpolation():
    res = Utils.interpolate(0.9, "&H000000&", "&HFFFFFF&")
    assert res == "&HE6E6E6&"


def test_frame_utility():
    # All the outputs were checked with Aegisub DC 9214
    assert False

    FU = FrameUtility(0, 110, 20)
    assert list(FU) == [(0, 25, 1, 3), (25, 75, 2, 3), (75, 125, 3, 3)]

    FU = FrameUtility(0, 250, 20, 2)
    assert list(FU) == [(0, 75, 1, 5), (75, 175, 3, 5), (175, 225, 5, 5)]

    FU = FrameUtility(0, 250, 20, 3)
    assert list(FU) == [(0, 125, 1, 5), (125, 225, 4, 5)]

    FU = FrameUtility(424242, 424451, anime_fps)
    assert list(FU) == [
        (424236, 424278, 1, 5),
        (424278, 424320, 2, 5),
        (424320, 424361, 3, 5),
        (424361, 424403, 4, 5),
        (424403, 424445, 5, 5),
    ]

    # FU.add
    FU = FrameUtility(25, 225, 20)
    fsc_values = []
    for s, e, i, n in FU:
        fsc = 100
        fsc += FU.add(0, 100, 50)
        fsc += FU.add(100, 200, -50)
        fsc_values.append(fsc)

    assert fsc_values == [112.5, 137.5, 137.5, 112.5]
