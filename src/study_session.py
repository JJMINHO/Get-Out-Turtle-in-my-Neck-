"""
Track one study session and append daily study summaries to CSV.
"""
import csv
import os
from datetime import datetime

import pandas as pd

import src.config as config


class StudySession:
    def __init__(self):
        self.started_at = None
        self.ended_at = None
        self.duration_seconds = 0
        self.focused_seconds = 0
        self.good_posture_seconds = 0
        self.bad_posture_seconds = 0
        self.away_seconds = 0
        self.no_face_seconds = 0
        self.drowsy_seconds = 0
        self.posture_score_sum = 0.0
        self.focus_score_sum = 0.0
        self.score_count = 0
        self.state_durations = {}
        self.finalized = False

        self._ensure_csv()

    def start(self):
        self.started_at = datetime.now()
        self.ended_at = None
        self.duration_seconds = 0
        self.focused_seconds = 0
        self.good_posture_seconds = 0
        self.bad_posture_seconds = 0
        self.away_seconds = 0
        self.no_face_seconds = 0
        self.drowsy_seconds = 0
        self.posture_score_sum = 0.0
        self.focus_score_sum = 0.0
        self.score_count = 0
        self.state_durations = {}
        self.finalized = False

    def update(self, delta_seconds, posture_score, posture_status, focus_score, focus_status, study_state):
        if self.started_at is None or self.finalized:
            return

        safe_delta = max(0, int(delta_seconds))
        if safe_delta == 0:
            return

        self.duration_seconds += safe_delta
        self.posture_score_sum += posture_score
        self.focus_score_sum += focus_score
        self.score_count += 1
        self.state_durations[study_state] = self.state_durations.get(study_state, 0.0) + safe_delta

        if focus_status == "Focused":
            self.focused_seconds += safe_delta
        if posture_status == "Good":
            self.good_posture_seconds += safe_delta
        elif posture_status == "Bad":
            self.bad_posture_seconds += safe_delta

        if study_state == "Looking Away" or focus_status == "Away":
            self.away_seconds += safe_delta
        if study_state == "No Face":
            self.no_face_seconds += safe_delta
        if study_state == "Drowsy":
            self.drowsy_seconds += safe_delta

    def snapshot(self):
        avg_posture = self.average_posture_score()
        avg_focus = self.average_focus_score()
        return {
            "session_seconds": self.duration_seconds,
            "today_seconds": self.today_total_seconds(include_current=True),
            "avg_posture": avg_posture,
            "avg_focus": avg_focus,
            "focused_seconds": self.focused_seconds,
            "good_posture_seconds": self.good_posture_seconds,
            "bad_posture_seconds": self.bad_posture_seconds,
            "away_seconds": self.away_seconds,
            "no_face_seconds": self.no_face_seconds,
            "drowsy_seconds": self.drowsy_seconds,
            "dominant_state": self.dominant_state(),
        }

    def finalize(self):
        if self.started_at is None or self.finalized:
            return None

        self.ended_at = datetime.now()
        self.finalized = True
        summary = self.snapshot()
        self._write_summary(summary)
        return summary

    def average_posture_score(self):
        if self.score_count == 0:
            return 0
        return self.posture_score_sum / self.score_count

    def average_focus_score(self):
        if self.score_count == 0:
            return 0
        return self.focus_score_sum / self.score_count

    def dominant_state(self):
        if not self.state_durations:
            return "Idle"
        return max(self.state_durations.items(), key=lambda item: item[1])[0]

    def today_total_seconds(self, include_current=False):
        total = 0
        today = datetime.now().strftime("%Y-%m-%d")
        if os.path.exists(config.DAILY_SESSIONS_CSV_PATH):
            try:
                sessions = pd.read_csv(config.DAILY_SESSIONS_CSV_PATH, engine="python", on_bad_lines="skip")
                if not sessions.empty and "date" in sessions and "duration_seconds" in sessions:
                    total = sessions.loc[sessions["date"].eq(today), "duration_seconds"].sum()
            except Exception:
                total = 0

        if include_current and not self.finalized:
            total += self.duration_seconds
        return int(total)

    def _ensure_csv(self):
        os.makedirs(os.path.dirname(config.DAILY_SESSIONS_CSV_PATH), exist_ok=True)
        if os.path.exists(config.DAILY_SESSIONS_CSV_PATH):
            return

        with open(config.DAILY_SESSIONS_CSV_PATH, "w", newline="") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow([
                "date",
                "start_time",
                "end_time",
                "duration_seconds",
                "focused_seconds",
                "good_posture_seconds",
                "bad_posture_seconds",
                "away_seconds",
                "no_face_seconds",
                "drowsy_seconds",
                "avg_posture_score",
                "avg_focus_score",
                "dominant_state",
            ])

    def _write_summary(self, summary):
        if self.duration_seconds <= 0:
            return

        with open(config.DAILY_SESSIONS_CSV_PATH, "a", newline="") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow([
                self.started_at.strftime("%Y-%m-%d"),
                self.started_at.strftime("%Y-%m-%d %H:%M:%S"),
                self.ended_at.strftime("%Y-%m-%d %H:%M:%S"),
                int(self.duration_seconds),
                int(summary["focused_seconds"]),
                int(summary["good_posture_seconds"]),
                int(summary["bad_posture_seconds"]),
                int(summary["away_seconds"]),
                int(summary["no_face_seconds"]),
                int(summary["drowsy_seconds"]),
                round(summary["avg_posture"], 1),
                round(summary["avg_focus"], 1),
                summary["dominant_state"],
            ])
