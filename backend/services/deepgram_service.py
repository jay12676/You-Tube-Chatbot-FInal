"""
Deepgram service: transcribe audio using Deepgram REST API directly.
Long audio files are split into parallel chunks for faster turnaround.
"""

import asyncio
import os
import shutil
import subprocess
import tempfile

import httpx
from dotenv import load_dotenv

load_dotenv()

DEEPGRAM_API_URL = "https://api.deepgram.com/v1/listen"
CHUNK_DURATION_SEC = int(os.getenv("DEEPGRAM_CHUNK_DURATION_SEC", "300"))  # seconds per chunk


# ──────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────────────────────

def _get_all_words(result: dict) -> list:
    """Extract word-level data from a Deepgram response."""
    channels = result.get("results", {}).get("channels", [])
    if channels:
        return channels[0].get("alternatives", [{}])[0].get("words", [])
    return []


def _build_segments_from_words(words: list, group_size: int = 8) -> list:
    """Group word dicts into text segments."""
    segments = []
    chunk_text: list[str] = []
    chunk_start = 0.0
    for i, w in enumerate(words):
        if not chunk_text:
            chunk_start = w.get("start", 0.0)
        chunk_text.append(w.get("punctuated_word", w.get("word", "")))
        if len(chunk_text) >= group_size or i == len(words) - 1:
            segments.append({
                "text": " ".join(chunk_text),
                "start": chunk_start,
                "end": w.get("end", 0.0),
            })
            chunk_text = []
    return segments


def _find_orphan_words(all_words: list, segments: list) -> list:
    """
    Return words whose time range isn't covered by any existing segment.
    Captures speech mixed with music that Deepgram detected word-level
    but didn't group into utterances.
    """
    if not all_words or not segments:
        return []
    orphans = []
    for w in all_words:
        w_start = w.get("start", 0.0)
        w_end = w.get("end", 0.0)
        covered = any(
            w_start >= seg["start"] - 0.1 and w_end <= seg["end"] + 0.1
            for seg in segments
        )
        if not covered:
            orphans.append(w)
    return orphans


def _parse_deepgram_result(result: dict) -> dict:
    """
    Parse a raw Deepgram API response into clean segments / words.
    All timestamps are relative to the start of the submitted audio chunk
    (caller applies any absolute offset before merging).
    """
    segments: list[dict] = []
    full_text = ""
    detected_language = "en"

    # Full transcript text + language
    if "results" in result and "channels" in result["results"]:
        channels = result["results"]["channels"]
        if channels:
            alt = channels[0].get("alternatives", [{}])[0]
            full_text = alt.get("transcript", "")
            dl = channels[0].get("detected_language")
            if dl:
                detected_language = dl

    # Prefer utterances (sentence-level with timestamps)
    if "results" in result and "utterances" in result["results"]:
        for utt in result["results"]["utterances"]:
            segments.append({
                "text": utt.get("transcript", ""),
                "start": utt.get("start", 0.0),
                "end": utt.get("end", 0.0),
            })

    all_words = _get_all_words(result)

    # Recover orphan words from gaps (speech mixed with music, etc.)
    if segments and all_words:
        orphans = _find_orphan_words(all_words, segments)
        if orphans:
            extra = _build_segments_from_words(orphans, group_size=6)
            print(f"[Deepgram] Recovered {len(orphans)} orphan words → {len(extra)} extra segments")
            segments.extend(extra)
            segments.sort(key=lambda s: s["start"])

    # Fallback: paragraphs → sentences
    if not segments and "results" in result:
        for ch in result["results"].get("channels", []):
            alt = ch.get("alternatives", [{}])[0]
            paragraphs_data = alt.get("paragraphs", {})
            if paragraphs_data and "paragraphs" in paragraphs_data:
                for para in paragraphs_data["paragraphs"]:
                    for sentence in para.get("sentences", []):
                        segments.append({
                            "text": sentence.get("text", ""),
                            "start": sentence.get("start", 0.0),
                            "end": sentence.get("end", 0.0),
                        })

    # Last fallback: words grouped into chunks
    if not segments and all_words:
        segments = _build_segments_from_words(all_words, group_size=10)

    if not full_text and segments:
        full_text = " ".join(s["text"] for s in segments)

    words = [
        {
            "word": w.get("punctuated_word", w.get("word", "")),
            "start": w.get("start", 0.0),
            "end": w.get("end", 0.0),
        }
        for w in all_words
        if w.get("word", "").strip()
    ]

    return {
        "segments": segments,
        "words": words,
        "full_text": full_text,
        "detected_language": detected_language,
    }


def _get_audio_duration(audio_path: str) -> float:
    """Return duration of an audio file in seconds via ffprobe."""
    try:
        r = subprocess.run(
            [
                "ffprobe", "-v", "quiet",
                "-show_entries", "format=duration",
                "-of", "csv=p=0",
                audio_path,
            ],
            capture_output=True, text=True, timeout=30,
        )
        return float(r.stdout.strip())
    except Exception as e:
        print(f"[Deepgram] ffprobe failed ({e}); will transcribe as single file")
        return 0.0


