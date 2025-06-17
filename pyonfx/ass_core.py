# PyonFX: An easy way to create KFX (Karaoke Effects) and complex typesetting using the ASS format (Advanced Substation Alpha).
# Copyright (C) 2019 Antonio Strippoli (CoffeeStraw/YellowFlash)
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

from __future__ import annotations
from dataclasses import dataclass
import re
import os
import sys
import time
import copy
import subprocess
from fractions import Fraction
from pathlib import Path
from video_timestamps import (
    ABCTimestamps,
    FPSTimestamps,
    RoundingMethod,
    VideoTimestamps,
)

from .font_utility import Font
from .convert import Convert


@dataclass
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

    def __repr__(self):
        return pretty_print(self)


@dataclass
class Style:
    """Style object contains a set of typographic formatting rules that is applied to dialogue lines."""

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

    def __repr__(self):
        return pretty_print(self)


@dataclass
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
        return pretty_print(self)


@dataclass
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
        return pretty_print(self)


@dataclass
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
        return pretty_print(self)


@dataclass
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
    leadin: float
    """Time (ms) between this line and the previous one."""
    leadout: float
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
        return pretty_print(self)

    def copy(self) -> Line:
        """
        Returns:
            A deep copy of this object (line)
        """
        return copy.deepcopy(self)


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
        vertical_kanji (bool): If True, line text with alignment 4, 5 or 6 will be positioned vertically.
            Additionally, ``line`` fields will be re-calculated based on the re-positioned ``line.chars``.
        video_index (int): Index of the video stream indicated in the `Video File` element from the `[Aegisub Project Garbage]` section.
            Only used if the `Video File` is a file.
        rounding_method (RoundingMethod): The rounding method used to round/floor the PTS (Presentation Time Stamp).
            Only used if the `Video File` element from the `[Aegisub Project Garbage]` section is a Dummy Video.
        time_scale (Fraction): Unit of time (in seconds) in terms of which frame timestamps are represented.
            Important: Don't confuse time_scale with the time_base. As a reminder, time_base = 1 / time_scale.
            Only used if the `Video File` element from the `[Aegisub Project Garbage]` section is a Dummy Video.
        first_pts (int): PTS (Presentation Time Stamp) of the first frame of the video.
            Only used if the `Video File` element from the `[Aegisub Project Garbage]` section is a Dummy Video.


    Attributes:
        path_input (str): Path for input file (absolute).
        path_output (str): Path for output file (absolute).
        meta (:class:`Meta`): Contains informations about the ASS given.
        styles (list of :class:`Style`): Contains all the styles in the ASS given.
        lines (list of :class:`Line`): Contains all the lines (events) in the ASS given.
        input_timestamps (:class:`ABCTimestamps`): The timestamps that represent the `Video File` element from the `[Aegisub Project Garbage]` section.

    .. _example:
    Example:
        ..  code-block:: python3

            io = Ass("in.ass")
            meta, styles, lines = io.get_data()
    """

    def __init__(
        self,
        path_input: str = "",
        path_output: str = "Output.ass",
        keep_original: bool = True,
        extended: bool = True,
        vertical_kanji: bool = False,
        video_index: int = 0,
        rounding_method: RoundingMethod = RoundingMethod.ROUND,  # type: ignore[attr-defined]
        time_scale: Fraction = Fraction(1000),
        first_timestamps: Fraction = Fraction(0),
    ):
        # Starting to take process time
        self.__saved = False
        self.__plines = 0
        self.__ptime = time.time()

        self.meta: Meta
        self.styles: dict[str, Style]
        self.lines: list[Line]
        self.input_timestamps: ABCTimestamps
        self.meta, self.styles, self.lines = Meta(), {}, []

        # Getting absolute sub file path
        dirname = os.path.dirname(os.path.abspath(sys.argv[0]))
        if not os.path.isabs(path_input):
            path_input = os.path.join(dirname, path_input)

        # Checking sub file validity (does it exists?)
        if not os.path.isfile(path_input):
            raise FileNotFoundError(
                "Invalid path for the Subtitle file: %s" % path_input
            )

        # Getting absolute output file path
        if path_output == "Output.ass":
            path_output = os.path.join(dirname, path_output)
        elif not os.path.isabs(path_output):
            path_output = os.path.join(dirname, path_output)

        self.path_input = path_input
        self.path_output = path_output
        self.__output = []
        self.__output_extradata = []

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
                        self.__output.append(line)
                    continue

                # Sections parsers
                if current_section in ("Script Info", "Aegisub Project Garbage"):
                    self._parse_meta_section_line(
                        line, video_index, rounding_method, time_scale, first_timestamps
                    )
                elif current_section == "V4+ Styles":
                    self._parse_styles_section_line(line)
                elif current_section == "Events":
                    self._parse_events_section_line(line, line_index, keep_original)
                    line_index += 1
                elif current_section == "Aegisub Extradata":
                    self.__output_extradata.append(line)
                elif (
                    current_section and line.strip()
                ):  # Non-empty line in unknown section
                    raise ValueError(
                        f"Unexpected section in the input file: [{current_section}]"
                    )

        # Add extended information to lines and meta?
        if extended:
            self._process_extended_line_data(vertical_kanji)

    def _get_media_absolute_path(self, mediafile: str) -> str:
        """Attempt to convert relative media file paths defined in the meta section to absolute paths."""
        if mediafile.startswith("?dummy"):
            return mediafile

        original_path = mediafile
        media_dir = os.path.dirname(self.path_input)

        # Handle relative paths
        while mediafile.startswith("../"):
            media_dir = os.path.dirname(media_dir)
            mediafile = mediafile[3:]

        absolute_path = os.path.normpath(os.path.join(media_dir, mediafile))

        return absolute_path if os.path.isfile(absolute_path) else original_path

    def _parse_meta_section_line(
        self,
        line: str,
        video_index: int,
        rounding_method: RoundingMethod,
        time_scale: Fraction,
        first_timestamps: Fraction,
    ) -> None:
        """Parse Script Info and Aegisub Project Garbage sections."""
        line = line.strip()
        if not line:
            self.__output.append(line + "\n")
            return

        # Parse different meta fields
        if match := re.match(r"WrapStyle:\s*(\d+)$", line):
            self.meta.wrap_style = int(match.group(1))
        elif match := re.match(r"ScaledBorderAndShadow:\s*(.+)$", line):
            self.meta.scaled_border_and_shadow = match.group(1).strip().lower() == "yes"
        elif match := re.match(r"PlayResX:\s*(\d+)$", line):
            self.meta.play_res_x = int(match.group(1))
        elif match := re.match(r"PlayResY:\s*(\d+)$", line):
            self.meta.play_res_y = int(match.group(1))
        elif match := re.match(r"Audio File:\s*(.*)$", line):
            self.meta.audio = self._get_media_absolute_path(match.group(1).strip())
            line = f"Audio File: {self.meta.audio}"
        elif match := re.match(r"Video File:\s*(.*)$", line):
            self.meta.video = self._get_media_absolute_path(match.group(1).strip())
            line = f"Video File: {self.meta.video}"

            # Set up timestamps based on video file
            if os.path.isfile(self.meta.video):
                self.input_timestamps = VideoTimestamps.from_video_file(
                    Path(self.meta.video), video_index
                )
            elif self.meta.video.startswith("?dummy"):
                # Parse dummy video format: ?dummy:fps:duration
                parts = self.meta.video.split(":")
                if len(parts) >= 2:
                    fps_str = parts[1]
                    fps = Fraction(fps_str)
                    self.input_timestamps = FPSTimestamps(
                        rounding_method, time_scale, fps, Fraction(first_timestamps)
                    )

        self.__output.append(line + "\n")

    def _parse_styles_section_line(self, line: str) -> None:
        """Parse V4+ Styles section."""
        self.__output.append(line)

        style_match = re.match(r"Style:\s*(.+)$", line)
        if not style_match:
            return

        # Parse style fields
        #   Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour,
        #   Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle,
        #   BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
        style_fields = [field.strip() for field in style_match.group(1).split(",")]
        style_name = style_fields[0]

        self.styles[style_name] = Style(
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

    def _parse_events_section_line(
        self, line: str, line_index: int, keep_original: bool
    ):
        """Parse Events section and return updated line index."""

        # Line for section's header
        if line.startswith("Format"):
            self.__output.append(line)
            return

        # Handle original line preservation
        if keep_original:
            self.__output.append(
                re.sub(r"^(Dialogue|Comment):", "Comment:", line, count=1)
            )

        # Parse dialogue/comment lines
        event_match = re.match(r"(Dialogue|Comment):\s*(.+)$", line)
        if not event_match:
            raise ValueError(
                f"Invalid event line. Line index: {line_index}, Line: {line}."
            )

        # Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
        event_type = event_match.group(1)
        event_data = event_match.group(2)

        # Parse event fields
        event_fields = [field for field in event_data.split(",")]

        # Convert time fields safely
        start_time_result = Convert.time(event_fields[1])
        end_time_result = Convert.time(event_fields[2])

        # Handle potential conversion errors
        if not isinstance(start_time_result, int) or not isinstance(
            end_time_result, int
        ):
            raise ValueError("Invalid time fields in the event line.")

        self.lines.append(
            Line(
                comment=(event_type == "Comment"),
                layer=int(event_fields[0]),
                start_time=start_time_result,
                end_time=end_time_result,
                style=event_fields[3],
                styleref=self.styles[event_fields[3]],
                actor=event_fields[4],
                margin_l=int(event_fields[5]),
                margin_r=int(event_fields[6]),
                margin_v=int(event_fields[7]),
                effect=event_fields[8],
                raw_text=",".join(event_fields[9:]),
                text="",
                i=line_index,
                duration=-1,
                leadin=float("nan"),
                leadout=float("nan"),
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
        )

    def _process_extended_line_data(self, vertical_kanji: bool) -> None:
        """Process extended line data including positioning, words, syllables, and characters."""
        lines_by_styles = {}

        # Let the fun begin (Pyon!)
        for line in self.lines:
            # Group lines by style for leadin/leadout calculation
            if line.style not in lines_by_styles:
                lines_by_styles[line.style] = []
            lines_by_styles[line.style].append(line)

            line.duration = line.end_time - line.start_time
            line.text = re.sub(r"\{.*?\}", "", line.raw_text)

            # Add dialog text sizes and positions (if possible)
            if line.styleref:
                # Creating a Font object and saving return values of font.get_metrics() for the future
                font = Font(line.styleref)
                font_metrics = font.get_metrics()

                line.width, line.height = font.get_text_extents(line.text)
                (
                    line.ascent,
                    line.descent,
                    line.internal_leading,
                    line.external_leading,
                ) = font_metrics

                if (
                    self.meta.play_res_x is not None
                    and self.meta.play_res_x > 0
                    and self.meta.play_res_y is not None
                    and self.meta.play_res_y > 0
                ):
                    # Horizontal position
                    tmp_margin_l = (
                        line.margin_l if line.margin_l != 0 else line.styleref.margin_l
                    )
                    tmp_margin_r = (
                        line.margin_r if line.margin_r != 0 else line.styleref.margin_r
                    )

                    if (line.styleref.alignment - 1) % 3 == 0:
                        line.left = tmp_margin_l
                        line.center = line.left + line.width / 2
                        line.right = line.left + line.width
                        line.x = line.left
                    elif (line.styleref.alignment - 2) % 3 == 0:
                        line.left = (
                            self.meta.play_res_x / 2
                            - line.width / 2
                            + tmp_margin_l / 2
                            - tmp_margin_r / 2
                        )
                        line.center = line.left + line.width / 2
                        line.right = line.left + line.width
                        line.x = line.center
                    else:
                        line.left = self.meta.play_res_x - tmp_margin_r - line.width
                        line.center = line.left + line.width / 2
                        line.right = line.left + line.width
                        line.x = line.right

                    # Vertical position
                    if line.styleref.alignment > 6:
                        line.top = (
                            line.margin_v
                            if line.margin_v != 0
                            else line.styleref.margin_v
                        )
                        line.middle = line.top + line.height / 2
                        line.bottom = line.top + line.height
                        line.y = line.top
                    elif line.styleref.alignment > 3:
                        line.top = self.meta.play_res_y / 2 - line.height / 2
                        line.middle = line.top + line.height / 2
                        line.bottom = line.top + line.height
                        line.y = line.middle
                    else:
                        line.top = (
                            self.meta.play_res_y
                            - (
                                line.margin_v
                                if line.margin_v != 0
                                else line.styleref.margin_v
                            )
                            - line.height
                        )
                        line.middle = line.top + line.height / 2
                        line.bottom = line.top + line.height
                        line.y = line.bottom

                # Calculating space width and saving spacing
                space_width = font.get_text_extents(" ")[0]
                style_spacing = line.styleref.spacing

                # Adding words
                line.words = []

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

                # Calculate word positions with all words data already available
                if (
                    line.words
                    and line.left
                    and line.right
                    and self.meta.play_res_x is not None
                    and self.meta.play_res_x > 0
                    and self.meta.play_res_y is not None
                    and self.meta.play_res_y > 0
                ):
                    if line.styleref.alignment > 6 or line.styleref.alignment < 4:
                        cur_x = line.left
                        for word in line.words:
                            # Horizontal position
                            cur_x = cur_x + word.prespace * (
                                space_width + style_spacing
                            )

                            word.left = cur_x
                            word.center = word.left + word.width / 2
                            word.right = word.left + word.width

                            if (line.styleref.alignment - 1) % 3 == 0:
                                word.x = word.left
                            elif (line.styleref.alignment - 2) % 3 == 0:
                                word.x = word.center
                            else:
                                word.x = word.right

                            # Vertical position
                            word.top = line.top
                            word.middle = line.middle
                            word.bottom = line.bottom
                            word.y = line.y

                            # Updating cur_x
                            cur_x = (
                                cur_x
                                + word.width
                                + word.postspace * (space_width + style_spacing)
                                + style_spacing
                            )
                    else:
                        max_width, sum_height = 0, 0
                        for word in line.words:
                            max_width = max(max_width, word.width)
                            sum_height = sum_height + word.height

                        cur_y = x_fix = self.meta.play_res_y / 2 - sum_height / 2
                        for word in line.words:
                            # Horizontal position
                            x_fix = (max_width - word.width) / 2

                            if line.styleref.alignment == 4:
                                word.left = line.left + x_fix
                                word.center = word.left + word.width / 2
                                word.right = word.left + word.width
                                word.x = word.left
                            elif line.styleref.alignment == 5:
                                word.left = self.meta.play_res_x / 2 - word.width / 2
                                word.center = word.left + word.width / 2
                                word.right = word.left + word.width
                                word.x = word.center
                            else:
                                word.left = line.right - word.width - x_fix
                                word.center = word.left + word.width / 2
                                word.right = word.left + word.width
                                word.x = word.right

                            # Vertical position
                            word.top = cur_y
                            word.middle = word.top + word.height / 2
                            word.bottom = word.top + word.height
                            word.y = word.middle
                            cur_y = cur_y + word.height

                # Adding syls
                line.syls = []

                # Split raw_text into [('tags', ...), ('text', ...), ...]
                token_pattern = re.compile(r"(\{.*?\})")
                tokens = [
                    (
                        ("tags", part[1:-1])  # ASS override tags (without braces)
                        if part.startswith("{") and part.endswith("}")
                        else ("text", part)  # Plain text
                    )
                    for part in token_pattern.split(line.raw_text)
                    if part
                ]

                # Parse syllable data from tokens
                syllable_data = []
                current_tags = ""
                current_k_tag = None
                current_k_duration = None
                current_text = ""

                for token_type, token_value in tokens:
                    if token_type == "tags":
                        # Find all karaoke tags (\k, \K, \kf, \ko, etc.) in the tag string
                        k_tags = list(
                            re.finditer(r"\\[kK][of]?(\d+)(\\-[^\\}]*)?", token_value)
                        )

                        last_end = 0
                        for k_match in k_tags:
                            # Add any non-karaoke tags before this \k tag
                            non_k_tags = token_value[last_end : k_match.start()]
                            if non_k_tags:
                                current_tags += non_k_tags

                            # If a previous \k tag was open, close the syllable
                            if current_k_tag is not None:
                                syllable_data.append(
                                    {
                                        "tags": current_tags,
                                        "k_tag": current_k_tag,
                                        "k_duration": current_k_duration,
                                        "text": current_text,
                                    }
                                )
                                current_tags = ""
                                current_text = ""

                            # Start a new \k tag
                            k_tag_full = k_match.group(0)
                            current_tags += k_tag_full
                            current_k_tag = k_tag_full
                            current_k_duration = k_match.group(1)

                            last_end = k_match.end()

                        # Add any remaining non-karaoke tags after the last \k tag
                        if last_end < len(token_value):
                            current_tags += token_value[last_end:]

                    else:  # token_type == 'text'
                        current_text += token_value
                        # If a \k tag is active, close the syllable
                        if current_k_tag is not None:
                            syllable_data.append(
                                {
                                    "tags": current_tags,
                                    "k_tag": current_k_tag,
                                    "k_duration": current_k_duration,
                                    "text": current_text,
                                }
                            )
                            current_tags = ""
                            current_k_tag = None
                            current_k_duration = None
                            current_text = ""

                # Add any remaining syllable data
                if current_k_tag is not None or current_text:
                    syllable_data.append(
                        {
                            "tags": current_tags,
                            "k_tag": current_k_tag,
                            "k_duration": current_k_duration,
                            "text": current_text,
                        }
                    )

                # Compute word boundaries for mapping syllables to words
                word_boundaries = []  # Each entry: (start_idx, end_idx, word_i)
                if line.words:
                    idx = 0
                    for w in line.words:
                        prespace = w.prespace
                        postspace = w.postspace
                        word_text = w.text
                        start = idx + prespace
                        end = start + len(word_text)
                        word_boundaries.append((start, end, w.i))
                        idx = end + postspace

                # Build Syllable objects from parsed syllable data
                si = 0
                last_time = 0
                syl_char_idx = 0
                for syl_data in syllable_data:
                    # Extract inline effect (\-EFFECT) if present
                    curr_inline_fx = re.search(r"\\\-([^\s\\}]+)", syl_data["tags"])
                    inline_fx_val = curr_inline_fx.group(1) if curr_inline_fx else ""
                    prespace = len(syl_data["text"]) - len(syl_data["text"].lstrip())
                    postspace = len(syl_data["text"]) - len(syl_data["text"].rstrip())
                    text_stripped = syl_data["text"].strip()

                    # Calculate timing for the syllable
                    if syl_data["k_tag"] is not None:
                        duration = int(syl_data["k_duration"]) * 10
                        end_time = last_time + duration
                    else:
                        duration = 0
                        end_time = last_time

                    # Map syllable to its word index
                    syl_start = syl_char_idx + prespace
                    syl_word_i = 0
                    for start, end, w_i in word_boundaries:
                        if start <= syl_start < end:
                            syl_word_i = w_i
                            break
                    syl_char_idx += prespace + len(text_stripped) + postspace

                    syl = Syllable(
                        i=si,
                        word_i=syl_word_i,
                        start_time=last_time,
                        end_time=end_time,
                        duration=duration,
                        styleref=line.styleref,
                        text=text_stripped,
                        tags=syl_data["tags"],
                        inline_fx=inline_fx_val,
                        prespace=prespace,
                        postspace=postspace,
                        width=font.get_text_extents(text_stripped)[0],
                        height=font.get_text_extents(text_stripped)[1],
                        x=float("nan"),
                        y=float("nan"),
                        left=float("nan"),
                        center=float("nan"),
                        right=float("nan"),
                        top=float("nan"),
                        middle=float("nan"),
                        bottom=float("nan"),
                    )
                    line.syls.append(syl)
                    si += 1
                    last_time = end_time

                # Calculate syllables positions with all syllables data already available
                if (
                    line.syls
                    and line.left
                    and line.center
                    and line.right
                    and self.meta.play_res_x is not None
                    and self.meta.play_res_x > 0
                    and self.meta.play_res_y is not None
                    and self.meta.play_res_y > 0
                ):
                    if (
                        line.styleref.alignment > 6
                        or line.styleref.alignment < 4
                        or not vertical_kanji
                    ):
                        cur_x = line.left
                        for syl in line.syls:
                            cur_x = cur_x + syl.prespace * (space_width + style_spacing)
                            # Horizontal position
                            syl.left = cur_x
                            syl.center = syl.left + syl.width / 2
                            syl.right = syl.left + syl.width

                            if (line.styleref.alignment - 1) % 3 == 0:
                                syl.x = syl.left
                            elif (line.styleref.alignment - 2) % 3 == 0:
                                syl.x = syl.center
                            else:
                                syl.x = syl.right

                            cur_x = (
                                cur_x
                                + syl.width
                                + syl.postspace * (space_width + style_spacing)
                                + style_spacing
                            )

                            # Vertical position
                            syl.top = line.top
                            syl.middle = line.middle
                            syl.bottom = line.bottom
                            syl.y = line.y

                    else:  # Kanji vertical position
                        max_width, sum_height = 0, 0
                        for syl in line.syls:
                            max_width = max(max_width, syl.width)
                            sum_height = sum_height + syl.height

                        cur_y = self.meta.play_res_y / 2 - sum_height / 2

                        for syl in line.syls:
                            # Horizontal position
                            x_fix = (max_width - syl.width) / 2
                            if line.styleref.alignment == 4:
                                syl.left = line.left + x_fix
                                syl.center = syl.left + syl.width / 2
                                syl.right = syl.left + syl.width
                                syl.x = syl.left
                            elif line.styleref.alignment == 5:
                                syl.left = line.center - syl.width / 2
                                syl.center = syl.left + syl.width / 2
                                syl.right = syl.left + syl.width
                                syl.x = syl.center
                            else:
                                syl.left = line.right - syl.width - x_fix
                                syl.center = syl.left + syl.width / 2
                                syl.right = syl.left + syl.width
                                syl.x = syl.right

                            # Vertical position
                            syl.top = cur_y
                            syl.middle = syl.top + syl.height / 2
                            syl.bottom = syl.top + syl.height
                            syl.y = syl.middle
                            cur_y = cur_y + syl.height

                # Adding chars
                line.chars = []

                # If we have syls in line, we prefert to work with them to provide more informations
                if line.syls:
                    words_or_syls = line.syls
                else:
                    words_or_syls = line.words

                # Getting chars
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

                # Calculate character positions with all characters data already available
                if (
                    line.chars
                    and line.left
                    and line.center
                    and line.right
                    and self.meta.play_res_x is not None
                    and self.meta.play_res_x > 0
                    and self.meta.play_res_y is not None
                    and self.meta.play_res_y > 0
                ):
                    if (
                        line.styleref.alignment > 6
                        or line.styleref.alignment < 4
                        or not vertical_kanji
                    ):
                        cur_x = line.left
                        for char in line.chars:
                            # Horizontal position
                            char.left = cur_x
                            char.center = char.left + char.width / 2
                            char.right = char.left + char.width

                            if (line.styleref.alignment - 1) % 3 == 0:
                                char.x = char.left
                            elif (line.styleref.alignment - 2) % 3 == 0:
                                char.x = char.center
                            else:
                                char.x = char.right

                            cur_x = cur_x + char.width + style_spacing

                            # Vertical position
                            char.top = line.top
                            char.middle = line.middle
                            char.bottom = line.bottom
                            char.y = line.y
                    else:
                        max_width, sum_height = 0, 0
                        for char in line.chars:
                            max_width = max(max_width, char.width)
                            sum_height = sum_height + char.height

                        cur_y = x_fix = self.meta.play_res_y / 2 - sum_height / 2

                        # Fixing line positions
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
                                char.center = char.left + char.width / 2
                                char.right = char.left + char.width
                                char.x = char.left
                            elif line.styleref.alignment == 5:
                                char.left = self.meta.play_res_x / 2 - char.width / 2
                                char.center = char.left + char.width / 2
                                char.right = char.left + char.width
                                char.x = char.center
                            else:
                                char.left = line.right - char.width - x_fix
                                char.center = char.left + char.width / 2
                                char.right = char.left + char.width
                                char.x = char.right

                            # Vertical position
                            char.top = cur_y
                            char.middle = char.top + char.height / 2
                            char.bottom = char.top + char.height
                            char.y = char.middle
                            cur_y = cur_y + char.height

        # Add durations between dialogs
        for style in lines_by_styles:
            lines_by_styles[style].sort(key=lambda x: x.start_time)
            for li, line in enumerate(lines_by_styles[style]):
                line.leadin = (
                    1000.1
                    if li == 0
                    else line.start_time - lines_by_styles[style][li - 1].end_time
                )
                line.leadout = (
                    1000.1
                    if li == len(lines_by_styles[style]) - 1
                    else lines_by_styles[style][li + 1].start_time - line.end_time
                )

    def get_data(self) -> tuple[Meta, dict[str, Style], list[Line]]:
        """Utility function to retrieve easily meta styles and lines.

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
        self.__output.append(
            "\n%s: %d,%s,%s,%s,%s,%04d,%04d,%04d,%s,%s"
            % (
                "Comment" if line.comment else "Dialogue",
                line.layer,
                Convert.time(max(0, int(line.start_time))),
                Convert.time(max(0, int(line.end_time))),
                line.style,
                line.actor,
                line.margin_l,
                line.margin_r,
                line.margin_v,
                line.effect,
                line.text,
            )
        )
        self.__plines += 1

    def save(self, quiet: bool = False) -> None:
        """Write everything inside the private output list to a file.

        Parameters:
            quiet (bool): If True, you will not get printed any message.
        """

        # Writing to file
        with open(self.path_output, "w", encoding="utf-8-sig") as f:
            f.writelines(self.__output + ["\n"])
            if self.__output_extradata:
                f.write("\n[Aegisub Extradata]\n")
                f.writelines(self.__output_extradata)

        self.__saved = True

        if not quiet:
            print(
                "Produced lines: %d\nProcess duration (in seconds): %.3f"
                % (self.__plines, time.time() - self.__ptime)
            )

    def open_aegisub(self) -> int:
        """Open the output (specified in self.path_output) with Aegisub.

        This can be usefull if you don't have MPV installed or you want to look at your output in detailed.

        Returns:
            0 if success, -1 if the output couldn't be opened.
        """

        # Check if it was saved
        if not self.__saved:
            print(
                "[WARNING] You've tried to open the output with Aegisub before having saved. Check your code."
            )
            return -1

        if sys.platform == "win32":
            os.startfile(self.path_output)
        else:
            try:
                subprocess.call(["aegisub", os.path.abspath(self.path_output)])
            except FileNotFoundError:
                print("[WARNING] Aegisub not found.")
                return -1

        return 0

    def open_mpv(
        self, video_path: str = "", video_start: str = "", full_screen: bool = False
    ) -> int:
        """Open the output (specified in self.path_output) in softsub with the MPV player.
        To utilize this function, MPV player is required. Additionally if you're on Windows, MPV must be in the PATH (check https://pyonfx.readthedocs.io/en/latest/quick%20start.html#installation-extra-step).

        This is one of the fastest way to reproduce your output in a comfortable way.

        Parameters:
            video_path (string): The video file path (absolute) to reproduce. If not specified, **meta.video** is automatically taken.
            video_start (string): The start time for the video (more info: https://mpv.io/manual/master/#options-start). If not specified, 0 is automatically taken.
            full_screen (bool): If True, it will reproduce the output in full screen. If not specified, False is automatically taken.
        """

        # Check if it was saved
        if not self.__saved:
            print(
                "[ERROR] You've tried to open the output with MPV before having saved. Check your code."
            )
            return -1

        # Check if mpv is usable
        if self.meta.video and self.meta.video.startswith("?dummy") and not video_path:
            print(
                "[WARNING] Cannot use MPV (if you have it in your PATH) for file preview, since your .ass contains a dummy video.\n"
                "You can specify a new video source using video_path parameter, check the documentation of the function."
            )
            return -1

        # Setting up the command to execute
        cmd = ["mpv"]

        if not video_path:
            if self.meta.video:
                cmd.append(self.meta.video)
            else:
                print("[ERROR] No video file specified and meta.video is None.")
                return -1
        else:
            cmd.append(video_path)
        if video_start:
            cmd.append("--start=" + video_start)
        if full_screen:
            cmd.append("--fs")

        cmd.append("--sub-file=" + self.path_output)

        try:
            subprocess.call(cmd)
        except FileNotFoundError:
            print(
                "[WARNING] MPV not found in your environment variables.\n"
                "Please refer to the documentation's \"Quick Start\" section if you don't know how to solve it."
            )
            return -1

        return 0


