# Phase 4 Test Log

**Date:** <!-- e.g. 2026-04-15 -->
**Machine:** GhostMachine — AMD RX 7700 XT, Ubuntu 24.04
**Branch/commit:** <!-- run: git log --oneline -1 -->

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
