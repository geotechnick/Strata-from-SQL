"""
Data validation functions for geotechnical parameters and database integrity.

This module provides comprehensive validation for soil test data, design parameters,
and data integrity checks throughout the application.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import numpy as np
from core.models import USCSClassification, ParameterSource
from utils.constants import PARAMETER_RANGES, FLOATING_POINT_TOLERANCE

logger = logging.getLogger(__name__)

class ValidationSeverity(Enum):
    """Validation result severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class ValidationResult:
    """Result of a validation check."""
    is_valid: bool
    severity: ValidationSeverity
    message: str
    field_name: Optional[str] = None
    suggested_value: Optional[Any] = None

class GeotechnicalValidator:
    """Comprehensive validation for geotechnical data."""
    
    def __init__(self):
        """Initialize validator with standard ranges and rules."""
        self.parameter_ranges = PARAMETER_RANGES
        self.validation_results: List[ValidationResult] = []
    
    def clear_results(self):
        """Clear previous validation results."""
        self.validation_results.clear()
    
    def add_result(self, result: ValidationResult):
        """Add validation result to the list."""
        self.validation_results.append(result)
    
    def get_results(self) -> List[ValidationResult]:
        """Get all validation results."""
        return self.validation_results.copy()
    
    def has_errors(self) -> bool:
        """Check if any validation errors exist."""
        return any(r.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL] 
                  for r in self.validation_results)
    
    def has_warnings(self) -> bool:
        """Check if any validation warnings exist."""
        return any(r.severity == ValidationSeverity.WARNING 
                  for r in self.validation_results)
    
    def validate_coordinate(self, x: float, y: float, coordinate_system: str = "State Plane") -> bool:
        """
        Validate coordinate values.
        
        Args:
            x: X coordinate
            y: Y coordinate
            coordinate_system: Coordinate system name
            
        Returns:
            True if coordinates are valid
        """
        is_valid = True
        
        # Check for reasonable coordinate ranges
        if coordinate_system.lower() == "state plane":
            if not (0 <= x <= 3000000):  # Reasonable state plane range
                self.add_result(ValidationResult(
                    is_valid=False,
                    severity=ValidationSeverity.WARNING,
                    message=f"X coordinate {x} may be outside typical State Plane range",
                    field_name="x_coordinate"
                ))
                is_valid = False
            
            if not (0 <= y <= 3000000):
                self.add_result(ValidationResult(
                    is_valid=False,
                    severity=ValidationSeverity.WARNING,
                    message=f"Y coordinate {y} may be outside typical State Plane range",
                    field_name="y_coordinate"
                ))
                is_valid = False
        
        return is_valid
    
    def validate_elevation(self, elevation: float) -> bool:
        """
        Validate elevation value.
        
        Args:
            elevation: Elevation value
            
        Returns:
            True if elevation is valid
        """
        # Check for reasonable elevation range
        if not (-1000 <= elevation <= 15000):  # Reasonable elevation range in feet
            self.add_result(ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.WARNING,
                message=f"Elevation {elevation} may be outside reasonable range (-1000 to 15000 ft)",
                field_name="elevation"
            ))
            return False
        
        return True
    
    def validate_depth_interval(self, depth_top: float, depth_bottom: float) -> bool:
        """
        Validate depth interval.
        
        Args:
            depth_top: Top depth
            depth_bottom: Bottom depth
            
        Returns:
            True if depth interval is valid
        """
        is_valid = True
        
        # Check depth order
        if depth_top >= depth_bottom:
            self.add_result(ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message=f"Top depth ({depth_top}) must be less than bottom depth ({depth_bottom})",
                field_name="depth_interval"
            ))
            is_valid = False
        
        # Check for negative depths
        if depth_top < 0:
            self.add_result(ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message=f"Top depth cannot be negative: {depth_top}",
                field_name="depth_top"
            ))
            is_valid = False
        
        # Check for excessive depths
        if depth_bottom > 500:  # 500 feet is quite deep for most projects
            self.add_result(ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.WARNING,
                message=f"Bottom depth ({depth_bottom}) is unusually deep",
                field_name="depth_bottom"
            ))
        
        return is_valid
    
    def validate_gradation_data(self, gradation: Dict[str, Any]) -> bool:
        """
        Validate gradation test data.
        
        Args:
            gradation: Gradation test data dictionary
            
        Returns:
            True if gradation data is valid
        """
        is_valid = True
        
        # Check percentages sum to 100
        percentages = []
        for key in ['gravel_percent', 'sand_percent', 'fines_percent']:
            if key in gradation and gradation[key] is not None:
                value = gradation[key]
                if not (0 <= value <= 100):
                    self.add_result(ValidationResult(
                        is_valid=False,
                        severity=ValidationSeverity.ERROR,
                        message=f"{key} must be between 0 and 100: {value}",
                        field_name=key
                    ))
                    is_valid = False
                else:
                    percentages.append(value)
        
        # Check if percentages sum to approximately 100
        if len(percentages) == 3:
            total = sum(percentages)
            if abs(total - 100.0) > 1.0:  # Allow 1% tolerance
                self.add_result(ValidationResult(
                    is_valid=False,
                    severity=ValidationSeverity.WARNING,
                    message=f"Gradation percentages sum to {total}%, should be 100%",
                    field_name="gradation_total"
                ))
        
        # Validate grain size diameters
        d_values = ['d10', 'd30', 'd60']
        d_sizes = {}
        for d_val in d_values:
            if d_val in gradation and gradation[d_val] is not None:
                value = gradation[d_val]
                if value <= 0:
                    self.add_result(ValidationResult(
                        is_valid=False,
                        severity=ValidationSeverity.ERROR,
                        message=f"{d_val} must be positive: {value}",
                        field_name=d_val
                    ))
                    is_valid = False
                else:
                    d_sizes[d_val] = value
        
        # Check grain size order: d10 < d30 < d60
        if len(d_sizes) >= 2:
            sizes = [(k, v) for k, v in d_sizes.items()]
            sizes.sort(key=lambda x: int(x[0][1:]))  # Sort by number
            
            for i in range(len(sizes) - 1):
                if sizes[i][1] >= sizes[i + 1][1]:
                    self.add_result(ValidationResult(
                        is_valid=False,
                        severity=ValidationSeverity.ERROR,
                        message=f"{sizes[i][0]} ({sizes[i][1]}) should be less than {sizes[i+1][0]} ({sizes[i+1][1]})",
                        field_name="grain_sizes"
                    ))
                    is_valid = False
        
        # Validate uniformity coefficient (Cu = d60/d10)
        if 'cu' in gradation and gradation['cu'] is not None:
            cu = gradation['cu']
            if cu < 1:
                self.add_result(ValidationResult(
                    is_valid=False,
                    severity=ValidationSeverity.ERROR,
                    message=f"Uniformity coefficient (Cu) must be ≥ 1: {cu}",
                    field_name="cu"
                ))
                is_valid = False
            
            # Check calculated vs provided Cu
            if 'd10' in d_sizes and 'd60' in d_sizes:
                calculated_cu = d_sizes['d60'] / d_sizes['d10']
                if abs(cu - calculated_cu) > 0.1 * calculated_cu:  # 10% tolerance
                    self.add_result(ValidationResult(
                        is_valid=False,
                        severity=ValidationSeverity.WARNING,
                        message=f"Provided Cu ({cu}) differs from calculated Cu ({calculated_cu:.2f})",
                        field_name="cu",
                        suggested_value=calculated_cu
                    ))
        
        # Validate coefficient of curvature (Cc = d30²/(d60*d10))
        if 'cc' in gradation and gradation['cc'] is not None:
            cc = gradation['cc']
            if cc <= 0:
                self.add_result(ValidationResult(
                    is_valid=False,
                    severity=ValidationSeverity.ERROR,
                    message=f"Coefficient of curvature (Cc) must be positive: {cc}",
                    field_name="cc"
                ))
                is_valid = False
            
            # Check calculated vs provided Cc
            if all(d in d_sizes for d in ['d10', 'd30', 'd60']):
                calculated_cc = (d_sizes['d30'] ** 2) / (d_sizes['d60'] * d_sizes['d10'])
                if abs(cc - calculated_cc) > 0.1 * calculated_cc:  # 10% tolerance
                    self.add_result(ValidationResult(
                        is_valid=False,
                        severity=ValidationSeverity.WARNING,
                        message=f"Provided Cc ({cc}) differs from calculated Cc ({calculated_cc:.3f})",
                        field_name="cc",
                        suggested_value=calculated_cc
                    ))
        
        return is_valid
    
    def validate_atterberg_limits(self, atterberg: Dict[str, Any]) -> bool:
        """
        Validate Atterberg limits data.
        
        Args:
            atterberg: Atterberg limits data dictionary
            
        Returns:
            True if Atterberg limits are valid
        """
        is_valid = True
        
        ll = atterberg.get('liquid_limit')
        pl = atterberg.get('plastic_limit')
        pi = atterberg.get('plasticity_index')
        
        # Validate individual limits
        for limit_name, limit_value in [('liquid_limit', ll), ('plastic_limit', pl)]:
            if limit_value is not None:
                if not (0 <= limit_value <= 200):
                    self.add_result(ValidationResult(
                        is_valid=False,
                        severity=ValidationSeverity.ERROR,
                        message=f"{limit_name} must be between 0 and 200: {limit_value}",
                        field_name=limit_name
                    ))
                    is_valid = False
        
        # Check relationship: PL ≤ LL
        if ll is not None and pl is not None:
            if pl > ll:
                self.add_result(ValidationResult(
                    is_valid=False,
                    severity=ValidationSeverity.ERROR,
                    message=f"Plastic limit ({pl}) cannot exceed liquid limit ({ll})",
                    field_name="atterberg_limits"
                ))
                is_valid = False
            
            # Check plasticity index calculation
            calculated_pi = ll - pl
            if pi is not None:
                if abs(pi - calculated_pi) > 1.0:  # 1% tolerance
                    self.add_result(ValidationResult(
                        is_valid=False,
                        severity=ValidationSeverity.WARNING,
                        message=f"Provided PI ({pi}) differs from calculated PI ({calculated_pi})",
                        field_name="plasticity_index",
                        suggested_value=calculated_pi
                    ))
        
        return is_valid
    
    def validate_design_parameter(self, parameter_name: str, value: float, 
                                source: ParameterSource, confidence: float) -> bool:
        """
        Validate design parameter value and metadata.
        
        Args:
            parameter_name: Name of the parameter
            value: Parameter value
            source: Source of the parameter
            confidence: Confidence level (0.0 to 1.0)
            
        Returns:
            True if parameter is valid
        """
        is_valid = True
        
        # Validate confidence level
        if not (0.0 <= confidence <= 1.0):
            self.add_result(ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message=f"Confidence must be between 0.0 and 1.0: {confidence}",
                field_name=f"{parameter_name}_confidence"
            ))
            is_valid = False
        
        # Check parameter ranges
        if parameter_name in self.parameter_ranges:
            param_range = self.parameter_ranges[parameter_name]
            min_val = param_range['min']
            max_val = param_range['max']
            units = param_range['units']
            
            if not (min_val <= value <= max_val):
                severity = ValidationSeverity.ERROR if (value < min_val * 0.5 or value > max_val * 2) else ValidationSeverity.WARNING
                self.add_result(ValidationResult(
                    is_valid=False,
                    severity=severity,
                    message=f"{parameter_name} ({value} {units}) outside typical range ({min_val}-{max_val} {units})",
                    field_name=parameter_name
                ))
                if severity == ValidationSeverity.ERROR:
                    is_valid = False
        
        # Validate source-specific requirements
        if source == ParameterSource.MANUAL and confidence < 0.8:
            self.add_result(ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.WARNING,
                message=f"Manual parameter {parameter_name} has low confidence ({confidence})",
                field_name=f"{parameter_name}_confidence"
            ))
        
        return is_valid
    
    def validate_uscs_classification(self, classification: str, 
                                   gradation: Optional[Dict] = None,
                                   atterberg: Optional[Dict] = None) -> bool:
        """
        Validate USCS classification against test data.
        
        Args:
            classification: USCS classification string
            gradation: Gradation test data
            atterberg: Atterberg limits data
            
        Returns:
            True if classification is consistent with test data
        """
        is_valid = True
        
        # Check if classification is valid USCS type
        try:
            uscs_enum = USCSClassification(classification)
        except ValueError:
            self.add_result(ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message=f"Invalid USCS classification: {classification}",
                field_name="uscs_classification"
            ))
            return False
        
        # Check consistency with gradation data
        if gradation:
            fines = gradation.get('fines_percent', 0)
            
            # Coarse-grained soils should have < 50% fines
            coarse_grained = ['GW', 'GP', 'GM', 'GC', 'SW', 'SP', 'SM', 'SC']
            if classification in coarse_grained and fines >= 50:
                self.add_result(ValidationResult(
                    is_valid=False,
                    severity=ValidationSeverity.WARNING,
                    message=f"Classification {classification} inconsistent with {fines}% fines (should be <50%)",
                    field_name="uscs_classification"
                ))
            
            # Fine-grained soils should have ≥ 50% fines
            fine_grained = ['ML', 'CL', 'OL', 'MH', 'CH', 'OH']
            if classification in fine_grained and fines < 50:
                self.add_result(ValidationResult(
                    is_valid=False,
                    severity=ValidationSeverity.WARNING,
                    message=f"Classification {classification} inconsistent with {fines}% fines (should be ≥50%)",
                    field_name="uscs_classification"
                ))
        
        # Check consistency with Atterberg limits
        if atterberg and classification in ['CL', 'CH', 'ML', 'MH', 'OL', 'OH']:
            ll = atterberg.get('liquid_limit')
            pi = atterberg.get('plasticity_index')
            
            if ll is not None:
                # High plasticity: LL ≥ 50
                if classification in ['CH', 'MH', 'OH'] and ll < 50:
                    self.add_result(ValidationResult(
                        is_valid=False,
                        severity=ValidationSeverity.WARNING,
                        message=f"High plasticity classification {classification} with LL={ll} (<50)",
                        field_name="uscs_classification"
                    ))
                
                # Low plasticity: LL < 50
                if classification in ['CL', 'ML', 'OL'] and ll >= 50:
                    self.add_result(ValidationResult(
                        is_valid=False,
                        severity=ValidationSeverity.WARNING,
                        message=f"Low plasticity classification {classification} with LL={ll} (≥50)",
                        field_name="uscs_classification"
                    ))
        
        return is_valid
    
    def validate_strata_geometry(self, layers: List[Dict]) -> bool:
        """
        Validate strata layer geometry for overlaps and gaps.
        
        Args:
            layers: List of strata layer dictionaries
            
        Returns:
            True if geometry is valid
        """
        is_valid = True
        
        if len(layers) < 2:
            return True
        
        # Sort layers by top elevation (descending)
        sorted_layers = sorted(layers, key=lambda x: x['top_elevation'], reverse=True)
        
        for i in range(len(sorted_layers) - 1):
            current_layer = sorted_layers[i]
            next_layer = sorted_layers[i + 1]
            
            current_bottom = current_layer['bottom_elevation']
            next_top = next_layer['top_elevation']
            
            # Check for gaps
            if abs(current_bottom - next_top) > FLOATING_POINT_TOLERANCE:
                if current_bottom > next_top:
                    # Gap between layers
                    gap_size = current_bottom - next_top
                    self.add_result(ValidationResult(
                        is_valid=False,
                        severity=ValidationSeverity.WARNING,
                        message=f"Gap of {gap_size:.2f} ft between layers at elevation {current_bottom:.2f}",
                        field_name="strata_geometry"
                    ))
                else:
                    # Overlap between layers
                    overlap_size = next_top - current_bottom
                    self.add_result(ValidationResult(
                        is_valid=False,
                        severity=ValidationSeverity.ERROR,
                        message=f"Overlap of {overlap_size:.2f} ft between layers at elevation {next_top:.2f}",
                        field_name="strata_geometry"
                    ))
                    is_valid = False
        
        return is_valid

