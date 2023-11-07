from decimal import Decimal
import os
from typing import Union
import pytest
from pyonfx import *
from fractions import Fraction

dir_path = os.path.dirname(os.path.realpath(__file__))


def test_from_fps_invalid_fps():
    # Verify fps limit
    with pytest.raises(ValueError) as exc_info:
        Timestamps.from_fps(-1)
    assert (
        str(exc_info.value)
        == "Parameter ``fps`` must be between 0 and 1000 (0 not included)."
    )

    with pytest.raises(ValueError) as exc_info:
        Timestamps.from_fps(0)
    assert (
        str(exc_info.value)
        == "Parameter ``fps`` must be between 0 and 1000 (0 not included)."
    )

    with pytest.raises(ValueError) as exc_info:
        Timestamps.from_fps(1001)
    assert (
        str(exc_info.value)
        == "Parameter ``fps`` must be between 0 and 1000 (0 not included)."
    )

    try:
        Timestamps.from_fps(1)
    except Exception:
        assert False

    try:
        Timestamps.from_fps(1000)
    except Exception:
        assert False


@pytest.mark.parametrize(
    "fps, expected_output",
    [
        (30, Fraction(30, 1000)),
        (24000 / 1001, Fraction(24000, 1001) / Fraction(1000)),
        (Fraction(24000, 1001), Fraction(24000, 1001) / Fraction(1000)),
        (Decimal(24000) / Decimal(1001), Fraction(24000, 1001) / Fraction(1000)),
    ],
)
def test_from_fps(fps: Union[int, float, Fraction, Decimal], expected_output: Fraction):
    expected_timestamps = [0]
    expected_last_frame_time = Fraction(0)

    timestamps = Timestamps.from_fps(fps)

    assert timestamps.timestamps == expected_timestamps
    assert timestamps.last_frame_time == expected_last_frame_time
    assert timestamps.fpms == pytest.approx(expected_output)
    assert timestamps.rounding_method == RoundingMethod.ROUND


def test_from_timestamps_file_real_file():
    timestamp_file_path = os.path.join(dir_path, "timestamps", "timestamps.txt")
    timestamp = Timestamps.from_timestamps_file(timestamp_file_path)

    expected_timestamps = [0, 50, 100]
    expected_last_frame_time = Fraction(100)
    expected_fpms = Fraction(2, 100)

    assert timestamp.timestamps == expected_timestamps
    assert timestamp.last_frame_time == expected_last_frame_time
    assert timestamp.fpms == expected_fpms
    assert timestamp.rounding_method == RoundingMethod.ROUND


def test_from_timestamps_file_string():
    timestamps_str = "# timecode format v2\n" "0\n" "50\n" "100\n"
    timestamp = Timestamps.from_timestamps_file(timestamps_str)

    expected_timestamps = [0, 50, 100]
    expected_last_frame_time = Fraction(100)
    expected_fpms = Fraction(2, 100)

    assert timestamp.timestamps == expected_timestamps
    assert timestamp.last_frame_time == expected_last_frame_time
    assert timestamp.fpms == expected_fpms
    assert timestamp.rounding_method == RoundingMethod.ROUND


def test_from_timestamps_file_round():
    timestamps_str = "# timecode format v2\n" "0\n" "50.5\n" "100.4\n"
    timestamp = Timestamps.from_timestamps_file(timestamps_str)

    expected_timestamps = [0, 51, 100]
    expected_last_frame_time = Fraction("100.4")
    expected_fpms = Fraction(2) / Fraction("100.4")

    assert timestamp.timestamps == expected_timestamps
    assert timestamp.last_frame_time == expected_last_frame_time
    assert timestamp.fpms == expected_fpms
    assert timestamp.rounding_method == RoundingMethod.ROUND


