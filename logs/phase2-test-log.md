# Phase 2 Test Log

**Date:** <!-- e.g. 2026-04-15 -->
**Machine:** GhostMachine — AMD RX 7700 XT, Ubuntu 24.04
**Branch/commit:** <!-- run: git log --oneline -1 -->

---

## Test Results

### Test 1 — Unit tests (17 tests)
- [ ] All 17 PASSED  [ ] Some FAILED

**Output of `pytest tests/ -v` (last 5 lines):**
```
<!-- paste here -->
```

---

### Test 2 — Gazebo: table and blocks visible
- [ ] Table visible (brown box)
- [ ] All 5 blocks visible (red, blue, green, yellow, white)
- [ ] Arm present (collapsed is OK)

**Gazebo screenshot:**
<!-- Save as logs/phase2-gazebo-screenshot.png -->

**Any errors in Terminal 1?**
```
<!-- paste here -->
```

---

### Test 3 — Camera topics in ROS2
- [ ] `/camera/rgb_image` present
- [ ] `/camera/depth_image` present
- [ ] `/camera/camera_info` present

**Output of `ros2 topic list | grep camera`:**
```
<!-- paste here -->
```

---

### Test 4 — Camera image in RViz2
- [ ] RViz2 opened automatically
- [ ] Camera panel shows a live image
- [ ] Blocks are visible in the image

**RViz2 screenshot:**
<!-- Save as logs/phase2-rviz-screenshot.png -->

---

### Test 5 — Active nodes
- [ ] PASS  [ ] FAIL

**Output of `ros2 node list`:**
```
<!-- paste here -->
```

---

## Overall Phase 2 Result

- [ ] **PASSED** — table, blocks, and camera image all visible
- [ ] **PASSED WITH ISSUES** — mostly working, see notes
- [ ] **FAILED** — blocked

**Blocking issues (if any):**
<!-- Describe the problem and paste the full error -->

**Non-blocking observations:**
<!-- Anything odd but not broken -->

---

## What to do next

```bash
git add logs/phase2-test-log.md
git add logs/phase2-gazebo-screenshot.png
git add logs/phase2-rviz-screenshot.png
git commit -m "test: Phase 2 verification results"
git push origin main
```
