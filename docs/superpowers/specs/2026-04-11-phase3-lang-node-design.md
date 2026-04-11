# Phase 3 — `lang_node` Design Spec
**Date:** 2026-04-11
**Status:** Approved

---

## Overview

`lang_node` is the language interface for LangRobot. It receives a plain English command on `/task_input`, sends it to a local Gemma 4 model via Ollama, and publishes a structured JSON task spec on `/task_command` for downstream nodes to consume.

**Phase 3 gate:** `ros2 topic echo /task_command` shows valid JSON for any English block-manipulation command.

---

## Architecture

Two files plus one test file:

```
src/langrobot/langrobot/
├── llm_client.py       ← pure Python: Ollama HTTP, prompt, JSON parsing, retry logic
└── lang_node.py        ← ROS2 node: subscribe /task_input, call llm_client, publish /task_command

tests/
└── test_lang_node.py   ← unit tests for llm_client (mocked HTTP, no ROS2 needed)
```

`llm_client.py` has zero ROS2 imports. Its public interface is one function:

```python
def parse_command(text: str) -> dict:
    """
    Send text to Ollama, parse the response into a task dict.
    Returns a valid task dict or {"action": "error", "reason": "..."}.
    Never raises — all failures are captured in the error dict.
    """
```

`lang_node.py` is a thin ROS2 wrapper (~50 lines): subscribe to `/task_input`, call `parse_command`, publish result to `/task_command`.

---

## ROS2 Topics

| Topic | Type | Direction |
|-------|------|-----------|
| `/task_input` | `std_msgs/String` | external → `lang_node` |
| `/task_command` | `std_msgs/String` (JSON) | `lang_node` → `planner_node` (Phase 5) |

**Note:** Stdin input (typing commands directly into the node terminal) is explicitly deferred. The `/task_input` topic is the only input mechanism for now. Stdin support can be added later by running a background thread in `lang_node.py` that publishes to `/task_input` internally.

---

## JSON Schema

### Success

```json
{"action": "pick_and_place", "object": "red", "target": "blue"}
```

| Field | Valid values | Notes |
|-------|-------------|-------|
| `action` | `"pick_and_place"` | Only action for Phase 3; extend in later phases |
| `object` | `"red"`, `"blue"`, `"green"`, `"yellow"`, `"white"` | Block to move |
| `target` | `"red"`, `"blue"`, `"green"`, `"yellow"`, `"white"` | Destination block |

### Error

```json
{"action": "error", "reason": "Could not parse LLM response after retry"}
```

Published when both LLM attempts fail to produce valid JSON. The node logs the raw Ollama output alongside this message.

---

## LLM Integration

**Model:** Gemma 4 via Ollama (`localhost:11434`)

**Transport:** Direct HTTP (`requests.post`) to Ollama REST API — no LangChain, no extra framework.

> **Decision:** LangChain was specified in the original design doc but is deferred. Direct Ollama HTTP is simpler, has fewer dependencies, and is easier to debug. LangChain (or a similar framework) should be revisited when chains, memory, or tool-use are needed (Phase 6+). See Decision Log.

> **Future:** When the prompt stabilises and needs tuning without code changes, extract it to a config file (e.g. `config/prompts/task_prompt.txt`). This is Option 3 from the architecture discussion — deferred until the prompt is stable.

### Prompt (first attempt)

```
You control a robot arm. There are 5 blocks on a table: red, blue, green, yellow, white.

Respond ONLY with a JSON object in this exact format:
{"action": "pick_and_place", "object": "<colour>", "target": "<colour>"}

User command: {user_text}
```

### Prompt (retry — second attempt)

Same prompt, with this line prepended:

```
Your previous response was not valid JSON. Respond with JSON only, no explanation.
```

---

## Error Handling & Retry Flow

```
/task_input received
    → attempt 1: send prompt → parse JSON
        ✓ success → publish to /task_command
        ✗ fail    → attempt 2: stricter prompt → parse JSON
            ✓ success → publish to /task_command
            ✗ fail    → log raw Ollama output
                      → publish {"action": "error", "reason": "..."} to /task_command
                      → wait for next /task_input
```

Failure conditions handled:
- Response is not valid JSON
- Response is valid JSON but missing required fields (`action`, `object`, `target`)
- `object` or `target` value is not one of the five known colours
- Ollama HTTP request raises `ConnectionError` or times out
- Ollama returns HTTP error status

The node never crashes on LLM failure. All failures produce an error dict.

---

## Testing

All tests in `tests/test_lang_node.py`. Use `unittest.mock.patch` on `requests.post` — no Ollama process needed, no ROS2 node spin needed.

| Test | What it verifies |
|------|-----------------|
| `test_valid_response` | Ollama returns good JSON → parsed correctly |
| `test_retry_on_bad_json` | First response is garbage → retries → second succeeds |
| `test_error_after_two_failures` | Both attempts fail → returns `{"action": "error", ...}` |
| `test_unknown_colour` | Ollama returns unknown colour → treated as parse failure |
| `test_ollama_unavailable` | `requests.post` raises `ConnectionError` → returns error dict |

---

## Phase 3 Verification Gate

**Unit tests (Mac, no Linux needed):**
```bash
PYTHONPATH=src/langrobot python3 -m pytest tests/test_lang_node.py -v
```

**Integration test (Linux PC):**

Terminal 1:
```bash
source install/setup.bash
ros2 launch langrobot langrobot.launch.py
```

Terminal 2:
```bash
source install/setup.bash
ros2 topic echo /task_command
```

Terminal 3:
```bash
source install/setup.bash
ros2 topic pub --once /task_input std_msgs/msg/String "data: 'move the red block onto the blue block'"
```

**Expected output in Terminal 2:**
```
data: '{"action": "pick_and_place", "object": "red", "target": "blue"}'
```

**Pass criteria:**
1. All unit tests pass
2. `/task_command` shows valid JSON within ~3 seconds of publishing to `/task_input`
3. English commands with typos or variations still produce valid JSON

---

## Decision Log Additions

| Date | Decision | Reason | Deferred |
|------|----------|--------|---------|
| 2026-04-11 | Direct Ollama HTTP over LangChain | Simpler, fewer deps, easier to debug for Phase 3 scope | LangChain when chains/memory/tool-use needed (Phase 6+) |
| 2026-04-11 | `/task_input` topic only (no stdin) | Clean ROS2 architecture; launch compatibility | Stdin via background thread, add when convenient |
| 2026-04-11 | Prompt hardcoded in `llm_client.py` | Prompt not yet stable; YAGNI | Extract to `config/prompts/` when prompt stabilises |
| 2026-04-11 | Minimal schema: action/object/target only | Build incrementally; get basics working first | Richer schema (confidence, spatial coords, multi-step) in later phases |
