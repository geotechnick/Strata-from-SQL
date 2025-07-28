"""
Application constants and configuration values.
"""

from pathlib import Path

# Application information
APP_NAME = "Strata Interpreter"
APP_VERSION = "0.1.0"
APP_ORGANIZATION = "Geotechnical Engineering"

# File paths
APP_DIR = Path(__file__).parent.parent
RESOURCES_DIR = APP_DIR / "resources"
SCHEMA_DIR = RESOURCES_DIR / "schema"
STYLES_DIR = RESOURCES_DIR / "styles"
ICONS_DIR = RESOURCES_DIR / "icons"

# Schema files
SOIL_PROFILE_SCHEMA_PATH = SCHEMA_DIR / "soil_profile_schema.json"
EQUATIONS_PATH = RESOURCES_DIR / "equations.json"

# Database settings
DEFAULT_DB_NAME = "strata_project.db"
BACKUP_EXTENSION = ".backup"

# Export/Import settings
JSON_EXPORT_EXTENSION = ".json"
JSON_EXPORT_FILTER = "JSON Files (*.json);;All Files (*)"
DIGGS_IMPORT_FILTER = "SQLite Database (*.db *.sqlite);;All Files (*)"

# UI Constants
DEFAULT_WINDOW_WIDTH = 1200
DEFAULT_WINDOW_HEIGHT = 800
MIN_WINDOW_WIDTH = 800
MIN_WINDOW_HEIGHT = 600

# Plot settings
DEFAULT_DPI = 100
PLOT_BACKGROUND_COLOR = '#FFFFFF'
PLOT_GRID_COLOR = '#CCCCCC'
PLOT_TEXT_COLOR = '#000000'

# Color scheme settings
USE_HIGH_CONTRAST = False  # Can be toggled by user

# Logging settings
LOG_FILE_NAME = "strata_interpreter.log"
LOG_MAX_SIZE = 10 * 1024 * 1024  # 10 MB
LOG_BACKUP_COUNT = 5

# Calculation tolerances
FLOATING_POINT_TOLERANCE = 1e-10
ELEVATION_TOLERANCE = 0.01  # feet or meters

# Unit conversion factors
FEET_TO_METERS = 0.3048
METERS_TO_FEET = 3.28084
PSF_TO_PA = 47.88026
PA_TO_PSF = 0.02088543
PCF_TO_KNM3 = 0.1571

# Standard test methods
ASTM_STANDARDS = {
    'D422': 'Particle-Size Analysis of Soils',
    'D4318': 'Liquid Limit, Plastic Limit, and Plasticity Index of Soils',
    'D2166': 'Unconfined Compressive Strength of Cohesive Soil',
    'D3080': 'Direct Shear Test of Soils Under Consolidated Drained Conditions',
    'D4767': 'Consolidated Undrained Triaxial Compression Test',
    'D2435': 'One-Dimensional Consolidation Properties of Soils',
    'D5084': 'Measurement of Hydraulic Conductivity of Saturated Porous Materials'
}

# Quality metrics thresholds
CONFIDENCE_THRESHOLDS = {
    'high': 0.8,
    'medium': 0.6,
    'low': 0.4
}

# Default parameter ranges for validation
PARAMETER_RANGES = {
    'unit_weight': {'min': 80, 'max': 150, 'units': 'pcf'},
    'friction_angle': {'min': 15, 'max': 45, 'units': 'degrees'},
    'cohesion': {'min': 0, 'max': 5000, 'units': 'psf'},
    'modulus_elasticity': {'min': 1000, 'max': 100000, 'units': 'ksf'},
    'permeability': {'min': 1e-9, 'max': 1e-3, 'units': 'cm/s'},
    'preconsolidation_pressure': {'min': 500, 'max': 20000, 'units': 'psf'},
    'compression_index': {'min': 0.01, 'max': 2.0, 'units': 'dimensionless'},
    'coefficient_consolidation': {'min': 1e-5, 'max': 1e-1, 'units': 'in²/min'}
}

# File format versions
CURRENT_JSON_VERSION = "1.0.0"
SUPPORTED_JSON_VERSIONS = ["1.0.0"]

# Auto-save settings
AUTO_SAVE_INTERVAL = 300  # seconds (5 minutes)
BACKUP_RETENTION_DAYS = 30

# Performance settings
MAX_SAMPLES_PER_BOREHOLE = 1000
MAX_BOREHOLES_PER_PROJECT = 100
CALCULATION_TIMEOUT = 30  # seconds