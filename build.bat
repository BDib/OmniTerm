@echo off
setlocal
cd /d "%~dp0"

:: OmniTerm Build Script
:: Builds a standalone Windows .exe using Nuitka (default) or PyInstaller.
::
:: Usage:
::   build.bat              - Build with Nuitka (default)
::   build.bat pyinstaller  - Build with PyInstaller (fallback)
::   build.bat debug        - Nuitka debug build
::   build.bat installer    - Build + create Inno Setup installer
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
    if exist dist_nuitka rmdir /s /q dist_nuitka
    if exist output rmdir /s /q output
    if exist installer_output rmdir /s /q installer_output
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

if "%MODE%"=="pyinstaller" goto :pyinstaller
if "%MODE%"=="pyinstaller-debug" goto :pyinstaller

:: ── Nuitka Build (default) ──
python -c "import nuitka" >nul 2>&1
if %errorlevel% neq 0 (
    echo Nuitka not found. Installing...
    python -m pip install nuitka --quiet
)

:: Fix Scons temp path bug
set OLD_TEMP=%TEMP%
set OLD_TMP=%TMP%
if not exist C:\Temp\nbuild mkdir C:\Temp\nbuild
set TEMP=C:\Temp\nbuild
set TMP=C:\Temp\nbuild

echo Building with Nuitka (standalone^)...
set NUITKA_ARGS=--standalone --enable-plugin=pyqt6 --output-dir=dist_nuitka --output-filename=OmniTerm.exe --include-data-file=settings.toml=settings.toml --include-package=winpty --include-package=serial --include-package=paramiko --include-package=toml --nofollow-import-to=tkinter,matplotlib,numpy,scipy,pandas,pytest,unittest --windows-console-mode=disable src/Main.py

if "%MODE%"=="debug" (
    set NUITKA_ARGS=%NUITKA_ARGS% --debug
)

python -m nuitka %NUITKA_ARGS%

:: Restore temp
set TEMP=%OLD_TEMP%
set TMP=%OLD_TMP%

:: Copy to dist
if exist dist_nuitka\Main.dist\OmniTerm.exe (
    if not exist dist mkdir dist
    xcopy /E /Y /Q dist_nuitka\Main.dist\* dist\ >nul
    echo Copied Nuitka build to dist\
)
goto :result

:pyinstaller
:: ── PyInstaller Build (fallback) ──
python -c "import PyInstaller" >nul 2>&1
if %errorlevel% neq 0 (
    echo PyInstaller not found. Installing...
    python -m pip install pyinstaller
)

if "%MODE%"=="pyinstaller-debug" (
    echo Building with PyInstaller (DEBUG mode^)...
    python -m PyInstaller OmniTerm.spec --noconfirm --console
) else (
    echo Building with PyInstaller (RELEASE mode^)...
    python -m PyInstaller OmniTerm.spec --noconfirm
)

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
