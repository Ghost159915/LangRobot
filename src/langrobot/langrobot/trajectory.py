def extract_final_positions(points) -> list[float]:
    """Return joint positions from the last point of a trajectory points list.

    Args:
        points: list of objects with a .positions attribute

    Returns:
        list of float joint positions

    Raises:
        ValueError: if points is empty
    """
    if not points:
        raise ValueError("JointTrajectory has no points")
    return list(points[-1].positions)


def trajectory_to_command(joint_trajectory_msg) -> list[float]:
    """Convert a JointTrajectory ROS2 message to a flat list of float positions.

    Extracts the final trajectory point's positions.

    Raises:
        ValueError: if the message has no points
    """
    return extract_final_positions(joint_trajectory_msg.points)
