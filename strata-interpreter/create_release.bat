@echo off
REM Batch script to build Strata Interpreter executable for release

echo ==========================================
echo Building Strata Interpreter Executable
echo ==========================================

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.9+ from https://python.org
    pause
    exit /b 1
)

REM Check if we're in the right directory
if not exist "src\main.py" (
    echo ERROR: This script must be run from the strata-interpreter directory
    echo Current directory: %CD%
    pause
    exit /b 1
)

echo.
echo Installing/upgrading required packages...
pip install --upgrade pip
pip install --upgrade pyinstaller
pip install -r requirements.txt

if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo Building executable...
python build_exe.py

if errorlevel 1 (
    echo ERROR: Build failed
    pause
    exit /b 1
)

echo.
echo ==========================================
echo BUILD COMPLETED SUCCESSFULLY!
echo ==========================================
echo.
echo Executable location: release\StrataInterpreter.exe
echo.
echo To test the executable:
echo 1. Navigate to the release folder
echo 2. Double-click StrataInterpreter.exe
echo.
echo The executable is ready for distribution!
echo.
pause