from backend.services import vision_service as vs


def test_ts_to_seconds_mm_ss():
    assert vs._ts_to_seconds("02:30") == 150.0


def test_ts_to_seconds_hh_mm_ss():
    assert vs._ts_to_seconds("1:02:03") == 3723.0


def test_ts_to_seconds_invalid_returns_none():
    assert vs._ts_to_seconds("banana") is None
    assert vs._ts_to_seconds("") is None


def test_parse_visual_response_plain_json():
    raw = '''[
      {"timestamp": "00:10", "end": "00:20", "label": "slide", "description": "Title slide"},
      {"timestamp": "00:05", "end": "00:09", "label": "text", "description": "Intro text"}
    ]'''
    out = vs._parse_visual_response(raw)
    assert len(out) == 2
    # sorted by start
    assert out[0]["start"] == 5.0
    assert out[1]["start"] == 10.0
    assert out[1]["end"] == 20.0
    assert out[0]["label"] == "text"
    assert out[0]["description"] == "Intro text"


def test_parse_visual_response_strips_markdown_fence():
    raw = '```json\n[{"timestamp":"00:01","end":"00:02","label":"diagram","description":"A flowchart"}]\n```'
    out = vs._parse_visual_response(raw)
    assert len(out) == 1
    assert out[0]["label"] == "diagram"


def test_parse_visual_response_drops_malformed_rows():
    raw = '''[
      {"timestamp": "00:10", "label": "slide", "description": "Good row"},
      {"label": "slide", "description": "No timestamp - dropped"},
      "not an object"
    ]'''
    out = vs._parse_visual_response(raw)
    assert len(out) == 1
    assert out[0]["description"] == "Good row"
    # missing end defaults to start
    assert out[0]["end"] == out[0]["start"]


def test_parse_visual_response_garbage_returns_empty():
    assert vs._parse_visual_response("I could not analyze this video.") == []
