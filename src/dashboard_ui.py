"""
Healthcare-style dashboard UI for the live posture analysis view.
"""
import customtkinter as ctk
from PIL import Image
import cv2


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
FONT_VALUE = (FONT_FAMILY, 44, "bold")
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


def run_dashboard(data_queue, command_queue=None):
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")

    app = ctk.CTk()
    app.geometry("1280x760")
    app.minsize(1200, 720)
    app.title("NeckCare Vision")
    app.configure(fg_color=COLORS["background"])

    def send_command(command):
        if command_queue is not None:
            command_queue.put(command)

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
    camera_state = ctk.CTkLabel(
        camera_header,
        text="Waiting",
        font=FONT_BODY,
        text_color=COLORS["text_sub"],
    )
    camera_state.pack(side="right")

    video_shell = ctk.CTkFrame(camera_card, fg_color="#F8FAFC", corner_radius=16)
    video_shell.pack(fill="both", expand=True, padx=18, pady=(0, 18))

    video_label = ctk.CTkLabel(
        video_shell,
        text="Waiting for camera...",
        font=(FONT_FAMILY, 16),
        text_color=COLORS["text_sub"],
    )
    video_label.pack(expand=True, fill="both", padx=12, pady=12)

    side_panel = ctk.CTkFrame(content, fg_color="transparent", width=360)
    side_panel.pack(side="right", fill="y")
    side_panel.pack_propagate(False)

    score_card = _create_card(side_panel, fill="x", pady=(0, 14))
    ctk.CTkLabel(score_card, text="Posture Score", font=FONT_SECTION, text_color=COLORS["text_sub"]).pack(
        anchor="w", padx=22, pady=(20, 0)
    )
    score_value = ctk.CTkLabel(score_card, text="-- / 100", font=FONT_VALUE, text_color=COLORS["text_main"])
    score_value.pack(anchor="w", padx=22, pady=(4, 4))
    status_badge = ctk.CTkLabel(
        score_card,
        text="● Caution",
        font=(FONT_FAMILY, 14, "bold"),
        text_color=COLORS["caution"],
        fg_color="#FFF7ED",
        corner_radius=12,
        padx=12,
        pady=5,
    )
    status_badge.pack(anchor="w", padx=22, pady=(0, 20))

    focus_card = _create_card(side_panel, fill="x", pady=(0, 14))
    ctk.CTkLabel(focus_card, text="Focus Score", font=FONT_SECTION, text_color=COLORS["text_sub"]).pack(
        anchor="w", padx=22, pady=(18, 0)
    )
    focus_value = ctk.CTkLabel(focus_card, text="-- / 100", font=FONT_VALUE, text_color=COLORS["text_main"])
    focus_value.pack(anchor="w", padx=22, pady=(4, 4))
    focus_status = ctk.CTkLabel(
        focus_card,
        text="화면 집중 상태를 분석 중입니다.",
        font=FONT_BODY,
        text_color=COLORS["text_sub"],
    )
    focus_status.pack(anchor="w", padx=22)
    focus_detail = ctk.CTkLabel(
        focus_card,
        text="Gaze: --   Focused: 00:00",
        font=(FONT_FAMILY, 13),
        text_color=COLORS["text_sub"],
    )
    focus_detail.pack(anchor="w", padx=22, pady=(4, 20))

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
    study_state.pack(anchor="w", padx=22, pady=(4, 2))
    study_detail = ctk.CTkLabel(
        study_card,
        text="Good 00:00   Away 00:00",
        font=(FONT_FAMILY, 13),
        text_color=COLORS["text_sub"],
    )
    study_detail.pack(anchor="w", padx=22, pady=(0, 4))
    study_detail_2 = ctk.CTkLabel(
        study_card,
        text="Bad 00:00   No Face 00:00",
        font=(FONT_FAMILY, 13),
        text_color=COLORS["text_sub"],
    )
    study_detail_2.pack(anchor="w", padx=22, pady=(0, 18))

    feedback_card = _create_card(side_panel, fill="both", expand=True)
    ctk.CTkLabel(feedback_card, text="Feedback", font=FONT_SECTION, text_color=COLORS["text_sub"]).pack(
        anchor="w", padx=22, pady=(20, 8)
    )
    feedback_text = ctk.CTkLabel(
        feedback_card,
        text="카메라를 시작하면 자세 피드백이 표시됩니다.",
        font=(FONT_FAMILY, 17, "bold"),
        text_color=COLORS["text_main"],
        wraplength=290,
        justify="left",
    )
    feedback_text.pack(anchor="w", padx=22, pady=(0, 20))

    controls = ctk.CTkFrame(root, fg_color="transparent")
    controls.pack(fill="x", pady=(18, 0))

    start_button = _make_button(
        controls,
        "Start Analysis",
        lambda: send_command("START_ANALYSIS"),
        COLORS["primary_mint"],
        "#FFFFFF",
    )
    start_button.pack(side="left", padx=(0, 12))

    stop_button = _make_button(
        controls,
        "Stop Camera",
        lambda: send_command("STOP_CAMERA"),
        "#FFFFFF",
        COLORS["text_main"],
        COLORS["border"],
    )
    stop_button.pack(side="left", padx=(0, 12))

    save_button = _make_button(
        controls,
        "Save Report",
        lambda: send_command("SAVE_REPORT"),
        "#EFF6FF",
        COLORS["primary_blue"],
        "#BFDBFE",
    )
    save_button.pack(side="left")

    latest_image = {"value": None}

    def update():
        try:
            data = None
            while not data_queue.empty():
                data = data_queue.get_nowait()

            if data == "QUIT":
                app.quit()
                return

            if data is not None:
                if "camera_state" in data and "stats" not in data:
                    camera_state.configure(text=data["camera_state"])
                    app.after(33, update)
                    return

                frame = data.get("frame")
                stats = data.get("stats", {})

                if frame is not None:
                    img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                    latest_image["value"] = ctk.CTkImage(light_image=img, dark_image=img, size=(800, 570))
                    video_label.configure(image=latest_image["value"], text="")
                    camera_state.configure(text="Analyzing")

                timer.configure(text=stats.get("time_str", "00:00:00"))
                today_timer.configure(text=f"Today {_format_seconds(stats.get('today_time', 0))}")

                posture_score = int(stats.get("posture_score", stats.get("avg_p", 0)))
                posture_status = stats.get("posture_status", "Warning")
                risk_label, risk_color = _risk_from_status(posture_status)
                current_focus_score = int(stats.get("focus_score", stats.get("avg_f", 0)))
                current_focus_status = stats.get("focus_status", "Away")
                current_gaze_zone = stats.get("gaze_zone", "--")
                focused_time = stats.get("focused_time", 0)
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

                score_value.configure(text=f"{posture_score} / 100", text_color=risk_color)
                focus_value.configure(text=f"{current_focus_score} / 100", text_color=focus_text_color)
                focus_status.configure(
                    text={
                        "Focused": "화면을 안정적으로 보고 있습니다.",
                        "Distracted": "시선이 잠시 흐트러졌습니다.",
                        "Away": "화면 밖을 보고 있거나 얼굴이 감지되지 않습니다.",
                    }.get(current_focus_status, f"현재 상태: {current_focus_status}"),
                    text_color=focus_text_color,
                )
                focus_detail.configure(text=f"Gaze: {current_gaze_zone}   Focused: {_format_seconds(focused_time)}")
                study_state.configure(text=current_study_state, text_color=state_color)
                study_detail.configure(
                    text=(
                        f"Good {_format_seconds(stats.get('good_posture_time', 0))}"
                        f"   Away {_format_seconds(stats.get('away_time', 0))}"
                    )
                )
                study_detail_2.configure(
                    text=(
                        f"Bad {_format_seconds(stats.get('bad_posture_time', 0))}"
                        f"   No Face {_format_seconds(stats.get('no_face_time', 0))}"
                    )
                )
                status_badge.configure(
                    text=f"● {risk_label}",
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
        app.destroy()

    app.protocol("WM_DELETE_WINDOW", on_close)
    app.after(33, update)
    app.mainloop()
