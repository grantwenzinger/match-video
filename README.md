# Match Video

This is a Python library that simplifies working with video from soccer matches. It allows match video to be selected intuitively by period number and clock, instead of absolute video time.

To accomplish this the start of each period is set as a chapter in the match video's metadata. Clips from the video can then be selected by period number and clock. ffmpeg handles both reading and writing the video chapter metadata and clip selection.

## Installation

### Requirements
- Python 3.6 or newer
- [ffmpeg](https://ffmpeg.org)

```shell
pip install match-video
```

## Usage

Before the video can be used, the start time of each half needs to be set.

```shell
match-video set-half-starts path/to/video.mp4 0:04 63:20
```

Then it is easy to select match video by period and clock!

```python
import match_video as mv

# get the third minute of the match
clip = mv.get_clip("path/to/video.mp4", period=1, start_clock=180, end_clock=240)

# get the start of each half and concatenate them
clip_clocks = [
    {"period": 1, "start_clock": 0, "end_clock": 30},
    {"period": 2, "start_clock": 0, "end_clock": 30},
]
clips = mv.get_clips("path/to/video.mp4", clip_clocks)
```

See the [examples](https://gitlab.com/grantwenzinger/match-video/-/tree/main/examples) to see how to save or display video clips.

## Support

<grantwenzinger@gmail.com>

## License

[MIT](https://choosealicense.com/licenses/mit/)
