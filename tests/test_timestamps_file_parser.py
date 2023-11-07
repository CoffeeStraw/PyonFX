from io import StringIO
import pytest
from pyonfx import *
from pyonfx.timestamps import TimestampsFileParser
from fractions import Fraction



def test_from_timestamps_file_empty_string():
    timestamps_str = ""

    with pytest.raises(ValueError) as exc_info:
        TimestampsFileParser.parse_file(StringIO(timestamps_str), RoundingMethod.ROUND)
    assert str(exc_info.value) == 'The timestamps at line 0 is invalid. Here is the line: ""'


def test_from_timestamps_file_v1_only_fps_string_int():
    timestamps_str = "# timecode format v1\n" \
    "Assume 30\n"

    expected_timestamps = [0]
    expected_last_frame_time = Fraction(0)
    expected_fpms = Fraction(30, 1000)

    timestamps, last_frame_time, fpms = TimestampsFileParser.parse_file(StringIO(timestamps_str), RoundingMethod.ROUND)

    assert timestamps == expected_timestamps
    assert last_frame_time == expected_last_frame_time
    assert fpms == expected_fpms


def test_from_timestamps_file_v1_only_fps_string_float():
    timestamps_str = "# timecode format v1\n" \
    "Assume 30.5\n"

    expected_timestamps = [0]
    expected_last_frame_time = Fraction(0)
    expected_fpms = Fraction("30.5") / Fraction(1000)

    timestamps, last_frame_time, fpms = TimestampsFileParser.parse_file(StringIO(timestamps_str), RoundingMethod.ROUND)

    assert timestamps == expected_timestamps
    assert last_frame_time == expected_last_frame_time
    assert fpms == expected_fpms


def test_from_timestamps_file_v1_string_floor():
    timestamps_str = "# timecode format v1\n" \
    "Assume 30\n" \
    "5,10,15\n"

    expected_timestamps = [0, 33, 66, 100, 133, 166, 233, 300, 366, 433, 500, 566]
    expected_last_frame_time = Fraction(1700, 3) # (5 * 1/30 * 1000 + 6 * 1/15 * 1000) = 1700 / 3
    expected_fpms = Fraction(30, 1000)

    timestamps, last_frame_time, fpms = TimestampsFileParser.parse_file(StringIO(timestamps_str), RoundingMethod.FLOOR)

    assert timestamps == expected_timestamps
    assert last_frame_time == expected_last_frame_time
    assert fpms == expected_fpms


def test_from_timestamps_file_v1_fps_with_range_string_int():
    timestamps_str = "# timecode format v1\n" \
    "Assume 30\n" \
    "5,10,15\n"

    expected_timestamps = [0, 33, 67, 100, 133, 167, 233, 300, 367, 433, 500, 567]
    expected_last_frame_time = Fraction(1700, 3) # (5 * 1/30 * 1000 + 6 * 1/15 * 1000) = 1700 / 3
    expected_fpms = Fraction(30, 1000)

    timestamps, last_frame_time, fpms = TimestampsFileParser.parse_file(StringIO(timestamps_str), RoundingMethod.ROUND)

    assert timestamps == expected_timestamps
    assert last_frame_time == expected_last_frame_time
    assert fpms == expected_fpms


def test_from_timestamps_file_v1_fps_with_range_string_float():
    timestamps_str = "# timecode format v1\n" \
    "Assume 30.5\n" \
    "5,10,15.5\n"

    expected_timestamps = [0, 33, 66, 98, 131, 164, 228, 293, 357, 422, 487, 551]
    expected_last_frame_time = Fraction(1042000, 1891)
    expected_fpms = Fraction("30.5") / Fraction(1000)

    timestamps, last_frame_time, fpms = TimestampsFileParser.parse_file(StringIO(timestamps_str), RoundingMethod.ROUND)

    assert timestamps == expected_timestamps
    assert last_frame_time == expected_last_frame_time
    assert fpms == expected_fpms


def test_from_timestamps_file_v1_out_of_order():
    timestamps_str = "# timecode format v1\n" \
    "Assume 30\n" \
    "10,15,25\n" \
    "0,5,25\n"

    # So, frame [0, 6] is 25 fps
    # So, frame [7, 10] is 30 fps
    # So, frame [11, 16] is 25 fps
    expected_timestamps = [0, 40, 80, 120, 160, 200, 240, 273, 307, 340, 373, 413, 453, 493, 533, 573, 613]
    expected_last_frame_time = Fraction(1840, 3) # 12 * 1/25 * 1000 + 4 * 1/30 * 1000 = 1840 / 3
    expected_fpms = Fraction(30, 1000)

    timestamps, last_frame_time, fpms = TimestampsFileParser.parse_file(StringIO(timestamps_str), RoundingMethod.ROUND)

    assert timestamps == expected_timestamps
    assert last_frame_time == expected_last_frame_time
    assert fpms == expected_fpms


