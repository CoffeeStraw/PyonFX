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

import re
from typing import Callable, Iterable, Literal, TypeVar

import rpeasings
from tqdm import tqdm
from video_timestamps import ABCTimestamps, TimeType

from .ass_core import Char, Line, Syllable, Word
from .convert import ColorModel, Convert


class Utils:
    """
    This class is a collection of static methods that will help the user in some tasks.
    """

    _LineWordSyllableChar = TypeVar("_LineWordSyllableChar", Line, Word, Syllable, Char)

    @staticmethod
    def progress_bar(
        iterable: Iterable[_LineWordSyllableChar], **kwargs
    ) -> Iterable[_LineWordSyllableChar]:
        """Wrap an iterable of [Line](pyonfx.ass_core.Line), [Word](pyonfx.ass_core.Word), [Syllable](pyonfx.ass_core.Syllable), or [Char](pyonfx.ass_core.Char) with a tqdm progress bar.

        Args:
            iterable: An iterable containing elements of type [Line](pyonfx.ass_core.Line), [Word](pyonfx.ass_core.Word), [Syllable](pyonfx.ass_core.Syllable), or [Char](pyonfx.ass_core.Char).
            **kwargs: Additional arguments passed to the tqdm progress bar.

        Returns:
            Iterable[_LineWordSyllableChar]: An iterator wrapping the original iterable with a tqdm
            progress bar displaying the iteration progress.

        Examples:
            >>> items = [line1, line2, line3]
            >>> for item in Utils.progress_bar(items):
            ...     process(item)

        See Also:
            [all_non_empty](pyonfx.utils.Utils.all_non_empty): Which also uses `progress_bar` for optionally wrapping its returned iterable.
        """
        # Convert to list to support multiple passes and len()
        items = list(iterable)
        if not items:
            return iter([])

        first = items[0]
        obj_name = type(first).__name__.lower()
        if obj_name not in ("line", "word", "syllable", "char"):
            raise TypeError(
                f"with_progress only supports Line, Word, Syllable, or Char (got {type(first)})."
            )
        emoji = {
            "line": "🐰",
            "word": "🔤",
            "syllable": "🎤",
            "char": "🔠",
        }

        return tqdm(
            items,
            desc=kwargs.pop("desc", f"Processed {obj_name}s"),
            unit=kwargs.pop("unit", obj_name),
            leave=kwargs.pop("leave", False),
            ascii=kwargs.pop("ascii", " ▖▘▝▗▚▞█"),
            bar_format=kwargs.pop(
                "bar_format",
                emoji[obj_name]
                + " {desc}: |{bar}| {percentage:3.0f}% [{n_fmt}/{total_fmt}] "
                "⏱️  {elapsed}<{remaining}, {rate_fmt}{postfix}",
            ),
            **kwargs,
        )

    @staticmethod
    def all_non_empty(
        lines_words_syls_or_chars: Iterable[_LineWordSyllableChar],
        *,
        filter_comment: bool = True,
        filter_whitespace_text: bool = True,
        filter_empty_duration: bool = False,
        renumber_indexes: bool = True,
        progress_bar: bool = True,
    ) -> Iterable[_LineWordSyllableChar]:
        """Filter and return non-empty elements from a given iterable.

        Args:
            lines_words_syls_or_chars: An iterable containing elements of type [Line](pyonfx.ass_core.Line), [Word](pyonfx.ass_core.Word), [Syllable](pyonfx.ass_core.Syllable), or [Char](pyonfx.ass_core.Char).
            filter_comment: If True, filters out objects with comments (only applicable for [Line](pyonfx.ass_core.Line) objects).
            filter_whitespace_text: If True, filters out objects whose text attribute is empty or contains only whitespace.
            filter_empty_duration: If True, filters out objects with a duration less than or equal to zero.
            renumber_indexes: If True, reassigns indexes (`i`, `word_i`, `syl_i`) of the filtered objects.
            progress_bar: If True, wraps the resulting iterable with a progress bar for visual feedback.

        Returns:
            Iterable[_LineWordSyllableChar]: An iterator that yields the filtered objects after applying all criteria.

        Examples:
            >>> for item in Utils.all_non_empty(lines):
            ...     print(item.text)

        See Also:
            [progress_bar](pyonfx.utils.Utils.progress_bar): Used to wrap the iterable with a progress indicator.
        """
        out: list[Utils._LineWordSyllableChar] = []
        for obj in lines_words_syls_or_chars:
            empty_for_text = filter_whitespace_text and not obj.text.strip()
            empty_for_duration = filter_empty_duration and obj.duration <= 0
            if empty_for_text or empty_for_duration:
                continue
            if filter_comment and isinstance(obj, Line) and obj.comment:
                continue
            out.append(obj)

        if renumber_indexes:

            def _renumber_attr(attr_name: str) -> None:
                if out and not hasattr(out[0], attr_name):
                    return

                first_seen: dict[int, int] = {}
                next_idx = 0

                for obj in out:
                    old_val = getattr(obj, attr_name)
                    if old_val not in first_seen:
                        first_seen[old_val] = next_idx
                        next_idx += 1
                    setattr(obj, attr_name, first_seen[old_val])

            for secondary in ("i", "word_i", "syl_i"):
                _renumber_attr(secondary)

        if progress_bar:
            return Utils.progress_bar(out)

        return iter(out)

    @staticmethod
    def accelerate(
        pct: float,
        acc: (
            float
            | Literal[
                "in_back",
                "out_back",
                "in_out_back",
                "in_bounce",
                "out_bounce",
                "in_out_bounce",
                "in_circ",
                "out_circ",
                "in_out_circ",
                "in_cubic",
                "out_cubic",
                "in_out_cubic",
                "in_elastic",
                "out_elastic",
                "in_out_elastic",
                "in_expo",
                "out_expo",
                "in_out_expo",
                "in_quad",
                "out_quad",
                "in_out_quad",
                "in_quart",
                "out_quart",
                "in_out_quart",
                "in_quint",
                "out_quint",
                "in_out_quint",
                "in_sine",
                "out_sine",
                "in_out_sine",
            ]
            | Callable[[float], float]
        ) = 1.0,
    ) -> float:
        """Transform a progress percentage using an acceleration function.
        
        Args:
            pct: A float representing the progress percentage, typically between 0.0 and 1.0.
            acc: A float, string, or callable defining the acceleration function. Defaults to 1.0 for linear progression.
                 - If a float is provided, it acts as the exponent for the transformation.
                 - If a string is provided, it must correspond to a preset easing function name as defined in `rpeasings`.
                 - If a callable is provided, it should accept a float and return a transformed float.

        Returns:
            float: The transformed percentage value after applying the acceleration function.
        
        Examples:
            >>> Utils.accelerate(0.5, 2.0)
            0.25
            >>> Utils.accelerate(0.5, "in_expo")
            0.3125
        
        Notes:
            Refer to https://easings.net/ for guidance in choosing among the available easing functions.
        
        See Also:
            [interpolate](pyonfx.utils.Utils.interpolate): Used for interpolating between values with easing.
        """
        if pct == 0.0 or pct == 1.0:
            return pct

        if isinstance(acc, (int, float)):
            fn: Callable[[float], float] = lambda x: x**acc
        elif isinstance(acc, str):
            try:
                fn = getattr(rpeasings, acc)
            except KeyError:
                raise ValueError(f"Unknown easing function: {acc!r}")
        elif callable(acc):
            fn = acc  # Assume it follows the Accelerator protocol
        else:
            raise TypeError("Accelerator must be float, str, or callable")

        return fn(pct)

    _FloatStr = TypeVar("_FloatStr", float, str)

    @staticmethod
    def interpolate(
        pct: float,
        val1: _FloatStr,
        val2: _FloatStr,
        acc: (
            float
            | Literal[
                "in_back",
                "out_back",
                "in_out_back",
                "in_bounce",
                "out_bounce",
                "in_out_bounce",
                "in_circ",
                "out_circ",
                "in_out_circ",
                "in_cubic",
                "out_cubic",
                "in_out_cubic",
                "in_elastic",
                "out_elastic",
                "in_out_elastic",
                "in_expo",
                "out_expo",
                "in_out_expo",
                "in_quad",
                "out_quad",
                "in_out_quad",
                "in_quart",
                "out_quart",
                "in_out_quart",
                "in_quint",
                "out_quint",
                "in_out_quint",
                "in_sine",
                "out_sine",
                "in_out_sine",
            ]
            | Callable[[float], float]
        ) = 1.0,
    ) -> _FloatStr:
        """Interpolate between two values with an optional acceleration (easing) function.
        
        Args:
            pct: A float in the range [0.0, 1.0] representing the interpolation factor.
            val1: The starting value (ASS color, ASS alpha channel or number) for interpolation.
            val2: The ending value (ASS color, ASS alpha channel or number) for interpolation.
            acc: A float, string, or callable defining the acceleration function. Defaults to 1.0 for linear progression.
                 - If a float is provided, it acts as the exponent for the transformation.
                 - If a string is provided, it must correspond to a preset easing function name as defined in `rpeasings`.
                 - If a callable is provided, it should accept a float and return a transformed float.

        Returns:
            The interpolated value, either a number or a string, matching the type of `val1` and `val2`.
        
        Examples:
            >>> Utils.interpolate(0.5, 10, 20)
            15.0
            >>> Utils.interpolate(0.9, "&HFFFFFF&", "&H000000&")
            &HE5E5E5&
            >>> Utils.interpolate(0.5, 10, 20, "ease-in")
            13.05
            >>> Utils.interpolate(0.5, 10, 20, 2.0)
            12.5
        
        Notes:
            Refer to https://easings.net/ for guidance in choosing among the available easing functions.
        
        See Also:
            [accelerate](pyonfx.utils.Utils.accelerate): Used to transform percentage values with easing.
        """
        if pct > 1.0 or pct < 0:
            raise ValueError(
                f"Percent value must be a float between 0.0 and 1.0, but yours was {pct}"
            )

        # Apply acceleration function
        pct = Utils.accelerate(pct, acc)

        def interpolate_numbers(val1: float, val2: float) -> float:
            nonlocal pct
            return val1 + (val2 - val1) * pct

        # Interpolating
        if isinstance(val1, str) and isinstance(val2, str):
            if len(val1) != len(val2):
                raise ValueError(
                    "ASS values must have the same type (either two alphas, two colors or two colors+alpha)."
                )
            if len(val1) == len("&HXX&"):
                val1_dec = Convert.alpha_ass_to_dec(val1)
                val2_dec = Convert.alpha_ass_to_dec(val2)
                a = interpolate_numbers(val1_dec, val2_dec)
                return Convert.alpha_dec_to_ass(a)
            elif len(val1) == len("&HBBGGRR&"):
                val1_rgb = Convert.color_ass_to_rgb(val1)
                val2_rgb = Convert.color_ass_to_rgb(val2)
                if isinstance(val1_rgb, tuple) and isinstance(val2_rgb, tuple):
                    rgb = tuple(
                        int(interpolate_numbers(v1, v2))
                        for v1, v2 in zip(val1_rgb, val2_rgb)
                    )
                    if len(rgb) == 3:
                        return Convert.color_rgb_to_ass(rgb)
                raise ValueError("Invalid RGB color conversion")
            elif len(val1) == len("&HAABBGGRR"):
                val1_rgba = Convert.color(val1, ColorModel.ASS, ColorModel.RGBA)
                val2_rgba = Convert.color(val2, ColorModel.ASS, ColorModel.RGBA)
                if isinstance(val1_rgba, tuple) and isinstance(val2_rgba, tuple):
                    rgba = tuple(
                        interpolate_numbers(v1, v2)
                        for v1, v2 in zip(val1_rgba, val2_rgba)
                    )
                    if len(rgba) == 4:
                        result = Convert.color(rgba, ColorModel.RGBA, ColorModel.ASS)
                        if isinstance(result, str):
                            return result
                raise ValueError("Invalid RGBA color conversion")
            else:
                raise ValueError(
                    f"Provided inputs '{val1}' and '{val2}' are not valid ASS strings."
                )
        elif isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
            return interpolate_numbers(float(val1), float(val2))
        else:
            raise TypeError(
                "Invalid input(s) type, either pass two strings or two numbers."
            )

    @staticmethod
    def retime(
        mode: Literal[
            "syl",
            "presyl",
            "postsyl",
            "line",
            "preline",
            "postline",
            "start2syl",
            "syl2end",
            "set",
            "abs",
            "sylpct",
        ],
        line: Line,
        word_syl_or_char: Word | Syllable | Char | None = None,
        *,
        offset_start=0,
        offset_end=0,
    ):
        """Adjust the timing of a subtitle line based on a specified mode.
        
        Args:
            mode: A string literal indicating the retime mode. Each mode applies a different timing adjustment strategy.
            line: The subtitle line object whose `start_time` and `end_time` will be adjusted.
            word_syl_or_char: An optional element ([Word](pyonfx.ass_core.Word), [Syllable](pyonfx.ass_core.Syllable), or [Char](pyonfx.ass_core.Char))
                              providing timing reference for modes that require relative timing. Must be provided for modes other than
                              "line", "preline", "postline", "set", and "abs".
            offset_start: An optional integer offset (in milliseconds) to add to the computed start time.
            offset_end: An optional integer offset (in milliseconds) to add to the computed end time.
        
        Examples:
            >>> # Retiming a line based on the timing of a syllable
            >>> Utils.retime("syl", line, syl, offset_start=10, offset_end=5)
            >>> # Retiming a line to keep its original timing (no adjustment)
            >>> Utils.retime("line", line)
        
        See Also:
            [kara-templater retime implementation](https://github.com/slackingway/karaOK/blob/master/autoload/ln.kara-templater-mod.lua#L352)
        """
        if mode == "syl":
            if word_syl_or_char is None:
                raise ValueError("word_syl_or_char must be provided for mode 'syl'")
            new_start = line.start_time + word_syl_or_char.start_time
            new_end = line.start_time + word_syl_or_char.end_time
        elif mode == "presyl":
            if word_syl_or_char is None:
                raise ValueError("word_syl_or_char must be provided for mode 'presyl'")
            new_start = line.start_time + word_syl_or_char.start_time
            new_end = line.start_time + word_syl_or_char.start_time
        elif mode == "postsyl":
            if word_syl_or_char is None:
                raise ValueError("word_syl_or_char must be provided for mode 'postsyl'")
            new_start = line.start_time + word_syl_or_char.end_time
            new_end = line.start_time + word_syl_or_char.end_time
        elif mode == "line":
            new_start = line.start_time
            new_end = line.end_time
        elif mode == "preline":
            new_start = line.start_time
            new_end = line.start_time
        elif mode == "postline":
            new_start = line.end_time
            new_end = line.end_time
        elif mode == "start2syl":
            if word_syl_or_char is None:
                raise ValueError(
                    "word_syl_or_char must be provided for mode 'start2syl'"
                )
            new_start = line.start_time
            new_end = line.start_time + word_syl_or_char.start_time
        elif mode == "syl2end":
            if word_syl_or_char is None:
                raise ValueError("word_syl_or_char must be provided for mode 'syl2end'")
            new_start = line.start_time + word_syl_or_char.end_time
            new_end = line.end_time
        elif mode in ("set", "abs"):
            new_start = 0
            new_end = 0
        elif mode == "sylpct":
            if word_syl_or_char is None:
                raise ValueError("word_syl_or_char must be provided for mode 'sylpct'")
            new_start = (
                line.start_time
                + word_syl_or_char.start_time
                + int(offset_start * word_syl_or_char.duration / 100)
            )
            new_end = (
                line.start_time
                + word_syl_or_char.start_time
                + int(offset_end * word_syl_or_char.duration / 100)
            )
        else:
            raise ValueError(f"Unknown retime mode: {mode}")

        if mode != "sylpct":
            new_start += offset_start
            new_end += offset_end

        line.start_time = new_start
        line.end_time = new_end


