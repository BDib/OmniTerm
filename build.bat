@echo off
setlocal
cd /d "%~dp0"

:: OmniTerm Build Script
:: Builds a standalone Windows .exe using PyInstaller or Nuitka.
::
:: Usage:
::   build.bat              - Build with PyInstaller (release mode)
::   build.bat nuitka       - Build with Nuitka (faster startup)
::   build.bat debug        - Build in debug mode (console visible)
::   build.bat clean        - Remove build artifacts

set MODE=%1
if "%MODE%"=="" set MODE=release

echo.
echo ============================================
echo   OmniTerm Build
echo ============================================
echo.

if "%MODE%"=="clean" (
    echo Cleaning build artifacts...
    if exist build rmdir /s /q build
    if exist dist rmdir /s /q dist
    if exist output rmdir /s /q output
    echo Done.
    goto :end
)

:: Check for Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python not found in PATH.
    exit /b 1
)

python -c "import sys; sys.path.insert(0,'src'); from config import VERSION; print(f'Building OmniTerm v{VERSION}')"

:: Install dependencies
echo Installing dependencies...
python -m pip install -r requirements.txt --quiet

if "%MODE%"=="nuitka" goto :nuitka
if "%MODE%"=="nuitka-debug" goto :nuitka

:: ── PyInstaller Build ──
python -c "import PyInstaller" >nul 2>&1
if %errorlevel% neq 0 (
    echo PyInstaller not found. Installing...
    python -m pip install pyinstaller
)

if "%MODE%"=="debug" (
    echo Building in DEBUG mode (console visible^)...
    python -m PyInstaller OmniTerm.spec --noconfirm --console
) else (
    echo Building in RELEASE mode...
    python -m PyInstaller OmniTerm.spec --noconfirm
)
goto :result

:nuitka
:: ── Nuitka Build ──
python -c "import nuitka" >nul 2>&1
if %errorlevel% neq 0 (
    echo Nuitka not found. Installing...
    python -m pip install nuitka --quiet
)

echo Building with Nuitka (standalone onefile^)...
echo This may take several minutes on first run...

set NUITKA_ARGS=--standalone --onefile --windows-console-mode=disable --output-dir=dist --output-filename=OmniTerm.exe --include-data-file=settings.toml=settings.toml --include-package=winpty --include-package=PyQt6 --include-package=serial --include-package=paramiko --include-package=toml --nofollow-import-to=tkinter,matplotlib,numpy,scipy,pandas,pytest,unittest src/Main.py

if "%MODE%"=="nuitka-debug" (
    set NUITKA_ARGS=%NUITKA_ARGS% --debug
)

python -m nuitka %NUITKA_ARGS%

:result
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
