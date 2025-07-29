"""
Build script to create executable using PyInstaller.
Run this script to build the Strata Interpreter executable.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def main():
    """Build the executable using PyInstaller."""
    
    # Get the current directory
    current_dir = Path(__file__).parent
    src_dir = current_dir / "src"
    main_py = src_dir / "main.py"
    
    if not main_py.exists():
        print(f"Error: {main_py} not found!")
        return False
    
    # Clean previous builds
    build_dir = current_dir / "build"
    dist_dir = current_dir / "dist"
    
    if build_dir.exists():
        shutil.rmtree(build_dir)
        print("Cleaned build directory")
    
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
        print("Cleaned dist directory")
    
    # PyInstaller command
    cmd = [
        "pyinstaller",
        "--name=StrataInterpreter",
        "--onefile",
        "--windowed",
        "--icon=src/resources/icons/app_icon.ico",
        "--add-data=src/resources;resources",
        "--add-data=src/utils;utils",
        "--hidden-import=PyQt6.QtWebEngineWidgets",
        "--hidden-import=PyQt6.QtWebEngineCore",
        "--hidden-import=matplotlib.backends.backend_qt5agg",
        "--hidden-import=folium",
        "--hidden-import=pyqtgraph",
        "--hidden-import=sqlalchemy",
        "--hidden-import=pandas",
        "--hidden-import=numpy",
        "--hidden-import=jsonschema",
        "--exclude-module=tkinter",
        "--exclude-module=unittest",
        "--exclude-module=test",
        str(main_py)
    ]
    
    print("Building executable with PyInstaller...")
    print(f"Command: {' '.join(cmd)}")
    
    try:
        # Run PyInstaller
        result = subprocess.run(cmd, cwd=current_dir, check=True, capture_output=True, text=True)
        print("Build completed successfully!")
        
        # Check if executable was created
        exe_path = dist_dir / "StrataInterpreter.exe"
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print(f"Executable created: {exe_path}")
            print(f"Size: {size_mb:.1f} MB")
            
            # Create a release directory
            release_dir = current_dir / "release"
            release_dir.mkdir(exist_ok=True)
            
            # Copy executable to release directory
            release_exe = release_dir / "StrataInterpreter.exe"
            shutil.copy2(exe_path, release_exe)
            print(f"Executable copied to: {release_exe}")
            
            return True
        else:
            print("Error: Executable not found after build")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"Build failed with error: {e}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)
    
    print("\n" + "="*50)
    print("BUILD SUCCESSFUL!")
    print("="*50)
    print("The executable is ready for distribution.")
    print("Location: release/StrataInterpreter.exe")
    print("\nTo test the executable:")
    print("1. Navigate to the release folder")
    print("2. Double-click StrataInterpreter.exe")
    print("3. The application should launch normally")