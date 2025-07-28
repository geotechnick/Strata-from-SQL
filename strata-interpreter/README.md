# Strata Interpreter

A professional geotechnical engineering application for soil strata interpretation and design parameter assignment using DIGGS SQL database format.

## Features

- **Interactive Strata Interpretation**: Visual interface for interpreting soil layers from borehole data
- **Design Parameter Assignment**: Calculate and assign geotechnical design parameters using established correlations
- **DIGGS SQL Compatibility**: Import and work with existing DIGGS SQL databases
- **JSON Export/Import**: Complete data preservation and sharing through standardized JSON format
- **Professional Visualization**: Maps, cross-sections, and parameter plots with USCS color coding
- **Parameter Calculation Engine**: Comprehensive calculations with multiple methods and validation
- **Data Validation**: Built-in validation for geotechnical data integrity and consistency

## Installation

### Requirements

- Python 3.9 or higher
- PyQt6 for GUI framework
- SQLAlchemy for database operations
- Additional scientific computing libraries (see requirements.txt)

### Setup

1. Clone the repository:
```bash
git clone https://github.com/geotechnick/strata-interpreter.git
cd strata-interpreter
```

2. Create and activate virtual environment:
```bash
python -m venv strata_env
# On Windows:
strata_env\Scripts\activate
# On macOS/Linux:
source strata_env/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Install development dependencies (optional):
```bash
pip install -r requirements-dev.txt
```

## Usage

### Running the Application

```bash
python src/main.py
```

### Basic Workflow

1. **Import Data**: Load existing DIGGS SQL database or import JSON soil profile
2. **Review Explorations**: Use the Map & Profile tab to visualize borehole locations and generate cross-sections
3. **Analyze Index Values**: Review N-values, plasticity index, and gradation data in tabular and plot format
4. **Assign Parameters**: Use design parameter tabs to calculate or manually assign geotechnical properties
5. **Export Results**: Save complete soil profile as JSON for use in design software

### Key Tabs

- **Map & Profile**: Interactive map of explorations with cross-section generation
- **Index Values**: Tabular display and elevation plots of SPT N-values, plasticity index, and fines content
- **Design Parameters**: Individual tabs for each parameter type with calculation methods and comparison views

## Data Format

### JSON Schema

The application uses a comprehensive JSON schema for soil profile data that includes:

- Project metadata and coordinate information
- Complete exploration data (boreholes, samples, test results)
- Interpreted strata layers with design parameters
- Calculation methods and source tracking
- Parameter override justifications

### DIGGS SQL Compatibility

Compatible with DIGGS 2.6 SQL database structure including:
- Project and HoleInfo tables
- Sample and TestResult tables
- Laboratory test data (gradation, Atterberg limits, strength tests, etc.)
- Field test data (SPT, penetration resistance, etc.)

## Development

### Project Structure

```
strata-interpreter/
├── src/
│   ├── core/                 # Database and calculation logic
│   ├── gui/                  # User interface components
│   ├── utils/                # Utilities and constants
│   └── resources/            # Stylesheets, icons, schemas
├── tests/                    # Test suite
├── docs/                     # Documentation
└── requirements.txt          # Dependencies
```

### Running Tests

```bash
pytest tests/
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint code
flake8 src/ tests/

# Type checking
mypy src/
```

## Parameter Calculations

The application includes comprehensive calculation methods for:

- **Unit Weight**: Dry, saturated, and submerged unit weights
- **Friction Angle**: SPT correlations, direct shear, and triaxial test analysis
- **Undrained Shear Strength**: Unconfined compression and triaxial methods
- **Modulus of Elasticity**: Empirical correlations and laboratory test results
- **Permeability**: Hazen formula, Kozeny-Carman equation, and laboratory tests
- **Consolidation Parameters**: Preconsolidation pressure, compression indices

All calculations include:
- Multiple calculation methods with confidence levels
- Source tracking (manual, calculated, estimated)
- Validation against typical parameter ranges
- Reference citations for equations used

## Color Coding

Consistent USCS color coding throughout the application:
- **Cool colors** (blues/purples) for fine-grained materials
- **Warm colors** (reds/oranges) for granular materials
- **Greys** for rock materials
- **Greens** for organic materials

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with appropriate tests
4. Run quality checks (tests, linting, formatting)
5. Submit pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For questions, issues, or feature requests, please use the GitHub issue tracker.

## Acknowledgments

- Based on DIGGS (Data Interchange for Geotechnical and GeoEnvironmental Specialists) standards
- Incorporates established geotechnical engineering correlations and methods
- Built with modern Python scientific computing stack (PyQt6, SQLAlchemy, pandas, matplotlib)

## Version History

- **v0.1.0**: Initial development version with core functionality
  - DIGGS SQL database import
  - Interactive strata interpretation
  - JSON export/import system
  - Basic parameter calculations
  - Map and profile visualization
  - Index values analysis