# Phase 4 Test Log

**Date:** 2026-04-12
**Machine:** GhostMachine — AMD RX 7700 XT, Ubuntu 24.04
**Branch/commit:** <!-- run: git log --oneline -1 -->

---

## Setup Errors & Solutions

### Error 1 — `rosdep install` warns about `ament_python`
**Command:** `rosdep install --from-paths src --ignore-src -r -y`

**Error:**
```
langrobot: Cannot locate rosdep definition for [ament_python]
```

**Solution:** Harmless warning. `ament_python` is part of the ROS2 Jazzy installation itself — rosdep has no system-package mapping for it but it is already present. The final line "All required rosdeps installed successfully" confirms everything needed was installed. Continue without action.

---

### Error 2 — `pip install opencv-python` numpy/scipy conflict
**Command:** `pip install --break-system-packages opencv-python`

**Error:**
```
scipy 1.11.4 requires numpy<1.28.0,>=1.21.6, but you have numpy 2.4.4 which is incompatible.
```

**Solution:** Harmless for this project. opencv-python upgraded numpy from 1.26.4 → 2.4.4 which conflicts with a system scipy install. LangRobot does not use scipy, so this has no effect. Install succeeded ("Successfully installed numpy-2.4.4"). If scipy is needed elsewhere later, pin numpy back with `pip install --break-system-packages "numpy<1.28"`.

---

### Error 3 — `perception_node` crashes: `cv_bridge` incompatible with numpy 2.x
**When:** On `ros2 launch langrobot langrobot.launch.py`

**Error:**
```
ImportError: A module that was compiled using NumPy 1.x cannot be run in NumPy 2.4.4
cv_bridge/boost/cv_bridge_boost → crash on imgmsg_to_cv2
[ERROR] [perception_node-7]: process has died [pid 4388, exit code -11]
```

**Root cause:** `pip install opencv-python` (Error 2) upgraded numpy 1.26.4 → 2.4.4. `cv_bridge` in ROS2 Jazzy is compiled against numpy 1.x and is binary-incompatible with numpy 2.x.

**Fix:**
```bash
pip install --break-system-packages "numpy<2"
```
Then `Ctrl+C` the launch and relaunch. Downgrading numpy to <2 satisfies both cv_bridge and scipy. opencv-python works fine on numpy 1.x.

**Prevention:** Always pin numpy when installing opencv on a ROS2 system: `pip install --break-system-packages "opencv-python" "numpy<2"`

---

## Test Results

### Test 1 — Unit tests (33 tests)
- [ ] All 33 PASSED  [ ] Some FAILED

**Output (last 5 lines):**
```
<!-- paste here -->
```

---

### Test 2 — perception_node starts
- [ ] `perception_node ready` appears
- [ ] `Camera intrinsics cached` appears (with values)

**Intrinsics logged:**
```
<!-- paste here -->
```

---

### Test 3 — /object_poses output
- [ ] JSON array of 5 dicts updating at framerate
- [ ] Visible blocks have non-null coordinates

**Sample output:**
```
<!-- paste here -->
```

---

### Test 4 — Position accuracy
- [ ] Positions within ~5 cm of Gazebo block locations
- [ ] y-axis correction needed: yes / no

**Notes:**
<!-- describe any corrections made -->

---

### Test 5 — Active nodes
- [ ] `/perception_node` in `ros2 node list`

**Output of `ros2 node list`:**
```
<!-- paste here -->
```

---

## Overall Phase 4 Result

- [ ] **PASSED**
- [ ] **PASSED WITH ISSUES** — see notes
- [ ] **FAILED**

**Issues:**
<!-- describe -->

---

## What to do next

```bash
git add logs/phase4-test-log.md
git commit -m "test: Phase 4 verification results"
git push origin main
```
