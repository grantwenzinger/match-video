from unittest.mock import call, patch

import match_video.cli as cli
from match_video.anchor import Anchor


@patch("match_video.cli.utils.write_anchors")
def test_set_half_starts(mock_write_anchors):
    cli.set_half_starts("input_path", "0:00", "60:00", "output_path")

    mock_write_anchors.assert_called_once_with(
        "input_path",
        "output_path",
        [
            Anchor(1, 0.0, 0.0),
            Anchor(2, 0.0, 3600.0),
        ],
    )


@patch("match_video.cli.utils.write_anchors")
def test_set_half_starts_inplace(mock_write_anchors):
    cli.set_half_starts("path", "0:00", "60:00")

    mock_write_anchors.assert_called_once_with(
        "path",
        "path",
        [
            Anchor(1, 0.0, 0.0),
            Anchor(2, 0.0, 3600.0),
        ],
    )


@patch("match_video.cli.typer.echo")
@patch(
    "match_video.cli.utils.read_anchors",
    return_value=[
        Anchor(1, 0.0, 0.0),
        Anchor(2, 0.0, 3600.0),
    ],
)
def test_read_anchors(mock_read_anchors, mock_typer_echo):
    cli.read_anchors("path")

    expected_calls = [
        call("Period 1 0:00 | 0:00 in video"),
        call("Period 2 0:00 | 60:00 in video"),
    ]
    mock_typer_echo.assert_has_calls(expected_calls, any_order=False)


@patch("match_video.cli.typer.echo")
@patch("match_video.cli.utils.read_anchors", return_value=[])
def test_read_anchors_no_anchors(mock_read_anchors, mock_typer_echo):
    cli.read_anchors("path")

    mock_typer_echo.assert_called_once_with("No anchors set for video")
