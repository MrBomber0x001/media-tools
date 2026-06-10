# SoundCloud Downloader + Video Converter

A small Python utility suite for downloading SoundCloud tracks/playlists and converting local video files to 3GP.

## Overview

This repository contains two GUI-based tools:

- `downloader.py`: A SoundCloud downloader with support for multiple URLs, playlist track selection, parallel downloads, and download logging.
- `video_converter_gui.py`: A local video converter that converts common video/audio formats to `.3gp` using `ffmpeg`.

## Requirements

- Python 3.12+
- `ffmpeg` installed and available on your PATH for `video_converter_gui.py`
- `scdl` Python package for `downloader.py`

Install dependencies with:

```bash
pip install scdl
```

## Usage

### SoundCloud Downloader

Run the downloader UI:

```bash
python downloader.py
```

Features:

- Paste one or more SoundCloud URLs into the text box
- Use one URL per line for batch downloads
- Download playlist directly or select individual tracks from a playlist
- Select / unselect all playlist tracks
- Parallel downloads with configurable thread count
- Download log output shown in the app

### Video Converter

Run the video converter UI:

```bash
python video_converter_gui.py
```

Features:

- Convert videos from formats such as `.mp4`, `.webm`, `.mkv`, `.avi`, `.mov`, `.flv`, `.m4v`, `.ogg`, `.wmv`, `.mpeg`, `.mpg`
- Output files are converted to `.3gp`
- Progress bar and conversion log

## Notes

- Ensure `scdl` is installed and accessible for SoundCloud downloading.
- Ensure `ffmpeg` is installed and accessible on your system PATH for conversions.
- The converter currently outputs files into the same folder as the source files.

## License

No license specified.
