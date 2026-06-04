"""
Tests for caption_service language selection.

The key scenario (real-world, reproduced from a BB Ki Vines video): a Hindi
video carries TWO tracks both labelled "hi" — a MANUAL track whose text is
actually English (a mislabelled translation) and the AUTO-generated genuine
Hindi track. We must return the real Hindi, not the mislabelled English.
"""

import backend.services.caption_service as cs


# ----- fakes that mimic youtube_transcript_api -----

class FakeSnippet:
    def __init__(self, text, start=0.0, duration=1.0):
        self.text = text
        self.start = start
        self.duration = duration


class FakeTranscript:
    def __init__(self, code, is_generated, lines):
        self.language_code = code
        self.language = code
        self.is_generated = is_generated
        self._lines = lines

    def fetch(self):
        return [FakeSnippet(t, i * 1.0, 1.0) for i, t in enumerate(self._lines)]


class FakeApi:
    def __init__(self, tracks):
        self._tracks = tracks

    def list(self, video_id):
        return list(self._tracks)

    def fetch(self, video_id, languages=None):
        # last-resort: mimic library "manual-first by language code" pick
        for code in (languages or []):
            for t in self._tracks:
                if t.language_code == code and not t.is_generated:
                    return t.fetch()
            for t in self._tracks:
                if t.language_code == code:
                    return t.fetch()
        raise Exception("no transcript")


def _patch(monkeypatch, tracks):
    monkeypatch.setattr(cs, "YouTubeTranscriptApi", lambda: FakeApi(tracks))


# ----- _script_matches -----

def test_script_matches_accepts_native_hindi():
    assert cs._script_matches("यह क्या है बिल बहुत ज़्यादा है", "hi") is True


def test_script_matches_rejects_english_labelled_hindi():
    assert cs._script_matches("What is this? Bill is too much.", "hi") is False


def test_script_matches_accepts_english_under_en():
    # Latin-script language → we cannot validate by script, so accept.
    assert cs._script_matches("What is this? Hello everyone.", "en") is True


# ----- selection -----

def test_mislabelled_hindi_manual_falls_through_to_auto(monkeypatch):
    tracks = [
        FakeTranscript("hi", False, ["What is this?", "Bill...", "Too much"]),   # English (mislabelled)
        FakeTranscript("hi", True, ["यह क्या है?", "बिल...", "बहुत ज़्यादा"]),      # genuine Hindi
    ]
    _patch(monkeypatch, tracks)

    result = cs.get_youtube_captions("vid")

    assert result is not None
    assert result["detected_language"] == "hi"
    # must be the genuine Hindi, NOT the mislabelled English
    assert "यह क्या है?" in result["full_text"]
    assert "What is this?" not in result["full_text"]


def test_correct_manual_english_is_used(monkeypatch):
    # No regression: a real English video keeps using its manual English track.
    tracks = [
        FakeTranscript("en", False, ["Hello everyone", "Welcome to the talk"]),
        FakeTranscript("en", True, ["hello everyone", "welcome to the talk"]),
    ]
    _patch(monkeypatch, tracks)

    result = cs.get_youtube_captions("vid")

    assert result is not None
    assert result["detected_language"] == "en"
    assert "Hello everyone" in result["full_text"]


def test_german_video_returns_german_not_english(monkeypatch):
    # German video with English + other translations present. The original
    # (auto-generated) German must win over the English translation track.
    tracks = [
        FakeTranscript("en", False, ["Hello, welcome"]),            # English translation
        FakeTranscript("de", False, ["Hallo, willkommen zum Video"]),  # German (original)
        FakeTranscript("de", True, ["hallo willkommen zum video"]),    # German auto
    ]
    _patch(monkeypatch, tracks)

    result = cs.get_youtube_captions("vid")

    assert result["detected_language"] == "de"
    assert "Hallo, willkommen zum Video" in result["full_text"]


def test_no_autotrack_prefers_videos_own_track_over_global_priority(monkeypatch):
    # French video with NO auto-generated track, only manual French + English.
    # Old code biased to the global hi/en list and would pick English; now we
    # stay within the video's own tracks (French listed first by YouTube).
    tracks = [
        FakeTranscript("fr", False, ["Bonjour tout le monde"]),  # French (original, listed first)
        FakeTranscript("en", False, ["Hello everyone"]),         # English translation
    ]
    _patch(monkeypatch, tracks)

    result = cs.get_youtube_captions("vid")

    assert result["detected_language"] == "fr"
    assert "Bonjour tout le monde" in result["full_text"]
