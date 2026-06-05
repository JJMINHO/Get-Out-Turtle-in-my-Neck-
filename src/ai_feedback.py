"""
AI-powered coach feedback for the dashboard feedback card.
"""
import csv
import json
import os
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta

import src.config as config


class AiFeedbackCoach:
    def __init__(self):
        self.openai_api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        self.openai_model = os.environ.get("OPENAI_MODEL", config.OPENAI_MODEL).strip()
        self.gemini_api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        self.gemini_model = os.environ.get("GEMINI_MODEL", config.GEMINI_MODEL).strip()
        self.cooldown_seconds = int(getattr(config, "AI_FEEDBACK_COOLDOWN_SECONDS", 180))
        self.trigger_cooldown_seconds = int(getattr(config, "AI_FEEDBACK_TRIGGER_COOLDOWN_SECONDS", 60))
        self.timeout_seconds = int(getattr(config, "AI_FEEDBACK_TIMEOUT_SECONDS", 8))
        self.latest_feedback = None
        self.last_request_time = 0
        self.in_flight = False
        self.lock = threading.Lock()

    def get_feedback(self, context, fallback):
        if not self.openai_api_key:
            self.openai_api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        if not self.gemini_api_key:
            self.gemini_api_key = os.environ.get("GEMINI_API_KEY", "").strip()

        if not self.openai_api_key and not self.gemini_api_key:
            return fallback

        now = time.time()
        upcoming_events = self._read_upcoming_events()
        is_triggered = self._check_triggers(context, upcoming_events)

        with self.lock:
            if self.in_flight:
                return self.latest_feedback or fallback

            cooldown = self.trigger_cooldown_seconds if is_triggered else self.cooldown_seconds
            should_request = (now - self.last_request_time >= cooldown)
            cached_feedback = self.latest_feedback

        if should_request:
            self._request_async(context, fallback, upcoming_events)

        return cached_feedback or fallback

    def _check_triggers(self, context, upcoming_events):
        # 1. Focus Score drops below 45
        focus_score = context.get("focus_score", 100)
        if focus_score < 45:
            return True

        # 2. No Face / Away state persists for a while (>= 20 seconds)
        consecutive_distracted = context.get("consecutive_distracted_seconds", 0)
        if consecutive_distracted >= 20:
            return True

        # 3. D-1 or D-Day (D-0) calendar event exists
        today = datetime.now().date()
        for event in upcoming_events:
            days_left = (event["date"] - today).days
            if days_left <= 1:
                return True

        # 4. Today's study time is insufficient compared to target (session >= 5 mins)
        today_seconds = context.get("today_time_seconds", 0)
        target_hours = context.get("target_study_time_hours", 4.0)
        target_seconds = target_hours * 3600
        session_seconds = context.get("session_time_seconds", 0)
        if session_seconds >= 300 and today_seconds < target_seconds:
            return True

        return False

    def _request_async(self, context, fallback, upcoming_events):
        with self.lock:
            self.in_flight = True
            self.last_request_time = time.time()

        thread = threading.Thread(
            target=self._request_feedback,
            args=(context, fallback, upcoming_events),
            daemon=True,
        )
        thread.start()

    def _request_feedback(self, context, fallback, upcoming_events):
        try:
            prompt = self._build_prompt(context, upcoming_events)
            if self.openai_api_key:
                try:
                    feedback = self._call_openai(prompt)
                except Exception as exc:
                    if not self.gemini_api_key:
                        raise
                    print(f"OpenAI feedback unavailable; trying Gemini fallback. Error: {exc}")
                    feedback = self._call_gemini(prompt)
            else:
                feedback = self._call_gemini(prompt)
            cleaned_feedback = self._clean_feedback(feedback)
            if cleaned_feedback:
                with self.lock:
                    self.latest_feedback = cleaned_feedback
        except Exception as exc:
            print(f"AI feedback unavailable; using local feedback. Error: {exc}")
        finally:
            with self.lock:
                self.in_flight = False

    def _build_prompt(self, context, upcoming_events):
        event_text = self._format_events(upcoming_events)
        target_hours = context.get("target_study_time_hours", 4.0)
        return f"""
You write Korean feedback for a posture/focus dashboard.
Write exactly 1 or 2 short Korean sentences in polite 존댓말.
Tone: calm, direct, practical, and slightly firm.
Sound like a real productivity coach, not a chatbot, teacher, drill sergeant, or motivational speaker.
Do not insult, shame, tease, threaten, exaggerate, role-play, use slang, use emojis, or mention medical claims.
Do not use labels like "피드백:", "코치:", "주의:", or markdown.
Include one immediate action the user should take now.

Good examples:
- 지금은 시선을 다시 화면으로 돌리고 10분만 이어가세요. 자세는 턱을 살짝 당긴 상태로 잡으면 충분합니다.
- 마감이 가까우니 지금은 딴짓을 줄이고 한 작업만 끝내세요. 25분 동안 화면에서 시선을 떼지 않는 걸 목표로 가겠습니다.
- 오늘 작업 시간이 아직 부족합니다. 자세를 바로 세우고 다음 15분은 끊지 말고 채우세요.

Avoid these patterns:
- Panic or doom warnings.
- Comments about the user's personality or identity.
- Self-introductions, labels, markdown, or dramatic slogans.

Current study data:
- Study day starts at 05:00.
- Today's target work/study time: {target_hours} hours
- Today's actual work/study time: {context.get("today_time_text")}
- Current session time: {context.get("session_time_text")}
- Posture score: {context.get("posture_score")} / 100 ({context.get("posture_status")})
- Focus score: {context.get("focus_score")} / 100 ({context.get("focus_status")})
- Focused time in this session: {context.get("focused_time_text")}
- Best focus streak: {context.get("max_focused_time_text")}
- Away time: {context.get("away_time_text")}
- No face time: {context.get("no_face_time_text")}
- Current study state: {context.get("study_state")}
- Consecutive distracted/away seconds: {context.get("consecutive_distracted_seconds", 0)}s

Upcoming exams, deadlines, or projects:
{event_text}

Return only the feedback text.
""".strip()

    def _call_openai(self, prompt):
        body = {
            "model": self.openai_model,
            "instructions": (
                "Write natural Korean feedback for a webcam-based posture and focus dashboard. "
                "Use polite 존댓말, stay concise, practical, and slightly firm. "
                "Return only the feedback sentence or sentences."
            ),
            "input": prompt,
            "max_output_tokens": 120,
        }
        request = urllib.request.Request(
            "https://api.openai.com/v1/responses",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.openai_api_key}",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            response_body = response.read().decode("utf-8")

        payload = json.loads(response_body)
        output_text = payload.get("output_text")
        if output_text:
            return output_text.strip()

        text_parts = []
        for output_item in payload.get("output", []):
            for content_item in output_item.get("content", []):
                if content_item.get("type") in ("output_text", "text"):
                    text_parts.append(content_item.get("text", ""))
        return "\n".join(text_parts).strip()

    def _call_gemini(self, prompt):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.gemini_model}:generateContent"
        body = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.45,
                "maxOutputTokens": 120,
            },
        }
        request = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": self.gemini_api_key,
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            response_body = response.read().decode("utf-8")

        payload = json.loads(response_body)
        candidates = payload.get("candidates", [])
        if not candidates:
            return ""
        parts = candidates[0].get("content", {}).get("parts", [])
        return "\n".join(part.get("text", "") for part in parts).strip()

    def _read_upcoming_events(self):
        if not os.path.exists(config.CALENDAR_EVENTS_CSV_PATH):
            self._ensure_calendar_events_csv()

        today = datetime.now().date()
        horizon = today + timedelta(days=14)
        events = []
        try:
            with open(config.CALENDAR_EVENTS_CSV_PATH, "r", newline="", encoding="utf-8") as csv_file:
                reader = csv.DictReader(csv_file)
                for row in reader:
                    event_date = self._parse_date(row.get("date"))
                    if event_date is None or event_date < today or event_date > horizon:
                        continue
                    events.append({
                        "date": event_date,
                        "title": row.get("title", "Untitled"),
                        "type": row.get("type", "deadline"),
                        "priority": row.get("priority", "normal"),
                    })
        except Exception as exc:
            print(f"Could not read calendar events: {exc}")
            return []

        return sorted(events, key=lambda item: item["date"])[:6]

    def _ensure_calendar_events_csv(self):
        os.makedirs(os.path.dirname(config.CALENDAR_EVENTS_CSV_PATH), exist_ok=True)
        if not os.path.exists(config.CALENDAR_EVENTS_CSV_PATH):
            today = datetime.now()
            exam_date = (today + timedelta(days=5)).strftime("%Y-%m-%d")
            project_date = (today + timedelta(days=7)).strftime("%Y-%m-%d")
            with open(config.CALENDAR_EVENTS_CSV_PATH, "w", newline="", encoding="utf-8") as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(["date", "title", "type", "priority"])
                writer.writerow([exam_date, "운영체제 기말고사", "exam", "high"])
                writer.writerow([project_date, "프로젝트 제출", "deadline", "high"])

    def _format_events(self, events):
        if not events:
            return "- No upcoming events registered."

        today = datetime.now().date()
        lines = []
        for event in events:
            days_left = (event["date"] - today).days
            if days_left == 0:
                timing = "today"
            elif days_left == 1:
                timing = "tomorrow"
            else:
                timing = f"in {days_left} days"
            lines.append(
                f"- {event['date']} ({timing}) {event['type']}: {event['title']} priority={event['priority']}"
            )
        return "\n".join(lines)

    def _parse_date(self, value):
        if not value:
            return None
        try:
            return datetime.strptime(value.strip(), "%Y-%m-%d").date()
        except ValueError:
            return None

    def _clean_feedback(self, feedback):
        cleaned = " ".join(feedback.split())
        for prefix in ("피드백:", "코치:", "주의:", "조언:", "Feedback:", "Coach:"):
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):].strip()
        cleaned = cleaned.strip("\"'“”‘’")
        if len(cleaned) > 140:
            cleaned = cleaned[:137].rstrip() + "..."
        return cleaned