def test_from_timestamps_file_floor():
    timestamps_str = "# timecode format v2\n" "0\n" "50.5\n" "100.4\n"
    timestamp = Timestamps.from_timestamps_file(
        timestamps_str, rounding_method=RoundingMethod.FLOOR
    )

    expected_timestamps = [0, 50, 100]
    expected_last_frame_time = Fraction("100.4")
    expected_fpms = Fraction(2) / Fraction("100.4")

    assert timestamp.timestamps == expected_timestamps
    assert timestamp.last_frame_time == expected_last_frame_time
    assert timestamp.fpms == expected_fpms
    assert timestamp.rounding_method == RoundingMethod.FLOOR


def test_from_timestamps_file_normalize_true():
    timestamps_str = "# timecode format v2\n" "10\n" "20\n" "30\n"
    timestamp = Timestamps.from_timestamps_file(timestamps_str)

    expected_timestamps = [0, 10, 20]
    expected_last_frame_time = Fraction(20)
    expected_fpms = Fraction(2, 20)

    assert timestamp.timestamps == expected_timestamps
    assert timestamp.last_frame_time == expected_last_frame_time
    assert timestamp.fpms == expected_fpms
    assert timestamp.rounding_method == RoundingMethod.ROUND


def test_from_timestamps_file_normalize_false():
    timestamps_str = "# timecode format v2\n" "10\n" "20\n" "30\n"
    timestamp = Timestamps.from_timestamps_file(timestamps_str, normalize=False)

    expected_timestamps = [10, 20, 30]
    expected_last_frame_time = Fraction(30)
    expected_fpms = Fraction(2, 20)

    assert timestamp.timestamps == expected_timestamps
    assert timestamp.last_frame_time == expected_last_frame_time
    assert timestamp.fpms == expected_fpms
    assert timestamp.rounding_method == RoundingMethod.ROUND


def test_from_video_file_mkv():
    video_file_path = os.path.join(dir_path, "timestamps", "test_video.mkv")

    # Verify that no warning message have been print
    with pytest.warns(None) as warning_list:
        timestamp = Timestamps.from_video_file(video_file_path)
    assert len(warning_list) == 0

    expected_timestamps = [
        int(frame * 1 / Fraction(24000, 1001) * 1000 + 0.5) for frame in range(500)
    ]
    expected_last_frame_time = int(
        499 * 1 / Fraction(24000, 1001) * 1000 + 0.5
    )  # Important to note, like said in the timestamps.py doc, mkv round timestamps to ms
    expected_fpms = Fraction(499, expected_last_frame_time)

    assert timestamp.timestamps == expected_timestamps
    assert timestamp.last_frame_time == expected_last_frame_time
    assert timestamp.fpms == expected_fpms
    assert timestamp.rounding_method == RoundingMethod.ROUND


def test_from_video_file_mp4():
    video_file_path = os.path.join(dir_path, "timestamps", "test_video.mp4")

    # Verify that no warning message have been print
    with pytest.warns(None) as warning_list:
        timestamp = Timestamps.from_video_file(video_file_path)
    assert len(warning_list) == 0

    expected_timestamps = [
        int(frame * 1 / Fraction(24000, 1001) * 1000 + 0.5) for frame in range(500)
    ]
    expected_last_frame_time = 499 * 1 / Fraction(24000, 1001) * 1000
    expected_fpms = Fraction(499, expected_last_frame_time)

    assert timestamp.timestamps == expected_timestamps
    assert timestamp.last_frame_time == pytest.approx(expected_last_frame_time)
    assert timestamp.fpms == pytest.approx(expected_fpms)
    assert timestamp.rounding_method == RoundingMethod.ROUND


def test_from_video_file_avi():
    video_file_path = os.path.join(dir_path, "timestamps", "test_video.avi")

    # Verify that no warning message have been print
    with pytest.warns(None) as warning_list:
        timestamp = Timestamps.from_video_file(video_file_path)
    assert len(warning_list) == 0

    expected_timestamps = [
        int(frame * 1 / Fraction(24000, 1001) * 1000 + 0.5) for frame in range(500)
    ]
    expected_last_frame_time = 499 * 1 / Fraction(24000, 1001) * 1000
    expected_fpms = Fraction(499, expected_last_frame_time)

    assert timestamp.timestamps == expected_timestamps
    assert timestamp.last_frame_time == pytest.approx(expected_last_frame_time)
    assert timestamp.fpms == pytest.approx(expected_fpms)
    assert timestamp.rounding_method == RoundingMethod.ROUND


