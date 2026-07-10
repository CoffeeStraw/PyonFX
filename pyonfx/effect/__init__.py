# PyonFX: An easy way to create KFX (Karaoke Effects) and complex typesetting using the ASS format (Advanced Substation Alpha).
# Copyright (C) 2019-2025 Antonio Strippoli (CoffeeStraw/YellowFlash)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

"""Reusable primitives for building PyonFX effects."""

from .random import derive_seed, random_for
from .timing import retime_line, retime_start_to_syllable, retime_syllable

__all__ = [
    "derive_seed",
    "random_for",
    "retime_line",
    "retime_start_to_syllable",
    "retime_syllable",
]
