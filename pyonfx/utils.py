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
import re
from typing import overload, TYPE_CHECKING
from video_timestamps import ABCTimestamps, TimeType

from .convert import Convert, ColorModel

if TYPE_CHECKING:
    from .ass_core import Line, Word, Syllable, Char


class Utils:
    """
    This class is a collection of static methods that will help the user in some tasks.
    """

    @overload
    @staticmethod
    def all_non_empty(
        lines_chars_syls_or_words: list[Line],
    ) -> list[Line]: ...

    @overload
    @staticmethod
    def all_non_empty(
        lines_chars_syls_or_words: list[Word],
    ) -> list[Word]: ...

    @overload
    @staticmethod
    def all_non_empty(
        lines_chars_syls_or_words: list[Syllable],
    ) -> list[Syllable]: ...

    @overload
    @staticmethod
    def all_non_empty(
        lines_chars_syls_or_words: list[Char],
    ) -> list[Char]: ...

    @staticmethod
    def all_non_empty(
        lines_chars_syls_or_words: (
            list[Line] | list[Word] | list[Syllable] | list[Char]
        ),
    ) -> list[Line] | list[Word] | list[Syllable] | list[Char]:
        """
        Helps to not check everytime for text containing only spaces or object's duration equals to zero.

        Parameters:
            lines_chars_syls_or_words (list of :class:`Line<pyonfx.ass_utility.Line>`, :class:`Char<pyonfx.ass_utility.Char>`, :class:`Syllable<pyonfx.ass_utility.Syllable>` or :class:`Word<pyonfx.ass_utility.Word>`)

        Returns:
            A list containing lines_chars_syls_or_words without objects with duration equals to zero or blank text (no text or only spaces).
        """
        out = []
        for obj in lines_chars_syls_or_words:
            if obj.text.strip() and obj.duration > 0:
                out.append(obj)
        return out

    @staticmethod
    def clean_tags(text: str) -> str:
        # TODO: Cleans up ASS subtitle lines of badly-formed override. Returns a cleaned up text.
        return ""

    @staticmethod
    def accelerate(pct: float, accelerator: float) -> float:
        # Modifies pct according to the acceleration provided.
        # TODO: Implement acceleration based on bezier's curve
        return pct**accelerator

    @overload
    @staticmethod
    def interpolate(
        pct: float,
        val1: float,
        val2: float,
        acc: float = 1.0,
    ) -> float: ...

    @overload
    @staticmethod
    def interpolate(
        pct: float,
        val1: str,
        val2: str,
        acc: float = 1.0,
    ) -> str: ...

    @staticmethod
    def interpolate(
        pct: float,
        val1: float | str,
        val2: float | str,
        acc: float = 1.0,
    ) -> str | float:
        """
        | Interpolates 2 given values (ASS colors, ASS alpha channels or numbers) by percent value as decimal number.
        | You can also provide a http://cubic-bezier.com to accelerate based on bezier curves. (TO DO)
        |
        | You could use that for the calculation of color/alpha gradients.

        Parameters:
            pct (float): Percent value of the interpolation.
            val1 (int, float or str): First value to interpolate (either string or number).
            val2 (int, float or str): Second value to interpolate (either string or number).
            acc (float, optional): Optional acceleration that influences final percent value.

        Returns:
            Interpolated value of given 2 values (so either a string or a number).

        Examples:
            ..  code-block:: python3

                print( Utils.interpolate(0.5, 10, 20) )
                print( Utils.interpolate(0.9, "&HFFFFFF&", "&H000000&") )

            >>> 15
            >>> &HE5E5E5&
        """
        if pct > 1.0 or pct < 0:
            raise ValueError(
                f"Percent value must be a float between 0.0 and 1.0, but yours was {pct}"
            )

        # Calculating acceleration (if requested)
        pct = Utils.accelerate(pct, acc) if acc != 1.0 else pct

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
                        interpolate_numbers(v1, v2)
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


