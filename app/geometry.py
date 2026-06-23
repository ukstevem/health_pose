"""Pure geometry helpers operating on 2D points.

No OpenCV / MediaPipe / FastAPI imports live here on purpose: these functions
are the portable core that a later browser-only (MediaPipe JS) build can mirror
in plain JavaScript. Keep them dependency-light and side-effect-free.
"""
from __future__ import annotations

import math
from typing import Tuple

Point = Tuple[float, float]


def angle_deg(a: Point, b: Point, c: Point) -> float:
    """Interior angle (degrees) at vertex ``b`` formed by points a-b-c.

    Returns a value in [0, 180]. ``180`` means a, b, c are collinear with b in
    the middle (a fully straight joint); small values mean a tightly bent joint.
    """
    bax, bay = a[0] - b[0], a[1] - b[1]
    bcx, bcy = c[0] - b[0], c[1] - b[1]
    dot = bax * bcx + bay * bcy
    mag = math.hypot(bax, bay) * math.hypot(bcx, bcy)
    if mag == 0.0:
        return 0.0
    cos = max(-1.0, min(1.0, dot / mag))
    return math.degrees(math.acos(cos))


def angle_from_vertical_deg(top: Point, bottom: Point) -> float:
    """Angle (degrees) of the segment top->bottom away from vertical.

    ``0`` = perfectly vertical (e.g. an upright torso); larger = more lean.
    Image coordinates: y grows downward, which does not affect this measure.
    """
    dx = top[0] - bottom[0]
    dy = top[1] - bottom[1]
    if dx == 0.0 and dy == 0.0:
        return 0.0
    # Deviation from the vertical axis, direction-agnostic: 0 = vertical,
    # 90 = horizontal. Using |dx|,|dy| keeps it independent of which end is up
    # and which way the lean tips.
    return math.degrees(math.atan2(abs(dx), abs(dy)))