def test_from_timestamps_file_v1_range_one_frame():
    timestamps_str = "# timecode format v1\n" \
    "Assume 30\n" \
    "0,0,25\n"

    expected_timestamps = [0, 40]
    expected_last_frame_time = Fraction(40)
    expected_fpms = Fraction(30, 1000)

    timestamps, last_frame_time, fpms = TimestampsFileParser.parse_file(StringIO(timestamps_str), RoundingMethod.ROUND)

    assert timestamps == expected_timestamps
    assert last_frame_time == expected_last_frame_time
    assert fpms == expected_fpms


def test_from_timestamps_file_v1_multiple_comments():
    timestamps_str = "# timecode format v1\n" \
    "# comments\n" \
    "Assume 30\n" \
    "# comments\n" \
    "0,0,25\n" \
    "# comments\n"

    expected_timestamps = [0, 40]
    expected_last_frame_time = Fraction(40)
    expected_fpms = Fraction(30, 1000)

    timestamps, last_frame_time, fpms = TimestampsFileParser.parse_file(StringIO(timestamps_str), RoundingMethod.ROUND)

    assert timestamps == expected_timestamps
    assert last_frame_time == expected_last_frame_time
    assert fpms == expected_fpms


def test_from_timestamps_file_v1_empty_line():
    timestamps_str = "# timecode format v1\n" \
    "Assume 30\n" \
    "\n" \
    "0,0,25\n" \
    "\n"

    expected_timestamps = [0, 40]
    expected_last_frame_time = Fraction(40)
    expected_fpms = Fraction(30, 1000)

    timestamps, last_frame_time, fpms = TimestampsFileParser.parse_file(StringIO(timestamps_str), RoundingMethod.ROUND)

    assert timestamps == expected_timestamps
    assert last_frame_time == expected_last_frame_time
    assert fpms == expected_fpms


def test_from_timestamps_file_v1_empty_file():
    timestamps_str = "# timecode format v1\n"

    with pytest.raises(ValueError) as exc_info:
        TimestampsFileParser.parse_file(StringIO(timestamps_str), RoundingMethod.ROUND)
    assert str(exc_info.value) == "The timestamps file does not contain a valid 'Assume' line with the default number of frames per second."


def test_from_timestamps_file_v1_fps_bad_separator():
    timestamps_str = "# timecode format v1\n" \
    "Assume 30\n" \
    "5;10;15\n"

    with pytest.raises(ValueError) as exc_info:
        TimestampsFileParser.parse_file(StringIO(timestamps_str), RoundingMethod.ROUND)
    assert str(exc_info.value) == "The timestamps file contain a invalid line. Here is it: \"5;10;15\""


def test_from_timestamps_file_v1_fps_invalid_start_frame():
    timestamps_str = "# timecode format v1\n" \
    "Assume 30\n" \
    "5.5,10,15\n"

    with pytest.raises(ValueError) as exc_info:
        TimestampsFileParser.parse_file(StringIO(timestamps_str), RoundingMethod.ROUND)
    assert str(exc_info.value) == "The timestamps file contain a invalid line. Here is it: \"5.5,10,15\""


def test_from_timestamps_file_v1_fps_invalid_end_frame():
    timestamps_str = "# timecode format v1\n" \
    "Assume 30\n" \
    "5,10.5,15\n"

    with pytest.raises(ValueError) as exc_info:
        TimestampsFileParser.parse_file(StringIO(timestamps_str), RoundingMethod.ROUND)
    assert str(exc_info.value) == "The timestamps file contain a invalid line. Here is it: \"5,10.5,15\""


def test_from_timestamps_file_v1_fps_invalid_range_fps():
    timestamps_str = "# timecode format v1\n" \
    "Assume 30\n" \
    "5,10,15a\n"

    with pytest.raises(ValueError) as exc_info:
        TimestampsFileParser.parse_file(StringIO(timestamps_str), RoundingMethod.ROUND)
    assert str(exc_info.value) == "The timestamps file contain a invalid line. Here is it: \"5,10,15a\""


