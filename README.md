# YouTube Smart Chatbot

An intelligent YouTube companion that shows a **live word-by-word transcript** synced with video playback, **understands what is shown on screen** (slides, diagrams, scenes), auto-generates an **AI summary** when you pause, lets you **ask questions** via a RAG chatbot, and **exports a downloadable PDF study pack** — in any language. Supports both single videos and full playlists.

---

## Features

- Live transcript that reveals each word exactly when it is spoken
- **Visual understanding** — a Gemini vision model analyzes the video and produces a timestamped, **searchable Visual Timeline** of what appears on screen (diagrams, slides, code, scenes)
- **📄 Study-notes PDF export** — turn any video into a downloadable study pack: screenshots of the on-screen slides/diagrams paired with notes that *teach the concept* and *explain what each image shows*. Choose **whole video** or **up to the pause point**
- **Multimodal summary & chat** — the AI summary and chatbot answers blend what was *said* with what was *shown*
- Works on **visuals-only videos** (no speech) — notes come from the visual content alone
- Supports any language — fetches YouTube captions in the **video's original spoken language**, falls back to Deepgram
- Paste a **playlist URL** to load all videos — plays sequentially with a scrollable queue
- Skip to the next playlist video any time with the **Next →** button
- Pause the video → AI summary generated automatically
- Ask doubts via chatbot — answers are grounded in the transcript and on-screen visuals
- Resume video without losing chat history
- Parallel processing — transcript ∥ visual analysis, and notes ∥ frame extraction — for fast turnaround

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Streamlit |
| Backend | FastAPI + Uvicorn |
| Audio / Video Download | yt-dlp |
| Speech-to-Text | Deepgram Nova-2 |
| Captions | youtube-transcript-api |
| LLM / Chat / Notes | Groq (Llama 3.3 70B) |
| Visual understanding | Google Gemini (gemini-flash) |
| PDF export | fpdf2 |
| Frame extraction | ffmpeg |

---

## Requirements

- Python 3.10+
- **ffmpeg** (and `ffprobe`) on your PATH — used for Deepgram audio chunking and study-notes frame extraction → https://ffmpeg.org
- Deepgram API key → https://deepgram.com
- Groq API key → https://console.groq.com
- Gemini API key (free) → https://aistudio.google.com — for visual understanding; the app still works without it (audio-only)

---

## Setup

**1. Clone the repository**
```bash
git clone https://github.com/jay12676/YouTube_Chatbot.git
cd YouTube_Chatbot
```

**2. Create and activate virtual environment**
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python -m venv venv
source venv/bin/activate
```

**3. Install dependencies**
```bash
pip install -r requirements.txt
```

**4. Create your `.env` file** in the project root (or `backend/.env`):
```
DEEPGRAM_API_KEY=your_deepgram_api_key_here
GROQ_API_KEY=your_groq_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here     # optional — enables visual understanding
```

> The repo bundles a Unicode font (`assets/fonts/DejaVuSans.ttf`) so the exported
> PDF renders non-Latin transcripts. No extra setup needed.

---

## Running the Project

You need **two terminals** open at the same time.

**Terminal 1 — Start the Backend (FastAPI)**
```bash
# Windows
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8011

# macOS / Linux
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8011
```

**Terminal 2 — Start the Frontend (Streamlit)**
```bash
# Windows
venv\Scripts\streamlit run frontend/app.py --server.port 8501

