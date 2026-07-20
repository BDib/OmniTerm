# OmniTerm Build Script (PowerShell)
# Builds a standalone Windows .exe using PyInstaller.
#
# Usage:
#   .\build.ps1          — Build in release mode
#   .\build.ps1 debug    — Build in debug mode (console visible)
#   .\build.ps1 clean    — Remove build artifacts
#
# IMPORTANT: Uses `python -m PyInstaller` to ensure the correct Python
# interpreter is used. If you have multiple Python installs, activate
# the right venv first.

param(
    [ValidateSet("release", "debug", "clean")]
    [string]$Mode = "release"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

Write-Host ""
Write-Host "============================================"
Write-Host "  OmniTerm v$(python -c "import sys; sys.path.insert(0,'src'); from config import VERSION; print(VERSION)")"
Write-Host "============================================"
Write-Host ""

if ($Mode -eq "clean") {
    Write-Host "Cleaning build artifacts..."
    if (Test-Path build) { Remove-Item -Recurse -Force build }
    if (Test-Path dist) { Remove-Item -Recurse -Force dist }
    Write-Host "Done."
    exit 0
}

# Check for Python
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: Python not found in PATH." -ForegroundColor Red
    Write-Host "Please install Python 3.10+ from https://python.org"
    exit 1
}

# Display version
python -c "import sys; sys.path.insert(0,'src'); from config import VERSION; print(f'Building OmniTerm v{VERSION}')"

# Check for PyInstaller (via python -m to use correct interpreter)
python -c "import PyInstaller" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "PyInstaller not found. Installing..."
    python -m pip install pyinstaller
}

# Install dependencies
Write-Host "Installing dependencies..."
python -m pip install -r requirements.txt --quiet

# Build — always use `python -m PyInstaller` to avoid picking up
# a different Python's pyinstaller.exe from PATH.
if ($Mode -eq "debug") {
    Write-Host "Building in DEBUG mode (console visible)..."
    python -m PyInstaller OmniTerm.spec --noconfirm --console
} else {
    Write-Host "Building in RELEASE mode..."
    python -m PyInstaller OmniTerm.spec --noconfirm
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
