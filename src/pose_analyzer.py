"""
Pose analyzer for extracting body landmarks using MediaPipe Pose.
"""
import cv2
import mediapipe as mp
import src.config as config


_POSE_LANDMARK_NAMES = [
    "NOSE",
    "LEFT_EYE_INNER",
    "LEFT_EYE",
    "LEFT_EYE_OUTER",
    "RIGHT_EYE_INNER",
    "RIGHT_EYE",
    "RIGHT_EYE_OUTER",
    "LEFT_EAR",
    "RIGHT_EAR",
    "MOUTH_LEFT",
    "MOUTH_RIGHT",
    "LEFT_SHOULDER",
    "RIGHT_SHOULDER",
    "LEFT_ELBOW",
    "RIGHT_ELBOW",
    "LEFT_WRIST",
    "RIGHT_WRIST",
    "LEFT_PINKY",
    "RIGHT_PINKY",
    "LEFT_INDEX",
    "RIGHT_INDEX",
    "LEFT_THUMB",
    "RIGHT_THUMB",
    "LEFT_HIP",
    "RIGHT_HIP",
    "LEFT_KNEE",
    "RIGHT_KNEE",
    "LEFT_ANKLE",
    "RIGHT_ANKLE",
    "LEFT_HEEL",
    "RIGHT_HEEL",
    "LEFT_FOOT_INDEX",
    "RIGHT_FOOT_INDEX",
]


class PoseAnalyzer:
    def __init__(self):
        self._mode = "unknown"
        self._available = True
        self._pose = None

        if hasattr(mp, "solutions"):
            # Legacy MediaPipe "solutions" API.
            self._mode = "solutions"
            self.mp_pose = mp.solutions.pose
            self.pose = self.mp_pose.Pose(
                min_detection_confidence=config.MIN_DETECTION_CONFIDENCE,
                min_tracking_confidence=config.MIN_TRACKING_CONFIDENCE,
            )
            self.mp_drawing = mp.solutions.drawing_utils
            return

        # MediaPipe Tasks API (newer builds of mediapipe).
        self._mode = "tasks"
        try:
            from mediapipe.tasks.python import vision
            from mediapipe.tasks.python.core import base_options

            options = vision.PoseLandmarkerOptions(
                base_options=base_options.BaseOptions(model_asset_path=config.POSE_MODEL_PATH),
                running_mode=vision.RunningMode.IMAGE,
                min_pose_detection_confidence=config.MIN_DETECTION_CONFIDENCE,
                min_pose_presence_confidence=config.MIN_DETECTION_CONFIDENCE,
                min_tracking_confidence=config.MIN_TRACKING_CONFIDENCE,
            )
            self._pose = vision.PoseLandmarker.create_from_options(options)
        except Exception as exc:
            self._available = False
            print(
                "PoseAnalyzer unavailable. Expected MediaPipe Tasks pose model at "
                f"{config.POSE_MODEL_PATH}. Error: {exc}"
            )

    def analyze(self, frame):
        """
        Analyzes the frame and returns pose results and landmarks dictionary.
        """
        if not self._available:
            return None, None

        image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        if self._mode == "solutions":
            results = self.pose.process(image_rgb)
            landmarks_data = None
            if results.pose_landmarks:
                landmarks_data = {}
                for idx, landmark in enumerate(results.pose_landmarks.landmark):
                    landmarks_data[self.mp_pose.PoseLandmark(idx).name] = {
                        "x": landmark.x,
                        "y": landmark.y,
                        "z": landmark.z,
                        "visibility": landmark.visibility,
                    }
            return results, landmarks_data

        # tasks mode
        from mediapipe.tasks.python.vision.core.image import Image, ImageFormat

        mp_image = Image(image_format=ImageFormat.SRGB, data=image_rgb)
        results = self._pose.detect(mp_image)

        landmarks_data = None
        if getattr(results, "pose_landmarks", None):
            # pose_landmarks: List[List[NormalizedLandmark]] for multiple poses.
            pose = results.pose_landmarks[0] if results.pose_landmarks else None
            if pose:
                landmarks_data = {}
                for idx, landmark in enumerate(pose):
                    name = _POSE_LANDMARK_NAMES[idx] if idx < len(_POSE_LANDMARK_NAMES) else f"IDX_{idx}"
                    landmarks_data[name] = {
                        "x": landmark.x,
                        "y": landmark.y,
                        "z": getattr(landmark, "z", 0.0),
                        "visibility": getattr(landmark, "visibility", 1.0),
                    }

        return results, landmarks_data

    def draw_landmarks(self, frame, results):
        """
        Draws pose landmarks on the frame for debugging.
        """
        if not results:
            return frame

        if self._mode == "solutions":
            if results.pose_landmarks:
                self.mp_drawing.draw_landmarks(frame, results.pose_landmarks, self.mp_pose.POSE_CONNECTIONS)
            return frame

        # tasks mode: draw keypoints (simple, fast).
        pose_landmarks = getattr(results, "pose_landmarks", None)
        if not pose_landmarks:
            return frame

        landmarks = pose_landmarks[0] if pose_landmarks else None
        if not landmarks:
            return frame

        h, w, _ = frame.shape
        for landmark in landmarks:
            x = int(landmark.x * w)
            y = int(landmark.y * h)
            cv2.circle(frame, (x, y), 2, (0, 255, 0), -1)
        return frame
