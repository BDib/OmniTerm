# -*- mode: python ; coding: utf-8 -*-
# OmniTerm PyInstaller spec file
from pathlib import Path
src_root = Path(SPECPATH)

a = Analysis(
    [str(src_root / "src" / "Main.py")],
    pathex=[str(src_root), str(src_root / "src")],
    binaries=[],
    datas=[(str(src_root / "settings.toml"), ".")],
    hiddenimports=["toml", "paramiko", "serial"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter", "_tkinter", "matplotlib", "numpy", "scipy",
        "pandas", "pytest", "unittest", "winpty",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz, a.scripts, a.binaries, a.zipfiles, a.datas, [],
    name="pyOmniTerm-win10-x64",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version=None,
)
