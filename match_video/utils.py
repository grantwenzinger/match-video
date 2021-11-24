import json
import os
import shutil
import subprocess
from contextlib import contextmanager
from operator import attrgetter
from tempfile import NamedTemporaryFile
from typing import Iterator, List, Tuple

from match_video.anchor import Anchor


def write_anchors(
    input_video_path: str, output_video_path: str, anchors: List[Anchor]
) -> None:
    """Write anchors to a video file.

    Anchors are written as chapters in the video's metadata. Any existing anchors will
    be overwritten.

    Args:
        input_video_path: The path to a video.
        output_video_path: The path to write the video with anchors to.
        anchors: A list of anchors specifying the start of each half and any
            discontinuities in the video.
    """
    existing_metadata: str

    with NamedTemporaryFile("r") as existing_metadata_file:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                input_video_path,
                "-f",
                "ffmetadata",
                existing_metadata_file.name,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        existing_metadata_file.seek(0)
        existing_metadata = existing_metadata_file.read()

    existing_metadata_without_chapters = (
        existing_metadata.split("[CHAPTER]")[0].strip()
        if "[CHAPTER]" in existing_metadata
        else existing_metadata
    )

    updated_metadata = existing_metadata_without_chapters

    for anchor in anchors:
        time = int(anchor.video_time * 1000)

        chapter = f"""

[CHAPTER]
TIMEBASE=1/1000
START={time}
END={time + 1}
title=Period {anchor.period}, {anchor.clock}"""

        updated_metadata += chapter

    with NamedTemporaryFile("w") as updated_metadata_file:
        updated_metadata_file.write(updated_metadata)
        updated_metadata_file.seek(0)

        def write_video_with_metadata(path: str) -> None:
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    input_video_path,
                    "-i",
                    updated_metadata_file.name,
                    "-map_metadata",
                    "1",
                    "-codec",
                    "copy",
                    path,
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

        if os.path.exists(output_video_path) and os.path.samefile(
            input_video_path, output_video_path
        ):
            # ffmpeg can't update video metadata in place, so use an intermediate file

            with NamedTemporaryFile("w", suffix=".mp4") as intermediate_file:
                write_video_with_metadata(intermediate_file.name)
                shutil.copy2(intermediate_file.name, output_video_path)
        else:
            write_video_with_metadata(output_video_path)