def test_from_video_file_avi_without_pts_time():
    # In some really really specific case, video can not have pts_time.
    video_file_path = os.path.join(dir_path, "timestamps", "video_without_pts_time.avi")

    # Verify that no warning message have been print
    with pytest.warns(None) as warning_list:
        timestamp = Timestamps.from_video_file(video_file_path)
    assert len(warning_list) == 0

    expected_timestamps = [
        int(frame * 1 / Fraction(24000, 1001) * 1000 + 0.5) for frame in range(500)
    ]
    expected_last_frame_time = 499 * 1 / Fraction(24000, 1001) * 1000
    expected_fpms = Fraction(499, expected_last_frame_time)

    assert timestamp.timestamps == expected_timestamps
    assert timestamp.last_frame_time == pytest.approx(expected_last_frame_time)
    assert timestamp.fpms == pytest.approx(expected_fpms)
    assert timestamp.rounding_method == RoundingMethod.ROUND


def test_from_video_file_mkv_where_timestamps_arent_in_ms():
    video_file_path = os.path.join(dir_path, "timestamps", "mkv_timestamps_not_ms.mkv")
    with pytest.warns(
        UserWarning,
        match="Your mkv file isn't perfectly rounded to ms. In this situation, you may prefer to use RoundingMethod.floor then RoundingMethod.ROUND.",
    ):
        Timestamps.from_video_file(video_file_path)


def test_from_video_file_invalid_file():
    invalid_file_path = os.path.join(dir_path, "timestamps", "generate_test_video.py")

    with pytest.raises(ValueError) as exc_info:
        Timestamps.from_video_file(invalid_file_path)
    assert str(exc_info.value) == f"The file {invalid_file_path} is not a video file."


def test_from_video_file_invalid_index():
    video_file_path = os.path.join(dir_path, "timestamps", "test_video.mkv")
    invalid_index = 10

    with pytest.raises(ValueError) as exc_info:
        Timestamps.from_video_file(video_file_path, invalid_index)
    assert (
        str(exc_info.value)
        == f"The index {invalid_index} is not in the file {video_file_path}."
    )


def test_from_video_file_index_is_not_a_video():
    video_file_path = os.path.join(dir_path, "timestamps", "test_video.mkv")
    invalid_index = 1

    with pytest.raises(ValueError) as exc_info:
        Timestamps.from_video_file(video_file_path, invalid_index)
    assert (
        str(exc_info.value)
        == f'The index {invalid_index} is not a video stream. It is an "audio" stream.'
    )


def test_from_video_file_invalid_path():
    video_file_path = "this is a invalid path"

    with pytest.raises(FileNotFoundError) as exc_info:
        Timestamps.from_video_file(video_file_path)
    assert (
        str(exc_info.value) == f'Invalid path for the video file: "{video_file_path}"'
    )


def test_validate():
    with pytest.raises(ValueError) as exc_info:
        Timestamps.validate([0])
    assert str(exc_info.value) == "There must be at least 2 timestamps."

    with pytest.raises(ValueError) as exc_info:
        Timestamps.validate([0, 42, 20])
    assert str(exc_info.value) == "Timestamps must be in non-decreasing order."

    with pytest.raises(ValueError) as exc_info:
        Timestamps.validate([20, 20])
    assert str(exc_info.value) == "Timestamps must not be all identical."


