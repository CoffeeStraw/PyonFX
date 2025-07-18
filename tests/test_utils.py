import os
from fractions import Fraction

from video_timestamps import FPSTimestamps, RoundingMethod

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
    timestamps = FPSTimestamps(RoundingMethod.ROUND, Fraction(1000), Fraction(20))  # type: ignore[attr-defined]
    FU = FrameUtility(0, 110, timestamps)
    assert list(FU) == [(0, 25, 1, 3), (25, 75, 2, 3), (75, 125, 3, 3)]

    FU = FrameUtility(0, 250, timestamps, 2)
    assert list(FU) == [(0, 75, 1, 5), (75, 175, 3, 5), (175, 225, 5, 5)]

    FU = FrameUtility(0, 250, timestamps, 3)
    assert list(FU) == [(0, 125, 1, 5), (125, 225, 4, 5)]

    timestamps = FPSTimestamps(RoundingMethod.ROUND, Fraction(1000), anime_fps)  # type: ignore[attr-defined]
    FU = FrameUtility(424242, 424451, timestamps)
    assert list(FU) == [
        (424236, 424278, 1, 5),
        (424278, 424320, 2, 5),
        (424320, 424362, 3, 5),
        (424362, 424403, 4, 5),
        (424403, 424445, 5, 5),
    ]

    # FU.add
    timestamps = FPSTimestamps(RoundingMethod.ROUND, Fraction(1000), Fraction(20))  # type: ignore[attr-defined]
    FU = FrameUtility(25, 225, timestamps)
    fsc_values = []
    for s, e, i, n in FU:
        fsc = 100
        fsc += FU.add(0, 100, 50)
        fsc += FU.add(100, 200, -50)
        fsc_values.append(fsc)

    assert fsc_values == [112.5, 137.5, 137.5, 112.5]


def test_accelerate_presets():
    from typing import Literal

    # Test points
    points = [0.0, 0.25, 0.5, 0.75, 1.0]
    presets: list[Literal["ease", "ease-in", "ease-out", "ease-in-out"]] = [
        "ease",
        "ease-in",
        "ease-out",
        "ease-in-out",
    ]
    # For each preset, check boundary and monotonicity
    for preset in presets:
        results = [Utils.accelerate(p, preset) for p in points]
        # 0.0 should map to 0.0, 1.0 to 1.0
        assert (
            abs(results[0] - 0.0) < 1e-7
        ), f"{preset} at 0.0 should be 0.0, got {results[0]}"
        assert (
            abs(results[-1] - 1.0) < 1e-7
        ), f"{preset} at 1.0 should be 1.0, got {results[-1]}"
        # Should be monotonic increasing
        for a, b in zip(results, results[1:]):
            assert a <= b, f"{preset} is not monotonic at {a}, {b}"
    # Additionally, check that ease-in starts slow and ease-out ends fast
    ease_in = [Utils.accelerate(p, "ease-in") for p in points]
    ease_out = [Utils.accelerate(p, "ease-out") for p in points]
    # ease-in should be below linear at midpoint, ease-out above
    assert ease_in[2] < 0.5, f"ease-in at 0.5 should be < 0.5, got {ease_in[2]}"
    assert ease_out[2] > 0.5, f"ease-out at 0.5 should be > 0.5, got {ease_out[2]}"
