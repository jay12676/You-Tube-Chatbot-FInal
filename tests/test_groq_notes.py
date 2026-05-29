import json

from backend.services import groq_service as gs


class _FakeResp:
    def __init__(self, content):
        self.choices = [type("C", (), {"message": type("M", (), {"content": content})})]


def _fake_client(content):
    class _Completions:
        def create(self, **kwargs):
            return _FakeResp(content)

    class _Chat:
        completions = _Completions()

    class _Client:
        chat = _Chat()

    return _Client()


def test_generate_study_notes_parses_json(monkeypatch):
    payload = json.dumps({
        "title": "Neural Networks",
        "key_takeaways": ["Neurons hold activations", "Layers transform inputs"],
        "notes": [
            {"index": 0, "heading": "What is a neuron", "note": "A thing holding a number."},
        ],
    })
    monkeypatch.setattr(gs, "_get_client", lambda: _fake_client(payload))

    segs = [{"text": "a neuron", "start": 10.0, "end": 14.0}]
    vis = [{"start": 12.0, "end": 16.0, "label": "diagram", "description": "neuron grid"}]
    out = gs.generate_study_notes(segs, vis, pause_time=None)

    assert out["title"] == "Neural Networks"
    assert len(out["key_takeaways"]) == 2
    # one section per visual moment, anchored to the REAL timestamp (not model-invented)
    assert len(out["sections"]) == 1
    assert out["sections"][0]["heading"] == "What is a neuron"
    assert out["sections"][0]["timestamp"] == 12.0


def test_generate_study_notes_anchors_all_moments_even_if_model_skips(monkeypatch):
    # model only enriches index 0; section for index 1 must still exist (from visual)
    payload = json.dumps({
        "title": "T",
        "key_takeaways": [],
        "notes": [{"index": 0, "heading": "First", "note": "n0"}],
    })
    monkeypatch.setattr(gs, "_get_client", lambda: _fake_client(payload))
    vis = [
        {"start": 5.0, "end": 6.0, "label": "slide", "description": "Slide A"},
        {"start": 30.0, "end": 31.0, "label": "diagram", "description": "Diagram B"},
    ]
    out = gs.generate_study_notes([], vis, pause_time=None)
    assert [s["timestamp"] for s in out["sections"]] == [5.0, 30.0]
    assert out["sections"][0]["heading"] == "First"
    # index 1 not enriched → falls back to the visual's label/description
    assert out["sections"][1]["heading"] == "Diagram"
    assert out["sections"][1]["note"] == "Diagram B"


def test_generate_study_notes_malformed_falls_back(monkeypatch):
    monkeypatch.setattr(gs, "_get_client", lambda: _fake_client("not json at all"))

    segs = [{"text": "hello", "start": 1.0, "end": 2.0}]
    vis = [{"start": 3.0, "end": 5.0, "label": "slide", "description": "Title slide"}]
    out = gs.generate_study_notes(segs, vis, pause_time=None)

    # graceful fallback: valid structure, sections derived from visuals
    assert isinstance(out["title"], str) and out["title"]
    assert isinstance(out["key_takeaways"], list)
    assert out["sections"][0]["timestamp"] == 3.0
    assert "Title slide" in out["sections"][0]["note"]
