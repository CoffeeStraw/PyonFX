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
    """Encapsulates the script properties of an ASS file, including video resolution, wrap style, and media file paths.

    Attributes:
        wrap_style: Specifies the wrap style for subtitles. The typical value 0 indicates smart wrapping.
        scaled_border_and_shadow: Determines whether border and shadow sizes are scaled according to the script resolution (True) or the video resolution (False).
        play_res_x: Specifies the script's video width resolution in pixels. This influences horizontal coordinate calculations.
        play_res_y: Specifies the script's video height resolution in pixels. This influences vertical coordinate calculations.
        audio: Absolute file path to the associated audio file.
        video: Absolute file path to the associated video file.
    """

    wrap_style: int | None
    scaled_border_and_shadow: bool | None
    play_res_x: int | None
    play_res_y: int | None
    audio: str | None
    video: str | None
    timestamps: ABCTimestamps | None

    def parse_line(self, line: str, ass_path: str) -> str:
        """Parses a single ASS line and update the relevant fields."""
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
        """Serializes the meta object into ASS script info and garbage sections."""
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
    """Represents a typographic style for ASS subtitles.

    Attributes:
        name: Unique identifier for the style.
        fontname: Typeface used for the subtitles.
        fontsize: Font size in points.
        color1: Primary fill color, typically in hexadecimal format.
        alpha1: Transparency (alpha channel) for the primary fill color.
        color2: Secondary color used for karaoke effects.
        alpha2: Transparency for the secondary color.
        color3: Outline (border) color.
        alpha3: Transparency for the outline color.
        color4: Shadow color.
        alpha4: Transparency for the shadow color.
        bold: Indicates if the font is italic.
        italic: Indicates if the font is italic.
        underline: Indicates if the text is underlined.
        strikeout: Indicates if the text has a strike-through effect.
        scale_x: Horizontal scaling factor as a percentage (100 means no scaling).
        scale_y: Vertical scaling factor as a percentage (100 means no scaling).
        spacing: Additional horizontal spacing between letters in pixels.
        angle: Rotation angle of the text in degrees.
        border_style: Specifies the border style: True for an opaque box, False for a standard outline.
        outline: Outline thickness in pixels.
        shadow: Shadow offset distance in pixels.
        alignment: ASS alignment code (typically an integer from 1 to 9).
        margin_l: Left margin in pixels.
        margin_r: Right margin in pixels.
        margin_v: Vertical margin in pixels; determines vertical positioning relative to the video frame.
        encoding: Font encoding/codepage. The value 1 is standard, allowing the selection of any installed font.
    """

    name: str
    fontname: str
    fontsize: float
    color1: str
    alpha1: str
    color2: str
    alpha2: str
    color3: str
    alpha3: str
    color4: str
    alpha4: str
    bold: bool
    italic: bool
    underline: bool
    strikeout: bool
    scale_x: float
    scale_y: float
    spacing: float
    angle: float
    border_style: bool
    outline: float
    shadow: float
    alignment: int
    margin_l: int
    margin_r: int
    margin_v: int
    encoding: int

    @classmethod
    def from_ass_line(cls, line: str) -> "Style":
        """Parse a single ASS line and return the corresponding Style object."""
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
        """Serialize a Style object into an ASS style line."""
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
    """Represents a single character within a subtitle line.

    Attributes:
        i: Zero-based index of the character within the line.
        word_i: Index of the word to which this character belongs.
        syl_i: Index of the syllable to which this character belongs.
        syl_char_i: Index of the character within its parent syllable.
        start_time: Start time in milliseconds when the character appears.
        end_time: End time in milliseconds when the character disappears.
        duration: Duration in milliseconds, computed as end_time - start_time.
        styleref: Reference to the Style object used for formatting this character.
        text: The actual character as a string.
        inline_fx: Inline effects specified for this character (derived from \\-EFFECT tag).
        width: Width of the character in pixels.
        height: Height of the character in pixels.
        x: Horizontal position (x-coordinate in pixels).
        y: Vertical position (y-coordinate in pixels).
        left: Left boundary (in pixels).
        center: Horizontal center position (in pixels).
        right: Right boundary (in pixels).
        top: Top boundary (in pixels).
        middle: Vertical center position (in pixels).
        bottom: Bottom boundary (in pixels).
    """

    i: int
    word_i: int
    syl_i: int
    syl_char_i: int
    start_time: int
    end_time: int
    styleref: Style
    text: str
    inline_fx: str
    width: float
    height: float
    x: float
    y: float
    left: float
    center: float
    right: float
    top: float
    middle: float
    bottom: float

    @property
    def duration(self) -> int:
        return self.end_time - self.start_time

    def __repr__(self):
        return _pretty_print(self)


