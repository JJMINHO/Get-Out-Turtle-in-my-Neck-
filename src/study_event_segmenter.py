"""
Convert frame-level posture/focus states into time-based study events.
"""
import csv
import os
from datetime import datetime

import src.config as config


class StudyEventSegmenter:
    def __init__(self):
        self.current_state = None
        self.current_started_at = None
        self.current_scores = []
        self.last_committed_state = None

        os.makedirs(os.path.dirname(config.STUDY_EVENTS_CSV_PATH), exist_ok=True)
        if not os.path.exists(config.STUDY_EVENTS_CSV_PATH):
            with open(config.STUDY_EVENTS_CSV_PATH, "w", newline="") as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow([
                    "start_time",
                    "end_time",
                    "event_type",
                    "duration",
                    "avg_posture_score",
                    "avg_focus_score",
                ])

    def update(self, posture_score, posture_status, focus_score, focus_status,
               face_detected, gaze_zone, drowsy):
        now = datetime.now()
        state = self._classify_state(posture_status, focus_status, face_detected, gaze_zone, drowsy)

        if self.current_state is None:
            self._start_event(state, now, posture_score, focus_score)
            return state

        if state == self.current_state:
            self.current_scores.append((posture_score, focus_score))
            return state

        self._finish_event(now)
        self._start_event(state, now, posture_score, focus_score)
        return state

    def close(self):
        if self.current_state is not None:
            self._finish_event(datetime.now(), force=True)

    def _classify_state(self, posture_status, focus_status, face_detected, gaze_zone, drowsy):
        if not face_detected or gaze_zone == "No Face":
            return "No Face"
        if drowsy:
            return "Drowsy"
        if posture_status == "Bad":
            return "Bad Posture"
        if gaze_zone == "Away" or focus_status == "Away":
            return "Looking Away"
        if gaze_zone == "Reading":
            return "Reading"
        if focus_status == "Focused":
            return "Focused"
        return "Distracted"

    def _start_event(self, state, started_at, posture_score, focus_score):
        self.current_state = state
        self.current_started_at = started_at
        self.current_scores = [(posture_score, focus_score)]

    def _finish_event(self, ended_at, force=False):
        duration = (ended_at - self.current_started_at).total_seconds()
        if duration >= config.STUDY_EVENT_MIN_DURATION_SECONDS or force:
            self._write_event(ended_at, duration)
            self.last_committed_state = self.current_state

    def _write_event(self, ended_at, duration):
        posture_scores = [score[0] for score in self.current_scores]
        focus_scores = [score[1] for score in self.current_scores]
        avg_posture_score = sum(posture_scores) / max(len(posture_scores), 1)
        avg_focus_score = sum(focus_scores) / max(len(focus_scores), 1)

        with open(config.STUDY_EVENTS_CSV_PATH, "a", newline="") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow([
                self.current_started_at.strftime("%Y-%m-%d %H:%M:%S"),
                ended_at.strftime("%Y-%m-%d %H:%M:%S"),
                self.current_state,
                round(duration, 1),
                round(avg_posture_score, 1),
                round(avg_focus_score, 1),
            ])
