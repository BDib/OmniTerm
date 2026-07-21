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
import glob as _glob

src_root = Path(SPECPATH)
_winpty_dir = Path(_winpty_mod.__file__).parent

# Find the winpty .pyd dynamically (differs by Python version)
_winpty_pyd = _glob.glob(str(_winpty_dir / "_winpty*.pyd"))
_binaries = []
for f in _winpty_pyd:
    _binaries.append((f, "winpty"))
for dll in ["conpty.dll", "winpty.dll", "winpty-agent.exe", "OpenConsole.exe"]:
    p = _winpty_dir / dll
    if p.exists():
        _binaries.append((str(p), "winpty"))

a = Analysis(
    [str(src_root / "src" / "Main.py")],
    pathex=[str(src_root), str(src_root / "src")],
    binaries=_binaries,
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
    name="pyOmniTerm",
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