def test_normalize():
    positive_timestamps_to_be_normalize = [10, 20, 30, 40, 50]
    negative_timestamps_to_be_normalize = [-10, 0, 10, 20, 30]
    timestamps_expected_results = [0, 10, 20, 30, 40]
    last_frame_time_expected_results = Fraction(40)
    assert Timestamps.normalize(
        positive_timestamps_to_be_normalize, positive_timestamps_to_be_normalize[-1]
    ) == (timestamps_expected_results, last_frame_time_expected_results)
    assert Timestamps.normalize(
        negative_timestamps_to_be_normalize, negative_timestamps_to_be_normalize[-1]
    ) == (timestamps_expected_results, last_frame_time_expected_results)


def test_timestamps_init():
    expected_rouding_method = RoundingMethod.FLOOR
    expected_timestamps = [0, 50]
    expected_fpms = Fraction(2) / Fraction(50)
    expected_last_frame_time = Fraction(50)

    timestamp = Timestamps(
        rounding_method=expected_rouding_method,
        timestamps=expected_timestamps,
        fpms=expected_fpms,
        last_frame_time=expected_last_frame_time,
    )

    assert timestamp.rounding_method == expected_rouding_method
    assert timestamp.timestamps == expected_timestamps
    assert timestamp.fpms == expected_fpms
    assert timestamp.last_frame_time == expected_last_frame_time

    with pytest.raises(ValueError) as exc_info:
        timestamp = Timestamps(
            rounding_method=expected_rouding_method,
            timestamps=expected_timestamps,
            fpms=expected_fpms,
        )
    assert (
        str(exc_info.value)
        == "If you specify a value for ``timestamps``, you must specify a value for ``last_frame_time``"
    )

    with pytest.raises(ValueError) as exc_info:
        timestamp = Timestamps(
            rounding_method=expected_rouding_method,
            timestamps=[0],
            fpms=expected_fpms,
            last_frame_time=expected_last_frame_time,
        )
    assert str(exc_info.value) == "There must be at least 2 timestamps."

    with pytest.raises(ValueError) as exc_info:
        timestamp = Timestamps(
            rounding_method=expected_rouding_method,
            last_frame_time=expected_last_frame_time,
        )
    assert (
        str(exc_info.value)
        == "If you don't specify a value for ``timestamps``, you must specify a value for ``fpms``"
    )

    with pytest.raises(ValueError) as exc_info:
        timestamp = Timestamps(
            rounding_method=expected_rouding_method,
            fpms=expected_fpms,
            last_frame_time=expected_last_frame_time,
        )
    assert (
        str(exc_info.value)
        == "If you specify a value for ``fpms``, you cannot specify a value for ``last_frame_time``"
    )

    # Test if only fps specified
    timestamp = Timestamps(
        rounding_method=expected_rouding_method,
        fpms=expected_fpms,
    )

    assert timestamp.rounding_method == expected_rouding_method
    assert timestamp.timestamps == [0]
    assert timestamp.fpms == expected_fpms
    assert timestamp.last_frame_time == Fraction(0)


def test_timestamps_init_normalize():
    timestamps = [50, 100]
    last_frame_time = Fraction(100)

    expected_rouding_method = RoundingMethod.FLOOR
    expected_timestamps = [0, 50]
    expected_fpms = Fraction(2) / Fraction(50)
    expected_last_frame_time = Fraction(50)

    timestamp = Timestamps(
        rounding_method=expected_rouding_method,
        timestamps=timestamps,
        fpms=expected_fpms,
        last_frame_time=last_frame_time,
    )

    assert timestamp.rounding_method == expected_rouding_method
    assert timestamp.timestamps == expected_timestamps
    assert timestamp.fpms == expected_fpms
    assert timestamp.last_frame_time == expected_last_frame_time

    timestamp = Timestamps(
        rounding_method=expected_rouding_method,
        timestamps=timestamps,
        normalize=False,
        fpms=expected_fpms,
        last_frame_time=last_frame_time,
    )

    assert timestamp.rounding_method == expected_rouding_method
    assert timestamp.timestamps == timestamps
    assert timestamp.fpms == expected_fpms
    assert timestamp.last_frame_time == last_frame_time
