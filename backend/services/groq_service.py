"""
Groq LLM service: summarization and RAG-based Q&A for YouTube transcripts.
Uses Groq's ultra-fast inference with Llama 3.3 70B.
"""

import json
import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))

# Model — override via GROQ_MODEL env var
MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")


def _get_client() -> Groq:
    """Create and return a Groq client."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not found in environment variables")
    return Groq(api_key=api_key)


def _format_timestamp(seconds: float) -> str:
    """Format seconds to MM:SS or HH:MM:SS."""
    h = int(seconds) // 3600
    m = (int(seconds) % 3600) // 60
    s = int(seconds) % 60
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def _build_context(
    segments: list[dict],
    visual_segments: list[dict] | None,
    pause_time: float,
) -> str:
    """
    Build a chronological transcript that interleaves spoken lines with
    on-screen visual descriptions, filtered to content up to pause_time.

    Spoken line:  "[MM:SS] text"
    Visual line:  "[VISUAL MM:SS] label: description"
    """
    rows: list[tuple[float, int, str]] = []
    for s in segments:
        if s["start"] <= pause_time:
            rows.append((s["start"], 0, f"[{_format_timestamp(s['start'])}] {s['text']}"))
    for v in (visual_segments or []):
        if v["start"] <= pause_time:
            ts = _format_timestamp(v["start"])
            rows.append((v["start"], 1, f"[VISUAL {ts}] {v['label']}: {v['description']}"))
    # sort by time; on tie, visual (1) after spoken (0)
    rows.sort(key=lambda r: (r[0], r[1]))
    return "\n".join(r[2] for r in rows)


def summarize_transcript(
    segments: list[dict],
    pause_time: float,
    visual_segments: list[dict] | None = None,
) -> str:
    """
    Generate a concise summary of transcript segments up to the pause point.

    Args:
        segments: List of {"text": str, "start": float, "end": float}
        pause_time: The time (in seconds) where the user paused

    Returns:
        Summary string
    """
    # Consider both spoken and on-screen visual content up to the pause point,
    # so visuals-only videos (no speech) still get summarised.
    watched_segments = [s for s in segments if s["start"] <= pause_time]
    watched_visuals = [v for v in (visual_segments or []) if v["start"] <= pause_time]

    if not watched_segments and not watched_visuals:
        return "No transcript content found up to this point."

    # Build chronological transcript (spoken + on-screen visuals)
    transcript_text = _build_context(segments, visual_segments, pause_time)
    time_str = _format_timestamp(pause_time)

    # Build the prompt
    system_prompt = (
        "You are an AI assistant helping a student understand a YouTube video. "
        "Your job is to provide clear, well-organized summaries that capture the "
        "key points and main ideas from the video content."
    )

    user_prompt = f"""The student has watched a YouTube video from the beginning up to {time_str}.

Here is the transcript of what they've watched so far:

{transcript_text}

Please provide a clear, concise summary of the key points covered so far:
- Use bullet points for main ideas
- Group related concepts together
- Highlight any important terms, definitions, or key takeaways
- Keep it educational and easy to understand
- Be concise but don't miss important points"""

    client = _get_client()
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
        max_tokens=1024,
    )

    return response.choices[0].message.content


def chat_with_context(
    question: str,
    segments: list[dict],
    pause_time: float,
    chat_history: list[dict] | None = None,
    visual_segments: list[dict] | None = None,
) -> str:
    """
    Answer a user question using transcript context (RAG-style).

    Args:
        question: The user's question
        segments: List of {"text": str, "start": float, "end": float}
        pause_time: The time (in seconds) where the user paused
        chat_history: Optional list of {"role": "user"|"assistant", "content": str}

    Returns:
        Answer string
    """
    # Consider both spoken and on-screen visual content up to the pause point.
    watched_segments = [s for s in segments if s["start"] <= pause_time]
    watched_visuals = [v for v in (visual_segments or []) if v["start"] <= pause_time]

    if not watched_segments and not watched_visuals:
        return "There's no transcript content available up to this point to answer your question."

    # Build chronological transcript (spoken + on-screen visuals)
    transcript_text = _build_context(segments, visual_segments, pause_time)
    time_str = _format_timestamp(pause_time)

    system_prompt = (
        "You are an AI tutor helping a student understand a YouTube video. "
        "The transcript contains spoken lines plus lines marked [VISUAL ...] that "
        "describe what is shown on screen (slides, diagrams, on-screen text). "
        "Answer the student's question based ONLY on this transcript content, using "
        "both spoken and visual information. If the answer is not clearly found, say so honestly. "
        "Write in plain, simple text like a helpful friend explaining something. "
        "Do NOT use markdown, asterisks, hashes, bullet dashes, or HTML tags. "
        "Use short paragraphs. If listing points, write them as: 1. First point. 2. Second point."
    )

    # Build messages
    messages = [{"role": "system", "content": system_prompt}]

    # Add context as the first user message
    context_msg = f"""Here is the transcript of the video the student has watched (from start to {time_str}):

{transcript_text}

Please answer questions based on this transcript content."""

    messages.append({"role": "user", "content": context_msg})
    messages.append({
        "role": "assistant",
        "content": "I've read through the transcript. I'm ready to answer your questions about the video content. Go ahead!",
    })

    # Add chat history
    if chat_history:
        for msg in chat_history:
            messages.append({
                "role": msg["role"],
                "content": msg["content"],
            })

    # Add the current question
    messages.append({"role": "user", "content": question})

    client = _get_client()
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.4,
        max_tokens=1024,
    )

    return response.choices[0].message.content


