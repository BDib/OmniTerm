@echo off
:: OmniTerm Build Script
:: Builds a standalone Windows .exe using PyInstaller.
::
:: Usage:
::   build.bat          — Build in release mode
::   build.bat debug    — Build in debug mode (console visible)
::   build.bat clean    — Remove build artifacts

setlocal
cd /d "%~dp0"

echo ============================================
echo   OmniTerm v0.8 Build
echo ============================================
echo.

if "%1"=="clean" (
    echo Cleaning build artifacts...
    if exist build rmdir /s /q build
    if exist dist rmdir /s /q dist
    if exist OmniTerm.spec del OmniTerm.spec
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

:: Display version info
python -c "from config import VERSION; print(f'Building OmniTerm v{VERSION}')"

:: Check for PyInstaller
python -c "import PyInstaller" >nul 2>&1
if %errorlevel% neq 0 (
    echo PyInstaller not found. Installing...
    pip install pyinstaller
)

:: Install dependencies
echo Installing dependencies...
pip install -r requirements.txt --quiet

:: Build
if "%1"=="debug" (
    echo Building in DEBUG mode (console visible)...
    pyinstaller OmniTerm.spec --noconfirm --console
) else (
    echo Building in RELEASE mode...
    pyinstaller OmniTerm.spec --noconfirm
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
