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

## Test 1 — Unit tests (25 tests)

```bash
PYTHONPATH=src/langrobot pytest tests/ -v
```

**What to look for:** All 25 tests pass.

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
| Response takes >30 s | GPU may not be active. Check `HSA_OVERRIDE_GFX_VERSION=11.0.1` is in `.bashrc` and you have logged out/in since ROCm install. |
| JSON has wrong colours | Gemma 4 hallucinated. Run the command again — retry logic should catch it. |

---

## Logging results

Fill in `logs/phase3-test-log.md`, then:

```bash
git add logs/phase3-test-log.md
git commit -m "test: Phase 3 verification results"
git push origin main
```
