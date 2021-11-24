import json
import subprocess
from unittest.mock import MagicMock, patch

import pytest

import match_video.utils as utils
from match_video.anchor import Anchor


@patch("match_video.utils.NamedTemporaryFile")
@patch("os.path.exists", return_value=False)
@patch("subprocess.run")
def test_write_anchors_no_periods(
    mock_subprocess_run, mock_exists, mock_temp_file_context
):
    existing_metadata = """;FFMETADATA1
major_brand=brand
minor_version=1
compatible_brands=compatible
encoder=Lavf58.76.100"""

    mock_temp_file_context.return_value.__enter__.return_value.read.return_value = (
        existing_metadata
    )

    anchors = []

    utils.write_anchors("input_path", "output_path", anchors)

    mock_temp_file = mock_temp_file_context.return_value.__enter__.return_value
    mock_temp_file.write.assert_called_once_with(existing_metadata)


@patch("match_video.utils.NamedTemporaryFile")
@patch("os.path.exists", return_value=False)
@patch("subprocess.run")
def test_write_anchors_two_periods(
    mock_subprocess_run, mock_exists, mock_temp_file_context
):
    existing_metadata = """;FFMETADATA1
major_brand=brand
minor_version=1
compatible_brands=compatible
encoder=Lavf58.76.100"""

    mock_temp_file_context.return_value.__enter__.return_value.read.return_value = (
        existing_metadata
    )

    anchors = [
        Anchor(1, 0.0, 10.0),
        Anchor(2, 0.0, 1000.0),
    ]

    utils.write_anchors("input_path", "output_path", anchors)

    expected_metadata = """;FFMETADATA1
major_brand=brand
minor_version=1
compatible_brands=compatible
encoder=Lavf58.76.100

[CHAPTER]
TIMEBASE=1/1000
START=10000
END=10001
title=Period 1, 0.0

[CHAPTER]
TIMEBASE=1/1000
START=1000000
END=1000001
title=Period 2, 0.0"""

    mock_temp_file = mock_temp_file_context.return_value.__enter__.return_value
    mock_temp_file.write.assert_called_once_with(expected_metadata)


@patch("match_video.utils.NamedTemporaryFile")
@patch("os.path.exists", return_value=False)
@patch("subprocess.run")
def test_write_anchors_overwrite(
    mock_subprocess_run, mock_exists, mock_temp_file_context
):
    existing_metadata = """;FFMETADATA1
major_brand=brand
minor_version=1
compatible_brands=compatible
encoder=Lavf58.76.100

[CHAPTER]
TIMEBASE=1/1000
START=10000
END=10001
title=Period 1, 0.0

[CHAPTER]
TIMEBASE=1/1000
START=1000000
END=1000001
title=Period 2, 0.0"""

    mock_temp_file_context.return_value.__enter__.return_value.read.return_value = (
        existing_metadata
    )

    anchors = [
        Anchor(3, 10.0, 30.0),
    ]

    utils.write_anchors("input_path", "output_path", anchors)

    expected_metadata = """;FFMETADATA1
major_brand=brand
minor_version=1
compatible_brands=compatible
encoder=Lavf58.76.100

[CHAPTER]
TIMEBASE=1/1000
START=30000
END=30001
title=Period 3, 10.0"""

    mock_temp_file = mock_temp_file_context.return_value.__enter__.return_value
    mock_temp_file.write.assert_called_once_with(expected_metadata)


