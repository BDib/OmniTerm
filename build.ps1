# OmniTerm Build Script (PowerShell)
# Builds a standalone Windows .exe using Nuitka (default) or PyInstaller.
#
# Usage:
#   .\build.ps1              — Build with Nuitka (default, fastest startup)
#   .\build.ps1 pyinstaller  — Build with PyInstaller (fallback)
#   .\build.ps1 debug        — Nuitka debug build
#   .\build.ps1 installer    — Build Nuitka + create Inno Setup installer
#   .\build.ps1 clean        — Remove build artifacts

param(
    [ValidateSet("release", "debug", "clean", "pyinstaller", "pyinstaller-debug", "installer")]
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
    if (Test-Path dist_nuitka) { Remove-Item -Recurse -Force dist_nuitka }
    if (Test-Path output) { Remove-Item -Recurse -Force output }
    if (Test-Path installer_output) { Remove-Item -Recurse -Force installer_output }
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

function Build-Nuitka {
    param([bool]$DebugMode = $false)

    python -c "import nuitka" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Nuitka not found. Installing..."
        python -m pip install nuitka --quiet
    }

    # Fix Scons temp path bug (spaces in path break the linker)
    $nbuildTemp = "C:\Temp\nbuild"
    New-Item -ItemType Directory -Force -Path $nbuildTemp | Out-Null
    $oldTemp = $env:TEMP; $oldTmp = $env:TMP
    $env:TEMP = $nbuildTemp; $env:TMP = $nbuildTemp

    $nuitka_args = @(
        "--onefile",
        "--enable-plugin=pyqt6",
        "--output-dir=dist_nuitka",
        "--output-filename=OmniTerm-windows-x64.exe",
        "--include-data-file=settings.toml=settings.toml",
        "--include-package=winpty",
        "--include-package=serial",
        "--include-package=paramiko",
        "--include-package=toml",
        "--nofollow-import-to=tkinter,matplotlib,numpy,scipy,pandas,pytest,unittest",
        "--windows-console-mode=disable",
        "src/Main.py"
    )

    if ($DebugMode) {
        $nuitka_args += "--debug"
    }

    Write-Host "Building with Nuitka (standalone)..."
    python -m nuitka @nuitka_args

    # Restore temp
    $env:TEMP = $oldTemp; $env:TMP = $oldTmp

    # Copy output to dist
    if (Test-Path "dist_nuitka\OmniTerm-windows-x64.exe") {
        if (-not (Test-Path dist)) { New-Item -ItemType Directory -Path dist | Out-Null }
        Copy-Item "dist_nuitka\OmniTerm-windows-x64.exe" "dist\OmniTerm-windows-x64.exe" -Force
        Write-Host "Copied Nuitka onefile to dist\"
    }
}

function Build-PyInstaller {
    param([bool]$DebugMode = $false)

    python -c "import PyInstaller" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "PyInstaller not found. Installing..."
        python -m pip install pyinstaller
    }

    if ($DebugMode) {
        Write-Host "Building with PyInstaller (DEBUG mode)..."
        python -m PyInstaller OmniTerm.spec --noconfirm --console
    } else {
        Write-Host "Building with PyInstaller (RELEASE mode)..."
        python -m PyInstaller OmniTerm.spec --noconfirm
    }
}

# ── Build ──
switch ($Mode) {
    "pyinstaller"       { Build-PyInstaller -DebugMode $false }
    "pyinstaller-debug"{ Build-PyInstaller -DebugMode $true }
    "debug"            { Build-Nuitka -DebugMode $true }
    default             { Build-Nuitka -DebugMode $false }
}

# ── Installer ──
if ($Mode -eq "installer") {
    Write-Host ""
    Write-Host "Creating installer with Inno Setup..."

    # Find Inno Setup compiler
    $iscc = $null
    $candidates = @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles(x86)}\Inno Setup 5\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 5\ISCC.exe"
    )
    foreach ($c in $candidates) {
        if (Test-Path $c) { $iscc = $c; break }
    }

    if (-not $iscc) {
        Write-Host "Inno Setup not found. Install from https://jrsoftware.org/isinfo.php" -ForegroundColor Yellow
        Write-Host "Skipping installer creation."
    } else {
        & $iscc installer\omniterm.iss
        if ($LASTEXITCODE -eq 0) {
            $setup = Get-Item installer_output\OmniTermSetup.exe -ErrorAction SilentlyContinue
            if ($setup) {
                Write-Host "Installer: $([math]::Round($setup.Length / 1MB, 1)) MB"
            }
        }
    }
}

# ── Result ──
Write-Host ""
if ($LASTEXITCODE -eq 0 -or $Mode -eq "installer") {
    $exe = Get-Item dist\OmniTerm.exe -ErrorAction SilentlyContinue
    Write-Host "============================================"
    Write-Host "  BUILD SUCCESSFUL"
    Write-Host "  Output: dist\OmniTerm.exe"
    if ($exe) {
        Write-Host "  Size:   $([math]::Round($exe.Length / 1MB, 1)) MB"
    }
    $setup = Get-Item installer_output\OmniTermSetup.exe -ErrorAction SilentlyContinue
    if ($setup) {
        Write-Host "  Installer: installer_output\OmniTermSetup.exe ($([math]::Round($setup.Length / 1MB, 1)) MB)"
    }
    Write-Host "============================================"
} else {
    Write-Host "============================================" -ForegroundColor Red
    Write-Host "  BUILD FAILED" -ForegroundColor Red
    Write-Host "============================================" -ForegroundColor Red
    exit 1
}
