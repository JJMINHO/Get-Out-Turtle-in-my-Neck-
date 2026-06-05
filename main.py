"""
Application entry point for DeskFlow Coach.
"""
import faulthandler
import multiprocessing
import os
import sys
import tempfile
import traceback


APP_NAME = "DeskFlow Coach"


def _data_dir():
    candidates = []
    if getattr(sys, "frozen", False):
        candidates.append(os.path.join(os.path.expanduser("~/Library/Application Support"), APP_NAME))
    else:
        candidates.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs"))
    candidates.append(os.path.join(tempfile.gettempdir(), APP_NAME))

    for path in candidates:
        try:
            os.makedirs(path, exist_ok=True)
            test_path = os.path.join(path, ".write_test")
            with open(test_path, "w", encoding="utf-8") as test_file:
                test_file.write("ok")
            os.remove(test_path)
            return path
        except OSError:
            continue
    return tempfile.gettempdir()


def _setup_runtime_logging():
    log_path = os.path.join(_data_dir(), "app.log")
    log_file = open(log_path, "a", encoding="utf-8")
    sys.stdout = log_file
    sys.stderr = log_file
    try:
        sys.stdout.reconfigure(line_buffering=True)
        sys.stderr.reconfigure(line_buffering=True)
    except Exception:
        pass
    faulthandler.enable(log_file)
    print("\n=== DeskFlow Coach starting ===", flush=True)
    print(f"frozen={getattr(sys, 'frozen', False)} executable={sys.executable}", flush=True)
    print(f"cwd={os.getcwd()}", flush=True)
    return log_file


def main():
    """Start the dashboard first, then fall back to the menu bar widget."""
    log_file = _setup_runtime_logging()
    try:
        from src.env_loader import load_dotenv
        load_dotenv()

        from src.config import POSE_MODEL_PATH, FACE_MODEL_PATH
        print(f"POSE_MODEL_PATH: {POSE_MODEL_PATH} (Exists: {os.path.exists(POSE_MODEL_PATH)})", flush=True)
        print(f"FACE_MODEL_PATH: {FACE_MODEL_PATH} (Exists: {os.path.exists(FACE_MODEL_PATH)})", flush=True)

        from src.dashboard_ui import run_dashboard_app
        worker = run_dashboard_app(stop_worker_on_close=False)
        from src.menubar_app import DeskPoseApp

        DeskPoseApp(worker=worker).run()
    except Exception as exc:
        print(f"Error starting application: {exc}", file=sys.stderr, flush=True)
        traceback.print_exc()
        sys.exit(1)
    finally:
        try:
            log_file.flush()
        except Exception:
            pass


if __name__ == "__main__":
    if sys.platform == 'darwin' and len(sys.argv) > 1 and sys.argv[1].startswith('--multiprocessing-fork'):
        from multiprocessing.spawn import freeze_support
        freeze_support()
        sys.exit(0)

    multiprocessing.freeze_support()
    main()
