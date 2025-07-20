# PyonFX: An easy way to create KFX (Karaoke Effects) and complex typesetting using the ASS format (Advanced Substation Alpha).
# Copyright (C) 2019-2025 Antonio Strippoli (CoffeeStraw/YellowFlash)
#                         and contributors (https://github.com/CoffeeStraw/PyonFX/graphs/contributors)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyonFX is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program. If not, see http://www.gnu.org/licenses/.

import copy
import itertools
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, fields
from fractions import Fraction
from pathlib import Path
from typing import Any, Callable

from tabulate import tabulate
from video_timestamps import (
    ABCTimestamps,
    FPSTimestamps,
    RoundingMethod,
    VideoTimestamps,
)

from .convert import Convert
from .font import Font


@dataclass(slots=True)
class Meta:
    """Meta object contains informations about the Ass.

    More info about each of them can be found on http://docs.aegisub.org/manual/Styles
    """

    wrap_style: int | None = None
    """Determines how line breaking is applied to the subtitle line."""

    scaled_border_and_shadow: bool | None = None
    """Determines if script resolution (True) or video resolution (False) should be used to scale border and shadow."""

    play_res_x: int | None = None
    """Video width resolution."""

    play_res_y: int | None = None
    """Video height resolution."""

    audio: str | None = None
    """Loaded audio file path (absolute)."""

    video: str | None = None
    """Loaded video file path (absolute)."""

    timestamps: ABCTimestamps | None = None
    """Timestamps associated to the video file."""

    def parse_line(self, line: str, ass_path: str) -> str:
        """Parses a single ASS line and update the relevant fields.

        Returns the updated line.
        """
        line = line.strip()

        if not line:
            pass
        elif match := re.match(r"WrapStyle:\s*(\d+)$", line):
            self.wrap_style = int(match.group(1))
        elif match := re.match(r"ScaledBorderAndShadow:\s*(.+)$", line):
            self.scaled_border_and_shadow = match.group(1).strip().lower() == "yes"
        elif match := re.match(r"PlayResX:\s*(\d+)$", line):
            self.play_res_x = int(match.group(1))
        elif match := re.match(r"PlayResY:\s*(\d+)$", line):
            self.play_res_y = int(match.group(1))
        elif match := re.match(r"Audio File:\s*(.*)$", line):
            self.audio = _resolve_path(ass_path, match.group(1).strip())
            line = f"Audio File: {self.audio}"
        elif match := re.match(r"Video File:\s*(.*)$", line):
            # Parse video file path
            match_group = str(match.group(1)).strip()
            is_dummy = match_group.startswith("?dummy")
            self.video = (
                match_group if is_dummy else _resolve_path(ass_path, match_group)
            )

            line = f"Video File: {self.video}"

            # Set up timestamps based on video file
            if os.path.isfile(self.video):
                self.timestamps = VideoTimestamps.from_video_file(Path(self.video))
            elif is_dummy:
                # Parse dummy video format: ?dummy:fps:duration
                parts = self.video.split(":")
                if len(parts) >= 2:
                    fps_str = parts[1]
                    fps = Fraction(fps_str)
                    self.timestamps = FPSTimestamps(
                        RoundingMethod.ROUND, Fraction(1000), fps, Fraction(0)  # type: ignore[attr-defined]
                    )

        return line + "\n"

    def serialize(self) -> tuple[list[str], list[str]]:
        """Serializes the meta object into 2 lists of ASS lines:
        - The first list contains the lines that should be inserted into the [Script Info] section.
        - The second list contains the lines that should be inserted into the [Aegisub Project Garbage] section.
        """
        script_info_lines = []
        if self.wrap_style is not None:
            script_info_lines.append(f"WrapStyle: {self.wrap_style}")
        if self.scaled_border_and_shadow is not None:
            script_info_lines.append(
                f"ScaledBorderAndShadow: {'Yes' if self.scaled_border_and_shadow else 'No'}"
            )
        if self.play_res_x is not None:
            script_info_lines.append(f"PlayResX: {self.play_res_x}")
        if self.play_res_y is not None:
            script_info_lines.append(f"PlayResY: {self.play_res_y}")

        # Append a newline to each Script Info line
        script_info_lines = [f"{line}\n" for line in script_info_lines]

        garbage_lines = []
        if self.audio is not None:
            garbage_lines.append(f"Audio File: {self.audio}")
        if self.video is not None:
            garbage_lines.append(f"Video File: {self.video}")

        # Append a newline to each Aegisub Project Garbage line
        garbage_lines = [f"{line}\n" for line in garbage_lines]

        return script_info_lines, garbage_lines