# macOS / Linux
venv/bin/streamlit run frontend/app.py --server.port 8501
```

**Open in browser:**
```
http://localhost:8501
```

**Check backend health:**
```
http://localhost:8011/api/health
```
Should return: `{"status":"healthy","deepgram_configured":true,"groq_configured":true}`

**FastAPI interactive docs:**
```
http://localhost:8011/docs
```

> **Note (Windows):** Do not use `--reload` with uvicorn on Windows — it causes a multiprocessing crash on file changes. Restart the backend manually after code changes instead.

---

## Project Structure

```
project/
├── backend/
│   ├── main.py                  # FastAPI app, all API routes
│   └── services/
│       ├── youtube_service.py   # yt-dlp audio/video download, metadata, playlist fetch
│       ├── caption_service.py   # YouTube captions (original spoken language)
│       ├── deepgram_service.py  # Deepgram STT fallback (parallel chunked)
│       ├── vision_service.py    # Gemini visual analysis → timestamped on-screen moments
│       ├── groq_service.py      # LLM summarization + RAG chat + study-notes generation
│       └── notes_service.py     # ffmpeg frame extraction + PDF study-pack builder
├── frontend/
│   └── app.py                   # Streamlit UI (player, visual timeline, export, chat)
├── assets/
│   └── fonts/DejaVuSans.ttf     # Unicode font bundled for multi-language PDFs
├── downloads/                   # Temporary audio/video files (auto-deleted)
├── requirements.txt
├── .env                         # API keys (never commit this)
└── README.md
```

---

## How It Works

**Single video:**
1. Paste a YouTube URL and click **Transcribe**
2. The backend runs two things **in parallel**: (a) the transcript — YouTube captions in the video's original language, or Deepgram on downloaded audio if there are none; (b) **Gemini visual analysis** of the video → timestamped on-screen moments
3. The video player and live transcript appear, plus a **📺 Visual Timeline** of what's shown on screen (searchable, auto-expanded for visuals-only videos)
4. Words appear one by one as the video plays
5. Pause the video → click **Get AI Summary** → a summary that blends what was *said* and *shown* up to that point
6. Ask questions in the chatbot → answers are grounded in both the transcript and the on-screen visuals
7. Click **📄 Generate Study Notes PDF** (choose *whole video* or *up to pause*) → download a study pack of slide screenshots + teaching notes + key takeaways
8. Resume the video — transcript continues, chat history is preserved

**Playlist:**
1. Paste a YouTube playlist URL (or a video URL that contains `list=`) and click **Load Playlist**
2. All video metadata is fetched instantly — no downloading yet
3. A scrollable queue panel shows all videos (done / now playing / upcoming)
4. The first video is transcribed and loaded automatically
5. Click **Next →** at any time to skip to the next video in the playlist

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/transcribe` | Load video, get transcript + word timestamps + visual segments |
| POST | `/api/playlist` | Fetch all video metadata from a playlist URL |
| POST | `/api/summarize` | Generate AI summary (spoken + visual) up to pause point |
| POST | `/api/chat` | Ask a question via RAG chatbot (spoken + visual context) |
| POST | `/api/export_notes` | Build & download a PDF study pack (screenshots + notes) |
| POST | `/api/set_pause` | Store current pause timestamp |
| GET | `/api/get_pause` | Get stored pause timestamp |
| GET | `/api/health` | Check API keys are configured |

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DEEPGRAM_API_KEY` | yes | Deepgram API key for speech-to-text (fallback when no captions) |
| `GROQ_API_KEY` | yes | Groq API key for summarization, chat, and study notes |
| `GEMINI_API_KEY` | optional | Google Gemini key for visual understanding; if missing, the app runs audio-only |
| `GROQ_MODEL` | optional | Groq chat model (default `llama-3.3-70b-versatile`) |
| `GEMINI_VISION_MODEL` | optional | Gemini vision model (default `gemini-flash-latest`) |
| `DEEPGRAM_MODEL` | optional | Deepgram model (default `nova-2`) |
| `DEEPGRAM_CHUNK_DURATION_SEC` | optional | Audio chunk size for parallel STT (default `300`) |

> **Free-tier note:** Gemini's free tier allows ~20 vision requests/day **per model**. If you hit the limit, switch `GEMINI_VISION_MODEL` (e.g. `gemini-flash-lite-latest`) for a fresh quota, or the app falls back to audio-only. Groq's free tier caps tokens/minute; study-notes requests are sized to stay within it.
