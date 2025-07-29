# Strata-from-SQL

**A professional geotechnical engineering desktop application for interpreting soil strata and assigning design parameters.**

## What This Software Does

Strata-from-SQL transforms raw geotechnical exploration data into design-ready soil profiles. The application:

- **Imports DIGGS SQL databases** containing borehole logs, samples, and laboratory test results
- **Provides interactive visualization** with site maps and cross-section generation  
- **Enables manual strata interpretation** by geotechnical engineers
- **Calculates design parameters** using established correlations (unit weight, friction angle, shear strength, etc.)
- **Exports complete soil profiles** as JSON files for design software integration

This bridges the gap between field investigation and engineering design by providing a systematic workflow for subsurface data interpretation.

## Quick Start

**Requirements:** Python 3.9+ ([download here](https://python.org))

```bash
# 1. Clone the repository
git clone https://github.com/geotechnick/Strata-from-SQL.git
cd Strata-from-SQL

# 2. Set up Python environment
python -m venv strata_env
strata_env\Scripts\activate        # Windows
# source strata_env/bin/activate   # macOS/Linux

# 3. Install dependencies
cd strata-interpreter
pip install -r requirements.txt

# 4. Run the application
python src/main.py
```

## Creating the Executable

To build the executable for distribution:

```bash
# Navigate to the strata-interpreter folder
cd strata-interpreter

# Option 1: Use the batch script (Windows)
create_release.bat

# Option 2: Use the Python build script
python build_exe.py

# Option 3: Use PyInstaller directly
pyinstaller strata_interpreter.spec
```

The executable will be created in `strata-interpreter/release/StrataInterpreter.exe` and is ready for distribution.

## How to Use

1. **Import Data**: File → Import DIGGS Database (load your .db/.sqlite file)
2. **Review Site**: Map & Profile tab shows borehole locations and cross-sections
3. **Analyze Tests**: Index Values tab displays SPT N-values, plasticity index, gradation data
4. **Assign Parameters**: Design Parameter tabs for unit weight, friction angle, etc.
5. **Export Results**: File → Export → Soil Profile (JSON) saves complete interpretation

## Key Features

- **DIGGS SQL Database Support** - Compatible with standard geotechnical data format
- **Interactive Site Visualization** - Maps and cross-section generation
- **Professional Parameter Calculations** - Multiple methods with confidence tracking
- **USCS Color Coding** - Industry-standard soil classification colors
- **Complete Data Preservation** - JSON export maintains all original data plus interpretations
- **Future ML Integration** - Architecture designed for machine learning expansion

## Technical Foundation

Built using the SQL database structure from [DIGGS_SQL](https://github.com/geotechnick/DIGGS_SQL) with:
- PyQt6 desktop framework for professional UI
- SQLAlchemy for robust database operations  
- Comprehensive geotechnical calculation engine
- JSON schema for standardized data exchange

**Future Development**: The modular architecture is designed for expansion with machine learning algorithms and integration with design software packages.
