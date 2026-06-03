"""
Background thread for camera capture and running the analysis loop.
"""
import cv2
import csv
import numpy as np
import os
import subprocess
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
from src.study_session import StudySession


class CameraWorker:
    def __init__(self, ui_callback=None):
        self.is_running = False
        self.show_debug = False
        self.debug_window_created = False
        self.latest_debug_frame = None
        self.debug_frame_lock = threading.Lock()

        self.show_dashboard = False
        self.dashboard_process = None
        self.dashboard_queue = None
        self.dashboard_command_queue = None

        self.session_start_time = None
        self.focused_time = 0.0
        self.good_posture_time = 0.0
        self.bad_posture_time = 0.0
        self.away_time = 0.0
        self.no_face_time = 0.0
        self.drowsy_time = 0.0
        self.current_bad_posture_seconds = 0
        self.current_focus_drop_seconds = 0
        self.current_drowsy_seconds = 0
        self.last_bad_posture_sound_second = None
        self.last_focus_drop_sound_second = None
        self.last_drowsy_sound_second = None
        self.score_sum_p = 0.0
        self.score_sum_f = 0.0
        self.score_count = 0
        self.last_counted_second = None
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
        self.study_session = StudySession()

        os.makedirs(os.path.dirname(config.CSV_LOG_PATH), exist_ok=True)
        if not os.path.exists(config.CSV_LOG_PATH):
            with open(config.CSV_LOG_PATH, "w", newline="") as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow([
                    "timestamp", "posture_score", "posture_status",
                    "head_offset_ratio", "shoulder_slope", "torso_offset_ratio",
                    "face_shoulder_delta", "turtle_neck_risk", "shoulder_drop_delta", "slouch_risk",
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
            self.session_start_time = int(time.time())
            self.focused_time = 0
            self.good_posture_time = 0
            self.bad_posture_time = 0
            self.away_time = 0
            self.no_face_time = 0
            self.drowsy_time = 0
            self.current_bad_posture_seconds = 0
            self.current_focus_drop_seconds = 0
            self.current_drowsy_seconds = 0
            self.last_bad_posture_sound_second = None
            self.last_focus_drop_sound_second = None
            self.last_drowsy_sound_second = None
            self.score_sum_p = 0.0
            self.score_sum_f = 0.0
            self.score_count = 0
            self.last_counted_second = self.session_start_time
            self.study_event_segmenter = StudyEventSegmenter()
            self.study_session.start()
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

    def set_dashboard(self, state):
        import multiprocessing
        self.show_dashboard = state
        if state:
            print("Dashboard window requested.")
            if self.dashboard_process is None or not self.dashboard_process.is_alive():
                from src.dashboard_ui import run_dashboard
                self.dashboard_queue = multiprocessing.Queue()
                self.dashboard_command_queue = multiprocessing.Queue()
                self.dashboard_process = multiprocessing.Process(
                    target=run_dashboard,
                    args=(self.dashboard_queue, self.dashboard_command_queue),
                )
                self.dashboard_process.start()
        else:
            print("Dashboard window disabled.")
            if self.dashboard_process is not None and self.dashboard_process.is_alive():
                if self.dashboard_queue:
                    self.dashboard_queue.put("QUIT")
                self.dashboard_process.join(timeout=2)
            self.dashboard_process = None
            self.dashboard_queue = None
            self.dashboard_command_queue = None

    def reset_calibration(self):
        self.posture_calculator.reset_calibration()
        self.eye_analyzer.reset()
        print("Posture calibration reset.")

    def _run_loop(self):
        cap = self._open_camera()
        if cap is None:
            self.is_running = False
            self._send_dashboard_status("Camera unavailable")
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
            current_second = int(current_time)
            if self.last_counted_second is None:
                self.last_counted_second = current_second
            elapsed_seconds = max(0, current_second - self.last_counted_second)
            self.last_counted_second = current_second

            self.score_sum_p += p_score
            self.score_sum_f += f_score
            self.score_count += 1

            if elapsed_seconds > 0:
                if f_status == "Focused":
                    self.focused_time += elapsed_seconds
                if p_status == "Good":
                    self.good_posture_time += elapsed_seconds
                    self.current_bad_posture_seconds = 0
                elif p_status == "Bad":
                    self.bad_posture_time += elapsed_seconds
                    self.current_bad_posture_seconds += elapsed_seconds
                else:
                    self.current_bad_posture_seconds = 0
                if study_state == "Looking Away" or f_status == "Away":
                    self.away_time += elapsed_seconds
                if study_state == "No Face":
                    self.no_face_time += elapsed_seconds
                if study_state == "Drowsy":
                    self.drowsy_time += elapsed_seconds

                if f_status == "Focused":
                    self.current_focus_drop_seconds = 0
                else:
                    self.current_focus_drop_seconds += elapsed_seconds

                if drowsy or study_state == "Drowsy":
                    self.current_drowsy_seconds += elapsed_seconds
                else:
                    self.current_drowsy_seconds = 0

                self.study_session.update(
                    elapsed_seconds,
                    p_score,
                    p_status,
                    f_score,
                    f_status,
                    study_state,
                )

                self._maybe_play_study_alert_sound(current_second)

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

            self._handle_dashboard_commands()

            if self.show_dashboard and self.dashboard_queue is not None:
                session_snapshot = self.study_session.snapshot()
                session_time = session_snapshot["session_seconds"]
                m, s = divmod(int(session_time), 60)
                h, m = divmod(m, 60)
                time_str = f"{h:02d}:{m:02d}:{s:02d}"
                
                avg_p = int(self.score_sum_p / self.score_count) if self.score_count > 0 else 0
                avg_f = int(self.score_sum_f / self.score_count) if self.score_count > 0 else 0

                stats = {
                    "time_str": time_str,
                    "today_time": session_snapshot["today_seconds"],
                    "avg_p": avg_p,
                    "avg_f": avg_f,
                    "posture_score": int(p_score),
                    "posture_status": p_status,
                    "neck_angle": float(neck_angle),
                    "shoulder_drop": float(slouch_delta),
                    "slouch_risk": slouch_risk,
                    "focus_score": int(f_score),
                    "focus_status": f_status,
                    "gaze_zone": gaze_zone,
                    "feedback": self._posture_feedback(p_status, slouch_risk),
                    "focused_time": self.focused_time,
                    "max_focused_time": session_snapshot["max_focused_streak_seconds"],
                    "good_posture_time": self.good_posture_time,
                    "bad_posture_time": self.bad_posture_time,
                    "away_time": self.away_time,
                    "no_face_time": self.no_face_time,
                    "drowsy_time": self.drowsy_time,
                    "study_state": study_state,
                    "dominant_state": session_snapshot["dominant_state"],
                }

                try:
                    while not self.dashboard_queue.empty():
                        try:
                            self.dashboard_queue.get_nowait()
                        except:
                            break
                    self.dashboard_queue.put({"frame": frame, "stats": stats})
                except Exception as e:
                    print(f"Dashboard queue error: {e}")

            time.sleep(config.UPDATE_INTERVAL_SECONDS)

        cap.release()
        self.study_event_segmenter.close()
        self.study_session.finalize()
        self._send_dashboard_status("Stopped")
        cv2.destroyAllWindows()

    def _handle_dashboard_commands(self):
        if self.dashboard_command_queue is None:
            return

        while not self.dashboard_command_queue.empty():
            command = self.dashboard_command_queue.get_nowait()
            if command == "START_ANALYSIS":
                if self.is_running:
                    self.reset_calibration()
                else:
                    self.start()
            elif command == "SAVE_REPORT":
                self._save_session_report()
            elif command == "STOP_CAMERA":
                self.is_running = False
            elif command == "DASHBOARD_CLOSED":
                self.show_dashboard = False
                self.dashboard_process = None
                self.dashboard_queue = None
                self.dashboard_command_queue = None
                break

    def handle_dashboard_commands(self):
        self._handle_dashboard_commands()

    def _posture_feedback(self, posture_status, slouch_risk="Low"):
        if str(posture_status).startswith("Calibrating"):
            return "정자세를 유지하며 기준 자세를 측정하고 있습니다."
        if slouch_risk == "High":
            return "어깨선이 기준보다 많이 낮아졌습니다. 허리를 세우고 가슴을 살짝 펴주세요."
        if slouch_risk == "Medium":
            return "어깨가 조금 내려갔습니다. 허리를 곧게 세워주세요."
        if posture_status == "Good":
            return "현재 자세가 안정적입니다. 이 자세를 유지하세요."
        if posture_status == "Warning":
            return "목이 약간 앞으로 나와 있습니다. 턱을 살짝 당겨주세요."
        if posture_status == "No Pose":
            return "상체가 카메라에 보이도록 앉아주세요."
        return "거북목 위험도가 높습니다. 귀와 어깨가 일직선이 되도록 자세를 조정하세요."

    def _save_session_report(self):
        try:
            os.makedirs("outputs", exist_ok=True)
            report_path = os.path.join("outputs", "session_report.txt")
            session_time = self.study_session.snapshot()["session_seconds"]
            avg_p = int(self.score_sum_p / self.score_count) if self.score_count > 0 else 0
            avg_f = int(self.score_sum_f / self.score_count) if self.score_count > 0 else 0
            session_snapshot = self.study_session.snapshot()
            with open(report_path, "w", encoding="utf-8") as report_file:
                report_file.write("NeckCare Vision Session Report\n")
                report_file.write(f"Saved at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                report_file.write(f"Session seconds: {int(session_time)}\n")
                report_file.write(f"Today total seconds: {int(session_snapshot['today_seconds'])}\n")
                report_file.write(f"Average posture score: {avg_p}\n")
                report_file.write(f"Average focus score: {avg_f}\n")
                report_file.write(f"Focused seconds: {int(self.focused_time)}\n")
                report_file.write(f"Max focused streak seconds: {int(session_snapshot['max_focused_streak_seconds'])}\n")
                report_file.write(f"Good posture seconds: {int(self.good_posture_time)}\n")
                report_file.write(f"Bad posture seconds: {int(self.bad_posture_time)}\n")
                report_file.write(f"Away seconds: {int(self.away_time)}\n")
                report_file.write(f"No face seconds: {int(self.no_face_time)}\n")
                report_file.write(f"Drowsy signal seconds: {int(self.drowsy_time)}\n")
                report_file.write(f"Dominant study state: {session_snapshot['dominant_state']}\n")
            print(f"Session report saved: {report_path}")
        except Exception as exc:
            print(f"Error saving session report: {exc}")

    def _send_dashboard_status(self, camera_state):
        if self.show_dashboard and self.dashboard_queue is not None:
            try:
                self.dashboard_queue.put({"camera_state": camera_state})
            except Exception as exc:
                print(f"Dashboard status update error: {exc}")

    def _maybe_play_study_alert_sound(self, current_second):
        if self.current_drowsy_seconds >= config.DROWSY_SOUND_AFTER_SECONDS:
            self._maybe_play_drowsy_sound(current_second)
            return

        if self.current_bad_posture_seconds >= config.BAD_POSTURE_SOUND_AFTER_SECONDS:
            self._maybe_play_bad_posture_sound(current_second)
            return

        self._maybe_play_focus_drop_sound(current_second)

    def _maybe_play_bad_posture_sound(self, current_second):
        if not getattr(config, "ENABLE_BAD_POSTURE_SOUND", True):
            return False
        if self.current_bad_posture_seconds < config.BAD_POSTURE_SOUND_AFTER_SECONDS:
            return False
        if self.last_bad_posture_sound_second is not None:
            elapsed_since_sound = current_second - self.last_bad_posture_sound_second
            if elapsed_since_sound < config.BAD_POSTURE_SOUND_COOLDOWN_SECONDS:
                return False

        self.last_bad_posture_sound_second = current_second
        self._play_alert_sound(config.BAD_POSTURE_SOUND_PATH)
        return True

    def _maybe_play_focus_drop_sound(self, current_second):
        if not getattr(config, "ENABLE_FOCUS_DROP_SOUND", True):
            return False
        if self.current_focus_drop_seconds < config.FOCUS_DROP_SOUND_AFTER_SECONDS:
            return False
        if self.last_focus_drop_sound_second is not None:
            elapsed_since_sound = current_second - self.last_focus_drop_sound_second
            if elapsed_since_sound < config.FOCUS_DROP_SOUND_COOLDOWN_SECONDS:
                return False

        self.last_focus_drop_sound_second = current_second
        self._play_alert_sound(config.FOCUS_DROP_SOUND_PATH)
        return True

    def _maybe_play_drowsy_sound(self, current_second):
        if not getattr(config, "ENABLE_DROWSY_SOUND", True):
            return False
        if self.current_drowsy_seconds < config.DROWSY_SOUND_AFTER_SECONDS:
            return False
        if self.last_drowsy_sound_second is not None:
            elapsed_since_sound = current_second - self.last_drowsy_sound_second
            if elapsed_since_sound < config.DROWSY_SOUND_COOLDOWN_SECONDS:
                return False

        self.last_drowsy_sound_second = current_second
        self._play_alert_sound(
            config.DROWSY_SOUND_PATH,
            repeat_count=config.DROWSY_SOUND_REPEAT_COUNT,
            repeat_gap_seconds=config.DROWSY_SOUND_REPEAT_GAP_SECONDS,
        )
        return True

    def _play_alert_sound(self, sound_path, repeat_count=1, repeat_gap_seconds=0.0):
        if not sound_path or not os.path.exists(sound_path):
            print(f"Alert sound not found: {sound_path}")
            return

        sound_thread = threading.Thread(
            target=self._play_alert_sound_sequence,
            args=(sound_path, max(1, int(repeat_count)), max(0.0, float(repeat_gap_seconds))),
            daemon=True,
        )
        sound_thread.start()

    def _play_alert_sound_sequence(self, sound_path, repeat_count, repeat_gap_seconds):
        try:
            for index in range(repeat_count):
                subprocess.run(
                    ["afplay", sound_path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
                if index < repeat_count - 1 and repeat_gap_seconds > 0:
                    time.sleep(repeat_gap_seconds)
        except Exception as exc:
            print(f"Could not play alert sound: {exc}")

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
        panel[:] = (18, 18, 18)

        # Header
        self._draw_panel_text(panel, "DESKPOSE COACH", 24, 38, 0.65, (230, 230, 230), 2)
        self._draw_panel_text(panel, time.strftime("%H:%M:%S"), 280, 38, 0.5, (120, 120, 120), 1)
        self._draw_status_pill(panel, study_state, 24, 58, self._state_color(study_state))

        y = 100
        y = self._draw_score_cards(panel, p_score, p_status, f_score, f_status, y)
        y += 16

        y = self._draw_section_title(panel, "Posture Metrics", y)
        y = self._draw_metric_row(panel, "Head offset", neck_angle, "%", y)
        y = self._draw_metric_row(panel, "Face ratio +", face_shoulder_delta, "", y)
        y = self._draw_metric_row(panel, "Turtle risk", turtle_neck_risk, "", y)
        y = self._draw_metric_row(panel, "Shoulder drop", slouch_delta, "", y)
        y = self._draw_metric_row(panel, "Slouch risk", slouch_risk, "", y)

        y += 12
        y = self._draw_section_title(panel, "Focus Metrics", y)
        y = self._draw_metric_row(panel, "Distance", distance_result["distance_state"], "", y)
        y = self._draw_metric_row(panel, "Gaze zone", gaze_zone, "", y)
        y = self._draw_metric_row(panel, "Head state", head_pose["head_state"], "", y)
        y = self._draw_metric_row(panel, "Eye x/y", f"{eye_x:.2f}, {eye_y:.2f}", "", y)
        y = self._draw_metric_row(panel, "Eye state", eye_result["eye_state"], "", y)
        y = self._draw_metric_row(panel, "Blink count", eye_result["blink_count"], "", y)

        footer_y = panel_height - 24
        if footer_y > y:
            self._draw_panel_text(panel, "Logging to: outputs/posture_focus_log.csv", 24, footer_y, 0.4, (100, 100, 100), 1)
        return panel

    def _draw_score_cards(self, panel, posture_score, posture_status, focus_score, focus_status, y):
        self._draw_score_card(panel, "POSTURE", posture_score, posture_status, 24, y, config.GOOD_THRESHOLD)
        self._draw_score_card(panel, "FOCUS", focus_score, focus_status, 200, y, config.FOCUSED_THRESHOLD)
        return y + 80

    def _draw_score_card(self, panel, title, score, status, x, y, good_threshold):
        color = self._score_color(score, good_threshold)
        cv2.rectangle(panel, (x, y), (x + 156, y + 70), (28, 28, 28), -1)
        cv2.rectangle(panel, (x, y), (x + 156, y + 70), (50, 50, 50), 1)
        cv2.line(panel, (x, y), (x, y + 70), color, 3)

        self._draw_panel_text(panel, title, x + 14, y + 20, 0.4, (160, 160, 160), 1)
        self._draw_panel_text(panel, f"{score:3d}", x + 14, y + 55, 0.9, (245, 245, 245), 2)
        self._draw_panel_text(panel, status, x + 76, y + 53, 0.45, color, 1)

    def _draw_section_title(self, panel, title, y):
        self._draw_panel_text(panel, title.upper(), 24, y + 15, 0.4, (130, 130, 130), 1)
        cv2.line(panel, (24, y + 24), (356, y + 24), (45, 45, 45), 1)
        return y + 44

    def _draw_status_pill(self, panel, text, x, y, color):
        text_str = str(text)
        (text_w, text_h), _ = cv2.getTextSize(text_str, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
        pill_width = text_w + 20
        cv2.rectangle(panel, (x, y), (x + pill_width, y + 22), (35, 35, 35), -1)
        cv2.rectangle(panel, (x, y), (x + pill_width, y + 22), color, 1)
        self._draw_panel_text(panel, text_str, x + 10, y + 16, 0.45, color, 1)

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

        self._draw_panel_text(panel, label, 24, y, 0.42, (170, 170, 170), 1)
        self._draw_panel_text(panel, value_text, 180, y, 0.45, (235, 235, 235), 1)

        if isinstance(value, float) and 0.0 <= value <= 1.0 and not unit:
            bar_w = 60
            bar_x = 296
            cv2.line(panel, (bar_x, y - 4), (bar_x + bar_w, y - 4), (50, 50, 50), 2)
            fill_w = int(bar_w * value)
            if fill_w > 0:
                cv2.line(panel, (bar_x, y - 4), (bar_x + fill_w, y - 4), (180, 180, 180), 2)

        return y + 20

    def _draw_score_bar(self, panel, x, y, width, height, score, color):
        cv2.rectangle(panel, (x, y), (x + width, y + height), (50, 50, 50), 1)
        fill_width = int(width * max(0, min(score, 100)) / 100)
        if fill_width > 0:
            cv2.rectangle(panel, (x, y), (x + fill_width, y + height), color, -1)

    def _draw_panel_text(self, panel, text, x, y, scale, color, thickness):
        cv2.putText(panel, str(text), (x, y), cv2.FONT_HERSHEY_SIMPLEX, scale, color,
                    thickness, cv2.LINE_AA)

    def _score_color(self, score, good_threshold):
        if score >= good_threshold:
            return (128, 222, 74)
        if score >= min(config.WARNING_THRESHOLD, config.DISTRACTED_THRESHOLD):
            return (21, 204, 250)
        return (113, 113, 248)

    def _state_color(self, state):
        if state in ["Focused", "Reading"]:
            return (128, 222, 74)
        if state in ["Distracted", "Bad Posture"]:
            return (21, 204, 250)
        return (113, 113, 248)

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
