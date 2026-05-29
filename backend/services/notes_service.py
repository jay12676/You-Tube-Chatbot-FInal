"""
Notes service: turn a video's transcript + on-screen visuals into a downloadable
PDF study pack — screenshots of the slides/diagrams paired with distilled notes.

Frame extraction (ffmpeg) and screenshots are best-effort: if anything fails the
PDF is still produced as text-only.
"""

import os
import subprocess

# Bundled Unicode font so non-latin transcripts don't crash the PDF.
# backend/services/notes_service.py → project root is three dirs up.
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_FONT_PATH = os.path.join(_ROOT, "assets", "fonts", "DejaVuSans.ttf")

_PURPLE = (124, 58, 237)
_DARK = (30, 30, 30)
_GREY = (90, 90, 90)


def _fmt_ts(seconds: float) -> str:
    """Format seconds as MM:SS or H:MM:SS."""
    s = int(seconds)
    h, m, sec = s // 3600, (s % 3600) // 60, s % 60
    return f"{h}:{m:02d}:{sec:02d}" if h > 0 else f"{m:02d}:{sec:02d}"


def _dedupe_and_cap(timestamps: list, max_frames: int = 40) -> list:
    """
    Sort timestamps, collapse any within 1.0s of the previously kept one, then
    evenly sample down to max_frames if needed.
    """
    kept: list[float] = []
    last = None
    for t in sorted(float(x) for x in timestamps):
        if last is None or t - last >= 1.0:
            kept.append(t)
            last = t
    if len(kept) > max_frames:
        step = len(kept) / max_frames
        kept = [kept[int(i * step)] for i in range(max_frames)]
    return kept


def extract_frames(video_path: str, timestamps: list, out_dir: str, max_frames: int = 40) -> dict:
    """
    Grab one JPG per (deduped/capped) timestamp via ffmpeg.
    Returns {timestamp: jpg_path}. Failures are skipped silently.
    """
    os.makedirs(out_dir, exist_ok=True)
    frames: dict[float, str] = {}
    wanted = _dedupe_and_cap(timestamps, max_frames)
    if len(timestamps) > len(wanted):
        print(f"[Notes] {len(timestamps)} visual moments → {len(wanted)} frames (deduped/capped)")
    for i, t in enumerate(wanted):
        out_path = os.path.join(out_dir, f"frame_{i:03d}.jpg")
        try:
            subprocess.run(
                ["ffmpeg", "-y", "-ss", str(t), "-i", video_path,
                 "-frames:v", "1", "-q:v", "3", out_path],
                capture_output=True, timeout=30,
            )
            if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
                frames[t] = out_path
        except Exception as e:  # noqa: BLE001 - screenshots are best-effort
            print(f"[Notes] frame at {t}s failed: {e}")
    return frames


def _nearest_frame(frames: dict, ts: float, tol: float = 2.5) -> str | None:
    """Return the frame path whose timestamp is closest to ts within tol seconds."""
    if not frames:
        return None
    best_t = min(frames.keys(), key=lambda k: abs(k - ts))
    if abs(best_t - ts) <= tol:
        return frames[best_t]
    return None


def build_study_notes_pdf(notes: dict, frames: dict, video_meta: dict, scope_label: str) -> bytes:
    """
    Build the study-pack PDF and return its bytes.

    notes: {"title": str, "key_takeaways": [str], "sections": [{"timestamp","heading","note"}]}
    frames: {timestamp: jpg_path}
    video_meta: {"title": str, "video_id": str, ...}
    """
    from fpdf import FPDF
    from fpdf.enums import XPos, YPos

    def line(pdf, h, txt):
        # multi_cell that returns the cursor to the left margin on the next line
        pdf.multi_cell(0, h, txt, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf = FPDF()
    pdf.add_font("DejaVu", "", _FONT_PATH)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # ── Cover ──────────────────────────────────────────────────────────────
    pdf.set_font("DejaVu", size=22)
    pdf.set_text_color(*_PURPLE)
    line(pdf, 11, notes.get("title") or video_meta.get("title") or "Study Notes")
    pdf.ln(1)
    pdf.set_font("DejaVu", size=10)
    pdf.set_text_color(*_GREY)
    line(pdf, 6, f"Video: {video_meta.get('title', '')}")
    line(pdf, 6, f"Scope: {scope_label}")
    pdf.ln(4)

    # ── Key Takeaways ──────────────────────────────────────────────────────
    takeaways = notes.get("key_takeaways") or []
    if takeaways:
        pdf.set_font("DejaVu", size=14)
        pdf.set_text_color(*_DARK)
        line(pdf, 9, "Key Takeaways")
        pdf.set_font("DejaVu", size=11)
        pdf.set_text_color(50, 50, 50)
        for k in takeaways:
            line(pdf, 7, f"•  {k}")
        pdf.ln(3)

    # ── Sections (one per visual moment) ───────────────────────────────────
    for sec in notes.get("sections") or []:
        ts = float(sec.get("timestamp", 0.0))
        pdf.set_font("DejaVu", size=13)
        pdf.set_text_color(*_PURPLE)
        line(pdf, 8, f"[{_fmt_ts(ts)}]  {sec.get('heading', '')}")

        img = _nearest_frame(frames, ts)
        if img and os.path.exists(img):
            try:
                pdf.image(img, w=130)
                pdf.ln(2)
            except Exception as e:  # noqa: BLE001 - image embedding is best-effort
                print(f"[Notes] could not embed image {img}: {e}")

        note = sec.get("note") or ""
        if note:
            pdf.set_font("DejaVu", size=11)
            pdf.set_text_color(40, 40, 40)
            line(pdf, 7, note)
        pdf.ln(4)

    return bytes(pdf.output())
