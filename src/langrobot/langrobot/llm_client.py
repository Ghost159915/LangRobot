"""
llm_client.py — pure Python Ollama HTTP client for lang_node.

No ROS2 imports. Public interface: parse_command(text) -> dict.
All failures return {"action": "error", "reason": "..."} — never raises.
"""
import json
import logging

import requests

logger = logging.getLogger(__name__)

VALID_COLOURS = {"red", "blue", "green", "yellow", "white"}
VALID_ACTIONS = {"pick_and_place"}
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "gemma4"
TIMEOUT_S = 30

_PROMPT_TEMPLATE = """\
You control a robot arm. There are 5 blocks on a table: red, blue, green, yellow, white.

Respond ONLY with a JSON object in this exact format:
{{"action": "pick_and_place", "object": "<colour>", "target": "<colour>"}}

User command: {user_text}"""

_RETRY_PREFIX = (
    "Your previous response was not valid JSON. "
    "Respond with JSON only, no explanation.\n\n"
)


def _call_ollama(prompt: str) -> str:
    """Send prompt to Ollama, return the response text. Raises on HTTP/network error."""
    resp = requests.post(
        OLLAMA_URL,
        json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
        timeout=TIMEOUT_S,
    )
    resp.raise_for_status()
    return resp.json()["response"].strip()


def _validate(data: dict) -> bool:
    """Return True if data matches the Phase 3 task schema."""
    if data.get("action") not in VALID_ACTIONS:
        return False
    if data.get("object") not in VALID_COLOURS:
        return False
    if data.get("target") not in VALID_COLOURS:
        return False
    if data["object"] == data["target"]:
        return False
    return True


def _parse(raw: str) -> dict | None:
    """Try to parse raw string as JSON task dict. Returns dict on success, None on failure."""
    # Strip markdown code fences if present
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        inner = lines[1:]
        if inner and inner[-1].strip().startswith("```"):
            inner = inner[:-1]
        text = "\n".join(inner)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    if not _validate(data):
        return None
    return data


def parse_command(text: str) -> dict:
    """
    Send text to Ollama, parse the response into a validated task dict.

    Retries once with a stricter prompt if the first response is invalid.
    Returns {"action": "error", "reason": "..."} if both attempts fail.
    Never raises.
    """
    base_prompt = _PROMPT_TEMPLATE.format(user_text=text)

    for attempt in range(2):
        prompt = (_RETRY_PREFIX + base_prompt) if attempt == 1 else base_prompt
        try:
            raw = _call_ollama(prompt)
        except Exception as exc:
            # Network errors return immediately — no point retrying with a stricter prompt.
            logger.error("Ollama request failed (attempt %d): %s", attempt + 1, exc)
            return {"action": "error", "reason": f"Ollama request failed: {exc}"}

        result = _parse(raw)
        if result is not None:
            return result

        logger.warning(
            "Attempt %d: could not parse response: %r", attempt + 1, raw
        )

    return {
        "action": "error",
        "reason": "Could not parse LLM response after retry",
    }
