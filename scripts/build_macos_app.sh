#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

BUILD_PYTHON="${DESKFLOW_BUILD_PYTHON:-/usr/bin/python3}"
BUILD_VENV="${DESKFLOW_BUILD_VENV:-.venv-build}"

if [ ! -d "$BUILD_VENV" ]; then
  "$BUILD_PYTHON" -m venv "$BUILD_VENV"
fi

source "$BUILD_VENV/bin/activate"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt

python - <<'PY'
import sys
print(f"Build Python: {sys.executable}")
print(f"Python version: {sys.version}")
PY

pyinstaller --clean --noconfirm DeskFlowCoach.spec

APP_PATH="dist/DeskFlow Coach.app"
ONEDIR_PATH="dist/DeskFlow Coach"
WRAPPED_ONEDIR_NAME="DeskFlow Coach"

rm -rf "$APP_PATH"
mkdir -p "$APP_PATH/Contents/MacOS" "$APP_PATH/Contents/Resources"
cp -R "$ONEDIR_PATH" "$APP_PATH/Contents/Resources/$WRAPPED_ONEDIR_NAME"

cat > "$APP_PATH/Contents/MacOS/DeskFlow Coach" <<'LAUNCHER'
#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec "$APP_ROOT/Resources/DeskFlow Coach/DeskFlow Coach"
LAUNCHER
chmod +x "$APP_PATH/Contents/MacOS/DeskFlow Coach"

cat > "$APP_PATH/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleDevelopmentRegion</key>
  <string>en</string>
  <key>CFBundleDisplayName</key>
  <string>DeskFlow Coach</string>
  <key>CFBundleExecutable</key>
  <string>DeskFlow Coach</string>
  <key>CFBundleIdentifier</key>
  <string>com.deskflow.coach</string>
  <key>CFBundleInfoDictionaryVersion</key>
  <string>6.0</string>
  <key>CFBundleName</key>
  <string>DeskFlow Coach</string>
  <key>CFBundlePackageType</key>
  <string>APPL</string>
  <key>CFBundleShortVersionString</key>
  <string>0.1.0</string>
  <key>CFBundleVersion</key>
  <string>0.1.0</string>
  <key>LSMinimumSystemVersion</key>
  <string>11.0</string>
  <key>NSCameraUsageDescription</key>
  <string>DeskFlow Coach uses the camera to estimate posture and screen-focus signals.</string>
</dict>
</plist>
PLIST

if command -v codesign >/dev/null 2>&1; then
  codesign --force --deep --sign - "$APP_PATH" >/dev/null 2>&1 || true
fi

echo
echo "Built: dist/DeskFlow Coach.app"
echo "Data directory: ~/Library/Application Support/DeskFlow Coach"
echo "Optional API key file: ~/Library/Application Support/DeskFlow Coach/.env"
