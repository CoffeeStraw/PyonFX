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

import os
from ffms2 import VideoSource
from fractions import Fraction
from typing import Tuple, Union, Optional


def from_fps(fps: Union[int, float, Fraction], n_frames: int) -> list[int]:
    """Create timestamps for `n_frames` frames, based on the `fps` provided.

    Args:
        fps (positive int, float or Fraction): Frames per second.
        n_frames: ...

    Returns:
        ...
    """
    # FPS must not exceed 1000:
    # https://github.com/Aegisub/Aegisub/blob/6f546951b4f004da16ce19ba638bf3eedefb9f31/libaegisub/common/vfr.cpp#L81
    if not 0 < fps <= 1000:
        raise ValueError("Parameter 'fps' must be between 0 and 1000 (0 not included).")

    timestamps = [round(frame * 1000 / fps) for frame in range(n_frames)]
    validate(timestamps)
    return timestamps


def from_timestamps_file(path_timestamps: str) -> list[int]:
    """Return timestamps parsed from a timestamps file.

    More about timestamps file here: https://mkvtoolnix.download/doc/mkvmerge.html#mkvmerge.external_timestamp_files

    To extract the timestamps file, you have 2 options:
        - Open the video with Aegisub. "Video" --> "Save Timecodes File";
        - Using [gMKVExtractGUI](https://sourceforge.net/projects/gmkvextractgui/) (warning: it will produce one timestamp too many at the end of the file, and you will need to manually remove it).

    Args:
        path_timestamps: ...

    Returns:
        ...
    """
    if not os.path.isfile(path_timestamps):
        raise FileNotFoundError(
            f'Invalid path for the timestamps file: "{path_timestamps}"'
        )

    timestamps = []
    with open(path_timestamps, "r") as f:
        format_version = f.readline().strip().replace("timecode", "timestamp")
        tf = "# timestamp format"

        if format_version in [f"{tf} v1", f"{tf} v3", f"{tf} v4"]:
            raise NotImplementedError(
                f'The timestamps file "{path_timestamps}" is in a format not currently supported by PyonFX.'
            )

        if format_version != f"{tf} v2":
            raise ValueError(
                f'The timestamps file "{path_timestamps}" is not properly formatted.'
            )

        while line := f.readline().strip():
            if line.startswith("#") or not line:
                continue
            try:
                timestamps.append(int(line))
            except ValueError:
                raise ValueError(
                    f'The timestamps file "{path_timestamps}" is not properly formatted.'
                )

    validate(timestamps)
    return normalize(timestamps)


def from_mkv(mkv_path: str, track_number: Optional[int] = None) -> list[int]:
    """Return timestamps read from a MKV file.

    Inspired by: https://github.com/Aegisub/Aegisub/blob/6f546951b4f004da16ce19ba638bf3eedefb9f31/src/video_provider_ffmpegsource.cpp#L296-L314

    Args:
        ...

    Returns:
        ...
    """
    video_source = VideoSource(mkv_path, track_number)

    timestamps = [
        int(
            (frame.PTS * video_source.track.time_base.numerator)
            / video_source.track.time_base.denominator
        )
        for frame in video_source.track.frame_info_list
    ]

    validate(timestamps)
    return normalize(timestamps)


def validate(timestamps):
    """Verify that the provided timestamps are valid.

    Inspired by: https://github.com/Aegisub/Aegisub/blob/6f546951b4f004da16ce19ba638bf3eedefb9f31/libaegisub/common/vfr.cpp#L39-L46

    Args:
        timestamps: ...

    Returns:
        ...
    """
    if len(timestamps) <= 1:
        raise ValueError("There must be at least 2 timestamps.")

    if any(timestamps[i] > timestamps[i + 1] for i in range(len(timestamps) - 1)):
        raise ValueError("Timestamps must be in non-decreasing order.")

    if timestamps.count(timestamps[0]) == len(timestamps):
        raise ValueError("Timestamps are all identical.")


def normalize(timestamps) -> list[int]:
    """Shift the timestamps to make them start from 0. This way, frame 0 will start at time 0.

    Inspired by: https://github.com/Aegisub/Aegisub/blob/6f546951b4f004da16ce19ba638bf3eedefb9f31/libaegisub/common/vfr.cpp#L50-L53

    Args:
        ...

    Returns:
        ...
    """
    if timestamps[0]:
        return list(map(lambda t: t - timestamps[0], timestamps))
    return timestamps


def get_den_num_last(timestamps) -> Tuple[int, int, int]:
    """Compute denominator, numerator and last values.

    Inspired by: https://github.com/Aegisub/Aegisub/blob/6f546951b4f004da16ce19ba638bf3eedefb9f31/libaegisub/common/vfr.cpp#L157-L159

    Args:
        ...

    Returns:
        ...
    """
    denominator = 1000000000

    numerator = int((len(timestamps) - 1) * denominator * 1000 / timestamps[-1])

    last = (len(timestamps) - 1) * denominator * 1000

    return denominator, numerator, last