def test_from_timestamps_file_v1_end_less_than_start():
    timestamps_str = "# timecode format v1\n" \
    "Assume 30\n" \
    "20,0,25\n"

    with pytest.raises(ValueError) as exc_info:
        TimestampsFileParser.parse_file(StringIO(timestamps_str), RoundingMethod.ROUND)
    assert str(exc_info.value) == "End frame must be greater than or equal to start frame."


def test_from_timestamps_file_v1_invalid_assume():
    timestamps_str = "# timecode format v1\n" \
    "Assume 30a\n"

    with pytest.raises(ValueError) as exc_info:
        TimestampsFileParser.parse_file(StringIO(timestamps_str), RoundingMethod.ROUND)
    assert str(exc_info.value) == "The timestamps file does not contain a valid 'Assume' line with the default number of frames per second."


def test_from_timestamps_file_v1_overlapping_range():
    timestamps_str = "# timecode format v1\n" \
    "Assume 30\n" \
    "0,50,10\n" \
    "10,40,10\n"

    with pytest.raises(ValueError) as exc_info:
        TimestampsFileParser.parse_file(StringIO(timestamps_str), RoundingMethod.ROUND)
    assert str(exc_info.value) == "Override ranges must not overlap."


def test_from_timestamps_file_v1_negative_start_of_range():
    timestamps_str = "# timecode format v1\n" \
    "Assume 30\n" \
    "-10,10,25\n"

    with pytest.raises(ValueError) as exc_info:
        TimestampsFileParser.parse_file(StringIO(timestamps_str), RoundingMethod.ROUND)
    assert str(exc_info.value) == "Cannot specify frame rate for negative frames."


def test_from_timestamps_file_v1_start_end_overlap():
    timestamps_str = "# timecode format v1\n" \
    "Assume 30\n" \
    "0,1,25\n" \
    "1,2,25"

    with pytest.raises(ValueError) as exc_info:
        TimestampsFileParser.parse_file(StringIO(timestamps_str), RoundingMethod.ROUND)
    assert str(exc_info.value) == "Override ranges must not overlap."


def test_from_timestamps_file_v1_range_missing_info():
    timestamps_str = "# timecode format v1\n" \
    "Assume 30\n" \
    "0,1\n"

    with pytest.raises(ValueError) as exc_info:
        TimestampsFileParser.parse_file(StringIO(timestamps_str), RoundingMethod.ROUND)
    assert str(exc_info.value) == "The timestamps file contain a invalid line. Here is it: \"0,1\""


def test_from_timestamps_file_v1_range_too_many_info():
    timestamps_str = "# timecode format v1\n" \
    "Assume 30\n" \
    "0,1,1,1\n"

    with pytest.raises(ValueError) as exc_info:
        TimestampsFileParser.parse_file(StringIO(timestamps_str), RoundingMethod.ROUND)
    assert str(exc_info.value) == "The timestamps file contain a invalid line. Here is it: \"0,1,1,1\""


def test_from_timestamps_file_v2_string_int():
    timestamps_str = "# timecode format v2\n" \
    "80\n" \
    "120\n"

    expected_timestamps = [80, 120]
    expected_last_frame_time = Fraction(120)
    expected_fpms = Fraction(25, 1000)

    timestamps, last_frame_time, fpms = TimestampsFileParser.parse_file(StringIO(timestamps_str), RoundingMethod.ROUND)

    assert timestamps == expected_timestamps
    assert last_frame_time == expected_last_frame_time
    assert fpms == expected_fpms


def test_from_timestamps_file_v2_string_float():
    timestamps_str = "# timecode format v2\n" \
    "0\n" \
    "42.5\n"

    expected_timestamps = [0, 43]
    expected_last_frame_time = Fraction("42.5")
    expected_fpms = Fraction(1) / Fraction("42.5")

    timestamps, last_frame_time, fpms = TimestampsFileParser.parse_file(StringIO(timestamps_str), RoundingMethod.ROUND)

    assert timestamps == expected_timestamps
    assert last_frame_time == expected_last_frame_time
    assert fpms == expected_fpms


def test_from_timestamps_file_v2_string_round():
    timestamps_str = "# timecode format v2\n" \
    "0\n" \
    "10.5\n" \
    "20.2\n" \
    "30.8\n"

    expected_timestamps = [0, 11, 20, 31]
    expected_last_frame_time = Fraction("30.8")
    expected_fpms = Fraction(3) / Fraction("30.8")

    timestamps, last_frame_time, fpms = TimestampsFileParser.parse_file(StringIO(timestamps_str), RoundingMethod.ROUND)

    assert timestamps == expected_timestamps
    assert last_frame_time == expected_last_frame_time
    assert fpms == expected_fpms


