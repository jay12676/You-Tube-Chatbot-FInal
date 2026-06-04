"""
Generator for "explanation of you tube chatbot.pdf".

A tutor-style, beginner-to-advanced walkthrough of the whole project: the
architecture, every service, the end-to-end flows, the latency/performance
story, how audio becomes text and visuals become a timeline, the tests, the run
commands, and an interview Q&A that doubles as the "challenges we solved" log.

Run:  venv\\Scripts\\python scripts/build_explanation_pdf.py
Output: ./explanation of you tube chatbot.pdf  (repo root)

Rendering notes:
- Uses the bundled Unicode font (assets/fonts/DejaVuSans.ttf) so bullets (•),
  arrows (→) and em-dashes (—) render correctly. Real bold isn't bundled, so
  headings use larger size + the brand purple for hierarchy.
- Code blocks use Courier (ASCII only) for a monospace feel.
"""

import os
from fpdf import FPDF
from fpdf.enums import XPos, YPos

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT = os.path.join(ROOT, "assets", "fonts", "DejaVuSans.ttf")
OUT = os.path.join(ROOT, "explanation of you tube chatbot.pdf")

PURPLE = (124, 92, 246)
DARK = (30, 30, 40)
GREY = (90, 96, 110)
CODE_BG = (244, 244, 248)