# Convenience functions
def validate_sample_data(sample_data: Dict[str, Any]) -> Tuple[bool, List[ValidationResult]]:
    """
    Validate complete sample data.
    
    Args:
        sample_data: Sample data dictionary
        
    Returns:
        Tuple of (is_valid, validation_results)
    """
    validator = GeotechnicalValidator()
    
    # Validate depth interval
    if 'depth_top' in sample_data and 'depth_bottom' in sample_data:
        validator.validate_depth_interval(sample_data['depth_top'], sample_data['depth_bottom'])
    
    # Validate laboratory tests
    lab_tests = sample_data.get('laboratory_tests', {})
    
    if 'gradation' in lab_tests:
        validator.validate_gradation_data(lab_tests['gradation'])
    
    if 'atterberg_limits' in lab_tests:
        validator.validate_atterberg_limits(lab_tests['atterberg_limits'])
    
    # Validate USCS classification
    if 'uscs_classification' in sample_data:
        validator.validate_uscs_classification(
            sample_data['uscs_classification'],
            lab_tests.get('gradation'),
            lab_tests.get('atterberg_limits')
        )
    
    return not validator.has_errors(), validator.get_results()

def validate_project_data(project_data: Dict[str, Any]) -> Tuple[bool, List[ValidationResult]]:
    """
    Validate complete project data.
    
    Args:
        project_data: Project data dictionary
        
    Returns:
        Tuple of (is_valid, validation_results)
    """
    validator = GeotechnicalValidator()
    
    # Validate project metadata
    if not project_data.get('project_name'):
        validator.add_result(ValidationResult(
            is_valid=False,
            severity=ValidationSeverity.ERROR,
            message="Project name is required",
            field_name="project_name"
        ))
    
    if not project_data.get('project_number'):
        validator.add_result(ValidationResult(
            is_valid=False,
            severity=ValidationSeverity.ERROR,
            message="Project number is required",
            field_name="project_number"
        ))
    
    # Validate explorations
    explorations = project_data.get('explorations', {})
    for borehole_id, borehole_data in explorations.items():
        location = borehole_data.get('location', {})
        if 'x' in location and 'y' in location:
            validator.validate_coordinate(
                location['x'], 
                location['y'],
                location.get('coordinate_system', 'State Plane')
            )
        
        if 'elevation' in location:
            validator.validate_elevation(location['elevation'])
        
        # Validate samples
        for sample in borehole_data.get('samples', []):
            sample_valid, sample_results = validate_sample_data(sample)
            validator.validation_results.extend(sample_results)
    
    # Validate strata geometry
    strata_layers = project_data.get('interpreted_strata', [])
    if strata_layers:
        validator.validate_strata_geometry(strata_layers)
    
    return not validator.has_errors(), validator.get_results()