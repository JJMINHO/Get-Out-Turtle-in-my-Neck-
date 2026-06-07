"""
macOS menu bar widget with minimal controls.
"""
import os
import threading

import rumps

from src.camera_worker import CameraWorker


class DeskPoseApp(rumps.App):
    def __init__(self, worker=None):
        super(DeskPoseApp, self).__init__("DeskFlow", quit_button=None)
        self.title = "DeskFlow (Off)"
        self.worker = worker or CameraWorker(ui_callback=self.update_scores)
        self.worker.ui_callback = self.update_scores
        self.is_monitoring = self.worker.is_running
        self.latest_scores = None
        self.score_lock = threading.Lock()
        self.start_item = rumps.MenuItem("Start", callback=self.start_monitoring)
        self.stop_item = rumps.MenuItem("Stop", callback=self.stop_monitoring)

        self.menu = [
            rumps.MenuItem("Show Dashboard", callback=self.show_dashboard),
            self.start_item,
            self.stop_item,
            None,
            rumps.MenuItem("Quit", callback=self.quit),
        ]
        self._sync_start_stop_menu()

        # rumps UI updates are safest from the app event loop.
        self.refresh_timer = rumps.Timer(self.refresh_title, 1)
        self.refresh_timer.start()

    def show_dashboard(self, sender):
        self.worker.set_dashboard(True)

    def start_monitoring(self, sender):
        if not self.is_monitoring:
            self.is_monitoring = True
            self.title = "Starting..."
            self._sync_start_stop_menu()
            self.worker.start()

    def stop_monitoring(self, sender):
        if self.is_monitoring:
            self.is_monitoring = False
            self.title = "DeskFlow (Off)"
            self._sync_start_stop_menu()
            self.worker.stop()

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

        if not self.is_monitoring and self.worker.is_running:
            self.is_monitoring = True
            self._sync_start_stop_menu()

        if self.is_monitoring and not self.worker.is_running:
            self.is_monitoring = False
            self.title = "DeskFlow (Off)"
            self._sync_start_stop_menu()

        if not self.is_monitoring:
            return

        with self.score_lock:
            scores = self.latest_scores

        if not scores:
            return

        p_score, p_status, f_score, f_status = scores
        if p_status == "Bad" or f_status == "Away":
            emoji = "🔴"
        elif p_status == "Warning" or f_status == "Distracted":
            emoji = "🟡"
        else:
            emoji = "🟢"

        self.title = f"{emoji} P: {p_score} │ F: {f_score}"

    def _sync_start_stop_menu(self):
        """Show only the action that is valid for the current running state."""
        self.start_item.hidden = self.is_monitoring
        self.stop_item.hidden = not self.is_monitoring

    def quit(self, sender):
        try:
            self.refresh_timer.stop()
        except Exception:
            pass

        if self.worker:
            self.worker.shutdown()

        threading.Timer(0.75, lambda: os._exit(0)).start()
        rumps.quit_application()
