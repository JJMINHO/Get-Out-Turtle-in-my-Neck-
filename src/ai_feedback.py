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
        self.cooldown_seconds = int(getattr(config, "AI_FEEDBACK_COOLDOWN_SECONDS", 600))
        self.trigger_cooldown_seconds = int(getattr(config, "AI_FEEDBACK_TRIGGER_COOLDOWN_SECONDS", 300))
        self.timeout_seconds = int(getattr(config, "AI_FEEDBACK_TIMEOUT_SECONDS", 8))
        self.latest_feedback = None
        self.last_request_time = 0
        self.last_context_signature = None
        self.event_cache = []
        self.event_cache_time = 0
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
        upcoming_events = self._get_cached_upcoming_events(now)
        feedback_mode = self._feedback_mode(context, upcoming_events)
        if feedback_mode is None:
            with self.lock:
                self.latest_feedback = None
                self.last_context_signature = None
            return fallback

        context_signature = self._context_signature(context, upcoming_events, feedback_mode)

        with self.lock:
            if self.in_flight:
                return self.latest_feedback or fallback

            cooldown = self.trigger_cooldown_seconds if feedback_mode == "schedule" else self.cooldown_seconds
            context_changed = context_signature != self.last_context_signature
            should_request = (
                (self.latest_feedback is None or context_changed)
                and now - self.last_request_time >= cooldown
            )
            cached_feedback = self.latest_feedback

        if should_request:
            self._request_async(context, fallback, upcoming_events, context_signature, feedback_mode)

        return cached_feedback or fallback

    def _get_cached_upcoming_events(self, now):
        if now - self.event_cache_time < 60:
            return self.event_cache

        self.event_cache = self._read_upcoming_events()
        self.event_cache_time = now
        return self.event_cache

    def _context_signature(self, context, upcoming_events, feedback_mode):
        event_signature = tuple(
            (event["date"].isoformat(), event["type"], event["priority"])
            for event in upcoming_events[:3]
        )
        return (
            feedback_mode,
            self._score_bucket(context.get("performance_score", 0)),
            self._score_bucket(context.get("focus_score", 0)),
            context.get("focus_status"),
            context.get("study_state"),
            int(context.get("today_time_seconds", 0) // 900),
            int(context.get("session_time_seconds", 0) // 600),
            int(context.get("consecutive_distracted_seconds", 0) // 30),
            event_signature,
        )

    def _score_bucket(self, value):
        try:
            return int(float(value) // 10)
        except (TypeError, ValueError):
            return 0

    def _feedback_mode(self, context, upcoming_events):
        if self._has_schedule_pressure(upcoming_events) and self._has_focus_or_work_concern(context):
            return "schedule"
        return "general"

    def _has_schedule_pressure(self, upcoming_events):
        today = datetime.now().date()
        for event in upcoming_events:
            days_left = (event["date"] - today).days
            if days_left <= 1 or (days_left <= 3 and event.get("priority") == "high"):
                return True
        return False

    def _has_focus_or_work_concern(self, context):
        focus_score = context.get("focus_score", 100)
        consecutive_distracted = context.get("consecutive_distracted_seconds", 0)
        focus_status = context.get("focus_status")
        work_seconds = context.get("today_time_seconds", 0)

        if focus_score < 55:
            return True
        if focus_status in ("Away", "Distracted"):
            return True
        if consecutive_distracted >= 20:
            return True
        if work_seconds < 1800:
            return True

        return False

    def _request_async(self, context, fallback, upcoming_events, context_signature, feedback_mode):
        with self.lock:
            self.in_flight = True
            self.last_request_time = time.time()
            self.last_context_signature = context_signature

        thread = threading.Thread(
            target=self._request_feedback,
            args=(context, fallback, upcoming_events, feedback_mode),
            daemon=True,
        )
        thread.start()

    def _request_feedback(self, context, fallback, upcoming_events, feedback_mode):
        try:
            prompt = self._build_prompt(context, upcoming_events, feedback_mode)
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

    def _build_prompt(self, context, upcoming_events, feedback_mode):
        event_text = self._format_events(upcoming_events)
        performance_score = self._safe_float(context.get("performance_score"))
        performance_instruction = self._performance_instruction(performance_score)
        if feedback_mode == "schedule":
            mode_instruction = (
                "Use the nearby exam, deadline, or project as the main reason for the nudge. "
                "Connect the user's current focus/work data to one immediate next action."
            )
            examples = """
- 내일 제출이 있으니 지금은 가장 중요한 부분 하나만 골라 20분 동안 처리하세요.
- 마감이 가까운데 집중이 흔들리고 있습니다. 지금은 자료를 더 찾지 말고 작성 중인 부분부터 마무리하세요.
- 시험이 가까우니 지금은 범위를 넓히지 말고 헷갈리는 항목 하나만 바로 정리하세요.
""".strip()
        else:
            mode_instruction = (
                "No urgent schedule is driving this message. "
                "Give a general work or study motivation nudge based on the user's current work rhythm."
            )
            examples = """
- 지금은 시작을 늦추지 말고 20분 안에 끝낼 수 있는 일 하나만 고르세요.
- 오늘은 완벽하게 하려 하지 말고 바로 끝낼 수 있는 작은 단위 하나부터 처리하세요.
- 흐름이 끊기기 전에 가장 쉬운 작업 하나를 정해 바로 손을 대세요.
""".strip()

        return f"""
You write Korean feedback for a schedule-aware focus dashboard.
Write exactly 1 short Korean sentence in polite 존댓말.
Tone: natural, calm, direct, and practical.
Sound like a Korean desk app giving a useful nudge, not a chatbot, teacher, drill sergeant, or motivational speaker.
Do not insult, shame, tease, threaten, exaggerate, role-play, use slang, use emojis, or mention medical claims.
Do not use labels like "피드백:", "코치:", "주의:", or markdown.
Include one immediate action the user should take now.

Good examples:
{examples}

Avoid these patterns:
- Panic or doom warnings.
- Comments about the user's personality or identity.
- Self-introductions, labels, markdown, or dramatic slogans.
- Stiff expressions like "제출용 핵심 작업", "진도를 내십시오", "형태로 먼저", "준비를 넓히지 말고".

Feedback mode:
{feedback_mode}

Mode instruction:
{mode_instruction}

Performance score guidance:
- Current performance score: {performance_score:.1f} / 100.
- {performance_instruction}

Current work data:
- Day boundary starts at 05:00.
- Today's actual work time: {context.get("today_time_text")}
- Current session time: {context.get("session_time_text")}
- Performance score: {performance_score:.1f} / 100
- Focus score: {context.get("focus_score")} / 100 ({context.get("focus_status")})
- Focused time in this session: {context.get("focused_time_text")}
- Best focus streak: {context.get("max_focused_time_text")}
- Away time: {context.get("away_time_text")}
- No face time: {context.get("no_face_time_text")}
- Current work state: {context.get("study_state")}
- Consecutive distracted/away seconds: {context.get("consecutive_distracted_seconds", 0)}s

Do not give posture advice. Posture feedback is handled locally by detection metrics.

Upcoming exams, deadlines, or projects:
{event_text}

Return only the feedback text.
""".strip()

    def _performance_instruction(self, performance_score):
        if performance_score < 40:
            return (
                "The score is poor, so be firmer and more urgent, but still polite. "
                "Tell the user to stop spreading attention and start one tiny concrete task now."
            )
        if performance_score < 65:
            return (
                "The score is weak, so use a clear corrective nudge. "
                "Point the user toward one short, finishable work block."
            )
        if performance_score < 80:
            return (
                "The score is acceptable but not strong, so encourage preserving momentum with one focused action."
            )
        return (
            "The score is strong, so keep the tone steady and reinforce continuing the current rhythm."
        )

    def _safe_float(self, value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    def _call_openai(self, prompt):
        body = {
            "model": self.openai_model,
            "instructions": (
                "Write natural Korean feedback for a webcam-based posture and focus dashboard. "
                "Use one concise Korean sentence in polite 존댓말. "
                "Avoid stiff translated expressions and return only the feedback sentence."
            ),
            "input": prompt,
            "max_output_tokens": 80,
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
            with open(config.CALENDAR_EVENTS_CSV_PATH, "w", newline="", encoding="utf-8") as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(["date", "title", "type", "priority"])

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
        replacements = {
            "제출용 핵심 작업": "가장 중요한 부분",
            "진도를 내십시오": "바로 시작하세요",
            "진도를 내세요": "바로 시작하세요",
            "준비를 넓히지 말고": "범위를 더 늘리지 말고",
            "20분만 끊어서": "20분 동안",
            "형태로 먼저": "방식으로",
        }
        for source, target in replacements.items():
            cleaned = cleaned.replace(source, target)
        cleaned = cleaned.strip("\"'“”‘’")
        if len(cleaned) > 110:
            cleaned = cleaned[:107].rstrip() + "..."
        return cleaned
