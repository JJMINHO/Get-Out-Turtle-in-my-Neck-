import customtkinter as ctk
from PIL import Image
import cv2

def run_dashboard(q):
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    FONT_TITLE = ("Helvetica", 28, "bold")
    FONT_SUBTITLE = ("Helvetica", 14)
    FONT_LABEL = ("Helvetica", 14, "bold")
    FONT_VALUE = ("Helvetica", 48, "bold")

    app = ctk.CTk()
    app.geometry("1440x820")
    app.title("DeskPose Coach")

    root = ctk.CTkFrame(app, fg_color="#0B1220")
    root.pack(fill="both", expand=True)

    header = ctk.CTkFrame(root, fg_color="transparent")
    header.pack(fill="x", padx=28, pady=(24, 12))

    title_box = ctk.CTkFrame(header, fg_color="transparent")
    title_box.pack(side="left")

    title = ctk.CTkLabel(title_box, text="DeskPose Coach", font=FONT_TITLE, text_color="#F9FAFB")
    title.pack(anchor="w")

    subtitle = ctk.CTkLabel(title_box, text="Forward Head Posture Monitor", font=FONT_SUBTITLE, text_color="#9CA3AF")
    subtitle.pack(anchor="w")

    timer = ctk.CTkLabel(
        header, text="00:00:00", font=("Helvetica", 18, "bold"), text_color="#E5E7EB", fg_color="#1F2937",
        corner_radius=12, padx=18, pady=8
    )
    timer.pack(side="right")

    content = ctk.CTkFrame(root, fg_color="transparent")
    content.pack(fill="both", expand=True, padx=28, pady=16)

    camera_card = ctk.CTkFrame(content, fg_color="#111827", corner_radius=22)
    camera_card.pack(side="left", fill="both", expand=True, padx=(0, 20))
    
    camera_header = ctk.CTkFrame(camera_card, fg_color="transparent")
    camera_header.pack(fill="x", padx=24, pady=(24, 0))
    
    ctk.CTkLabel(camera_header, text="Live Camera", font=FONT_LABEL, text_color="#E5E7EB").pack(side="left")
    
    show_camera_var = ctk.BooleanVar(value=True)
    def toggle_camera():
        if not show_camera_var.get():
            video_label.configure(image="", text="Camera Feed Hidden")
            
    switch = ctk.CTkSwitch(camera_header, text="Show", variable=show_camera_var, command=toggle_camera, 
                           progress_color="#38BDF8", font=FONT_SUBTITLE)
    switch.pack(side="right")
    
    video_label = ctk.CTkLabel(camera_card, text="Waiting for camera...", font=FONT_SUBTITLE, text_color="#9CA3AF")
    video_label.pack(expand=True, fill="both", padx=16, pady=16)

    side_panel = ctk.CTkFrame(content, fg_color="#111827", corner_radius=22, width=400)
    side_panel.pack(side="right", fill="y")
    
    def create_score_card(parent, title_text):
        card = ctk.CTkFrame(parent, fg_color="#1F2937", corner_radius=16)
        card.pack(fill="x", padx=24, pady=(24, 0))
        
        lbl_title = ctk.CTkLabel(card, text=title_text, font=FONT_LABEL, text_color="#9CA3AF")
        lbl_title.pack(anchor="w", padx=20, pady=(20, 0))
        
        lbl_val = ctk.CTkLabel(card, text="0", font=FONT_VALUE, text_color="#F9FAFB")
        lbl_val.pack(anchor="w", padx=20, pady=(0, 20))
        return lbl_val, card
        
    posture_val_lbl, posture_card = create_score_card(side_panel, "Avg Posture Score")
    focus_val_lbl, focus_card = create_score_card(side_panel, "Avg Focus Score")
    
    stats_card = ctk.CTkFrame(side_panel, fg_color="#1F2937", corner_radius=16)
    stats_card.pack(fill="both", expand=True, padx=24, pady=24)
    
    ctk.CTkLabel(stats_card, text="Session Statistics", font=FONT_LABEL, text_color="#9CA3AF").pack(anchor="w", padx=20, pady=(20, 10))
    
    def create_stat_row(parent, label_text):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=8)
        ctk.CTkLabel(row, text=label_text, font=FONT_SUBTITLE, text_color="#E5E7EB").pack(side="left")
        val_lbl = ctk.CTkLabel(row, text="0s", font=FONT_SUBTITLE, text_color="#38BDF8")
        val_lbl.pack(side="right")
        return val_lbl
        
    lbl_focus_time = create_stat_row(stats_card, "Focused Time")
    lbl_good_time = create_stat_row(stats_card, "Good Posture Time")
    lbl_bad_time = create_stat_row(stats_card, "Bad Posture Time")

    def update():
        try:
            data = None
            while not q.empty():
                data = q.get_nowait()
            
            if data == "QUIT":
                app.quit()
                return
                
            if data is not None:
                frame = data.get("frame")
                stats = data.get("stats")
                
                if frame is not None:
                    if show_camera_var.get():
                        img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                        ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(960, 720))
                        video_label.configure(image=ctk_img, text="")
                    
                if stats is not None:
                    timer.configure(text=stats.get("time_str", "00:00:00"))
                    
                    avg_p = stats.get("avg_p", 0)
                    avg_f = stats.get("avg_f", 0)
                    
                    posture_val_lbl.configure(text=str(avg_p))
                    focus_val_lbl.configure(text=str(avg_f))
                    
                    lbl_focus_time.configure(text=f"{int(stats.get('focused_time', 0))}s")
                    lbl_good_time.configure(text=f"{int(stats.get('good_posture_time', 0))}s")
                    lbl_bad_time.configure(text=f"{int(stats.get('bad_posture_time', 0))}s")
                    
                    # Colors
                    def score_color(val, thresh):
                        if val >= thresh: return "#22C55E" # Success
                        if val >= thresh - 20: return "#F59E0B" # Warning
                        return "#EF4444" # Danger
                        
                    posture_val_lbl.configure(text_color=score_color(avg_p, 80)) # GOOD_THRESHOLD from config, hardcoded here is fine or we can pass it
                    focus_val_lbl.configure(text_color=score_color(avg_f, 75))   # FOCUSED_THRESHOLD
                    
        except Exception as e:
            print("Dashboard update loop error:", e)
        
        app.after(33, update)

    app.after(33, update)
    app.mainloop()
