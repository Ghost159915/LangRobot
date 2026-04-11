# Phase 3 — `lang_node` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `lang_node` — a ROS2 node that receives plain English commands on `/task_input`, queries Gemma 4 via Ollama HTTP, and publishes a validated JSON task spec on `/task_command`.

**Architecture:** `llm_client.py` is pure Python (no ROS2) — it handles Ollama HTTP, prompt construction, JSON validation, and retry logic. `lang_node.py` is a thin ROS2 wrapper that subscribes to `/task_input`, calls `llm_client.parse_command()`, and publishes the result to `/task_command`. All LLM logic is unit-testable without ROS2.

**Tech Stack:** Python 3.11, ROS2 Jazzy, `requests` (Ollama HTTP), `pytest` + `unittest.mock`.

---

## Environment context (read before starting)

- **Repo root = colcon workspace:** `~/Desktop/Projects/LangRobot/`
- **ROS2 package source:** `src/langrobot/langrobot/`
- **Build command:** `cd ~/Desktop/Projects/LangRobot && colcon build --symlink-install`
- **Source command:** `source install/setup.bash`
- **Run unit tests (no ROS2 needed):** `PYTHONPATH=src/langrobot python3 -m pytest tests/ -v`
- **Run tests on Mac:** same command works on Mac (no ROS2 or Ollama needed — all LLM calls are mocked)
- **Ollama endpoint:** `http://localhost:11434/api/generate` — model `gemma4`
- **`--symlink-install` means:** edits to Python files in `src/` take effect immediately without rebuilding

---

## File map

| Action | Path | Responsibility |
|--------|------|---------------|
| **Create** | `src/langrobot/langrobot/llm_client.py` | Ollama HTTP, prompt, JSON parse, retry — pure Python |
| **Create** | `src/langrobot/langrobot/lang_node.py` | ROS2 node: subscribe `/task_input`, publish `/task_command` |
| **Create** | `tests/test_lang_node.py` | Unit tests for `llm_client` (mocked HTTP) |
| **Modify** | `src/langrobot/setup.py` | Add `lang_node` console script entry point |
| **Modify** | `src/langrobot/launch/langrobot.launch.py` | Add `lang_node` to launch description |
| **Modify** | `docs/testing/phase2-verification-guide.md` | Add Phase 3 verification section (new file: `docs/testing/phase3-verification-guide.md`) |
| **Create** | `logs/phase3-test-log.md` | Template for Linux PC verification |

---

## Task 1: `llm_client.py` — core LLM logic + unit tests

**Files:**
- Create: `src/langrobot/langrobot/llm_client.py`
- Create: `tests/test_lang_node.py`

### Constants and schema

The five valid block colours and the only valid action for Phase 3:

```python
VALID_COLOURS = {"red", "blue", "green", "yellow", "white"}
VALID_ACTIONS = {"pick_and_place"}
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "gemma4"
```

### Prompt templates

```python
_PROMPT_TEMPLATE = """\
You control a robot arm. There are 5 blocks on a table: red, blue, green, yellow, white.

Respond ONLY with a JSON object in this exact format:
{{"action": "pick_and_place", "object": "<colour>", "target": "<colour>"}}

User command: {user_text}"""

_RETRY_PREFIX = (
    "Your previous response was not valid JSON. "
    "Respond with JSON only, no explanation.\n\n"
)
```

### Public interface

```python
def parse_command(text: str) -> dict:
    """
    Send text to Ollama, parse response into a task dict.
    Retries once with a stricter prompt on parse failure.
    Never raises — all failures return {"action": "error", "reason": "..."}.
    """
```

- [ ] **Step 1: Write the failing tests**

Create `tests/test_lang_node.py` with this exact content:

