"""
Estimate relative face-to-screen distance from face landmark size.
"""
import src.config as config


class DistanceAnalyzer:
    def estimate_distance(self, face_landmarks):
        """
        Return relative distance state from face bbox size.
        This is a visual proxy, not a real-world centimeter estimate.
        """
        if not face_landmarks:
            return {
                "distance_state": "No Face",
                "face_width_ratio": 0,
                "face_height_ratio": 0,
                "face_area_ratio": 0,
            }

        xs = [landmark.x for landmark in face_landmarks if hasattr(landmark, "x")]
        ys = [landmark.y for landmark in face_landmarks if hasattr(landmark, "y")]
        if not xs or not ys:
            return {
                "distance_state": "No Face",
                "face_width_ratio": 0,
                "face_height_ratio": 0,
                "face_area_ratio": 0,
            }

        face_width_ratio = max(xs) - min(xs)
        face_height_ratio = max(ys) - min(ys)
        face_area_ratio = face_width_ratio * face_height_ratio

        if face_width_ratio >= config.FACE_TOO_CLOSE_WIDTH_RATIO:
            distance_state = "Too Close"
        elif face_width_ratio <= config.FACE_TOO_FAR_WIDTH_RATIO:
            distance_state = "Too Far"
        else:
            distance_state = "Normal Distance"

        return {
            "distance_state": distance_state,
            "face_width_ratio": face_width_ratio,
            "face_height_ratio": face_height_ratio,
            "face_area_ratio": face_area_ratio,
        }