@dataclass(slots=True)
class Style:
    """Style object contains a set of typographic formatting rules that is applied to dialogue lines."""

    name: str
    """Style name."""
    fontname: str
    """Font name."""
    fontsize: float
    """Font size in points."""
    color1: str
    """Primary color (fill)."""
    alpha1: str
    """Transparency of color1."""
    color2: str
    """Secondary color (for karaoke effect)."""
    alpha2: str
    """Transparency of color2."""
    color3: str
    """Outline (border) color."""
    alpha3: str
    """Transparency of color3."""
    color4: str
    """Shadow color."""
    alpha4: str
    """Transparency of color4."""
    bold: bool
    """Whether the font is bold."""
    italic: bool
    """Whether the font is italic."""
    underline: bool
    """Whether the font is underlined."""
    strikeout: bool
    """Whether the font is struck out."""
    scale_x: float
    """Horizontal text scaling (percentage)."""
    scale_y: float
    """Vertical text scaling (percentage)."""
    spacing: float
    """Horizontal spacing between letters."""
    angle: float
    """Text rotation angle (degrees)."""
    border_style: bool
    """True for opaque box, False for standard outline."""
    outline: float
    """Border thickness."""
    shadow: float
    """Shadow offset distance."""
    alignment: int
    """Text alignment (ASS alignment code)."""
    margin_l: int
    """Left margin (pixels)."""
    margin_r: int
    """Right margin (pixels)."""
    margin_v: int
    """Vertical margin (pixels)."""
    encoding: int
    """Font encoding/codepage."""

    @classmethod
    def from_ass_line(cls, line: str) -> "Style":
        """Parses a single ASS line and returns the corresponding Style object."""
        style_match = re.match(r"Style:\s*(.+)$", line)
        if not style_match:
            raise ValueError(f"Invalid style line: {line}")

        # Parse style fields
        #   Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour,
        #   Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle,
        #   BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
        style_fields = [field.strip() for field in style_match.group(1).split(",")]

        return cls(
            name=style_fields[0],
            fontname=style_fields[1],
            fontsize=float(style_fields[2]),
            color1=f"&H{style_fields[3][4:]}&",
            alpha1=f"{style_fields[3][:4]}&",
            color2=f"&H{style_fields[4][4:]}&",
            alpha2=f"{style_fields[4][:4]}&",
            color3=f"&H{style_fields[5][4:]}&",
            alpha3=f"{style_fields[5][:4]}&",
            color4=f"&H{style_fields[6][4:]}&",
            alpha4=f"{style_fields[6][:4]}&",
            bold=style_fields[7] == "-1",
            italic=style_fields[8] == "-1",
            underline=style_fields[9] == "-1",
            strikeout=style_fields[10] == "-1",
            scale_x=float(style_fields[11]),
            scale_y=float(style_fields[12]),
            spacing=float(style_fields[13]),
            angle=float(style_fields[14]),
            border_style=style_fields[15] == "3",
            outline=float(style_fields[16]),
            shadow=float(style_fields[17]),
            alignment=int(style_fields[18]),
            margin_l=int(style_fields[19]),
            margin_r=int(style_fields[20]),
            margin_v=int(style_fields[21]),
            encoding=int(style_fields[22]),
        )

    def serialize(self, style_name: str) -> str:
        """Serializes a Style object into an ASS style line."""
        bold = "-1" if self.bold else "0"
        italic = "-1" if self.italic else "0"
        underline = "-1" if self.underline else "0"
        strikeout = "-1" if self.strikeout else "0"
        border = "3" if self.border_style else "1"
        fontsize = (
            str(int(self.fontsize))
            if self.fontsize == int(self.fontsize)
            else str(self.fontsize)
        )
        scale_x = (
            str(int(self.scale_x))
            if self.scale_x == int(self.scale_x)
            else str(self.scale_x)
        )
        scale_y = (
            str(int(self.scale_y))
            if self.scale_y == int(self.scale_y)
            else str(self.scale_y)
        )
        spacing = (
            str(int(self.spacing))
            if self.spacing == int(self.spacing)
            else str(self.spacing)
        )
        angle = (
            str(int(self.angle)) if self.angle == int(self.angle) else str(self.angle)
        )
        outline_width = (
            str(int(self.outline))
            if self.outline == int(self.outline)
            else str(self.outline)
        )
        shadow = (
            str(int(self.shadow))
            if self.shadow == int(self.shadow)
            else str(self.shadow)
        )
        primary = f"&H{self.alpha1}{self.color1}"
        secondary = f"&H{self.alpha2}{self.color2}"
        outline_col = f"&H{self.alpha3}{self.color3}"
        back = f"&H{self.alpha4}{self.color4}"
        style_line = (
            f"Style: {style_name},{self.fontname},{fontsize},{primary},{secondary},"
            f"{outline_col},{back},{bold},{italic},{underline},{strikeout},"
            f"{scale_x},{scale_y},{spacing},{angle},{border},{outline_width},"
            f"{shadow},{self.alignment},{self.margin_l},{self.margin_r},"
            f"{self.margin_v},{self.encoding}\n"
        )
        return style_line


@dataclass(slots=True)
class Char:
    """Char object contains information about a single character in a line."""

    i: int
    """Character index in the line."""
    word_i: int
    """Index of the word this character belongs to."""
    syl_i: int
    """Index of the syllable this character belongs to."""
    syl_char_i: int
    """Index of the character within its syllable."""
    start_time: int
    """Start time (ms) of the character."""
    end_time: int
    """End time (ms) of the character."""
    duration: int
    """Duration (ms) of the character."""
    styleref: Style
    """Reference to the Style object for this character's line."""
    text: str
    """The character itself as a string."""
    inline_fx: str
    """Inline effect for the character (from \\\\-EFFECT tag)."""
    width: float
    """Width of the character (pixels)."""
    height: float
    """Height of the character (pixels)."""
    x: float
    """Horizontal position of the character (pixels)."""
    y: float
    """Vertical position of the character (pixels)."""
    left: float
    """Left position of the character (pixels)."""
    center: float
    """Center position of the character (pixels)."""
    right: float
    """Right position of the character (pixels)."""
    top: float
    """Top position of the character (pixels)."""
    middle: float
    """Middle position of the character (pixels)."""
    bottom: float
    """Bottom position of the character (pixels)."""

    def __repr__(self):
        return _pretty_print(self)


@dataclass(slots=True)
class Syllable:
    """Syllable object contains information about a single syllable in a line."""

    i: int
    """Syllable index in the line."""
    word_i: int
    """Index of the word this syllable belongs to."""
    start_time: int
    """Start time (ms) of the syllable."""
    end_time: int
    """End time (ms) of the syllable."""
    duration: int
    """Duration (ms) of the syllable."""
    styleref: Style
    """Reference to the Style object for this syllable's line."""
    text: str
    """Text of the syllable."""
    tags: str
    """ASS override tags preceding the syllable text (excluding \\\\k tags)."""
    inline_fx: str
    """Inline effect for the syllable (from \\\\-EFFECT tag)."""
    prespace: int
    """Number of spaces before the syllable."""
    postspace: int
    """Number of spaces after the syllable."""
    width: float
    """Width of the syllable (pixels)."""
    height: float
    """Height of the syllable (pixels)."""
    x: float
    """Horizontal position of the syllable (pixels)."""
    y: float
    """Vertical position of the syllable (pixels)."""
    left: float
    """Left position of the syllable (pixels)."""
    center: float
    """Center position of the syllable (pixels)."""
    right: float
    """Right position of the syllable (pixels)."""
    top: float
    """Top position of the syllable (pixels)."""
    middle: float
    """Middle position of the syllable (pixels)."""
    bottom: float
    """Bottom position of the syllable (pixels)."""

    def __repr__(self):
        return _pretty_print(self)


@dataclass(slots=True)
class Word:
    """Word object contains information about a single word in a line."""

    i: int
    """Word index in the line."""
    start_time: int
    """Start time (ms) of the word (same as line start)."""
    end_time: int
    """End time (ms) of the word (same as line end)."""
    duration: int
    """Duration (ms) of the word (same as line duration)."""
    styleref: Style
    """Reference to the Style object for this word's line."""
    text: str
    """Text of the word."""
    prespace: int
    """Number of spaces before the word."""
    postspace: int
    """Number of spaces after the word."""
    width: float
    """Width of the word (pixels)."""
    height: float
    """Height of the word (pixels)."""
    x: float
    """Horizontal position of the word (pixels)."""
    y: float
    """Vertical position of the word (pixels)."""
    left: float
    """Left position of the word (pixels)."""
    center: float
    """Center position of the word (pixels)."""
    right: float
    """Right position of the word (pixels)."""
    top: float
    """Top position of the word (pixels)."""
    middle: float
    """Middle position of the word (pixels)."""
    bottom: float
    """Bottom position of the word (pixels)."""

    def __repr__(self):
        return _pretty_print(self)