def generate_study_notes(
    segments: list[dict],
    visual_segments: list[dict] | None = None,
    pause_time: float | None = None,
) -> dict:
    """
    Produce a study-notes structure for the PDF export.

    Scope: if pause_time is set (>0), only content up to that point is used;
    otherwise the whole video is used.

    Returns:
        {
          "title": str,
          "key_takeaways": [str, ...],
          "sections": [{"timestamp": float, "heading": str, "note": str}, ...],
        }
    Sections correspond one-to-one to the (scoped) visual moments so each maps
    to an extracted screenshot. Falls back to a valid structure on any failure.
    """
    visual_segments = visual_segments or []
    segs = segments or []

    if pause_time and pause_time > 0:
        segs = [s for s in segs if s["start"] <= pause_time]
        scope_visuals = [v for v in visual_segments if v["start"] <= pause_time]
    else:
        scope_visuals = list(visual_segments)

    scope_visuals = sorted(scope_visuals, key=lambda v: float(v.get("start", 0)))
    segs_sorted = sorted(segs, key=lambda s: float(s.get("start", 0)))

    # Build "units" — the timeline points each section is anchored to.
    # Prefer the real visual moments (so sections match extracted frames); when a
    # video has no visuals but does have speech, chunk the transcript into topic
    # windows so we still produce proper text notes.
    units: list[dict] = []
    if scope_visuals:
        for i, v in enumerate(scope_visuals):
            w_start = float(v["start"])
            w_end = float(scope_visuals[i + 1]["start"]) if i + 1 < len(scope_visuals) else float("inf")
            spoken = " ".join(
                s.get("text", "") for s in segs_sorted
                if (w_start - 0.5) <= float(s.get("start", 0)) < w_end
            ).strip()
            units.append({
                "start": w_start,
                "heading": str(v.get("label", "scene")).title(),
                "shown_on_screen": v.get("description", ""),
                "narration": spoken,
            })
    elif segs_sorted:
        n_chunks = min(14, max(4, len(segs_sorted) // 8))
        size = max(1, len(segs_sorted) // n_chunks)
        for c in range(0, len(segs_sorted), size):
            chunk = segs_sorted[c:c + size]
            units.append({
                "start": float(chunk[0].get("start", 0)),
                "heading": "Topic",
                "shown_on_screen": "",
                "narration": " ".join(s.get("text", "") for s in chunk).strip(),
            })

    if not units:
        return {"title": "Study Notes", "key_takeaways": [], "sections": []}

    def _fallback() -> dict:
        return {
            "title": "Study Notes",
            "key_takeaways": [],
            "sections": [
                {
                    "timestamp": float(u["start"]),
                    "heading": u["heading"],
                    "note": (u["narration"][:500] or u["shown_on_screen"]),
                }
                for u in units
            ],
        }

    # Numbered list for the model. Keep narration compact — Groq free tier is
    # 12k tokens/min total, so the whole request must stay under that.
    moments = [
        {
            "index": i,
            "timestamp": round(float(u["start"]), 1),
            "shown_on_screen": u["shown_on_screen"],
            "narration": u["narration"][:500],
        }
        for i, u in enumerate(units)
    ]

    def _section_for(i: int, enrich: dict) -> dict:
        u = units[i]
        e = enrich.get(i, {})
        fallback_note = (u["narration"][:500] if u["narration"] else "") or u["shown_on_screen"]
        return {
            "timestamp": float(u["start"]),
            "heading": e.get("heading") or u["heading"],
            "note": e.get("note") or fallback_note,
        }

    system_prompt = (
        "You are an expert tutor writing study notes from a video. For each on-screen "
        "moment you are given the narration spoken during it and a description of what is "
        "shown. Write notes that TEACH the concept from the narration AND explain what the "
        "on-screen visual/diagram shows and what it indicates or means — not a description "
        "like 'an image appears'. Write notes a student can revise from. Respond with JSON only."
    )
    user_prompt = f"""The video's moments (each with its timestamp, what is shown on screen, and the narration spoken at that point):

{json.dumps(moments, ensure_ascii=False)}

Produce study notes as STRICT JSON with exactly this shape:
{{"title": "concise descriptive title", "key_takeaways": ["bullet", ...], "notes": [{{"index": <int>, "heading": "short topic heading", "note": "2-4 sentence study note"}}]}}

For each note:
- Explain the CONCEPT being taught at that moment, using the narration (the actual lesson — definitions, reasoning, formulas, steps).
- Then explain what the on-screen visual/diagram shows and what it indicates or demonstrates.
- Make it substantive and self-contained, like real revision notes — do NOT just say what appears on screen.

Rules:
- Provide EXACTLY ONE notes entry for EACH index above, reusing the same index integers. Do not merge or skip indices.
- key_takeaways: 4-6 crisp bullets capturing the most important points of the whole video.
- Output JSON only — no prose, no markdown fences."""

    try:
        client = _get_client()
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=3500,
            response_format={"type": "json_object"},
        )
        data = json.loads(response.choices[0].message.content)

        # Map the model's per-index enrichment back onto the real moments.
        enrich: dict[int, dict] = {}
        for n in data.get("notes", []) or []:
            try:
                idx = int(n.get("index"))
            except (TypeError, ValueError):
                continue
            enrich[idx] = {
                "heading": str(n.get("heading", "")).strip(),
                "note": str(n.get("note", "")).strip(),
            }

        sections = [_section_for(i, enrich) for i in range(len(units))]

        return {
            "title": str(data.get("title") or "Study Notes").strip() or "Study Notes",
            "key_takeaways": [str(k).strip() for k in (data.get("key_takeaways") or []) if str(k).strip()],
            "sections": sections,
        }

    except Exception as e:  # noqa: BLE001 - notes generation must not hard-fail
        print(f"[Notes] Groq notes generation failed ({type(e).__name__}: {e}); using fallback")
        return _fallback()
