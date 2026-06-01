"""
Detect blink and eye closure state from eye landmarks.
"""
import time

import src.config as config
from src.gaze_analyzer import GazeAnalyzer


class EyeAnalyzer:
    def __init__(self):
        self.gaze_analyzer = GazeAnalyzer()
        self.eye_was_closed = False
        self.eye_closed_started_at = None
        self.blink_count = 0

    def reset(self):
        self.eye_was_closed = False
        self.eye_closed_started_at = None
        self.blink_count = 0

    def analyze(self, face_landmarks):
        eye_aspect_ratio = self.gaze_analyzer.estimate_eye_aspect_ratio(face_landmarks)
        now = time.time()

        if face_landmarks is None:
            self.eye_was_closed = False
            self.eye_closed_started_at = None
            return self._result("No Face", eye_aspect_ratio, 0)

        eye_closed = eye_aspect_ratio < config.DROWSY_EAR_THRESHOLD
        if eye_closed and not self.eye_was_closed:
            self.eye_closed_started_at = now

        eye_closed_duration = 0
        if eye_closed and self.eye_closed_started_at is not None:
            eye_closed_duration = now - self.eye_closed_started_at

        eye_state = "Eye Open"
        if eye_closed:
            if eye_closed_duration >= config.LONG_EYE_CLOSURE_SECONDS:
                eye_state = "Long Eye Closure"
            else:
                eye_state = "Blink"
        elif self.eye_was_closed:
            previous_duration = 0 if self.eye_closed_started_at is None else now - self.eye_closed_started_at
            if previous_duration <= config.BLINK_MAX_SECONDS:
                self.blink_count += 1
            self.eye_closed_started_at = None

        self.eye_was_closed = eye_closed
        return self._result(eye_state, eye_aspect_ratio, eye_closed_duration)

    def _result(self, eye_state, eye_aspect_ratio, eye_closed_duration):
        return {
            "eye_state": eye_state,
            "eye_aspect_ratio": eye_aspect_ratio,
            "blink_count": self.blink_count,
            "eye_closed_duration": eye_closed_duration,
            "drowsy": eye_state == "Long Eye Closure",
        }
