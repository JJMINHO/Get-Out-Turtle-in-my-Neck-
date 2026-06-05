"""
Load local environment variables for deployment-safe app configuration.
"""
import os
import sys


def _candidate_env_paths(path):
    if os.path.isabs(path):
        return [path]

    paths = [
        os.path.abspath(path),
        os.path.join(os.getcwd(), path),
    ]
    if getattr(sys, "frozen", False):
        if hasattr(sys, "_MEIPASS"):
            paths.append(os.path.join(sys._MEIPASS, path))
        paths.extend([
            os.path.join(os.path.dirname(sys.executable), path),
            os.path.join(os.path.expanduser("~/Library/Application Support"), "DeskFlow Coach", path),
        ])

    seen = set()
    unique_paths = []
    for candidate in paths:
        if candidate in seen:
            continue
        seen.add(candidate)
        unique_paths.append(candidate)
    return unique_paths


def load_dotenv(path=".env"):
    """Load KEY=VALUE pairs from .env without overriding existing env vars."""
    env_path = None
    for candidate in _candidate_env_paths(path):
        if os.path.exists(candidate):
            env_path = candidate
            break

    if env_path is None:
        return

    with open(env_path, "r", encoding="utf-8") as env_file:
        for raw_line in env_file:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
