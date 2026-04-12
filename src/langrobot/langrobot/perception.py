"""
perception.py — pure Python block detection via HSV colour segmentation.

No ROS2 imports. Public interface: detect_blocks(bgr, depth, camera_info) -> list[dict].
All failures return visible=False entries — never raises.
"""
import logging

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# Camera world position (from worlds/basic.sdf pose: 0.5 0 1.5 0 1.5708 0)
CAMERA_X = 0.5
CAMERA_Y = 0.0
CAMERA_Z = 1.5

# Minimum contour area in pixels — filters out noise specks
MIN_CONTOUR_AREA = 100

# Fixed colour order: output list always has entries in this order
COLOURS = ["red", "blue", "green", "yellow", "white"]

# HSV ranges per colour. Each colour has one or more (lo, hi) ranges that are
# OR'd together. Red needs two ranges because its hue wraps around 0°.
# Format: (np.array([H_lo, S_lo, V_lo]), np.array([H_hi, S_hi, V_hi]))
_HSV_RANGES = {
    "red":    [(np.array([0,   100, 100]), np.array([10,  255, 255])),
               (np.array([170, 100, 100]), np.array([180, 255, 255]))],
    "blue":   [(np.array([100, 100, 100]), np.array([130, 255, 255]))],
    "green":  [(np.array([40,  100, 100]), np.array([80,  255, 255]))],
    "yellow": [(np.array([20,  100, 100]), np.array([35,  255, 255]))],
    "white":  [(np.array([0,   0,   200]), np.array([180, 30,  255]))],
}


def _get_mask(hsv: np.ndarray, colour: str) -> np.ndarray:
    """Return binary mask for `colour` in the HSV image."""
    ranges = _HSV_RANGES[colour]
    mask = cv2.inRange(hsv, ranges[0][0], ranges[0][1])
    for lo, hi in ranges[1:]:
        mask = cv2.bitwise_or(mask, cv2.inRange(hsv, lo, hi))
    return mask


def _find_centroid(mask: np.ndarray):
    """Return (u, v) centroid of the largest contour by area, or None if not found.

    Only one detection per colour is returned. If a colour appears as multiple
    disconnected regions (e.g. occlusion), only the largest region is used.
    """
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    largest = max(contours, key=cv2.contourArea)
    if cv2.contourArea(largest) < MIN_CONTOUR_AREA:
        return None
    M = cv2.moments(largest)
    if M["m00"] == 0:
        return None
    u = int(M["m10"] / M["m00"])
    v = int(M["m01"] / M["m00"])
    return u, v


def _project_to_world(u: int, v: int, depth: float, camera_info: dict):
    """
    Back-project pixel (u, v) + depth to world-frame (x, y, z).

    Camera is fixed at (CAMERA_X, CAMERA_Y, CAMERA_Z) pointing straight down
    (pitch = π/2). Image +u → world +x. Image +v → world -y (flipped).
    Depth increases downward so world_z = CAMERA_Z - depth.
    """
    fx = camera_info["fx"]
    fy = camera_info["fy"]
    cx = camera_info["cx"]
    cy = camera_info["cy"]

    x_cam = (u - cx) * depth / fx
    y_cam = (v - cy) * depth / fy

    x_world = CAMERA_X + x_cam
    y_world = CAMERA_Y + y_cam   # image Y increases downward; world Y increases upward
    z_world = CAMERA_Z - depth

    return x_world, y_world, z_world


def detect_blocks(
    bgr: np.ndarray,
    depth: np.ndarray,
    camera_info: dict,
) -> list:
    """
    Detect all 5 coloured blocks in the image.

    Args:
        bgr:         HxWx3 uint8 array in BGR order (OpenCV convention).
        depth:       HxW float32 array, values in metres.
        camera_info: dict with keys fx, fy, cx, cy (pinhole intrinsics).

    Returns:
        List of 5 dicts, always one per colour, in fixed order
        [red, blue, green, yellow, white]:
          {"colour": str, "x": float|None, "y": float|None,
           "z": float|None, "visible": bool}
        Never raises — failures produce visible=False entries.
    """
    try:
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    except Exception as exc:
        logger.error("HSV conversion failed: %s", exc)
        return [
            {"colour": c, "x": None, "y": None, "z": None, "visible": False}
            for c in COLOURS
        ]

    results = []
    for colour in COLOURS:
        entry = {"colour": colour, "x": None, "y": None, "z": None, "visible": False}
        try:
            mask = _get_mask(hsv, colour)
            centroid = _find_centroid(mask)
            if centroid is None:
                results.append(entry)
                continue

            u, v = centroid
            d = float(depth[v, u])
            if d <= 0.0 or not np.isfinite(d):
                results.append(entry)
                continue

            x, y, z = _project_to_world(u, v, d, camera_info)
            entry = {
                "colour": colour,
                "x": round(x, 3),
                "y": round(y, 3),
                "z": round(z, 3),
                "visible": True,
            }
        except Exception as exc:
            logger.error("Detection failed for %s: %s", colour, exc)
        results.append(entry)

    return results
