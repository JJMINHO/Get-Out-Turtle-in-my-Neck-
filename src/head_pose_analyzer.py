"""
Estimate lightweight head pose from MediaPipe face landmarks.
"""
import math

import src.config as config


class HeadPoseAnalyzer:
    def estimate_head_pose(self, face_landmarks):
        if face_landmarks is None:
            return {
                "head_yaw": 0,
                "head_pitch": 0,
                "head_roll": 0,
                "head_state": "No Face",
            }

        try:
            nose_tip = face_landmarks[1]
            chin = face_landmarks[152]
            left_eye = face_landmarks[33]
            right_eye = face_landmarks[263]

            dist_left = nose_tip.x - left_eye.x
            dist_right = right_eye.x - nose_tip.x
            yaw_ratio = dist_left / max(dist_left + dist_right, 0.001)
            head_yaw = (yaw_ratio - 0.5) * 100

            eye_y = (left_eye.y + right_eye.y) / 2
            pitch_ratio = (nose_tip.y - eye_y) / max(chin.y - nose_tip.y, 0.001)
            head_pitch = (pitch_ratio - 0.7) * 100

            head_roll = math.degrees(math.atan2(right_eye.y - left_eye.y, right_eye.x - left_eye.x))
            head_state = self._classify_head_state(head_yaw, head_pitch, head_roll)
            return {
                "head_yaw": head_yaw,
                "head_pitch": head_pitch,
                "head_roll": head_roll,
                "head_state": head_state,
            }
        except (IndexError, ZeroDivisionError):
            return {
                "head_yaw": 0,
                "head_pitch": 0,
                "head_roll": 0,
                "head_state": "No Face",
            }

    def _classify_head_state(self, head_yaw, head_pitch, head_roll):
        if abs(head_roll) >= config.HEAD_ROLL_TILT_THRESHOLD:
            return "Head Tilted"
        if head_yaw >= config.HEAD_YAW_THRESHOLD:
            return "Looking Left"
        if head_yaw <= -config.HEAD_YAW_THRESHOLD:
            return "Looking Right"
        if head_pitch >= config.HEAD_PITCH_DOWN_THRESHOLD:
            return "Looking Down"
        if head_pitch <= -config.HEAD_PITCH_UP_THRESHOLD:
            return "Looking Up"
        return "Forward"
