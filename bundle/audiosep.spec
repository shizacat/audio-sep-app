# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the desktop app.

On macOS the bundle is dist/AudioSep.app. The delivered file is
dist/AudioSep-macos-arm64.dmg or dist/AudioSep-macos-x86_64.dmg.
On Windows the delivered file is dist/AudioSep-windows.zip.
On Linux the delivered file is dist/AudioSep-linux.zip.
"""

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

root = Path(SPECPATH).resolve().parent
version = "0.1.0"
for line in (root / "src" / "audiosep_app" / "__init__.py").read_text(encoding="utf-8").splitlines():
    if line.startswith("__version__"):
        version = line.split("=", 1)[1].strip().strip('"').strip("'")
        break

a = Analysis(
    [str(root / "bundle" / "entry.py")],
    pathex=[str(root / "src")],
    binaries=collect_dynamic_libs("onnxruntime"),
    datas=collect_data_files("audiosep_app"),
    hiddenimports=[
        "lameenc",
        "miniaudio",
        "onnxruntime",
        "soundfile",
        "tokenizers",
    ],
    excludes=["pytest", "ruff"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="AudioSep",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
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
    a.datas,
    strip=False,
    upx=False,
    name="AudioSep",
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="AudioSep.app",
        bundle_identifier="app.audiosep.desktop",
        info_plist={
            "CFBundleName": "AudioSep",
            "CFBundleDisplayName": "AudioSep",
            "CFBundleShortVersionString": version.split(".dev", 1)[0],
            "CFBundleVersion": version,
            "NSHighResolutionCapable": True,
        },
    )
