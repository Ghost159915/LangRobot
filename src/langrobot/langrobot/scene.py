# Gazebo world geometry constants — single source of truth.
# Used by unit tests to verify layout invariants.
# Will also be imported by planner_node (Phase 5) for initial pose estimates.

# ── Arm ──────────────────────────────────────────────────────────────────────
ARM_REACH_M: float = 0.855  # Franka FR3 maximum reach from base centre (metres)

# ── Table ────────────────────────────────────────────────────────────────────
# SDF box is centred at TABLE_POSE_XYZ; its half-extents are TABLE_SIZE_XYZ / 2.
TABLE_POSE_XYZ: tuple[float, float, float] = (0.5, 0.0, 0.2)
TABLE_SIZE_XYZ: tuple[float, float, float] = (0.5, 1.0, 0.4)

# Top surface z-coordinate (derived — do not edit independently)
TABLE_TOP_Z: float = TABLE_POSE_XYZ[2] + TABLE_SIZE_XYZ[2] / 2  # 0.4 m

# ── Blocks ───────────────────────────────────────────────────────────────────
BLOCK_SIZE: float = 0.05  # 5 cm solid cubes

# Centre positions (x, y, z) — blocks rest on TABLE_TOP_Z surface.
_BLOCK_Z = TABLE_TOP_Z + BLOCK_SIZE / 2  # 0.425 m

BLOCK_POSITIONS: dict[str, tuple[float, float, float]] = {
    "red":    (0.45, -0.25, _BLOCK_Z),
    "blue":   (0.45,  0.25, _BLOCK_Z),
    "green":  (0.55, -0.15, _BLOCK_Z),
    "yellow": (0.55,  0.15, _BLOCK_Z),
    "white":  (0.60,  0.00, _BLOCK_Z),
}

# ── Camera ───────────────────────────────────────────────────────────────────
# Overhead position; SDF pose pitch = π/2 rotates +X optical axis to point −Z.
CAMERA_POSE_XYZ: tuple[float, float, float] = (0.5, 0.0, 1.5)
