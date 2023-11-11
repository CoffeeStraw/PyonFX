# -*- coding: utf-8 -*-
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
from enum import Enum
import json
import os
import re
import shutil
import subprocess
import sys
import warnings
from decimal import Decimal
from fractions import Fraction
from io import StringIO, TextIOWrapper
from typing import Callable, List, Optional, Tuple, Union


class RoundingMethod(Enum):
    FLOOR: Callable[[Fraction], int] = lambda ms: int(ms)
    ROUND: Callable[[Fraction], int] = lambda ms: int(ms + Fraction("0.5"))


class RangeV1:
    def __init__(self, start_frame: int, end_frame: int, fps: Fraction):
        self.start_frame = start_frame
        self.end_frame = end_frame
        self.fps = fps


class TimestampsFileParser:
    def parse_file(
        file_content: TextIOWrapper, rounding_method: RoundingMethod
    ) -> Tuple[List[int], Fraction, Fraction]:
        """Parse timestamps from a [timestamps file](https://mkvtoolnix.download/doc/mkvmerge.html#mkvmerge.external_timestamp_files) and return them.

        Inspired by: https://gitlab.com/mbunkus/mkvtoolnix/-/blob/72dfe260effcbd0e7d7cf6998c12bb35308c004f/src/merge/timestamp_factory.cpp#L27-74

        Parameters:
            file_content (TextIOWrapper): The timestamps content
            rounding_method (RoundingMethod): A rounding method

        Returns:
            A tuple containing these 3 informations:
                1. A list of each timestamps rounded or floored to milliseconds.
                2. The last timestamps not rounded
                3. If the format of timestamps is 1, then it return the fpms of the Assume section
                   If the format of timestamps is 2 or 4, then it approximate the fpms.
                        It calculate the fps like this: (1000 * nbr_frame) / (last_timestamps - first_timestamps)
        """

        regex_timestamps = re.compile("^# time(?:code|stamp) *format v(\\d+).*")

        line = file_content.readline()
        match = regex_timestamps.search(line)
        if match is None:
            raise ValueError(
                f'The timestamps at line 0 is invalid. Here is the line: "{line}"'
            )

        version = int(match.group(1))

        if version == 1:
            timestamps, last_frame_time, fpms = TimestampsFileParser._parse_v1_file(
                file_content, rounding_method
            )
        elif version == 2 or version == 4:
            (
                timestamps,
                last_frame_time,
                fpms,
            ) = TimestampsFileParser._parse_v2_and_v4_file(
                file_content, version, rounding_method
            )
        else:
            raise NotImplementedError(
                f"The file uses version {version} for its timestamps, but this format is currently not compatible with PyonFX."
            )

        return timestamps, last_frame_time, fpms

    def _parse_v1_file(
        file_content: TextIOWrapper, rounding_method: RoundingMethod
    ) -> Tuple[List[int], Fraction, Fraction]:
        """Create timestamps based on the timestamps v1 file provided.

        Inspired by: https://gitlab.com/mbunkus/mkvtoolnix/-/blob/72dfe260effcbd0e7d7cf6998c12bb35308c004f/src/merge/timestamp_factory.cpp#L82-175

        Parameters:
            file_content (TextIOWrapper): The timestamps content
            rounding_method (RoundingMethod): A rounding method

        Returns:
            A tuple containing these 3 informations:
                1. A list of each timestamps rounded to milliseconds
                2. The last timestamps not rounded
                3. The fpms
        """
        timestamps: List[int] = []
        ranges_v1: List[RangeV1] = []
        line: str = ""

        for line in file_content:
            if not line:
                raise ValueError(
                    f"The timestamps file does not contain a valid 'Assume' line with the default number of frames per second."
                )
            line = line.strip(" \t")

            if line and not line.startswith("#"):
                break

        if not line.lower().startswith("assume "):
            raise ValueError(
                f"The timestamps file does not contain a valid 'Assume' line with the default number of frames per second."
            )

        line = line[7:].strip(" \t")
        try:
            default_fps = Fraction(line)
        except ValueError:
            raise ValueError(
                f"The timestamps file does not contain a valid 'Assume' line with the default number of frames per second."
            )

        for line in file_content:
            line = line.strip(" \t\n\r")

            if not line or line.startswith("#"):
                continue

            line_splitted = line.split(",")
            if len(line_splitted) != 3:
                raise ValueError(
                    f'The timestamps file contain a invalid line. Here is it: "{line}"'
                )
            try:
                start_frame = int(line_splitted[0])
                end_frame = int(line_splitted[1])
                fps = Fraction(line_splitted[2])
            except ValueError:
                raise ValueError(
                    f'The timestamps file contain a invalid line. Here is it: "{line}"'
                )

            range_v1 = RangeV1(start_frame, end_frame, fps)

            if range_v1.start_frame < 0 or range_v1.end_frame < 0:
                raise ValueError("Cannot specify frame rate for negative frames.")
            if range_v1.end_frame < range_v1.start_frame:
                raise ValueError(
                    "End frame must be greater than or equal to start frame."
                )
            if range_v1.fps <= 0:
                raise ValueError("FPS must be greater than zero.")
            elif range_v1.fps == 0:
                # mkvmerge allow fps to 0, but we can ignore them, since they won't impact the timestamps
                continue

            ranges_v1.append(range_v1)

        ranges_v1.sort(key=lambda x: x.start_frame)

        time: Fraction = Fraction(0)
        frame: int = 0
        for range_v1 in ranges_v1:
            if frame > range_v1.start_frame:
                raise ValueError("Override ranges must not overlap.")

            while frame < range_v1.start_frame:
                timestamps.append(rounding_method(time))
                time += Fraction(1000) / default_fps
                frame += 1

            while frame <= range_v1.end_frame:
                timestamps.append(rounding_method(time))
                time += Fraction(1000) / range_v1.fps
                frame += 1

        timestamps.append(rounding_method(time))
        fpms = default_fps / Fraction(1000)
        return timestamps, time, fpms

    def _parse_v2_and_v4_file(
        file_content: TextIOWrapper, version: int, rounding_method: RoundingMethod
    ) -> Tuple[List[int], Fraction, Fraction]:
        """Create timestamps based on the timestamps v1 file provided.

        Inspired by: https://gitlab.com/mbunkus/mkvtoolnix/-/blob/72dfe260effcbd0e7d7cf6998c12bb35308c004f/src/merge/timestamp_factory.cpp#L201-267

        Parameters:
            file_content (TextIOWrapper): The timestamps content
            version (int): The version of the timestamps (only 2 or 4 is allowed)
            rounding_method (RoundingMethod): A rounding method

        Returns:
            A tuple containing these 3 informations:
                1. A list of each timestamps rounded to milliseconds
                2. The last timestamps not rounded
                3. The fpms
        """

        if version != 2 and version != 4:
            raise ValueError("You can only specify version 2 or 4.")

        timestamps: List[int] = []
        previous_timestamp: int = 0
        lowest_timestamp: Fraction = None
        highest_timestamp: Fraction = None

        for line in file_content:
            line = line.strip(" \t")

            if not line or line.startswith("#"):
                continue

            try:
                timestamp = Fraction(line)
            except ValueError:
                raise ValueError(
                    f'The timestamps file contain a invalid line. Here is it: "{line}"'
                )

            if highest_timestamp is None or highest_timestamp < timestamp:
                highest_timestamp = timestamp
            if lowest_timestamp is None or lowest_timestamp > timestamp:
                lowest_timestamp = timestamp

            rounded_timestamp = rounding_method(timestamp)

            if version == 2 and rounded_timestamp < previous_timestamp:
                raise ValueError(
                    f"The timestamps file contain timestamps NOT in ascending order."
                )

            previous_timestamp = rounded_timestamp
            timestamps.append(rounded_timestamp)

        if not len(timestamps):
            raise ValueError(f"The timestamps file is empty.")

        if version == 4:
            timestamps.sort()

        duration = highest_timestamp - lowest_timestamp
        if duration:
            fpms = Fraction(len(timestamps) - 1) / (
                highest_timestamp - lowest_timestamp
            )
        else:
            fpms = 0
        return timestamps, highest_timestamp, fpms


