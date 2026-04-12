"""
FastAPI backend for YouTube Smart Chatbot.
Handles video audio extraction, Deepgram transcription,
and RAG-based summarization & Q&A via Groq.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import os
import sys

# Fix Windows console encoding for Unicode (Hindi, emoji, etc.)
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from backend.services.youtube_service import extract_video_info, download_audio, extract_playlist_info
from backend.services.deepgram_service import transcribe_audio
from backend.services.caption_service import get_youtube_captions
from backend.services.groq_service import summarize_transcript, chat_with_context

# Load environment variables
load_dotenv()

app = FastAPI(
    title="YouTube Smart Chatbot API",
    description="Backend API for YouTube video transcription and RAG chatbot",
    version="1.0.0",
)

# CORS — allow Streamlit frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- Schemas ----------

class VideoRequest(BaseModel):
    url: str


class TranscriptSegment(BaseModel):
    text: str
    start: float
    end: float


class WordTimestamp(BaseModel):
    word: str
    start: float
    end: float


class TranscriptResponse(BaseModel):
    video_id: str
    title: str
    duration: int
    thumbnail: str
    segments: list[TranscriptSegment]
    words: list[WordTimestamp] = []
    full_text: str
    detected_language: str


class SummarizeRequest(BaseModel):
    segments: list[dict]
    pause_time: float


class SummarizeResponse(BaseModel):
    summary: str
    pause_time: float
    segments_used: int


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    question: str
    segments: list[dict]
    pause_time: float
    chat_history: list[ChatMessage] = []


class ChatResponse(BaseModel):
    answer: str


class PlaylistVideoItem(BaseModel):
    id: str
    title: str
    duration: int
    thumbnail: str
    url: str


class PlaylistResponse(BaseModel):
    playlist_title: str
    videos: list[PlaylistVideoItem]
    total: int


# In-memory pause store (per-server, good enough for single-user dev use)
_pause_store: dict = {"time": None}


# ---------- Routes ----------

@app.get("/")
def root():
    return {"status": "ok", "message": "YouTube Smart Chatbot API is running 🚀"}


@app.post("/api/transcribe", response_model=TranscriptResponse)
async def transcribe_video(request: VideoRequest):
    """
    Takes a YouTube URL, downloads audio, transcribes with Deepgram,
    and returns timestamped transcript segments.
    """
    try:
        # Step 1: Extract video metadata
        print(f"[API] Loading video: {request.url}")
        video_info = extract_video_info(request.url)
        print(f"[API] Video: {video_info['title']} (duration: {video_info['duration']}s)", flush=True)

        # Step 2: Try YouTube captions first (fast, gapless, no API cost)
        print(f"[API] Trying YouTube captions first...")
        transcript_result = get_youtube_captions(video_info["id"])

        if transcript_result:
            print(f"[API] YouTube captions found: {len(transcript_result['segments'])} segments")
        else:
            # Step 3: Fall back to Deepgram (download audio → transcribe)
            print(f"[API] No YouTube captions — falling back to Deepgram...")
            audio_path = download_audio(request.url, video_info["id"])
            print(f"[API] Audio saved: {audio_path}")

            transcript_result = await transcribe_audio(audio_path)
            print(f"[API] Deepgram transcription: {len(transcript_result['segments'])} segments, "
                  f"{len(transcript_result.get('words', []))} words")

            # Clean up downloaded audio
            try:
                if os.path.exists(audio_path):
                    os.remove(audio_path)
                    print(f"[API] Cleaned up audio file: {audio_path}")
            except Exception as cleanup_err:
                print(f"[API] Warning: Could not delete audio file: {cleanup_err}")

        # Step 4: Return response
        return TranscriptResponse(
            video_id=video_info["id"],
            title=video_info["title"],
            duration=video_info["duration"],
            thumbnail=video_info["thumbnail"],
            segments=[
                TranscriptSegment(**seg) for seg in transcript_result["segments"]
            ],
            words=[
                WordTimestamp(**w) for w in transcript_result.get("words", [])
            ],
            full_text=transcript_result["full_text"],
            detected_language=transcript_result["detected_language"],
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=f"Audio processing error: {str(e)}")
    except Exception as e:
        print(f"[API] Error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")


@app.post("/api/summarize", response_model=SummarizeResponse)
def summarize_video(request: SummarizeRequest):
    """
    Summarize transcript content up to the pause point using Groq LLM.
    """
    try:
        print(f"[API] Summarizing transcript up to {request.pause_time:.1f}s "
              f"({len(request.segments)} total segments)")

        summary = summarize_transcript(request.segments, request.pause_time)
        segments_used = len([s for s in request.segments if s["start"] <= request.pause_time])

        print(f"[API] Summary generated ({segments_used} segments used)")

        return SummarizeResponse(
            summary=summary,
            pause_time=request.pause_time,
            segments_used=segments_used,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"[API] Summarize error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"Summarization failed: {str(e)}")


@app.post("/api/chat", response_model=ChatResponse)
def chat_about_video(request: ChatRequest):
    """
    Answer a user's question about the video using RAG with transcript context.
    """
    try:
        print(f"[API] Chat question: '{request.question[:80]}...' "
              f"(pause_time={request.pause_time:.1f}s, history={len(request.chat_history)} msgs)")

        history = [{"role": m.role, "content": m.content} for m in request.chat_history]

        answer = chat_with_context(
            question=request.question,
            segments=request.segments,
            pause_time=request.pause_time,
            chat_history=history,
        )

        print(f"[API] Chat answer generated ({len(answer)} chars)")

        return ChatResponse(answer=answer)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"[API] Chat error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


@app.post("/api/playlist", response_model=PlaylistResponse)
def get_playlist(request: VideoRequest):
    """Return metadata for all videos in a YouTube playlist URL."""
    try:
        result = extract_playlist_info(request.url)
        return PlaylistResponse(
            playlist_title=result["playlist_title"],
            videos=[PlaylistVideoItem(**v) for v in result["videos"]],
            total=result["total"],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"[API] Playlist error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load playlist: {str(e)}")


@app.post("/api/set_pause")
def set_pause(data: dict):
    """Called by the player JS when the video is paused."""
    _pause_store["time"] = data.get("time")
    return {"ok": True}


@app.get("/api/get_pause")
def get_pause():
    """Returns the most recently stored pause time."""
    return {"time": _pause_store["time"]}


@app.get("/api/health")
def health_check():
    """Health check endpoint."""
    deepgram_key = os.getenv("DEEPGRAM_API_KEY")
    groq_key = os.getenv("GROQ_API_KEY")
    return {
        "status": "healthy",
        "deepgram_configured": bool(deepgram_key),
        "groq_configured": bool(groq_key),
    }