```python
import json
from unittest.mock import patch, MagicMock

import pytest

from langrobot.llm_client import parse_command


def _mock_response(text: str) -> MagicMock:
    """Build a mock requests.Response whose .json() returns Ollama's streaming format."""
    mock = MagicMock()
    mock.raise_for_status.return_value = None
    mock.json.return_value = {"response": text, "done": True}
    return mock


def test_valid_response():
    good_json = '{"action": "pick_and_place", "object": "red", "target": "blue"}'
    with patch("langrobot.llm_client.requests.post", return_value=_mock_response(good_json)):
        result = parse_command("move the red block onto the blue block")
    assert result == {"action": "pick_and_place", "object": "red", "target": "blue"}


def test_retry_on_bad_json():
    bad = "Sure! Here is the JSON: pick red block."
    good_json = '{"action": "pick_and_place", "object": "green", "target": "yellow"}'
    responses = [_mock_response(bad), _mock_response(good_json)]
    with patch("langrobot.llm_client.requests.post", side_effect=responses):
        result = parse_command("put green on yellow")
    assert result == {"action": "pick_and_place", "object": "green", "target": "yellow"}


def test_error_after_two_failures():
    bad = "I cannot do that."
    with patch("langrobot.llm_client.requests.post", return_value=_mock_response(bad)):
        result = parse_command("do something")
    assert result["action"] == "error"
    assert "reason" in result


def test_unknown_colour():
    bad_colour = '{"action": "pick_and_place", "object": "purple", "target": "blue"}'
    good_json = '{"action": "pick_and_place", "object": "white", "target": "blue"}'
    responses = [_mock_response(bad_colour), _mock_response(good_json)]
    with patch("langrobot.llm_client.requests.post", side_effect=responses):
        result = parse_command("move the white block to blue")
    assert result == {"action": "pick_and_place", "object": "white", "target": "blue"}


def test_ollama_unavailable():
    import requests as req
    with patch("langrobot.llm_client.requests.post", side_effect=req.ConnectionError("refused")):
        result = parse_command("move red to blue")
    assert result["action"] == "error"
    assert "reason" in result


def test_same_object_and_target_is_invalid():
    bad = '{"action": "pick_and_place", "object": "red", "target": "red"}'
    good_json = '{"action": "pick_and_place", "object": "red", "target": "blue"}'
    responses = [_mock_response(bad), _mock_response(good_json)]
    with patch("langrobot.llm_client.requests.post", side_effect=responses):
        result = parse_command("move red somewhere")
    assert result == {"action": "pick_and_place", "object": "red", "target": "blue"}
```

- [ ] **Step 2: Run tests — confirm they all fail**

```bash
PYTHONPATH=src/langrobot python3 -m pytest tests/test_lang_node.py -v
```

Expected: `ModuleNotFoundError: No module named 'langrobot.llm_client'`. All 6 tests must error or fail.

- [ ] **Step 3: Implement `llm_client.py`**

Create `src/langrobot/langrobot/llm_client.py` with this exact content:

```python
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
        text = "\n".join(lines[1:-1]) if len(lines) > 2 else text
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
    prompt = _PROMPT_TEMPLATE.format(user_text=text)

    for attempt in range(2):
        if attempt == 1:
            prompt = _RETRY_PREFIX + prompt
        try:
            raw = _call_ollama(prompt)
        except Exception as exc:
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
```

- [ ] **Step 4: Run tests — confirm all 6 pass**

```bash
PYTHONPATH=src/langrobot python3 -m pytest tests/test_lang_node.py -v
```

Expected:
```
tests/test_lang_node.py::test_valid_response PASSED
tests/test_lang_node.py::test_retry_on_bad_json PASSED
tests/test_lang_node.py::test_error_after_two_failures PASSED
tests/test_lang_node.py::test_unknown_colour PASSED
tests/test_lang_node.py::test_ollama_unavailable PASSED
tests/test_lang_node.py::test_same_object_and_target_is_invalid PASSED

6 passed
```

Also confirm all 17 existing tests still pass:

```bash
PYTHONPATH=src/langrobot python3 -m pytest tests/ -v
```

Expected: 23 passed (17 existing + 6 new).

- [ ] **Step 5: Commit**

```bash
git add src/langrobot/langrobot/llm_client.py tests/test_lang_node.py
git commit -m "feat: llm_client — Ollama HTTP client with retry and validation"
```

---

## Task 2: `lang_node.py` — ROS2 node wrapper

**Files:**
- Create: `src/langrobot/langrobot/lang_node.py`
- Modify: `src/langrobot/setup.py`

- [ ] **Step 1: Create `src/langrobot/langrobot/lang_node.py`**

```python
"""
lang_node.py — ROS2 node that bridges /task_input → Ollama → /task_command.

Subscribes to /task_input (std_msgs/String).
Publishes   to /task_command (std_msgs/String, JSON).
"""
import json

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

from langrobot.llm_client import parse_command


class LangNode(Node):
    def __init__(self):
        super().__init__('lang_node')

        self._sub = self.create_subscription(
            String,
            '/task_input',
            self._on_task_input,
            10,
        )
        self._pub = self.create_publisher(String, '/task_command', 10)

        self.get_logger().info(
            'lang_node ready — publish to /task_input to send a command'
        )

    def _on_task_input(self, msg: String) -> None:
        text = msg.data.strip()
        if not text:
            self.get_logger().warning('Received empty /task_input — ignoring')
            return

        self.get_logger().info(f'Received command: {text!r}')
        result = parse_command(text)

        if result.get('action') == 'error':
            self.get_logger().error(f'LLM error: {result.get("reason")}')
        else:
            self.get_logger().info(f'Parsed task: {result}')

        out = String()
        out.data = json.dumps(result)
        self._pub.publish(out)


def main(args=None):
    rclpy.init(args=args)
    node = LangNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
```