class Doc(FPDF):
    def header(self):
        # No running header on the cover page.
        if self.page_no() == 1:
            return
        self.set_font("Deja", "", 8)
        self.set_text_color(*GREY)
        self.cell(0, 6, f"Explanation of YouTube Chatbot", align="L")
        self.cell(0, 6, f"Page {self.page_no()}", align="R",
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_draw_color(220, 220, 228)
        self.line(self.l_margin, self.get_y() + 1, self.w - self.r_margin, self.get_y() + 1)
        self.ln(4)


def new_doc() -> Doc:
    pdf = Doc(format="A4")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.set_margins(18, 16, 18)
    pdf.add_font("Deja", "", FONT)
    pdf.add_font("Deja", "B", FONT)  # no bold TTF bundled → reuse regular
    return pdf


def h1(pdf, text):
    pdf.ln(2)
    pdf.set_font("Deja", "B", 16)
    pdf.set_text_color(*PURPLE)
    pdf.multi_cell(0, 8, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(*DARK)
    pdf.ln(1)


def h2(pdf, text):
    pdf.ln(1)
    pdf.set_font("Deja", "B", 11.5)
    pdf.set_text_color(*PURPLE)
    pdf.multi_cell(0, 6.5, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(*DARK)


def body(pdf, text):
    pdf.set_font("Deja", "", 10.3)
    pdf.set_text_color(*DARK)
    pdf.multi_cell(0, 5.4, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(0.8)


def bullets(pdf, items):
    pdf.set_font("Deja", "", 10.3)
    pdf.set_text_color(*DARK)
    for it in items:
        x = pdf.get_x()
        pdf.cell(5, 5.4, "•")
        pdf.multi_cell(0, 5.4, it, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(0.8)


def code(pdf, text):
    pdf.ln(0.5)
    pdf.set_font("Courier", "", 8.6)
    pdf.set_fill_color(*CODE_BG)
    pdf.set_text_color(40, 40, 60)
    for line in text.split("\n"):
        pdf.cell(0, 4.8, "  " + line, fill=True,
                 new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(*DARK)
    pdf.ln(1.5)


def qa(pdf, q, a):
    pdf.set_font("Deja", "B", 10.3)
    pdf.set_text_color(*DARK)
    pdf.multi_cell(0, 5.4, "Q.  " + q, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Deja", "", 10.3)
    pdf.set_text_color(50, 50, 60)
    pdf.multi_cell(0, 5.4, "A.  " + a, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(*DARK)
    pdf.ln(1.6)


def box(pdf, x, y, w, h, title, sub, fill):
    pdf.set_xy(x, y)
    pdf.set_fill_color(*fill)
    pdf.set_draw_color(*PURPLE)
    pdf.rect(x, y, w, h, style="DF", round_corners=True, corner_radius=2)
    pdf.set_xy(x, y + 2.5)
    pdf.set_font("Deja", "B", 9.5)
    pdf.set_text_color(20, 20, 30)
    pdf.cell(w, 5, title, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_x(x)
    pdf.set_font("Deja", "", 7.6)
    pdf.set_text_color(70, 70, 85)
    pdf.multi_cell(w, 3.6, sub, align="C")
    pdf.set_text_color(*DARK)


def arrow(pdf, x, y1, y2):
    pdf.set_draw_color(*GREY)
    pdf.line(x, y1, x, y2)
    pdf.line(x - 1.5, y2 - 2, x, y2)
    pdf.line(x + 1.5, y2 - 2, x, y2)


def build():
    pdf = new_doc()

    # ---------------- Cover ----------------
    pdf.add_page()
    pdf.ln(40)
    pdf.set_font("Deja", "B", 26)
    pdf.set_text_color(*PURPLE)
    pdf.multi_cell(0, 12, "Explanation of\nYouTube Chatbot", align="C",
                   new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(4)
    pdf.set_font("Deja", "", 12)
    pdf.set_text_color(*GREY)
    pdf.multi_cell(0, 6,
                   "A complete, beginner-to-advanced walkthrough\n"
                   "of the architecture, the code, and how it all runs.",
                   align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(8)
    pdf.set_font("Deja", "", 10.5)
    pdf.set_text_color(*DARK)
    pdf.multi_cell(0, 5.6,
                   "Read this top to bottom. Each PHASE builds on the previous one, the way you "
                   "would actually learn the project. By the end you will understand every moving "
                   "part, know the exact commands to run it, and be ready for interview questions.",
                   align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # ---------------- Contents ----------------
    pdf.add_page()
    h1(pdf, "Contents")
    bullets(pdf, [
        "Phase 1  — The Big Picture: what this app is and why it is different",
        "Phase 2  — Architecture at 30,000 feet (frontend + backend)",
        "Phase 3  — The Tech Stack, and why each piece was chosen",
        "Phase 4  — Project layout & configuration (.env)",
        "Phase 5  — The backend entry point: main.py (FastAPI)",
        "Phase 6  — Service deep-dives (the brains of the app)",
        "Phase 7  — The frontend: the Streamlit app (app.py)",
        "Phase 8  — End-to-end flows: what happens, step by step",
        "Phase 9  — Cross-cutting concepts (the 'aha' lessons)",
        "Phase 10 — Performance & latency: how we made it fast",
        "Phase 11 — Testing",
        "Phase 12 — How to run the project (all commands)",
        "Phase 13 — Glossary for beginners",
        "Phase 14 — Interview questions & answers (with the challenges we solved)",
    ])

    # ---------------- Phase 1 ----------------
    pdf.add_page()
    h1(pdf, "Phase 1 — The Big Picture")
    h2(pdf, "What is this app?")
    body(pdf, "YouTube Smart Chatbot is a learning companion for YouTube videos. You paste a video "
              "(or playlist) URL and it does four things:")
    bullets(pdf, [
        "Shows a LIVE transcript that reveals each line exactly as it is spoken, synced to the video.",
        "WATCHES the video with an AI vision model and lists what appears on screen (slides, "
        "diagrams, scenes) on a searchable timeline.",
        "When you pause, it writes an AI SUMMARY of everything watched so far, and answers your "
        "questions via a chatbot.",
        "Exports a downloadable PDF STUDY PACK: screenshots of the on-screen slides paired with "
        "notes that teach the concept.",
    ])
    h2(pdf, "Why is it different from YouTube's own AI?")
    body(pdf, "YouTube now has AI summaries and a chat tool, so we deliberately built things YouTube "
              "does NOT do:")
    bullets(pdf, [
        "It UNDERSTANDS THE VISUALS, not just the audio — so it works even on videos with "
        "diagrams or no speech at all.",
        "It gives you a TAKEAWAY ARTIFACT — a PDF you keep — instead of an answer that "
        "disappears in a chat box.",
        "Its summaries are PROGRESSIVE (only up to where you paused) — no spoilers.",
    ])
    body(pdf, "Keep these four capabilities in mind; every part of the code exists to serve one of them.")

    # ---------------- Phase 2 ----------------
    pdf.add_page()
    h1(pdf, "Phase 2 — Architecture at 30,000 Feet")
    body(pdf, "The app is TWO separate programs that run at the same time and talk over HTTP:")
    h2(pdf, "1) The Frontend (Streamlit) — what you see in the browser")
    body(pdf, "A Python web UI. It draws the page, embeds the YouTube player, shows the transcript, "
              "buttons, chat, and the PDF download. It holds NO real intelligence — it just collects "
              "your input and calls the backend.")
    h2(pdf, "2) The Backend (FastAPI) — the brain")
    body(pdf, "A web API server exposing 'endpoints' (URLs like /api/transcribe). Each endpoint does "
              "the heavy work — downloading, transcribing, calling AI models, building PDFs — and "
              "returns JSON.")

    h2(pdf, "The system at a glance")
    # ---- drawn architecture diagram ----
    top = pdf.get_y() + 2
    cx = pdf.w / 2
    W = 70
    x = cx - W / 2
    box(pdf, x, top, W, 12, "Browser (you)", "paste a URL, watch, pause, ask, download", (236, 233, 254))
    arrow(pdf, cx, top + 12, top + 18)
    box(pdf, x, top + 18, W, 13, "Streamlit Frontend", "the UI  •  port 8501", (236, 233, 254))
    pdf.set_xy(x + W + 3, top + 22)
    pdf.set_font("Deja", "", 7.5); pdf.set_text_color(*GREY)
    pdf.cell(40, 4, "HTTP + JSON")
    arrow(pdf, cx, top + 31, top + 37)
    box(pdf, x, top + 37, W, 13, "FastAPI Backend", "the brain  •  port 8011", (236, 233, 254))
    # fan-out to four services
    sy = top + 56
    sw = 40
    gap = 4
    total = sw * 4 + gap * 3
    sx0 = cx - total / 2
    labels = [
        ("Captions", "YouTube's own\ncaptions (fast)", (224, 247, 235)),
        ("Deepgram", "speech→text\nfallback", (224, 247, 235)),
        ("Gemini vision", "watches video,\ndescribes screen", (255, 244, 224)),
        ("Groq LLM", "summary, chat,\nstudy notes", (255, 244, 224)),
    ]
    for i, (t, s, f) in enumerate(labels):
        bx = sx0 + i * (sw + gap)
        arrow(pdf, bx + sw / 2, top + 50, sy)
        box(pdf, bx, sy, sw, 14, t, s, f)
    pdf.set_xy(pdf.l_margin, sy + 18)
    pdf.set_text_color(*DARK)
    body(pdf, "Data only flows one way at a time: the browser asks the frontend, the frontend asks the "
              "backend over HTTP+JSON, and the backend fans out to whichever services it needs, then "
              "returns JSON back up.")
    h2(pdf, "The 'services' pattern")
    body(pdf, "Inside the backend, the real work is split into focused SERVICE files under "
              "backend/services/. Each service does ONE job and knows nothing about the web layer. "
              "main.py is the thin 'controller' that wires requests to services. This separation is "
              "the single most important design idea in the project.")

    # ---------------- Phase 3 ----------------
    pdf.add_page()
    h1(pdf, "Phase 3 — The Tech Stack (and why)")
    pairs = [
        ("Streamlit", "Frontend UI in pure Python — fast to build, no JS/HTML framework needed."),
        ("FastAPI + Uvicorn", "The backend web framework + the server that runs it. Async, fast, auto-docs at /docs."),
        ("yt-dlp", "Downloads audio/video and reads video metadata from YouTube."),
        ("youtube-transcript-api", "Fetches YouTube's own captions (fast, free, accurate)."),
        ("Deepgram (Nova-2)", "Speech-to-text FALLBACK when a video has no captions."),
        ("Groq (Llama 3.3 70B)", "The LLM: writes summaries, answers chat, generates study notes. Very fast."),
        ("Google Gemini (flash)", "The VISION model: 'watches' the video and describes what's on screen."),
        ("fpdf2", "Builds the PDF study pack in pure Python."),
        ("ffmpeg", "Splits audio into chunks (Deepgram) and grabs frame screenshots (notes)."),
        ("pytest", "Runs the automated tests."),
    ]
    for name, desc in pairs:
        pdf.set_font("Deja", "B", 10.3); pdf.set_text_color(*DARK)
        pdf.multi_cell(0, 5.2, name, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font("Deja", "", 10.0); pdf.set_text_color(50, 50, 60)
        pdf.multi_cell(0, 5.0, "   " + desc, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(0.6)
    pdf.set_text_color(*DARK)
    body(pdf, "Key idea: external AI/work is reached through small, swappable services. Swap Gemini "
              "for another vision model and only one file changes.")

    # ---------------- Phase 4 ----------------
    pdf.add_page()
    h1(pdf, "Phase 4 — Project Layout & Configuration")
    h2(pdf, "Folder structure")
    code(pdf,
         "backend/\n"
         "  main.py                 FastAPI app + all routes (the controller)\n"
         "  services/\n"
         "    caption_service.py    YouTube captions (original spoken language)\n"
         "    deepgram_service.py   Speech-to-text fallback (parallel chunks)\n"
         "    youtube_service.py    yt-dlp: metadata, audio/video download, playlist\n"
         "    vision_service.py     Gemini: on-screen visual moments\n"
         "    groq_service.py       summary + chat + study-notes generation\n"
         "    notes_service.py      ffmpeg frames + PDF study-pack builder\n"
         "frontend/\n"
         "  app.py                  Streamlit UI (player, timeline, chat, export)\n"
         "assets/fonts/DejaVuSans.ttf   Unicode font bundled for PDFs\n"
         "downloads/                Temp audio/video (auto-deleted)\n"
         ".env                      Secret API keys (never committed)")
    h2(pdf, "Configuration: the .env file")
    body(pdf, "Secrets/settings live in a .env file (loaded by 'python-dotenv'). The code reads them "
              "with os.getenv(...).")
    bullets(pdf, [
        "DEEPGRAM_API_KEY, GROQ_API_KEY — required.",
        "GEMINI_API_KEY — optional; without it the app runs audio-only (no visuals).",
        "GROQ_MODEL, GEMINI_VISION_MODEL, DEEPGRAM_MODEL — optional model overrides.",
    ])
    body(pdf, "Why .env? So secrets stay out of the code and out of GitHub. .gitignore excludes it.")

    # ---------------- Phase 5 ----------------
    pdf.add_page()
    h1(pdf, "Phase 5 — The Backend Entry Point: main.py")
    h2(pdf, "Creating the app")
    body(pdf, "main.py creates the FastAPI application and enables CORS (so the browser frontend may "
              "call it). It then imports the service functions it will orchestrate.")
    code(pdf, "app = FastAPI(title='YouTube Smart Chatbot API')\n"
              "app.add_middleware(CORSMiddleware, allow_origins=['*'], ...)")
    h2(pdf, "Schemas (Pydantic models)")
    body(pdf, "Python classes describing exactly what JSON a request/response must contain. FastAPI "
              "validates input automatically and builds the /docs page from them.")
    code(pdf, "class VisualSegment(BaseModel):\n"
              "    start: float\n"
              "    end: float\n"
              "    label: str\n"
              "    description: str")
    h2(pdf, "The routes (endpoints)")
    bullets(pdf, [
        "/api/transcribe    — load a video: transcript + visual moments",
        "/api/summarize     — AI summary up to the pause point",
        "/api/chat          — answer a question (RAG)",
        "/api/export_notes  — build & return the PDF study pack",
        "/api/playlist      — list all videos in a playlist",
        "/api/set_pause, /api/get_pause — remember where you paused",
        "/api/health        — check that API keys are configured",
    ])
    body(pdf, "A route reads the validated request, calls the right service(s), wraps the result, and "
              "handles errors via HTTPException. The intelligence lives in the services.")

    # ---------------- Phase 6 ----------------
    pdf.add_page()
    h1(pdf, "Phase 6 — Service Deep-Dives")
    body(pdf, "This is the heart of the project. We go through each service in the order data flows.")
    h2(pdf, "6.1  caption_service.py")
    body(pdf, "Tries YouTube's OWN captions. Subtlety: popular videos have community-translated "
              "tracks, so the 'first' track can be the wrong language. Fix: the AUTO-GENERATED track "
              "is always in the spoken language; we read its code, fetch that first, then a preferred "
              "list, then anything else.")
    code(pdf, "original_lang = generated_codes[0] if generated_codes else None\n"
              "fetch_order = [original_lang] + _LANGUAGE_PRIORITY + remaining")
    body(pdf, "Returns {segments, words, full_text, detected_language}, or None (no captions) → fall "
              "back to Deepgram.")
    h2(pdf, "6.2  deepgram_service.py")
    body(pdf, "Used when captions are missing. ffprobe reads duration; ffmpeg splits into 5-min "
              "chunks; all chunks go to Deepgram at once (asyncio.gather); results merge with each "
              "chunk's timestamps shifted by its offset. Same dict shape as captions — and, unlike "
              "captions, it includes real per-WORD timestamps.")
    h2(pdf, "6.3  youtube_service.py")
    body(pdf, "Metadata + audio download + low-res video download + playlist expansion via yt-dlp. "
              "Always uses a CLEAN url + noplaylist so a radio-mix URL can't pull a different video.")
    code(pdf, "clean_url = f'https://www.youtube.com/watch?v={video_id}'\n"
              "ydl_opts = { ..., 'noplaylist': True }")
    h2(pdf, "6.4  vision_service.py (Gemini)")
    body(pdf, "Sends the video URL to Gemini, gets JSON moments {timestamp, end, label, "
              "description}. Robustness: URL normalisation, strict JSON parsing (MM:SS→seconds, drop "
              "bad rows, sort), and graceful empty [] on any failure so it never breaks transcribe.")
    h2(pdf, "6.5  groq_service.py (LLM)")
    body(pdf, "summarize_transcript and chat_with_context share _build_context, which interleaves "
              "spoken lines and [VISUAL ...] lines chronologically up to the pause. "
              "generate_study_notes builds 'units' (one per visual moment, or transcript chunks if "
              "none), attaches the narration spoken during each, and asks Groq (JSON mode) to enrich "
              "each unit BY INDEX with a teaching note.")
    h2(pdf, "6.6  notes_service.py")
    body(pdf, "extract_frames: ffmpeg grabs one screenshot per visual timestamp (de-duplicated and "
              "capped). build_study_notes_pdf: fpdf2 lays out the title, key takeaways, and one "
              "section per moment — heading, the matching screenshot, and the teaching note — using "
              "the bundled Unicode font so non-Latin transcripts render.")

    # ---------------- Phase 7 ----------------
    pdf.add_page()
    h1(pdf, "Phase 7 — The Frontend (app.py)")
    body(pdf, "Streamlit re-runs the whole script on every interaction; st.session_state is the "
              "memory that survives.")
    h2(pdf, "Session state")
    body(pdf, "transcript_data, visual_segments, video_id, pause_time, summary, chat_history, "
              "notes_pdf persist across re-runs and reset on a new video.")
    h2(pdf, "The video player + live transcript sync")
    body(pdf, "build_player_html returns a self-contained HTML+JS block (components.html). It loads "
              "the YouTube IFrame API; a JS loop polls the real playback time every 100 ms and "
              "reveals transcript lines as their timestamps arrive, and posts the pause time to "
              "/api/set_pause.")
    body(pdf, "Sync subtlety: YouTube captions are PHRASE-level — one start time per line, no "
              "per-word timing. Faking even word-by-word timing made words drift out of sync with "
              "the speech, so each caption LINE is now revealed at its real start time, like "
              "subtitles. When the transcript comes from Deepgram instead, it carries real per-word "
              "timestamps, so each individual word lights up exactly when spoken.")
    h2(pdf, "Visual Timeline, summary, chat, export")
    bullets(pdf, [
        "Visual Timeline: separate searchable panel, auto-expanded for visuals-only videos.",
        "Summary + chat live in an st.fragment so only that part re-runs — the video never reloads.",
        "Export posts the data to /api/export_notes and offers the PDF via st.download_button. "
        "'Up to pause point' reads the LIVE pause time from the backend, and the file is named "
        "after the video title.",
    ])

    # ---------------- Phase 8 ----------------
    pdf.add_page()
    h1(pdf, "Phase 8 — End-to-End Flows")
    h2(pdf, "Flow A — Transcribe")
    bullets(pdf, [
        "Frontend POSTs the URL to /api/transcribe.",
        "Backend reads metadata, then runs IN PARALLEL: (a) transcript (captions or Deepgram), "
        "(b) Gemini visual analysis.",
        "Merges into one response: segments + words + visual_segments.",
        "Frontend renders player, live transcript, and Visual Timeline.",
    ])
    h2(pdf, "Flow B — Summary  /  Flow C — Chat")
    body(pdf, "On pause/question, the frontend sends segments + visuals (+ pause/history). "
              "groq_service builds the chronological spoken+visual context and asks Groq. Chat is "
              "grounded ONLY in that context (RAG).")
    h2(pdf, "Flow D — Export Study Notes (PDF)")
    bullets(pdf, [
        "Pick scope, click Generate. 'Up to pause point' uses the live backend pause time.",
        "Backend runs IN PARALLEL: (a) Groq writes notes JSON; (b) download video + ffmpeg frames.",
        "fpdf2 assembles the PDF; bytes streamed back as a download named after the video title.",
    ])

    # ---------------- Phase 9 ----------------
    pdf.add_page()
    h1(pdf, "Phase 9 — Cross-Cutting Concepts")
    h2(pdf, "Async & parallelism")
    body(pdf, "Overlap independent slow calls with asyncio.gather; wrap blocking functions in "
              "asyncio.to_thread. Used in transcribe (audio || vision) and export (notes || frames).")
    h2(pdf, "Graceful degradation")
    body(pdf, "Every optional capability fails SOFT: no Gemini → []; no captions → Deepgram; "
              "screenshot fails → text-only PDF; LLM JSON fails → raw content. The app always "
              "produces something useful.")
    h2(pdf, "Respecting free-tier limits")
    bullets(pdf, [
        "Gemini: ~20 vision requests/day per model. Swap GEMINI_VISION_MODEL for a fresh quota.",
        "Groq: 12k tokens/minute. The notes request is trimmed to fit.",
    ])

    # ---------------- Phase 10 (NEW: dedicated performance/latency) ----------------
    pdf.add_page()
    h1(pdf, "Phase 10 — Performance & Latency")
    body(pdf, "Latency was a first-class concern. Four techniques keep the app feeling instant even "
              "though it orchestrates several slow AI services.")
    h2(pdf, "1) Captions-first fast path")
    body(pdf, "Most videos have YouTube captions, which are free and return instantly. We only "
              "download audio and run Deepgram when there are NO captions — so the common case skips "
              "the two slowest steps (download + speech-to-text) entirely.")
    h2(pdf, "2) Parallel chunked speech-to-text")
    body(pdf, "When Deepgram is needed, ffmpeg splits the audio into 5-minute chunks and ALL chunks "
              "are sent concurrently with asyncio.gather. A 30-minute video becomes ~6 parallel "
              "requests, so wall-clock time is roughly one chunk instead of the whole file — a "
              "near-linear speedup. Each chunk's timestamps are shifted by its offset, then merged.")
    h2(pdf, "3) Transcript ∥ vision overlap")
    body(pdf, "Transcribe kicks off Gemini visual analysis and the audio transcript at the same "
              "time (asyncio.gather). The two longest operations run together instead of back-to-back, "
              "so total time is the slower of the two, not their sum.")
    h2(pdf, "4) Notes ∥ frame-extraction overlap")
    body(pdf, "Exporting a study pack runs the Groq note-writing and the ffmpeg screenshot grabbing "
              "in parallel, then assembles the PDF once both finish. Blocking calls are pushed off "
              "the event loop with asyncio.to_thread so they truly overlap.")
    body(pdf, "Net effect: the user waits for the single slowest stage of each operation, not the "
              "sum of every stage.")

    # ---------------- Phase 11 (Testing) ----------------
    pdf.add_page()
    h1(pdf, "Phase 11 — Testing")
    body(pdf, "pytest, test-first. AI calls are mocked so the suite is fast, free, deterministic.")
    bullets(pdf, [
        "test_vision_service.py — parsing, URL normalisation, graceful-empty.",
        "test_groq_visual.py / test_groq_notes.py — context blending and note anchoring.",
        "test_notes_service.py — frame de-dup/cap, PDF builder returns valid bytes.",
        "test_transcribe_api.py / test_export_notes_api.py — endpoints with services mocked.",
        "test_youtube_video.py — clean-URL + noplaylist behaviour.",
    ])

    # ---------------- Phase 12 (Run) ----------------
    pdf.add_page()
    h1(pdf, "Phase 12 — How to Run the Project")
    h2(pdf, "One-time setup")
    code(pdf, "python -m venv venv\n"
              "venv\\Scripts\\activate\n"
              "pip install -r requirements.txt\n"
              "# Install ffmpeg; ensure 'ffmpeg' & 'ffprobe' on PATH\n"
              "# Create backend/.env: DEEPGRAM_API_KEY, GROQ_API_KEY, GEMINI_API_KEY")
    h2(pdf, "Run it (two terminals)")
    code(pdf, "# Terminal 1 (backend)\n"
              "python -m uvicorn backend.main:app --host 0.0.0.0 --port 8011\n"
              "\n"
              "# Terminal 2 (frontend)\n"
              "venv\\Scripts\\streamlit run frontend/app.py --server.port 8501")
    body(pdf, "Open  http://localhost:8501")
    h2(pdf, "Useful checks")
    code(pdf, "http://localhost:8011/api/health     # backend health\n"
              "http://localhost:8011/docs           # interactive API docs\n"
              "python -m pytest tests/ -v           # run the tests")
    body(pdf, "Windows: do NOT use uvicorn --reload; restart manually after edits. "
              "Tip: if uvicorn says '10048 / only one usage of each socket address', the backend is "
              "already running — check /api/health before starting another.")

    # ---------------- Phase 13 (Glossary) ----------------
    pdf.add_page()
    h1(pdf, "Phase 13 — Glossary for Beginners")
    gloss = [
        ("API / Endpoint", "URLs one program calls to ask another to do work (e.g. /api/transcribe)."),
        ("Backend / Frontend", "Backend = server doing the work; Frontend = the UI you see."),
        ("JSON", "Text format (key: value) used to send data between frontend and backend."),
        ("Pydantic model", "A class that defines and validates the shape of JSON data."),
        ("LLM", "Large Language Model (Groq's Llama) — writes summaries and answers."),
        ("RAG", "Answering using ONLY provided context, so the AI can't invent facts."),
        ("STT", "Speech-To-Text — turning spoken audio into written words (Deepgram)."),
        ("Vision model", "An AI that can 'see' video/images (Gemini) and describe them."),
        ("Async / to_thread", "Running slow waiting tasks together / off the main thread, without freezing."),
        ("Graceful degradation", "When an optional feature fails, the app keeps working with less."),
        ("Session state", "Streamlit's memory that survives the script re-running on each click."),
    ]
    for term, desc in gloss:
        pdf.set_font("Deja", "B", 10.3); pdf.set_text_color(*DARK)
        pdf.multi_cell(0, 5.2, term, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font("Deja", "", 10.0); pdf.set_text_color(50, 50, 60)
        pdf.multi_cell(0, 5.0, "   " + desc, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(0.5)

    # ---------------- Phase 14 (Interview) ----------------
    pdf.add_page()
    h1(pdf, "Phase 14 — Interview Questions & Answers")
    body(pdf, "Tricky questions an interviewer might ask about THIS project — with strong answers. "
              "These cover the speech-to-text pipeline, the visual timeline, the live-sync and export "
              "fixes, the real challenges faced, and how each was solved.")

    h2(pdf, "A. Speech-to-Text (audio → text)")
    qa(pdf, "How do you turn the video's audio into text?",
       "Two-tier. First I try YouTube's own captions via youtube-transcript-api — free, instant, "
       "accurate. Only if a video has no captions do I download the audio with yt-dlp and send it to "
       "Deepgram (Nova-2) for speech-to-text. Captions-first keeps it fast and cheap.")
    qa(pdf, "Deepgram is slow on long audio. How did you speed it up?",
       "I split the audio into 5-minute chunks with ffmpeg and send ALL chunks to Deepgram "
       "concurrently with asyncio.gather. A 30-minute video becomes ~6 parallel requests, so "
       "wall-clock time is roughly one chunk instead of the whole file — a near-linear speedup.")
    qa(pdf, "If you transcribe chunks separately, how do the timestamps stay correct?",
       "Each chunk's transcript starts at 0. I remember each chunk's OFFSET (chunk index × 300s) and "
       "add it to every word/segment timestamp before merging, then sort by start time. So a word at "
       "0:12 in chunk 3 becomes 10:12 globally.")
    qa(pdf, "Captions came back in the WRONG language (Arabic on an English video). Why, and how did "
            "you fix it?",
       "Popular videos carry community-translated MANUAL caption tracks in dozens of languages, and "
       "my code took the first one listed — which happened to be Arabic. Fix: the AUTO-GENERATED "
       "track is always in the language actually spoken, so I read its language code, treat it as the "
       "'original language', and fetch that first. English video → English, Hindi video → Hindi.")

    pdf.add_page()
    h2(pdf, "B. Visual understanding (video → timeline)")
    qa(pdf, "How does the app 'see' what's in the video?",
       "I pass the YouTube URL directly to Google Gemini (a multimodal model) with a prompt asking "
       "it to return JSON moments — a timestamp, a short label, and a description of what's on "
       "screen. I parse that into a searchable Visual Timeline and also feed it into the summary and "
       "chat so answers reflect what was SHOWN, not just said.")
    qa(pdf, "What happens when the Gemini free-tier quota runs out?",
       "The quota is about 20 requests/day per model. When it's hit, analyze_video_visuals returns "
       "an empty list and the app continues audio-only. The vision model is also swappable via an "
       "env var, so a different model gives a fresh quota.")

    h2(pdf, "C. Live transcript sync")
    qa(pdf, "The live transcript drifted out of sync with the speech on caption videos. Why, and how "
            "did you fix it?",
       "YouTube captions are PHRASE-level: one start time per line, with no per-word timing. The UI "
       "was faking word-by-word timing by spreading each line's words evenly across the gap to the "
       "next line — so words appeared at invented times that didn't match the audio (and "
       "auto-generated caption timing already lags slightly). Fix: reveal each caption LINE at its "
       "real start time, like subtitles, which stays accurate at the line level. For exact per-word "
       "sync, the transcript can come from Deepgram, which provides real word timestamps.")

    h2(pdf, "D. Study-notes PDF generation")
    qa(pdf, "Your notes had only 4 sections and no images, even though the video had 38 visual "
            "moments. Why?",
       "I had asked the LLM to 'make one section per visual moment and reuse its timestamp', but it "
       "collapsed them into ~4 thematic sections with INVENTED round timestamps (2:40, 5:00). Since "
       "the PDF matches screenshots to sections by timestamp, those fake timestamps matched no real "
       "frame → no images.")
    qa(pdf, "How did you fix the sparse-notes-and-missing-images problem?",
       "I stopped trusting the LLM for structure. I build the sections DETERMINISTICALLY from the "
       "real visual moments (exact timestamps), and only ask the LLM to ENRICH each one BY INDEX "
       "with a heading and a teaching note. Now there's one section per real moment, timestamps are "
       "exact, and every screenshot embeds.")

    pdf.add_page()
    qa(pdf, "The notes just described the screen ('an image appears'). How did you make them teach?",
       "For each visual moment I gather the NARRATION spoken during its time window and pass that to "
       "the LLM, instructing it to explain the CONCEPT from the narration and interpret what the "
       "diagram INDICATES — not describe pixels. The result reads like real revision notes.")
    qa(pdf, "A long video's notes request hit Groq's 12k-tokens-per-minute limit (HTTP 413). Fix?",
       "I trimmed the per-moment narration sent to the model and lowered max_tokens so the whole "
       "request stays under the free-tier limit; if it still fails, it falls back to using the raw "
       "narration as the note.")
    qa(pdf, "The 'Up to pause point' export returned the WHOLE video even though you'd paused. Why?",
       "The export button read st.session_state.pause_time, which is only populated AFTER clicking "
       "'Get AI Summary'. Paused-then-exported sent 0, and the backend treats 0 as 'no pause → whole "
       "video'. Fix: the export now reads the LIVE pause time from the backend (/api/get_pause) — the "
       "same place the player stores it on every pause — so the scope matches where you actually "
       "stopped. (The download is also named after the video title now, not the raw video ID.)")

    h2(pdf, "E. Architecture, performance & curveballs")
    qa(pdf, "Why split into a separate frontend and backend instead of one Streamlit app?",
       "Separation of concerns and reuse. The backend is a clean JSON API with no UI assumptions, "
       "so it can be tested independently, scaled separately, and reused by another client (mobile, "
       "CLI) without touching the UI.")
    qa(pdf, "How do you keep the chatbot from hallucinating?",
       "It's RAG: the system prompt instructs the model to answer ONLY from the provided transcript "
       "+ visual context, and to say so honestly if the answer isn't there. The context is also "
       "scoped up to the pause point, which doubles as a no-spoiler feature.")

    pdf.add_page()
    qa(pdf, "What was the trickiest non-obvious bug?",
       "Several tie: (1) the wrong-language captions (fixed via the auto-generated track); (2) the "
       "radio-mix URL silently downloading a DIFFERENT video (fixed with a clean URL + noplaylist); "
       "(3) the LLM inventing timestamps that broke image embedding (fixed by anchoring sections to "
       "real moments); (4) the live transcript drifting (fixed with phrase-level reveal); and (5) "
       "'Up to pause point' ignoring the pause (fixed by reading the live backend pause time). Almost "
       "all were 'it runs but produces subtly wrong output' bugs — the hardest kind.")
    body(pdf, "That's the whole project — the why, the architecture, every service, the frontend, the "
              "flows, the performance story, the concepts, the tests, the run commands, and the "
              "interview story. Re-read any phase as needed.")
    body(pdf, "Happy learning, and good luck in the interview!")

    pdf.output(OUT)
    print(f"Wrote {OUT} ({pdf.page_no()} pages)")


if __name__ == "__main__":
    build()
