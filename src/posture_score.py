"""
Calculates posture score and status based on pose landmarks.
"""
import math
import statistics
import time

import src.config as config

class PostureScoreCalculator:
    def __init__(self):
        self.calibration_started_at = None
        self.baseline_samples = []
        self.baseline_face_shoulder_ratio = None
        self.baseline_head_height_ratio = None
        self.baseline_shoulder_y = None
        self.baseline_torso_height_ratio = None
        self.smoothed_metrics = None
        self.smoothed_score = None
        self.calibrated = False

    def _calculate_angle(self, p1, p2, p3):
        """
        Calculate angle between 3 points. p2 is the vertex.
        """
        radians = math.atan2(p3['y'] - p2['y'], p3['x'] - p2['x']) - \
                  math.atan2(p1['y'] - p2['y'], p1['x'] - p2['x'])
        angle = abs(radians * 180.0 / math.pi)
        if angle > 180.0:
            angle = 360 - angle
        return angle

    def _calculate_slope(self, p1, p2):
        """
        Calculate slope (angle from horizontal) between 2 points.
        """
        dx = p2['x'] - p1['x']
        dy = p2['y'] - p1['y']
        angle = abs(math.atan2(dy, dx) * 180.0 / math.pi)
        return angle

    def _midpoint(self, p1, p2):
        return {'x': (p1['x'] + p2['x']) / 2, 'y': (p1['y'] + p2['y']) / 2}

    def _distance(self, p1, p2):
        return math.hypot(p2['x'] - p1['x'], p2['y'] - p1['y'])

    def reset_calibration(self):
        self.calibration_started_at = None
        self.baseline_samples = []
        self.baseline_face_shoulder_ratio = None
        self.baseline_head_height_ratio = None
        self.baseline_shoulder_y = None
        self.baseline_torso_height_ratio = None
        self.smoothed_metrics = None
        self.smoothed_score = None
        self.calibrated = False

    def calculate(self, pose_landmarks, face_landmarks=None):
        """
        Calculates posture metrics and overall score.
        Returns score, status, head_offset, shoulder_slope, torso_offset,
        face_ratio_delta, turtle_neck_risk, slouch_delta, slouch_risk.
        """
        if not pose_landmarks:
            return 0, "No Pose", 0, 0, 0, 0, "Unknown", 0, "Unknown"

        try:
            # Extract necessary landmarks
            nose = pose_landmarks.get('NOSE')
            l_shoulder = pose_landmarks.get('LEFT_SHOULDER')
            r_shoulder = pose_landmarks.get('RIGHT_SHOULDER')
            l_hip = pose_landmarks.get('LEFT_HIP')
            r_hip = pose_landmarks.get('RIGHT_HIP')
            l_ear = pose_landmarks.get('LEFT_EAR')
            r_ear = pose_landmarks.get('RIGHT_EAR')
            l_eye = pose_landmarks.get('LEFT_EYE')
            r_eye = pose_landmarks.get('RIGHT_EYE')

            if not all([nose, l_shoulder, r_shoulder, l_hip, r_hip, l_ear, r_ear, l_eye, r_eye]):
                 return 0, "Missing Landmarks", 0, 0, 0, 0, "Unknown", 0, "Unknown"

            mid_shoulder = self._midpoint(l_shoulder, r_shoulder)
            mid_ear = self._midpoint(l_ear, r_ear)
            mid_hip = self._midpoint(l_hip, r_hip)
            shoulder_width = max(self._distance(l_shoulder, r_shoulder), 0.001)
            face_width = self._calculate_face_width(face_landmarks)
            if face_width is None:
                face_width = max(self._distance(l_ear, r_ear), self._distance(l_eye, r_eye), 0.001)
            face_shoulder_ratio = face_width / shoulder_width

            # Front-facing webcam proxies normalized by shoulder width.
            head_offset_ratio = abs(nose['x'] - mid_shoulder['x']) / shoulder_width
            head_height_ratio = (mid_shoulder['y'] - nose['y']) / shoulder_width
            torso_height_ratio = max(mid_hip['y'] - mid_shoulder['y'], 0) / shoulder_width
            torso_offset_ratio = abs(mid_shoulder['x'] - mid_hip['x']) / shoulder_width
            shoulder_angle = self._calculate_slope(r_shoulder, l_shoulder)
            shoulder_slope = abs(180 - shoulder_angle) if shoulder_angle > 90 else abs(shoulder_angle)

            calibration_status = self._update_calibration(
                face_shoulder_ratio,
                head_height_ratio,
                mid_shoulder['y'],
                torso_height_ratio,
            )
            if calibration_status != "Ready":
                remaining = self._calibration_remaining_seconds()
                return (
                    100, f"Calibrating {remaining}s", head_offset_ratio * 100, shoulder_slope,
                    torso_offset_ratio * 100, 0, "Calibrating", 0, "Calibrating"
                )

            metrics = self._smooth_metrics({
                "face_shoulder_ratio": face_shoulder_ratio,
                "head_height_ratio": head_height_ratio,
                "head_offset_ratio": head_offset_ratio,
                "torso_offset_ratio": torso_offset_ratio,
                "shoulder_slope": shoulder_slope,
                "shoulder_y": mid_shoulder['y'],
                "torso_height_ratio": torso_height_ratio,
            })

            face_shoulder_ratio = metrics["face_shoulder_ratio"]
            head_height_ratio = metrics["head_height_ratio"]
            head_offset_ratio = metrics["head_offset_ratio"]
            torso_offset_ratio = metrics["torso_offset_ratio"]
            shoulder_slope = metrics["shoulder_slope"]
            shoulder_y = metrics["shoulder_y"]
            torso_height_ratio = metrics["torso_height_ratio"]

            neck_angle = head_offset_ratio * 100
            torso_lean = torso_offset_ratio * 100

            face_ratio_delta = face_shoulder_ratio - self.baseline_face_shoulder_ratio
            head_height_delta = self.baseline_head_height_ratio - head_height_ratio
            face_ratio_delta = self._apply_noise_floor(face_ratio_delta)
            head_height_delta = self._apply_noise_floor(head_height_delta)
            turtle_neck_signal = max(face_ratio_delta, head_height_delta * 0.35)
            shoulder_drop_delta = shoulder_y - self.baseline_shoulder_y
            torso_height_drop_delta = self.baseline_torso_height_ratio - torso_height_ratio
            shoulder_drop_delta = self._apply_noise_floor(shoulder_drop_delta)
            torso_height_drop_delta = self._apply_noise_floor(torso_height_drop_delta)
            slouch_signal = max(shoulder_drop_delta, torso_height_drop_delta)

            if turtle_neck_signal >= config.FACE_SHOULDER_RATIO_BAD:
                turtle_neck_risk = "High"
            elif turtle_neck_signal >= config.FACE_SHOULDER_RATIO_WARNING:
                turtle_neck_risk = "Medium"
            else:
                turtle_neck_risk = "Low"

            if slouch_signal >= config.SLOUCH_DROP_BAD or torso_height_drop_delta >= config.TORSO_HEIGHT_DROP_BAD:
                slouch_risk = "High"
            elif slouch_signal >= config.SLOUCH_DROP_WARNING or torso_height_drop_delta >= config.TORSO_HEIGHT_DROP_WARNING:
                slouch_risk = "Medium"
            else:
                slouch_risk = "Low"

            score = 100

            if head_offset_ratio > config.HEAD_OFFSET_RATIO_THRESHOLD:
                score -= (head_offset_ratio - config.HEAD_OFFSET_RATIO_THRESHOLD) * 70

            if shoulder_slope > config.SHOULDER_SLOPE_THRESHOLD:
                score -= (shoulder_slope - config.SHOULDER_SLOPE_THRESHOLD) * 2.5

            if torso_offset_ratio > config.TORSO_OFFSET_RATIO_THRESHOLD:
                score -= (torso_offset_ratio - config.TORSO_OFFSET_RATIO_THRESHOLD) * 80

            if turtle_neck_signal > config.FACE_SHOULDER_RATIO_WARNING:
                score -= (turtle_neck_signal - config.FACE_SHOULDER_RATIO_WARNING) * 300

            if slouch_signal > config.SLOUCH_DROP_WARNING:
                score -= (slouch_signal - config.SLOUCH_DROP_WARNING) * 260

            score = max(0, min(100, score))
            if turtle_neck_risk == "High" or slouch_risk == "High":
                score = min(score, config.WARNING_THRESHOLD - 1)
            elif turtle_neck_risk == "Medium" or slouch_risk == "Medium":
                score = min(score, config.GOOD_THRESHOLD - 1)
            score = self._smooth_score(score)

            # Determine Status
            if score >= config.GOOD_THRESHOLD:
                status = "Good"
            elif score >= config.WARNING_THRESHOLD:
                status = "Warning"
            else:
                status = "Bad"

            return (
                score, status, neck_angle, shoulder_slope, torso_lean,
                face_ratio_delta, turtle_neck_risk, slouch_signal, slouch_risk
            )

        except Exception as e:
            print(f"Error calculating posture score: {e}")
            return 0, "Error", 0, 0, 0, 0, "Unknown", 0, "Unknown"

    def _update_calibration(self, face_shoulder_ratio, head_height_ratio, shoulder_y, torso_height_ratio):
        if self.calibrated:
            return "Ready"

        now = time.time()
        if self.calibration_started_at is None:
            self.calibration_started_at = now

        self.baseline_samples.append((face_shoulder_ratio, head_height_ratio, shoulder_y, torso_height_ratio))
        if now - self.calibration_started_at < config.CALIBRATION_SECONDS:
            return "Collecting"

        if not self.baseline_samples:
            return "Collecting"

        sample_count = len(self.baseline_samples)
        self.baseline_face_shoulder_ratio = statistics.median(sample[0] for sample in self.baseline_samples)
        self.baseline_head_height_ratio = statistics.median(sample[1] for sample in self.baseline_samples)
        self.baseline_shoulder_y = statistics.median(sample[2] for sample in self.baseline_samples)
        self.baseline_torso_height_ratio = statistics.median(sample[3] for sample in self.baseline_samples)
        self.calibrated = True
        print(
            "Posture baseline calibrated: "
            f"face/shoulder={self.baseline_face_shoulder_ratio:.3f}, "
            f"head_height={self.baseline_head_height_ratio:.3f}, "
            f"shoulder_y={self.baseline_shoulder_y:.3f}, "
            f"torso_height={self.baseline_torso_height_ratio:.3f}"
        )
        return "Ready"

    def _calculate_face_width(self, face_landmarks):
        if not face_landmarks:
            return None

        xs = [landmark.x for landmark in face_landmarks if hasattr(landmark, 'x')]
        if not xs:
            return None
        return max(max(xs) - min(xs), 0.001)

    def _smooth_metrics(self, metrics):
        if self.smoothed_metrics is None:
            self.smoothed_metrics = metrics
            return metrics

        alpha = config.POSTURE_SMOOTHING_ALPHA
        self.smoothed_metrics = {
            key: (alpha * metrics[key]) + ((1 - alpha) * self.smoothed_metrics[key])
            for key in metrics
        }
        return self.smoothed_metrics

    def _apply_noise_floor(self, value):
        if abs(value) < config.POSTURE_NOISE_FLOOR:
            return 0
        return value

    def _smooth_score(self, score):
        if self.smoothed_score is None:
            self.smoothed_score = score
        else:
            alpha = config.POSTURE_SMOOTHING_ALPHA
            self.smoothed_score = (alpha * score) + ((1 - alpha) * self.smoothed_score)
        return int(round(self.smoothed_score))

    def _calibration_remaining_seconds(self):
        if self.calibration_started_at is None:
            return config.CALIBRATION_SECONDS
        elapsed = time.time() - self.calibration_started_at
        return max(0, int(math.ceil(config.CALIBRATION_SECONDS - elapsed)))
