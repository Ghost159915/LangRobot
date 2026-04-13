import sys
from pathlib import Path

# Make the langrobot package importable without setting PYTHONPATH manually.
# ROS2 packages (rclpy, sensor_msgs, etc.) come from the sourced install/setup.bash.
sys.path.insert(0, str(Path(__file__).parent / "src" / "langrobot"))
