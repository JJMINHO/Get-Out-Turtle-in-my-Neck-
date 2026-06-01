"""
Background thread for camera capture and running the analysis loop.
"""
import cv2
import csv
import numpy as np
import os
import threading
import time
from datetime import datetime

import src.config as config
from src.distance_analyzer import DistanceAnalyzer
from src.eye_analyzer import EyeAnalyzer
from src.face_analyzer import FaceAnalyzer
from src.focus_score import FocusScoreCalculator
from src.gaze_analyzer import GazeAnalyzer
from src.head_pose_analyzer import HeadPoseAnalyzer
from src.pose_analyzer import PoseAnalyzer
from src.posture_score import PostureScoreCalculator
from src.study_event_segmenter import StudyEventSegmenter


class CameraWorker:
    def __init__(self, ui_callback=None):
        self.is_running = False
        self.show_debug = False
        self.debug_window_created = False
        self.latest_debug_frame = None
        self.debug_frame_lock = threading.Lock()
        self.thread = None
        self.ui_callback = ui_callback

        self.pose_analyzer = PoseAnalyzer()
        self.face_analyzer = FaceAnalyzer()
        self.distance_analyzer = DistanceAnalyzer()
        self.eye_analyzer = EyeAnalyzer()
        self.gaze_analyzer = GazeAnalyzer()
        self.head_pose_analyzer = HeadPoseAnalyzer()
        self.posture_calculator = PostureScoreCalculator()
        self.focus_calculator = FocusScoreCalculator()
        self.study_event_segmenter = StudyEventSegmenter()

        os.makedirs(os.path.dirname(config.CSV_LOG_PATH), exist_ok=True)
        if not os.path.exists(config.CSV_LOG_PATH):
            with open(config.CSV_LOG_PATH, "w", newline="") as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow([
                    "timestamp", "posture_score", "posture_status",
                    "head_offset_ratio", "shoulder_slope", "torso_offset_ratio",
                    "face_shoulder_delta", "turtle_neck_risk", "slouch_delta", "slouch_risk",
                    "focus_score", "focus_status", "face_detected",
                    "gaze_zone", "head_yaw", "head_pitch", "eye_x", "eye_y",
                    "head_roll", "head_state", "eye_aspect_ratio", "eye_state",
                    "blink_count", "eye_closed_duration", "drowsy",
                    "distance_state", "face_width_ratio", "face_area_ratio"
                ])

    def start(self):
        if not self.is_running:
            self.posture_calculator.reset_calibration()
            self.eye_analyzer.reset()
            self.is_running = True
            self.thread = threading.Thread(target=self._run_loop, daemon=True)
            self.thread.start()

    def stop(self):
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=2.0)
            self.thread = None

    def set_debug(self, state):
        self.show_debug = state
        if state:
            print("Debug window requested.")
        else:
            print("Debug window disabled.")
            with self.debug_frame_lock:
                self.latest_debug_frame = None

    def reset_calibration(self):
        self.posture_calculator.reset_calibration()
        self.eye_analyzer.reset()
        print("Posture calibration reset.")

    def _run_loop(self):
        cap = self._open_camera()
        if cap is None:
            self.is_running = False
            return

        last_log_time = 0

        while self.is_running:
            success, frame = cap.read()
            if not success:
                print("Failed to read frame.")
                break

            frame = cv2.flip(frame, 1)
            height, width, _ = frame.shape

            pose_results, pose_landmarks = self.pose_analyzer.analyze(frame)
            face_results, face_detected, face_landmarks = self.face_analyzer.analyze(frame)
            distance_result = self.distance_analyzer.estimate_distance(face_landmarks)
            (
                p_score, p_status, neck_angle, shoulder_slope, torso_lean,
                face_shoulder_delta, turtle_neck_risk, slouch_delta, slouch_risk
            ) = self.posture_calculator.calculate(pose_landmarks, face_landmarks)
            head_pose = self.head_pose_analyzer.estimate_head_pose(face_landmarks)

            gaze_zone, head_yaw, head_pitch, eye_x, eye_y = self.gaze_analyzer.estimate_gaze(
                face_landmarks,
                width,
                height,
            )
            head_yaw = head_pose["head_yaw"]
            head_pitch = head_pose["head_pitch"]
            eye_result = self.eye_analyzer.analyze(face_landmarks)
            eye_aspect_ratio = eye_result["eye_aspect_ratio"]
            drowsy = eye_result["drowsy"]

            f_score, f_status = self.focus_calculator.calculate(
                face_detected,
                gaze_zone,
                head_yaw,
                head_pitch,
                eye_aspect_ratio,
                eye_x,
                eye_y,
            )
            study_state = self.study_event_segmenter.update(
                p_score,
                p_status,
                f_score,
                f_status,
                face_detected,
                gaze_zone,
                drowsy,
            )

            if self.ui_callback:
                self.ui_callback(p_score, p_status, f_score, f_status)

            current_time = time.time()
            if current_time - last_log_time >= 1.0:
                self._log_data(p_score, p_status, neck_angle, shoulder_slope, torso_lean,
                               face_shoulder_delta, turtle_neck_risk, slouch_delta, slouch_risk,
                               f_score, f_status, face_detected, gaze_zone,
                               head_yaw, head_pitch, head_pose, eye_x, eye_y, eye_result,
                               distance_result)
                last_log_time = current_time

            if self.show_debug:
                try:
                    debug_frame = self._build_debug_frame(
                        frame, pose_results, face_results, p_score, p_status,
                        neck_angle, shoulder_slope, torso_lean,
                        face_shoulder_delta, turtle_neck_risk, slouch_delta, slouch_risk,
                        f_score, f_status, study_state, face_detected,
                        gaze_zone, head_yaw, head_pitch, head_pose,
                        eye_x, eye_y, eye_result, distance_result,
                    )
                    with self.debug_frame_lock:
                        self.latest_debug_frame = debug_frame
                except Exception as exc:
                    print(f"Debug window error; keeping camera running and disabling debug: {exc}")
                    self.show_debug = False
                    with self.debug_frame_lock:
                        self.latest_debug_frame = None
            else:
                with self.debug_frame_lock:
                    self.latest_debug_frame = None

            time.sleep(config.UPDATE_INTERVAL_SECONDS)

        cap.release()
        self.study_event_segmenter.close()
        cv2.destroyAllWindows()

    def _open_camera(self):
        backend = None
        if getattr(config, "CAMERA_BACKEND", None) == "avfoundation":
            backend = getattr(cv2, "CAP_AVFOUNDATION", None)

        indices = []
        try:
            indices.append(int(config.CAMERA_INDEX))
        except Exception:
            indices.append(0)

        for idx in getattr(config, "CAMERA_INDEX_FALLBACKS", []):
            if idx not in indices:
                indices.append(idx)

        last_error = None
        for camera_index in indices:
            try:
                cap = cv2.VideoCapture(camera_index, backend) if backend is not None else cv2.VideoCapture(camera_index)
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.FRAME_WIDTH)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)

                if cap.isOpened():
                    print(f"Camera opened: index={camera_index} backend={config.CAMERA_BACKEND}")
                    return cap

                last_error = f"cap.isOpened() == False (index={camera_index})"
                cap.release()
            except Exception as exc:
                last_error = f"{type(exc).__name__}: {exc} (index={camera_index})"

        print("Error: Could not open any camera index.")
        print("Tried indices:", indices)
        print("Backend:", getattr(config, "CAMERA_BACKEND", None))
        if last_error:
            print("Last error:", last_error)
        print("Check macOS permissions: System Settings -> Privacy & Security -> Camera.")
        print("Also ensure no other app is using the camera (Zoom/Meet/Photo Booth, etc).")
        return None

    def show_latest_debug_frame(self):
        with self.debug_frame_lock:
            debug_frame = None if self.latest_debug_frame is None else self.latest_debug_frame.copy()

        if debug_frame is None:
            return

        if not self.debug_window_created:
            cv2.namedWindow(config.DEBUG_WINDOW_NAME, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(config.DEBUG_WINDOW_NAME, debug_frame.shape[1], debug_frame.shape[0])
            self.debug_window_created = True

        cv2.imshow(config.DEBUG_WINDOW_NAME, debug_frame)
        cv2.waitKey(1)

    def close_debug_window(self):
        self._close_debug_window()

    def _build_debug_frame(self, frame, pose_results, face_results, p_score, p_status,
                          neck_angle, shoulder_slope, torso_lean,
                          face_shoulder_delta, turtle_neck_risk, slouch_delta, slouch_risk,
                          f_score, f_status, study_state, face_detected,
                          gaze_zone, head_yaw, head_pitch, head_pose,
                          eye_x, eye_y, eye_result, distance_result):
        video_frame = frame.copy()
        video_frame = self.pose_analyzer.draw_landmarks(video_frame, pose_results)
        video_frame = self.face_analyzer.draw_landmarks(video_frame, face_results)

        panel = self._build_debug_panel(
            video_frame.shape[0],
            p_score,
            p_status,
            neck_angle,
            shoulder_slope,
            torso_lean,
            face_shoulder_delta,
            turtle_neck_risk,
            slouch_delta,
            slouch_risk,
            f_score,
            f_status,
            study_state,
            face_detected,
            gaze_zone,
            head_yaw,
            head_pitch,
            head_pose,
            eye_x,
            eye_y,
            eye_result,
            distance_result,
        )
        debug_frame = np.hstack([video_frame, panel])
        return debug_frame

    def _build_debug_panel(self, panel_height, p_score, p_status, neck_angle,
                           shoulder_slope, torso_lean, face_shoulder_delta,
                           turtle_neck_risk, slouch_delta, slouch_risk, f_score, f_status,
                           study_state,
                           face_detected, gaze_zone, head_yaw, head_pitch,
                           head_pose, eye_x, eye_y, eye_result, distance_result):
        panel_width = config.DEBUG_PANEL_WIDTH
        panel = np.zeros((panel_height, panel_width, 3), dtype=np.uint8)
        panel[:] = (24, 24, 24)

        self._draw_panel_text(panel, "DeskPose Coach", 22, 34, 0.72, (245, 245, 245), 2)
        self._draw_panel_text(panel, time.strftime("%H:%M:%S"), 250, 34, 0.5, (160, 160, 160), 1)
        self._draw_status_pill(panel, study_state, 22, 52, self._state_color(study_state))

        y = 92
        y = self._draw_score_cards(panel, p_score, p_status, f_score, f_status, y)
        y += 12

        y = self._draw_section_title(panel, "Posture", y)
        y = self._draw_metric_row(panel, "Head offset", neck_angle, "%", y)
        y = self._draw_metric_row(panel, "Face ratio +", face_shoulder_delta, "", y)
        y = self._draw_metric_row(panel, "Turtle risk", turtle_neck_risk, "", y)
        y = self._draw_metric_row(panel, "Slouch +", slouch_delta, "", y)
        y = self._draw_metric_row(panel, "Slouch risk", slouch_risk, "", y)

        y += 8
        y = self._draw_section_title(panel, "Focus", y)
        y = self._draw_metric_row(panel, "Distance", distance_result["distance_state"], "", y)
        y = self._draw_metric_row(panel, "Gaze zone", gaze_zone, "", y)
        y = self._draw_metric_row(panel, "Head state", head_pose["head_state"], "", y)
        y = self._draw_metric_row(panel, "Eye x/y", f"{eye_x:.2f}, {eye_y:.2f}", "", y)
        y = self._draw_metric_row(panel, "Eye state", eye_result["eye_state"], "", y)
        y = self._draw_metric_row(panel, "Blink count", eye_result["blink_count"], "", y)

        footer_y = panel_height - 34
        if footer_y > y:
            self._draw_panel_text(panel, "Logs: outputs/posture_focus_log.csv", 22, footer_y, 0.42, (135, 135, 135), 1)
        return panel

    def _draw_score_cards(self, panel, posture_score, posture_status, focus_score, focus_status, y):
        self._draw_score_card(panel, "Posture", posture_score, posture_status, 22, y, config.GOOD_THRESHOLD)
        self._draw_score_card(panel, "Focus", focus_score, focus_status, 202, y, config.FOCUSED_THRESHOLD)
        return y + 86

    def _draw_score_card(self, panel, title, score, status, x, y, good_threshold):
        color = self._score_color(score, good_threshold)
        cv2.rectangle(panel, (x, y), (x + 156, y + 72), (38, 38, 38), -1)
        cv2.rectangle(panel, (x, y), (x + 156, y + 72), (62, 62, 62), 1)
        self._draw_panel_text(panel, title, x + 12, y + 22, 0.48, (170, 170, 170), 1)
        self._draw_panel_text(panel, f"{score:3d}", x + 12, y + 55, 0.95, color, 2)
        self._draw_panel_text(panel, status, x + 75, y + 53, 0.46, color, 1)

    def _draw_section_title(self, panel, title, y):
        cv2.line(panel, (22, y), (358, y), (58, 58, 58), 1)
        self._draw_panel_text(panel, title.upper(), 22, y + 20, 0.44, (155, 155, 155), 1)
        return y + 42

    def _draw_status_pill(self, panel, text, x, y, color):
        text_width = max(120, min(270, 12 * len(str(text))))
        cv2.rectangle(panel, (x, y), (x + text_width, y + 24), (42, 42, 42), -1)
        cv2.rectangle(panel, (x, y), (x + text_width, y + 24), color, 1)
        self._draw_panel_text(panel, str(text), x + 10, y + 17, 0.45, color, 1)

    def _draw_score_block(self, panel, title, score, status, y, good_threshold):
        color = self._score_color(score, good_threshold)
        self._draw_panel_text(panel, title, 22, y, 0.5, (170, 170, 170), 1)
        self._draw_panel_text(panel, f"{score:3d}", 22, y + 34, 1.0, color, 3)
        self._draw_panel_text(panel, status, 106, y + 31, 0.62, color, 2)
        self._draw_score_bar(panel, 22, y + 43, 275, 11, score, color)
        return y + 61

    def _draw_metric_row(self, panel, label, value, unit, y):
        if isinstance(value, (float, int)):
            if abs(value) < 1 and not unit:
                value_text = f"{value:.3f}"
            elif unit == "%":
                value_text = f"{value:.1f} {unit}".strip()
            elif unit == "deg":
                value_text = f"{value:.1f} {unit}".strip()
            else:
                value_text = f"{value:.2f} {unit}".strip()
        else:
            value_text = str(value)

        self._draw_panel_text(panel, label, 22, y, 0.43, (185, 185, 185), 1)
        self._draw_panel_text(panel, value_text, 178, y, 0.45, (245, 245, 245), 1)
        return y + 16

    def _draw_score_bar(self, panel, x, y, width, height, score, color):
        cv2.rectangle(panel, (x, y), (x + width, y + height), (80, 80, 80), 1)
        fill_width = int(width * max(0, min(score, 100)) / 100)
        if fill_width > 0:
            cv2.rectangle(panel, (x, y), (x + fill_width, y + height), color, -1)

    def _draw_panel_text(self, panel, text, x, y, scale, color, thickness):
        cv2.putText(panel, str(text), (x, y), cv2.FONT_HERSHEY_SIMPLEX, scale, color,
                    thickness, cv2.LINE_AA)

    def _score_color(self, score, good_threshold):
        if score >= good_threshold:
            return (80, 220, 120)
        if score >= min(config.WARNING_THRESHOLD, config.DISTRACTED_THRESHOLD):
            return (60, 210, 240)
        return (80, 90, 240)

    def _state_color(self, state):
        if state in ["Focused", "Reading"]:
            return (80, 220, 120)
        if state in ["Distracted", "Bad Posture"]:
            return (60, 210, 240)
        return (80, 90, 240)

    def _close_debug_window(self):
        if not self.debug_window_created:
            return

        try:
            if cv2.getWindowProperty(config.DEBUG_WINDOW_NAME, cv2.WND_PROP_VISIBLE) >= 1:
                cv2.destroyWindow(config.DEBUG_WINDOW_NAME)
        except cv2.error:
            pass
        finally:
            self.debug_window_created = False

    def _log_data(self, p_score, p_status, neck_ang, shoulder_slope, torso_lean,
                  face_shoulder_delta, turtle_neck_risk, slouch_delta, slouch_risk,
                  f_score, f_status, face_detected, gaze_zone,
                  head_yaw, head_pitch, head_pose, eye_x, eye_y, eye_result,
                  distance_result):
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(config.CSV_LOG_PATH, "a", newline="") as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow([
                    timestamp, p_score, p_status,
                    round(neck_ang, 2), round(shoulder_slope, 2), round(torso_lean, 2),
                    round(face_shoulder_delta, 3), turtle_neck_risk,
                    round(slouch_delta, 3), slouch_risk,
                    f_score, f_status, face_detected,
                    gaze_zone, round(head_yaw, 2), round(head_pitch, 2),
                    round(head_pose["head_roll"], 2), head_pose["head_state"],
                    round(eye_x, 3), round(eye_y, 3),
                    round(eye_result["eye_aspect_ratio"], 3),
                    eye_result["eye_state"],
                    eye_result["blink_count"],
                    round(eye_result["eye_closed_duration"], 2),
                    eye_result["drowsy"],
                    distance_result["distance_state"],
                    round(distance_result["face_width_ratio"], 3),
                    round(distance_result["face_area_ratio"], 3)
                ])
        except Exception as e:
            print(f"Error logging data: {e}")