def pretty_print(
    obj: Meta | Style | Line | Word | Syllable | Char, indent: int = 0, name: str = ""
) -> str:
    # Utility function to print object Meta, Style, Line, Word, Syllable and Char (this is a dirty solution probably)
    if type(obj) == Line:
        out = " " * indent + f"lines[{obj.i}] ({type(obj).__name__}):\n"
    elif type(obj) == Word:
        out = " " * indent + f"words[{obj.i}] ({type(obj).__name__}):\n"
    elif type(obj) == Syllable:
        out = " " * indent + f"syls[{obj.i}] ({type(obj).__name__}):\n"
    elif type(obj) == Char:
        out = " " * indent + f"chars[{obj.i}] ({type(obj).__name__}):\n"
    else:
        out = " " * indent + f"{name}({type(obj).__name__}):\n"

    # Let's print all this object fields
    indent += 4
    for k, v in obj.__dict__.items():
        if "__dict__" in dir(v):
            # Work recursively to print another object
            out += pretty_print(v, indent, k + " ")
        elif type(v) == list:
            for i, el in enumerate(v):
                # Work recursively to print other objects inside a list
                out += pretty_print(el, indent, f"{k}[{i}] ")
        else:
            # Just print a field of this object
            out += " " * indent + f"{k}: {str(v)}\n"

    return out
