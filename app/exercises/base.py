"""Common types for exercise trackers.

A tracker consumes a frame's worth of landmarks and returns a flat state dict
that the web layer streams over the WebSocket. Trackers are deliberately pure
(no camera / network / drawing concerns) so they port to MediaPipe JS later.

``landmarks`` is a mapping of MediaPipe Pose landmark name -> (x, y, visibility)
in normalised image coordinates (0..1), y growing downward.
"""
from __future__ import annotations

from typing import Dict, Tuple

Landmark = Tuple[float, float, float]  # (x, y, visibility)
Landmarks = Dict[str, Landmark]
