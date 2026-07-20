# -*- mode: python ; coding: utf-8 -*-
# OmniTerm PyInstaller spec file
#
# Build with:
#   pyinstaller OmniTerm.spec
#
# Or via the convenience scripts:
#   build.bat          (cmd)
#   .\build.ps1        (PowerShell)

from pathlib import Path
import winpty as _winpty_mod

src_root = Path(SPECPATH)
_winpty_dir = Path(_winpty_mod.__file__).parent

a = Analysis(
    [str(src_root / "src" / "Main.py")],
    pathex=[str(src_root), str(src_root / "src")],
    binaries=[
        (str(_winpty_dir / "_winpty.cp313-win_amd64.pyd"), "winpty"),
        (str(_winpty_dir / "conpty.dll"), "winpty"),
        (str(_winpty_dir / "winpty.dll"), "winpty"),
        (str(_winpty_dir / "winpty-agent.exe"), "winpty"),
        (str(_winpty_dir / "OpenConsole.exe"), "winpty"),
    ],
    datas=[
        (str(src_root / "settings.toml"), "."),
    ],
    hiddenimports=["toml", "winpty"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter", "_tkinter",
        "matplotlib",
        "numpy",
        "scipy",
        "pandas",
        "pytest",
        "unittest",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="OmniTerm",
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
    # icon="assets/OmniTerm.ico",
)