@dataclass(slots=True)
class Line:
    """Line object contains information about a single subtitle line in the ASS file."""

    comment: bool
    """True if this line is a comment, False if it is a dialogue."""
    layer: int
    """Layer number for the line (higher layers are drawn above lower ones)."""
    start_time: int
    """Start time (ms) of the line."""
    end_time: int
    """End time (ms) of the line."""
    style: str
    """Style name used for this line. Could be None in case of non-existing style name."""
    styleref: Style
    """Reference to the Style object for this line."""
    actor: str
    """Actor field."""
    margin_l: int
    """Left margin for this line (pixels)."""
    margin_r: int
    """Right margin for this line (pixels)."""
    margin_v: int
    """Vertical margin for this line (pixels)."""
    effect: str
    """Effect field."""
    raw_text: str
    """Raw text of the line (including tags)."""
    text: str
    """Stripped text of the line (no tags)."""
    i: int
    """Line index in the file."""
    duration: int
    """Duration (ms) of the line."""
    leadin: int
    """Time (ms) between this line and the previous one."""
    leadout: int
    """Time (ms) between this line and the next one."""
    width: float
    """Width of the line (pixels)."""
    height: float
    """Height of the line (pixels)."""
    ascent: float
    """Font ascent for the line."""
    descent: float
    """Font descent for the line."""
    internal_leading: float
    """Font internal leading for the line."""
    external_leading: float
    """Font external leading for the line."""
    x: float
    """Horizontal position of the line (pixels)."""
    y: float
    """Vertical position of the line (pixels)."""
    left: float
    """Left position of the line (pixels)."""
    center: float
    """Center position of the line (pixels)."""
    right: float
    """Right position of the line (pixels)."""
    top: float
    """Top position of the line (pixels)."""
    middle: float
    """Middle position of the line (pixels)."""
    bottom: float
    """Bottom position of the line (pixels)."""
    words: list[Word]
    """List of Word objects in this line."""
    syls: list[Syllable]
    """List of Syllable objects in this line (if available)."""
    chars: list[Char]
    """List of Char objects in this line."""

    def __repr__(self):
        return _pretty_print(self)

    def copy(self) -> "Line":
        """
        Returns:
            A deep copy of this object (line)
        """
        return copy.deepcopy(self)

    @classmethod
    def from_ass_line(
        cls, line: str, line_index: int, styles: dict[str, Style]
    ) -> "Line":
        """Parses a single ASS line and returns the corresponding Line object."""
        event_match = re.match(r"(Dialogue|Comment):\s*(.+)$", line)
        if not event_match:
            raise ValueError(
                f"Invalid event line. Line index: {line_index}, Line: {line}."
            )

        # Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
        event_type = event_match.group(1)
        event_data = event_match.group(2)

        # Split into fields, allowing the text field to contain commas
        event_fields = event_data.split(",", 9)
        if len(event_fields) < 10:
            raise ValueError(f"Incomplete event line at index {line_index}: {line}")

        # Convert time fields
        try:
            start_time = Convert.time(event_fields[1])
            end_time = Convert.time(event_fields[2])
        except Exception as e:
            raise ValueError(f"Invalid time fields at line {line_index}: {e}")

        # Resolve style reference
        style_name = event_fields[3]
        try:
            styleref = styles[style_name]
        except KeyError:
            raise ValueError(f"Unknown style '{style_name}' at line {line_index}")

        return cls(
            comment=(event_type == "Comment"),
            layer=int(event_fields[0]),
            start_time=start_time,
            end_time=end_time,
            style=style_name,
            styleref=styleref,
            actor=event_fields[4],
            margin_l=int(event_fields[5]),
            margin_r=int(event_fields[6]),
            margin_v=int(event_fields[7]),
            effect=event_fields[8],
            raw_text=event_fields[9],
            text="",
            i=line_index,
            duration=-1,
            leadin=-1,
            leadout=-1,
            width=float("nan"),
            height=float("nan"),
            ascent=float("nan"),
            descent=float("nan"),
            internal_leading=float("nan"),
            external_leading=float("nan"),
            x=float("nan"),
            y=float("nan"),
            left=float("nan"),
            center=float("nan"),
            right=float("nan"),
            top=float("nan"),
            middle=float("nan"),
            bottom=float("nan"),
            words=[],
            syls=[],
            chars=[],
        )

    def serialize(self) -> str:
        return (
            f"{'Comment' if self.comment else 'Dialogue'}: {self.layer},"
            f"{Convert.time(max(0, int(self.start_time)))},"
            f"{Convert.time(max(0, int(self.end_time)))},"
            f"{self.style},"
            f"{self.actor},"
            f"{self.margin_l:04d},"
            f"{self.margin_r:04d},"
            f"{self.margin_v:04d},"
            f"{self.effect},"
            f"{self.text}\n"
        )


