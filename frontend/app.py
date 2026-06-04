"""
Streamlit Frontend — YouTube Smart Chatbot
Features: URL input → Video embed → Real-time synced transcript
          → Pause to get AI Summary → Ask doubts via RAG chatbot
"""

import os
import streamlit as st
import requests
import json
import re
from dotenv import load_dotenv

# Load .env from the frontend/ directory (same folder as this file)
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# ---------- Page Config ----------
st.set_page_config(
    page_title="YouTube Smart Chatbot",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8011")

# ---------- Custom CSS ----------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

    /* Global */
    .stApp {
        background: linear-gradient(160deg, #0a0a1a 0%, #111128 40%, #0d1b2a 100%);
        font-family: 'Inter', sans-serif;
    }

    /* Header area */
    .main-header {
        text-align: center;
        padding: 2rem 0 1rem;
    }
    .main-header h1 {
        font-size: 2.8rem;
        font-weight: 800;
        background: linear-gradient(135deg, #6366f1, #8b5cf6, #a78bfa);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.3rem;
        letter-spacing: -0.5px;
    }
    .main-header p {
        color: #94a3b8;
        font-size: 1.05rem;
        font-weight: 400;
    }

    /* URL Input container */
    .url-container {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 16px;
        padding: 1.5rem 2rem;
        margin: 1rem auto 2rem;
        max-width: 900px;
        backdrop-filter: blur(20px);
    }

    /* Streamlit input overrides */
    .stTextInput > div > div > input {
        background: rgba(255,255,255,0.06) !important;
        border: 1px solid rgba(99,102,241,0.3) !important;
        border-radius: 12px !important;
        color: #e2e8f0 !important;
        font-size: 1rem !important;
        padding: 0.8rem 1.2rem !important;
        font-family: 'Inter', sans-serif !important;
    }
    .stTextInput > div > div > input:focus {
        border-color: #6366f1 !important;
        box-shadow: 0 0 0 3px rgba(99,102,241,0.15) !important;
    }
    .stTextInput > div > div > input::placeholder {
        color: #64748b !important;
    }
    .stTextInput label {
        color: #cbd5e1 !important;
        font-weight: 500 !important;
        font-size: 0.95rem !important;
    }

    /* Button overrides */
    .stButton > button {
        background: linear-gradient(135deg, #6366f1, #7c3aed) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 0.7rem 2.5rem !important;
        font-size: 1rem !important;
        font-weight: 600 !important;
        font-family: 'Inter', sans-serif !important;
        letter-spacing: 0.3px;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 15px rgba(99,102,241,0.3) !important;
    }
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 25px rgba(99,102,241,0.45) !important;
    }

    /* Video info card */
    .video-info-card {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 16px;
        padding: 1.2rem 1.5rem;
        margin-bottom: 1.5rem;
        backdrop-filter: blur(20px);
    }
    .video-info-card h3 {
        color: #e2e8f0;
        margin: 0 0 0.4rem;
        font-size: 1.2rem;
        font-weight: 600;
    }
    .video-info-card .meta {
        color: #94a3b8;
        font-size: 0.85rem;
    }
    .video-info-card .meta span {
        margin-right: 1.2rem;
    }
    .lang-badge {
        display: inline-block;
        background: rgba(99,102,241,0.15);
        color: #a78bfa;
        padding: 2px 10px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 500;
    }

    /* Spinner / status overrides */
    .stSpinner > div {
        border-top-color: #6366f1 !important;
    }

    /* Alerts and success */
    .stAlert {
        border-radius: 12px !important;
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Divider */
    .custom-divider {
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(99,102,241,0.3), transparent);
        margin: 1.5rem 0;
    }

    /* ===== Summary Card ===== */
    .summary-card {
        background: linear-gradient(135deg, rgba(99,102,241,0.08), rgba(139,92,246,0.06));
        border: 1px solid rgba(99,102,241,0.2);
        border-radius: 16px;
        padding: 1.5rem 2rem;
        margin: 1rem 0;
        backdrop-filter: blur(20px);
        animation: fadeSlideIn 0.5s ease-out;
    }
    .summary-card h3 {
        color: #a78bfa;
        font-size: 1.1rem;
        font-weight: 600;
        margin-bottom: 0.8rem;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .summary-card .summary-content {
        color: #cbd5e1;
        font-size: 0.95rem;
        line-height: 1.7;
    }
    .summary-card .summary-content ul {
        margin: 0.5rem 0;
        padding-left: 1.2rem;
    }
    .summary-card .summary-content li {
        margin-bottom: 0.3rem;
    }
    .summary-meta {
        margin-top: 0.8rem;
        padding-top: 0.6rem;
        border-top: 1px solid rgba(255,255,255,0.06);
        font-size: 0.8rem;
        color: #64748b;
        display: flex;
        gap: 1.5rem;
    }

    @keyframes fadeSlideIn {
        from { opacity: 0; transform: translateY(15px); }
        to { opacity: 1; transform: translateY(0); }
    }

    /* ===== Chat UI ===== */
    .chat-container {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 16px;
        padding: 1.2rem 1.5rem;
        margin: 1rem 0;
        backdrop-filter: blur(20px);
    }
    .chat-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 1rem;
        padding-bottom: 0.8rem;
        border-bottom: 1px solid rgba(255,255,255,0.06);
    }
    .chat-header h3 {
        color: #e2e8f0;
        font-size: 1.05rem;
        font-weight: 600;
        margin: 0;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .chat-header .hint {
        font-size: 0.8rem;
        color: #64748b;
    }

    /* Chat messages */
    .chat-messages {
        max-height: 400px;
        overflow-y: auto;
        padding: 0.5rem 0;
        margin-bottom: 1rem;
    }
    .chat-messages::-webkit-scrollbar {
        width: 5px;
    }
    .chat-messages::-webkit-scrollbar-track {
        background: rgba(255,255,255,0.02);
    }
    .chat-messages::-webkit-scrollbar-thumb {
        background: rgba(99,102,241,0.3);
        border-radius: 3px;
    }

    .chat-msg {
        margin-bottom: 1rem;
        animation: msgAppear 0.3s ease-out;
    }
    .chat-msg.user {
        text-align: right;
    }
    .chat-msg .msg-bubble {
        display: inline-block;
        max-width: 85%;
        padding: 0.8rem 1.2rem;
        border-radius: 14px;
        font-size: 0.93rem;
        line-height: 1.6;
        text-align: left;
    }
    .chat-msg.user .msg-bubble {
        background: linear-gradient(135deg, #6366f1, #7c3aed);
        color: white;
        border-bottom-right-radius: 4px;
    }
    .chat-msg.assistant .msg-bubble {
        background: rgba(255,255,255,0.06);
        border: 1px solid rgba(255,255,255,0.08);
        color: #cbd5e1;
        border-bottom-left-radius: 4px;
    }
    .chat-msg .msg-label {
        font-size: 0.72rem;
        color: #64748b;
        margin-bottom: 4px;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    @keyframes msgAppear {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }

    /* Number input overrides */
    .stNumberInput > div > div > input {
        background: rgba(255,255,255,0.06) !important;
        border: 1px solid rgba(99,102,241,0.3) !important;
        border-radius: 12px !important;
        color: #e2e8f0 !important;
        font-family: 'JetBrains Mono', monospace !important;
    }
    .stNumberInput label {
        color: #cbd5e1 !important;
        font-weight: 500 !important;
    }

    /* Chat input area */
    .stChatInput > div {
        background: rgba(255,255,255,0.06) !important;
        border: 1px solid rgba(99,102,241,0.3) !important;
        border-radius: 12px !important;
    }
    .stChatInput textarea {
        color: #e2e8f0 !important;
        font-family: 'Inter', sans-serif !important;
    }

    /* ===== Playlist Queue ===== */
    .playlist-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 0.8rem;
    }
    .playlist-header h3 { color: #e2e8f0; font-size: 1rem; font-weight: 600; margin: 0; }
    .playlist-header .pl-count { color: #64748b; font-size: 0.82rem; font-family: 'JetBrains Mono', monospace; }
    .playlist-queue {
        display: flex;
        gap: 12px;
        overflow-x: auto;
        padding: 4px 2px 10px;
    }
    .playlist-queue::-webkit-scrollbar { height: 4px; }
    .playlist-queue::-webkit-scrollbar-track { background: rgba(255,255,255,0.02); }
    .playlist-queue::-webkit-scrollbar-thumb { background: rgba(99,102,241,0.3); border-radius: 2px; }
    .pl-card {
        flex-shrink: 0;
        width: 155px;
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.07);
        border-radius: 10px;
        overflow: hidden;
        position: relative;
    }
    .pl-card.pl-current { border-color: #6366f1; box-shadow: 0 0 14px rgba(99,102,241,0.3); }
    .pl-card.pl-done { opacity: 0.4; }
    .pl-card img { width: 100%; aspect-ratio: 16/9; object-fit: cover; display: block; }
    .pl-card-body { padding: 6px 8px 8px; }
    .pl-card-title {
        font-size: 11px; color: #94a3b8; line-height: 1.4;
        display: -webkit-box; -webkit-line-clamp: 2;
        -webkit-box-orient: vertical; overflow: hidden;
    }
    .pl-card.pl-current .pl-card-title { color: #f1f5f9; }
    .pl-card-dur { font-size: 10px; color: #64748b; margin-top: 3px; font-family: 'JetBrains Mono', monospace; }
    .pl-badge {
        position: absolute; top: 4px; right: 4px;
        background: rgba(0,0,0,0.65); color: #f1f5f9;
        font-size: 10px; padding: 2px 5px; border-radius: 4px;
    }
    .pl-badge-playing { background: rgba(99,102,241,0.85) !important; }
</style>
""", unsafe_allow_html=True)


# ---------- Helper Functions ----------

def extract_video_id(url: str) -> str | None:
    """Extract YouTube video ID from URL."""
    patterns = [
        r'(?:v=)([0-9A-Za-z_-]{11})',
        r'(?:youtu\.be/)([0-9A-Za-z_-]{11})',
        r'(?:embed/)([0-9A-Za-z_-]{11})',
        r'(?:shorts/)([0-9A-Za-z_-]{11})',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def format_duration(seconds: int) -> str:
    """Format seconds to MM:SS or HH:MM:SS."""
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def render_visual_timeline(visual_segments: list, query: str = "") -> None:
    """Render the searchable visual timeline as Streamlit markdown rows."""
    q = query.strip().lower()
    shown = 0
    for v in visual_segments:
        text = f"{v.get('label', '')} {v.get('description', '')}".lower()
        if q and q not in text:
            continue
        ts = format_duration(int(v.get("start", 0)))
        label = str(v.get("label", "scene")).replace("<", "&lt;").replace(">", "&gt;")
        desc = str(v.get("description", "")).replace("<", "&lt;").replace(">", "&gt;")
        st.markdown(
            f"<div style='padding:6px 0; border-bottom:1px solid #1e293b;'>"
            f"<span style='color:#a78bfa; font-weight:600;'>⏱ {ts}</span> "
            f"<span style='color:#38bdf8; font-size:0.8rem; text-transform:uppercase;'>{label}</span><br>"
            f"<span style='color:#cbd5e1; font-size:0.9rem;'>{desc}</span></div>",
            unsafe_allow_html=True,
        )
        shown += 1
    if shown == 0:
        st.caption("No visual moments match your search." if q else "No visual content detected for this video.")


def is_playlist_url(url: str) -> bool:
    """
    Return True if the URL points to a real YouTube playlist.

    Auto-generated "radio"/"mix" lists (IDs starting with RD, e.g. RDOikOgyDeOQw
    appended when you click a song) are NOT real playlists — yt-dlp can't
    enumerate them — so we treat those as a single video instead.
    """
    if not url or "list=" not in url:
        return False
    if not ("youtube.com" in url or "youtu.be" in url):
        return False
    match = re.search(r"list=([A-Za-z0-9_-]+)", url)
    if match and match.group(1).startswith("RD"):
        return False  # radio / auto-mix — handle as a single video
    return True


def build_player_html(video_id: str, segments: list, title: str, words: list = None, backend_url: str = "http://localhost:8011") -> str:
    """
    Build a self-contained HTML page with side-by-side layout:
    - LEFT: YouTube video player + status bar
    - RIGHT: Live transcript that reveals each word as it is spoken
    Sends postMessage to Streamlit parent on pause with current timestamp.
    """
    segments_json = json.dumps(segments)
    words_json = json.dumps(words or [])

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                font-family: 'Inter', sans-serif;
                background: transparent;
                color: #e2e8f0;
                overflow: hidden;
            }}

            /* ===== Side-by-side Layout ===== */
            .main-layout {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 20px;
                height: 100vh;
                padding: 8px;
            }}

            /* Left Column: Video + Status */
            .left-column {{
                display: flex;
                flex-direction: column;
                gap: 12px;
                min-width: 0;
            }}

            /* Right Column: Transcript */
            .right-column {{
                display: flex;
                flex-direction: column;
                gap: 10px;
                min-width: 0;
                min-height: 0;
            }}

            /* Video Player */
            .player-section {{
                width: 100%;
                border-radius: 14px;
                overflow: hidden;
                box-shadow: 0 8px 32px rgba(0,0,0,0.4);
                background: #000;
                flex-shrink: 0;
            }}
            .player-section iframe {{
                width: 100%;
                aspect-ratio: 16/9;
                display: block;
            }}

            /* Status Bar */
            .status-bar {{
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 10px 16px;
                background: rgba(255,255,255,0.04);
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 10px;
                font-size: 12px;
                flex-shrink: 0;
            }}
            .status-indicator {{
                display: flex;
                align-items: center;
                gap: 8px;
            }}
            .status-dot {{
                width: 8px;
                height: 8px;
                border-radius: 50%;
                background: #22c55e;
                animation: pulse-dot 2s ease-in-out infinite;
            }}
            .status-dot.paused {{
                background: #f59e0b;
                animation: none;
            }}
            @keyframes pulse-dot {{
                0%, 100% {{ opacity: 1; }}
                50% {{ opacity: 0.4; }}
            }}
            .current-time {{
                font-family: 'JetBrains Mono', monospace;
                color: #a78bfa;
                font-weight: 500;
                font-size: 13px;
            }}

            /* Transcript Panel */
            .transcript-panel {{
                background: rgba(255,255,255,0.03);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 14px;
                display: flex;
                flex-direction: column;
                overflow: hidden;
                flex: 1;
                min-height: 0;
            }}

            .transcript-header {{
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 14px 18px 10px;
                flex-shrink: 0;
                border-bottom: 1px solid rgba(255,255,255,0.06);
            }}
            .transcript-header h3 {{
                font-size: 15px;
                font-weight: 600;
                color: #cbd5e1;
                display: flex;
                align-items: center;
                gap: 8px;
            }}
            .segment-counter {{
                font-size: 11px;
                color: #64748b;
                font-family: 'JetBrains Mono', monospace;
            }}

            /* Waiting message */
            .waiting-msg {{
                text-align: center;
                padding: 50px 20px;
                color: #64748b;
                font-size: 14px;
                animation: waiting-pulse 2.5s ease-in-out infinite;
            }}
            .waiting-msg .icon {{
                font-size: 2.2rem;
                margin-bottom: 10px;
            }}
            @keyframes waiting-pulse {{
                0%, 100% {{ opacity: 0.5; }}
                50% {{ opacity: 1; }}
            }}

            .transcript-container {{
                padding: 6px 8px;
                overflow-y: auto;
                scroll-behavior: smooth;
                flex: 1;
                min-height: 0;
            }}
            /* Scrollbar styling */
            .transcript-container::-webkit-scrollbar {{
                width: 5px;
            }}
            .transcript-container::-webkit-scrollbar-track {{
                background: rgba(255,255,255,0.02);
                border-radius: 3px;
            }}
            .transcript-container::-webkit-scrollbar-thumb {{
                background: rgba(99,102,241,0.3);
                border-radius: 3px;
            }}
            .transcript-container::-webkit-scrollbar-thumb:hover {{
                background: rgba(99,102,241,0.5);
            }}

            /* Word-row — hidden until its first word is spoken */
            .word-row {{
                display: none;
                gap: 10px;
                padding: 7px 12px;
                border-radius: 8px;
                margin-bottom: 2px;
                border-left: 3px solid transparent;
                transition: background 0.3s ease, border-color 0.3s ease;
            }}
            .word-row.row-visible {{
                display: flex;
                align-items: baseline;
            }}
            .word-row.row-active {{
                background: rgba(99, 102, 241, 0.12);
                border-left-color: #6366f1;
                box-shadow: 0 0 20px rgba(99,102,241,0.08);
            }}
            .word-row.row-past {{
                opacity: 0.55;
                border-left-color: rgba(99,102,241,0.12);
            }}

            .timestamp {{
                font-family: 'JetBrains Mono', monospace;
                font-size: 11px;
                color: #6366f1;
                font-weight: 500;
                min-width: 46px;
                padding-top: 2px;
                flex-shrink: 0;
            }}
            .word-row.row-active .timestamp {{
                color: #a78bfa;
            }}

            .words-content {{
                font-size: 13px;
                line-height: 1.7;
                color: #94a3b8;
                flex: 1;
            }}
            .word-row.row-active .words-content {{
                color: #f1f5f9;
            }}

            /* Each word starts invisible; fades in when revealed */
            .w {{
                display: inline;
                opacity: 0;
                transition: opacity 0.18s ease;
            }}
            .w.w-shown {{
                opacity: 1;
            }}

            /* No transcript fallback */
            .no-transcript {{
                text-align: center;
                padding: 40px 20px;
                color: #64748b;
            }}

            /* Pause notification banner */
            .pause-banner {{
                display: none;
                align-items: center;
                justify-content: center;
                gap: 10px;
                padding: 10px 16px;
                background: linear-gradient(135deg, rgba(99,102,241,0.15), rgba(139,92,246,0.1));
                border: 1px solid rgba(99,102,241,0.3);
                border-radius: 10px;
                font-size: 13px;
                color: #a78bfa;
                animation: fadeSlideIn 0.4s ease-out;
                flex-shrink: 0;
            }}
            .pause-banner.visible {{
                display: flex;
            }}
            @keyframes fadeSlideIn {{
                from {{ opacity: 0; transform: translateY(-10px); }}
                to {{ opacity: 1; transform: translateY(0); }}
            }}
        </style>
    </head>
    <body>
        <div class="main-layout">
            <!-- LEFT: Video + Status -->
            <div class="left-column">
                <div class="player-section">
                    <div id="player"></div>
                </div>
                <div class="status-bar">
                    <div class="status-indicator">
                        <div class="status-dot paused" id="statusDot"></div>
                        <span id="statusText" style="color: #94a3b8;">Press play — transcript will appear live</span>
                    </div>
                    <div class="current-time" id="currentTime">00:00</div>
                </div>
                <div class="pause-banner" id="pauseBanner">
                    ⏸️ Video paused at <strong id="pauseTimeDisplay">00:00</strong> — Use the chatbot below to get a summary & ask questions!
                </div>
            </div>

            <!-- RIGHT: Transcript -->
            <div class="right-column">
                <div class="transcript-panel">
                    <div class="transcript-header">
                        <h3>📝 Live Transcript</h3>
                        <span class="segment-counter" id="segmentCounter">0 / {len(words or segments)} words</span>
                    </div>
                    <div class="transcript-container" id="transcriptContainer">
                        <div class="waiting-msg" id="waitingMsg">
                            <div class="icon">▶️</div>
                            <div>Play the video — transcript appears here live</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- YouTube IFrame API -->
        <script>
            var tag = document.createElement('script');
            tag.src = "https://www.youtube.com/iframe_api";
            var firstScriptTag = document.getElementsByTagName('script')[0];
            firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);

            var player;
            var segments = {segments_json};
            var words = {words_json};

            // Group words into display rows of 8 for layout; fall back to segment-based rows
            var ROW_SIZE = 8;
            var rows = [];          // {{words:[...], start, end, rowIndex}}
            var wordMeta = [];      // per-word: {{start, rowIndex, wordIndex}}

            (function buildRows() {{
                var source = words.length > 0 ? null : segments; // prefer words
                if (words.length > 0) {{
                    // Build rows from word-level data
                    for (var i = 0; i < words.length; i += ROW_SIZE) {{
                        var chunk = words.slice(i, i + ROW_SIZE);
                        rows.push({{
                            words: chunk,
                            start: chunk[0].start,
                            end: chunk[chunk.length - 1].end
                        }});
                    }}
                    words.forEach(function(w, i) {{
                        wordMeta.push({{start: w.start, rowIndex: Math.floor(i / ROW_SIZE), wordIndex: i}});
                    }});
                }} else {{
                    // Fall back: YouTube captions are PHRASE-level (one start time per
                    // line, no per-word timing). Faking even word-by-word timing makes
                    // words drift out of sync with speech, so instead we reveal the whole
                    // line together the instant its real caption start time arrives — like
                    // normal subtitles. This stays accurately synced at the line level.
                    // (For true per-word sync, use the "Precise word-sync" toggle, which
                    // re-runs with Deepgram and provides real word timestamps above.)
                    segments.forEach(function(seg, si) {{
                        var toks = seg.text.split(' ').filter(function(t){{ return t.length > 0; }});
                        var spreadEnd = (si < segments.length - 1)
                            ? segments[si + 1].start
                            : seg.end;
                        // All words in the line share the line's real start time → they
                        // appear together exactly when the line is spoken.
                        var fakeWords = toks.map(function(t) {{
                            return {{ word: t, start: seg.start, end: spreadEnd }};
                        }});
                        var globalOffset = wordMeta.length;
                        fakeWords.forEach(function(w, wi) {{
                            wordMeta.push({{start: w.start, rowIndex: si, wordIndex: globalOffset + wi}});
                        }});
                        rows.push({{words: fakeWords, start: seg.start, end: spreadEnd}});
                    }});
                }}
            }})();

            var lastActiveRow = -1;
            var userScrolling = false;
            var userScrollTimeout = null;
            var lastPauseTime = 0;

            function onYouTubeIframeAPIReady() {{
                player = new YT.Player('player', {{
                    videoId: '{video_id}',
                    playerVars: {{
                        'autoplay': 0,
                        'modestbranding': 1,
                        'rel': 0,
                        'fs': 1,
                        'cc_load_policy': 0,
                        'enablejsapi': 1,
                        'origin': window.location.ancestorOrigins
                            ? (window.location.ancestorOrigins[0] || window.location.origin)
                            : window.location.origin,
                    }},
                    events: {{
                        'onReady': onPlayerReady,
                        'onStateChange': onPlayerStateChange,
                    }}
                }});
            }}

            function onPlayerReady(event) {{
                buildRowElements();
                setupScrollDetection();
                startTracking();
            }}

            function setupScrollDetection() {{
                var container = document.getElementById('transcriptContainer');
                container.addEventListener('wheel', function() {{
                    userScrolling = true;
                    clearTimeout(userScrollTimeout);
                    userScrollTimeout = setTimeout(function() {{ userScrolling = false; }}, 4000);
                }});
                container.addEventListener('touchmove', function() {{
                    userScrolling = true;
                    clearTimeout(userScrollTimeout);
                    userScrollTimeout = setTimeout(function() {{ userScrolling = false; }}, 4000);
                }});
            }}

            function onPlayerStateChange(event) {{
                var dot = document.getElementById('statusDot');
                var text = document.getElementById('statusText');
                var banner = document.getElementById('pauseBanner');

                if (event.data === YT.PlayerState.PLAYING) {{
                    dot.className = 'status-dot';
                    text.textContent = 'Playing — transcript syncing live...';
                    text.style.color = '#22c55e';
                    banner.className = 'pause-banner';
                    var wm = document.getElementById('waitingMsg');
                    if (wm) wm.style.display = 'none';
                }} else if (event.data === YT.PlayerState.PAUSED) {{
                    var currentTime = player.getCurrentTime();
                    lastPauseTime = currentTime;
                    dot.className = 'status-dot paused';
                    text.textContent = 'Paused';
                    text.style.color = '#f59e0b';
                    document.getElementById('pauseTimeDisplay').textContent = formatTime(currentTime);
                    banner.className = 'pause-banner visible';
                    window.parent.postMessage({{ type: 'youtube_paused', time: currentTime }}, '*');
                    // Store pause time in backend so Streamlit can read it without postMessage
                    fetch('{backend_url}/api/set_pause', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify({{time: currentTime}})
                    }}).catch(function() {{}});
                }} else if (event.data === YT.PlayerState.ENDED) {{
                    dot.className = 'status-dot paused';
                    text.textContent = 'Video ended';
                    text.style.color = '#94a3b8';
                    banner.className = 'pause-banner';
                    window.parent.postMessage({{ type: 'youtube_ended', time: player.getDuration() }}, '*');
                }}
            }}

            function buildRowElements() {{
                var container = document.getElementById('transcriptContainer');
                if (rows.length === 0) {{
                    container.innerHTML = '<div class="no-transcript">No transcript found.</div>';
                    return;
                }}
                rows.forEach(function(row, ri) {{
                    var rowDiv = document.createElement('div');
                    rowDiv.className = 'word-row';
                    rowDiv.id = 'row-' + ri;

                    var ts = document.createElement('span');
                    ts.className = 'timestamp';
                    ts.textContent = formatTime(row.start);
                    rowDiv.appendChild(ts);

                    var content = document.createElement('span');
                    content.className = 'words-content';

                    var globalBase = 0;
                    for (var r = 0; r < ri; r++) {{ globalBase += rows[r].words.length; }}

                    row.words.forEach(function(w, wi) {{
                        var wSpan = document.createElement('span');
                        wSpan.className = 'w';
                        wSpan.id = 'w-' + (globalBase + wi);
                        // Add space before every word except the first
                        wSpan.textContent = (wi === 0 ? '' : ' ') + escapeText(w.word);
                        content.appendChild(wSpan);
                    }});

                    rowDiv.appendChild(content);

                    // Click → seek to this row's start time
                    rowDiv.addEventListener('click', (function(start) {{
                        return function() {{
                            if (player && player.seekTo) {{
                                player.seekTo(start, true);
                                player.playVideo();
                                userScrolling = false;
                                clearTimeout(userScrollTimeout);
                            }}
                        }};
                    }})(row.start));

                    container.appendChild(rowDiv);
                }});
            }}

            function startTracking() {{
                setInterval(function() {{
                    if (!player || !player.getCurrentTime) return;
                    var time = player.getCurrentTime();
                    updateTimeDisplay(time);
                    syncTranscript(time);
                }}, 100); // 100 ms for smooth word-by-word feel
            }}

            function syncTranscript(time) {{
                var activeRow = -1;
                var shownWords = 0;

                // Reveal individual words and track the active row
                wordMeta.forEach(function(wm) {{
                    var el = document.getElementById('w-' + wm.wordIndex);
                    if (!el) return;
                    if (time >= wm.start) {{
                        if (!el.classList.contains('w-shown')) {{
                            el.classList.add('w-shown');
                            // Hide waiting message on first word reveal
                            var waiting = document.getElementById('waitingMsg');
                            if (waiting) waiting.style.display = 'none';
                        }}
                        shownWords++;
                    }}
                }});

                // Update row visibility and active/past state
                rows.forEach(function(row, ri) {{
                    var rowEl = document.getElementById('row-' + ri);
                    if (!rowEl) return;
                    if (time >= row.start) {{
                        rowEl.classList.add('row-visible');
                        if (time >= row.start && time <= row.end + 0.5) {{
                            rowEl.className = 'word-row row-visible row-active';
                            activeRow = ri;
                        }} else if (time > row.end + 0.5) {{
                            rowEl.className = 'word-row row-visible row-past';
                        }}
                    }}
                }});

                // Auto-scroll to active row when it changes
                if (activeRow >= 0 && activeRow !== lastActiveRow && !userScrolling) {{
                    lastActiveRow = activeRow;
                    var activeEl = document.getElementById('row-' + activeRow);
                    if (activeEl) {{
                        activeEl.scrollIntoView({{ behavior: 'smooth', block: 'nearest' }});
                    }}
                }} else if (activeRow >= 0) {{
                    lastActiveRow = activeRow;
                }}

                var counter = document.getElementById('segmentCounter');
                counter.textContent = shownWords + ' / ' + wordMeta.length + ' words';
            }}

            function updateTimeDisplay(time) {{
                document.getElementById('currentTime').textContent = formatTime(time);
            }}

            function formatTime(seconds) {{
                var h = Math.floor(seconds / 3600);
                var m = Math.floor((seconds % 3600) / 60);
                var s = Math.floor(seconds % 60);
                if (h > 0) return String(h) + ':' + String(m).padStart(2,'0') + ':' + String(s).padStart(2,'0');
                return String(m).padStart(2,'0') + ':' + String(s).padStart(2,'0');
            }}

            function escapeText(text) {{
                var d = document.createElement('div');
                d.textContent = text;
                return d.innerHTML;
            }}
        </script>
    </body>
    </html>
    """


def render_chat_messages(chat_history: list) -> str:
    """Render chat messages as HTML."""
    if not chat_history:
        return ""

    html_parts = []
    for msg in chat_history:
        role = msg["role"]
        content = msg["content"]
        # Escape HTML characters for safety
        content_escaped = content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        # Convert newlines and markdown-style bullets to HTML
        content_html = content_escaped.replace("\n", "<br>")

        if role == "user":
            label = "You"
            html_parts.append(f'''
                <div class="chat-msg user">
                    <div class="msg-label">{label}</div>
                    <div class="msg-bubble">{content_html}</div>
                </div>
            ''')
        else:
            label = "AI Tutor"
            html_parts.append(f'''
                <div class="chat-msg assistant">
                    <div class="msg-label">{label}</div>
                    <div class="msg-bubble">{content_html}</div>
                </div>
            ''')

    return "".join(html_parts)


# ---------- Session State Initialization ----------
if "transcript_data" not in st.session_state:
    st.session_state.transcript_data = None
if "video_id" not in st.session_state:
    st.session_state.video_id = None
if "video_title" not in st.session_state:
    st.session_state.video_title = None
if "video_duration" not in st.session_state:
    st.session_state.video_duration = 0
if "detected_language" not in st.session_state:
    st.session_state.detected_language = None
if "is_loading" not in st.session_state:
    st.session_state.is_loading = False
if "full_text" not in st.session_state:
    st.session_state.full_text = ""
if "words_data" not in st.session_state:
    st.session_state.words_data = []
if "visual_segments" not in st.session_state:
    st.session_state.visual_segments = []
if "notes_pdf" not in st.session_state:
    st.session_state.notes_pdf = None

# RAG Chatbot state
if "pause_time" not in st.session_state:
    st.session_state.pause_time = None
if "summary" not in st.session_state:
    st.session_state.summary = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "chatbot_active" not in st.session_state:
    st.session_state.chatbot_active = False
if "summary_loading" not in st.session_state:
    st.session_state.summary_loading = False

# Playlist state
if "playlist_videos" not in st.session_state:
    st.session_state.playlist_videos = []
if "playlist_index" not in st.session_state:
    st.session_state.playlist_index = 0
if "is_playlist" not in st.session_state:
    st.session_state.is_playlist = False
if "playlist_title" not in st.session_state:
    st.session_state.playlist_title = ""
if "pending_next" not in st.session_state:
    st.session_state.pending_next = False


# ---------- UI Layout ----------

# Header
st.markdown("""
<div class="main-header">
    <h1>🎬 YouTube Smart Chatbot</h1>
    <p>Paste a YouTube video or playlist URL • Real-time transcription • Pause for AI summary & ask doubts</p>
</div>
""", unsafe_allow_html=True)

# URL Input Section
col_input, col_btn = st.columns([4, 1])

with col_input:
    url_input = st.text_input(
        "🔗 YouTube URL",
        placeholder="https://www.youtube.com/watch?v=...  or  playlist?list=...",
        label_visibility="collapsed",
        key="url_input",
    )

with col_btn:
    _btn_label = "📋 Load Playlist" if is_playlist_url(url_input) else "🚀 Transcribe"
    load_clicked = st.button(_btn_label, use_container_width=True, key="load_btn")


# ---------- Handle Load & Transcribe ----------

# Determine the URL to transcribe this render cycle
_url_to_transcribe: str | None = None

if load_clicked and url_input:
    if is_playlist_url(url_input):
        # ── Playlist: fetch metadata, then transcribe first video ─────────────
        st.session_state.is_playlist = True
        st.session_state.transcript_data = None
        st.session_state.pause_time = None
        st.session_state.summary = None
        st.session_state.chat_history = []
        st.session_state.chatbot_active = False
        with st.spinner("📋 Fetching playlist…"):
            try:
                pl_resp = requests.post(
                    f"{BACKEND_URL}/api/playlist",
                    json={"url": url_input},
                    timeout=60,
                )
                if pl_resp.status_code == 200:
                    pl_data = pl_resp.json()
                    st.session_state.playlist_videos = pl_data["videos"]
                    st.session_state.playlist_title = pl_data["playlist_title"]
                    st.session_state.playlist_index = 0
                    if pl_data["videos"]:
                        _url_to_transcribe = pl_data["videos"][0]["url"]
                    else:
                        st.error("❌ Playlist is empty or no videos could be loaded.")
                else:
                    st.error(f"❌ Playlist error: {pl_resp.json().get('detail', 'Unknown')}")
            except requests.exceptions.ConnectionError:
                st.error(f"❌ Cannot connect to backend at {BACKEND_URL}. Make sure FastAPI is running.")
            except Exception as e:
                st.error(f"❌ Could not load playlist: {str(e)}")
    else:
        # ── Single video ──────────────────────────────────────────────────────
        st.session_state.is_playlist = False
        st.session_state.playlist_videos = []
        st.session_state.playlist_title = ""
        _url_to_transcribe = url_input

elif st.session_state.pending_next:
    # ── Playlist skip / next (triggered by the Next button) ──────────────────
    st.session_state.pending_next = False
    idx = st.session_state.playlist_index
    if 0 <= idx < len(st.session_state.playlist_videos):
        _url_to_transcribe = st.session_state.playlist_videos[idx]["url"]

# ── Common transcription block ────────────────────────────────────────────────
if _url_to_transcribe:
    video_id = extract_video_id(_url_to_transcribe)
    if not video_id:
        st.error("❌ Invalid YouTube URL. Please paste a valid YouTube video link.")
    else:
        st.session_state.is_loading = True
        st.session_state.transcript_data = None
        st.session_state.visual_segments = []
        st.session_state.notes_pdf = None
        st.session_state.pause_time = None
        st.session_state.summary = None
        st.session_state.chat_history = []
        st.session_state.chatbot_active = False
        try:
            requests.post(f"{BACKEND_URL}/api/set_pause", json={"time": None}, timeout=2)
        except Exception:
            pass

        progress_container = st.empty()
        with progress_container.container():
            st.markdown("---")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.empty().info("⏳ **Step 1/3**: Extracting video info...")
            with col2:
                st.empty().markdown("⬜ **Step 2/3**: Downloading audio...")
            with col3:
                st.empty().markdown("⬜ **Step 3/3**: Transcribing in parallel chunks...")

        try:
            with st.spinner(""):
                response = requests.post(
                    f"{BACKEND_URL}/api/transcribe",
                    json={"url": _url_to_transcribe},
                    timeout=600,
                )

            if response.status_code == 200:
                data = response.json()
                try:
                    requests.post(f"{BACKEND_URL}/api/set_pause", json={"time": None}, timeout=3)
                except Exception:
                    pass
                st.session_state.transcript_data = data["segments"]
                st.session_state.words_data = data.get("words", [])
                st.session_state.visual_segments = data.get("visual_segments", [])
                st.session_state.video_id = data["video_id"]
                st.session_state.video_title = data["title"]
                st.session_state.video_duration = data["duration"]
                st.session_state.detected_language = data["detected_language"]
                st.session_state.full_text = data["full_text"]
                st.session_state.is_loading = False
                progress_container.empty()
                st.rerun()
            else:
                error_detail = response.json().get("detail", "Unknown error")
                st.error(f"❌ Backend error: {error_detail}")
                st.session_state.is_loading = False

        except requests.exceptions.ConnectionError:
            st.error(f"❌ Cannot connect to backend at {BACKEND_URL}. Make sure FastAPI is running.")
            st.session_state.is_loading = False
        except requests.exceptions.Timeout:
            st.error("❌ Request timed out. The video might be too long.")
            st.session_state.is_loading = False
        except Exception as e:
            st.error(f"❌ Unexpected error: {str(e)}")
            st.session_state.is_loading = False


# ---------- Playlist Queue Panel ----------
if st.session_state.is_playlist and st.session_state.playlist_videos:
    videos = st.session_state.playlist_videos
    idx = st.session_state.playlist_index
    total = len(videos)

    cards_html = ""
    for i, v in enumerate(videos):
        if i < idx:
            status_class = "pl-card pl-done"
            badge = '<span class="pl-badge">✓</span>'
        elif i == idx:
            status_class = "pl-card pl-current"
            badge = '<span class="pl-badge pl-badge-playing">▶ Now</span>'
        else:
            status_class = "pl-card"
            badge = f'<span class="pl-badge">{i + 1}</span>'

        dur_str = format_duration(v["duration"]) if v.get("duration") else "--:--"
        title_safe = v["title"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        thumb = v.get("thumbnail") or f"https://i.ytimg.com/vi/{v['id']}/mqdefault.jpg"

        cards_html += f"""
        <div class="{status_class}">
            {badge}
            <img src="{thumb}" alt="" loading="lazy">
            <div class="pl-card-body">
                <div class="pl-card-title">{title_safe}</div>
                <div class="pl-card-dur">{dur_str}</div>
            </div>
        </div>"""

    st.markdown(f"""
    <div class="video-info-card">
        <div class="playlist-header">
            <h3>📋 {st.session_state.playlist_title.replace('<','&lt;').replace('>','&gt;')}</h3>
            <span class="pl-count">Video {idx + 1} / {total}</span>
        </div>
        <div class="playlist-queue">{cards_html}</div>
    </div>
    """, unsafe_allow_html=True)


# ---------- Display Video + Transcript ----------
# Render once a transcription has completed — transcript_data is a list (possibly
# empty for a no-speech video that only has visual segments), so check `is not None`
# rather than truthiness, otherwise visuals-only videos would show a blank page.
if st.session_state.transcript_data is not None and st.session_state.video_id:

    # Video info card
    duration_str = format_duration(st.session_state.video_duration)
    lang = st.session_state.detected_language or "auto"
    num_segments = len(st.session_state.transcript_data)

    st.markdown(f"""
    <div class="video-info-card">
        <h3>{st.session_state.video_title}</h3>
        <div class="meta">
            <span>⏱️ {duration_str}</span>
            <span>📝 {num_segments} segments</span>
            <span class="lang-badge">🌐 {lang.upper()}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Playlist navigation bar ───────────────────────────────────────────────
    if st.session_state.is_playlist and st.session_state.playlist_videos:
        _pl_idx = st.session_state.playlist_index
        _pl_videos = st.session_state.playlist_videos
        _next_idx = _pl_idx + 1
        _, _nav_col, _ = st.columns([1, 2, 1])
        with _nav_col:
            if _next_idx < len(_pl_videos):
                _next_title = _pl_videos[_next_idx]["title"]
                if len(_next_title) > 38:
                    _next_title = _next_title[:38] + "…"
                if st.button(f"⏭️ Next → {_next_title}", use_container_width=True, key="next_video_btn"):
                    st.session_state.playlist_index = _next_idx
                    st.session_state.pending_next = True
                    st.session_state.transcript_data = None
                    st.session_state.visual_segments = []
                    st.session_state.pause_time = None
                    st.session_state.summary = None
                    st.session_state.chat_history = []
                    st.session_state.chatbot_active = False
                    st.rerun()
            else:
                st.success("✅ Playlist complete — all videos watched!")

    # Build and render the player + transcript HTML
    html = build_player_html(
        video_id=st.session_state.video_id,
        segments=st.session_state.transcript_data,
        words=st.session_state.words_data,
        title=st.session_state.video_title,
        backend_url=BACKEND_URL,
    )

    # Side-by-side layout: height needs video (aspect 16:9 at ~half width) + status bar
    component_height = 550
    import streamlit.components.v1 as components
    components.html(html, height=component_height, scrolling=False)

    # Divider
    st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)

    # ==========================================
    # VISUAL TIMELINE SECTION
    # ==========================================
    if st.session_state.get("visual_segments"):
        # Auto-expand when the video has no spoken transcript, so a visuals-only
        # video surfaces its content instead of looking empty.
        _no_speech = not st.session_state.transcript_data
        with st.expander(
            f"📺 Visual Timeline ({len(st.session_state.visual_segments)} moments)",
            expanded=_no_speech,
        ):
            vt_query = st.text_input(
                "Search what's on screen",
                key="visual_search",
                placeholder="e.g. diagram, Newton, code...",
                label_visibility="collapsed",
            )
            render_visual_timeline(st.session_state.visual_segments, vt_query)
        st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)

    # ==========================================
    # EXPORT STUDY NOTES (PDF)
    # ==========================================
    st.markdown("#### 📄 Export Study Notes")
    st.caption("Download a PDF study pack — the slides/diagrams shown on screen, paired with notes. Something YouTube never gives you.")
    _scope_choice = st.radio(
        "Coverage",
        ["Whole video", "Up to pause point"],
        horizontal=True,
        key="notes_scope",
        label_visibility="collapsed",
    )
    if st.button("📄 Generate Study Notes PDF", key="gen_notes_btn"):
        _scope = "pause" if _scope_choice == "Up to pause point" else "full"
        # For "Up to pause point" use the LIVE pause time stored in the backend
        # (set by the player whenever the video is paused). Don't rely on
        # st.session_state.pause_time — that is only populated after the user
        # clicks "Get AI Summary", so paused-then-export would otherwise send 0
        # and the backend would fall back to the whole video.
        _pause_t = float(st.session_state.pause_time or 0)
        if _scope == "pause":
            try:
                _pr = requests.get(f"{BACKEND_URL}/api/get_pause", timeout=3)
                _live_pause = _pr.json().get("time") if _pr.status_code == 200 else None
                if _live_pause and _live_pause > 0:
                    _pause_t = float(_live_pause)
            except Exception:
                pass
            if _pause_t <= 0:
                st.warning("⏸️ Pause the video first, then choose “Up to pause point.” "
                           "No pause detected — using the whole video instead.")
        with st.spinner("📝 Building your study pack (grabbing slides + writing notes)…"):
            try:
                _resp = requests.post(
                    f"{BACKEND_URL}/api/export_notes",
                    json={
                        "url": f"https://www.youtube.com/watch?v={st.session_state.video_id}",
                        "segments": st.session_state.transcript_data or [],
                        "visual_segments": st.session_state.get("visual_segments", []),
                        "scope": _scope,
                        "pause_time": _pause_t,
                    },
                    timeout=240,
                )
                if _resp.status_code == 200:
                    st.session_state.notes_pdf = _resp.content
                else:
                    st.session_state.notes_pdf = None
                    try:
                        _detail = _resp.json().get("detail", "Unknown error")
                    except Exception:
                        _detail = "Unknown error"
                    st.error(f"❌ Export failed: {_detail}")
            except Exception as e:
                st.session_state.notes_pdf = None
                st.error(f"❌ Could not connect to backend: {e}")

    if st.session_state.get("notes_pdf"):
        # Name the file after the video title (not the raw video ID), so the
        # download is recognisable. Strip characters Windows/macOS disallow in
        # filenames and trim length.
        _raw_title = (st.session_state.get("video_title") or "study notes").strip()
        _safe_title = re.sub(r'[\\/:*?"<>|]+', "", _raw_title)   # drop illegal chars
        _safe_title = re.sub(r"\s+", " ", _safe_title).strip()[:80] or "study notes"
        _notes_filename = f"Study Notes - {_safe_title}.pdf"
        st.download_button(
            "⬇️ Download Study Notes PDF",
            data=st.session_state.notes_pdf,
            file_name=_notes_filename,
            mime="application/pdf",
            key="dl_notes_btn",
        )

    st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)

    # ==========================================
    # RAG CHATBOT SECTION
    # ==========================================

    # --- Auto-detect pause time from backend, then offer summary ---
    try:
        pause_resp = requests.get(f"{BACKEND_URL}/api/get_pause", timeout=3)
        detected_pause = pause_resp.json().get("time") if pause_resp.status_code == 200 else None
    except Exception:
        detected_pause = None

    if detected_pause and detected_pause > 0:
        pt_display = format_duration(int(detected_pause))
        st.markdown(f"""
        <div style="text-align:center; margin: 0.5rem 0 1rem;">
            <span style="color:#a78bfa; font-size:0.95rem;">
                ⏸️ Video paused at <strong style="color:#f1f5f9;">{pt_display}</strong>
            </span>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="text-align:center; margin:0.5rem 0 1rem;">
            <span style="color:#64748b; font-size:0.9rem;">
                ⏸️ Pause the video — then click below to get an AI summary &amp; ask questions
            </span>
        </div>
        """, unsafe_allow_html=True)

    col_btn_center = st.columns([1, 2, 1])[1]
    with col_btn_center:
        summary_clicked = st.button(
            "🤖 Get AI Summary",
            use_container_width=True,
            key="summary_btn",
        )

    # On click, re-fetch pause time (catches pauses that happened before button render)
    if summary_clicked:
        try:
            pause_resp = requests.get(f"{BACKEND_URL}/api/get_pause", timeout=3)
            detected_pause = pause_resp.json().get("time") if pause_resp.status_code == 200 else None
        except Exception:
            detected_pause = None

    input_pause_time = detected_pause or 0

    # Handle summary generation
    if summary_clicked and input_pause_time == 0:
        st.warning("⏸️ Please pause the video first, then click Get AI Summary.")

    if summary_clicked and input_pause_time > 0:
        st.session_state.pause_time = input_pause_time
        st.session_state.summary_loading = True
        st.session_state.chatbot_active = True
        st.session_state.summary = None

        try:
            with st.spinner("🤖 Generating AI summary..."):
                resp = requests.post(
                    f"{BACKEND_URL}/api/summarize",
                    json={
                        "segments": st.session_state.transcript_data,
                        "pause_time": float(input_pause_time),
                        "visual_segments": st.session_state.get("visual_segments", []),
                    },
                    timeout=60,
                )

            if resp.status_code == 200:
                data = resp.json()
                st.session_state.summary = data["summary"]
                st.session_state.summary_loading = False
                st.rerun()
            else:
                error_detail = resp.json().get("detail", "Unknown error")
                st.error(f"❌ Summary error: {error_detail}")
                st.session_state.summary_loading = False

        except requests.exceptions.ConnectionError:
            st.error("❌ Cannot connect to backend.")
            st.session_state.summary_loading = False
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
            st.session_state.summary_loading = False


    # --- Summary + Chat in a fragment so video player never rerenders ---
    @st.fragment
    def summary_and_chat():
        # Display summary
        if st.session_state.summary and st.session_state.pause_time:
            pt = st.session_state.pause_time
            pt_str = format_duration(int(pt))
            segments_used = len([s for s in st.session_state.transcript_data if s["start"] <= pt])
            st.markdown(f"""
            <div class="summary-card">
                <h3>📋 AI Summary — watched up to {pt_str}</h3>
                <div class="summary-content">{st.session_state.summary.replace(chr(10), '<br>')}</div>
                <div class="summary-meta">
                    <span>📝 {segments_used} segments analyzed</span>
                    <span>⏱️ Content: 0:00 → {pt_str}</span>
                    <span>🤖 Powered by Groq Llama 3.3</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # Chat interface
        if st.session_state.chatbot_active and st.session_state.summary:
            st.markdown("#### 💬 Ask Doubts About This Video")

            # Show previous messages
            for msg in st.session_state.chat_history:
                with st.chat_message(msg["role"]):
                    st.write(msg["content"])

            # Input — only this fragment reruns on submit, video is untouched
            user_question = st.chat_input("Type your question here...")

            if user_question:
                st.session_state.chat_history.append({"role": "user", "content": user_question})

                with st.spinner("Thinking..."):
                    try:
                        resp = requests.post(
                            f"{BACKEND_URL}/api/chat",
                            json={
                                "question": user_question,
                                "segments": st.session_state.transcript_data,
                                "pause_time": float(st.session_state.pause_time),
                                "chat_history": st.session_state.chat_history[:-1],
                                "visual_segments": st.session_state.get("visual_segments", []),
                            },
                            timeout=60,
                        )
                        answer = resp.json()["answer"] if resp.status_code == 200 else f"Error: {resp.json().get('detail','')}"
                    except Exception as e:
                        answer = f"Could not connect to backend: {str(e)}"

                st.session_state.chat_history.append({"role": "assistant", "content": answer})
                # Rerun only this fragment — video player is untouched
                st.rerun()

            if st.session_state.chat_history:
                if st.button("🗑️ Clear Chat", key="clear_chat_btn"):
                    st.session_state.chat_history = []
                    st.rerun()

    summary_and_chat()

    # Full transcript expander — below the chatbot
    st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)
    with st.expander("📄 Full Transcript Text", expanded=False):
        if st.session_state.transcript_data:
            st.text_area(
                "Complete transcript",
                value=st.session_state.get("full_text", ""),
                height=300,
                label_visibility="collapsed",
            )
        else:
            st.info(
                "🎬 This video has no spoken audio — its content is visual. "
                "See the **📺 Visual Timeline** above for what appears on screen."
            )

elif not st.session_state.is_loading:
    # Empty state
    st.markdown("""
    <div style="text-align: center; padding: 4rem 2rem; color: #475569;">
        <div style="font-size: 4rem; margin-bottom: 1rem;">🎬</div>
        <h3 style="color: #64748b; font-weight: 500; margin-bottom: 0.5rem;">
            Paste a YouTube URL to get started
        </h3>
        <p style="color: #475569; font-size: 0.95rem;">
            Supports videos in any language • Powered by Deepgram Nova-2 & Groq AI
        </p>
    </div>
    """, unsafe_allow_html=True)
