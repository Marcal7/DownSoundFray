# DownSoundFray

DownSoundFray is a simple, web-based application to download music from various platforms, including Spotify, YouTube, and SoundCloud. It provides an elegant UI to manage downloads and automatically handles conversions.

## Features
- **Spotify Integration**: Download entire playlists or single tracks directly using `spotdl`.
- **YouTube & SoundCloud**: Powered by `yt-dlp` to download audio from these platforms.
- **Real-time Progress**: Displays the current status, download percentage, and file information for active downloads.
- **Custom Download Location**: easily change the download directory through a native folder picker dialog.

## Requirements
- Python 3.8+
- [FFmpeg](https://ffmpeg.org/download.html) (Required by `spotdl` and `yt-dlp` to extract and process audio)

## Installation

1. Clone or download this repository.
2. Open your terminal or command prompt in the project directory.
3. Install the required Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Ensure you have `ffmpeg` installed and added to your system's PATH.

## Usage

You can start the DownSoundFray server by running the included batch file:

```bash
iniciar.bat
```

Alternatively, you can run the server manually:

```bash
python -m uvicorn main:app --port 8000
```

Once started, open your web browser and navigate to `http://127.0.0.1:8000`.
