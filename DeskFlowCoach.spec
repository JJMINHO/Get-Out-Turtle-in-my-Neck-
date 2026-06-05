# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_data_files, collect_submodules


block_cipher = None

datas = [
    ("assets/pose_landmarker_lite.task", "assets"),
    ("assets/face_landmarker.task", "assets"),
]
if os.path.exists(".env"):
    datas.append((".env", "."))
datas += collect_data_files("customtkinter")

hiddenimports = []
hiddenimports += collect_submodules("mediapipe")


import os
import mediapipe
mediapipe_path = os.path.dirname(mediapipe.__file__)
libmediapipe_path = os.path.join(mediapipe_path, "tasks", "c", "libmediapipe.dylib")
binaries_list = []
if os.path.exists(libmediapipe_path):
    binaries_list.append((libmediapipe_path, "mediapipe/tasks/c"))

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=binaries_list,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="DeskFlow Coach",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="DeskFlow Coach",
)
app = BUNDLE(
    coll,
    name="DeskFlow Coach.app",
    icon="assets/app_icon.icns",
    bundle_identifier="com.deskflow.coach",
    info_plist={
        "CFBundleName": "DeskFlow Coach",
        "CFBundleDisplayName": "DeskFlow Coach",
        "CFBundleShortVersionString": "0.1.0",
        "CFBundleVersion": "0.1.0",
        "NSCameraUsageDescription": "DeskFlow Coach uses the camera to estimate posture and screen-focus signals.",
    },
)
