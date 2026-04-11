import numpy as np
import pytest

from langrobot.perception import detect_blocks


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _camera_info():
    """Typical pinhole intrinsics for a 640×480 image."""
    return {"fx": 554.0, "fy": 554.0, "cx": 320.0, "cy": 240.0}


def _solid_rgb(bgr_colour, h=480, w=640):
    """Synthetic image filled with a single BGR colour."""
    img = np.zeros((h, w, 3), dtype=np.uint8)
    img[:] = bgr_colour
    return img


def _solid_depth(value=1.0, h=480, w=640):
    """Depth image where every pixel is `value` metres."""
    return np.full((h, w), value, dtype=np.float32)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_red_block_detected():
    """Solid red image → red block detected as visible."""
    rgb = _solid_rgb((0, 0, 200))        # BGR red
    depth = _solid_depth(1.0)
    result = detect_blocks(rgb, depth, _camera_info())
    red = next(b for b in result if b["colour"] == "red")
    assert red["visible"] is True
    assert red["x"] is not None
    assert red["y"] is not None
    assert red["z"] is not None


def test_unknown_colour_not_detected():
    """Purple image (not one of our 5 colours) → all blocks not visible."""
    rgb = _solid_rgb((128, 0, 128))      # BGR purple
    depth = _solid_depth(1.0)
    result = detect_blocks(rgb, depth, _camera_info())
    assert len(result) == 5
    assert all(b["visible"] is False for b in result)
    assert all(b["x"] is None for b in result)


def test_depth_to_3d():
    """
    Solid red image with centroid at centre pixel + depth=1.0m.
    Camera at (0.5, 0, 1.5) pointing straight down.
    Centre pixel → directly below camera → world (0.5, 0.0, 0.5).
    """
    rgb = _solid_rgb((0, 0, 200))        # BGR red — centroid lands at (320, 240)
    depth = _solid_depth(1.0)
    result = detect_blocks(rgb, depth, _camera_info())
    red = next(b for b in result if b["colour"] == "red")
    assert red["visible"] is True
    assert abs(red["x"] - 0.5) < 0.003   # within 3 mm (integer pixel centroid rounding at fx=554)
    assert abs(red["y"] - 0.0) < 0.003
    assert abs(red["z"] - 0.5) < 0.001   # depth is exact (uniform depth image)


def test_all_five_colours():
    """Image with all 5 colour strips → all 5 blocks visible."""
    h, w = 480, 640
    img = np.zeros((h, w, 3), dtype=np.uint8)
    # Each colour occupies a horizontal strip (top 96 rows, 128 px wide)
    img[0:96, 0:128]   = (0,   0,   200)   # red
    img[0:96, 128:256] = (200, 0,   0  )   # blue
    img[0:96, 256:384] = (0,   200, 0  )   # green
    img[0:96, 384:512] = (0,   255, 255)   # yellow (BGR: B=0, G=255, R=255)
    img[0:96, 512:640] = (220, 220, 220)   # white
    depth = _solid_depth(1.0)

    result = detect_blocks(img, depth, _camera_info())
    assert len(result) == 5
    visible = [b for b in result if b["visible"]]
    assert len(visible) == 5


def test_missing_block_returns_null():
    """Only red present → red visible, other 4 have visible=False and null coords."""
    rgb = _solid_rgb((0, 0, 200))        # BGR red only
    depth = _solid_depth(1.0)
    result = detect_blocks(rgb, depth, _camera_info())

    red = next(b for b in result if b["colour"] == "red")
    assert red["visible"] is True

    for colour in ["blue", "green", "yellow", "white"]:
        block = next(b for b in result if b["colour"] == colour)
        assert block["visible"] is False
        assert block["x"] is None
        assert block["y"] is None
        assert block["z"] is None


def test_zero_depth_returns_not_visible():
    """Block detected in RGB but depth=0 → visible=False (invalid depth)."""
    rgb = _solid_rgb((0, 0, 200))        # red
    depth = _solid_depth(0.0)            # all-zero depth — invalid
    result = detect_blocks(rgb, depth, _camera_info())
    red = next(b for b in result if b["colour"] == "red")
    assert red["visible"] is False
    assert red["x"] is None


def test_nan_depth_returns_not_visible():
    """Block detected in RGB but depth=NaN → visible=False (invalid depth)."""
    rgb = _solid_rgb((0, 0, 200))        # red
    depth = _solid_depth(float("nan"))
    result = detect_blocks(rgb, depth, _camera_info())
    red = next(b for b in result if b["colour"] == "red")
    assert red["visible"] is False
    assert red["x"] is None


def test_malformed_input_returns_all_not_visible():
    """Wrong-shaped input → detect_blocks never raises, returns 5 visible=False."""
    bad_input = np.zeros((10,), dtype=np.uint8)   # 1D — not a valid image
    depth = _solid_depth(1.0)
    result = detect_blocks(bad_input, depth, _camera_info())
    assert len(result) == 5
    assert all(b["visible"] is False for b in result)
