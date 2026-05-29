"""
FastAPI backend for YoTube Smart Chatbot.
Handles video audio extraction, Deepgram transcription,
and RAG-based summarization & Q&A via Groq.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import asyncio
import io
import os
import shutil
import sys
import tempfile

# Fix Windows console encoding for Unicode (Hindi, emoji, etc.)
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from backend.services.youtube_service import (
    extract_video_info, download_audio, download_video, extract_playlist_info,
)
from backend.services.deepgram_service import transcribe_audio
from backend.services.caption_service import get_youtube_captions
from backend.services.groq_service import summarize_transcript, chat_with_context, generate_study_notes
from backend.services.vision_service import analyze_video_visuals
from backend.services.notes_service import extract_frames, build_study_notes_pdf

# Load environment variables from backend/.env
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

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


class VisualSegment(BaseModel):
    start: float
    end: float
    label: str
    description: str


class TranscriptResponse(BaseModel):
    video_id: str
    title: str
    duration: int
    thumbnail: str
    segments: list[TranscriptSegment]
    words: list[WordTimestamp] = []
    visual_segments: list[VisualSegment] = []
    full_text: str
    detected_language: str


class SummarizeRequest(BaseModel):
    segments: list[dict]
    pause_time: float
    visual_segments: list[dict] = []


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
    visual_segments: list[dict] = []


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


class ExportNotesRequest(BaseModel):
    url: str
    segments: list[dict] = []
    visual_segments: list[dict] = []
    scope: str = "full"          # "full" | "pause"
    pause_time: float = 0.0


# In-memory pause store (per-server, good enough for single-user dev use)
_pause_store: dict = {"time": None}


# ---------- Routes ----------

@app.get("/")
def root():
    return {"status": "ok", "message": "YouTube Smart Chatbot API is running 🚀"}


async def _get_audio_transcript(url: str, video_info: dict) -> dict:
    """
    Existing audio pipeline, extracted so it can run concurrently with vision.
    Tries YouTube captions first; falls back to downloading audio + Deepgram.
    Blocking calls are off-loaded to threads so they run in parallel with vision.
    """
    print("[API] Trying YouTube captions first...")
    transcript_result = await asyncio.to_thread(get_youtube_captions, video_info["id"])

    if transcript_result:
        print(f"[API] YouTube captions found: {len(transcript_result['segments'])} segments")
        return transcript_result

    print("[API] No YouTube captions — falling back to Deepgram...")
    audio_path = await asyncio.to_thread(download_audio, url, video_info["id"])
    print(f"[API] Audio saved: {audio_path}")

    transcript_result = await transcribe_audio(audio_path)
    print(f"[API] Deepgram transcription: {len(transcript_result['segments'])} segments, "
          f"{len(transcript_result.get('words', []))} words")

    try:
        if os.path.exists(audio_path):
            os.remove(audio_path)
            print(f"[API] Cleaned up audio file: {audio_path}")
    except Exception as cleanup_err:
        print(f"[API] Warning: Could not delete audio file: {cleanup_err}")

    return transcript_result


@app.post("/api/transcribe", response_model=TranscriptResponse)
async def transcribe_video(request: VideoRequest):
    """
    Takes a YouTube URL, runs the audio transcript and Gemini visual analysis
    concurrently, and returns timestamped transcript + visual segments.
    """
    try:
        # Step 1: Kick off visual analysis immediately — it only needs the URL,
        # not the metadata, so it overlaps the (blocking) metadata + audio work.
        print(f"[API] Loading video: {request.url}")
        vision_task = asyncio.create_task(analyze_video_visuals(request.url, 0))

        # Step 2: Extract metadata + run the audio transcript pipeline.
        video_info = await asyncio.to_thread(extract_video_info, request.url)
        print(f"[API] Video: {video_info['title']} (duration: {video_info['duration']}s)", flush=True)
        transcript_result = await _get_audio_transcript(request.url, video_info)

        # Step 3: Collect the visual analysis (already running in parallel).
        visual_segments = await vision_task

        # Step 3: Return combined response
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
            visual_segments=[
                VisualSegment(**v) for v in visual_segments
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

        summary = summarize_transcript(
            request.segments, request.pause_time, request.visual_segments
        )
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
            visual_segments=request.visual_segments,
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


@app.post("/api/export_notes")
async def export_notes(request: ExportNotesRequest):
    """
    Build a downloadable PDF study pack: on-screen slides/diagrams (screenshots)
    paired with distilled notes, scoped to the whole video or up to the pause point.
    Screenshots are best-effort — if video download/ffmpeg fails, the PDF is text-only.

    The Groq notes call and the video-download + frame-extraction are independent,
    so they run concurrently to cut wall-clock time.
    """
    try:
        video_info = await asyncio.to_thread(extract_video_info, request.url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not load video: {str(e)}")

    # Determine scope
    pause = request.pause_time if (request.scope == "pause" and request.pause_time and request.pause_time > 0) else None
    if pause is None:
        scope_label = "Whole video"
    else:
        scope_label = f"Up to {int(pause // 60)}:{int(pause % 60):02d}"

    # Visual moments in scope → screenshot timestamps
    scoped_visuals = request.visual_segments
    if pause is not None:
        scoped_visuals = [v for v in scoped_visuals if v.get("start", 0) <= pause]
    timestamps = [float(v["start"]) for v in scoped_visuals if "start" in v]

    tmp_dir = tempfile.mkdtemp(prefix="notes_frames_")
    state: dict = {"video_path": None}

    async def _build_frames() -> dict:
        if not timestamps:
            return {}
        try:
            vp = await asyncio.to_thread(download_video, request.url, video_info["id"])
            state["video_path"] = vp
            return await asyncio.to_thread(extract_frames, vp, timestamps, tmp_dir)
        except Exception as e:  # noqa: BLE001 - screenshots are best-effort
            print(f"[API] Study-notes screenshots unavailable ({type(e).__name__}: {e}) — text-only")
            return {}

    async def _build_notes() -> dict:
        return await asyncio.to_thread(
            generate_study_notes, request.segments, request.visual_segments, pause
        )

    try:
        # Screenshots (download + ffmpeg) and the Groq notes call run in parallel.
        frames, notes = await asyncio.gather(_build_frames(), _build_notes())
        pdf_bytes = await asyncio.to_thread(
            build_study_notes_pdf, notes, frames, video_info, scope_label
        )
    except Exception as e:
        print(f"[API] Export notes error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to build study notes: {str(e)}")
    finally:
        try:
            if state["video_path"] and os.path.exists(state["video_path"]):
                os.remove(state["video_path"])
        except Exception:
            pass
        shutil.rmtree(tmp_dir, ignore_errors=True)

    filename = f"study-notes-{video_info['id']}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


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
