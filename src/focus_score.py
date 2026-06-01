"""
Calculates focus score and status based on face detection and gaze zone.
"""
import src.config as config

class FocusScoreCalculator:
    def __init__(self):
        self.current_score = 100
        
    def calculate(self, face_detected, gaze_zone, head_yaw, head_pitch, eye_aspect_ratio=0, eye_x=0.5, eye_y=0.5):
        """
        Calculates focus score with simple moving average/penalties to avoid jitter.
        Returns focus_score, focus_status.
        """
        # Base adjustment amounts
        RECOVERY_RATE = 5
        PENALTY_AWAY = 10
        PENALTY_DISTRACTED = 5
        
        target_score = 100
        
        if not face_detected or gaze_zone == "No Face":
            target_score -= PENALTY_AWAY * 5 # Max penalty if no face
        elif gaze_zone == "Away":
            target_score -= PENALTY_AWAY * 3
        elif gaze_zone == "Reading":
            target_score = config.READING_FOCUS_SCORE
        elif gaze_zone in ["Left", "Right", "Up", "Down"]:
            yaw_penalty = min(30, abs(head_yaw) * 0.5)
            pitch_penalty = min(30, abs(head_pitch) * 0.5)
            eye_penalty = min(45, (abs(eye_x - 0.5) + abs(eye_y - 0.5)) * 80)
            target_score -= max(yaw_penalty, pitch_penalty, eye_penalty)

        if face_detected and eye_aspect_ratio and eye_aspect_ratio < config.DROWSY_EAR_THRESHOLD:
            target_score -= 35
            
        target_score = max(0, min(100, target_score))
        
        # Smooth the score to prevent rapid jumping
        # If dropping, drop faster. If recovering, recover slower.
        if target_score < self.current_score:
            self.current_score = max(target_score, self.current_score - 15)
        else:
            self.current_score = min(target_score, self.current_score + RECOVERY_RATE)
            
        score = int(self.current_score)
        
        # Determine Status
        if score >= config.FOCUSED_THRESHOLD:
            status = "Focused"
        elif score >= config.DISTRACTED_THRESHOLD:
            status = "Distracted"
        else:
            status = "Away"
            
        return score, status