@patch("shutil.copy2")
@patch("match_video.utils.NamedTemporaryFile")
@patch("os.path.samefile", return_value=True)
@patch("os.path.exists", return_value=True)
@patch("subprocess.run")
def test_write_anchors_inplace(
    mock_subprocess_run, mock_exists, mock_samefile, mock_temp_file_context, mock_copy2
):
    existing_metadata = """;FFMETADATA1
major_brand=brand
minor_version=1
compatible_brands=compatible
encoder=Lavf58.76.100"""

    mock_temp_file_context.return_value.__enter__.return_value.read.return_value = (
        existing_metadata
    )
    mock_temp_file_context.return_value.__enter__.return_value.name = (
        "intermediate_file_name"
    )

    anchors = [
        Anchor(1, 0.0, 10.0),
        Anchor(2, 0.0, 1000.0),
    ]

    utils.write_anchors("path", "path", anchors)

    expected_metadata = """;FFMETADATA1
major_brand=brand
minor_version=1
compatible_brands=compatible
encoder=Lavf58.76.100

[CHAPTER]
TIMEBASE=1/1000
START=10000
END=10001
title=Period 1, 0.0

[CHAPTER]
TIMEBASE=1/1000
START=1000000
END=1000001
title=Period 2, 0.0"""

    mock_temp_file = mock_temp_file_context.return_value.__enter__.return_value
    mock_temp_file.write.assert_called_once_with(expected_metadata)

    mock_copy2.assert_called_once_with("intermediate_file_name", "path")


