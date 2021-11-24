import sys

import match_video as mv


def main():
    """Get the first minute of a match and save it."""
    video_path = sys.argv[1]

    print("Getting match kickoff...")
    clip = mv.get_clip(video_path, period=1, start_clock=0, end_clock=60)

    with open("kickoff.mp4", "wb") as clip_file:
        clip_file.write(clip)

    print("Kickoff saved as kickoff.mp4!")


if __name__ == "__main__":
    main()