@dataclass(slots=True)
class Syllable:
    """Represents a syllable within a subtitle line.

    Attributes:
        i: Zero-based index of the syllable within the line.
        word_i: Index of the word that contains this syllable.
        start_time: Start time in milliseconds when the syllable begins.
        end_time: End time in milliseconds when the syllable ends.
        duration: Duration in milliseconds, computed as end_time - start_time.
        styleref: Reference to the Style object used for formatting this syllable.
        text: Text content of the syllable.
        tags: ASS override tags preceding the syllable text (excluding \\k tags).
        inline_fx: Inline effects for the syllable (derived from \\-EFFECT tag).
        prespace: Number of leading spaces before the syllable.
        postspace: Number of trailing spaces after the syllable.
        width: Width of the syllable in pixels.
        height: Height of the syllable in pixels.
        x: Horizontal position (x-coordinate in pixels).
        y: Vertical position (y-coordinate in pixels).
        left: Left boundary (in pixels).
        center: Horizontal center position (in pixels).
        right: Right boundary (in pixels).
        top: Top boundary (in pixels).
        middle: Vertical center position (in pixels).
        bottom: Bottom boundary (in pixels).
    """

    i: int
    word_i: int
    start_time: int
    end_time: int
    styleref: Style
    text: str
    tags: str
    inline_fx: str
    prespace: int
    postspace: int
    width: float
    height: float
    x: float
    y: float
    left: float
    center: float
    right: float
    top: float
    middle: float
    bottom: float

    @property
    def duration(self) -> int:
        return self.end_time - self.start_time

    def __repr__(self):
        return _pretty_print(self)


@dataclass(slots=True)
class Word:
    """Represents a word within a subtitle line.

    Attributes:
        i: Zero-based index of the word within the line.
        start_time: Start time in milliseconds for the word (typically matching the line's start time).
        end_time: End time in milliseconds for the word (typically matching the line's end time).
        duration: Duration in milliseconds, computed as end_time - start_time.
        styleref: Reference to the Style object for this word.
        text: Text content of the word.
        prespace: Number of leading spaces before the word.
        postspace: Number of trailing spaces after the word.
        width: Width of the word in pixels.
        height: Height of the word in pixels.
        x: Horizontal position (x-coordinate in pixels).
        y: Vertical position (y-coordinate in pixels).
        left: Left boundary (in pixels).
        center: Horizontal center position (in pixels).
        right: Right boundary (in pixels).
        top: Top boundary (in pixels).
        middle: Vertical center position (in pixels).
        bottom: Bottom boundary (in pixels).
    """

    i: int
    start_time: int
    end_time: int
    styleref: Style
    text: str
    prespace: int
    postspace: int
    width: float
    height: float
    x: float
    y: float
    left: float
    center: float
    right: float
    top: float
    middle: float
    bottom: float

    @property
    def duration(self) -> int:
        return self.end_time - self.start_time

    def __repr__(self):
        return _pretty_print(self)


