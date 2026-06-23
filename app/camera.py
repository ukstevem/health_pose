"""Webcam capture + MediaPipe Pose + overlay drawing.

This module is the only owner of the camera. It runs the pose estimation,
feeds keypoints to the active exercise tracker, draws an annotated frame for
the MJPEG stream, and publishes the latest tracker state for the WebSocket to
read. OpenCV does capture + drawing only (never pose); MediaPipe does pose.
"""
from __future__ import annotations

import os
import threading
from typing import Dict, Optional

import cv2
import mediapipe as mp

from .exercises import make_tracker

mp_pose = mp.solutions.pose
mp_draw = mp.solutions.drawing_utils
mp_styles = mp.solutions.drawing_styles

# MediaPipe landmark index -> our snake_case name (only the joints we use).
_WANTED = {
    mp_pose.PoseLandmark.LEFT_SHOULDER: "left_shoulder",
    mp_pose.PoseLandmark.RIGHT_SHOULDER: "right_shoulder",
    mp_pose.PoseLandmark.LEFT_HIP: "left_hip",
    mp_pose.PoseLandmark.RIGHT_HIP: "right_hip",
    mp_pose.PoseLandmark.LEFT_KNEE: "left_knee",
    mp_pose.PoseLandmark.RIGHT_KNEE: "right_knee",
    mp_pose.PoseLandmark.LEFT_ANKLE: "left_ankle",
    mp_pose.PoseLandmark.RIGHT_ANKLE: "right_ankle",
}


def _extract_landmarks(results, w: int, h: int) -> Dict[str, tuple]:
    """Map MediaPipe results to {name: (x_px, y_px, visibility)}.

    Pixel coordinates (not normalised) so joint angles are not distorted by the
    frame aspect ratio.
    """
    out: Dict[str, tuple] = {}
    if not results.pose_landmarks:
        return out
    for idx, name in _WANTED.items():
        p = results.pose_landmarks.landmark[idx]
        out[name] = (p.x * w, p.y * h, p.visibility)
    return out


class CameraPipeline:
    def __init__(self) -> None:
        self.cam_index = int(os.environ.get("HP_CAM_INDEX", "0"))
        self.width = int(os.environ.get("HP_WIDTH", "960"))
        self.height = int(os.environ.get("HP_HEIGHT", "540"))
        self.tracker = make_tracker("squat")
        self._state: dict = self.tracker._state(None, None, False)
        self._lock = threading.Lock()
        self._pose: Optional[mp_pose.Pose] = None
        self._cap: Optional[cv2.VideoCapture] = None

    # --- public API -----------------------------------------------------------
    def state(self) -> dict:
        with self._lock:
            return dict(self._state)

    def set_exercise(self, name: str) -> None:
        with self._lock:
            self.tracker = make_tracker(name)
            self._state = self.tracker._state(None, None, False)

    def reset(self) -> None:
        with self._lock:
            self.tracker.reset()

    # --- frame source ----------------------------------------------------------
    def _ensure_open(self) -> None:
        if self._pose is None:
            self._pose = mp_pose.Pose(
                model_complexity=1,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5,
            )
        if self._cap is None or not self._cap.isOpened():
            cap = cv2.VideoCapture(self.cam_index, cv2.CAP_DSHOW)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self._cap = cap

    def frames(self):
        """Generator of JPEG bytes for an MJPEG multipart stream."""
        self._ensure_open()
        if not self._cap or not self._cap.isOpened():
            yield self._jpeg(self._error_frame("Cannot open camera "
                                               f"(index {self.cam_index})"))
            return

        while True:
            ok, frame = self._cap.read()
            if not ok:
                yield self._jpeg(self._error_frame("Camera read failed"))
                continue

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            rgb.flags.writeable = False
            results = self._pose.process(rgb)

            h, w = frame.shape[:2]
            lm = _extract_landmarks(results, w, h)
            if lm:
                with self._lock:
                    self._state = self.tracker.update(lm)

            self._draw(frame, results)
            yield self._jpeg(frame)

    # --- drawing ---------------------------------------------------------------
    def _draw(self, frame, results) -> None:
        if results.pose_landmarks:
            mp_draw.draw_landmarks(
                frame,
                results.pose_landmarks,
                mp_pose.POSE_CONNECTIONS,
                landmark_drawing_spec=mp_styles.get_default_pose_landmarks_style(),
            )
        s = self.state()
        lines = [
            f"REPS: {s['reps']}",
            f"{s['phase'].upper()}  knee={s['knee_angle']}  lean={s['torso_lean']}",
            s.get("cue", ""),
        ]
        y = 34
        for i, text in enumerate(lines):
            scale = 1.1 if i == 0 else 0.6
            thick = 3 if i == 0 else 2
            cv2.putText(frame, text, (16, y), cv2.FONT_HERSHEY_SIMPLEX, scale,
                        (0, 0, 0), thick + 2, cv2.LINE_AA)
            cv2.putText(frame, text, (16, y), cv2.FONT_HERSHEY_SIMPLEX, scale,
                        (0, 255, 0), thick, cv2.LINE_AA)
            y += 40 if i == 0 else 28

    def _error_frame(self, msg: str):
        import numpy as np
        frame = np.zeros((self.height, self.width, 3), dtype="uint8")
        cv2.putText(frame, msg, (20, self.height // 2),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2, cv2.LINE_AA)
        return frame

    @staticmethod
    def _jpeg(frame) -> bytes:
        ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        payload = buf.tobytes() if ok else b""
        return (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + payload + b"\r\n")


# Module-level singleton — the one camera owner for the process.
pipeline = CameraPipeline()
