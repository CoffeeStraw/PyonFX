import os
import pytest
from pyonfx import *

dir_path = os.path.dirname(os.path.realpath(__file__))

def test_validate_timecodes():

    with pytest.raises(ValueError) as exc_info:
        timestamps.from_timestamps_file(
            os.path.join(dir_path, "Ass", "timestamps_short.txt")
        )
    assert str(exc_info.value) == "There must be at least 2 timestamps."

    with pytest.raises(ValueError) as exc_info:
        timestamps.from_timestamps_file(
            os.path.join(dir_path, "Ass", "timestamps_not_sorted.txt")
        )
    assert str(exc_info.value) == "Timestamps must be in non-decreasing order."

    with pytest.raises(ValueError) as exc_info:
        timestamps.from_timestamps_file(
            os.path.join(dir_path, "Ass", "timestamps_identical.txt")
        )
    assert str(exc_info.value) == "Timestamps must not be all identical."