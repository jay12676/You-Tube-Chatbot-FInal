"""
Deepgram service: transcribe audio using Deepgram REST API directly.
No SDK needed — uses httpx for HTTP calls.
"""

import os
import httpx
from dotenv import load_dotenv

load_dotenv()

DEEPGRAM_API_URL = "https://api.deepgram.com/v1/listen"


def _get_all_words(result: dict) -> list:
    """Extract the word-level data from Deepgram response."""
    channels = result.get("results", {}).get("channels", [])
    if channels:
        return channels[0].get("alternatives", [{}])[0].get("words", [])
    return []


def _build_segments_from_words(words: list, group_size: int = 8) -> list:
    """Group a list of word dicts into text segments."""
    segments = []
    chunk_text = []
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
    Find words that fall in time gaps NOT covered by any existing segment.
    This captures speech mixed with music or intro words that Deepgram
    detected at word-level but didn't group into utterances.
    """
    if not all_words or not segments:
        return []

    orphan_words = []
    for w in all_words:
        w_start = w.get("start", 0.0)
        w_end = w.get("end", 0.0)
        # Check if this word falls inside any existing segment
        covered = False
        for seg in segments:
            # Word is covered if it overlaps with a segment
            if w_start >= seg["start"] - 0.1 and w_end <= seg["end"] + 0.1:
                covered = True
                break
        if not covered:
            orphan_words.append(w)

    return orphan_words


async def transcribe_audio(audio_path: str) -> dict:
    """
    Send audio file to Deepgram pre-recorded API and return
    timestamped transcript segments.
    
    Returns:
        {
            "segments": [{"text": str, "start": float, "end": float}, ...],
            "full_text": str,
            "detected_language": str
        }
    """
    api_key = os.getenv("DEEPGRAM_API_KEY")
    if not api_key:
        raise ValueError("DEEPGRAM_API_KEY not found in environment variables")

    headers = {
        "Authorization": f"Token {api_key}",
        "Content-Type": "audio/*",
    }

    params = {
        "model": "nova-2",
        "smart_format": "true",
        "utterances": "true",
        "detect_language": "true",
        "paragraphs": "true",
        "punctuate": "true",
        "filler_words": "true",     # capture filler words (um, uh, etc.)
        "diarize": "true",          # better speaker detection in noisy audio
    }

    # Read audio file
    with open(audio_path, "rb") as f:
        audio_data = f.read()

    file_size_mb = len(audio_data) / (1024 * 1024)
    print(f"[Deepgram] Sending audio file: {audio_path} ({file_size_mb:.1f} MB)")

    # Send to Deepgram (long timeout for large files)
    async with httpx.AsyncClient(timeout=600.0) as client:
        response = await client.post(
            DEEPGRAM_API_URL,
            headers=headers,
            params=params,
            content=audio_data,
        )
        response.raise_for_status()
        result = response.json()

    # Parse the response into clean segments
    segments = []
    full_text = ""
    detected_language = "en"

    # Try to get detected language
    if "results" in result and "channels" in result["results"]:
        channels = result["results"]["channels"]
        if channels:
            alt = channels[0].get("alternatives", [{}])[0]
            full_text = alt.get("transcript", "")

            # Get detected language
            dl = channels[0].get("detected_language")
            if dl:
                detected_language = dl

    # Prefer utterances (sentence-level with timestamps)
    if "results" in result and "utterances" in result["results"]:
        utterances = result["results"]["utterances"]
        if utterances:
            for utt in utterances:
                segments.append({
                    "text": utt.get("transcript", ""),
                    "start": utt.get("start", 0.0),
                    "end": utt.get("end", 0.0),
                })

    # Always extract word-level timestamps (used for word-by-word display and gap recovery)
    all_words = _get_all_words(result)

    # ── Rescue orphan words from gaps (e.g. speech mixed with music) ──
    # Deepgram may detect individual words but not group them into
    # utterances when there's loud background music. This step finds
    # those words and creates extra segments so nothing is lost.
    if segments and all_words:
        orphans = _find_orphan_words(all_words, segments)
        if orphans:
            extra_segments = _build_segments_from_words(orphans, group_size=6)
            print(f"[Deepgram] Recovered {len(orphans)} orphan words → {len(extra_segments)} extra segments")
            segments.extend(extra_segments)
            # Sort all segments by start time
            segments.sort(key=lambda s: s["start"])

    # Fallback: use paragraphs → sentences
    if not segments and "results" in result:
        channels = result["results"].get("channels", [])
        if channels:
            alt = channels[0].get("alternatives", [{}])[0]
            paragraphs_data = alt.get("paragraphs", {})
            if paragraphs_data and "paragraphs" in paragraphs_data:
                for para in paragraphs_data["paragraphs"]:
                    for sentence in para.get("sentences", []):
                        segments.append({
                            "text": sentence.get("text", ""),
                            "start": sentence.get("start", 0.0),
                            "end": sentence.get("end", 0.0),
                        })

    # Last fallback: use words grouped into chunks
    if not segments and all_words:
        segments = _build_segments_from_words(all_words, group_size=10)

    # Build full text from segments if not already set
    if not full_text and segments:
        full_text = " ".join(s["text"] for s in segments)

    # Build clean word list for word-by-word frontend display
    words = [
        {
            "word": w.get("punctuated_word", w.get("word", "")),
            "start": w.get("start", 0.0),
            "end": w.get("end", 0.0),
        }
        for w in all_words
        if w.get("word", "").strip()
    ]

    print(f"[Deepgram] Transcription complete: {len(segments)} segments, {len(words)} words, language={detected_language}")

    return {
        "segments": segments,
        "words": words,
        "full_text": full_text,
        "detected_language": detected_language,
    }
