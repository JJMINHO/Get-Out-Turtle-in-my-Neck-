"""
Application entry point for DeskFlow Coach.
"""
import sys

from src.dashboard_ui import run_dashboard_app
from src.env_loader import load_dotenv


def main():
    """Start the dashboard first, then fall back to the menu bar widget."""
    try:
        load_dotenv()
        worker = run_dashboard_app(stop_worker_on_close=False)
        from src.menubar_app import DeskPoseApp

        DeskPoseApp(worker=worker).run()
    except Exception as exc:
        print(f"Error starting application: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
