import os

def load_dotenv():
    dotenv_path = ".env"
    if os.path.exists(dotenv_path):
        try:
            with open(dotenv_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        key, val = line.split("=", 1)
                        key = key.strip()
                        val = val.strip().strip('"').strip("'")
                        os.environ[key] = val
        except Exception as e:
            print(f"Error loading .env: {e}")

load_dotenv()

# Configuration values used across the DeskPose Coach application.


CAMERA_INDEX = 0
# Try these indices if CAMERA_INDEX fails.
CAMERA_INDEX_FALLBACKS = [0, 1, 2]

# On macOS, AVFoundation is usually the most reliable OpenCV backend.
# If None, OpenCV will choose a default backend.
CAMERA_BACKEND = "avfoundation"  # "avfoundation" or None

FRAME_WIDTH = 640
FRAME_HEIGHT = 480
UPDATE_INTERVAL_SECONDS = 0.1

MIN_DETECTION_CONFIDENCE = 0.5
MIN_TRACKING_CONFIDENCE = 0.5

GOOD_THRESHOLD = 80
WARNING_THRESHOLD = 60
FOCUSED_THRESHOLD = 75
DISTRACTED_THRESHOLD = 45

CALIBRATION_SECONDS = 3
POSTURE_SMOOTHING_ALPHA = 0.18
POSTURE_NOISE_FLOOR = 0.012
FACE_SHOULDER_RATIO_WARNING = 0.025
FACE_SHOULDER_RATIO_BAD = 0.075
SHOULDER_DROP_WARNING = 0.035
SHOULDER_DROP_BAD = 0.075
SLOUCH_DROP_WARNING = 0.045
SLOUCH_DROP_BAD = 0.090
TORSO_HEIGHT_DROP_WARNING = 0.060
TORSO_HEIGHT_DROP_BAD = 0.120
HEAD_OFFSET_RATIO_THRESHOLD = 0.35
TORSO_OFFSET_RATIO_THRESHOLD = 0.25
SHOULDER_SLOPE_THRESHOLD = 8
DROWSY_EAR_THRESHOLD = 0.20
BLINK_MAX_SECONDS = 0.35
LONG_EYE_CLOSURE_SECONDS = 0.8

GAZE_LEFT_THRESHOLD = 0.35
GAZE_RIGHT_THRESHOLD = 0.65
GAZE_UP_THRESHOLD = 0.33
GAZE_DOWN_THRESHOLD = 0.62
READING_HEAD_PITCH_THRESHOLD = 8
READING_FOCUS_SCORE = 92
FACE_TOO_CLOSE_WIDTH_RATIO = 0.42
FACE_TOO_FAR_WIDTH_RATIO = 0.16
HEAD_YAW_THRESHOLD = 24
HEAD_PITCH_DOWN_THRESHOLD = 26
HEAD_PITCH_UP_THRESHOLD = 24
HEAD_ROLL_TILT_THRESHOLD = 15

CSV_LOG_PATH = "outputs/posture_focus_log.csv"
STUDY_EVENTS_CSV_PATH = "outputs/study_events.csv"
DAILY_SESSIONS_CSV_PATH = "outputs/daily_sessions.csv"
CALENDAR_EVENTS_CSV_PATH = "outputs/calendar_events.csv"
STUDY_EVENT_MIN_DURATION_SECONDS = 2.0
# A study day runs from 05:00 through 04:59 the next calendar day.
STUDY_DAY_START_HOUR = 5

OPENAI_MODEL = "gpt-5.4-mini"
GEMINI_MODEL = "gemini-2.0-flash"
AI_FEEDBACK_COOLDOWN_SECONDS = 180
AI_FEEDBACK_TRIGGER_COOLDOWN_SECONDS = 60
AI_FEEDBACK_TIMEOUT_SECONDS = 8
DAILY_TARGET_STUDY_SECONDS = 4 * 60 * 60
TARGET_STUDY_TIME_HOURS = 4.0


ENABLE_BAD_POSTURE_SOUND = True
BAD_POSTURE_SOUND_AFTER_SECONDS = 5
BAD_POSTURE_SOUND_COOLDOWN_SECONDS = 60
BAD_POSTURE_SOUND_PATH = "/System/Library/Sounds/Ping.aiff"

ENABLE_FOCUS_DROP_SOUND = True
FOCUS_DROP_SOUND_AFTER_SECONDS = 10
FOCUS_DROP_SOUND_COOLDOWN_SECONDS = 90
FOCUS_DROP_SOUND_PATH = "/System/Library/Sounds/Glass.aiff"

ENABLE_DROWSY_SOUND = True
DROWSY_SOUND_AFTER_SECONDS = 2
DROWSY_SOUND_COOLDOWN_SECONDS = 120
DROWSY_SOUND_PATH = "/System/Library/Sounds/Sosumi.aiff"
DROWSY_SOUND_REPEAT_COUNT = 3
DROWSY_SOUND_REPEAT_GAP_SECONDS = 0.35

DEBUG_WINDOW_NAME = "DeskPose Coach Debug"
DEBUG_PANEL_WIDTH = 380

DASHBOARD_WINDOW_NAME = "DeskPose Dashboard"
DASHBOARD_PANEL_WIDTH = 350

# MediaPipe Tasks model assets (download these into assets/).
POSE_MODEL_PATH = os.path.join("assets", "pose_landmarker_lite.task")
FACE_MODEL_PATH = os.path.join("assets", "face_landmarker.task")