def read_anchors(video_path: str) -> List[Anchor]:
    """Read the anchor points from the chapter metadata of a video file.

    Args:
        video_path: The path to a video.

    Returns:
        The list of anchors set for the video.

    Raises:
        ValueError: The video's metadata could not be read.
    """
    result_json = subprocess.run(
        [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_error",
            "-show_chapters",
            video_path,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    result = json.loads(result_json.stdout)

    if "error" in result:
        raise ValueError(
            f"Unable to read the metadata for {video_path}, {result['error']['string']}"
        )

    def get_anchor(chapter: dict) -> Anchor:
        period_str, clock_str = chapter["tags"]["title"].split(", ")
        period = int(period_str.split("Period ")[-1])
        clock = float(clock_str)

        video_time = float(chapter["start_time"])

        return Anchor(period, clock, video_time)

    anchors = [get_anchor(chapter) for chapter in result["chapters"]]

    return anchors


def get_clip(
    video_path: str, period: int, start_clock: float, end_clock: float
) -> bytes:
    """Get a clip from a match by period and clock.

    Args:
        video_path: The path to a video.
        period: The period of the match the clip is in.
        start_clock: The start of the clip in seconds since the start of the period.
        end_clock: The end of the clip in seconds since the start of the period.

    Returns:
        The video clip as bytes.

    Raises:
        ValueError: The video does not have anchors or the clips is before the first
            anchor in its period.
    """
    anchors = read_anchors(video_path)

    if len(anchors) == 0:
        raise ValueError(f"{video_path} has no set anchors")

    start_video_time, end_video_time = _get_video_times(
        anchors, period, start_clock, end_clock
    )

    clip: bytes

    with _video_sans_chapters(video_path) as video_sans_chapters_path:
        with NamedTemporaryFile("rb", suffix=".mp4") as clip_file:
            _extract_clip(
                video_sans_chapters_path,
                clip_file.name,
                start_video_time,
                end_video_time,
            )

            clip = clip_file.read()

    return clip


def get_clips(video_path: str, clip_clocks: List[dict]) -> bytes:
    """Get clips from a match by period and clock.

    Args:
        video_path: The path to a video.
        clip_clocks: A list of clips to select and stitch together. Each clip
            dictionary should have a period, start_clock, and end_clock. These values
            are the same as with get_clip.

    Returns:
        The video clips as bytes.

    Raises:
        ValueError: The video does not have anchors or one of the clips is before the
            first anchor in its period.
    """
    anchors = read_anchors(video_path)

    if len(anchors) == 0:
        raise ValueError(f"{video_path} has no set anchors")

    clip_files: List

    with _video_sans_chapters(video_path) as video_sans_chapters_path:

        def create_clip_file(clip_info: dict):
            clip_file = NamedTemporaryFile("rb", suffix=".mp4")

            start_video_time, end_video_time = _get_video_times(
                anchors,
                clip_info["period"],
                clip_info["start_clock"],
                clip_info["end_clock"],
            )

            _extract_clip(
                video_sans_chapters_path,
                clip_file.name,
                start_video_time,
                end_video_time,
            )

            return clip_file

        clip_files = [create_clip_file(clip_info) for clip_info in clip_clocks]

    clips: bytes

    with NamedTemporaryFile("w") as clip_paths_file:
        clip_paths = "\n".join([f"file '{clip_file.name}'" for clip_file in clip_files])
        clip_paths_file.write(clip_paths)
        clip_paths_file.seek(0)

        with NamedTemporaryFile("rb", suffix=".mp4") as clips_file:
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-f",
                    "concat",
                    "-safe",
                    "0",
                    "-i",
                    clip_paths_file.name,
                    "-c",
                    "copy",
                    clips_file.name,
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            clips = clips_file.read()

    for clip_file in clip_files:
        clip_file.close()

    return clips


def _get_video_times(
    anchors: List[Anchor], period: int, start_clock: float, end_clock: float
) -> Tuple[float, float]:
    """Convert period and match clocks into video times.

    Args:
        anchors: A video's anchors.
        period: The period of the match.
        start_clock: A time since the start of the period.
        end_clock: A time since the start of the period.

    Returns:
        A pair, (start_video_time, end_video_time), that correspond to start_clock and
        end_clock in video time.

    Raises:
        ValueError: There are no anchors in the period before start_clock.
    """
    prior_anchors = sorted(
        [
            anchor
            for anchor in anchors
            if anchor.period == period and anchor.clock <= start_clock
        ],
        key=attrgetter("clock"),
    )

    if len(prior_anchors) == 0:
        minute = int(start_clock / 60)
        second = int(start_clock % 60)

        raise ValueError(
            f"No anchors set in period {period} before {minute}:{second:02}"
        )

    last_anchor = prior_anchors[-1]
    start_offset = start_clock - last_anchor.clock
    start_video_time = last_anchor.video_time + start_offset

    duration = end_clock - start_clock
    end_video_time = start_video_time + duration

    return start_video_time, end_video_time


@contextmanager
def _video_sans_chapters(video_path: str) -> Iterator[str]:
    """Create a copy of a video without its chapters.

    Args:
        video_path: The path to a video.

    Yields:
        The path to the copied video file without chapters.
    """
    with NamedTemporaryFile("rb", suffix=".mp4") as video_sans_chapters_file:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                video_path,
                "-map",
                "0",
                "-vcodec",
                "copy",
                "-acodec",
                "copy",
                "-map_chapters",
                "-1",
                video_sans_chapters_file.name,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        yield video_sans_chapters_file.name


def _extract_clip(
    input_video_path: str, output_video_path: str, start_time: float, end_time: float
) -> None:
    """Extract a clip from input_video_path and write it to output_video_path.

    Output can be incorrect if input_video_path has chapters. Use _video_sans_chapters
    to copy the video file without chapters before using this method.

    Args:
        input_video_path: The path to a video.
        output_video_path: The path to write the video with anchors to.
        start_time: The start of the clip in seconds since video start.
        end_time: The end of the clip in seconds since video start.
    """
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-ss",
            f"{start_time:0.2f}",
            "-to",
            f"{end_time:0.2f}",
            "-i",
            input_video_path,
            "-map",
            "0",
            "-vcodec",
            "copy",
            "-acodec",
            "copy",
            output_video_path,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