@dataclass(slots=True)
class Line:
    """Represents a subtitle line in an ASS file.

    Attributes:
        comment: Indicates if the line is a comment (True) or dialogue (False).
        layer: Layer number for the line (higher layers are rendered above lower ones).
        start_time: Start time in milliseconds when the line appears.
        end_time: End time in milliseconds when the line disappears.
        duration: Duration in milliseconds, computed as end_time - start_time.
        style: Name of the style applied to the line.
        styleref: Reference to the Style object used for formatting this line.
        actor: Actor or source associated with the line.
        margin_l: Left margin in pixels.
        margin_r: Right margin in pixels.
        margin_v: Vertical margin in pixels.
        effect: Effect field for the line.
        raw_text: Original text of the line, including override tags.
        text: Stripped text of the line (override tags removed).
        i: Zero-based index of the line in the ASS file.
        leadin: Time gap in milliseconds before this line, relative to the previous line.
        leadout: Time gap in milliseconds after this line, relative to the next line.
        width: Width of the line in pixels.
        height: Height of the line in pixels.
        ascent: Font ascent value for the line.
        descent: Font descent value for the line.
        internal_leading: Internal leading (line spacing within the font) in pixels.
        external_leading: External leading (additional spacing between lines) in pixels.
        x: Horizontal position (x-coordinate in pixels) of the line.
        y: Vertical position (y-coordinate in pixels) of the line.
        left: Left boundary of the line (in pixels).
        center: Horizontal center position of the line (in pixels).
        right: Right boundary of the line (in pixels).
        top: Top boundary of the line (in pixels).
        middle: Vertical center position of the line (in pixels).
        bottom: Bottom boundary of the line (in pixels).
        words: List of Word objects contained in the line.
        syls: List of Syllable objects in the line (if available).
        chars: List of Char objects in the line.
    """

    comment: bool
    layer: int
    start_time: int
    end_time: int
    style: str
    styleref: Style
    actor: str
    margin_l: int
    margin_r: int
    margin_v: int
    effect: str
    raw_text: str
    text: str
    i: int
    leadin: int
    leadout: int
    width: float
    height: float
    ascent: float
    descent: float
    internal_leading: float
    external_leading: float
    x: float
    y: float
    left: float
    center: float
    right: float
    top: float
    middle: float
    bottom: float
    words: list[Word]
    syls: list[Syllable]
    chars: list[Char]

    @property
    def duration(self) -> int:
        return self.end_time - self.start_time

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
        """Parse a single ASS line and return the corresponding Line object."""
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
        """Serialize a Line object into an ASS line."""
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
    """ASS File Handler.

    This class provides an interface for reading, processing, and writing Advanced SubStation Alpha (ASS) subtitle files.
    It extracts metadata, styles, and dialogue events, computes extended layout metrics, and outputs ASS files for use with Aegisub or MPV.
    It also supports preserving the original subtitle content as comments and auto-resolves file paths.

    Attributes:
        path_input: absolute path to the input subtitle file.
        path_output: absolute path to the output subtitle file.
        meta: metadata extracted from the ASS file.
        styles: mapping of style names to their style objects present in the ASS file.
        lines: list of subtitle event lines parsed from the file.
        PIXEL_STYLE: default lightweight style for pixel-based effects.

    Examples:
        >>> io = Ass("in.ass")
        >>> meta, styles, lines = io.get_data()
    """

    PIXEL_STYLE: Style = Style(
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
        """Initialize the ASS object.

        Args:
            path_input: The path for the input ASS file, which can be relative or absolute.
            path_output: The path for the output ASS file (default: "output.ass").
            keep_original: If True, the original lines are kept as comments in the output.
            extended: If True, extended information (including positioning, metrics, words, syllables, and characters) will be computed.
            vertical_kanji: If True, lines with alignment 4, 5 or 6 will be repositioned vertically.
        """
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
        self.meta: Meta = Meta(
            wrap_style=None,
            scaled_border_and_shadow=None,
            play_res_x=None,
            play_res_y=None,
            audio=None,
            video=None,
            timestamps=None,
        )
        self.styles: dict[str, Style] = {}
        self.lines: list[Line] = []

        # Getting absolute sub file path
        self.path_input: str = _resolve_path(sys.argv[0], path_input)
        if not os.path.isfile(self.path_input):
            raise FileNotFoundError(
                "Invalid path for the Subtitle file: %s" % self.path_input
            )
        self.path_output: str = _resolve_path(sys.argv[0], path_output)

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

                # Copy-paste lines
                elif line.startswith("Format") or not line.strip():
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
            for wi, (prespace, word_text, postspace) in enumerate(
                re.findall(r"(\s*)([^\s]+)(\s*)", line.text)
            ):
                width, height = font.get_text_extents(word_text)
                line.words.append(
                    Word(
                        i=wi,
                        start_time=line.start_time,
                        end_time=line.end_time,
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
        """Replace metadata in the ASS output file.

        Args:
            meta: A Meta object containing the updated metadata.

        Examples:
            >>> meta, _, _ = self.get_data()
            >>> meta.wrap_style = 2
            >>> self.replace_meta(meta)
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
        """Replace an existing style in the ASS output file.

        Args:
            style_name: The name of the style to be replaced.
            style: A Style object containing the updated style parameters.

        Examples:
            >>> style = styles['Default']
            >>> style.fontname = 'Helvetica'
            >>> io.replace_style('Default', style)

        See Also:
            [add_style][pyonfx.ass_core.Ass.add_style]
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
        """Add a new style to the ASS output file.

        Args:
            style_name: The name for the new style. This name must be unique within the ASS file.
            style: A Style object containing the styling parameters for the new style.

        Examples:
            >>> new_style = Style(name="NewStyle", fontname="Arial", fontsize=20, color1="FFFFFF", alpha1="00",
            ...                    color2="FFFFFF", alpha2="00", color3="000000", alpha3="0000",
            ...                    color4="000000", alpha4="0000", bold=False, italic=False, underline=False,
            ...                    strikeout=False, scale_x=100, scale_y=100, spacing=0, angle=0, border_style=False,
            ...                    outline=0, shadow=0, alignment=7, margin_l=0, margin_r=0, margin_v=0, encoding=1)
            >>> io.add_style("NewStyle", new_style)

        Notes:
            Ensure that the style name is unique in the current styles mapping.

        See Also:
            [replace_style][pyonfx.ass_core.Ass.replace_style]
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
        """Retrieve metadata, styles, and subtitle lines from the ASS file.

        This utility method returns the essential components of a parsed ASS file:

        - meta: A Meta object containing configuration and metadata.
        - styles: A dictionary mapping style names to their corresponding Style objects.
        - lines: A list of Line objects representing the subtitle dialogue events.

        Returns:
            tuple: A tuple containing the meta object, the dictionary of styles, and the list of subtitle lines.

        Examples:
            >>> meta, styles, lines = ass.get_data()
        """
        return self.meta, self.styles, self.lines

    def write_line(self, line: Line) -> None:
        """Write a subtitle line to the output buffer.

        Args:
            line: A Line object representing a subtitle event.

        Examples:
            >>> line = some_line_object  # a valid Line object
            >>> io.write_line(line)

        Notes:
            This method only updates the internal buffer; you must call save() to persist the changes to disk.

        See Also:
            [save][pyonfx.ass_core.Ass.save]
        """
        self._output.append(line.serialize())
        self._plines += 1

    def save(self, quiet: bool = False) -> None:
        """Save the processed subtitles to the output ASS file and print performance metrics.

        Args:
            quiet: If True, suppresses the output messages during the save process. Defaults to False.

        Notes:
            Make sure to call this method after all subtitle processing is complete to persist your changes.

        See Also:
            [open_aegisub][pyonfx.ass_core.Ass.open_aegisub], [open_mpv][pyonfx.ass_core.Ass.open_mpv]
        """
        # Add script generation info
        header_idx = next(
            i
            for i, line in enumerate(self._output)
            if line.strip().startswith("[Script Info]")
        )
        start_idx = header_idx + 1
        end_idx = next(
            (
                i
                for i in range(start_idx, len(self._output))
                if self._output[i].startswith("[")
            ),
            len(self._output),
        )

        found_generated = False
        i = start_idx
        while i < end_idx:
            line = self._output[i]
            stripped = line.lstrip()
            if stripped.startswith("; http:"):
                self._output.pop(i)
                end_idx -= 1
            elif stripped.startswith("; Script generated by"):
                self._output[i] = "; Script generated by PyonFX\n"
                found_generated = True
                i += 1
            else:
                i += 1

        if not found_generated:
            self._output.insert(start_idx, "; Script generated by PyonFX\n")

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
        """Attempt to open the output ASS file in Aegisub.

        Returns:
            bool: True if the output file is successfully opened in Aegisub, False otherwise.

        Notes:
            Make sure to call the save() method before invoking open_aegisub, or the output file may not exist.

        See Also:
            `open_mpv`
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
        """Open the output subtitle file in MPV media player along with the associated video.

        This method attempts to play the output ASS file using MPV and automatically handles subtitle hot-reload via an IPC socket.
        If an existing MPV instance is detected, it sends a command to reload the subtitles;
        if not, it launches a new MPV process with IPC enabled.

        Args:
            video_path: The absolute path to the video file to be played. If None, the video path from meta.video is used.
            video_start: The starting time for video playback (e.g., "00:01:23"); if None, playback starts from the beginning.
            full_screen: If True, launches MPV in full-screen mode; otherwise, in windowed mode.
            extra_mpv_options: Additional command-line options to pass to MPV.
            aegisub_fallback: If True, falls back to opening the output with Aegisub when MPV is not found.

        Returns:
            bool: True if MPV successfully launches or hot-reloads the subtitles; False otherwise.

        Examples:
            >>> io.open_mpv(video_path="/path/to/video.mp4", full_screen=True)

        See Also:
            [open_aegisub][pyonfx.ass_core.Ass.open_aegisub]
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
