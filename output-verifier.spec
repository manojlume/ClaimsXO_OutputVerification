# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller specification for output-verifier.exe.

Important:
  Do NOT bundle config.yaml (or any YAML) into the executable.
  Configuration must remain an external file supplied via --config.
"""

from PyInstaller.utils.hooks import collect_submodules

hiddenimports = collect_submodules("output_verifier")

a = Analysis(
    ["src/output_verifier/__main__.py"],
    pathex=["src"],
    binaries=[],
    # Keep datas empty on purpose: YAML config stays outside the .exe.
    datas=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="output-verifier",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
