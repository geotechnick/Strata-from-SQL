# Building the Strata Interpreter Executable

This document provides instructions for building the Strata Interpreter executable for distribution.

## Prerequisites

1. **Python 3.9+** installed and working
2. **PyInstaller** installed: `pip install pyinstaller`
3. **All dependencies** installed: `pip install -r requirements.txt`
4. **UPX** (optional, for compression): Download from https://upx.github.io/

## Build Methods

### Method 1: Using the Build Script (Recommended)

```bash
# 1. Navigate to the project directory
cd strata-interpreter

# 2. Ensure all dependencies are installed
pip install -r requirements.txt
pip install pyinstaller

# 3. Run the build script
python build_exe.py
```

The executable will be created in the `release/` folder.

### Method 2: Using PyInstaller Directly

```bash
# Using the spec file
pyinstaller strata_interpreter.spec

# Or using command line options
pyinstaller --name=StrataInterpreter --onefile --windowed src/main.py
```

### Method 3: Manual PyInstaller Command

```bash
pyinstaller \
  --name=StrataInterpreter \
  --onefile \
  --windowed \
  --add-data="src/resources;resources" \
  --add-data="src/utils;utils" \
  --hidden-import=PyQt6.QtWebEngineWidgets \
  --hidden-import=matplotlib.backends.backend_qt5agg \
  --hidden-import=folium \
  --hidden-import=pyqtgraph \
  --exclude-module=tkinter \
  src/main.py
```

## Build Output

After a successful build, you'll find:

- **dist/StrataInterpreter.exe** - The main executable
- **release/StrataInterpreter.exe** - Copy ready for distribution
- **build/** - Temporary build files (can be deleted)

## Testing the Executable

1. Navigate to the `release/` folder
2. Double-click `StrataInterpreter.exe`
3. The application should launch normally
4. Test basic functionality:
   - Application opens without errors
   - Menus and tabs are accessible
   - File import dialogs work
   - Basic UI interactions function

## Distribution

The executable in the `release/` folder is ready for distribution:

1. **Single File**: The exe is self-contained with all dependencies
2. **No Installation**: Users can run it directly
3. **Windows Compatible**: Works on Windows 10/11
4. **Size**: Typically 50-100 MB depending on dependencies

## Troubleshooting

### Common Issues

**"Module not found" errors:**
- Add missing modules to `hiddenimports` in the spec file
- Or use `--hidden-import=module_name` in command line

**Large executable size:**
- Ensure UPX is installed for compression
- Remove unnecessary modules from excludes

**Application won't start:**
- Test with `--console` flag to see error messages
- Check that all resources are included with `--add-data`

**Missing resources:**
- Verify resource paths in the spec file
- Check that resource files exist in the source

### Build Environment

**Recommended setup:**
- Clean Python virtual environment
- Latest versions of dependencies
- Windows 10/11 for Windows executables
- 4GB+ RAM for build process

## Automation

For automated builds, you can:

1. **GitHub Actions**: Set up CI/CD to build releases automatically
2. **Batch Script**: Create a `.bat` file that runs the build process
3. **PowerShell**: Use PowerShell scripts for advanced build automation

## File Structure After Build

```
strata-interpreter/
├── src/                    # Source code
├── build/                  # Temporary build files
├── dist/                   # PyInstaller output
├── release/                # Distribution ready files
│   └── StrataInterpreter.exe
├── build_exe.py           # Build script
├── strata_interpreter.spec # PyInstaller spec
└── build_instructions.md  # This file
```