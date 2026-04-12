"""
Groq LLM service: summarization and RAG-based Q&A for YouTube transcripts.
Uses Groq's ultra-fast inference with Llama 3.3 70B.
"""

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


def summarize_transcript(segments: list[dict], pause_time: float) -> str:
    """
    Generate a concise summary of transcript segments up to the pause point.

    Args:
        segments: List of {"text": str, "start": float, "end": float}
        pause_time: The time (in seconds) where the user paused

    Returns:
        Summary string
    """
    # Filter segments up to the pause point
    watched_segments = [s for s in segments if s["start"] <= pause_time]

    if not watched_segments:
        return "No transcript content found up to this point."

    # Build transcript text with timestamps
    transcript_lines = []
    for seg in watched_segments:
        ts = _format_timestamp(seg["start"])
        transcript_lines.append(f"[{ts}] {seg['text']}")

    transcript_text = "\n".join(transcript_lines)
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
    # Filter segments up to the pause point
    watched_segments = [s for s in segments if s["start"] <= pause_time]

    if not watched_segments:
        return "There's no transcript content available up to this point to answer your question."

    # Build transcript text
    transcript_lines = []
    for seg in watched_segments:
        ts = _format_timestamp(seg["start"])
        transcript_lines.append(f"[{ts}] {seg['text']}")

    transcript_text = "\n".join(transcript_lines)
    time_str = _format_timestamp(pause_time)

    system_prompt = (
        "You are an AI tutor helping a student understand a YouTube video. "
        "Answer the student's question based ONLY on the transcript content provided. "
        "If the answer is not clearly found in the transcript, say so honestly. "
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