def test_from_timestamps_file_v2_string_floor():
    timestamps_str = "# timecode format v2\n" \
    "0\n" \
    "10.5\n" \
    "20.2\n" \
    "30.8\n"

    expected_timestamps = [0, 10, 20, 30]
    expected_last_frame_time = Fraction("30.8")
    expected_fpms = Fraction(3) / Fraction("30.8")

    timestamps, last_frame_time, fpms = TimestampsFileParser.parse_file(StringIO(timestamps_str), RoundingMethod.FLOOR)

    assert timestamps == expected_timestamps
    assert last_frame_time == expected_last_frame_time
    assert fpms == expected_fpms


def test_from_timestamps_file_v2_string_with_comments():
    timestamps_str = "# timecode format v2\n" \
    "# This is a comment\n" \
    "0\n" \
    "#another_comment_without_space\n" \
    "42\n"

    expected_timestamps = [0, 42]
    expected_last_frame_time = Fraction(42)
    expected_fpms = Fraction(1, 42)

    timestamps, last_frame_time, fpms = TimestampsFileParser.parse_file(StringIO(timestamps_str), RoundingMethod.ROUND)

    assert timestamps == expected_timestamps
    assert last_frame_time == expected_last_frame_time
    assert fpms == expected_fpms


def test_from_timestamps_file_v2_empty_file():
    timestamps_str = "# timecode format v2\n"

    with pytest.raises(ValueError) as exc_info:
        TimestampsFileParser.parse_file(StringIO(timestamps_str), RoundingMethod.ROUND)
    assert str(exc_info.value) == "The timestamps file is empty."


def test_from_timestamps_file_v2_empty_line():
    timestamps_str = "# timecode format v2\n" \
    "\n" \
    "0\n" \
    "42\n"

    with pytest.raises(ValueError) as exc_info:
        TimestampsFileParser.parse_file(StringIO(timestamps_str), RoundingMethod.ROUND)
    assert str(exc_info.value) == "The timestamps file contain a invalid line. Here is it: \"\n\""


def test_from_timestamps_file_v2_out_of_order():
    timestamps_str = "# timecode format v2\n" \
    "0\n" \
    "25\n" \
    "10\n"

    with pytest.raises(ValueError) as exc_info:
        TimestampsFileParser.parse_file(StringIO(timestamps_str), RoundingMethod.ROUND)
    assert str(exc_info.value) == "The timestamps file contain timestamps NOT in ascending order."


def test_from_timestamps_file_v4_out_of_order():
    timestamps_str = "# timecode format v4\n" \
    "0\n" \
    "25\n" \
    "10\n"

    expected_timestamps = [0, 10, 25]
    expected_last_frame_time = Fraction(25)
    expected_fpms = Fraction(2, 25)

    timestamps, last_frame_time, fpms = TimestampsFileParser.parse_file(StringIO(timestamps_str), RoundingMethod.ROUND)

    assert timestamps == expected_timestamps
    assert last_frame_time == expected_last_frame_time
    assert fpms == expected_fpms


def test_from_timestamps_file_invalid_format():
    timestamps_str = "# timecode format v5\n"

    with pytest.raises(NotImplementedError) as exc_info:
        TimestampsFileParser.parse_file(StringIO(timestamps_str), RoundingMethod.ROUND)
    assert str(exc_info.value) == "The file uses version 5 for its timestamps, but this format is currently not compatible with PyonFX."


def test_from_timestamps_file_header_timestamp_vs_timecode():
    expected_timestamps = [0]
    expected_last_frame_time = Fraction(0)
    expected_fpms = Fraction(0)

    timestamps_str = "# timestamp format v4\n" \
    "0"

    timestamps, last_frame_time, fpms = TimestampsFileParser.parse_file(StringIO(timestamps_str), RoundingMethod.ROUND)
    assert timestamps == expected_timestamps
    assert last_frame_time == expected_last_frame_time
    assert fpms == expected_fpms

    timestamps_str = "# timecode format v4\n" \
    "0"

    timestamps, last_frame_time, fpms = TimestampsFileParser.parse_file(StringIO(timestamps_str), RoundingMethod.ROUND)
    assert timestamps == expected_timestamps
    assert last_frame_time == expected_last_frame_time
    assert fpms == expected_fpms