def _split_audio(audio_path: str, chunk_sec: int) -> tuple[list, str | None]:
    """
    Split audio into chunks of chunk_sec seconds using ffmpeg.

    Returns:
        chunks   – list of (chunk_path, offset_sec)
        temp_dir – directory to clean up afterwards (None if not split)
    """
    duration = _get_audio_duration(audio_path)
    if duration == 0 or duration <= chunk_sec:
        return [(audio_path, 0.0)], None

    temp_dir = tempfile.mkdtemp(prefix="dg_chunks_")
    ext = os.path.splitext(audio_path)[1] or ".mp3"
    chunks: list[tuple[str, float]] = []
    offset = 0.0
    idx = 0

    while offset < duration:
        cpath = os.path.join(temp_dir, f"chunk_{idx:03d}{ext}")
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", audio_path,
                "-ss", str(offset),
                "-t", str(chunk_sec),
                "-acodec", "copy",
                cpath,
            ],
            capture_output=True, timeout=120,
        )
        if os.path.exists(cpath) and os.path.getsize(cpath) > 1024:
            chunks.append((cpath, offset))
        offset += chunk_sec
        idx += 1

    print(f"[Deepgram] Split {duration:.0f}s audio → {len(chunks)} chunks of ≤{chunk_sec}s")
    return chunks, temp_dir


# ──────────────────────────────────────────────────────────────────────────────
# Core async transcription
# ──────────────────────────────────────────────────────────────────────────────

_DEEPGRAM_PARAMS = {
    "model": os.getenv("DEEPGRAM_MODEL", "nova-2"),
    "smart_format": "true",
    "utterances": "true",
    "detect_language": "true",
    "paragraphs": "true",
    "punctuate": "true",
    "filler_words": "true",
    "diarize": "true",
}


async def _transcribe_single_file(audio_path: str, api_key: str, label: str = "") -> dict:
    """Send one audio file to Deepgram and return parsed result (no offset applied)."""
    headers = {
        "Authorization": f"Token {api_key}",
        "Content-Type": "audio/*",
    }

    with open(audio_path, "rb") as f:
        audio_data = f.read()

    size_mb = len(audio_data) / (1024 * 1024)
    tag = f" [{label}]" if label else ""
    print(f"[Deepgram]{tag} Sending {size_mb:.1f} MB …")

    async with httpx.AsyncClient(timeout=600.0) as client:
        response = await client.post(
            DEEPGRAM_API_URL,
            headers=headers,
            params=_DEEPGRAM_PARAMS,
            content=audio_data,
        )
        response.raise_for_status()
        return _parse_deepgram_result(response.json())


async def transcribe_audio(audio_path: str) -> dict:
    """
    Transcribe an audio file with Deepgram.

    For audio longer than CHUNK_DURATION_SEC (5 min), the file is split into
    parallel chunks that are all sent to Deepgram simultaneously, then the
    results are merged with corrected timestamps.  This gives a near-linear
    speedup: a 30-minute video becomes ~6 parallel 5-minute requests.

    Returns:
        {
            "segments": [{"text": str, "start": float, "end": float}, ...],
            "words":    [{"word": str, "start": float, "end": float}, ...],
            "full_text": str,
            "detected_language": str,
        }
    """
    api_key = os.getenv("DEEPGRAM_API_KEY")
    if not api_key:
        raise ValueError("DEEPGRAM_API_KEY not found in environment variables")

    file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
    print(f"[Deepgram] Input: {os.path.basename(audio_path)} ({file_size_mb:.1f} MB)")

    chunks, temp_dir = _split_audio(audio_path, CHUNK_DURATION_SEC)

    if len(chunks) == 1:
        # Short file — no chunking needed
        result = await _transcribe_single_file(audio_path, api_key)
        print(
            f"[Deepgram] Done: {len(result['segments'])} segments, "
            f"{len(result['words'])} words, lang={result['detected_language']}"
        )
        return result

    # ── Parallel chunk transcription ──────────────────────────────────────────
    print(f"[Deepgram] Transcribing {len(chunks)} chunks in parallel …")
    tasks = [
        _transcribe_single_file(cpath, api_key, label=f"chunk {i+1}/{len(chunks)}")
        for i, (cpath, _) in enumerate(chunks)
    ]
    chunk_results = await asyncio.gather(*tasks)

    # ── Merge with timestamp offsets ──────────────────────────────────────────
    merged_segments: list[dict] = []
    merged_words: list[dict] = []
    merged_texts: list[str] = []
    detected_language = "en"

    for (_, offset), res in zip(chunks, chunk_results):
        for seg in res["segments"]:
            merged_segments.append({
                "text": seg["text"],
                "start": seg["start"] + offset,
                "end": seg["end"] + offset,
            })
        for w in res["words"]:
            merged_words.append({
                "word": w["word"],
                "start": w["start"] + offset,
                "end": w["end"] + offset,
            })
        if res["full_text"]:
            merged_texts.append(res["full_text"])
        if res["detected_language"] not in ("en", ""):
            detected_language = res["detected_language"]

    merged_segments.sort(key=lambda s: s["start"])
    merged_words.sort(key=lambda w: w["start"])
    full_text = " ".join(merged_texts)

    # Clean up temp chunk files
    if temp_dir:
        try:
            shutil.rmtree(temp_dir)
        except Exception:
            pass

    print(
        f"[Deepgram] Merged: {len(merged_segments)} segments, "
        f"{len(merged_words)} words, lang={detected_language}"
    )
    return {
        "segments": merged_segments,
        "words": merged_words,
        "full_text": full_text,
        "detected_language": detected_language,
    }
