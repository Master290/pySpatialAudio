# pySpatialAudio

**pySpatialAudio** is a powerful Python-based music player designed for advanced spatial audio playback and visualization. It supports multi-channel audio configurations (up to 24 channels) and features a dynamic, scalable user interface for visualizing and controlling sound fields in real-time. [Watch the showcase](https://youtu.be/wbYkrV6kors)

![Screenshot](https://i.imgur.com/qlCgWXM.png)
24 channel song example

## Features

*   Native support for **Stereo**, **5.1**, **7.1**, and up to **24-Channel** (MPEG-H/22.2) layouts.
*   Uses **FFmpeg** backend to decode virtually any audio format (WAV, FLAC, MP3, M4A, E-AC3, (TrueHD should work)).
    *   *Note: Proprietary MPEG-H 3D Audio requires a FFmpeg build with `libmpeghdec` enabled or you should decode it to .wav file*
*   **Cool UI things**:
    *   Automatically arranges speakers in 1, 2, or 3 rings based on channel count.
    *   Interactive canvas—zoom in with the mouse wheel and drag to pan around the sound field. Laggy as hell, I'll fix it someday.
    *   Dynamic sound beams visualize active channels and volume levels.
*   **Channel Control**:
    *   Isolate or silence any individual channel.
    *   Remap input channels to different output speakers on the fly.
    *   Gain control for every speaker.
*  Automatically adjusts widget size for high-channel-count layouts to reduce clutter.

## Requirements

*   **Python 3.10+**
*   **FFmpeg** (Must be installed and added to system PATH)
