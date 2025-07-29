# Strata Interpreter

**A professional desktop application for geotechnical engineers to interpret soil strata and assign design parameters for engineering analysis.**

## What Does This Software Do?

Strata Interpreter helps geotechnical engineers transform raw subsurface exploration data into design-ready soil profiles. The software:

- **Imports exploration data** from DIGGS SQL databases containing borehole logs, soil samples, and laboratory test results
- **Visualizes site conditions** with interactive maps showing borehole locations and cross-section generation
- **Interprets soil layers** by allowing engineers to manually define strata boundaries and assign soil types
- **Calculates design parameters** using established geotechnical correlations (unit weight, friction angle, shear strength, etc.)
- **Exports complete soil profiles** as JSON files that preserve all data and can be imported into design software

This bridges the gap between field/laboratory data collection and engineering design by providing a systematic way to interpret subsurface conditions and assign the soil parameters needed for foundation design, slope stability analysis, and other geotechnical applications.

## Key Features

- **DIGGS SQL Database Import**: Work with standardized geotechnical databases
- **Interactive Site Maps**: View borehole locations and generate cross-sections between explorations  
- **Index Value Analysis**: Plot and analyze SPT N-values, plasticity index, and gradation data
- **Parameter Calculation Engine**: Multiple calculation methods with confidence tracking
- **USCS Color Coding**: Professional soil classification visualization throughout
- **Complete Data Export**: Save interpreted profiles as JSON for design software integration

## Installation

### Quick Start (Recommended)

**For most users, download the pre-built executable:**
1. Go to the [Releases](https://github.com/geotechnick/strata-interpreter/releases) page
2. Download `StrataInterpreter.exe` for Windows
3. Run the executable - no installation required!

### Developer Installation

**Requirements:** Python 3.9+ (download from [python.org](https://python.org))

```bash
# 1. Download the code
git clone https://github.com/geotechnick/strata-interpreter.git
cd strata-interpreter

# 2. Set up Python environment  
python -m venv strata_env
strata_env\Scripts\activate        # Windows
# source strata_env/bin/activate   # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the application
python src/main.py
```

## How to Use

### Getting Started
1. **Launch** the application (run executable or `python src/main.py`)
2. **Import your data** using File → Import DIGGS Database (or use File → Import JSON Profile for existing projects)
3. **Start interpreting** your soil data using the tabs described below

### Main Workflow

**Step 1: Import Data**
- Use **File → Import DIGGS Database** to load your `.db` or `.sqlite` file containing borehole and test data
- Or use **File → Import JSON Profile** to load previously saved projects

**Step 2: Review Site Layout**  
- Go to **Map & Profile** tab to see borehole locations on an interactive map
- Select multiple boreholes and click "Generate Profile" to create cross-sections
- Use this to understand the site geology and plan your strata interpretation

**Step 3: Analyze Test Data**
- Switch to **Index Values** tab to review SPT N-values, plasticity index, and gradation data
- Data is color-coded by soil type and plotted vs. elevation
- Use filters to focus on specific soil types or data with complete test results

**Step 4: Interpret Strata & Assign Parameters**
- Use individual **Design Parameter** tabs (Unit Weight, Friction Angle, etc.) to:
  - View calculated values from correlations
  - Manually override parameters with engineering judgment  
  - Compare manual vs. calculated values
  - Track confidence levels and justifications

**Step 5: Export Results**
- Use **File → Export → Soil Profile (JSON)** to save your complete interpretation
- The JSON file contains all original data plus your interpretations
- This file can be imported into design software or shared with colleagues

### Understanding the Interface

- **Map & Profile Tab**: Site visualization and cross-section generation
- **Index Values Tab**: Tabular and graphical display of test data (N-values, PI, fines content)  
- **Parameter Tabs**: Individual tabs for each design parameter with calculation tools
- **Color Coding**: Blue/purple = fine-grained soils, Red/orange = granular soils, Gray = rock, Green = organic

## Supported Data Formats

**Input:**
- **DIGGS SQL Databases** (`.db`, `.sqlite` files) - Industry standard geotechnical data format
- **JSON Soil Profiles** - Previously saved projects from this software

**Output:**  
- **JSON Soil Profiles** - Complete project data that can be shared or imported into design software
- **CSV/Excel exports** - Tabular data from any analysis tab

## Technical Details

### Parameter Calculations
The software includes established geotechnical correlations for:
- **Unit Weight**: Laboratory measurements and moisture-density relationships
- **Friction Angle**: SPT correlations (Peck, Schmertmann), direct shear analysis  
- **Undrained Shear Strength**: Unconfined compression, triaxial test analysis
- **Modulus of Elasticity**: SPT and strength-based correlations
- **Permeability**: Hazen formula, Kozeny-Carman equation, laboratory tests
- **Consolidation**: Casagrande method, compression/consolidation indices

### System Requirements
- **Operating System**: Windows 10/11 (executable), or any OS with Python 3.9+
- **Memory**: 512 MB RAM minimum, 2 GB recommended for large projects
- **Storage**: 100 MB free space for installation
- **Display**: 1024x768 minimum resolution, 1920x1080 recommended

## Troubleshooting

**Common Issues:**

- **"Database file not found"**: Ensure your DIGGS database file has `.db` or `.sqlite` extension
- **"No data displayed"**: Check that your database contains the required tables (Project, HoleInfo, Samples)
- **Map not loading**: Requires internet connection for map tiles
- **Slow performance**: Large databases may take time to load; use filters to work with subsets of data

**Getting Help:**
- Check the built-in help system: Help → About
- Report bugs or request features on [GitHub Issues](https://github.com/geotechnick/strata-interpreter/issues)
- For technical questions, include your data file format and error messages

## License & Attribution

**License:** MIT License - free for commercial and personal use

**Credits:**
- Based on DIGGS (Data Interchange for Geotechnical and GeoEnvironmental Specialists) standards
- Uses established geotechnical engineering correlations from Bowles, Das, Terzaghi, and others
- Built with PyQt6, SQLAlchemy, pandas, and matplotlib

**Version:** 0.1.0 - Initial release with core functionality