class FrameUtility:
    """Provide an accurate frame-by-frame iteration engine for subtitle processing.
    
    This class enables precise operations on video frames by dividing a time interval (from `start_ms` to `end_ms`)
    into discrete frame segments based on a given timestamps object. It calculates the corresponding frame indices and yields
    a tuple for each frame segment containing:
      - The start time of the frame segment (in milliseconds).
      - The end time of the frame segment (in milliseconds), clamped to the video duration.
      - The current frame index (starting at 1).
      - The total number of frame segments.
    
    Examples:
        >>> # Assume `io.input_timestamps` is an instance of ABCTimestamps and the video has a 20 fps frame rate (50 ms per frame)
        >>> FU = FrameUtility(0, 110, io.input_timestamps)
        >>> for s, e, i, n in FU:
        ...     print(f"Frame {i}/{n}: {s} - {e}")
        Frame 1/3: 0 - 25
        Frame 2/3: 25 - 75
        Frame 3/3: 75 - 125
    
    Notes:
        A mid-point approach is used to center each frame's timing around the player's seek time, ensuring that subtitles
        remain visible throughout the entire frame duration. This method is reliable for both constant frame rate (CFR) and
        variable frame rate (VFR) videos.
    """

    def __init__(
        self,
        start_ms: int,
        end_ms: int,
        timestamps: ABCTimestamps | None,
        n_fr: int = 1,
    ):
        """Initialize the FrameUtility object.

        Args:
            start_ms: A positive integer representing the starting time (in milliseconds) of the interval.
            end_ms: A positive integer representing the ending time (in milliseconds) of the interval.
            timestamps: An instance of `ABCTimestamps` used to convert between time values and frame numbers.
            n_fr: An optional positive integer specifying the number of frames to process per iteration (default is 1).
        """
        # Check for invalid values
        if start_ms < 0 or end_ms < 0:
            raise ValueError("Parameters 'start_ms' and 'end_ms' must be >= 0.")
        if end_ms < start_ms:
            raise ValueError("Parameter 'start_ms' is expected to be <= 'end_ms'.")
        if n_fr <= 0:
            raise ValueError("Parameter 'n_fr' must be > 0.")
        if timestamps is None:
            raise ValueError(
                "Parameter 'timestamps' cannot be None (hint: does your ASS file have a video specified?)."
            )

        self.timestamps = timestamps
        self.start_ms = start_ms
        self.end_ms = end_ms

        self.start_fr = self.curr_fr = timestamps.time_to_frame(
            start_ms, TimeType.START, 3
        )
        self.end_fr = timestamps.time_to_frame(end_ms, TimeType.END, 3)
        self.end_ms_snapped = timestamps.frame_to_time(
            self.end_fr, TimeType.END, 3, True
        )
        self.n_fr = n_fr
        self.i = 0
        self.n = self.end_fr - self.start_fr + 1

    def __iter__(self):
        # Generate values for the frames on demand. The end time is always clamped to the end_ms value.
        for self.i in range(0, self.n, self.n_fr):
            yield (
                self.timestamps.frame_to_time(self.curr_fr, TimeType.START, 3, True),
                min(
                    self.timestamps.frame_to_time(
                        self.curr_fr + self.n_fr - 1, TimeType.END, 3, True
                    ),
                    self.end_ms_snapped,
                ),
                self.i + 1,
                self.n,
            )
            self.curr_fr += self.n_fr

        # Reset the object to make it usable again
        self.reset()

    def reset(self):
        """Reset the frame utility to its initial state."""
        self.i = 0
        self.curr_fr = self.start_fr

    def add(
        self,
        start_time: float,
        end_time: float,
        end_value: float,
        acc: (
            float
            | Literal[
                "in_back",
                "out_back",
                "in_out_back",
                "in_bounce",
                "out_bounce",
                "in_out_bounce",
                "in_circ",
                "out_circ",
                "in_out_circ",
                "in_cubic",
                "out_cubic",
                "in_out_cubic",
                "in_elastic",
                "out_elastic",
                "in_out_elastic",
                "in_expo",
                "out_expo",
                "in_out_expo",
                "in_quad",
                "out_quad",
                "in_out_quad",
                "in_quart",
                "out_quart",
                "in_out_quart",
                "in_quint",
                "out_quint",
                "in_out_quint",
                "in_sine",
                "out_sine",
                "in_out_sine",
            ]
            | Callable[[float], float]
        ) = 1.0,
    ) -> float:
        """Apply a frame-by-frame numeric transformation similar to the ASS '\\t' tag.
        
        This method computes an adjustment value for the current frame by interpolating between 0 and `end_value` over a
        specified time interval defined by `start_time` and `end_time`. Mimicking the behavior of the ASS '\\t' tag,
        it calculates the interpolation progress based on the midpoint of the current frame within the interval and applies
        an optional acceleration (easing) function (`acc`) to modulate the transformation.
        
        Args:
            start_time: The start time (in milliseconds) of the transformation interval.
            end_time: The end time (in milliseconds) of the transformation interval.
            end_value: The final adjustment value to be reached at the end of the interval.
            acc: A float, string, or callable defining the acceleration function. Defaults to 1.0 for linear progression.
                 - If a float is provided, it acts as the exponent for the transformation.
                 - If a string is provided, it must correspond to a preset easing function name as defined in `rpeasings`.
                 - If a callable is provided, it should accept a float and return a transformed float.

        Returns:
            float: The computed adjustment value for the current frame.
        
        Examples:
            >>> # Let's assume to have an Ass object named "io" having a 20 fps video (i.e. frames are 50 ms long)
            >>> FU = FrameUtility(25, 225, io.input_timestamps)
            >>> for s, e, i, n in FU:
            ...     # We would like to transform the fsc value
            ...     # from 100 up 150 for the first 100 ms,
            ...     # and then from 150 to 100 for the remaining 200 ms
            ...     fsc = 100
            ...     fsc += FU.add(0, 100, 50)
            ...     fsc += FU.add(100, 200, -50)
            ...     print(f"Frame {i}/{n}: {s} - {e}; fsc: {fsc}")
            Frame 1/4: 25 - 75; fsc: 112.5
            Frame 2/4: 75 - 125; fsc: 137.5
            Frame 3/4: 125 - 175; fsc: 137.5
            Frame 4/4: 175 - 225; fsc: 112.5
        
        Notes:
            This method should be used within a loop iterating a FrameUtility object.

        See Also:
            [Utils.accelerate](pyonfx.utils.Utils.accelerate): For transforming percentage values with easing.
        """
        curr_ms = self.timestamps.frame_to_time(
            self.i + (self.n_fr - 1) // 2, TimeType.END, 3, True
        )

        if curr_ms <= start_time:
            return 0
        elif curr_ms >= end_time:
            return end_value

        curr = curr_ms - start_time
        total = end_time - start_time
        return Utils.interpolate(curr / total, 0, end_value, acc)


