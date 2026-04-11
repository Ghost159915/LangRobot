import math

import pytest

from langrobot.scene import (
    ARM_REACH_M,
    BLOCK_POSITIONS,
    BLOCK_SIZE,
    CAMERA_POSE_XYZ,
    TABLE_POSE_XYZ,
    TABLE_SIZE_XYZ,
    TABLE_TOP_Z,
)


def test_table_top_height():
    expected = TABLE_POSE_XYZ[2] + TABLE_SIZE_XYZ[2] / 2
    assert TABLE_TOP_Z == pytest.approx(expected)


def test_table_within_arm_reach():
    # Every block must be within arm reach of the base at (0, 0, 0).
    # This is the meaningful constraint — the arm must grasp each block.
    for name, (x, y, z) in BLOCK_POSITIONS.items():
        dist = math.sqrt(x * x + y * y + z * z)
        assert dist < ARM_REACH_M, f"{name} block at dist={dist:.3f}m exceeds reach {ARM_REACH_M}m"


def test_all_blocks_on_table_surface():
    expected_z = TABLE_TOP_Z + BLOCK_SIZE / 2
    for name, (x, y, z) in BLOCK_POSITIONS.items():
        assert z == pytest.approx(expected_z), f"{name} block z incorrect"


def test_all_blocks_within_table_bounds():
    x_min = TABLE_POSE_XYZ[0] - TABLE_SIZE_XYZ[0] / 2
    x_max = TABLE_POSE_XYZ[0] + TABLE_SIZE_XYZ[0] / 2
    y_min = TABLE_POSE_XYZ[1] - TABLE_SIZE_XYZ[1] / 2
    y_max = TABLE_POSE_XYZ[1] + TABLE_SIZE_XYZ[1] / 2
    half = BLOCK_SIZE / 2
    for name, (x, y, z) in BLOCK_POSITIONS.items():
        assert x_min + half <= x <= x_max - half, f"{name} block x={x} out of table"
        assert y_min + half <= y <= y_max - half, f"{name} block y={y} out of table"


def test_five_blocks():
    assert len(BLOCK_POSITIONS) == 5


def test_block_names():
    assert set(BLOCK_POSITIONS.keys()) == {"red", "blue", "green", "yellow", "white"}


def test_camera_above_everything():
    assert CAMERA_POSE_XYZ[2] > TABLE_TOP_Z + BLOCK_SIZE


def test_blocks_no_overlap():
    # Use Chebyshev distance (max of axis distances) for axis-aligned cube overlap.
    # Two BLOCK_SIZE cubes don't overlap when max(|dx|, |dy|) >= BLOCK_SIZE.
    names = list(BLOCK_POSITIONS.keys())
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            ax, ay, _ = BLOCK_POSITIONS[a]
            bx, by, _ = BLOCK_POSITIONS[b]
            chebyshev = max(abs(ax - bx), abs(ay - by))
            assert chebyshev >= BLOCK_SIZE, f"{a} and {b} blocks overlap (chebyshev={chebyshev:.3f})"
