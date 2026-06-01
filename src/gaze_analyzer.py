"""
Gaze analyzer for estimating rough gaze zone based on face landmarks.
We use head pose estimation (yaw, pitch) as a proxy for coarse gaze.
"""
import numpy as np

import src.config as config

class GazeAnalyzer:
    def __init__(self):
        self.left_eye_indices = [33, 160, 158, 133, 153, 144]
        self.right_eye_indices = [362, 385, 387, 263, 373, 380]
        self.left_iris_indices = [468, 469, 470, 471, 472]
        self.right_iris_indices = [473, 474, 475, 476, 477]

    def estimate_eye_aspect_ratio(self, face_landmarks):
        """
        Estimates blink/drowsiness signal using Eye Aspect Ratio (EAR).
        Lower values mean the eye appears more closed.
        """
        if face_landmarks is None:
            return 0

        try:
            left_ear = self._calculate_ear(face_landmarks, self.left_eye_indices)
            right_ear = self._calculate_ear(face_landmarks, self.right_eye_indices)
            return (left_ear + right_ear) / 2.0
        except (IndexError, ZeroDivisionError):
            return 0

    def _calculate_ear(self, landmarks, indices):
        p1 = np.array([landmarks[indices[0]].x, landmarks[indices[0]].y])
        p2 = np.array([landmarks[indices[1]].x, landmarks[indices[1]].y])
        p3 = np.array([landmarks[indices[2]].x, landmarks[indices[2]].y])
        p4 = np.array([landmarks[indices[3]].x, landmarks[indices[3]].y])
        p5 = np.array([landmarks[indices[4]].x, landmarks[indices[4]].y])
        p6 = np.array([landmarks[indices[5]].x, landmarks[indices[5]].y])

        vertical_1 = np.linalg.norm(p2 - p6)
        vertical_2 = np.linalg.norm(p3 - p5)
        horizontal = np.linalg.norm(p1 - p4)
        return (vertical_1 + vertical_2) / (2.0 * horizontal)

    def estimate_gaze(self, face_landmarks, frame_width, frame_height):
        """
        Estimates coarse gaze zone and normalized eye position.
        eye_x/eye_y are approximate iris positions inside the eye box.
        """
        if face_landmarks is None:
            return "No Face", 0, 0, 0.5, 0.5
            
        # Simplified Head Pose Estimation
        # We'll use the nose tip, chin, left eye, right eye, left mouth, right mouth
        # MediaPipe Face Mesh landmark indices
        nose_tip = face_landmarks[1]
        chin = face_landmarks[152]
        left_eye = face_landmarks[33]
        right_eye = face_landmarks[263]
        
        # Calculate 2D positions
        nx, ny = nose_tip.x, nose_tip.y
        cx, cy = chin.x, chin.y
        lex, ley = left_eye.x, left_eye.y
        rex, rey = right_eye.x, right_eye.y
        
        # Head Yaw (Left/Right)
        # Ratio of left eye to nose vs right eye to nose
        dist_left = nx - lex
        dist_right = rex - nx
        
        # Handle divide by zero
        if dist_left + dist_right == 0:
            yaw_ratio = 0.5
        else:
            yaw_ratio = dist_left / (dist_left + dist_right)
            
        # Mapping ratio to rough angles (0.5 is center)
        # Roughly: < 0.4 Right, > 0.6 Left
        head_yaw = (yaw_ratio - 0.5) * 100 # -50 to 50 scale roughly
        
        # Head Pitch (Up/Down)
        # Ratio of eye-to-nose vs nose-to-chin
        eye_y = (ley + rey) / 2
        dist_eye_nose = ny - eye_y
        dist_nose_chin = cy - ny
        
        if dist_nose_chin == 0:
            pitch_ratio = 0.5
        else:
            pitch_ratio = dist_eye_nose / dist_nose_chin
            
        # Normal pitch ratio is roughly 0.6 to 0.8
        # We map it to a centered value
        # < 0.5 Up, > 0.9 Down
        head_pitch = (pitch_ratio - 0.7) * 100 # -20 to 20 scale roughly

        eye_x, eye_y = self._estimate_iris_position(face_landmarks)

        if eye_y > config.GAZE_DOWN_THRESHOLD and abs(head_yaw) < 35:
            gaze_zone = "Reading"
        elif abs(head_yaw) > 48 or abs(head_pitch) > 58:
            gaze_zone = "Away"
        elif eye_x < 0.18 or eye_x > 0.82:
            gaze_zone = "Away"
        elif eye_x < config.GAZE_LEFT_THRESHOLD:
            gaze_zone = "Left"
        elif eye_x > config.GAZE_RIGHT_THRESHOLD:
            gaze_zone = "Right"
        elif eye_y < config.GAZE_UP_THRESHOLD:
            gaze_zone = "Up"
        elif eye_y > config.GAZE_DOWN_THRESHOLD:
            if head_pitch > config.READING_HEAD_PITCH_THRESHOLD or abs(head_yaw) < 35:
                gaze_zone = "Reading"
            else:
                gaze_zone = "Down"
        elif head_yaw > 24:
            gaze_zone = "Left"
        elif head_yaw < -24:
            gaze_zone = "Right"
        elif head_pitch > 26:
            gaze_zone = "Reading"
        elif head_pitch < -24:
            gaze_zone = "Up"
        else:
            gaze_zone = "Center"
            
        return gaze_zone, head_yaw, head_pitch, eye_x, eye_y

    def _estimate_iris_position(self, face_landmarks):
        if len(face_landmarks) < 478:
            return 0.5, 0.5

        left_eye_x, left_eye_y = self._eye_position(
            face_landmarks,
            corner_left_idx=33,
            corner_right_idx=133,
            top_idx=159,
            bottom_idx=145,
            iris_indices=self.left_iris_indices,
        )
        right_eye_x, right_eye_y = self._eye_position(
            face_landmarks,
            corner_left_idx=362,
            corner_right_idx=263,
            top_idx=386,
            bottom_idx=374,
            iris_indices=self.right_iris_indices,
        )
        return (left_eye_x + right_eye_x) / 2.0, (left_eye_y + right_eye_y) / 2.0

    def _eye_position(self, landmarks, corner_left_idx, corner_right_idx, top_idx, bottom_idx, iris_indices):
        corner_left = landmarks[corner_left_idx]
        corner_right = landmarks[corner_right_idx]
        eye_top = landmarks[top_idx]
        eye_bottom = landmarks[bottom_idx]
        iris_x = sum(landmarks[idx].x for idx in iris_indices) / len(iris_indices)
        iris_y = sum(landmarks[idx].y for idx in iris_indices) / len(iris_indices)

        min_x = min(corner_left.x, corner_right.x)
        max_x = max(corner_left.x, corner_right.x)
        min_y = min(eye_top.y, eye_bottom.y)
        max_y = max(eye_top.y, eye_bottom.y)
        eye_x = (iris_x - min_x) / max(max_x - min_x, 0.001)
        eye_y = (iris_y - min_y) / max(max_y - min_y, 0.001)
        return float(np.clip(eye_x, 0, 1)), float(np.clip(eye_y, 0, 1))
