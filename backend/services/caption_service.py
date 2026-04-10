"""
YouTube Caption Service: fetch YouTube's own captions as the primary transcript source.
Falls back gracefully when captions are unavailable.

Why: YouTube's auto-generated captions cover every spoken word with timestamps,
including words Deepgram misses due to background music or low-confidence detections.
"""

from youtube_transcript_api import YouTubeTranscriptApi


# Language codes to try, in priority order.
# This list covers most videos — add more codes here as needed.
_LANGUAGE_PRIORITY = [
    "hi", "en", "hi-IN", "en-IN", "en-US", "en-GB",
    "ta", "te", "kn", "ml", "mr", "bn", "gu", "pa",
    "fr", "de", "es", "pt", "ru", "ja", "ko", "zh", "ar",
]


def get_youtube_captions(video_id: str) -> dict | None:
    """
    Fetch YouTube captions for the given video ID.

    Tries manual captions first, then auto-generated ones, across a wide list
    of language codes so it works for any video language.

    Returns:
        {
            "segments": [{"text": str, "start": float, "end": float}, ...],
            "words": [],          # YouTube captions are phrase-level; frontend interpolates
            "full_text": str,
            "detected_language": str,
        }
        or None if no captions are available at all.
    """
    api = YouTubeTranscriptApi()

    # 1. Get the list of available transcripts for this video
    try:
        transcript_list = api.list(video_id)
    except Exception as e:
        print(f"[Captions] Could not list transcripts for {video_id}: {e}")
        return None

    # 2. Collect all available language codes (manual first, then generated)
    manual_codes = []
    generated_codes = []
    for t in transcript_list:
        if t.is_generated:
            generated_codes.append(t.language_code)
        else:
            manual_codes.append(t.language_code)

    print(f"[Captions] Manual: {manual_codes} | Auto-generated: {generated_codes}")

    # 3. Build priority fetch order: manual codes first, then generated
    fetch_order = manual_codes + generated_codes
    if not fetch_order:
        print(f"[Captions] No captions available for {video_id}")
        return None

    # 4. Fetch using the best available language
    try:
        entries = api.fetch(video_id, languages=fetch_order)
        detected_language = fetch_order[0]
    except Exception as e:
        print(f"[Captions] Fetch failed: {e}")
        return None

    if not entries:
        print(f"[Captions] Empty transcript returned for {video_id}")
        return None

    # 5. Convert to our standard segment format
    segments = []
    for entry in entries:
        text = entry.text.strip()
        if not text:
            continue
        start = float(entry.start)
        duration = float(entry.duration) if entry.duration else 1.0
        segments.append({
            "text": text,
            "start": start,
            "end": round(start + duration, 3),
        })

    if not segments:
        return None

    full_text = " ".join(s["text"] for s in segments)
    print(f"[Captions] Got {len(segments)} caption segments, language={detected_language}")

    return {
        "segments": segments,
        "words": [],          # frontend JS interpolates word timing from segments
        "full_text": full_text,
        "detected_language": detected_language,
    }
