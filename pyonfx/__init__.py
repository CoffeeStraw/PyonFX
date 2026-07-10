# -*- coding: utf-8 -*-

from .ass_core import Ass, Char, Line, Meta, Style, Syllable, Word
from .convert import ColorModel, Convert
from .events import Event
from .font import Font
from .geometry import (
    bounds_intersect,
    ensure_multipolygon,
    repair_geometry,
    safe_difference,
    safe_intersection,
)
from .pixel import Pixel, PixelCollection
from .shape import Shape, ShapeElement
from .utils import ColorUtility, FrameUtility, Utils
