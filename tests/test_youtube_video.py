import backend.services.youtube_service as ys


def test_download_video_uses_clean_url_and_noplaylist(monkeypatch, tmp_path):
    captured = {}

    class FakeYDL:
        def __init__(self, opts):
            captured["opts"] = opts

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def extract_info(self, url, download):
            captured["url"] = url
            # simulate yt-dlp writing the file
            p = tmp_path / "vid123.mp4"
            p.write_bytes(b"fakevideo")
            return {"ext": "mp4"}

    monkeypatch.setattr(ys, "DOWNLOADS_DIR", str(tmp_path))
    monkeypatch.setattr(ys.yt_dlp, "YoutubeDL", FakeYDL)

    path = ys.download_video(
        "https://www.youtube.com/watch?v=vid123&list=RDvid123&start_radio=1", "vid123"
    )

    assert captured["url"] == "https://www.youtube.com/watch?v=vid123"
    assert captured["opts"]["noplaylist"] is True
    assert path.endswith("vid123.mp4")
