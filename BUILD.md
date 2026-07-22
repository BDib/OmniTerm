# Building OmniTerm

OmniTerm can be built using **Nuitka** (default, fastest) or **PyInstaller** (fallback). An **Inno Setup** installer can also be created.

## Quick Start

```powershell
# Default build (Nuitka)
.\build.ps1

# Or with cmd
build.bat
```

## Build Options

| Command | Description |
|---------|-------------|
| `.\build.ps1` | Nuitka standalone build (default) |
| `.\build.ps1 pyinstaller` | PyInstaller standalone build |
| `.\build.ps1 debug` | Nuitka debug build (console visible) |
| `.\build.ps1 pyinstaller-debug` | PyInstaller debug build |
| `.\build.ps1 installer` | Build + create Inno Setup installer |
| `.\build.ps1 clean` | Remove all build artifacts |

## Nuitka vs PyInstaller

| | Nuitka | PyInstaller |
|---|---|---|
| **Startup** | ~13ms | ~97ms |
| **Size** | ~25 MB | ~44 MB |
| **Build time** | ~5-10 min (first run) | ~30s |
| **Default** | Yes | Fallback |

Nuitka compiles Python to C before packaging, eliminating the Python interpreter startup overhead. First build is slow due to C compilation, but subsequent builds use cached artifacts.

## Output Files

| File | Builder | Description |
|------|---------|-------------|
| `dist\OmniTerm-win10-x64.exe` | Nuitka | Standalone executable |
| `dist\pyOmniTerm-win10-x64.exe` | PyInstaller | Standalone executable |
| `installer_output\OmniTermSetup-win10-x64.exe` | Inno Setup | Windows installer |

## Creating an Installer

The project includes an Inno Setup script (`installer\omniterm.iss`) for creating a professional Windows installer.

### Prerequisites
- [Inno Setup 6](https://jrsoftware.org/isinfo.php) installed

### Build
```powershell
.\build.ps1 installer
```

### Installer Features
- Installs to Program Files
- Creates Start Menu and desktop shortcuts
- Optional .toml file association
- Uninstaller
- Post-install launch option
- Requires admin privileges (UAC prompt)

## CI/CD

GitHub Actions automatically:
1. Tests on Python 3.10-3.13
2. Builds with PyInstaller on tag push
3. Creates Inno Setup installer
4. Publishes release to GitHub with win10/11 x64 binaries

## Troubleshooting

### Nuitka build fails
- Ensure Visual Studio Build Tools are installed (`cl.exe` must be available)
- Nuitka requires MSVC on Windows
- First build takes ~5-10 minutes due to C compilation
- Clean temp files: `Remove-Item -Recur -Force C:\Temp\nbuild`

### PyInstaller build fails
- Run `pip install pyinstaller` first
- Check that all dependencies are installed

### Installer build fails
- Install Inno Setup 6 from https://jrsoftware.org/isinfo.php
- Ensure Inno Setup is in the default install path

### Terminal crashes after 5 seconds (Nuitka only)
- This was fixed in v2.1.0. The issue was `STARTUPINFOEXW` vs `STARTUPINFOW` in the ConPTY startup code.
- If you still see this, ensure you're running the latest build.
