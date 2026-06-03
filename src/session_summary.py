"""
Build a lightweight text summary from DeskPose CSV logs.
"""
import os

import pandas as pd

import src.config as config


class SessionSummary:
    def build_summary(self):
        if not os.path.exists(config.CSV_LOG_PATH):
            return "No posture/focus log found yet."

        frame_log = pd.read_csv(config.CSV_LOG_PATH, engine="python", on_bad_lines="skip")
        if frame_log.empty:
            return "Posture/focus log is empty."

        event_log = self._read_event_log()
        daily_log = self._read_daily_log()
        avg_posture = frame_log["posture_score"].mean()
        avg_focus = frame_log["focus_score"].mean()

        posture_bad_ratio = self._ratio(frame_log, "posture_status", "Bad")
        focus_focused_ratio = self._ratio(frame_log, "focus_status", "Focused")
        reading_ratio = self._ratio(frame_log, "gaze_zone", "Reading")
        away_ratio = self._ratio(frame_log, "gaze_zone", "Away")

        lines = [
            "DeskPose Session Summary",
            "",
            f"Average posture score: {avg_posture:.1f}",
            f"Average focus score: {avg_focus:.1f}",
            f"Bad posture frames: {posture_bad_ratio:.1f}%",
            f"Focused frames: {focus_focused_ratio:.1f}%",
            f"Reading frames: {reading_ratio:.1f}%",
            f"Away gaze frames: {away_ratio:.1f}%",
        ]

        if daily_log is not None and not daily_log.empty:
            today = pd.Timestamp.today().strftime("%Y-%m-%d")
            today_log = daily_log[daily_log["date"].eq(today)]
            if not today_log.empty:
                today_seconds = today_log["duration_seconds"].sum()
                focused_seconds = today_log["focused_seconds"].sum()
                bad_posture_seconds = today_log["bad_posture_seconds"].sum()
                lines.extend([
                    "",
                    "Today's study record:",
                    f"- Total study time: {self._format_seconds(today_seconds)}",
                    f"- Focused time: {self._format_seconds(focused_seconds)}",
                    f"- Bad posture time: {self._format_seconds(bad_posture_seconds)}",
                ])

        if event_log is not None and not event_log.empty:
            lines.extend(["", "Top study events:"])
            event_durations = event_log.groupby("event_type")["duration"].sum().sort_values(ascending=False)
            for event_type, duration in event_durations.head(5).items():
                lines.append(f"- {event_type}: {duration:.1f}s")

        return "\n".join(lines)

    def _read_event_log(self):
        if not os.path.exists(config.STUDY_EVENTS_CSV_PATH):
            return None
        return pd.read_csv(config.STUDY_EVENTS_CSV_PATH, engine="python", on_bad_lines="skip")

    def _read_daily_log(self):
        if not os.path.exists(config.DAILY_SESSIONS_CSV_PATH):
            return None
        return pd.read_csv(config.DAILY_SESSIONS_CSV_PATH, engine="python", on_bad_lines="skip")

    def _ratio(self, frame_log, column, target):
        if column not in frame_log:
            return 0
        return (frame_log[column].eq(target).mean()) * 100

    def _format_seconds(self, seconds):
        hours, remainder = divmod(int(seconds), 3600)
        minutes, secs = divmod(remainder, 60)
        if hours > 0:
            return f"{hours}h {minutes}m {secs}s"
        return f"{minutes}m {secs}s"