class Ass:
    """Contains all the informations about a file in the ASS format and the methods to work with it for both input and output.

    | Usually you will create an Ass object and use it for input and output (see example_ section).
    | PyonFX set automatically an absolute path for all the info in the output, so that wherever you will
      put your generated file, it should always load correctly video and audio.

    Args:
        path_input (str): Path for the input file (either relative to your .py file or absolute).
        path_output (str): Path for the output file (either relative to your .py file or absolute) (DEFAULT: "Output.ass").
        keep_original (bool): If True, you will find all the lines of the input file commented before the new lines generated.
        extended (bool): Calculate more informations from lines (usually you will not have to touch this).
        vertical_kanji (bool): If True, line text with alignment 4, 5 or 6 will be positioned vertically. Additionally, ``line`` fields will be re-calculated based on the re-positioned ``line.chars``.
        progress (bool): If True, a progress bar will be displayed when iterating over the lines.

    Attributes:
        path_input (str): Path for input file (absolute).
        path_output (str): Path for output file (absolute).
        meta (:class:`Meta`): Contains informations about the ASS given.
        styles (list of :class:`Style`): Contains all the styles in the ASS given.
        lines (list of :class:`Line`): Contains all the lines (events) in the ASS given.
        PIXEL_STYLE (:class:`Style`): Constant lightweight style for pixels.

    .. _example:
    Example:
        ..  code-block:: python3

            io = Ass("in.ass")
            meta, styles, lines = io.get_data()
    """

    PIXEL_STYLE = Style(
        name="p",
        fontname="Arial",
        fontsize=20,
        color1="FFFFFF",
        alpha1="00",
        color2="FFFFFF",
        alpha2="00",
        color3="000000",
        alpha3="0000",
        color4="000000",
        alpha4="0000",
        bold=False,
        italic=False,
        underline=False,
        strikeout=False,
        scale_x=100,
        scale_y=100,
        spacing=0,
        angle=0,
        border_style=False,
        outline=0,
        shadow=0,
        alignment=7,
        margin_l=0,
        margin_r=0,
        margin_v=0,
        encoding=1,
    )
    """Lightweight style for pixels."""

    def __init__(
        self,
        path_input: str,
        path_output: str = "output.ass",
        keep_original: bool = True,
        extended: bool = True,
        vertical_kanji: bool = False,
    ):
        # Progress/statistics
        self._saved = False
        self._plines = 0  # Total produced lines
        self._ptime = time.time()  # Total processing time
        self._stats_by_effect: defaultdict[str, dict[str, float | int]] = defaultdict(
            lambda: {"lines": 0, "time": 0.0, "calls": 0}
        )

        # Output buffers
        self._output: list[str] = []
        self._output_extradata: list[str] = []

        # Public attributes
        self.meta: Meta = Meta()
        self.styles: dict[str, Style] = {}
        self.lines: list[Line] = []

        # Getting absolute sub file path
        self.path_input = _resolve_path(sys.argv[0], path_input)
        if not os.path.isfile(self.path_input):
            raise FileNotFoundError(
                "Invalid path for the Subtitle file: %s" % self.path_input
            )
        self.path_output = _resolve_path(sys.argv[0], path_output)

        # Parse the ASS file
        current_section = ""
        line_index = 0

        with open(self.path_input, encoding="utf-8-sig") as file:
            for line in file:
                # New section?
                section_match = re.match(r"^\[([^\]]*)\]", line)
                if section_match:
                    current_section = section_match.group(1)
                    if current_section != "Aegisub Extradata":
                        self._output.append(line)
                    continue

                if line.startswith("Format") or not line.strip():
                    self._output.append(line)
                # Sections parsers
                elif current_section in ("Script Info", "Aegisub Project Garbage"):
                    line = self.meta.parse_line(line, self.path_input)
                    self._output.append(line)
                elif current_section == "V4+ Styles":
                    style = Style.from_ass_line(line)
                    self.styles[style.name] = style
                    self._output.append(line)
                elif current_section == "Events":
                    self.lines.append(Line.from_ass_line(line, line_index, self.styles))
                    if keep_original:
                        self._output.append(
                            re.sub(r"^(Dialogue|Comment):", "Comment:", line, count=1)
                        )
                    line_index += 1
                elif current_section == "Aegisub Extradata":
                    self._output_extradata.append(line)
                elif (
                    current_section and line.strip()
                ):  # Non-empty line in unknown section
                    raise ValueError(
                        f"Unexpected section in the input file: [{current_section}]"
                    )

        # Add extended information to lines and meta?
        if extended:
            self._process_extended_line_data(vertical_kanji)

    def _process_extended_line_data(self, vertical_kanji: bool) -> None:
        """Process extended line data including positioning, words, syllables, and characters."""

        def _split_raw_segments(
            lines: list[Line],
        ) -> tuple[list[Line], list[int], list[int]]:
            """Split each raw_text at \\N and compute cumulative k-offsets."""
            output_lines: list[Line] = []
            new_lines_indices: list[int] = []
            new_lines_k_offsets: list[int] = []
            for line in lines:
                raw_segments = line.raw_text.split("\\N")
                text_segments = re.sub(r"\{.*?\}", "", line.raw_text).split("\\N")
                seg_k_durations = [
                    sum(int(m) * 10 for m in re.findall(r"\\[kK][of]?(\d+)", seg))
                    for seg in raw_segments
                ]
                cumulative_k_durations = [
                    sum(seg_k_durations[:i]) for i in range(len(seg_k_durations))
                ]

                for seg_idx, (raw_seg, text_seg) in enumerate(
                    zip(raw_segments, text_segments)
                ):
                    seg_line = line.copy()
                    seg_line.raw_text = raw_seg
                    seg_line.text = text_seg
                    output_lines.append(seg_line)
                    new_lines_indices.append(seg_idx)
                    new_lines_k_offsets.append(cumulative_k_durations[seg_idx])
            return output_lines, new_lines_indices, new_lines_k_offsets

        def _compute_line_fields(line: Line, font: Font, split_index: int):
            """Compute duration, text, font metrics, dimensions and positions for a line."""
            line.duration = line.end_time - line.start_time
            line.text = re.sub(r"\{.*?\}", "", line.raw_text)

            line.width, line.height = font.get_text_extents(line.text.strip())
            (
                line.ascent,
                line.descent,
                line.internal_leading,
                line.external_leading,
            ) = font.get_metrics()

            if (
                self.meta.play_res_x is None
                or self.meta.play_res_x <= 0
                or self.meta.play_res_y is None
                or self.meta.play_res_y <= 0
            ):
                return

            # Resolve margins
            margins = {
                "l": line.margin_l or line.styleref.margin_l,
                "r": line.margin_r or line.styleref.margin_r,
                "v": line.margin_v or line.styleref.margin_v,
            }

            # Horizontal position
            h_group = (line.styleref.alignment - 1) % 3
            positions = [
                margins["l"],
                (self.meta.play_res_x - line.width) / 2
                + (margins["l"] - margins["r"]) / 2,
                self.meta.play_res_x - margins["r"] - line.width,
            ]
            line.left = positions[h_group]
            line.center = line.left + line.width / 2
            line.right = line.left + line.width
            line.x = (line.left, line.center, line.right)[h_group]

            # Vertical position
            v_group = (line.styleref.alignment - 1) // 3
            positions = [
                self.meta.play_res_y - margins["v"] - line.height,  # bottom
                (self.meta.play_res_y - line.height) / 2,  # middle
                margins["v"],  # top
            ]
            line.top = positions[v_group]
            line.middle = line.top + line.height / 2
            line.bottom = line.top + line.height
            line.y = (line.bottom, line.middle, line.top)[v_group]

            # Apply vertical offset for split lines
            if split_index > 0:
                offset = split_index * line.height
                line.top += offset
                line.middle += offset
                line.bottom += offset
                line.y += offset

        def _build_words(line: Line, font: Font):
            """Build words for a line."""
            for wi, (prespace, word_text, postspace) in enumerate(
                re.findall(r"(\s*)([^\s]+)(\s*)", line.text)
            ):
                width, height = font.get_text_extents(word_text)
                line.words.append(
                    Word(
                        i=wi,
                        start_time=line.start_time,
                        end_time=line.end_time,
                        duration=line.duration,
                        styleref=line.styleref,
                        text=word_text,
                        prespace=len(prespace),
                        postspace=len(postspace),
                        width=width,
                        height=height,
                        x=float("nan"),
                        y=float("nan"),
                        left=float("nan"),
                        center=float("nan"),
                        right=float("nan"),
                        top=float("nan"),
                        middle=float("nan"),
                        bottom=float("nan"),
                    )
                )

            if (
                line.left == float("nan")
                or self.meta.play_res_x is None
                or self.meta.play_res_y is None
            ):
                return

            h_group = (line.styleref.alignment - 1) % 3
            v_group = (line.styleref.alignment - 1) // 3

            if not vertical_kanji or v_group in (0, 2):
                cur_x = line.left
                space_offset = space_width + style_spacing

                for i, word in enumerate(line.words):
                    # Add prespace offset for all words except the first one
                    if i > 0:
                        cur_x += word.prespace * space_offset

                    # Horizontal position
                    word.left = cur_x
                    word.center = word.left + word.width / 2
                    word.right = word.left + word.width
                    word.x = [word.left, word.center, word.right][h_group]

                    # Vertical position (copy from line)
                    word.top, word.middle, word.bottom, word.y = (
                        line.top,
                        line.middle,
                        line.bottom,
                        line.y,
                    )

                    # Update cur_x for next word
                    cur_x += word.width + word.postspace * space_offset + style_spacing
            else:
                max_width = max(word.width for word in line.words)
                sum_height = sum(word.height for word in line.words)

                cur_y = self.meta.play_res_y / 2 - sum_height / 2
                alignment = line.styleref.alignment

                for word in line.words:
                    # Horizontal position
                    x_fix = (max_width - word.width) / 2

                    if alignment == 4:
                        word.left = line.left + x_fix
                        word.x = word.left
                    elif alignment == 5:
                        word.left = self.meta.play_res_x / 2 - word.width / 2
                        word.x = word.left + word.width / 2
                    else:
                        word.left = line.right - word.width - x_fix
                        word.x = word.left + word.width

                    word.center = word.left + word.width / 2
                    word.right = word.left + word.width

                    # Vertical position
                    word.top = cur_y
                    word.middle = cur_y + word.height / 2
                    word.bottom = cur_y + word.height
                    word.y = word.middle
                    cur_y += word.height

        def _parse_syllables(line_raw_text: str) -> list[tuple[str, int, str]]:
            """Parse ASS karaoke line into syllable divisions.

            ASS karaoke works by having timing tags (like \\k50) that indicate syllable boundaries,
            with other styling tags that can appear before or after them. We group
            tags and text into logical divisions based on karaoke timing boundaries.
            """
            KARAOKE_PATTERN = re.compile(r"\\[kK][fot]?(\d+)?")
            TAG_BLOCK_PATTERN = re.compile(r"\{([^}]*)\}|([^{]+)")
            TAG_EXTRACT_PATTERN = re.compile(r"\\[^\\]*")

            result = []
            pending_tags = []
            current_tags = []
            current_text = ""
            current_duration = ""

            # Split line into tag blocks {...} and text segments
            for match in TAG_BLOCK_PATTERN.finditer(line_raw_text):
                tag_content, text_content = match.group(1), match.group(2)

                if tag_content is not None:
                    tags = TAG_EXTRACT_PATTERN.findall(tag_content)
                    karaoke_matches = {tag: KARAOKE_PATTERN.match(tag) for tag in tags}
                    has_karaoke = any(karaoke_matches.values())

                    if has_karaoke:
                        # Karaoke block: process tags
                        found_karaoke = False
                        for tag in tags:
                            k_match = karaoke_matches[tag]
                            if k_match:
                                if current_tags:
                                    result.append(
                                        (
                                            "".join(current_tags),
                                            current_duration,
                                            current_text,
                                        )
                                    )
                                    current_text = ""
                                current_tags = pending_tags + [tag]
                                current_duration = (
                                    int(k_match.group(1)) if k_match.group(1) else 0
                                )
                                pending_tags = []
                                found_karaoke = True
                            else:
                                if found_karaoke:
                                    current_tags.append(tag)
                                else:
                                    pending_tags.append(tag)
                    else:
                        # Non-karaoke block: decide where these tags belong
                        if current_tags and not current_text:
                            current_tags.extend(tags)
                        else:
                            pending_tags.extend(tags)
                else:
                    # Plain text: add to current division
                    current_text += text_content

            # Add the final division if it exists
            if current_tags:
                result.append(("".join(current_tags), current_duration, current_text))

            return result

        def _build_syllables(
            line: Line,
            syllable_data: list[tuple[str, int, str]],
            font: Font,
            split_k_offset: int,
        ):
            # Precompute word boundaries (start_idx, end_idx, word_i)
            word_boundaries: list[tuple[int, int, int]] = []
            idx = 0
            for w in line.words:
                start = idx + w.prespace
                end = start + len(w.text)
                word_boundaries.append((start, end, w.i))
                idx = end + w.postspace

            last_time = split_k_offset
            syl_char_idx = 0

            for syl_i, (tags, k_dur, raw_text) in enumerate(syllable_data):
                # Inline effect
                m = re.search(r"\\-([^\s\\}]+)", tags)
                inline_fx = m.group(1) if m else ""

                # Text and spacing
                text_stripped = raw_text.strip()
                prespace = len(raw_text) - len(raw_text.lstrip())
                postspace = (
                    len(raw_text) - len(raw_text.rstrip()) if text_stripped else 0
                )

                # Timing
                duration = k_dur * 10 if k_dur else 0
                start_time = last_time
                end_time = start_time + duration

                # Determine word index
                syl_start = syl_char_idx + prespace
                syl_word_i = next(
                    (w_i for s, e, w_i in word_boundaries if s <= syl_start < e), 0
                )

                # Font metrics
                width, height = font.get_text_extents(text_stripped)

                # Create and append syllable
                line.syls.append(
                    Syllable(
                        i=syl_i,
                        word_i=syl_word_i,
                        start_time=start_time,
                        end_time=end_time,
                        duration=duration,
                        styleref=line.styleref,
                        text=text_stripped,
                        tags=tags,
                        inline_fx=inline_fx,
                        prespace=prespace,
                        postspace=postspace,
                        width=width,
                        height=height,
                        x=float("nan"),
                        y=float("nan"),
                        left=float("nan"),
                        center=float("nan"),
                        right=float("nan"),
                        top=float("nan"),
                        middle=float("nan"),
                        bottom=float("nan"),
                    )
                )

                # Update for next iteration
                last_time = end_time
                syl_char_idx += prespace + len(text_stripped) + postspace

            if (
                line.left == float("nan")
                or self.meta.play_res_x is None
                or self.meta.play_res_y is None
            ):
                return

            h_group = (line.styleref.alignment - 1) % 3
            v_group = (line.styleref.alignment - 1) // 3

            if not vertical_kanji or v_group in (0, 2):
                cur_x = line.left
                found_first_text_syl = False
                space_offset = space_width + style_spacing

                for syl in line.syls:
                    # Add prespace offset only after the first syllable with text
                    if found_first_text_syl:
                        cur_x += syl.prespace * space_offset
                    elif syl.text:
                        found_first_text_syl = True

                    # Horizontal position
                    syl.left = cur_x
                    syl.center = syl.left + syl.width / 2
                    syl.right = syl.left + syl.width
                    syl.x = [syl.left, syl.center, syl.right][h_group]

                    # Vertical position
                    syl.top, syl.middle, syl.bottom, syl.y = (
                        line.top,
                        line.middle,
                        line.bottom,
                        line.y,
                    )

                    # Update cur_x for next syllable
                    cur_x += syl.width + syl.postspace * space_offset + style_spacing
            else:
                max_width = max(syl.width for syl in line.syls)
                sum_height = sum(syl.height for syl in line.syls)

                cur_y = self.meta.play_res_y / 2 - sum_height / 2
                alignment = line.styleref.alignment

                for syl in line.syls:
                    x_fix = (max_width - syl.width) / 2

                    # Horizontal position
                    if alignment == 4:
                        syl.left = line.left + x_fix
                    elif alignment == 5:
                        syl.left = self.meta.play_res_x / 2 - syl.width / 2
                    else:
                        syl.left = line.right - syl.width - x_fix

                    syl.center = syl.left + syl.width / 2
                    syl.right = syl.left + syl.width
                    syl.x = [syl.left, syl.center, syl.right][h_group]

                    # Vertical position
                    syl.top = cur_y
                    syl.middle = cur_y + syl.height / 2
                    syl.bottom = cur_y + syl.height
                    syl.y = syl.middle

                    cur_y += syl.height

        def _build_chars(line: Line, font: Font):
            # Chars are built from syllables: fallback to words if no syllables
            words_or_syls = line.syls if line.syls else line.words

            char_index = 0
            for el in words_or_syls:
                el_text = "{}{}{}".format(
                    " " * el.prespace, el.text, " " * el.postspace
                )
                for ci, char_text in enumerate(list(el_text)):
                    width, height = font.get_text_extents(char_text)

                    char = Char(
                        i=char_index,
                        word_i=getattr(el, "word_i", el.i),
                        syl_i=el.i if line.syls else -1,  # -1 means no syllable
                        syl_char_i=ci,
                        start_time=el.start_time,
                        end_time=el.end_time,
                        duration=el.duration,
                        styleref=line.styleref,
                        text=char_text,
                        inline_fx=getattr(el, "inline_fx", ""),
                        width=width,
                        height=height,
                        x=float("nan"),
                        y=float("nan"),
                        left=float("nan"),
                        center=float("nan"),
                        right=float("nan"),
                        top=float("nan"),
                        middle=float("nan"),
                        bottom=float("nan"),
                    )
                    char_index += 1
                    line.chars.append(char)

            if (
                line.left == float("nan")
                or self.meta.play_res_x is None
                or self.meta.play_res_y is None
            ):
                return

            h_group = (line.styleref.alignment - 1) % 3
            v_group = (line.styleref.alignment - 1) // 3

            if not vertical_kanji or v_group in (0, 2):
                cur_x = line.left
                found_first_non_whitespace = False

                for char in line.chars:
                    # Horizontal position
                    char.left = cur_x
                    char.center = char.left + char.width / 2
                    char.right = char.left + char.width
                    char.x = [char.left, char.center, char.right][h_group]

                    # Update cur_x after first visible character
                    if found_first_non_whitespace:
                        cur_x += char.width + style_spacing
                    elif not char.text.isspace():
                        found_first_non_whitespace = True
                        cur_x += char.width + style_spacing

                    # Vertical position (copy from line)
                    char.top, char.middle, char.bottom, char.y = (
                        line.top,
                        line.middle,
                        line.bottom,
                        line.y,
                    )
            else:
                max_width = max(char.width for char in line.chars)
                sum_height = sum(char.height for char in line.chars)
                cur_y = self.meta.play_res_y / 2 - sum_height / 2

                # Set line box metrics
                line.top = cur_y
                line.middle = self.meta.play_res_y / 2
                line.bottom = line.top + sum_height
                line.width = max_width
                line.height = sum_height

                if line.styleref.alignment == 4:
                    line.center = line.left + max_width / 2
                    line.right = line.left + max_width
                elif line.styleref.alignment == 5:
                    line.left = line.center - max_width / 2
                    line.right = line.left + max_width
                else:
                    line.left = line.right - max_width
                    line.center = line.left + max_width / 2

                for char in line.chars:
                    # Horizontal position
                    x_fix = (max_width - char.width) / 2

                    if line.styleref.alignment == 4:
                        char.left = line.left + x_fix
                    elif line.styleref.alignment == 5:
                        char.left = self.meta.play_res_x / 2 - char.width / 2
                    else:
                        char.left = line.right - char.width - x_fix

                    char.center = char.left + char.width / 2
                    char.right = char.left + char.width
                    char.x = [char.left, char.center, char.right][h_group]

                    # Vertical position
                    char.top = cur_y
                    char.middle = cur_y + char.height / 2
                    char.bottom = cur_y + char.height
                    char.y = char.middle

                    cur_y += char.height

        def _assign_lead_times(lines_by_styles):
            """
            For each style, sort lines by start_time, group consecutive lines
            with the same index (i), then compute and assign leadin and leadout
            durations for each line in those groups.
            """
            for _, lines in lines_by_styles.items():
                # Sort lines by start_time
                sorted_lines = sorted(lines, key=lambda l: l.start_time)

                # Group consecutive lines with the same index 'i'
                grouped = [
                    list(group)
                    for _, group in itertools.groupby(sorted_lines, key=lambda l: l.i)
                ]

                # Compute and assign leadin/leadout for each group
                for idx, group in enumerate(grouped):
                    prev_end = grouped[idx - 1][-1].end_time if idx > 0 else None
                    next_start = (
                        grouped[idx + 1][0].start_time
                        if idx < len(grouped) - 1
                        else None
                    )

                    leadin = (
                        1001 if prev_end is None else group[0].start_time - prev_end
                    )
                    leadout = (
                        1001 if next_start is None else next_start - group[-1].end_time
                    )

                    for line in group:
                        line.leadin = leadin
                        line.leadout = leadout

        # Let the fun begin (Pyon!)
        self.lines, new_lines_indices, new_lines_k_offsets = _split_raw_segments(
            self.lines
        )
        lines_by_styles: dict[str, list[Line]] = defaultdict(list)

        for line, split_index, split_k_offset in zip(
            self.lines, new_lines_indices, new_lines_k_offsets
        ):
            # Group lines by style for leadin/leadout calculation
            lines_by_styles[line.style].append(line)

            # Get font metrics and spacing
            font = Font(line.styleref)
            space_width = font.get_text_extents(" ")[0]
            style_spacing = line.styleref.spacing

            # Compute line fields
            _compute_line_fields(line, font, split_index)

            # Build words
            _build_words(line, font)

            # Build syllables
            syllable_data = _parse_syllables(line.raw_text)
            _build_syllables(line, syllable_data, font, split_k_offset)

            # Build chars
            _build_chars(line, font)

        # Add leadin/leadout
        _assign_lead_times(lines_by_styles)

    def replace_meta(self, meta: Meta) -> None:
        """Replaces only the meta fields in the output sections.

        Updates lines corresponding to the meta object's fields in the
        [Script Info] and [Aegisub Project Garbage] sections, leaving other lines untouched.
        """
        self.meta = meta
        new_script_lines, new_garbage_lines = meta.serialize()

        def get_key(line: str) -> str:
            return line.split(":", 1)[0].strip() if ":" in line else ""

        def update_section(section: str, new_lines: list[str]) -> None:
            # Build a dictionary of new meta lines keyed by their meta key
            new_meta = {get_key(line): line for line in new_lines if get_key(line)}

            # Locate the section header in the _output list
            try:
                header_idx = next(
                    i
                    for i, line in enumerate(self._output)
                    if line.strip().startswith(section)
                )
            except StopIteration:
                if section == "[Aegisub Project Garbage]":
                    # Insert the Aegisub Project Garbage section after [Script Info] if available
                    try:
                        script_idx = next(
                            i
                            for i, line in enumerate(self._output)
                            if line.strip().startswith("[Script Info]")
                        )
                        end_script_idx = next(
                            (
                                j
                                for j, line in enumerate(
                                    self._output[script_idx + 1 :], start=script_idx + 1
                                )
                                if line.strip().startswith("[")
                            ),
                            len(self._output),
                        )
                        insert_idx = end_script_idx
                    except StopIteration:
                        insert_idx = len(self._output)
                    self._output.insert(insert_idx, f"{section}\n")
                    self._output.insert(insert_idx + 1, "\n")
                    header_idx = insert_idx
                else:
                    raise ValueError(f"{section} is not a valid section.")

            # Determine the end of the section (first line starting with '[' after header)
            end_idx = (
                next(
                    (
                        j
                        for j, line in enumerate(
                            self._output[header_idx + 1 :], start=header_idx + 1
                        )
                        if line.strip().startswith("[")
                    ),
                    len(self._output),
                )
                - 1
            )

            # Update only the meta-related lines in this section
            updated_block = [
                new_meta.pop(get_key(line), line) if get_key(line) else line
                for line in self._output[header_idx + 1 : end_idx]
            ]

            # Append any new meta lines not already present
            updated_block.extend(new_meta.values())
            self._output[:] = (
                self._output[: header_idx + 1] + updated_block + self._output[end_idx:]
            )

        update_section("[Script Info]", new_script_lines)
        update_section("[Aegisub Project Garbage]", new_garbage_lines)

    def replace_style(self, style_name: str, style: Style) -> None:
        """Replaces a given ASS style in the output.

        The style is serialized and inserted into the [V4+ Styles] section.
        """
        if style_name not in self.styles:
            raise ValueError(f"Style {style_name} does not exist.")

        # Update the style in the dictionary
        self.styles[style_name] = style

        # Serialize the new style
        new_style_line = style.serialize(style_name)

        # Update the corresponding style line in the _output list
        for idx, line in enumerate(self._output):
            stripped_line = line.lstrip()
            if stripped_line.startswith("Style:"):
                parts = stripped_line[len("Style:") :].split(",", 1)
                if parts and parts[0].strip() == style_name:
                    self._output[idx] = new_style_line
                    break

    def add_style(self, style_name: str, style: Style) -> None:
        """Adds a given ASS style into the output if it doesn't already exist.

        The style is serialized and inserted into the [V4+ Styles] section.
        """
        if style_name in self.styles:
            raise ValueError(f"Style {style_name} already exists.")

        insertion_index = None
        in_styles_section = False
        for i, line in enumerate(self._output):
            stripped = line.strip()
            if stripped.startswith("[") and "V4+ Styles" in stripped:
                in_styles_section = True
                continue
            if in_styles_section and stripped.startswith("["):
                insertion_index = i - 1
                break
        if insertion_index is None:
            insertion_index = len(self._output)

        style_line = style.serialize(style_name)
        self._output.insert(insertion_index, style_line)
        self.styles[style_name] = style

    def get_data(self) -> tuple[Meta, dict[str, Style], list[Line]]:
        """Utility function to retrieve easily meta, styles and lines.

        Returns:
            :attr:`meta`, :attr:`styles` and :attr:`lines`
        """
        return self.meta, self.styles, self.lines

    def write_line(self, line: Line) -> None:
        """Appends a line to the output list (which is private) that later on will be written to the output file when calling save().

        Use it whenever you've prepared a line, it will not impact performance since you
        will not actually write anything until :func:`save` will be called.

        Parameters:
            line (:class:`Line`): A line object. If not valid, TypeError is raised.
        """
        self._output.append(line.serialize())
        self._plines += 1

    def save(self, quiet: bool = False) -> None:
        """Write everything inside the private output list to a file.

        Parameters:
            quiet (bool): If True, you will not get printed any message.
        """

        # Writing to file
        with open(self.path_output, "w", encoding="utf-8-sig") as f:
            f.writelines(self._output)
            if self._output_extradata:
                f.write("\n[Aegisub Extradata]\n")
                f.writelines(self._output_extradata)

        self._saved = True

        if quiet:
            return

        total_runtime = time.time() - self._ptime
        avg_per_gen_line = total_runtime / self._plines if self._plines else 0.0

        print(f"🐰 Produced lines: {self._plines}")
        print(
            f"⏱️  Total runtime: {total_runtime:.1f}s"
            f" (avg {avg_per_gen_line:.3f}s per generated line)"
        )

        if self._stats_by_effect:
            print("\n📊 STATISTICS")

            table_data = []
            for eff, data in self._stats_by_effect.items():
                calls = data["calls"]
                lines = data["lines"]
                time_s = data["time"]
                avg_call = time_s / calls if calls else 0.0

                table_data.append(
                    [
                        eff,
                        calls,
                        lines,
                        f"{time_s:.3f}",
                        f"{avg_call:.3f}",
                    ]
                )

            headers = [
                "Name",
                "Calls",
                "Lines",
                "Time (s)",
                "Avg/Call (s)",
                "Avg/Line (s)",
            ]
            print(
                tabulate(
                    table_data,
                    headers=headers,
                    tablefmt="rounded_grid",
                    numalign="right",
                )
            )

    def open_aegisub(self) -> bool:
        """Attempts to open the subtitle output file in Aegisub.

        Returns:
            True if the file is successfully opened, False otherwise.
        """

        # Check if it was saved
        if not self._saved:
            print(
                "[WARNING] You've tried to open the output with Aegisub before having saved. Check your code."
            )
            return False

        if sys.platform == "win32":
            os.startfile(self.path_output)
        else:
            try:
                subprocess.call(["aegisub", os.path.abspath(self.path_output)])
            except FileNotFoundError:
                print("[WARNING] Aegisub not found.")
                return False

        return True

    def open_mpv(
        self,
        video_path: str | None = None,
        *,
        video_start: str | None = None,
        full_screen: bool = False,
        extra_mpv_options: list[str] = [],
        aegisub_fallback: bool = True,
    ) -> bool:
        """Opens the output subtitle file using MPV media player along with the associated video.

        This method attempts to:
          - Use an already running MPV instance to hot-reload subtitles via an IPC socket if detected.
          - Launch a new MPV process with IPC enabled if no such instance exists.
          - Fall back to opening the output in Aegisub if MPV is not available and aegisub_fallback is True.

        Parameters:
            video_path (str | None): The absolute path to the video file to be played. If None, the video path from meta.video is used.
            video_start (str | None): The starting time for video playback (e.g., "00:01:23"). If None, playback starts from the beginning.
            full_screen (bool): If True, launches MPV in full-screen mode; otherwise, in windowed mode.
            extra_mpv_options (list[str]): Additional command-line options to pass to MPV.
            aegisub_fallback (bool): If True, falls back to opening the output with Aegisub when MPV is not found in the system PATH.

        Returns:
            True if MPV is successfully launched or the subtitles are hot-reloaded in an existing MPV instance; False otherwise (e.g., if the output file has not been saved or MPV is unavailable).
        """
        if not self._saved:
            print(
                "[ERROR] You've tried to open the output with MPV before having saved. Check your code."
            )
            return False

        if not shutil.which("mpv"):
            if aegisub_fallback:
                print(
                    "[WARNING] MPV not found in your environment variables"
                    "(please refer to the documentation's 'Quick Start' section).\n\n"
                    "Falling back to Aegisub."
                )
                self.open_aegisub()
            else:
                print(
                    "[ERROR] MPV not found in your environment variables"
                    "(please refer to the documentation's 'Quick Start' section).\n\n"
                    "Exiting."
                )
            return False

        if video_path is None:
            if self.meta.video and not self.meta.video.startswith("?dummy"):
                video_path = self.meta.video
            else:
                print(
                    "[ERROR] No video file specified and meta.video is None or is a dummy video."
                )
                return False

        # Define IPC socket path for mpv communication
        ipc_socket = (
            r"\\.\pipe\mpv_pyonfx" if sys.platform == "win32" else "/tmp/mpv_pyonfx"
        )

        # Attempt hot-reload
        if (
            sys.platform == "win32" and "mpv_pyonfx" in os.listdir(r"\\.\pipe")
        ) or os.path.exists(ipc_socket):
            try:
                if sys.platform == "win32":
                    with open(ipc_socket, "r+b", buffering=0) as pipe:
                        pipe.write(
                            json.dumps({"command": ["sub-reload"]}).encode("utf-8")
                            + b"\n"
                        )
                else:
                    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
                        sock.connect(ipc_socket)
                        sock.sendall(
                            json.dumps({"command": ["sub-reload"]}).encode("utf-8")
                            + b"\n"
                        )
                print("Hot-reload: Subtitles reloaded in existing mpv instance.")
                return True
            except OSError as e:
                print("Hot-reload failed with OSError:", e)
                return False

        # Build command to launch mpv with IPC enabled
        cmd = ["mpv", "--input-ipc-server=" + ipc_socket]
        cmd.append(video_path)
        if video_start is not None:
            cmd.append("--start=" + video_start)
        if full_screen:
            cmd.append("--fs")
        cmd.append("--sub-file=" + self.path_output)
        cmd.extend(extra_mpv_options)

        try:
            subprocess.Popen(cmd)
        except FileNotFoundError:
            print(
                "[WARNING] MPV not found in your environment variables.\n"
                "Please refer to the documentation's 'Quick Start' section."
            )
            return False

        return True

    def track(self, func: Callable[..., Any]) -> Callable[..., Any]:
        """Decorator to track function performance, gathering timing statistics and monitoring progress.

        This decorator automatically measures execution time, counts function calls,
        and tracks the number of lines produced by the decorated function.
        All statistics are displayed in the final output when save() is called.

        Usage::

            @io.track
            def my_function(...):
                ...
        """

        def wrapper(*args: Any, **kwargs: Any):
            prev_produced_lines = self._plines
            start = time.perf_counter()

            try:
                return func(*args, **kwargs)
            finally:
                end = time.perf_counter()
                stats = self._stats_by_effect[func.__name__]
                stats["calls"] += 1
                stats["lines"] += self._plines - prev_produced_lines
                stats["time"] += end - start

        return wrapper


