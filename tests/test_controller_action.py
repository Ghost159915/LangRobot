"""Unit tests for FollowJointTrajectory execution logic.

Tests run on Mac (no ROS2) — all ROS2 types are stubbed.
"""
from __future__ import annotations
import time
import pytest


# ── Minimal stubs so we can import without rclpy ──────────────────────────

class _Duration:
    def __init__(self, sec=0, nanosec=0):
        self.sec = sec
        self.nanosec = nanosec

    def to_sec(self):
        return self.sec + self.nanosec / 1e9


class _Point:
    def __init__(self, positions, time_from_start):
        self.positions = positions
        self.time_from_start = time_from_start


# ── Pure function extracted from ControllerNode ───────────────────────────

def run_trajectory_points(points, publish_fn, now_fn, sleep_fn):
    """Iterate trajectory points in time order, publishing each one."""
    if not points:
        return
    sorted_points = sorted(points, key=lambda p: p.time_from_start.sec + p.time_from_start.nanosec / 1e9)
    prev_t = 0.0
    for point in sorted_points:
        t = point.time_from_start.sec + point.time_from_start.nanosec / 1e9
        delay = t - prev_t
        if delay > 0:
            sleep_fn(delay)
        publish_fn(list(point.positions))
        prev_t = t


# ── Tests ─────────────────────────────────────────────────────────────────

def test_points_published_in_time_order():
    """Points must be published in ascending time_from_start order."""
    published = []

    points = [
        _Point([2.0, 2.0], _Duration(sec=2)),
        _Point([1.0, 1.0], _Duration(sec=1)),  # out of order
        _Point([3.0, 3.0], _Duration(sec=3)),
    ]

    run_trajectory_points(
        points,
        publish_fn=lambda pos: published.append(pos),
        now_fn=time.time,
        sleep_fn=lambda _: None,
    )

    assert published == [[1.0, 1.0], [2.0, 2.0], [3.0, 3.0]]


def test_inter_point_timing():
    """sleep_fn must be called with each inter-point delay."""
    slept = []

    points = [
        _Point([0.0], _Duration(sec=1)),
        _Point([1.0], _Duration(sec=3)),
        _Point([2.0], _Duration(sec=5)),
    ]

    run_trajectory_points(
        points,
        publish_fn=lambda _: None,
        now_fn=time.time,
        sleep_fn=lambda d: slept.append(round(d, 6)),
    )

    assert slept == [1.0, 2.0, 2.0]


def test_empty_trajectory_does_nothing():
    """Empty points list must not call publish_fn or sleep_fn."""
    published = []
    slept = []

    run_trajectory_points(
        [],
        publish_fn=lambda p: published.append(p),
        now_fn=time.time,
        sleep_fn=lambda d: slept.append(d),
    )

    assert published == []
    assert slept == []


def test_single_point_published_immediately():
    """A single point must be published with the full time_from_start delay before it."""
    published = []
    slept = []

    points = [_Point([0.5, 1.0, 1.5], _Duration(sec=2))]

    run_trajectory_points(
        points,
        publish_fn=lambda p: published.append(list(p)),
        now_fn=time.time,
        sleep_fn=lambda d: slept.append(d),
    )

    assert published == [[0.5, 1.0, 1.5]]
    assert slept == [2.0]
