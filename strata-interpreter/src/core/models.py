"""
Data models for geotechnical strata interpretation.

This module defines the core data structures used throughout the application,
including project metadata, exploration data, and design parameters.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum

class USCSClassification(Enum):
    """USCS soil classification types."""
    # Coarse-grained soils
    GW = "Well-graded gravel"
    GP = "Poorly graded gravel"
    GM = "Silty gravel"
    GC = "Clayey gravel"
    SW = "Well-graded sand"
    SP = "Poorly graded sand"
    SM = "Silty sand"
    SC = "Clayey sand"
    
    # Fine-grained soils
    ML = "Inorganic silt"
    CL = "Inorganic clay"
    OL = "Organic silt/clay"
    MH = "Inorganic silt (high plasticity)"
    CH = "Inorganic clay (high plasticity)"
    OH = "Organic clay/silt (high plasticity)"
    
    # Highly organic
    PT = "Peat"

class ParameterSource(Enum):
    """Source of design parameter values."""
    MANUAL = "manual"
    CALCULATED = "calculated"
    ESTIMATED = "estimated"

@dataclass
class Location:
    """Geographic location with coordinates and elevation."""
    x: float
    y: float
    elevation: float
    coordinate_system: str = "State Plane"

@dataclass
class GradationTest:
    """Gradation test results."""
    gravel_percent: Optional[float] = None
    sand_percent: Optional[float] = None
    fines_percent: Optional[float] = None
    d10: Optional[float] = None
    d30: Optional[float] = None
    d60: Optional[float] = None
    cu: Optional[float] = None  # Uniformity coefficient
    cc: Optional[float] = None  # Coefficient of curvature

@dataclass
class AtterbergLimits:
    """Atterberg limits test results."""
    liquid_limit: Optional[float] = None
    plastic_limit: Optional[float] = None
    plasticity_index: Optional[float] = None

@dataclass
class MoistureDensity:
    """Moisture and density test results."""
    natural_moisture: Optional[float] = None
    dry_density: Optional[float] = None
    wet_density: Optional[float] = None

@dataclass
class TriaxialTest:
    """Single triaxial test result."""
    confining_pressure: float
    peak_strength: float
    friction_angle: Optional[float] = None

@dataclass
class DirectShearTest:
    """Single direct shear test result."""
    normal_stress: float
    shear_strength: float

@dataclass
class StrengthTests:
    """Strength test results."""
    unconfined_compression: Optional[float] = None
    triaxial_tests: List[TriaxialTest] = field(default_factory=list)
    direct_shear: List[DirectShearTest] = field(default_factory=list)

@dataclass
class ConsolidationTests:
    """Consolidation test results."""
    preconsolidation_pressure: Optional[float] = None
    compression_index: Optional[float] = None
    recompression_index: Optional[float] = None
    coefficient_consolidation: Optional[float] = None

@dataclass
class PermeabilityTests:
    """Permeability test results."""
    horizontal_permeability: Optional[float] = None
    vertical_permeability: Optional[float] = None
    test_method: Optional[str] = None

@dataclass
class LaboratoryTests:
    """Complete laboratory test suite."""
    gradation: Optional[GradationTest] = None
    atterberg_limits: Optional[AtterbergLimits] = None
    moisture_density: Optional[MoistureDensity] = None
    strength_tests: Optional[StrengthTests] = None
    consolidation_tests: Optional[ConsolidationTests] = None
    permeability_tests: Optional[PermeabilityTests] = None

@dataclass
class FieldTests:
    """Field test results."""
    spt_n_value: Optional[float] = None
    field_moisture: Optional[float] = None
    penetration_resistance: Optional[float] = None

@dataclass
class Sample:
    """Soil sample with test results."""
    sample_id: str
    depth_top: float
    depth_bottom: float
    field_description: str
    uscs_classification: Optional[USCSClassification] = None
    field_tests: Optional[FieldTests] = None
    laboratory_tests: Optional[LaboratoryTests] = None

@dataclass
class DrillingInfo:
    """Drilling method and contractor information."""
    method: str
    date: datetime
    contractor: str

@dataclass
class Exploration:
    """Exploration/borehole information."""
    borehole_id: str
    location: Location
    drilling_info: DrillingInfo
    samples: List[Sample] = field(default_factory=list)

@dataclass
class DesignParameter:
    """Design parameter with calculation details."""
    value: float
    calculation_method: str
    source: ParameterSource
    confidence: float  # 0.0 to 1.0
    override_justification: Optional[str] = None

@dataclass
class DesignParameters:
    """Complete set of design parameters for a strata layer."""
    unit_weight: Optional[DesignParameter] = None
    friction_angle: Optional[DesignParameter] = None
    cohesion: Optional[DesignParameter] = None
    modulus_elasticity: Optional[DesignParameter] = None
    permeability_horizontal: Optional[DesignParameter] = None
    permeability_vertical: Optional[DesignParameter] = None
    preconsolidation_pressure: Optional[DesignParameter] = None
    compression_index: Optional[DesignParameter] = None
    coefficient_consolidation: Optional[DesignParameter] = None

@dataclass
class SupportingData:
    """Supporting data for strata interpretation."""
    samples_used: List[str]  # List of sample IDs
    calculation_details: Dict[str, Any]
    references: List[str]  # Citations

@dataclass
class StrataLayer:
    """Interpreted soil strata layer."""
    strata_id: str
    top_elevation: float
    bottom_elevation: float
    soil_type: str
    uscs_classification: USCSClassification
    design_parameters: DesignParameters
    supporting_data: SupportingData

@dataclass
class ProjectMetadata:
    """Project metadata and information."""
    project_name: str
    project_number: str
    date_created: datetime
    created_by: str
    version: str
    coordinate_system: str

@dataclass
class CalculationMethods:
    """Calculation methods and validation results."""
    equations_used: Dict[str, Any]
    validation_results: Dict[str, Any]
    quality_metrics: Dict[str, Any]

@dataclass
class SoilProfile:
    """Complete soil profile project."""
    project_metadata: ProjectMetadata
    explorations: Dict[str, Exploration]
    interpreted_strata: List[StrataLayer]
    calculation_methods: CalculationMethods