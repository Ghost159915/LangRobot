"""Unit tests for planner_node pure helpers.

Runs on Mac without ROS2. Tests pose computation and sequence abort logic.
"""
from __future__ import annotations
import json
import math
import pytest


# ── Copy of the pure functions from planner_node ─────────────────────────
# (We test the functions before planner_node.py exists — TDD.)

def find_block(poses: list[dict], colour: str) -> dict | None:
    """Return the block dict for the given colour if visible, else None."""
    for block in poses:
        if block['colour'] == colour and block.get('visible'):
            return block
    return None


def compute_pre_grasp_pose(block: dict) -> tuple[float, float, float]:
    """Return (x, y, z) 10 cm above the block centre."""
    return (block['x'], block['y'], block['z'] + 0.10)


def compute_grasp_pose(block: dict) -> tuple[float, float, float]:
    """Return (x, y, z) at the block centre (grasp height)."""
    return (block['x'], block['y'], block['z'])


def compute_lift_pose(block: dict) -> tuple[float, float, float]:
    """Return (x, y, z) 15 cm above the block centre."""
    return (block['x'], block['y'], block['z'] + 0.15)


def compute_pre_place_pose(target: dict) -> tuple[float, float, float]:
    """Return (x, y, z) 10 cm above the target block."""
    return (target['x'], target['y'], target['z'] + 0.10)


def compute_place_pose(target: dict) -> tuple[float, float, float]:
    """Return (x, y, z) at target top + 5 cm (stack height)."""
    return (target['x'], target['y'], target['z'] + 0.05)


# ── Tests ─────────────────────────────────────────────────────────────────

_POSES = [
    {'colour': 'red',    'x': 0.45, 'y': -0.25, 'z': 0.425, 'visible': True},
    {'colour': 'blue',   'x': 0.45, 'y':  0.25, 'z': 0.425, 'visible': True},
    {'colour': 'green',  'x': None, 'y':  None,  'z': None,  'visible': False},
    {'colour': 'yellow', 'x': 0.55, 'y':  0.15, 'z': 0.425, 'visible': True},
    {'colour': 'white',  'x': 0.60, 'y':  0.0,  'z': 0.425, 'visible': True},
]


def test_find_block_visible():
    block = find_block(_POSES, 'red')
    assert block is not None
    assert block['colour'] == 'red'


def test_find_block_not_visible_returns_none():
    block = find_block(_POSES, 'green')
    assert block is None


def test_find_block_unknown_colour_returns_none():
    block = find_block(_POSES, 'purple')
    assert block is None


def test_pre_grasp_pose_is_10cm_above():
    block = {'colour': 'red', 'x': 0.45, 'y': -0.25, 'z': 0.425, 'visible': True}
    x, y, z = compute_pre_grasp_pose(block)
    assert x == pytest.approx(0.45)
    assert y == pytest.approx(-0.25)
    assert z == pytest.approx(0.525)  # 0.425 + 0.10


def test_grasp_pose_at_block_centre():
    block = {'colour': 'red', 'x': 0.45, 'y': -0.25, 'z': 0.425, 'visible': True}
    x, y, z = compute_grasp_pose(block)
    assert x == pytest.approx(0.45)
    assert y == pytest.approx(-0.25)
    assert z == pytest.approx(0.425)


def test_lift_pose_is_15cm_above():
    block = {'colour': 'red', 'x': 0.45, 'y': -0.25, 'z': 0.425, 'visible': True}
    x, y, z = compute_lift_pose(block)
    assert z == pytest.approx(0.575)  # 0.425 + 0.15


def test_place_pose_is_5cm_above_target_top():
    target = {'colour': 'blue', 'x': 0.45, 'y': 0.25, 'z': 0.425, 'visible': True}
    x, y, z = compute_place_pose(target)
    assert x == pytest.approx(0.45)
    assert y == pytest.approx(0.25)
    assert z == pytest.approx(0.475)  # 0.425 + 0.05


def test_pre_place_pose_is_10cm_above_target():
    target = {'colour': 'blue', 'x': 0.45, 'y': 0.25, 'z': 0.425, 'visible': True}
    x, y, z = compute_pre_place_pose(target)
    assert z == pytest.approx(0.525)  # 0.425 + 0.10
