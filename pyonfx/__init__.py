# -*- coding: utf-8 -*-
"""An easy way to do KFX and complex typesetting based on subtitle format ASS (Advanced Substation Alpha)."""

from .ass_utility import Meta, Style, Line, Word, Syllable, Char, Ass
from .font_utility import Font
from .convert import Convert
from .utils import Utils
from .settings import Settings

__version__ = '0.1.0'
