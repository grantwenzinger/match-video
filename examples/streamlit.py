import base64

import streamlit as st

import match_video as mv


def main():
    """Streamlit app that shows the start of each half of a match."""
    st.subheader("Start of Each Half")

    clips = mv.get_clips(
        "videos/broadcast.mp4",
        [
            {"period": 1, "start_clock": 0, "end_clock": 10},
            {"period": 2, "start_clock": 0, "end_clock": 10},
        ],
    )
    st.video(clips)

    # create link to download video
    data_base_64 = base64.b64encode(clips).decode()
    download_link = f'<a href="data:file/txt;base64,{data_base_64}" download="clips.mp4">Download</a>'
    st.markdown(download_link, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
