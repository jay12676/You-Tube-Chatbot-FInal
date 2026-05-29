"""
YouTube service: extract video metadata and download audio using yt-dlp.
"""

import yt_dlp
import re
import os
import sys
import base64
import tempfile

# Fix Windows console encoding for Unicode
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Set environment variable to force UTF-8 in subprocesses
os.environ["PYTHONIOENCODING"] = "utf-8"

DOWNLOADS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "downloads")


def _get_ydl_auth_opts() -> dict:
    """
    Returns extra yt-dlp options for authentication/bot-bypass.
    - Reads YTDLP_COOKIES_B64 (base64-encoded cookies.txt) and writes to a temp file.
    - Reads YTDLP_PROXY if set.
    """
    opts = {}
    cookies_b64 = os.getenv("YTDLP_COOKIES_B64")
    if cookies_b64:
        try:
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="wb")
            tmp.write(base64.urlsafe_b64decode(cookies_b64 + '=='))
            tmp.close()
            opts["cookiefile"] = tmp.name
        except Exception as e:
            print(f"[yt-dlp] Failed to load cookies: {e}")
    proxy = os.getenv("YTDLP_PROXY")
    if proxy:
        opts["proxy"] = proxy
    return opts


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

    # Use a clean single-video URL so yt-dlp never follows a &list=RD... radio
    # mix or &start_radio=1 into a different (often unavailable) video.
    clean_url = f"https://www.youtube.com/watch?v={video_id}"

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'noplaylist': True,
        'extractor_args': {'youtube': {'player_client': ['android_music', 'mediaconnect']}},
        **_get_ydl_auth_opts(),
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(clean_url, download=False)
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

    # Clean single-video URL — ignore any &list=RD.../&start_radio params so we
    # download the requested video, not the next one in an auto-generated mix.
    clean_url = f"https://www.youtube.com/watch?v={video_id}"

    ydl_opts = {
        'format': 'bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best',
        'outtmpl': output_template,
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'noplaylist': True,
        'extractor_args': {'youtube': {'player_client': ['android_music', 'mediaconnect']}},
        **_get_ydl_auth_opts(),
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(clean_url, download=True)
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


def download_video(url: str, video_id: str) -> str:
    """
    Download a low-resolution video file (for study-notes frame extraction).

    Mirrors download_audio but fetches a small mp4 video stream — enough for
    ffmpeg to grab readable slide/diagram frames without a large download.
    Returns the path to the downloaded video file.
    """
    os.makedirs(DOWNLOADS_DIR, exist_ok=True)
    output_template = os.path.join(DOWNLOADS_DIR, f"{video_id}.%(ext)s")

    # Clean single-video URL so we never follow a &list=RD.../&start_radio mix.
    clean_url = f"https://www.youtube.com/watch?v={video_id}"

    ydl_opts = {
        'format': 'bestvideo[height<=480][ext=mp4]/best[height<=480][ext=mp4]/best',
        'outtmpl': output_template,
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        'extractor_args': {'youtube': {'player_client': ['android_music', 'mediaconnect']}},
        **_get_ydl_auth_opts(),
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(clean_url, download=True)
        ext = info.get('ext', 'mp4')
        downloaded_path = os.path.join(DOWNLOADS_DIR, f"{video_id}.{ext}")

        if not os.path.exists(downloaded_path):
            for f in os.listdir(DOWNLOADS_DIR):
                if f.startswith(video_id):
                    downloaded_path = os.path.join(DOWNLOADS_DIR, f)
                    break

        if not os.path.exists(downloaded_path):
            raise FileNotFoundError(f"Video file not found after download for: {video_id}")

        return downloaded_path


def extract_playlist_info(url: str) -> dict:
    """
    Extract metadata for every video in a YouTube playlist.

    Returns:
        {
            "playlist_title": str,
            "videos": [{"id", "title", "duration", "thumbnail", "url"}, ...],
            "total": int,
        }
    """
    # When the URL is a watch URL with a list= param (e.g. watch?v=xxx&list=yyy),
    # yt-dlp returns a redirect object instead of expanding the playlist.
    # Always convert to a canonical playlist URL so we get all entries.
    list_match = re.search(r'list=([A-Za-z0-9_-]+)', url)
    if list_match:
        url = f"https://www.youtube.com/playlist?list={list_match.group(1)}"

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,   # metadata only, no download
        "ignoreerrors": True,   # skip unavailable videos
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        if not info:
            # yt-dlp returns None for un-enumerable lists (e.g. RD radio mixes)
            raise ValueError(
                "Could not load this playlist — it may be a YouTube auto-mix/radio "
                "(list starting with 'RD'). Paste the single video URL instead."
            )
        # Force-materialise the LazyList INSIDE the context so the ydl
        # network session is still open when each entry is fetched.
        raw_entries = list(info.get("entries") or [])

    print(f"[YouTube] Raw entries fetched: {len(raw_entries)}")

    videos = []
    for entry in raw_entries:
        if not entry:
            continue
        vid_id = entry.get("id") or entry.get("url", "").split("v=")[-1].split("&")[0]
        if not vid_id:
            print(f"[YouTube] Skipping entry with no id: {list(entry.keys())}")
            continue
        videos.append({
            "id": vid_id,
            "title": entry.get("title", "Unknown Title"),
            "duration": int(entry.get("duration") or 0),
            "thumbnail": (
                entry.get("thumbnail")
                or f"https://i.ytimg.com/vi/{vid_id}/mqdefault.jpg"
            ),
            "url": f"https://www.youtube.com/watch?v={vid_id}",
        })

    print(f"[YouTube] Playlist '{info.get('title')}': {len(videos)} videos")
    return {
        "playlist_title": info.get("title", "Untitled Playlist"),
        "videos": videos,
        "total": len(videos),
    }
