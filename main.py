"""
Application entry point for DeskPose Coach.
"""
import sys

from src.menubar_app import DeskPoseApp


def main():
    """Start the macOS menu bar application."""
    try:
        DeskPoseApp().run()
    except Exception as exc:
        print(f"Error starting application: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()