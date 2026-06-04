"""
Healthcare-style dashboard UI for the live posture analysis view.
"""
import calendar
import csv
import os
from datetime import datetime

import customtkinter as ctk
from PIL import Image
import cv2

import src.config as config
from src.daily_score import DailyScoreCalculator
from src.study_session import study_day_string


COLORS = {
    "background": "#F4FAF9",
    "card": "#FFFFFF",
    "primary_mint": "#2DD4BF",
    "primary_blue": "#3B82F6",
    "text_main": "#111827",
    "text_sub": "#6B7280",
    "border": "#E5E7EB",
    "normal": "#10B981",
    "caution": "#F59E0B",
    "danger": "#EF4444",
    "muted": "#EEF2F7",
}

FONT_FAMILY = "Apple SD Gothic Neo"
FONT_TITLE = (FONT_FAMILY, 28, "bold")
FONT_SUBTITLE = (FONT_FAMILY, 14)
FONT_SECTION = (FONT_FAMILY, 16, "bold")
FONT_BODY = (FONT_FAMILY, 14)
FONT_VALUE = (FONT_FAMILY, 40, "bold")
FONT_BUTTON = (FONT_FAMILY, 15, "bold")


def _risk_from_status(status):
    if status == "Good" or status == "Normal":
        return "Normal", COLORS["normal"]
    if status == "Warning" or status == "Caution" or str(status).startswith("Calibrating"):
        return "Caution", COLORS["caution"]
    return "Danger", COLORS["danger"]


def _feedback_for_status(status):
    if str(status).startswith("Calibrating"):
        return "정자세를 유지하며 기준 자세를 측정하고 있습니다."
    if status == "Good" or status == "Normal":
        return "현재 자세가 안정적입니다. 이 자세를 유지하세요."
    if status == "Warning" or status == "Caution":
        return "목이 약간 앞으로 나와 있습니다. 턱을 살짝 당겨주세요."
    if status == "No Pose":
        return "상체가 카메라에 보이도록 앉아주세요."
    return "거북목 위험도가 높습니다. 귀와 어깨가 일직선이 되도록 자세를 조정하세요."


def _focus_color(status):
    if status == "Focused":
        return COLORS["normal"]
    if status == "Distracted":
        return COLORS["caution"]
    return COLORS["danger"]


def _format_seconds(seconds):
    hours, remainder = divmod(int(seconds), 3600)
    minutes, secs = divmod(remainder, 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def _format_hours_minutes(seconds):
    hours, remainder = divmod(int(seconds), 3600)
    minutes, _secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}"


def _safe_int(value):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def _percent(value):
    return f"{int(round(max(0, min(float(value), 1.0)) * 100))}%"


def _create_card(parent, **pack_options):
    card = ctk.CTkFrame(
        parent,
        fg_color=COLORS["card"],
        corner_radius=18,
        border_width=1,
        border_color=COLORS["border"],
    )
    card.pack(**pack_options)
    return card


def _make_button(parent, text, command, fg_color, text_color, border_color=None):
    return ctk.CTkButton(
        parent,
        text=text,
        command=command,
        height=46,
        corner_radius=14,
        font=FONT_BUTTON,
        fg_color=fg_color,
        hover_color=fg_color,
        text_color=text_color,
        border_width=1 if border_color else 0,
        border_color=border_color or fg_color,
    )


