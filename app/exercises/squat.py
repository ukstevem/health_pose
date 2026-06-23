"""Squat rep counter + form checker (rule-based, no ML).

Rep counting is a knee-angle state machine with hysteresis (down -> up cycle).
Form checks are conservative geometry, tuned to catch gross faults only:
  * insufficient depth (didn't break ~parallel), and
  * excessive forward torso lean.

All thresholds assume a side-on (sagittal) camera view.
"""
from __future__ import annotations

from typing import Optional

from ..geometry import angle_deg, angle_from_vertical_deg
from .base import Landmarks

# --- Tunable thresholds (degrees) ---------------------------------------------
KNEE_UP = 160.0      # knee straighter than this => standing ("up")
KNEE_DOWN = 120.0    # knee more bent than this => committed to a descent ("down")
DEPTH_OK = 100.0     # deepest knee angle must reach <= this for "good depth"
LEAN_MAX = 45.0      # torso lean from vertical beyond this => "chest up"
MIN_VISIBILITY = 0.5  # per-landmark MediaPipe visibility gate


def _pick_side(lm: Landmarks) -> Optional[str]:
    """Return 'left' or 'right' — whichever leg's joints are most visible."""
    def score(side: str) -> float:
        keys = (f"{side}_hip", f"{side}_knee", f"{side}_ankle")
        if not all(k in lm for k in keys):
            return -1.0
        return sum(lm[k][2] for k in keys)

    left, right = score("left"), score("right")
    best = max(left, right)
    if best < 0 or (best / 3.0) < MIN_VISIBILITY:
        return None
    return "left" if left >= right else "right"


class SquatTracker:
    name = "squat"

    def __init__(self) -> None:
        self.reps = 0
        self.phase = "up"            # "up" | "down"
        self._min_knee = 180.0       # deepest knee angle within current descent
        self._max_lean = 0.0         # worst torso lean within current descent
        self.last_rep_feedback = ""  # form verdict from the most recent rep
        self.cue = "Stand side-on to the camera"

    def reset(self) -> None:
        self.__init__()

    def update(self, lm: Landmarks) -> dict:
        side = _pick_side(lm)
        if side is None:
            self.cue = "Move into frame (side-on)"
            return self._state(knee_angle=None, lean=None, tracking=False)

        hip = lm[f"{side}_hip"][:2]
        knee = lm[f"{side}_knee"][:2]
        ankle = lm[f"{side}_ankle"][:2]
        shoulder = lm[f"{side}_shoulder"][:2] if f"{side}_shoulder" in lm else hip

        knee_angle = angle_deg(hip, knee, ankle)
        lean = angle_from_vertical_deg(shoulder, hip)

        # Track the deepest point and worst lean during a descent.
        if self.phase == "down":
            self._min_knee = min(self._min_knee, knee_angle)
            self._max_lean = max(self._max_lean, lean)

        # State machine with hysteresis.
        if self.phase == "up" and knee_angle < KNEE_DOWN:
            self.phase = "down"
            self._min_knee = knee_angle
            self._max_lean = lean
            self.cue = "Down..."
        elif self.phase == "down" and knee_angle > KNEE_UP:
            self.phase = "up"
            self.reps += 1
            self.last_rep_feedback = self._grade_rep()
            self.cue = self.last_rep_feedback

        if self.phase == "down":
            self.cue = "Down..." if knee_angle > DEPTH_OK else "Good depth — drive up"

        return self._state(knee_angle=knee_angle, lean=lean, tracking=True)

    def _grade_rep(self) -> str:
        problems = []
        if self._min_knee > DEPTH_OK:
            problems.append("squat deeper")
        if self._max_lean > LEAN_MAX:
            problems.append("chest up")
        return "Good rep" if not problems else " + ".join(problems).capitalize()

    def _state(self, knee_angle, lean, tracking: bool) -> dict:
        return {
            "exercise": self.name,
            "reps": self.reps,
            "phase": self.phase,
            "cue": self.cue,
            "last_rep_feedback": self.last_rep_feedback,
            "knee_angle": round(knee_angle, 1) if knee_angle is not None else None,
            "torso_lean": round(lean, 1) if lean is not None else None,
            "tracking": tracking,
        }
