"""
Calculate daily study performance scores from session and vision logs.
"""
import csv
import os
from datetime import datetime

import src.config as config
from src.study_session import study_day_string


DEFAULT_TARGET_STUDY_SECONDS = 4 * 60 * 60


class DailyScoreCalculator:
    def __init__(self, target_study_seconds=None):
        self.target_study_seconds = int(
            target_study_seconds
            or getattr(config, "DAILY_TARGET_STUDY_SECONDS", DEFAULT_TARGET_STUDY_SECONDS)
        )

    def calculate(self, day=None, current_stats=None):
        study_day = day or study_day_string()
        summary = self._read_daily_session_summary(study_day)
        events = self._read_events(study_day)
        quadrants = self._read_quadrants(study_day)
        event_durations = self._event_durations(events)

        if current_stats:
            self._merge_current_stats(summary, current_stats)

        study_seconds = summary["study_seconds"]
        focused_seconds = summary["focused_seconds"]
        good_posture_seconds = summary["good_posture_seconds"]
        away_seconds = summary["away_seconds"]
        no_face_seconds = summary["no_face_seconds"]
        drowsy_seconds = summary["drowsy_seconds"]

        focus_density = self._ratio(focused_seconds, study_seconds)
        time_ratio = min(self._ratio(study_seconds, self.target_study_seconds), 1.0)
        good_posture_ratio = self._ratio(good_posture_seconds, study_seconds)
        stable_presence_ratio = max(
            0.0,
            1.0 - self._ratio(away_seconds + no_face_seconds + drowsy_seconds, study_seconds),
        )

        focus_part = focus_density * 40
        time_part = time_ratio * 30
        quality_ratio = (
            0.45 * focus_density
            + 0.35 * good_posture_ratio
            + 0.20 * stable_presence_ratio
        )
        quality_part = quality_ratio * 30
        daily_score = min(100.0, focus_part + time_part + quality_part)

        return {
            "date": study_day,
            "daily_score": round(daily_score, 1),
            "focus_part": round(focus_part, 1),
            "time_part": round(time_part, 1),
            "quality_part": round(quality_part, 1),
            "focus_density": round(focus_density, 3),
            "time_ratio": round(time_ratio, 3),
            "vision_quality_ratio": round(quality_ratio, 3),
            "good_posture_ratio": round(good_posture_ratio, 3),
            "stable_presence_ratio": round(stable_presence_ratio, 3),
            "study_seconds": int(study_seconds),
            "focused_seconds": int(focused_seconds),
            "target_study_seconds": self.target_study_seconds,
            "away_seconds": int(away_seconds),
            "no_face_seconds": int(no_face_seconds),
            "drowsy_seconds": int(drowsy_seconds),
            "events": events,
            "event_durations": event_durations,
            "quadrants": quadrants,
        }

    def _event_durations(self, events):
        durations = {}
        for event in events:
            event_type = event.get("event_type", "Unknown")
            durations[event_type] = durations.get(event_type, 0.0) + self._safe_float(event.get("duration"))
        return durations

    def _read_daily_session_summary(self, study_day):
        summary = {
            "study_seconds": 0,
            "focused_seconds": 0,
            "good_posture_seconds": 0,
            "bad_posture_seconds": 0,
            "away_seconds": 0,
            "no_face_seconds": 0,
            "drowsy_seconds": 0,
        }

        if not os.path.exists(config.DAILY_SESSIONS_CSV_PATH):
            return summary

        with open(config.DAILY_SESSIONS_CSV_PATH, "r", newline="") as csv_file:
            reader = csv.DictReader(csv_file)
            for row in reader:
                if row.get("date") != study_day:
                    continue
                summary["study_seconds"] += self._safe_int(row.get("duration_seconds"))
                summary["focused_seconds"] += self._safe_int(row.get("focused_seconds"))
                summary["good_posture_seconds"] += self._safe_int(row.get("good_posture_seconds"))
                summary["bad_posture_seconds"] += self._safe_int(row.get("bad_posture_seconds"))
                summary["away_seconds"] += self._safe_int(row.get("away_seconds"))
                summary["no_face_seconds"] += self._safe_int(row.get("no_face_seconds"))
                summary["drowsy_seconds"] += self._safe_int(row.get("drowsy_seconds"))
        return summary

    def _read_events(self, study_day):
        if not os.path.exists(config.STUDY_EVENTS_CSV_PATH):
            return []

        events = []
        with open(config.STUDY_EVENTS_CSV_PATH, "r", newline="") as csv_file:
            reader = csv.DictReader(csv_file)
            for row in reader:
                start_time = self._parse_datetime(row.get("start_time"))
                if start_time is None or study_day_string(start_time) != study_day:
                    continue
                events.append({
                    "start_time": row.get("start_time", ""),
                    "end_time": row.get("end_time", ""),
                    "event_type": row.get("event_type", "Unknown"),
                    "duration": self._safe_float(row.get("duration")),
                    "avg_posture_score": self._safe_float(row.get("avg_posture_score")),
                    "avg_focus_score": self._safe_float(row.get("avg_focus_score")),
                })
        return events[-24:]

    def _read_quadrants(self, study_day):
        quadrants = {
            "strong": 0,
            "posture_risk": 0,
            "focus_risk": 0,
            "low_quality": 0,
        }
        if not os.path.exists(config.CSV_LOG_PATH):
            return quadrants

        with open(config.CSV_LOG_PATH, "r", newline="") as csv_file:
            reader = csv.DictReader(csv_file)
            for row in reader:
                timestamp = self._parse_datetime(row.get("timestamp"))
                if timestamp is None or study_day_string(timestamp) != study_day:
                    continue

                posture_score = self._safe_float(row.get("posture_score"))
                focus_score = self._safe_float(row.get("focus_score"))
                if posture_score >= 80 and focus_score >= 75:
                    quadrants["strong"] += 1
                elif posture_score < 80 and focus_score >= 75:
                    quadrants["posture_risk"] += 1
                elif posture_score >= 80 and focus_score < 75:
                    quadrants["focus_risk"] += 1
                else:
                    quadrants["low_quality"] += 1
        return quadrants

    def _merge_current_stats(self, summary, stats):
        summary["study_seconds"] += self._safe_int(stats.get("session_seconds"))
        summary["focused_seconds"] += self._safe_int(stats.get("focused_time"))
        summary["good_posture_seconds"] += self._safe_int(stats.get("good_posture_time"))
        summary["bad_posture_seconds"] += self._safe_int(stats.get("bad_posture_time"))
        summary["away_seconds"] += self._safe_int(stats.get("away_time"))
        summary["no_face_seconds"] += self._safe_int(stats.get("no_face_time"))
        summary["drowsy_seconds"] += self._safe_int(stats.get("drowsy_time"))

    def _parse_datetime(self, value):
        if not value:
            return None
        try:
            return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None

    def _ratio(self, numerator, denominator):
        if denominator <= 0:
            return 0.0
        return max(0.0, min(float(numerator) / float(denominator), 1.0))

    def _safe_int(self, value):
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return 0

    def _safe_float(self, value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0
