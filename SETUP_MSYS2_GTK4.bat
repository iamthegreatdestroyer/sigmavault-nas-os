@echo off
REM MSYS2 GTK4 Setup Launcher for Windows
REM This script launches MSYS2 and runs the setup

echo.
echo ========================================
echo MSYS2 GTK4 Setup for SigmaVault Desktop
echo ========================================
echo.

REM Check if MSYS2 is installed
if not exist "S:\msys64\mingw64.exe" (
    echo ERROR: MSYS2 not found at S:\msys64
    echo Please install MSYS2 first
    pause
    exit /b 1
)

echo Launching MSYS2 MinGW64 terminal...
echo.
echo The terminal will:
echo 1. Update package manager
echo 2. Install GTK4, libadwaita, and build tools
echo 3. Set up Python virtual environment
echo 4. Install PyGObject
echo 5. Verify everything works
echo.
echo This may take 5-15 minutes on first run...
echo.

REM Launch MSYS2 with the setup script
S:\msys64\mingw64.exe -c "bash /s/sigmavault-nas-os/SETUP_MSYS2_GTK4.sh"

echo.
echo ========================================
echo Setup completed!
echo.
echo Next steps:
echo 1. Open MSYS2 MinGW64 terminal: S:\msys64\mingw64.exe
echo 2. cd /s/sigmavault-nas-os/src/desktop-ui
echo 3. source .venv/Scripts/activate
echo 4. python main.py
echo ========================================
echo.
pause