class Timestamps:
    """Timestamps object contains informations about the timestamps of an video.

    Video player have 2 methods to deal with timestamps. Some floor them and other round them.
    This can lead to difference when displaying the subtitle.
        Ex:
            Player - Method - proof
            mpv    - round  - https://github.com/mpv-player/mpv/blob/7480efa62c0a2a1779b4fdaa804a6512aa488400/sub/sd_ass.c#L499
            FFmpeg - floor  - https://github.com/FFmpeg/FFmpeg/blob/fd1712b6fb8b7acc04ccaa7c02b9a5c9f233cfb3/libavfilter/vf_subtitles.c#L195
            VLC    - floor  - https://github.com/videolan/vlc/blob/f7bb59d9f51cc10b25ff86d34a3eff744e60c46e/include/vlc_tick.h#L118-L130
            MPC-HC - floor  - https://github.com/clsid2/mpc-hc/blob/0994fd605a9fb4d15806d0efdd6399ba1bc5f984/src/Subtitles/LibassContext.cpp#L843
    Important note:
        Matroska (.mkv) file are an exception !!!
        If you want to be compatible with mkv, use RoundingMethod.ROUND.
        By default, they only have a precision to milliseconds instead of nanoseconds like most format.
            For more detail see:
                1- https://mkvtoolnix.download/doc/mkvmerge.html#mkvmerge.description.timestamp_scale
                2- https://matroska.org/technical/notes.html#timestampscale-rounding

    Parameters:
        rounding_method (RoundingMethod): A rounding method. See the comment above about floor vs round.
            99% of the time, you want to use RoundingMethod.ROUND.
        timestamps (List[int], optional): A list of [timestamps](https://en.wikipedia.org/wiki/Timestamp) in milliseconds encoded as integers.
                                It represent each frame [presentation timestamp (PTS)](https://en.wikipedia.org/wiki/Presentation_timestamp)
        normalize (bool, optional): If True, it will shift the timestamps to make them start from 0. If false, the option does nothing.
        fpms (Fraction, optional): The fpms.
        last_frame_time (Fraction, optional): The last frame time not rounded.
    """

    timestamps: List[int]
    last_frame_time: Fraction
    fpms: Fraction
    rounding_method: RoundingMethod

    def __init__(
        self,
        rounding_method: RoundingMethod,
        timestamps: Optional[List[int]] = None,
        normalize: Optional[bool] = True,
        fpms: Optional[Fraction] = None,
        last_frame_time: Optional[Fraction] = None,
    ):
        self.rounding_method = rounding_method

        if timestamps is not None:
            if last_frame_time is None:
                raise ValueError(
                    "If you specify a value for ``timestamps``, you must specify a value for ``last_frame_time``"
                )
            self.last_frame_time = last_frame_time

            # Validate the timestamps
            if len(timestamps) <= 1:
                raise ValueError("There must be at least 2 timestamps.")

            if any(timestamps[i] > timestamps[i + 1] for i in range(len(timestamps) - 1)):
                raise ValueError("Timestamps must be in non-decreasing order.")

            if timestamps.count(timestamps[0]) == len(timestamps):
                raise ValueError("Timestamps must not be all identical.")

            self.timestamps = timestamps

            if normalize:
                self.timestamps, self.last_frame_time = Timestamps.normalize(
                    self.timestamps, self.last_frame_time
                )

            if fpms is None:
                # Approximation of the fpms
                self.fpms = Fraction(
                    len(timestamps) - 1, self.timestamps[-1] - self.timestamps[0]
                )
            else:
                self.fpms = fpms
        else:
            if fpms is None:
                raise ValueError(
                    "If you don't specify a value for ``timestamps``, you must specify a value for ``fpms``"
                )
            if last_frame_time is not None:
                raise ValueError(
                    "If you specify a value for ``fpms``, you cannot specify a value for ``last_frame_time``"
                )

            self.fpms = fpms
            self.timestamps = [0]
            self.last_frame_time = Fraction(0)

    @classmethod
    def from_fps(
        cls: Timestamps,
        fps: Union[int, float, Fraction, Decimal],
        rounding_method: Optional[RoundingMethod] = RoundingMethod.ROUND,
    ) -> Timestamps:
        """Create timestamps based on the `fps` provided.

        Parameters:
            fps (positive int, int | float | Fraction | Decimal): Frames per second.
            rounding_method (RoundingMethod, optional): A rounding method. See the comment in Timestamps description about floor vs round.

        Returns:
            A Timestamps instance.
        """
        if not 0 < fps <= 1000:
            raise ValueError(
                "Parameter ``fps`` must be between 0 and 1000 (0 not included)."
            )

        fpms = Fraction(fps) / Fraction(1000)

        timestamps = cls(
            rounding_method=rounding_method,
            fpms=fpms,
        )
        return timestamps

    @classmethod
    def from_timestamps_file(
        cls: Timestamps,
        path_to_timestamps_file_or_content: Union[str, os.PathLike[str]],
        normalize: Optional[bool] = True,
        rounding_method: Optional[RoundingMethod] = RoundingMethod.ROUND,
    ) -> Timestamps:
        """Create timestamps based on a [timestamps file](https://mkvtoolnix.download/doc/mkvmerge.html#mkvmerge.external_timestamp_files).

        To extract the timestamps file, you have 2 options:
            - Open the video with Aegisub. "Video" --> "Save Timecodes File";
            - Using [gMKVExtractGUI](https://sourceforge.net/projects/gmkvextractgui/) (warning: it will produce one timestamp too many at the end of the file, and you will need to manually remove it).

        Parameters:
            path_to_timestamps_file_or_content (str | os.PathLike[str]):
                Path for the timestamps file (either relative to your .py file or absolute).
                Or, it can directly be a string of the timestamps file content.
            normalize (bool, optional): If True, it will shift the timestamps to make them start from 0. If false, the option does nothing.
            rounding_method (RoundingMethod, optional): A rounding method. See the comment in Timestamps description about floor vs round.

        Returns:
            A Timestamps instance.
        """

        if os.path.isfile(path_to_timestamps_file_or_content):
            with open(path_to_timestamps_file_or_content, "r") as f:
                timestamps, last_frame_time, fpms = TimestampsFileParser.parse_file(
                    f, rounding_method
                )
        else:
            f = StringIO(path_to_timestamps_file_or_content)
            timestamps, last_frame_time, fpms = TimestampsFileParser.parse_file(
                f, rounding_method
            )

        return cls(
            rounding_method=rounding_method,
            timestamps=timestamps,
            normalize=normalize,
            fpms=fpms,
            last_frame_time=last_frame_time,
        )

    @classmethod
    def from_video_file(
        cls: Timestamps,
        video_path: str,
        index: Optional[int] = 0,
        normalize: Optional[bool] = True,
        rounding_method: Optional[RoundingMethod] = RoundingMethod.ROUND,
    ) -> Timestamps:
        """Create timestamps based on the ``video_path`` provided.

        Note:
            This method requires the ``ffprobe`` program to be available.

        Parameters:
            video_path (str): A Video path.
            index (int, optional): Stream index of the video.
            normalize (bool, optional): If True, it will shift the timestamps to make them start from 0. If false, the option does nothing.
            rounding_method (RoundingMethod, optional): A rounding method. See the comment in Timestamps description about floor vs round.
        Returns:
            An Timestamps instance.
        """

        def get_timestamps(packets) -> Tuple[Fraction, Fraction, List[int]]:
            timestamps: List[int] = []

            lowest_timestamp: Fraction = None
            highest_timestamp: Fraction = None

            for packet in packets:
                timestamp = Fraction(
                    packet.get("pts_time", packet.get("dts_time"))
                ) * Fraction(1000)
                if highest_timestamp is None or highest_timestamp < timestamp:
                    highest_timestamp = timestamp
                if lowest_timestamp is None or lowest_timestamp > timestamp:
                    lowest_timestamp = timestamp
                timestamps.append(rounding_method(timestamp))

            timestamps.sort()
            return lowest_timestamp, highest_timestamp, timestamps

        # Verify if ffprobe is installed
        if shutil.which("ffprobe") is None:
            raise Exception("ffprobe is not in the environment variable.")

        if not os.path.isfile(video_path):
            raise FileNotFoundError(f'Invalid path for the video file: "{video_path}"')

        # Getting video absolute path and checking for its existance
        if not os.path.isabs(video_path):
            dirname = os.path.dirname(os.path.abspath(sys.argv[0]))
            video_path = os.path.join(dirname, video_path)

        cmd = [
            "ffprobe",
            "-select_streams",
            f"{index}",
            "-show_entries",
            "packet=pts_time,dts_time:stream=codec_type,time_base:format=format_name",
            f"{video_path}",
            "-print_format",
            "json",
        ]
        ffprobe_output = subprocess.run(cmd, capture_output=True, text=True)
        ffprobe_output_dict = json.loads(ffprobe_output.stdout)

        if not ffprobe_output_dict:
            raise ValueError(f"The file {video_path} is not a video file.")

        if len(ffprobe_output_dict["streams"]) == 0:
            raise ValueError(f"The index {index} is not in the file {video_path}.")

        if ffprobe_output_dict["streams"][0]["codec_type"] != "video":
            raise ValueError(
                f'The index {index} is not a video stream. It is an "{ffprobe_output_dict["streams"][0]["codec_type"]}" stream.'
            )

        if ffprobe_output_dict["format"]["format_name"] == "matroska,webm":
            # We only do this check for .mkv file. See the note about mkv in the class documentation
            time_base = Fraction(ffprobe_output_dict["streams"][0]["time_base"])
            # 1/1000 represent 1 ms. If the time_base cannot divided by 1/1000, then it means that the timestamps aren't rounded
            if time_base % (1 / 1000):
                warnings.warn(
                    "Your mkv file isn't perfectly rounded to ms. In this situation, you may prefer to use RoundingMethod.floor then RoundingMethod.ROUND.",
                    UserWarning,
                )

        first_frame_time, last_frame_time, timestamps = get_timestamps(
            ffprobe_output_dict["packets"]
        )
        fpms = Fraction(len(timestamps) - 1) / (last_frame_time - first_frame_time)

        return cls(
            rounding_method=rounding_method,
            timestamps=timestamps,
            normalize=normalize,
            fpms=fpms,
            last_frame_time=last_frame_time,
        )

    @staticmethod
    def normalize(
        timestamps: List[int], last_frame_time: Fraction
    ) -> Tuple[List[int], Fraction]:
        """Shift the timestamps to make them start from 0. This way, frame 0 will start at time 0.

        Parameters:
            timestamps (list of int): A list of [timestamps](https://en.wikipedia.org/wiki/Timestamp) encoded as integers.
            last_frame_time (Fraction): The last frame time not rounded.
        Returns:
            The timestamps normalized and the last frame time normalized.
        """
        if timestamps[0]:
            return (
                list(map(lambda t: t - timestamps[0], timestamps)),
                last_frame_time - timestamps[0],
            )
        return timestamps, last_frame_time