- [ ] **Step 2: Add `lang_node` entry point to `setup.py`**

In `src/langrobot/setup.py`, the `entry_points` block currently reads:

```python
    entry_points={
        'console_scripts': [
            'controller_node = langrobot.controller_node:main',
        ],
    },
```

Change it to:

```python
    entry_points={
        'console_scripts': [
            'controller_node = langrobot.controller_node:main',
            'lang_node = langrobot.lang_node:main',
        ],
    },
```

- [ ] **Step 3: Verify Python syntax on both files**

```bash
cd src/langrobot
python3 -c "import ast; ast.parse(open('langrobot/lang_node.py').read()); print('lang_node OK')"
python3 -c "import ast; ast.parse(open('langrobot/llm_client.py').read()); print('llm_client OK')"
```

Expected:
```
lang_node OK
llm_client OK
```

- [ ] **Step 4: Commit**

```bash
cd ~/Desktop/Projects/LangRobot
git add src/langrobot/langrobot/lang_node.py src/langrobot/setup.py
git commit -m "feat: lang_node ROS2 wrapper — /task_input → /task_command"
```

---

## Task 3: Wire `lang_node` into the launch file

**Files:**
- Modify: `src/langrobot/launch/langrobot.launch.py`

The launch file currently ends with:

```python
    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        robot_state_publisher,
        gazebo,
        clock_bridge,
        delayed_camera_bridge,
        delayed_spawn,
        controller_node,
        rviz_node,
    ])
```

- [ ] **Step 1: Add `lang_node` to the launch description**

Add this Node definition before the `return` statement (after `rviz_node`):

```python
    lang_node = Node(
        package='langrobot',
        executable='lang_node',
        name='lang_node',
        output='screen',
    )
```

Then add `lang_node` to the `LaunchDescription` list:

```python
    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        robot_state_publisher,
        gazebo,
        clock_bridge,
        delayed_camera_bridge,
        delayed_spawn,
        controller_node,
        rviz_node,
        lang_node,
    ])
```

Note: `lang_node` does NOT get `use_sim_time` — it talks to Ollama (wall-clock HTTP) and does not use ROS2 simulation time.

- [ ] **Step 2: Verify Python syntax**

```bash
python3 -c "import ast; ast.parse(open('src/langrobot/launch/langrobot.launch.py').read()); print('Syntax OK')"
```

Expected: `Syntax OK`

- [ ] **Step 3: Commit**

```bash
git add src/langrobot/launch/langrobot.launch.py
git commit -m "feat: add lang_node to launch file"
```

---

## Task 4: Build, install, and run all tests

**Files:** none new — verify everything integrates cleanly.

- [ ] **Step 1: Run the full unit test suite (Mac — no ROS2 needed)**

```bash
cd ~/Desktop/Projects/LangRobot
PYTHONPATH=src/langrobot python3 -m pytest tests/ -v
```

Expected: **23 passed** (17 existing + 6 new `test_lang_node.py` tests).

- [ ] **Step 2: Build on Linux PC**

```bash
cd ~/Desktop/Projects/LangRobot
git pull origin main
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
```

Expected:
```
Summary: 2 packages finished [Xs]
```

No `failed` or `aborted`. If `requests` is not installed, run:
```bash
pip install --break-system-packages requests
```

- [ ] **Step 3: Verify `lang_node` executable is available**

```bash
source install/setup.bash
ros2 run langrobot lang_node --help 2>&1 | head -5
```

Expected: no `executable not found` error. (The node will start and spin — Ctrl+C to stop.)

- [ ] **Step 4: Commit**

No new code — if all tests passed and build succeeded, push:

```bash
git push origin main
```

---

## Task 5: Phase 3 verification guide + test log

**Files:**
- Create: `docs/testing/phase3-verification-guide.md`
- Create: `logs/phase3-test-log.md`

- [ ] **Step 1: Create `docs/testing/phase3-verification-guide.md`**

