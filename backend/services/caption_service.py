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


# Languages whose native script is NON-Latin. If a caption track is labelled
# with one of these codes but its text is mostly Latin characters, the track is
# almost certainly a mislabelled translation (e.g. English subtitles uploaded
# under the "hi" Hindi code) rather than the real original-language track.
_NON_LATIN_LANGS = {
    "hi", "ta", "te", "kn", "ml", "mr", "bn", "gu", "pa",
    "ru", "ja", "ko", "zh", "ar", "fa", "ur", "th", "he", "el",
}


def _script_matches(text: str, lang_code: str) -> bool:
    """
    Heuristic: does a caption track's TEXT actually match its declared language
    CODE, by script?

    YouTube lets uploaders mislabel a track's language — most commonly English
    subtitles uploaded under the original-language code, so asking for "hi" can
    return English text. For non-Latin-script languages we can detect this
    cheaply: genuine Hindi/Tamil/Arabic/… text is mostly non-ASCII letters,
    whereas a mislabelled English track is almost all ASCII. For Latin-script
    languages we cannot tell them apart this way, so we accept (return True).
    """
    base = lang_code.split("-")[0].lower()
    if base not in _NON_LATIN_LANGS:
        return True
    letters = [c for c in text[:1000] if c.isalpha()]
    if not letters:
        return True
    native = sum(1 for c in letters if ord(c) > 0x7F)
    return native / len(letters) >= 0.3


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

    # 2. Collect available language codes (manual vs auto-generated)
    manual_codes = []
    generated_codes = []
    for t in transcript_list:
        if t.is_generated:
            generated_codes.append(t.language_code)
        else:
            manual_codes.append(t.language_code)

    print(f"[Captions] Manual: {manual_codes} | Auto-generated: {generated_codes}")

    # 3. Build the fetch order so the transcript is ALWAYS in the video's own
    #    spoken language — English video → English, German → German, etc.
    #
    #    The AUTO-GENERATED track is YouTube's speech-recognition of the actual
    #    audio, so its language code IS the original spoken language. We treat it
    #    as authoritative and fetch it first. Community-translated MANUAL tracks
    #    (often dozens per popular video) must never override it — so after the
    #    original language we prefer the video's OWN remaining tracks, and only
    #    fall back to a global language list as an absolute last resort (reached
    #    only when none of this video's tracks were usable).
    original_lang = generated_codes[0] if generated_codes else None

    fetch_order: list[str] = []
    if original_lang:
        fetch_order.append(original_lang)
    # This video's own tracks next (auto-generated first — they're original
    # language; manual tracks are usually translations).
    for code in generated_codes + manual_codes:
        if code not in fetch_order:
            fetch_order.append(code)
    # Global fallback list — last resort only.
    for code in _LANGUAGE_PRIORITY:
        if code not in fetch_order:
            fetch_order.append(code)

    if not fetch_order:
        print(f"[Captions] No captions available for {video_id}")
        return None

    # 4. Index the available tracks so we can pick a SPECIFIC variant (manual
    #    vs auto-generated) per language and VALIDATE its text before trusting
    #    the label. The plain api.fetch(languages=...) can't do this: it prefers
    #    a manual track over the generated one for the same code, which on this
    #    kind of video returns a mislabelled English track sitting under "hi".
    by_code: dict[str, dict] = {}
    for t in transcript_list:
        slot = by_code.setdefault(t.language_code, {})
        slot["gen" if t.is_generated else "man"] = t

    entries = None
    detected_language = None
    for code in fetch_order:
        bucket = by_code.get(code)
        if not bucket:
            continue
        # Manual first (usually higher quality), then auto-generated — but only
        # accept a track whose text's SCRIPT matches the language code, so a
        # mislabelled translation (English under "hi") is skipped in favour of
        # the genuine auto-generated original-language track.
        for variant in ("man", "gen"):
            t = bucket.get(variant)
            if t is None:
                continue
            try:
                fetched = list(t.fetch())
            except Exception as e:
                print(f"[Captions] fetch {code}/{variant} failed: {e}")
                continue
            sample = " ".join(getattr(s, "text", "") for s in fetched[:40])
            if not _script_matches(sample, code):
                print(f"[Captions] {code}/{variant} looks mislabelled "
                      f"(script != {code}) — skipping")
                continue
            entries = fetched
            detected_language = t.language_code
            break
        if entries is not None:
            break

    # 4b. Last resort: if every candidate failed the script check (e.g. the only
    #     track really is a mislabelled one), accept the library's default pick
    #     so the user still gets *something* rather than no transcript at all.
    if entries is None:
        try:
            fetched = api.fetch(video_id, languages=fetch_order)
            entries = list(fetched)
            detected_language = (getattr(fetched, "language_code", None)
                                 or original_lang or fetch_order[0])
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
