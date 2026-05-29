import base64
import os

from backend.services import notes_service as ns

# 1x1 px PNG
_PNG_1x1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)


def test_dedupe_and_cap_collapses_close_timestamps():
    out = ns._dedupe_and_cap([0.0, 0.5, 1.2, 1.4, 3.0], max_frames=40)
    # 0.5 collapsed into 0.0; 1.4 collapsed into 1.2
    assert out == [0.0, 1.2, 3.0]


def test_dedupe_and_cap_caps_count():
    out = ns._dedupe_and_cap([float(i) for i in range(100)], max_frames=10)
    assert len(out) == 10
    assert out[0] == 0.0


def test_build_pdf_text_only_returns_pdf_bytes():
    notes = {
        "title": "Sample Notes",
        "key_takeaways": ["First point", "Second point — café"],
        "sections": [{"timestamp": 12.0, "heading": "Intro", "note": "An overview."}],
    }
    out = ns.build_study_notes_pdf(notes, {}, {"title": "Vid", "video_id": "x"}, "Whole video")
    assert isinstance(out, (bytes, bytearray))
    assert bytes(out[:4]) == b"%PDF"


def test_build_pdf_embeds_nearest_frame(tmp_path):
    img = tmp_path / "f.png"
    img.write_bytes(_PNG_1x1)
    notes = {
        "title": "With Image",
        "key_takeaways": [],
        "sections": [{"timestamp": 10.0, "heading": "Slide", "note": "A slide."}],
    }
    # frame keyed slightly off the section timestamp — nearest match should still embed it
    frames = {10.3: str(img)}
    out = ns.build_study_notes_pdf(notes, frames, {"title": "Vid", "video_id": "x"}, "Up to 0:30")
    assert bytes(out[:4]) == b"%PDF"


def test_extract_frames_keys_by_timestamp(monkeypatch, tmp_path):
    def fake_run(cmd, **kwargs):
        # cmd[-1] is the output path; create a dummy file
        out_path = cmd[-1]
        with open(out_path, "wb") as f:
            f.write(_PNG_1x1)
        class R: pass
        return R()

    monkeypatch.setattr(ns.subprocess, "run", fake_run)
    frames = ns.extract_frames("fake.mp4", [5.0, 5.3, 20.0], str(tmp_path), max_frames=40)
    # 5.3 collapses into 5.0 → two distinct frames
    assert sorted(frames.keys()) == [5.0, 20.0]
    for p in frames.values():
        assert os.path.exists(p)