@patch("subprocess.run")
def test_read_anchors_no_periods(mock_subprocess_run):
    mock_subprocess_run.return_value = MagicMock()
    mock_subprocess_run.return_value.stdout = json.dumps({"chapters": []})

    result = utils.read_anchors("path")

    mock_subprocess_run.assert_called_once_with(
        [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_error",
            "-show_chapters",
            "path",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert len(result) == 0


@patch("subprocess.run")
def test_read_anchors_one_period(mock_subprocess_run):
    mock_subprocess_run.return_value = MagicMock()
    mock_subprocess_run.return_value.stdout = json.dumps(
        {
            "chapters": [
                {
                    "id": 0,
                    "time_base": "1/1000",
                    "start": 0,
                    "start_time": "0.000000",
                    "end": 1000000,
                    "end_time": "1000.000000",
                    "tags": {"title": "Period 1, 0.0"},
                }
            ]
        }
    )

    result = utils.read_anchors("path")

    mock_subprocess_run.assert_called_once_with(
        [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_error",
            "-show_chapters",
            "path",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert len(result) == 1

    assert result[0] == Anchor(1, 0.0, 0.0)


@patch("subprocess.run")
def test_read_anchors_many_periods(mock_subprocess_run):
    mock_subprocess_run.return_value = MagicMock()
    mock_subprocess_run.return_value.stdout = json.dumps(
        {
            "chapters": [
                {
                    "id": 0,
                    "time_base": "1/1000",
                    "start": 0,
                    "start_time": "0.000000",
                    "end": 1000000,
                    "end_time": "1000.000000",
                    "tags": {"title": "Period 1, 0.0"},
                },
                {
                    "id": 0,
                    "time_base": "1/1000",
                    "start": 1100000,
                    "start_time": "1100.000000",
                    "end": 2100000,
                    "end_time": "2100.000000",
                    "tags": {"title": "Period 2, 10.0"},
                },
                {
                    "id": 0,
                    "time_base": "1/1000",
                    "start": 5000000,
                    "start_time": "5000.000000",
                    "end": 5100000,
                    "end_time": "5100.000000",
                    "tags": {"title": "Period 3, 0.0"},
                },
                {
                    "id": 0,
                    "time_base": "1/1000",
                    "start": 5200000,
                    "start_time": "5200.000000",
                    "end": 5300000,
                    "end_time": "5300.000000",
                    "tags": {"title": "Period 4, 0.0"},
                },
            ]
        }
    )

    result = utils.read_anchors("path")

    mock_subprocess_run.assert_called_once_with(
        [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_error",
            "-show_chapters",
            "path",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert len(result) == 4

    assert result[0] == Anchor(1, 0.0, 0.0)
    assert result[1] == Anchor(2, 10.0, 1100.0)
    assert result[2] == Anchor(3, 0.0, 5000.0)
    assert result[3] == Anchor(4, 0.0, 5200.0)


@patch("subprocess.run")
def test_read_anchors_bad_path(mock_subprocess_run):
    mock_subprocess_run.return_value = MagicMock()
    mock_subprocess_run.return_value.stdout = json.dumps(
        {"error": {"code": -2, "string": "No such file or directory"}}
    )

    with pytest.raises(ValueError):
        utils.read_anchors("path")


@patch("match_video.utils._extract_clip")
@patch("match_video.utils.NamedTemporaryFile")
@patch("match_video.utils._video_sans_chapters")
@patch(
    "match_video.utils.read_anchors",
    return_value=[
        Anchor(1, 0.0, 0.0),
        Anchor(2, 0.0, 1000.0),
    ],
)
def test_get_clip(
    mock_read_anchors,
    mock_video_sans_chapters_context,
    mock_temp_file_context,
    mock_extract_clip,
):
    clip = utils.get_clip("path", 1, 0.0, 10.0)

    video_sans_chapters_path = (
        mock_video_sans_chapters_context.return_value.__enter__.return_value
    )
    clip_file_path = mock_temp_file_context.return_value.__enter__.return_value.name

    mock_extract_clip.assert_called_once_with(
        video_sans_chapters_path, clip_file_path, 0.0, 10.0
    )


@patch("match_video.utils.read_anchors", return_value=[])
def test_get_clip_no_anchors(mock_read_anchors):
    with pytest.raises(ValueError):
        utils.get_clip("path", 1, 0.0, 10.0)


@patch("match_video.utils.read_anchors", return_value=[])
def test_get_clips_no_anchors(mock_read_anchors):
    clip_clocks = [
        {"period": 1, "start_clock": 0.0, "end_clock": 10.0},
    ]

    with pytest.raises(ValueError):
        utils.get_clips("path", clip_clocks)


def test_get_video_time_half_start():
    anchors = [
        Anchor(1, 0.0, 100.0),
        Anchor(2, 0.0, 10000.0),
    ]

    start_video_time, end_video_time = utils._get_video_times(anchors, 1, 0.0, 10.0)

    assert start_video_time == 100.0
    assert end_video_time == 110.0


def test_get_video_time_offset():
    anchors = [
        Anchor(1, 0.0, 100.0),
        Anchor(2, 0.0, 10000.0),
    ]

    start_video_time, end_video_time = utils._get_video_times(anchors, 1, 670.0, 1000.0)

    assert start_video_time == 770.0
    assert end_video_time == 1100.0


def test_get_video_time_later_period():
    anchors = [
        Anchor(1, 0.0, 100.0),
        Anchor(2, 0.0, 10000.0),
        Anchor(3, 0.0, 20000.0),
        Anchor(4, 0.0, 30000.0),
    ]

    start_video_time, end_video_time = utils._get_video_times(anchors, 4, 100, 1000.0)

    assert start_video_time == 30100.0
    assert end_video_time == 31000.0


def test_get_video_time_before_discontinuity():
    anchors = [
        Anchor(1, 0.0, 100.0),
        Anchor(1, 1000.0, 2000.0),
        Anchor(2, 0.0, 10000.0),
    ]

    start_video_time, end_video_time = utils._get_video_times(anchors, 1, 500.0, 600.0)

    assert start_video_time == 600.0
    assert end_video_time == 700.0


def test_get_video_time_after_discontinuity():
    anchors = [
        Anchor(1, 0.0, 100.0),
        Anchor(1, 1000.0, 2000.0),
        Anchor(2, 0.0, 10000.0),
    ]

    start_video_time, end_video_time = utils._get_video_times(
        anchors, 1, 1500.0, 1600.0
    )

    assert start_video_time == 2500.0
    assert end_video_time == 2600.0


def test_get_video_time_before_first_anchor_in_period():
    anchors = [
        Anchor(1, 1000.0, 2000.0),
        Anchor(2, 0.0, 10000.0),
    ]

    with pytest.raises(ValueError):
        utils._get_video_times(anchors, 1, 10.0, 20.0)
