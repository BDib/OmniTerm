# OmniTerm Build Script (PowerShell)
# Builds a standalone Windows .exe using PyInstaller or Nuitka.
#
# Usage:
#   .\build.ps1              — Build with PyInstaller (release mode)
#   .\build.ps1 nuitka       — Build with Nuitka (faster startup)
#   .\build.ps1 debug        — Build in debug mode (console visible)
#   .\build.ps1 clean        — Remove build artifacts

param(
    [ValidateSet("release", "debug", "clean", "nuitka", "nuitka-debug")]
    [string]$Mode = "release"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$ver = python -c "import sys; sys.path.insert(0,'src'); from config import VERSION; print(VERSION)"
Write-Host ""
Write-Host "============================================"
Write-Host "  OmniTerm v$ver"
Write-Host "============================================"
Write-Host ""

if ($Mode -eq "clean") {
    Write-Host "Cleaning build artifacts..."
    if (Test-Path build) { Remove-Item -Recurse -Force build }
    if (Test-Path dist) { Remove-Item -Recurse -Force dist }
    if (Test-Path output) { Remove-Item -Recurse -Force output }
    Write-Host "Done."
    exit 0
}

# Check for Python
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: Python not found in PATH." -ForegroundColor Red
    exit 1
}

python -c "import sys; sys.path.insert(0,'src'); from config import VERSION; print(f'Building OmniTerm v{VERSION}')"

# Install dependencies
Write-Host "Installing dependencies..."
python -m pip install -r requirements.txt --quiet

if ($Mode -like "nuitka*") {
    # ── Nuitka Build ──
    python -c "import nuitka" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Nuitka not found. Installing..."
        python -m pip install nuitka --quiet
    }

    $nuitka_args = @(
        "--standalone",
        "--onefile",
        "--windows-console-mode=disable",
        "--output-dir=dist",
        "--output-filename=OmniTerm.exe",
        "--include-data-dir=src=src",
        "--include-data-file=settings.toml=settings.toml",
        "--include-package=winpty",
        "--include-package=PyQt6",
        "--include-package=PyQt6.QtWidgets",
        "--include-package=PyQt6.QtCore",
        "--include-package=PyQt6.QtGui",
        "--include-package=serial",
        "--include-package=paramiko",
        "--include-package=toml",
        "--nofollow-import-to=tkinter,matplotlib,numpy,scipy,pandas,pytest,unittest",
        "--windows-icon-from-ico=assets/OmniTerm.ico",
        "src/Main.py"
    )

    if ($Mode -eq "nuitka-debug") {
        $nuitka_args += "--debug"
    }

    Write-Host "Building with Nuitka (standalone onefile)..."
    Write-Host "This may take several minutes on first run..."
    python -m nuitka @nuitka_args

} else {
    # ── PyInstaller Build ──
    python -c "import PyInstaller" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "PyInstaller not found. Installing..."
        python -m pip install pyinstaller
    }

    if ($Mode -eq "debug") {
        Write-Host "Building in DEBUG mode (console visible)..."
        python -m PyInstaller OmniTerm.spec --noconfirm --console
    } else {
        Write-Host "Building in RELEASE mode..."
        python -m PyInstaller OmniTerm.spec --noconfirm
    }
}

Write-Host ""
if ($LASTEXITCODE -eq 0) {
    $exe = Get-Item dist\OmniTerm.exe -ErrorAction SilentlyContinue
    Write-Host "============================================"
    Write-Host "  BUILD SUCCESSFUL"
    Write-Host "  Output: dist\OmniTerm.exe"
    if ($exe) {
        Write-Host "  Size:   $([math]::Round($exe.Length / 1MB, 1)) MB"
    }
    Write-Host "============================================"
} else {
    Write-Host "============================================" -ForegroundColor Red
    Write-Host "  BUILD FAILED" -ForegroundColor Red
    Write-Host "============================================" -ForegroundColor Red
    exit 1
}
