"""
macOS menu bar UI implementation using rumps.
"""
import os
import subprocess
import threading

import rumps

from src.camera_worker import CameraWorker
from src.session_summary import SessionSummary


class DeskPoseApp(rumps.App):
    def __init__(self):
        super(DeskPoseApp, self).__init__("DeskPose")
        self.title = "DeskPose (Off)"
        self.worker = CameraWorker(ui_callback=self.update_scores)
        self.session_summary = SessionSummary()
        self.is_monitoring = False
        self.latest_scores = None
        self.score_lock = threading.Lock()

        self.status_item = rumps.MenuItem("Status: Waiting...")
        self.start_stop_button = rumps.MenuItem("Start Monitoring", callback=self.toggle_monitoring)
        self.dashboard_button = rumps.MenuItem("Show Dashboard", callback=self.toggle_dashboard)
        self.debug_button = rumps.MenuItem("Show Debug Window", callback=self.toggle_debug)
        self.summary_button = rumps.MenuItem("Show Session Summary", callback=self.show_session_summary)
        self.open_outputs_button = rumps.MenuItem("Open Outputs Folder", callback=self.open_outputs_folder)
        self.reset_calibration_button = rumps.MenuItem("Reset Posture Calibration", callback=self.reset_calibration)

        self.menu = [
            self.start_stop_button,
            None,
            self.status_item,
            None,
            self.dashboard_button,
            self.debug_button,
            self.summary_button,
            self.open_outputs_button,
            None,
            self.reset_calibration_button,
        ]

        # rumps UI updates are safest from the app event loop.
        self.refresh_timer = rumps.Timer(self.refresh_title, 1)
        self.refresh_timer.start()
        self.debug_timer = rumps.Timer(self.refresh_debug_window, 0.1)
        self.debug_timer.start()

    def toggle_monitoring(self, sender):
        if not self.is_monitoring:
            self.is_monitoring = True
            self.start_stop_button.title = "Stop Monitoring"
            self.title = "Starting..."
            self.worker.start()
        else:
            self.is_monitoring = False
            self.start_stop_button.title = "Start Monitoring"
            self.title = "DeskPose (Off)"
            self.worker.stop()

    def toggle_debug(self, sender):
        if self.worker.show_debug:
            self.worker.set_debug(False)
            self.debug_button.title = "Show Debug Window"
        else:
            self.worker.set_debug(True)
            self.debug_button.title = "Hide Debug Window"

    def toggle_dashboard(self, sender):
        if self.worker.show_dashboard:
            self.worker.set_dashboard(False)
            self.dashboard_button.title = "Show Dashboard"
        else:
            self.worker.set_dashboard(True)
            self.dashboard_button.title = "Hide Dashboard"

    def reset_calibration(self, sender):
        self.worker.reset_calibration()
        self.title = "Recalibrating..."

    def open_outputs_folder(self, sender):
        outputs_path = os.path.abspath("outputs")
        os.makedirs(outputs_path, exist_ok=True)
        subprocess.Popen(["open", outputs_path])

    def show_session_summary(self, sender):
        rumps.alert(
            title="DeskPose Session Summary",
            message=self.session_summary.build_summary(),
            ok="OK",
        )

    def update_scores(self, p_score, p_status, f_score, f_status):
        """Store scores received from the background camera worker."""
        with self.score_lock:
            self.latest_scores = (p_score, p_status, f_score, f_status)

    def refresh_title(self, _sender):
        """Refresh the menu bar title from the app event loop."""
        self.worker.handle_dashboard_commands()

        if self.worker.show_dashboard and (
            self.worker.dashboard_process is None or not self.worker.dashboard_process.is_alive()
        ):
            self.worker.show_dashboard = False
            self.worker.dashboard_process = None
            self.worker.dashboard_queue = None
            self.worker.dashboard_command_queue = None

        self.debug_button.title = "Hide Debug Window" if self.worker.show_debug else "Show Debug Window"
        self.dashboard_button.title = "Hide Dashboard" if self.worker.show_dashboard else "Show Dashboard"

        if not self.is_monitoring and self.worker.is_running:
            self.is_monitoring = True
            self.start_stop_button.title = "Stop Monitoring"

        if self.is_monitoring and not self.worker.is_running:
            self.is_monitoring = False
            self.start_stop_button.title = "Start Monitoring"
            self.title = "DeskPose (Off)"

        if not self.is_monitoring:
            self.status_item.title = "Status: Idle"
            return

        with self.score_lock:
            scores = self.latest_scores

        if not scores:
            self.status_item.title = "Status: Analyzing..."
            return

        p_score, p_status, f_score, f_status = scores
        if p_status == "Bad" or f_status == "Away":
            emoji = "🔴"
        elif p_status == "Warning" or f_status == "Distracted":
            emoji = "🟡"
        else:
            emoji = "🟢"

        self.title = f"{emoji} P: {p_score} │ F: {f_score}"
        self.status_item.title = f"Posture: {p_status}  |  Focus: {f_status}"

    def refresh_debug_window(self, _sender):
        """Display the latest debug frame from the app event loop."""
        if self.is_monitoring and self.worker.show_debug:
            self.worker.show_latest_debug_frame()
        else:
            self.worker.close_debug_window()



    def quit(self, sender):
        self.refresh_timer.stop()
        self.debug_timer.stop()
        if self.worker:
            self.worker.stop()
            self.worker.set_dashboard(False)
            self.worker.close_debug_window()
        super().quit(sender)