class FrameUtility:
    """This class allows to accurately work in a frame per frame environment.

    You can use it to iterate over the frames going from ``start_ms``
    to ``end_ms`` and perform operations easily over multiple frames.

    Parameters:
        start_ms (positive int): Initial time in ms.
        end_ms (positive int): Final time in ms.
        timestamps (ABCTimestamps): A timestamps object from [VideoTimestamps](https://github.com/moi15moi/VideoTimestamps/).
        n_fr (positive int, optional): Number of frames covered by each iteration.

    Returns:
        Returns a Generator yielding start_ms, end_ms, current frame index and total number of frames at each step.

    Example:
        >>> # Let's assume to have an Ass object named "io" having a 20 fps video (i.e. frames are 50 ms long)
        >>> FU = FrameUtility(0, 110, io.input_timestamps)
        >>> for s, e, i, n in FU:
        >>>     print(f"Frame {i}/{n}: {s} - {e}")
        >>>
        >>> Frame 1/3: 0 - 25
        >>> Frame 2/3: 25 - 75
        >>> Frame 3/3: 75 - 125

    Note:
        Understanding FrameUtility:

        When playing a video with subtitles (e.g., an .mkv file):
        - A subtitle line is displayed when the player's current time falls between the line's start and end times
        - Videos can have either constant frame rates (CFR) or variable frame rates (VFR)

        Example with a CFR video at 20 fps (50ms per frame):
        - Player seeks frames at: 0ms, 50ms, 100ms, 150ms, ...

        When generating subtitle lines per frame, FrameUtility uses a "mid-point" approach:
        - Each frame's timing is centered around the player's seek time
        - This ensures the subtitle will be visible for the entire frame duration

        Frame timings example:
        Frame #: Start - End (Player's seek time)
        Frame 0:   0 -  25 (0, special case)
        Frame 1:  25 -  75 (50)
        Frame 2:  75 - 125 (100)
        Frame 3: 125 - 175 (150)
        ...

        This approach:
        - Ensures smooth frame transitions
        - Avoids flickering by avoiding gaps between frames
        - Works reliably for both CFR and VFR videos
    """

    def __init__(
        self,
        start_ms: int,
        end_ms: int,
        timestamps: ABCTimestamps,
        n_fr: int = 1,
    ):
        # Check for invalid values
        if start_ms < 0 or end_ms < 0:
            raise ValueError("Parameters 'start_ms' and 'end_ms' must be >= 0.")
        if end_ms < start_ms:
            raise ValueError("Parameter 'start_ms' is expected to be <= 'end_ms'.")
        if n_fr <= 0:
            raise ValueError("Parameter 'n_fr' must be > 0.")

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
        """
        Resets the FrameUtility object to its starting values.
        It is a mandatory operation if you want to reuse the same object.
        """
        self.i = 0
        self.curr_fr = self.start_fr

    def add(
        self,
        start_time: float,
        end_time: float,
        end_value: float,
        accelerator: float = 1.0,
    ) -> float:
        """Frame-by-frame equivalent of the ASS ``\\t`` tag.

        This function provides a frame-accurate way to transform numeric values over time,
        similar to how the ASS ``\\t`` tag transforms styles. While ``\\t`` handles complete
        style transformations, this method focuses on transforming individual numeric values
        that can then be used within style tags.

        Note:
            Must be used within a for loop iterating a FrameUtility object.

        Parameters:
            start_time (float): Initial time.
            end_time (float): Final time.
            end_value (float): Numeric value reached at end_time.
            accelerator (float): Accelerator value.

        Returns:
            The transformed numeric value at the current frame of this FrameUtility object.

        Examples:
            >>> # Let's assume to have an Ass object named "io" having a 20 fps video (i.e. frames are 50 ms long)
            >>> FU = FrameUtility(25, 225, io.input_timestamps)
            >>> for s, e, i, n in FU:
            >>>     # We would like to transform the fsc value
            >>>     # from 100 up 150 for the first 100 ms,
            >>>     # and then from 150 to 100 for the remaining 200 ms
            >>>     fsc = 100
            >>>     fsc += FU.add(0, 100, 50)
            >>>     fsc += FU.add(100, 200, -50)
            >>>     print(f"Frame {i}/{n}: {s} - {e}; fsc: {fsc}")
            >>>
            >>> Frame 1/4: 25 - 75; fsc: 112.5
            >>> Frame 2/4: 75 - 125; fsc: 137.5
            >>> Frame 3/4: 125 - 175; fsc: 137.5
            >>> Frame 4/4: 175 - 225; fsc: 112.5
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
        return Utils.interpolate(curr / total, 0, end_value, accelerator)


class ColorUtility:
    """
    This class helps to obtain all the color transformations written in a list of lines
    (usually all the lines of your input .ass)
    to later retrieve all of those transformations that fit between the start_time and end_time of a line passed,
    without having to worry about interpolating times or other stressfull tasks.

    It is highly suggested to create this object just one time in your script, for performance reasons.

    Note:
        A few notes about the color transformations in your lines:

        * Every color-tag has to be in the format of ``c&Hxxxxxx&``, do not forget the last &;
        * You can put color changes without using transformations, like ``{\\1c&HFFFFFF&\\3c&H000000&}Test``, but those will be interpreted as ``{\\t(0,0,\\1c&HFFFFFF&\\3c&H000000&)}Test``;
        * For an example of how color changes should be put in your lines, check `this <https://github.com/CoffeeStraw/PyonFX/blob/master/examples/2%20-%20Beginner/in2.ass#L34-L36>`_.

        Also, it is important to remember that **color changes in your lines are treated as if they were continuous**.

        For example, let's assume we have two lines:

        #. ``{\\1c&HFFFFFF&\\t(100,150,\\1c&H000000&)}Line1``, starting at 0ms, ending at 100ms;
        #. ``{}Line2``, starting at 100ms, ending at 200ms.

        Even if the second line **doesn't have any color changes** and you would expect to have the style's colors,
        **it will be treated as it has** ``\\1c&H000000&``. That could seem strange at first,
        but thinking about your generated lines, **the majority** will have **start_time and end_time different** from the ones of your original file.

        Treating transformations as if they were continous, **ColorUtility will always know the right colors** to pick for you.
        Also, remember that even if you can't always see them directly on Aegisub, you can use transformations
        with negative times or with times that exceed line total duration.

    Parameters:
        lines (list of Line): List of lines to be parsed
        offset (integer, optional): Milliseconds you may want to shift all the color changes

    Returns:
        Returns a ColorUtility object.

    Examples:
        ..  code-block:: python3
            :emphasize-lines: 2, 4

            # Parsing all the lines in the file
            CU = ColorUtility(lines)
            # Parsing just a single line (the first in this case) in the file
            CU = ColorUtility([ line[0] ])
    """

    def __init__(self, lines: list[Line], offset: int = 0):
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
        """Returns all the color_changes in the object that fit (in terms of time) between line.start_time and line.end_time.

        Parameters:
            line (Line object): The line of which you want to get the color changes
            c1 (bool, optional): If False, you will not get color values containing primary color
            c3 (bool, optional): If False, you will not get color values containing border color
            c4 (bool, optional): If False, you will not get color values containing shadow color

        Returns:
            A string containing color changes interpolated.

        Note:
            If c1, c3 or c4 is/are None, the script will automatically recognize what you used in the color changes in the lines and put only the ones considered essential.

        Examples:
            ..  code-block:: python3
                :emphasize-lines: 6

                # Assume that we have l as a copy of line and we're iterating over all the syl in the current line
                # All the fun stuff of the effect creation...
                l.start_time = line.start_time + syl.start_time
                l.end_time   = line.start_time + syl.end_time

                l.text = "{\\\\an5\\\\pos(%.3f,%.3f)\\\\fscx120\\\\fscy120%s}%s" % (syl.center, syl.middle, CU.get_color_change(l), syl.text)
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
        """Returns the single color(s) in the color_changes that fit the current frame (line.start_time) in your frame loop.

        Note:
            If you get errors, try either modifying your \\\\t values or set your **fr parameter** in FU object to **10**.

        Parameters:
            line (Line object): The line of which you want to get the color changes
            c1 (bool, optional): If False, you will not get color values containing primary color.
            c3 (bool, optional): If False, you will not get color values containing border color.
            c4 (bool, optional): If False, you will not get color values containing shadow color.

        Returns:
            A string containing color changes interpolated.

        Examples:
            ..  code-block:: python3
                :emphasize-lines: 5

                # Assume that we have l as a copy of line and we're iterating over all the syl in the current line and we're iterating over the frames
                l.start_time = s
                l.end_time   = e

                l.text = "{\\\\an5\\\\pos(%.3f,%.3f)\\\\fscx120\\\\fscy120%s}%s" % (syl.center, syl.middle, CU.get_fr_color_change(l), syl.text)
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
