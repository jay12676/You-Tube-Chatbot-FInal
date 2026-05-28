"""
Vision service: analyze a video's on-screen visuals with Gemini.

Given a YouTube URL, returns a timestamped list of visual segments describing
what appears on screen. Purely additive: any failure (missing key, unsupported
video, API error) returns an empty list so the rest of the app is unaffected.
"""

import asyncio
import json
import os
import re

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))

VISION_MODEL = os.getenv("GEMINI_VISION_MODEL", "gemini-2.0-flash")

_PROMPT = (
    "You are analyzing a video to capture what is shown ON SCREEN (not spoken). "
    "Identify the meaningful visual moments: new slides, diagrams, charts, "
    "important on-screen text, code, and notable demonstrations or scenes. "
    "Do NOT report every second — only when the visible content meaningfully changes.\n\n"
    "Return ONLY a JSON array (no prose, no markdown fences). Each element:\n"
    '{"timestamp": "MM:SS", "end": "MM:SS", '
    '"label": "slide|diagram|chart|text|code|demo|scene", '
    '"description": "one concise sentence about what is shown"}\n'
    "Use HH:MM:SS only if the video is over an hour. If nothing visual is "
    "worth noting, return []."
)


def _ts_to_seconds(ts: str) -> float | None:
    """Convert 'MM:SS' or 'HH:MM:SS' to float seconds. None if unparseable."""
    if not isinstance(ts, str) or not ts.strip():
        return None
    parts = ts.strip().split(":")
    try:
        nums = [int(p) for p in parts]
    except ValueError:
        return None
    if len(nums) == 2:
        m, s = nums
        return float(m * 60 + s)
    if len(nums) == 3:
        h, m, s = nums
        return float(h * 3600 + m * 60 + s)
    return None


def _extract_json_array(raw: str) -> str:
    """Strip markdown fences / surrounding prose and return the JSON array text."""
    text = raw.strip()
    # Remove ```json ... ``` or ``` ... ``` fences
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    return text


def _parse_visual_response(raw: str) -> list[dict]:
    """
    Parse Gemini's raw text into clean visual segments.

    Returns [{"start": float, "end": float, "label": str, "description": str}],
    sorted by start. Drops malformed rows. Returns [] if nothing parses.
    """
    try:
        data = json.loads(_extract_json_array(raw))
    except (json.JSONDecodeError, ValueError):
        return []
    if not isinstance(data, list):
        return []

    segments: list[dict] = []
    for row in data:
        if not isinstance(row, dict):
            continue
        start = _ts_to_seconds(row.get("timestamp", ""))
        if start is None:
            continue
        end = _ts_to_seconds(row.get("end", "")) or start
        if end < start:
            end = start
        segments.append({
            "start": start,
            "end": end,
            "label": str(row.get("label", "scene")).strip() or "scene",
            "description": str(row.get("description", "")).strip(),
        })
    segments.sort(key=lambda s: s["start"])
    return segments
