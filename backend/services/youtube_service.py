"""
YouTube service: extract video metadata and download audio using yt-dlp.
"""

import yt_dlp
import re
import os
import sys

# Fix Windows console encoding for Unicode
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Set environment variable to force UTF-8 in subprocesses
os.environ["PYTHONIOENCODING"] = "utf-8"

DOWNLOADS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "downloads")


def extract_video_id(url: str) -> str | None:
    """Extract the 11-character video ID from various YouTube URL formats."""
    patterns = [
        r'(?:v=)([0-9A-Za-z_-]{11})',
        r'(?:youtu\.be/)([0-9A-Za-z_-]{11})',
        r'(?:embed/)([0-9A-Za-z_-]{11})',
        r'(?:shorts/)([0-9A-Za-z_-]{11})',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def extract_video_info(url: str) -> dict:
    """
    Extract video metadata without downloading.
    Returns dict with id, title, duration, thumbnail.
    """
    video_id = extract_video_id(url)
    if not video_id:
        raise ValueError(f"Could not extract video ID from URL: {url}")

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return {
            "id": video_id,
            "title": info.get("title", "Unknown Title"),
            "duration": info.get("duration", 0),
            "thumbnail": info.get("thumbnail", ""),
            "uploader": info.get("uploader", "Unknown"),
        }


def download_audio(url: str, video_id: str) -> str:
    """
    Download audio from a YouTube video using yt-dlp.
    Returns the path to the downloaded audio file.
    """
    os.makedirs(DOWNLOADS_DIR, exist_ok=True)
    output_template = os.path.join(DOWNLOADS_DIR, f"{video_id}.%(ext)s")

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_template,
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        ext = info.get('ext', 'webm')
        downloaded_path = os.path.join(DOWNLOADS_DIR, f"{video_id}.{ext}")

        # yt-dlp might save with a different extension, find it
        if not os.path.exists(downloaded_path):
            for f in os.listdir(DOWNLOADS_DIR):
                if f.startswith(video_id):
                    downloaded_path = os.path.join(DOWNLOADS_DIR, f)
                    break

        if not os.path.exists(downloaded_path):
            raise FileNotFoundError(f"Audio file not found after download for video: {video_id}")

        return downloaded_path
