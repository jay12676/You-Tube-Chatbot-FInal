from backend.services import groq_service as gs


def test_build_context_audio_only():
    segs = [{"text": "Hello world", "start": 1.0, "end": 2.0}]
    out = gs._build_context(segs, [], pause_time=10.0)
    assert "[00:01] Hello world" in out
    assert "VISUAL" not in out


def test_build_context_interleaves_visual_chronologically():
    segs = [{"text": "Spoken at 5s", "start": 5.0, "end": 6.0}]
    vis = [{"start": 2.0, "end": 4.0, "label": "slide", "description": "Title slide"}]
    out = gs._build_context(segs, vis, pause_time=10.0)
    lines = out.splitlines()
    # visual at 2s comes before spoken at 5s
    assert lines[0] == '[VISUAL 00:02] slide: Title slide'
    assert lines[1] == '[00:05] Spoken at 5s'


def test_build_context_filters_visual_by_pause_time():
    segs = [{"text": "early", "start": 1.0, "end": 2.0}]
    vis = [{"start": 99.0, "end": 100.0, "label": "slide", "description": "Future slide"}]
    out = gs._build_context(segs, vis, pause_time=10.0)
    assert "Future slide" not in out


def test_summarize_accepts_visual_segments_signature():
    # empty segments path returns the no-content message without calling the API
    assert gs.summarize_transcript([], pause_time=5.0, visual_segments=[]) == \
        "No transcript content found up to this point."


def test_build_context_visual_only_video():
    # no spoken segments, only visuals — context should still have the visual line
    vis = [{"start": 1.0, "end": 3.0, "label": "scene", "description": "Glowing mushrooms"}]
    out = gs._build_context([], vis, pause_time=10.0)
    assert out == '[VISUAL 00:01] scene: Glowing mushrooms'
