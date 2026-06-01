"""
Face analyzer for extracting face landmarks using MediaPipe Face Mesh.
"""
import cv2
import mediapipe as mp
import src.config as config


class FaceAnalyzer:
    def __init__(self):
        self._mode = "unknown"
        self._available = True
        self._face = None

        if hasattr(mp, "solutions"):
            self._mode = "solutions"
            self.mp_face_mesh = mp.solutions.face_mesh
            self.face_mesh = self.mp_face_mesh.FaceMesh(
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=config.MIN_DETECTION_CONFIDENCE,
                min_tracking_confidence=config.MIN_TRACKING_CONFIDENCE,
            )
            self.mp_drawing = mp.solutions.drawing_utils
            self.mp_drawing_styles = mp.solutions.drawing_styles
            return

        self._mode = "tasks"
        try:
            from mediapipe.tasks.python import vision
            from mediapipe.tasks.python.core import base_options

            options = vision.FaceLandmarkerOptions(
                base_options=base_options.BaseOptions(model_asset_path=config.FACE_MODEL_PATH),
                running_mode=vision.RunningMode.IMAGE,
                num_faces=1,
                min_face_detection_confidence=config.MIN_DETECTION_CONFIDENCE,
                min_face_presence_confidence=config.MIN_DETECTION_CONFIDENCE,
                min_tracking_confidence=config.MIN_TRACKING_CONFIDENCE,
                output_face_blendshapes=False,
                output_facial_transformation_matrixes=False,
            )
            self._face = vision.FaceLandmarker.create_from_options(options)
        except Exception as exc:
            self._available = False
            print(
                "FaceAnalyzer unavailable. Expected MediaPipe Tasks face model at "
                f"{config.FACE_MODEL_PATH}. Error: {exc}"
            )

    def analyze(self, frame):
        """
        Analyzes the frame and returns face results and landmarks.
        """
        if not self._available:
            return None, False, None

        image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        if self._mode == "solutions":
            results = self.face_mesh.process(image_rgb)
            face_detected = False
            landmarks_data = None
            if results.multi_face_landmarks:
                face_detected = True
                face_landmarks = results.multi_face_landmarks[0]
                landmarks_data = face_landmarks.landmark
            return results, face_detected, landmarks_data

        from mediapipe.tasks.python.vision.core.image import Image, ImageFormat

        mp_image = Image(image_format=ImageFormat.SRGB, data=image_rgb)
        results = self._face.detect(mp_image)

        face_detected = False
        landmarks_data = None
        face_landmarks = getattr(results, "face_landmarks", None)
        if face_landmarks:
            face_detected = True
            landmarks_data = face_landmarks[0]

        return results, face_detected, landmarks_data

    def draw_landmarks(self, frame, results):
        """
        Draws face landmarks on the frame for debugging.
        """
        if not results:
            return frame

        if self._mode == "solutions":
            if results.multi_face_landmarks:
                for face_landmarks in results.multi_face_landmarks:
                    self.mp_drawing.draw_landmarks(
                        image=frame,
                        landmark_list=face_landmarks,
                        connections=self.mp_face_mesh.FACEMESH_TESSELATION,
                        landmark_drawing_spec=None,
                        connection_drawing_spec=self.mp_drawing_styles.get_default_face_mesh_tesselation_style(),
                    )
                    self.mp_drawing.draw_landmarks(
                        image=frame,
                        landmark_list=face_landmarks,
                        connections=self.mp_face_mesh.FACEMESH_CONTOURS,
                        landmark_drawing_spec=None,
                        connection_drawing_spec=self.mp_drawing_styles.get_default_face_mesh_contours_style(),
                    )
                    self.mp_drawing.draw_landmarks(
                        image=frame,
                        landmark_list=face_landmarks,
                        connections=self.mp_face_mesh.FACEMESH_IRISES,
                        landmark_drawing_spec=None,
                        connection_drawing_spec=self.mp_drawing_styles.get_default_face_mesh_iris_connections_style(),
                    )
            return frame

        face_landmarks = getattr(results, "face_landmarks", None)
        if not face_landmarks:
            return frame

        landmarks = face_landmarks[0] if face_landmarks else None
        if not landmarks:
            return frame

        h, w, _ = frame.shape
        # Draw a sparse set of points to keep debug view responsive.
        step = 3
        for idx in range(0, len(landmarks), step):
            lm = landmarks[idx]
            x = int(lm.x * w)
            y = int(lm.y * h)
            cv2.circle(frame, (x, y), 1, (255, 255, 0), -1)
        return frame
