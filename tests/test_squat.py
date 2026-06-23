"""Unit tests for the squat rep/form state machine.

No camera or MediaPipe needed: we synthesise landmark dicts with a known knee
angle and feed sequences through the tracker. Geometry: place the knee at a
fixed point with the hip straight above it; the ankle is positioned so the
hip-knee-ankle angle equals the target knee angle.
"""
import math

from app.exercises.squat import SquatTracker


def landmarks(knee_angle: float, lean: float = 0.0, vis: float = 1.0) -> dict:
    """Build a side-on landmark set with the given knee angle (degrees)."""
    knee = (100.0, 300.0)
    hip = (100.0, 200.0)  # straight above the knee (up = smaller y)

    # knee->hip points up (0,-1); choose knee->ankle so the interior angle
    # at the knee equals knee_angle. a = 180 - knee_angle.
    a = math.radians(180.0 - knee_angle)
    ankle = (knee[0] + 100.0 * math.sin(a), knee[1] + 100.0 * math.cos(a))

    # Shoulder above the hip, tilted forward by `lean` degrees from vertical.
    lr = math.radians(lean)
    shoulder = (hip[0] + 100.0 * math.sin(lr), hip[1] - 100.0 * math.cos(lr))

    lm = {}
    for side in ("left", "right"):
        lm[f"{side}_shoulder"] = (*shoulder, vis)
        lm[f"{side}_hip"] = (*hip, vis)
        lm[f"{side}_knee"] = (*knee, vis)
        lm[f"{side}_ankle"] = (*ankle, vis)
    return lm


def feed(tracker, angles, lean=0.0):
    state = None
    for ang in angles:
        state = tracker.update(landmarks(ang, lean=lean))
    return state


def test_counts_one_good_rep():
    t = SquatTracker()
    state = feed(t, [175, 150, 110, 90, 110, 150, 175])
    assert state["reps"] == 1
    assert state["last_rep_feedback"] == "Good rep"


def test_counts_multiple_reps():
    t = SquatTracker()
    cycle = [175, 110, 90, 110, 175]
    feed(t, cycle * 3)
    assert t.reps == 3


def test_shallow_rep_flags_depth():
    # Bends past KNEE_DOWN (120) but never reaches DEPTH_OK (100).
    t = SquatTracker()
    state = feed(t, [175, 150, 115, 110, 115, 150, 175])
    assert state["reps"] == 1
    assert "deeper" in state["last_rep_feedback"].lower()


def test_excessive_lean_flags_chest_up():
    t = SquatTracker()
    state = feed(t, [175, 110, 90, 110, 175], lean=60.0)
    assert state["reps"] == 1
    assert "chest up" in state["last_rep_feedback"].lower()


def test_tiny_bob_does_not_count():
    # Never crosses KNEE_DOWN, so no rep.
    t = SquatTracker()
    state = feed(t, [175, 165, 150, 165, 175])
    assert state["reps"] == 0


def test_low_visibility_does_not_track():
    t = SquatTracker()
    state = t.update(landmarks(90, vis=0.1))
    assert state["tracking"] is False
    assert state["reps"] == 0