class ColorUtility:
    """Extract and manage color transformations from ASS subtitle lines.

    Parses ASS Line objects to extract color change commands (\\1c, \\3c, \\4c) 
    and their transformations (\\t tags), and provides interpolated color values
    for smooth transitions during subtitle rendering.
    
    Examples:
        >>> cu = ColorUtility(subtitle_lines)
        >>> color_tags = cu.get_color_change(current_line)
        >>> print(f"Color tags: {color_tags}")
        \\1c&HFFFFFF&\\t(100,200,\\1c&H000000&)
    
    Notes:
        - Create only one ColorUtility instance per ASS file for optimal performance.
        - Lines without explicit colors inherit from the last defined color state.
        
    See Also:
        `Utils.interpolate` for color interpolation between ASS color values.
    """

    def __init__(self, lines: list[Line], offset: int = 0):
        """Initialize the ColorUtility object.

        Args:
            lines: A list of Line objects representing the subtitle lines to be analyzed for color changes.
            offset: An optional integer (in milliseconds) to shift all color change timings, useful for synchronization.
        """
        self.color_changes = []
        self.c1_req = False
        self.c3_req = False
        self.c4_req = False

        # Compiling regex
        tag_all = re.compile(r"{.*?}")
        tag_t = re.compile(r"\\t\( *?(-?\d+?) *?, *?(-?\d+?) *?, *(.+?) *?\)")
        tag_c1 = re.compile(r"\\1c(&H.{6}&)")
        tag_c3 = re.compile(r"\\3c(&H.{6}&)")
        tag_c4 = re.compile(r"\\4c(&H.{6}&)")

        for line in lines:
            # Obtaining all tags enclosured in curly brackets
            tags = tag_all.findall(line.raw_text)

            # Let's search all color changes in the tags
            for tag in tags:
                # Get everything beside \t to see if there are some colors there
                other_tags = tag_t.sub("", tag)

                # Searching for colors in the other tags
                c1, c3, c4 = (
                    tag_c1.search(other_tags),
                    tag_c3.search(other_tags),
                    tag_c4.search(other_tags),
                )

                # If we found something, add to the list as a color change
                if c1 or c3 or c4:
                    if c1:
                        c1 = c1.group(0)
                        self.c1_req = True
                    if c3:
                        c3 = c3.group(0)
                        self.c3_req = True
                    if c4:
                        c4 = c4.group(0)
                        self.c4_req = True

                    self.color_changes.append(
                        {
                            "start": line.start_time + offset,
                            "end": line.start_time + offset,
                            "acc": 1,
                            "c1": c1,
                            "c3": c3,
                            "c4": c4,
                        }
                    )

                # Find all transformation in tag
                ts = tag_t.findall(tag)

                # Working with each transformation
                for t in ts:
                    # Parsing start, end, optional acceleration and colors
                    start, end, acc_colors = int(t[0]), int(t[1]), t[2].split(",")
                    acc, c1, c3, c4 = 1, None, None, None

                    # Do we have also acceleration?
                    if len(acc_colors) == 1:
                        c1, c3, c4 = (
                            tag_c1.search(acc_colors[0]),
                            tag_c3.search(acc_colors[0]),
                            tag_c4.search(acc_colors[0]),
                        )
                    elif len(acc_colors) == 2:
                        acc = float(acc_colors[0])
                        c1, c3, c4 = (
                            tag_c1.search(acc_colors[1]),
                            tag_c3.search(acc_colors[1]),
                            tag_c4.search(acc_colors[1]),
                        )
                    else:
                        # This transformation is malformed (too many ','), let's skip this
                        continue

                    # If found, extract from groups
                    if c1:
                        c1 = c1.group(0)
                        self.c1_req = True
                    if c3:
                        c3 = c3.group(0)
                        self.c3_req = True
                    if c4:
                        c4 = c4.group(0)
                        self.c4_req = True

                    # Saving in the list
                    self.color_changes.append(
                        {
                            "start": line.start_time + start + offset,
                            "end": line.start_time + end + offset,
                            "acc": acc,
                            "c1": c1,
                            "c3": c3,
                            "c4": c4,
                        }
                    )

    def get_color_change(
        self,
        line: Line,
        c1: bool | None = None,
        c3: bool | None = None,
        c4: bool | None = None,
    ) -> str:
        """Generate color transformation tags for a subtitle line's time range.
        
        Returns interpolated color changes that occur within the line's time span,
        including base colors and transformation tags. Automatically inherits colors
        from previous lines when not explicitly overridden.
        
        Args:
            line: [Line](pyonfx.ass_core.Line) object containing timing and style information.
            c1: Include primary color changes. Auto-detected if None.
            c3: Include border color changes. Auto-detected if None.
            c4: Include shadow color changes. Auto-detected if None.
        
        Returns:
            str: ASS-formatted color tags for the line (e.g., "\\1c&HFFFFFF&\\t(100,200,\\1c&H000000&)").
        
        Examples:
            >>> line.start_time, line.end_time = 1000, 2000
            >>> cu.get_color_change(line)
            "\\1c&HFFFFFF&\\3c&H000000&\\t(500,1000,\\1c&H000000&\\3c&HFFFFFF&)"
            >>> cu.get_color_change(line, c1=True, c3=False, c4=False)
            "\\1c&HFFFFFF&\\t(500,1000,\\1c&H000000&)"
        
        See Also:
            [get_fr_color_change](pyonfx.utils.ColorUtility.get_fr_color_change) for frame-by-frame color values.
        """
        transform = ""

        # If we don't have user's settings, we set c values
        # to the ones that we previously saved
        c1 = self.c1_req if c1 is None else c1
        c3 = self.c3_req if c3 is None else c3
        c4 = self.c4_req if c4 is None else c4

        if line.styleref is None:
            raise ValueError("Line has no styleref")

        # Reading default colors
        base_c1 = "\\1c" + line.styleref.color1
        base_c3 = "\\3c" + line.styleref.color3
        base_c4 = "\\4c" + line.styleref.color4

        for color_change in self.color_changes:
            if color_change["end"] <= line.start_time:
                # Get base colors from this color change, since it is before my current line
                # Last color change written in .ass wins
                if color_change["c1"]:
                    base_c1 = color_change["c1"]
                if color_change["c3"]:
                    base_c3 = color_change["c3"]
                if color_change["c4"]:
                    base_c4 = color_change["c4"]
            elif color_change["start"] <= line.end_time:
                # We have found a valid color change, append it to the transform
                start_time = color_change["start"] - line.start_time
                end_time = color_change["end"] - line.start_time

                # We don't want to have times = 0
                start_time = 1 if start_time == 0 else start_time
                end_time = 1 if end_time == 0 else end_time

                transform += "\\t(%d,%d," % (start_time, end_time)

                if color_change["acc"] != 1:
                    transform += str(color_change["acc"])

                if c1 and color_change["c1"]:
                    transform += color_change["c1"]
                if c3 and color_change["c3"]:
                    transform += color_change["c3"]
                if c4 and color_change["c4"]:
                    transform += color_change["c4"]

                transform += ")"

        # Appending default color found, if requested
        if c4:
            transform = base_c4 + transform
        if c3:
            transform = base_c3 + transform
        if c1:
            transform = base_c1 + transform

        return transform

    def get_fr_color_change(
        self,
        line: Line,
        c1: bool | None = None,
        c3: bool | None = None,
        c4: bool | None = None,
    ) -> str:
        """Get interpolated color values for a specific frame time.
        
        Returns the exact color values at line.start_time by interpolating between
        color transformations. Essential for frame-by-frame rendering where you need
        precise color values at specific moments.
        
        Args:
            line: [Line](pyonfx.ass_core.Line) object where start_time represents the current frame time.
            c1: Include primary color interpolation. Auto-detected if None.
            c3: Include border color interpolation. Auto-detected if None. 
            c4: Include shadow color interpolation. Auto-detected if None.
        
        Returns:
            str: Interpolated ASS color tags for the exact frame time (e.g., "\\1c&H808080&").
        
        Examples:
            >>> line.start_time = 1500  # Frame at 1.5 seconds
            >>> cu.get_fr_color_change(line)
            "\\1c&H808080&\\3c&HFF0000&"
            >>> cu.get_fr_color_change(line, c1=True, c3=False)
            "\\1c&H808080&"
        
        See Also:
            [get_color_change](pyonfx.utils.ColorUtility.get_color_change) for complete transformation sequences over time ranges.
        """
        # If we don't have user's settings, we set c values
        # to the ones that we previously saved
        c1 = self.c1_req if c1 is None else c1
        c3 = self.c3_req if c3 is None else c3
        c4 = self.c4_req if c4 is None else c4

        if line.styleref is None:
            raise ValueError("Line has no styleref")

        # Reading default colors
        base_c1 = "\\1c" + line.styleref.color1
        base_c3 = "\\3c" + line.styleref.color3
        base_c4 = "\\4c" + line.styleref.color4

        # Searching valid color_change
        current_time = line.start_time
        latest_index = -1

        for i, color_change in enumerate(self.color_changes):
            if current_time >= color_change["start"]:
                latest_index = i

        # If no color change is found, take default from style
        if latest_index == -1:
            colors = ""
            if c1:
                colors += base_c1
            if c3:
                colors += base_c3
            if c4:
                colors += base_c4
            return colors

        # If we have passed the end of the lastest color change available, then take the final values of it
        if current_time >= self.color_changes[latest_index]["end"]:
            colors = ""
            if c1 and self.color_changes[latest_index]["c1"]:
                colors += self.color_changes[latest_index]["c1"]
            if c3 and self.color_changes[latest_index]["c3"]:
                colors += self.color_changes[latest_index]["c3"]
            if c4 and self.color_changes[latest_index]["c4"]:
                colors += self.color_changes[latest_index]["c4"]
            return colors

        # Else, interpolate the latest color change
        start = current_time - self.color_changes[latest_index]["start"]
        end = (
            self.color_changes[latest_index]["end"]
            - self.color_changes[latest_index]["start"]
        )
        pct = start / end

        # If we're in the first color_change, interpolate with base colors
        if latest_index == 0:
            colors = ""
            if c1 and self.color_changes[latest_index]["c1"]:
                colors += "\\1c" + Utils.interpolate(
                    pct,
                    base_c1[3:],
                    self.color_changes[latest_index]["c1"][3:],
                    self.color_changes[latest_index]["acc"],
                )
            if c3 and self.color_changes[latest_index]["c3"]:
                colors += "\\3c" + Utils.interpolate(
                    pct,
                    base_c3[3:],
                    self.color_changes[latest_index]["c3"][3:],
                    self.color_changes[latest_index]["acc"],
                )
            if c4 and self.color_changes[latest_index]["c4"]:
                colors += "\\4c" + Utils.interpolate(
                    pct,
                    base_c4[3:],
                    self.color_changes[latest_index]["c4"][3:],
                    self.color_changes[latest_index]["acc"],
                )
            return colors

        # Else, we interpolate between current color change and previous
        colors = ""
        if c1:
            colors += "\\1c" + Utils.interpolate(
                pct,
                self.color_changes[latest_index - 1]["c1"][3:],
                self.color_changes[latest_index]["c1"][3:],
                self.color_changes[latest_index]["acc"],
            )
        if c3:
            colors += "\\3c" + Utils.interpolate(
                pct,
                self.color_changes[latest_index - 1]["c3"][3:],
                self.color_changes[latest_index]["c3"][3:],
                self.color_changes[latest_index]["acc"],
            )
        if c4:
            colors += "\\4c" + Utils.interpolate(
                pct,
                self.color_changes[latest_index - 1]["c4"][3:],
                self.color_changes[latest_index]["c4"][3:],
                self.color_changes[latest_index]["acc"],
            )
        return colors
