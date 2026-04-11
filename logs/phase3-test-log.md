# Phase 3 Test Log

**Date:** <!-- 2026-04-11 -->
**Machine:** GhostMachine — AMD RX 7700 XT, Ubuntu 24.04
**Branch/commit:** <!-- run: git log --oneline -1 -->

---

## Test Results

### Test 1 — Unit tests (25 tests)
- [x] All 25 PASSED  [ ] Some FAILED

**Output of `pytest tests/ -v` (last 5 lines):**
```
<tests/test_scene.py::test_five_blocks PASSED                             [ 88%]
tests/test_scene.py::test_block_names PASSED                             [ 92%]
tests/test_scene.py::test_camera_above_everything PASSED                 [ 96%]
tests/test_scene.py::test_blocks_no_overlap PASSED                       [100%]

============================== 25 passed in 0.08s ==============================
>
```

---

### Test 2 — lang_node starts
- [x] `lang_node ready` message appears in Terminal 1

---

### Test 3 — Command → JSON output

**Command tried:** "put the green block on top of the yellow block"
**Output on /task_command:**

data: '{"action": "pick_and_place", "object": "green", "target": "yellow"}'


- [x] Valid JSON received within ~3 s
- [x] Tested at least 3 different commands

---

### Test 4 — Active nodes
- [x] `/lang_node` present in `ros2 node list`

**Output of `ros2 node list`:**
ghost@GhostMachine:~/Desktop/Projects/LangRobot$ ros2 node list
/camera_bridge
/clock_bridge
/controller_node
/lang_node
/robot_state_publisher
/rviz2
/transform_listener_impl_60eea2914cd0

---

## Overall Phase 3 Result

- [x] **PASSED** — valid JSON for all tested commands
- [x] **PASSED WITH ISSUES** — mostly working, see notes
- [ ] **FAILED** — blocked

**Blocking issues (if any):**
<!-- Describe and paste error -->

**Non-blocking observations:**
the terminals update correctly however i still see no movement or any sign of life from the gazebo simulaion, robot doeesnt move just is there.

---

## What to do next

```bash
git add logs/phase3-test-log.md
git commit -m "test: Phase 3 verification results"
git push origin main
```
