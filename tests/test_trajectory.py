import pytest
import math
from langrobot.trajectory import extract_final_positions, trajectory_to_command


class FakePoint:
    def __init__(self, positions):
        self.positions = positions


class FakeTrajectory:
    def __init__(self, points):
        self.points = points


def test_final_point_positions_returned():
    points = [FakePoint([1.0, 2.0, 3.0]), FakePoint([4.0, 5.0, 6.0])]
    result = extract_final_positions(points)
    assert result == [4.0, 5.0, 6.0]


def test_only_last_point_used():
    points = [FakePoint([0.1, 0.2]), FakePoint([0.3, 0.4]), FakePoint([0.5, 0.6])]
    result = extract_final_positions(points)
    assert result == [0.5, 0.6]


def test_single_point():
    points = [FakePoint([1.0, 2.0, 3.0])]
    result = extract_final_positions(points)
    assert result == [1.0, 2.0, 3.0]


def test_empty_points_raises_value_error():
    with pytest.raises(ValueError):
        extract_final_positions([])


def test_seven_joint_positions():
    home = [0.0, -math.pi / 4, 0.0, -3 * math.pi / 4, 0.0, math.pi / 2, math.pi / 4]
    points = [FakePoint(home)]
    result = extract_final_positions(points)
    assert len(result) == 7


def test_positions_are_floats():
    points = [FakePoint([1.0, 2.0, 3.0])]
    result = extract_final_positions(points)
    for v in result:
        assert isinstance(v, float)
