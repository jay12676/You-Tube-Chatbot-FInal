# YouTube Smart Chatbot

An intelligent YouTube companion that shows a **live word-by-word transcript** synced with video playback, auto-generates an **AI summary** when you pause, and lets you **ask questions** about the video via a RAG chatbot — in any language.

---

## Features

- Live transcript that reveals each word exactly when it is spoken
- Supports any language — fetches YouTube captions first, falls back to Deepgram
- Pause the video → AI summary generated automatically
- Ask doubts via chatbot — answers are grounded in the transcript
- Resume video without losing chat history

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Streamlit |
| Backend | FastAPI + Uvicorn |
| Audio Download | yt-dlp |
| Speech-to-Text | Deepgram Nova-2 |
| Captions | youtube-transcript-api |
| LLM / Chat | Groq (Llama 3.3 70B) |

---

## Requirements

- Python 3.10+
- Deepgram API key → https://deepgram.com
- Groq API key → https://console.groq.com

---

## Setup

**1. Clone the repository**
```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
cd YOUR_REPO_NAME
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

**4. Create your `.env` file** in the project root:
```
DEEPGRAM_API_KEY=your_deepgram_api_key_here
GROQ_API_KEY=your_groq_api_key_here
```

---

## Running the Project

You need **two terminals** open at the same time.

**Terminal 1 — Start the Backend (FastAPI)**
```bash
cd "path/to/project"
venv\Scripts\uvicorn backend.main:app --host 0.0.0.0 --port 8001 --reload
```

**Terminal 2 — Start the Frontend (Streamlit)**
```bash
cd "path/to/project"
venv\Scripts\streamlit run frontend/app.py --server.port 8502
```

**Open in browser:**
```
http://localhost:8502
```

**Check backend health:**
```
http://localhost:8001/api/health
```
Should return: `{"status":"healthy","deepgram_configured":true,"groq_configured":true}`

**FastAPI interactive docs:**
```
http://localhost:8001/docs
```

---

## Project Structure

```
project/
├── backend/
│   ├── main.py                  # FastAPI app, all API routes
│   └── services/
│       ├── youtube_service.py   # yt-dlp audio download + metadata
│       ├── caption_service.py   # YouTube captions (primary transcript source)
│       ├── deepgram_service.py  # Deepgram STT fallback
│       └── groq_service.py      # LLM summarization + RAG chat
├── frontend/
│   └── app.py                   # Streamlit UI
├── downloads/                   # Temporary audio files (auto-deleted)
├── requirements.txt
├── .env                         # API keys (never commit this)
└── README.md
```

---

## How It Works

1. Paste a YouTube URL and click **Transcribe**
2. The backend tries YouTube captions first (fast, gapless). If unavailable, downloads audio and uses Deepgram
3. The video player and live transcript panel appear side by side
4. Words appear one by one as the video plays
5. Pause the video → click **Get AI Summary** → summary of everything watched so far
6. Ask questions in the chatbot → answers come from the transcript context only
7. Resume the video — transcript continues, chat history is preserved

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/transcribe` | Load video, get transcript + word timestamps |
| POST | `/api/summarize` | Generate AI summary up to pause point |
| POST | `/api/chat` | Ask a question via RAG chatbot |
| POST | `/api/set_pause` | Store current pause timestamp |
| GET | `/api/get_pause` | Get stored pause timestamp |
| GET | `/api/health` | Check API keys are configured |

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `DEEPGRAM_API_KEY` | Deepgram API key for speech-to-text |
| `GROQ_API_KEY` | Groq API key for LLM summarization and chat |
