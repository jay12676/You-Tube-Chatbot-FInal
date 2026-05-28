from fastapi.testclient import TestClient
import backend.main as main

client = TestClient(main.app)


def test_transcribe_includes_visual_segments(monkeypatch):
    monkeypatch.setattr(main, "extract_video_info", lambda url: {
        "id": "vid123", "title": "T", "duration": 100, "thumbnail": "x",
    })
    monkeypatch.setattr(main, "get_youtube_captions", lambda vid: {
        "segments": [{"text": "hi", "start": 0.0, "end": 1.0}],
        "words": [], "full_text": "hi", "detected_language": "en",
    })

    async def fake_vision(url, duration):
        return [{"start": 2.0, "end": 4.0, "label": "slide", "description": "Intro"}]

    monkeypatch.setattr(main, "analyze_video_visuals", fake_vision)

    r = client.post("/api/transcribe", json={"url": "https://youtu.be/vid123"})
    assert r.status_code == 200
    body = r.json()
    assert body["visual_segments"] == [
        {"start": 2.0, "end": 4.0, "label": "slide", "description": "Intro"}
    ]


def test_summarize_accepts_visual_segments(monkeypatch):
    monkeypatch.setattr(main, "summarize_transcript",
                        lambda segments, pause_time, visual_segments=None: "SUMMARY")
    r = client.post("/api/summarize", json={
        "segments": [{"text": "a", "start": 0.0, "end": 1.0}],
        "pause_time": 5.0,
        "visual_segments": [{"start": 1.0, "end": 2.0, "label": "slide", "description": "d"}],
    })
    assert r.status_code == 200
    assert r.json()["summary"] == "SUMMARY"


def test_chat_accepts_visual_segments(monkeypatch):
    monkeypatch.setattr(main, "chat_with_context",
                        lambda **kwargs: "ANSWER")
    r = client.post("/api/chat", json={
        "question": "what?",
        "segments": [{"text": "a", "start": 0.0, "end": 1.0}],
        "pause_time": 5.0,
        "chat_history": [],
        "visual_segments": [{"start": 1.0, "end": 2.0, "label": "slide", "description": "d"}],
    })
    assert r.status_code == 200
    assert r.json()["answer"] == "ANSWER"
