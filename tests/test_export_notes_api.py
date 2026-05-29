from fastapi.testclient import TestClient
import backend.main as main

client = TestClient(main.app)


def test_export_notes_returns_pdf(monkeypatch):
    monkeypatch.setattr(main, "extract_video_info", lambda url: {
        "id": "vid123", "title": "T", "duration": 100, "thumbnail": "x",
    })
    monkeypatch.setattr(main, "download_video", lambda url, vid: "fake.mp4")
    monkeypatch.setattr(main, "extract_frames", lambda video, ts, out_dir, max_frames=40: {})
    monkeypatch.setattr(main, "generate_study_notes", lambda segments, visual_segments, pause_time=None: {
        "title": "Notes", "key_takeaways": ["k"], "sections": [],
    })
    monkeypatch.setattr(main, "build_study_notes_pdf",
                        lambda notes, frames, meta, scope: b"%PDF-1.4 fake")

    r = client.post("/api/export_notes", json={
        "url": "https://youtu.be/vid123",
        "segments": [{"text": "a", "start": 0.0, "end": 1.0}],
        "visual_segments": [{"start": 2.0, "end": 4.0, "label": "slide", "description": "d"}],
        "scope": "full",
        "pause_time": 0.0,
    })
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content.startswith(b"%PDF")


def test_export_notes_degrades_when_video_download_fails(monkeypatch):
    monkeypatch.setattr(main, "extract_video_info", lambda url: {
        "id": "vid123", "title": "T", "duration": 100, "thumbnail": "x",
    })

    def boom(url, vid):
        raise RuntimeError("download blocked")

    monkeypatch.setattr(main, "download_video", boom)
    monkeypatch.setattr(main, "generate_study_notes", lambda segments, visual_segments, pause_time=None: {
        "title": "Notes", "key_takeaways": [], "sections": [],
    })
    monkeypatch.setattr(main, "build_study_notes_pdf",
                        lambda notes, frames, meta, scope: b"%PDF-1.4 fake")

    r = client.post("/api/export_notes", json={
        "url": "https://youtu.be/vid123",
        "segments": [],
        "visual_segments": [{"start": 2.0, "end": 4.0, "label": "slide", "description": "d"}],
        "scope": "full",
        "pause_time": 0.0,
    })
    # screenshots are best-effort → still returns a PDF
    assert r.status_code == 200
    assert r.content.startswith(b"%PDF")
