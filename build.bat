@echo off
setlocal
cd /d "%~dp0"

:: OmniTerm Build Script
:: Builds a standalone Windows .exe using PyInstaller.
::
:: Usage:
::   build.bat          - Build in release mode
::   build.bat debug    - Build in debug mode (console visible)
::   build.bat clean    - Remove build artifacts
::
:: For PowerShell, use: .\build.ps1 [release|debug|clean]
::
:: IMPORTANT: Uses `python -m PyInstaller` to ensure the correct Python
:: interpreter is used. If you have multiple Python installs, activate
:: the right venv first.

echo.
echo ============================================
echo   OmniTerm Build
echo ============================================
echo.

if "%1"=="clean" (
    echo Cleaning build artifacts...
    if exist build rmdir /s /q build
    if exist dist rmdir /s /q dist
    echo Done.
    goto :end
)

:: Check for Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python not found in PATH.
    echo Please install Python 3.10+ from https://python.org
    exit /b 1
)

:: Display version
python -c "from config import VERSION; print(f'Building OmniTerm v{VERSION}')"

:: Check for PyInstaller (via python -m to use correct interpreter)
python -c "import PyInstaller" >nul 2>&1
if %errorlevel% neq 0 (
    echo PyInstaller not found. Installing...
    python -m pip install pyinstaller
)

:: Install dependencies
echo Installing dependencies...
python -m pip install -r requirements.txt --quiet

:: Build — always use `python -m PyInstaller` to avoid picking up
:: a different Python's pyinstaller.exe from PATH.
if "%1"=="debug" (
    echo Building in DEBUG mode ^(console visible^)...
    python -m PyInstaller OmniTerm.spec --noconfirm --console
) else (
    echo Building in RELEASE mode...
    python -m PyInstaller OmniTerm.spec --noconfirm
)

echo.
if %errorlevel% equ 0 (
    echo ============================================
    echo   BUILD SUCCESSFUL
    echo   Output: dist\OmniTerm.exe
    echo ============================================
    dir dist\OmniTerm.exe 2>nul
) else (
    echo ============================================
    echo   BUILD FAILED
    echo ============================================
)

:end
endlocal