def run_dashboard(data_queue, command_queue=None, command_poller=None, on_close_callback=None):
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")

    app = ctk.CTk()
    app.geometry("1280x840")
    app.minsize(900, 680)
    app.title("NeckCare Vision")
    app.configure(fg_color=COLORS["background"])

    def send_command(command):
        if command_queue is not None:
            command_queue.put(command)

    is_studying = {"value": False}
    latest_stats = {"value": {}}
    daily_score_calculator = DailyScoreCalculator()
    daily_score_cache = {"updated_at": 0, "report": daily_score_calculator.calculate()}

    def toggle_study():
        send_command("TOGGLE_STUDY")

    def current_daily_score():
        now = datetime.now().timestamp()
        if now - daily_score_cache["updated_at"] >= 5:
            current_stats = latest_stats["value"] or None
            if current_stats and not current_stats.get("is_running", False):
                current_stats = None
            daily_score_cache["report"] = daily_score_calculator.calculate(
                day=study_day_string(),
                current_stats=current_stats,
            )
            daily_score_cache["updated_at"] = now
        return daily_score_cache["report"]

    def add_metric_bar(parent, label, value, color, max_value=1.0):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(
            row,
            text=label,
            font=(FONT_FAMILY, 13, "bold"),
            text_color=COLORS["text_main"],
            width=160,
            anchor="w",
        ).pack(side="left")
        bar = ctk.CTkProgressBar(row, height=12, progress_color=color, fg_color="#E5E7EB")
        bar.pack(side="left", fill="x", expand=True, padx=(10, 10))
        bar.set(0 if max_value <= 0 else max(0, min(float(value) / float(max_value), 1.0)))
        ctk.CTkLabel(
            row,
            text=_percent(value / max_value if max_value > 1 else value),
            font=(FONT_FAMILY, 12, "bold"),
            text_color=COLORS["text_sub"],
            width=46,
        ).pack(side="right")

    def add_quadrant_tile(parent, row, column, title, subtitle, count, color, selected=False):
        tile = ctk.CTkFrame(
            parent,
            fg_color="#F8FAFC" if not selected else "#E6FFFB",
            corner_radius=14,
            border_width=2 if selected else 1,
            border_color=color if selected else COLORS["border"],
        )
        tile.grid(row=row, column=column, sticky="nsew", padx=6, pady=6)
        ctk.CTkLabel(
            tile,
            text=title,
            font=(FONT_FAMILY, 15, "bold"),
            text_color=color,
        ).pack(anchor="w", padx=14, pady=(12, 2))
        ctk.CTkLabel(
            tile,
            text=subtitle,
            font=(FONT_FAMILY, 12),
            text_color=COLORS["text_sub"],
            wraplength=160,
            justify="left",
        ).pack(anchor="w", padx=14)
        ctk.CTkLabel(
            tile,
            text=f"{count}",
            font=(FONT_FAMILY, 24, "bold"),
            text_color=COLORS["text_main"],
        ).pack(anchor="w", padx=14, pady=(4, 12))

    def add_timeline_summary(parent, report, state_colors):
        durations = report["event_durations"]
        bar = ctk.CTkFrame(parent, fg_color="#E5E7EB", height=20, corner_radius=10)
        bar.pack(fill="x", padx=18, pady=(0, 12))
        bar.pack_propagate(False)

        offset = 0.0
        visible_durations = sorted(durations.items(), key=lambda item: item[1], reverse=True)[:5]
        visible_total = max(sum(duration for _event_type, duration in visible_durations), 1)
        for event_type, duration in visible_durations:
            ratio = duration / visible_total
            segment = ctk.CTkFrame(
                bar,
                fg_color=state_colors.get(event_type, COLORS["text_sub"]),
                corner_radius=8,
            )
            segment.place(relx=offset, rely=0, relwidth=min(ratio, 1.0 - offset), relheight=1)
            offset = min(1.0, offset + ratio)
            if offset >= 1.0:
                break

        legend = ctk.CTkFrame(parent, fg_color="transparent")
        legend.pack(fill="x", padx=18, pady=(0, 10))
        for event_type, duration in sorted(durations.items(), key=lambda item: item[1], reverse=True)[:5]:
            item = ctk.CTkLabel(
                legend,
                text=f"{event_type} {_format_seconds(duration)}",
                font=(FONT_FAMILY, 12, "bold"),
                text_color=state_colors.get(event_type, COLORS["text_sub"]),
            )
            item.pack(side="left", padx=(0, 14))

    def show_daily_report_window():
        report = current_daily_score()

        window = ctk.CTkToplevel(app)
        window.title("Daily Vision Report")
        window.geometry("960x720")
        window.minsize(860, 620)
        window.configure(fg_color=COLORS["background"])
        window.transient(app)
        window.focus()

        shell = ctk.CTkFrame(window, fg_color=COLORS["background"])
        shell.pack(fill="both", expand=True, padx=26, pady=24)

        header_row = ctk.CTkFrame(shell, fg_color="transparent")
        header_row.pack(fill="x", pady=(0, 18))
        ctk.CTkLabel(
            header_row,
            text="Daily Vision Report",
            font=(FONT_FAMILY, 26, "bold"),
            text_color=COLORS["text_main"],
        ).pack(side="left")
        ctk.CTkLabel(
            header_row,
            text=report["date"],
            font=(FONT_FAMILY, 15, "bold"),
            text_color=COLORS["primary_blue"],
            fg_color="#EAF4FF",
            corner_radius=14,
            padx=14,
            pady=7,
        ).pack(side="right")

        top = ctk.CTkFrame(shell, fg_color="transparent")
        top.pack(fill="x", pady=(0, 16))

        score_card = _create_card(top, side="left", fill="both", expand=True, padx=(0, 14))
        ctk.CTkLabel(
            score_card,
            text="Daily Study Score",
            font=FONT_SECTION,
            text_color=COLORS["text_sub"],
        ).pack(anchor="w", padx=22, pady=(20, 0))
        score_color = COLORS["normal"] if report["daily_score"] >= 75 else COLORS["caution"]
        if report["daily_score"] < 50:
            score_color = COLORS["danger"]
        ctk.CTkLabel(
            score_card,
            text=f"{report['daily_score']:.1f}",
            font=(FONT_FAMILY, 56, "bold"),
            text_color=score_color,
        ).pack(anchor="w", padx=22, pady=(2, 14))

        parts_card = _create_card(top, side="left", fill="both", expand=True)
        ctk.CTkLabel(
            parts_card,
            text="Score Parts",
            font=FONT_SECTION,
            text_color=COLORS["text_sub"],
        ).pack(anchor="w", padx=22, pady=(20, 12))
        add_metric_bar(parts_card, "집중농도", report["focus_part"], COLORS["primary_mint"], 40)
        add_metric_bar(parts_card, "학습량", report["time_part"], COLORS["primary_blue"], 30)
        add_metric_bar(parts_card, "비전 품질", report["quality_part"], COLORS["normal"], 30)

        middle = ctk.CTkFrame(shell, fg_color="transparent")
        middle.pack(fill="x", pady=(0, 16))

        ratio_card = _create_card(middle, side="left", fill="both", expand=True, padx=(0, 14))
        ctk.CTkLabel(ratio_card, text="Daily Metrics", font=FONT_SECTION, text_color=COLORS["text_sub"]).pack(
            anchor="w", padx=22, pady=(20, 12)
        )
        add_metric_bar(ratio_card, "집중 비율", report["focus_density"], COLORS["primary_mint"])
        add_metric_bar(ratio_card, "목표 학습량", report["time_ratio"], COLORS["primary_blue"])
        add_metric_bar(ratio_card, "좋은 자세", report["good_posture_ratio"], COLORS["normal"])
        add_metric_bar(ratio_card, "화면 안정성", report["stable_presence_ratio"], COLORS["caution"])

        quadrant_card = _create_card(middle, side="left", fill="both", expand=True)
        ctk.CTkLabel(
            quadrant_card,
            text="Focus x Posture Quadrant",
            font=FONT_SECTION,
            text_color=COLORS["text_sub"],
        ).pack(anchor="w", padx=22, pady=(20, 12))
        quadrants = report["quadrants"]
        dominant_quadrant = max(quadrants.items(), key=lambda item: item[1])[0] if quadrants else "strong"
        quadrant_grid = ctk.CTkFrame(quadrant_card, fg_color="transparent")
        quadrant_grid.pack(fill="both", expand=True, padx=16, pady=(0, 18))
        for row_index in range(2):
            quadrant_grid.grid_rowconfigure(row_index, weight=1)
        for column_index in range(2):
            quadrant_grid.grid_columnconfigure(column_index, weight=1)
        add_quadrant_tile(
            quadrant_grid,
            0,
            0,
            "Strong",
            "Focus high / Posture high",
            quadrants["strong"],
            COLORS["normal"],
            dominant_quadrant == "strong",
        )
        add_quadrant_tile(
            quadrant_grid,
            0,
            1,
            "Posture Risk",
            "Focus high / Posture low",
            quadrants["posture_risk"],
            COLORS["caution"],
            dominant_quadrant == "posture_risk",
        )
        add_quadrant_tile(
            quadrant_grid,
            1,
            0,
            "Focus Risk",
            "Focus low / Posture high",
            quadrants["focus_risk"],
            COLORS["primary_blue"],
            dominant_quadrant == "focus_risk",
        )
        add_quadrant_tile(
            quadrant_grid,
            1,
            1,
            "Low Quality",
            "Focus low / Posture low",
            quadrants["low_quality"],
            COLORS["danger"],
            dominant_quadrant == "low_quality",
        )

        timeline_card = _create_card(shell, fill="both", expand=True)
        ctk.CTkLabel(
            timeline_card,
            text="Study State Timeline",
            font=FONT_SECTION,
            text_color=COLORS["text_sub"],
        ).pack(anchor="w", padx=22, pady=(18, 10))
        timeline = ctk.CTkScrollableFrame(timeline_card, fg_color="#F8FAFC", corner_radius=14)
        timeline.pack(fill="both", expand=True, padx=18, pady=(0, 18))

        state_colors = {
            "Focused": COLORS["normal"],
            "Reading": COLORS["primary_blue"],
            "Bad Posture": COLORS["caution"],
            "Looking Away": COLORS["danger"],
            "No Face": COLORS["danger"],
            "Drowsy": COLORS["danger"],
            "Distracted": COLORS["caution"],
        }
        if report["event_durations"]:
            add_timeline_summary(timeline_card, report, state_colors)
        if not report["events"]:
            ctk.CTkLabel(
                timeline,
                text="아직 기록된 study event가 없습니다.",
                font=FONT_BODY,
                text_color=COLORS["text_sub"],
            ).pack(anchor="w", padx=14, pady=14)
        for event in report["events"]:
            color = state_colors.get(event["event_type"], COLORS["text_sub"])
            row = ctk.CTkFrame(timeline, fg_color="#FFFFFF", corner_radius=10)
            row.pack(fill="x", padx=10, pady=(10, 0))
            ctk.CTkLabel(row, text=" ", width=8, fg_color=color, corner_radius=4).pack(side="left", fill="y")
            text = (
                f"{event['start_time'][-8:]} - {event['end_time'][-8:]}  "
                f"{event['event_type']}  {_format_seconds(event['duration'])}"
            )
            ctk.CTkLabel(
                row,
                text=text,
                font=(FONT_FAMILY, 13, "bold"),
                text_color=COLORS["text_main"],
            ).pack(side="left", padx=12, pady=10)

    def build_calendar_data():
        daily_totals = {}
        if os.path.exists(config.DAILY_SESSIONS_CSV_PATH):
            try:
                with open(config.DAILY_SESSIONS_CSV_PATH, "r", newline="") as csv_file:
                    reader = csv.DictReader(csv_file)
                    for row in reader:
                        day = row.get("date")
                        if not day:
                            continue
                        entry = daily_totals.setdefault(day, {"study": 0, "focus": 0})
                        entry["study"] += _safe_int(row.get("duration_seconds"))
                        entry["focus"] += _safe_int(row.get("focused_seconds"))
            except Exception as exc:
                return {}, {}, f"캘린더 데이터를 읽을 수 없습니다: {exc}"

        stats = latest_stats["value"]
        if stats:
            today = study_day_string()
            entry = daily_totals.setdefault(today, {"study": 0, "focus": 0})
            entry["study"] += _safe_int(stats.get("session_seconds", 0))
            entry["focus"] += _safe_int(stats.get("focused_time", 0))

        return daily_totals, build_event_records(), None

    def build_event_records():
        if not os.path.exists(config.CALENDAR_EVENTS_CSV_PATH):
            return []

        events = []
        try:
            with open(config.CALENDAR_EVENTS_CSV_PATH, "r", newline="") as csv_file:
                reader = csv.DictReader(csv_file)
                for index, row in enumerate(reader):
                    day = row.get("date")
                    title = row.get("title")
                    if day and title:
                        events.append({
                            "id": str(index),
                            "date": day,
                            "title": title,
                            "type": row.get("type", "deadline"),
                            "priority": row.get("priority", "normal"),
                        })
        except Exception:
            return []

        return events

    def show_calendar_window():
        daily_totals, event_records, error_message = build_calendar_data()
        active_study_day = study_day_string()
        active_date = datetime.strptime(active_study_day, "%Y-%m-%d")
        visible_month = {"year": active_date.year, "month": active_date.month}
        selected_event_id = {"value": None}

        window = ctk.CTkToplevel(app)
        window.title("DeskPose Calendar")
        window.geometry("1280x800")
        window.minsize(1120, 720)
        window.configure(fg_color=COLORS["background"])
        window.transient(app)
        window.focus()

        shell = ctk.CTkFrame(window, fg_color=COLORS["background"])
        shell.pack(fill="both", expand=True, padx=24, pady=22)

        top_bar = ctk.CTkFrame(shell, fg_color="transparent")
        top_bar.pack(fill="x", pady=(0, 16))

        title_area = ctk.CTkFrame(top_bar, fg_color="transparent")
        title_area.pack(side="left")
        ctk.CTkLabel(
            title_area,
            text="캘린더",
            font=(FONT_FAMILY, 24, "bold"),
            text_color=COLORS["text_main"],
        ).pack(anchor="w")
        ctk.CTkLabel(
            title_area,
            text="학습일은 05:00부터 다음날 04:59까지입니다.",
            font=FONT_BODY,
            text_color=COLORS["text_sub"],
        ).pack(anchor="w", pady=(2, 0))

        month_label = ctk.CTkLabel(
            top_bar,
            text="",
            font=(FONT_FAMILY, 18, "bold"),
            text_color=COLORS["text_main"],
        )
        month_label.pack(side="right", padx=(14, 0))

        body = ctk.CTkFrame(shell, fg_color="transparent")
        body.pack(fill="both", expand=True)
        body.grid_columnconfigure(0, weight=3, minsize=620)
        body.grid_columnconfigure(1, weight=2, minsize=360)
        body.grid_rowconfigure(0, weight=1)

        calendar_frame = ctk.CTkFrame(
            body,
            fg_color=COLORS["card"],
            border_width=1,
            border_color=COLORS["border"],
            corner_radius=16,
        )
        calendar_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 16))

        manage_panel = ctk.CTkFrame(
            body,
            fg_color=COLORS["card"],
            border_width=1,
            border_color=COLORS["border"],
            corner_radius=16,
        )
        manage_panel.grid(row=0, column=1, sticky="nsew")

        nav_frame = ctk.CTkFrame(top_bar, fg_color="transparent")
        nav_frame.pack(side="right")

        def shift_month(delta):
            month_index = visible_month["month"] + delta
            year = visible_month["year"]
            if month_index < 1:
                month_index = 12
                year -= 1
            elif month_index > 12:
                month_index = 1
                year += 1
            visible_month["year"] = year
            visible_month["month"] = month_index
            render_month()

        ctk.CTkButton(
            nav_frame,
            text="<",
            command=lambda: shift_month(-1),
            width=42,
            height=36,
            corner_radius=12,
            font=(FONT_FAMILY, 16, "bold"),
            fg_color="#FFFFFF",
            hover_color="#F8FAFC",
            text_color=COLORS["text_main"],
            border_width=1,
            border_color=COLORS["border"],
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            nav_frame,
            text="이번 달",
            command=lambda: go_today(),
            width=78,
            height=36,
            corner_radius=12,
            font=(FONT_FAMILY, 13, "bold"),
            fg_color="#FFFFFF",
            hover_color="#F8FAFC",
            text_color=COLORS["text_main"],
            border_width=1,
            border_color=COLORS["border"],
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            nav_frame,
            text=">",
            command=lambda: shift_month(1),
            width=42,
            height=36,
            corner_radius=12,
            font=(FONT_FAMILY, 16, "bold"),
            fg_color="#FFFFFF",
            hover_color="#F8FAFC",
            text_color=COLORS["text_main"],
            border_width=1,
            border_color=COLORS["border"],
        ).pack(side="left")

        ctk.CTkLabel(
            manage_panel,
            text="일정 관리",
            font=(FONT_FAMILY, 20, "bold"),
            text_color=COLORS["text_main"],
        ).pack(anchor="w", padx=18, pady=(18, 4))

        form_card = ctk.CTkFrame(manage_panel, fg_color="transparent")
        form_card.pack(fill="x", padx=18, pady=(10, 0))

        ctk.CTkLabel(
            form_card,
            text="날짜",
            font=(FONT_FAMILY, 13, "bold"),
            text_color=COLORS["text_main"],
        ).pack(anchor="w", pady=(0, 6))

        date_entry = ctk.CTkEntry(
            form_card,
            height=38,
            font=FONT_BODY,
            placeholder_text="YYYY-MM-DD",
        )
        date_entry.insert(0, active_study_day)
        date_entry.pack(fill="x", pady=(0, 6))

        date_picker_visible = {"value": False}
        date_picker = ctk.CTkScrollableFrame(
            form_card,
            height=72,
            fg_color="#F8FAFC",
            corner_radius=12,
            border_width=1,
            border_color=COLORS["border"],
        )

        title_entry = ctk.CTkEntry(
            form_card,
            height=38,
            font=FONT_BODY,
            placeholder_text="일정 이름 없이 추가 가능",
        )
        title_entry.pack(fill="x", pady=(0, 8))

        select_row = ctk.CTkFrame(form_card, fg_color="transparent")
        select_row.pack(fill="x", pady=(0, 8))

        type_menu = ctk.CTkOptionMenu(
            select_row,
            values=["none", "exam", "deadline", "project", "assignment"],
            width=180,
            height=38,
            fg_color="#FFFFFF",
            button_color=COLORS["primary_mint"],
            button_hover_color=COLORS["primary_mint"],
            text_color=COLORS["text_main"],
            font=FONT_BODY,
        )
        type_menu.set("none")
        type_menu.pack(side="left", fill="x", expand=True, padx=(0, 8))

        priority_menu = ctk.CTkOptionMenu(
            select_row,
            values=["high", "normal", "low"],
            width=130,
            height=38,
            fg_color="#FFFFFF",
            button_color=COLORS["primary_blue"],
            button_hover_color=COLORS["primary_blue"],
            text_color=COLORS["text_main"],
            font=FONT_BODY,
        )
        priority_menu.set("normal")
        priority_menu.pack(side="left")

        action_row = ctk.CTkFrame(form_card, fg_color="transparent")
        action_row.pack(fill="x", pady=(2, 10))

        form_status = ctk.CTkLabel(
            manage_panel,
            text="",
            font=(FONT_FAMILY, 12, "bold"),
            text_color=COLORS["text_sub"],
        )
        form_status.pack(anchor="w", padx=18, pady=(0, 10))

        ctk.CTkLabel(
            manage_panel,
            text="등록된 일정",
            font=(FONT_FAMILY, 15, "bold"),
            text_color=COLORS["text_main"],
        ).pack(anchor="w", padx=18, pady=(2, 8))

        event_list = ctk.CTkScrollableFrame(
            manage_panel,
            fg_color="#F8FAFC",
            corner_radius=14,
            border_width=1,
            border_color=COLORS["border"],
        )
        event_list.pack(fill="both", expand=True, padx=18, pady=(0, 18))

        def ensure_calendar_events_file():
            os.makedirs(os.path.dirname(config.CALENDAR_EVENTS_CSV_PATH), exist_ok=True)
            if os.path.exists(config.CALENDAR_EVENTS_CSV_PATH):
                return
            with open(config.CALENDAR_EVENTS_CSV_PATH, "w", newline="") as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(["date", "title", "type", "priority"])

        def write_calendar_events():
            ensure_calendar_events_file()
            with open(config.CALENDAR_EVENTS_CSV_PATH, "w", newline="") as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(["date", "title", "type", "priority"])
                for event in event_records:
                    writer.writerow([
                        event["date"],
                        event["title"],
                        event["type"],
                        event["priority"],
                    ])

        def next_event_id():
            existing_ids = [_safe_int(event.get("id")) for event in event_records]
            return str((max(existing_ids) + 1) if existing_ids else 0)

        def find_selected_event():
            event_id = selected_event_id["value"]
            if event_id is None:
                return None
            for event in event_records:
                if event["id"] == event_id:
                    return event
            return None

        def clear_event_form():
            selected_event_id["value"] = None
            title_entry.delete(0, "end")
            type_menu.set("none")
            priority_menu.set("normal")
            form_status.configure(text="새 일정", text_color=COLORS["text_sub"])
            render_event_list()

        def hide_date_picker():
            if date_picker_visible["value"]:
                date_picker.pack_forget()
                date_picker_visible["value"] = False

        def show_date_picker():
            if not date_picker_visible["value"]:
                date_picker.pack(fill="x", pady=(0, 8), before=title_entry)
                date_picker_visible["value"] = True
                render_date_picker()

        def toggle_date_picker(_event=None):
            if date_picker_visible["value"]:
                hide_date_picker()
            else:
                show_date_picker()

        date_entry.bind("<Button-1>", toggle_date_picker)
        try:
            date_entry._entry.bind("<Button-1>", toggle_date_picker)
        except AttributeError:
            pass

        def select_date(day_key):
            date_entry.delete(0, "end")
            date_entry.insert(0, day_key)
            form_status.configure(text="날짜 선택됨", text_color=COLORS["primary_blue"])
            render_date_picker()
            hide_date_picker()

        def select_event(event_id):
            selected_event_id["value"] = event_id
            event = find_selected_event()
            if event is None:
                clear_event_form()
                return

            date_entry.delete(0, "end")
            date_entry.insert(0, event["date"])
            title_entry.delete(0, "end")
            title_entry.insert(0, event["title"])
            type_menu.set(event["type"])
            priority_menu.set(event["priority"])
            form_status.configure(text="선택됨", text_color=COLORS["primary_blue"])
            hide_date_picker()
            render_event_list()

        def read_event_form():
            day = date_entry.get().strip()
            title = title_entry.get().strip()
            event_type = type_menu.get().strip()
            priority = priority_menu.get().strip()

            try:
                parsed_day = datetime.strptime(day, "%Y-%m-%d")
            except ValueError:
                form_status.configure(text="날짜 형식을 확인하세요.", text_color=COLORS["danger"])
                return

            if not title:
                title = "메모 없음"

            return {
                "date": day,
                "title": title,
                "type": event_type,
                "priority": priority,
            }, parsed_day

        def add_calendar_event():
            event, parsed_day = read_event_form()
            if event is None:
                return

            event["id"] = next_event_id()
            event_records.append(event)
            write_calendar_events()
            visible_month["year"] = parsed_day.year
            visible_month["month"] = parsed_day.month
            selected_event_id["value"] = event["id"]
            title_entry.delete(0, "end")
            form_status.configure(text="추가됨", text_color=COLORS["normal"])
            render_month()
            render_event_list()

        def update_calendar_event():
            selected = find_selected_event()
            if selected is None:
                form_status.configure(text="수정할 일정을 선택하세요.", text_color=COLORS["danger"])
                return

            event, parsed_day = read_event_form()
            if event is None:
                return

            selected.update(event)
            write_calendar_events()
            visible_month["year"] = parsed_day.year
            visible_month["month"] = parsed_day.month
            form_status.configure(text="수정됨", text_color=COLORS["normal"])
            render_month()
            render_event_list()

        def delete_calendar_event():
            selected = find_selected_event()
            if selected is None:
                form_status.configure(text="삭제할 일정을 선택하세요.", text_color=COLORS["danger"])
                return

            event_records.remove(selected)
            write_calendar_events()
            clear_event_form()
            form_status.configure(text="삭제됨", text_color=COLORS["normal"])
            render_month()

        ctk.CTkButton(
            action_row,
            text="추가",
            command=add_calendar_event,
            width=76,
            height=42,
            corner_radius=12,
            font=FONT_BUTTON,
            fg_color=COLORS["primary_mint"],
            hover_color=COLORS["primary_mint"],
            text_color="#FFFFFF",
        ).pack(side="left", fill="x", expand=True, padx=(0, 6))
        ctk.CTkButton(
            action_row,
            text="수정",
            command=update_calendar_event,
            width=76,
            height=42,
            corner_radius=12,
            font=FONT_BUTTON,
            fg_color="#EFF6FF",
            hover_color="#EFF6FF",
            text_color=COLORS["primary_blue"],
            border_width=1,
            border_color="#BFDBFE",
        ).pack(side="left", fill="x", expand=True, padx=(0, 6))
        ctk.CTkButton(
            action_row,
            text="삭제",
            command=delete_calendar_event,
            width=76,
            height=42,
            corner_radius=12,
            font=FONT_BUTTON,
            fg_color="#FEF2F2",
            hover_color="#FEF2F2",
            text_color=COLORS["danger"],
            border_width=1,
            border_color="#FECACA",
        ).pack(side="left", fill="x", expand=True)

        def render_event_list():
            for child in event_list.winfo_children():
                child.destroy()

            if not event_records:
                ctk.CTkLabel(
                    event_list,
                    text="등록된 일정이 없습니다.",
                    font=FONT_BODY,
                    text_color=COLORS["text_sub"],
                ).pack(anchor="w", padx=12, pady=12)
                return

            sorted_events = sorted(event_records, key=lambda event: (event["date"], event["title"]))
            for event in sorted_events:
                selected = event["id"] == selected_event_id["value"]
                event_color = COLORS["danger"] if event["priority"] == "high" else COLORS["caution"]
                event_label = event["title"] if event["type"] == "none" else f"{event['type']} · {event['title']}"
                row = ctk.CTkButton(
                    event_list,
                    text=f"{event['date']}\n{event_label}",
                    command=lambda event_id=event["id"]: select_event(event_id),
                    height=54,
                    corner_radius=10,
                    font=(FONT_FAMILY, 13, "bold" if selected else "normal"),
                    fg_color="#E6FFFB" if selected else "#FFFFFF",
                    hover_color="#E6FFFB",
                    text_color=event_color if selected else COLORS["text_main"],
                    border_width=1,
                    border_color=COLORS["primary_mint"] if selected else COLORS["border"],
                    anchor="w",
                )
                row.pack(fill="x", padx=8, pady=(8, 0))

        def go_today():
            now = datetime.now()
            current_study_day = datetime.strptime(study_day_string(), "%Y-%m-%d")
            visible_month["year"] = current_study_day.year
            visible_month["month"] = current_study_day.month
            render_month()

        def render_date_picker():
            for child in date_picker.winfo_children():
                child.destroy()

            year = visible_month["year"]
            month = visible_month["month"]
            month_days = calendar.Calendar(firstweekday=6).itermonthdates(year, month)
            for day_date in month_days:
                if day_date.month != month:
                    continue

                day_key = day_date.strftime("%Y-%m-%d")
                selected = date_entry.get().strip() == day_key
                button = ctk.CTkButton(
                    date_picker,
                    text=f"{day_date.day:02d}  {day_key}",
                    command=lambda selected_day=day_key: select_date(selected_day),
                    height=32,
                    corner_radius=9,
                    font=(FONT_FAMILY, 12, "bold" if selected else "normal"),
                    fg_color="#E6FFFB" if selected else "#FFFFFF",
                    hover_color="#E6FFFB",
                    text_color=COLORS["primary_mint"] if selected else COLORS["text_main"],
                    border_width=1,
                    border_color=COLORS["primary_mint"] if selected else COLORS["border"],
                    anchor="w",
                )
                button.pack(fill="x", padx=6, pady=(6, 0))

        def render_month():
            for child in calendar_frame.winfo_children():
                child.destroy()
            render_date_picker()

            year = visible_month["year"]
            month = visible_month["month"]
            month_label.configure(text=f"{year}.{month:02d}")

            if error_message:
                ctk.CTkLabel(
                    calendar_frame,
                    text=error_message,
                    font=FONT_BODY,
                    text_color=COLORS["danger"],
                ).grid(row=0, column=0, columnspan=7, padx=18, pady=18, sticky="w")
                return

            weekday_labels = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
            for column, weekday in enumerate(weekday_labels):
                ctk.CTkLabel(
                    calendar_frame,
                    text=weekday,
                    font=(FONT_FAMILY, 13, "bold"),
                    text_color=COLORS["text_sub"],
                ).grid(row=0, column=column, padx=8, pady=(14, 8), sticky="ew")
                calendar_frame.grid_columnconfigure(column, weight=1, uniform="calendar-day")

            month_matrix = calendar.Calendar(firstweekday=6).monthdatescalendar(year, month)
            events_by_day = {}
            for event in event_records:
                events_by_day.setdefault(event["date"], []).append(event)

            for row_index, week in enumerate(month_matrix, start=1):
                calendar_frame.grid_rowconfigure(row_index, weight=1, uniform="calendar-week")
                for column_index, day_date in enumerate(week):
                    day_key = day_date.strftime("%Y-%m-%d")
                    is_current_month = day_date.month == month
                    is_today = day_key == study_day_string()
                    totals = daily_totals.get(day_key, {"study": 0, "focus": 0})
                    events = events_by_day.get(day_key, [])
                    has_content = totals["study"] > 0 or totals["focus"] > 0 or bool(events)

                    cell = ctk.CTkFrame(
                        calendar_frame,
                        fg_color="#FFFFFF" if is_current_month else "#F8FAFC",
                        corner_radius=12,
                        border_width=2 if is_today else 1,
                        border_color=COLORS["primary_mint"] if is_today else COLORS["border"],
                    )
                    cell.grid(row=row_index, column=column_index, padx=7, pady=7, sticky="nsew")

                    day_color = COLORS["text_main"] if is_current_month else "#CBD5E1"
                    ctk.CTkLabel(
                        cell,
                        text=f"{day_date.day}" + (" · 오늘" if is_today else ""),
                        font=(FONT_FAMILY, 15, "bold"),
                        text_color=day_color,
                    ).pack(anchor="nw", padx=10, pady=(8, 2))

                    if totals["study"] > 0:
                        ctk.CTkLabel(
                            cell,
                            text=f"학습 {_format_hours_minutes(totals['study'])}",
                            font=(FONT_FAMILY, 12, "bold"),
                            text_color=COLORS["primary_blue"],
                        ).pack(anchor="w", padx=10)
                    if totals["focus"] > 0:
                        ctk.CTkLabel(
                            cell,
                            text=f"집중 {_format_hours_minutes(totals['focus'])}",
                            font=(FONT_FAMILY, 12, "bold"),
                            text_color=COLORS["primary_mint"],
                        ).pack(anchor="w", padx=10)

                    for event in events[:2]:
                        event_color = COLORS["danger"] if event["priority"] == "high" else COLORS["caution"]
                        event_label = event["title"] if event["type"] == "none" else f"{event['type']} · {event['title']}"
                        ctk.CTkButton(
                            cell,
                            text=event_label,
                            command=lambda event_id=event["id"]: select_event(event_id),
                            height=22,
                            corner_radius=8,
                            font=(FONT_FAMILY, 11),
                            fg_color="#FFFFFF",
                            hover_color="#F8FAFC",
                            text_color=event_color,
                            border_width=0,
                            anchor="w",
                        ).pack(fill="x", padx=8, pady=(2, 0))
                    if len(events) > 2:
                        ctk.CTkLabel(
                            cell,
                            text=f"+{len(events) - 2} more",
                            font=(FONT_FAMILY, 11, "bold"),
                            text_color=COLORS["text_sub"],
                        ).pack(anchor="w", padx=10, pady=(2, 0))

                    if not has_content:
                        ctk.CTkLabel(
                            cell,
                            text="",
                            font=(FONT_FAMILY, 11),
                            text_color=COLORS["text_sub"],
                        ).pack(anchor="w", padx=10)

        render_month()
        render_event_list()

    root = ctk.CTkFrame(app, fg_color=COLORS["background"])
    root.pack(fill="both", expand=True, padx=28, pady=24)

    header = ctk.CTkFrame(root, fg_color="transparent")
    header.pack(fill="x", pady=(0, 18))

    title_box = ctk.CTkFrame(header, fg_color="transparent")
    title_box.pack(side="left")

    ctk.CTkLabel(
        title_box,
        text="NeckCare Vision",
        font=FONT_TITLE,
        text_color=COLORS["text_main"],
    ).pack(anchor="w")
    ctk.CTkLabel(
        title_box,
        text="Real-time Forward Head Posture Analyzer",
        font=FONT_SUBTITLE,
        text_color=COLORS["text_sub"],
    ).pack(anchor="w", pady=(2, 0))

    calendar_button = ctk.CTkButton(
        header,
        text="캘린더",
        command=show_calendar_window,
        width=92,
        height=38,
        corner_radius=14,
        font=(FONT_FAMILY, 14, "bold"),
        fg_color="#FFFFFF",
        hover_color="#F8FAFC",
        text_color=COLORS["text_main"],
        border_width=1,
        border_color=COLORS["border"],
    )

    daily_report_button = ctk.CTkButton(
        header,
        text="Daily Report",
        command=show_daily_report_window,
        width=116,
        height=38,
        corner_radius=14,
        font=(FONT_FAMILY, 14, "bold"),
        fg_color="#EFF6FF",
        hover_color="#EFF6FF",
        text_color=COLORS["primary_blue"],
        border_width=1,
        border_color="#BFDBFE",
    )

    timer = ctk.CTkLabel(
        header,
        text="00:00:00",
        font=(FONT_FAMILY, 16, "bold"),
        text_color=COLORS["primary_blue"],
        fg_color="#EAF4FF",
        corner_radius=14,
        padx=18,
        pady=8,
    )
    timer.pack(side="right")

    today_timer = ctk.CTkLabel(
        header,
        text="Today 00:00",
        font=(FONT_FAMILY, 14, "bold"),
        text_color=COLORS["primary_mint"],
        fg_color="#E6FFFB",
        corner_radius=14,
        padx=16,
        pady=8,
    )
    today_timer.pack(side="right", padx=(0, 10))
    calendar_button.pack(side="right", padx=(0, 10))
    daily_report_button.pack(side="right", padx=(0, 10))

    content = ctk.CTkFrame(root, fg_color="transparent")
    content.pack(fill="both", expand=True)

    camera_card = _create_card(content, side="left", fill="both", expand=True, padx=(0, 18))

    camera_header = ctk.CTkFrame(camera_card, fg_color="transparent")
    camera_header.pack(fill="x", padx=22, pady=(18, 8))

    ctk.CTkLabel(
        camera_header,
        text="● Live Camera",
        font=FONT_SECTION,
        text_color=COLORS["normal"],
    ).pack(side="left")

    camera_view_enabled = ctk.BooleanVar(value=True)

    def update_camera_view_state():
        try:
            side_panel.winfo_exists()
        except NameError:
            return

        if not camera_view_enabled.get():
            video_label.configure(image="", text="Camera view hidden")
            camera_card.pack_forget()
            side_panel.pack_forget()
            side_panel.configure(width=560)
            side_panel.pack(fill="both", expand=True)
            app.geometry("760x840")
        else:
            side_panel.pack_forget()
            camera_card.pack(side="left", fill="both", expand=True, padx=(0, 18))
            side_panel.configure(width=520)
            side_panel.pack(side="right", fill="both")
            app.geometry("1280x840")

    camera_view_switch = ctk.CTkSwitch(
        header,
        text="Camera View",
        variable=camera_view_enabled,
        command=update_camera_view_state,
        progress_color=COLORS["primary_mint"],
        button_color=COLORS["primary_mint"],
        font=(FONT_FAMILY, 13, "bold"),
        text_color=COLORS["text_sub"],
    )
    camera_view_switch.pack(side="right", padx=(0, 10))

    camera_state = ctk.CTkLabel(
        camera_header,
        text="Waiting",
        font=FONT_BODY,
        text_color=COLORS["text_sub"],
    )
    camera_state.pack(side="right", padx=(0, 14))

    video_shell = ctk.CTkFrame(camera_card, fg_color="#F8FAFC", corner_radius=16)
    video_shell.pack(fill="both", expand=True, padx=18, pady=(0, 18))

    video_label = ctk.CTkLabel(
        video_shell,
        text="Waiting for camera...",
        font=(FONT_FAMILY, 16),
        text_color=COLORS["text_sub"],
    )
    video_label.pack(expand=True, fill="both", padx=12, pady=12)

    side_panel = ctk.CTkScrollableFrame(content, fg_color="transparent", width=520)
    side_panel.pack(side="right", fill="both")

    score_row = ctk.CTkFrame(side_panel, fg_color="transparent")
    score_row.pack(fill="x", pady=(0, 14))

    score_card = _create_card(score_row, side="left", fill="both", expand=True, padx=(0, 7))
    ctk.CTkLabel(score_card, text="Posture Score", font=FONT_SECTION, text_color=COLORS["text_sub"]).pack(
        anchor="w", padx=16, pady=(18, 0)
    )
    score_value = ctk.CTkLabel(score_card, text="--", font=FONT_VALUE, text_color=COLORS["text_main"])
    score_value.pack(anchor="w", padx=16, pady=(4, 4))
    status_badge = ctk.CTkLabel(
        score_card,
        text="Caution",
        font=(FONT_FAMILY, 14, "bold"),
        text_color=COLORS["caution"],
        fg_color="#FFF7ED",
        corner_radius=12,
        padx=12,
        pady=5,
    )
    status_badge.pack(anchor="w", padx=16, pady=(0, 18))

    focus_card = _create_card(score_row, side="left", fill="both", expand=True, padx=(7, 0))
    ctk.CTkLabel(focus_card, text="Focus Score", font=FONT_SECTION, text_color=COLORS["text_sub"]).pack(
        anchor="w", padx=16, pady=(18, 0)
    )
    focus_value = ctk.CTkLabel(focus_card, text="--", font=FONT_VALUE, text_color=COLORS["text_main"])
    focus_value.pack(anchor="w", padx=16, pady=(4, 18))

    study_card = _create_card(side_panel, fill="x", pady=(0, 14))
    ctk.CTkLabel(study_card, text="Study Session", font=FONT_SECTION, text_color=COLORS["text_sub"]).pack(
        anchor="w", padx=22, pady=(18, 0)
    )
    study_state = ctk.CTkLabel(
        study_card,
        text="Ready",
        font=(FONT_FAMILY, 24, "bold"),
        text_color=COLORS["text_main"],
    )
    study_state.pack(anchor="w", padx=22, pady=(4, 18))

    daily_row = ctk.CTkFrame(side_panel, fg_color="transparent")
    daily_row.pack(fill="x", pady=(0, 14))

    daily_card = _create_card(daily_row, side="left", fill="both", expand=True, padx=(0, 7))
    ctk.CTkLabel(daily_card, text="학습 시간", font=FONT_SECTION, text_color=COLORS["text_sub"]).pack(
        anchor="w", padx=16, pady=(18, 0)
    )
    daily_value = ctk.CTkLabel(
        daily_card,
        text="00:00",
        font=(FONT_FAMILY, 30, "bold"),
        text_color=COLORS["primary_blue"],
    )
    daily_value.pack(anchor="w", padx=16, pady=(4, 18))

    focus_time_card = _create_card(daily_row, side="left", fill="both", expand=True, padx=(7, 0))
    ctk.CTkLabel(focus_time_card, text="집중 시간", font=FONT_SECTION, text_color=COLORS["text_sub"]).pack(
        anchor="w", padx=16, pady=(18, 0)
    )
    focus_time_value = ctk.CTkLabel(
        focus_time_card,
        text="00:00",
        font=(FONT_FAMILY, 30, "bold"),
        text_color=COLORS["primary_mint"],
    )
    focus_time_value.pack(anchor="w", padx=16, pady=(4, 18))

    daily_score_card = _create_card(side_panel, fill="x", pady=(0, 14))
    ctk.CTkLabel(
        daily_score_card,
        text="Daily Study Score",
        font=FONT_SECTION,
        text_color=COLORS["text_sub"],
    ).pack(anchor="w", padx=22, pady=(18, 0))
    daily_score_value = ctk.CTkLabel(
        daily_score_card,
        text="--",
        font=(FONT_FAMILY, 38, "bold"),
        text_color=COLORS["text_main"],
    )
    daily_score_value.pack(anchor="w", padx=22, pady=(4, 4))
    daily_score_detail = ctk.CTkLabel(
        daily_score_card,
        text="Focus --  Time --  Vision --",
        font=(FONT_FAMILY, 12, "bold"),
        text_color=COLORS["text_sub"],
    )
    daily_score_detail.pack(anchor="w", padx=22, pady=(0, 18))

    feedback_card = _create_card(side_panel, fill="both", expand=True)
    ctk.CTkLabel(feedback_card, text="Feedback", font=FONT_SECTION, text_color=COLORS["text_sub"]).pack(
        anchor="w", padx=22, pady=(20, 8)
    )
    feedback_text = ctk.CTkLabel(
        feedback_card,
        text="카메라를 시작하면 자세 피드백이 표시됩니다.",
        font=(FONT_FAMILY, 15, "bold"),
        text_color=COLORS["text_main"],
        wraplength=290,
        justify="left",
    )
    feedback_text.pack(anchor="w", padx=22, pady=(0, 20))

    controls = ctk.CTkFrame(root, fg_color="transparent")
    controls.pack(fill="x", pady=(18, 0))

    start_button = _make_button(
        controls,
        "학습 시작",
        toggle_study,
        COLORS["primary_mint"],
        "#FFFFFF",
    )
    start_button.pack(side="left", padx=(0, 12))

    reset_button = _make_button(
        controls,
        "자세 리셋",
        lambda: send_command("RESET_CALIBRATION"),
        "#F8FAFC",
        COLORS["text_main"],
        COLORS["border"],
    )
    reset_button.pack(side="left", padx=(0, 12))

    latest_image = {"value": None}

    def update():
        try:
            if command_poller is not None:
                command_poller()

            data = None
            while not data_queue.empty():
                data = data_queue.get_nowait()

            if data == "QUIT":
                app.quit()
                return

            if data is not None:
                if "camera_state" in data and "stats" not in data:
                    camera_state.configure(text=data["camera_state"])
                    if "is_running" in data:
                        is_studying["value"] = bool(data["is_running"])
                        latest_stats["value"] = {
                            **latest_stats["value"],
                            "is_running": is_studying["value"],
                        }
                        daily_score_cache["updated_at"] = 0
                        start_button.configure(
                            text="학습 중지" if is_studying["value"] else "학습 시작",
                            fg_color=COLORS["danger"] if is_studying["value"] else COLORS["primary_mint"],
                            hover_color=COLORS["danger"] if is_studying["value"] else COLORS["primary_mint"],
                        )
                    app.after(33, update)
                    return

                frame = data.get("frame")
                stats = data.get("stats", {})
                latest_stats["value"] = stats

                if frame is not None:
                    if camera_view_enabled.get():
                        img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                        latest_image["value"] = ctk.CTkImage(light_image=img, dark_image=img, size=(800, 570))
                        video_label.configure(image=latest_image["value"], text="")
                    else:
                        video_label.configure(image="", text="Camera view hidden")
                    camera_state.configure(text="Analyzing")

                timer.configure(text=stats.get("time_str", "00:00:00"))
                today_seconds = stats.get("today_time", 0)
                current_study_day = stats.get("study_day", study_day_string())
                today_timer.configure(text=f"{current_study_day} · {_format_seconds(today_seconds)}")
                daily_value.configure(text=_format_seconds(today_seconds))
                focused_time = stats.get("focused_time", 0)
                focus_time_value.configure(text=_format_seconds(focused_time))
                daily_report = current_daily_score()
                daily_score_color = COLORS["normal"] if daily_report["daily_score"] >= 75 else COLORS["caution"]
                if daily_report["daily_score"] < 50:
                    daily_score_color = COLORS["danger"]
                daily_score_value.configure(
                    text=f"{daily_report['daily_score']:.1f}",
                    text_color=daily_score_color,
                )
                daily_score_detail.configure(
                    text=(
                        f"Focus {daily_report['focus_part']:.1f}"
                        f"  Time {daily_report['time_part']:.1f}"
                        f"  Vision {daily_report['quality_part']:.1f}"
                    )
                )
                is_studying["value"] = bool(stats.get("is_running", True))
                start_button.configure(
                    text="학습 중지" if is_studying["value"] else "학습 시작",
                    fg_color=COLORS["danger"] if is_studying["value"] else COLORS["primary_mint"],
                    hover_color=COLORS["danger"] if is_studying["value"] else COLORS["primary_mint"],
                )

                posture_score = int(stats.get("posture_score", stats.get("avg_p", 0)))
                posture_status = stats.get("posture_status", "Warning")
                risk_label, risk_color = _risk_from_status(posture_status)
                current_focus_score = int(stats.get("focus_score", stats.get("avg_f", 0)))
                current_focus_status = stats.get("focus_status", "Away")
                focus_text_color = _focus_color(current_focus_status)
                current_study_state = stats.get("study_state", "Analyzing")
                state_color = {
                    "Focused": COLORS["normal"],
                    "Reading": COLORS["primary_blue"],
                    "Bad Posture": COLORS["caution"],
                    "Distracted": COLORS["caution"],
                    "Looking Away": COLORS["danger"],
                    "No Face": COLORS["danger"],
                    "Drowsy": COLORS["danger"],
                }.get(current_study_state, COLORS["text_main"])

                score_value.configure(text=str(posture_score), text_color=risk_color)
                focus_value.configure(text=str(current_focus_score), text_color=focus_text_color)
                study_state.configure(text=current_study_state, text_color=state_color)
                status_badge.configure(
                    text=risk_label,
                    text_color=risk_color,
                    fg_color={
                        "Normal": "#ECFDF5",
                        "Caution": "#FFF7ED",
                        "Danger": "#FEF2F2",
                    }.get(risk_label, "#FFF7ED"),
                )
                feedback_text.configure(text=stats.get("feedback", _feedback_for_status(posture_status)))

        except Exception as exc:
            print("Dashboard update loop error:", exc)

        app.after(33, update)

    def on_close():
        send_command("DASHBOARD_CLOSED")
        if on_close_callback is not None:
            on_close_callback()
        app.destroy()

    app.protocol("WM_DELETE_WINDOW", on_close)
    app.after(33, update)
    app.mainloop()


def run_dashboard_app(stop_worker_on_close=True):
    """Run the dashboard as the main application window."""
    import queue

    from src.camera_worker import CameraWorker

    data_queue = queue.Queue()
    command_queue = queue.Queue()
    worker = CameraWorker()
    worker.show_dashboard = True
    worker.dashboard_queue = data_queue
    worker.dashboard_command_queue = command_queue

    def poll_commands():
        worker.handle_dashboard_commands()

    def shutdown_worker():
        worker.stop()
        worker.set_debug(False)
        detach_dashboard()

    def detach_dashboard():
        worker.show_dashboard = False
        worker.dashboard_queue = None
        worker.dashboard_command_queue = None

    close_callback = shutdown_worker if stop_worker_on_close else detach_dashboard

    try:
        run_dashboard(
            data_queue,
            command_queue,
            command_poller=poll_commands,
            on_close_callback=close_callback,
        )
    finally:
        close_callback()

    return worker