def _resolve_path(base_path: str, input_path: str) -> str:
    """Resolve an input path relative to a base path or return absolute path if input is absolute."""
    _input_path = Path(input_path)
    if _input_path.is_absolute():
        return str(_input_path.resolve(strict=False))

    _base_path = Path(base_path)
    base_dir = _base_path.parent if _base_path.is_file() else _base_path

    resolved_path = base_dir / _input_path
    return str(resolved_path.resolve(strict=False))


def _pretty_print(obj):
    """Create a pretty string representation for dataclass objects.

    Special handling for Style objects and list-based fields.
    """
    # Get all fields of the object
    obj_fields = fields(obj.__class__)

    # Prepare field representations
    field_reprs = []
    for field in obj_fields:
        value = getattr(obj, field.name)

        # For Style objects, we'll show only the fontname and ellipsis
        if (
            field.name == "styleref"
            and value is not None
            and value.__class__.__name__ == "Style"
        ):
            field_reprs.append(f"{field.name}=Style(fontname={value.fontname!r}, ...)")

        # For list fields, we'll show only the first item with i and text
        elif isinstance(value, list):
            if len(value) > 0:
                first_item = value[0]
                if hasattr(first_item, "i") and hasattr(first_item, "text"):
                    first_item_repr = f"{first_item.__class__.__name__}(i={first_item.i!r}, text={first_item.text!r}, ...)"
                else:
                    first_item_repr = _pretty_print(first_item)

                # Add count of omitted elements
                if len(value) > 1:
                    field_reprs.append(
                        f"{field.name}=[{first_item_repr}, ... (+{len(value)-1} more)]"
                    )
                else:
                    field_reprs.append(f"{field.name}=[{first_item_repr}]")
            else:
                field_reprs.append(f"{field.name}=[]")

        # Default handling for other fields
        else:
            field_reprs.append(f"{field.name}={value!r}")

    # Construct the final representation
    return f"{obj.__class__.__name__}({', '.join(field_reprs)})"