```markdown
# Phase 3 Verification Guide

How to verify Phase 3 (`lang_node`) on the Linux PC.

**Gate:** `ros2 topic echo /task_command` shows valid JSON within ~3 seconds of publishing to `/task_input`.

---

## Before you start

```bash
cd ~/Desktop/Projects/LangRobot
git pull origin main
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
```

Confirm Ollama is running and Gemma 4 is available:
```bash
ollama list | grep gemma4
```
If not listed: `ollama pull gemma4`

---

## Test 1 — Unit tests (23 tests)

```bash
PYTHONPATH=src/langrobot python3 -m pytest tests/ -v
```

**What to look for:** All 23 tests pass, including the 6 new `test_lang_node.py` tests.

---

## Test 2 — Launch and verify lang_node starts

**Terminal 1:**
```bash
source install/setup.bash
ros2 launch langrobot langrobot.launch.py
```

**What to look for in terminal output:**
```
[lang_node]: lang_node ready — publish to /task_input to send a command
```

---

## Test 3 — Send a command and check output

**Terminal 2:**
```bash
source install/setup.bash
ros2 topic echo /task_command
```

**Terminal 3:**
```bash
source install/setup.bash
ros2 topic pub --once /task_input std_msgs/msg/String "data: 'move the red block onto the blue block'"
```

**What to look for in Terminal 2 (within ~3 seconds):**
```
data: '{"action": "pick_and_place", "object": "red", "target": "blue"}'
```

Try at least 3 different commands:
- `"put the green block on top of the yellow block"`
- `"pick up white and place it on red"`
- `"stack blue on green"`

---

## Test 4 — Check active nodes

```bash
ros2 node list
```

**What to look for:**
```
/camera_bridge
/clock_bridge
/controller_node
/lang_node
/robot_state_publisher
/rviz2
```

`/lang_node` must appear.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `lang_node` not in `ros2 node list` | Check `colcon build` succeeded and `setup.py` has the `lang_node` entry point. |
| `/task_command` shows `{"action": "error", ...}` | Check Ollama is running: `ollama list`. If not: `ollama serve` in a separate terminal. |
| Response takes >30 s | GPU may not be active. Check: `HSA_OVERRIDE_GFX_VERSION=11.0.1` is in `.bashrc` and you've logged out/in since ROCm install. |
| JSON has wrong colours | Gemma 4 hallucinated. Run the command again — retry logic should catch it. |

---

## Logging results

Fill in `logs/phase3-test-log.md`, then:

```bash
git add logs/phase3-test-log.md
git commit -m "test: Phase 3 verification results"
git push origin main
```
```

- [ ] **Step 2: Create `logs/phase3-test-log.md`**

```markdown
# Phase 3 Test Log

**Date:** <!-- e.g. 2026-04-15 -->
**Machine:** GhostMachine — AMD RX 7700 XT, Ubuntu 24.04
**Branch/commit:** <!-- run: git log --oneline -1 -->

---

## Test Results

### Test 1 — Unit tests (23 tests)
- [ ] All 23 PASSED  [ ] Some FAILED

**Output of `pytest tests/ -v` (last 5 lines):**
```
<!-- paste here -->
```

---

### Test 2 — lang_node starts
- [ ] `lang_node ready` message appears in Terminal 1

---

### Test 3 — Command → JSON output

**Command tried:** <!-- paste command -->
**Output on /task_command:**
```
<!-- paste here -->
```

- [ ] Valid JSON received within ~3 s
- [ ] Tested at least 3 different commands

---

### Test 4 — Active nodes
- [ ] `/lang_node` present in `ros2 node list`

**Output of `ros2 node list`:**
```
<!-- paste here -->
```

---

## Overall Phase 3 Result

- [ ] **PASSED** — valid JSON for all tested commands
- [ ] **PASSED WITH ISSUES** — mostly working, see notes
- [ ] **FAILED** — blocked

**Blocking issues (if any):**
<!-- Describe and paste error -->

**Non-blocking observations:**
<!-- Anything odd but not broken -->

---

## What to do next

```bash
git add logs/phase3-test-log.md
git commit -m "test: Phase 3 verification results"
git push origin main
```
```

- [ ] **Step 3: Commit**

```bash
git add docs/testing/phase3-verification-guide.md logs/phase3-test-log.md
git commit -m "docs: Phase 3 verification guide and test log template"
git push origin main
```

---

## Phase 3 gate

**PASS criteria (all required):**
1. All 23 unit tests pass
2. `lang_node ready` appears in launch output
3. `/task_command` shows valid JSON (`{"action": "pick_and_place", "object": "...", "target": "..."}`) within ~3 seconds of publishing to `/task_input`
4. `/lang_node` appears in `ros2 node list`

If any criterion fails, commit the log with the error and push — fixes will be issued before Phase 4.

---

## Phase 4 preview (for context, not implemented here)

Phase 4 adds `perception_node`: a YOLOv8-based node that subscribes to `/camera/rgb_image` and `/camera/depth_image` and publishes detected block poses to `/object_poses`. Gate: `ros2 topic echo /object_poses` shows correct 3D positions for all 5 blocks.
