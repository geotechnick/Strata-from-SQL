"""
Parameter calculation engine for geotechnical design parameters.

This module implements calculation methods for all design parameters based on
laboratory test results and empirical correlations.
"""

import logging
import math
from typing import Dict, List, Optional, Tuple, Any, Union
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
import numpy as np
from core.models import ParameterSource, USCSClassification
from utils.constants import PARAMETER_RANGES

logger = logging.getLogger(__name__)

class CalculationMethod(Enum):
    """Available calculation methods for each parameter."""
    # Unit Weight
    SATURATED_UNIT_WEIGHT = "saturated_unit_weight"
    DRY_UNIT_WEIGHT = "dry_unit_weight"
    SUBMERGED_UNIT_WEIGHT = "submerged_unit_weight"
    
    # Friction Angle
    SPT_CORRELATION = "spt_correlation"
    DIRECT_SHEAR = "direct_shear"
    TRIAXIAL_DRAINED = "triaxial_drained"
    
    # Undrained Shear Strength  
    UNCONFINED_COMPRESSION = "unconfined_compression"
    TRIAXIAL_UNDRAINED = "triaxial_undrained"
    FIELD_VANE = "field_vane"
    
    # Modulus of Elasticity
    EMPIRICAL_CORRELATION = "empirical_correlation"
    LABORATORY_TEST = "laboratory_test"
    
    # Permeability
    HAZEN_FORMULA = "hazen_formula"
    KOZENY_CARMAN = "kozeny_carman"
    LABORATORY_PERMEABILITY = "laboratory_permeability"
    
    # Consolidation
    CASAGRANDE_METHOD = "casagrande_method"
    STRAIN_ENERGY_METHOD = "strain_energy_method"

@dataclass
class CalculationResult:
    """Result of a parameter calculation."""
    value: float
    method: CalculationMethod
    confidence: float
    source_data: Dict[str, Any]
    references: List[str]
    notes: str = ""

@dataclass
class CalculationInput:
    """Input data for parameter calculations."""
    test_data: Dict[str, Any]
    sample_depth: float
    uscs_classification: USCSClassification
    effective_stress: Optional[float] = None

class ParameterCalculator(ABC):
    """Abstract base class for parameter calculators."""
    
    @abstractmethod
    def calculate(self, inputs: CalculationInput) -> List[CalculationResult]:
        """Calculate parameter using available methods."""
        pass
    
    @abstractmethod
    def get_available_methods(self, inputs: CalculationInput) -> List[CalculationMethod]:
        """Get available calculation methods for given inputs."""
        pass

class UnitWeightCalculator(ParameterCalculator):
    """Calculator for unit weight parameters."""
    
    def calculate(self, inputs: CalculationInput) -> List[CalculationResult]:
        """Calculate unit weight using available data."""
        results = []
        
        moisture_density = inputs.test_data.get('moisture_density', {})
        
        # Dry unit weight calculation
        dry_density = moisture_density.get('dry_density')
        if dry_density is not None:
            results.append(CalculationResult(
                value=dry_density,
                method=CalculationMethod.DRY_UNIT_WEIGHT,
                confidence=0.95,
                source_data={'dry_density': dry_density},
                references=['ASTM D7263'],
                notes="Direct measurement from laboratory test"
            ))
        
        # Saturated unit weight calculation
        wet_density = moisture_density.get('wet_density')
        natural_moisture = moisture_density.get('natural_moisture')
        
        if wet_density is not None:
            results.append(CalculationResult(
                value=wet_density,
                method=CalculationMethod.SATURATED_UNIT_WEIGHT,
                confidence=0.90,
                source_data={'wet_density': wet_density},
                references=['ASTM D7263'],
                notes="Measured wet density"
            ))
        elif dry_density is not None and natural_moisture is not None:
            # Calculate wet density from dry density and moisture content
            wet_density_calc = dry_density * (1 + natural_moisture / 100)
            results.append(CalculationResult(
                value=wet_density_calc,
                method=CalculationMethod.SATURATED_UNIT_WEIGHT,
                confidence=0.85,
                source_data={'dry_density': dry_density, 'natural_moisture': natural_moisture},
                references=['Soil Mechanics Fundamentals'],
                notes=f"Calculated from dry density and moisture content"
            ))
        
        # Submerged unit weight (saturated - water)
        if results:
            saturated_weight = max(r.value for r in results if r.method == CalculationMethod.SATURATED_UNIT_WEIGHT)
            submerged_weight = saturated_weight - 62.4  # Water unit weight in pcf
            results.append(CalculationResult(
                value=submerged_weight,
                method=CalculationMethod.SUBMERGED_UNIT_WEIGHT,
                confidence=0.90,
                source_data={'saturated_weight': saturated_weight},
                references=['Soil Mechanics Fundamentals'],
                notes="Saturated unit weight minus water unit weight"
            ))
        
        return results
    
    def get_available_methods(self, inputs: CalculationInput) -> List[CalculationMethod]:
        """Get available unit weight calculation methods."""
        methods = []
        moisture_density = inputs.test_data.get('moisture_density', {})
        
        if moisture_density.get('dry_density') is not None:
            methods.append(CalculationMethod.DRY_UNIT_WEIGHT)
        
        if (moisture_density.get('wet_density') is not None or 
            (moisture_density.get('dry_density') is not None and 
             moisture_density.get('natural_moisture') is not None)):
            methods.extend([
                CalculationMethod.SATURATED_UNIT_WEIGHT,
                CalculationMethod.SUBMERGED_UNIT_WEIGHT
            ])
        
        return methods

class FrictionAngleCalculator(ParameterCalculator):
    """Calculator for friction angle parameters."""
    
    def calculate(self, inputs: CalculationInput) -> List[CalculationResult]:
        """Calculate friction angle using available data."""
        results = []
        
        # SPT correlation for granular soils
        field_tests = inputs.test_data.get('field_tests', {})
        spt_n_value = field_tests.get('spt_n_value')
        
        if spt_n_value is not None and self._is_granular(inputs.uscs_classification):
            # Peck, Hanson, and Thornburn correlation
            phi = 28 + 15 * math.log10(spt_n_value) if spt_n_value > 0 else 28
            phi = min(phi, 45)  # Cap at 45 degrees
            
            confidence = 0.7 if spt_n_value >= 10 else 0.6
            results.append(CalculationResult(
                value=phi,
                method=CalculationMethod.SPT_CORRELATION,
                confidence=confidence,
                source_data={'spt_n_value': spt_n_value},
                references=['Peck, Hanson, and Thornburn (1974)'],
                notes=f"φ = 28 + 15*log10(N) for N={spt_n_value}"
            ))
        
        # Direct shear test
        strength_tests = inputs.test_data.get('strength_tests', {})
        direct_shear = strength_tests.get('direct_shear', [])
        
        if len(direct_shear) >= 2:
            # Linear regression to find friction angle
            normal_stresses = [test['normal_stress'] for test in direct_shear]
            shear_strengths = [test['shear_strength'] for test in direct_shear]
            
            # Calculate friction angle from slope
            phi = self._calculate_friction_angle_from_shear(normal_stresses, shear_strengths)
            
            if phi is not None:
                results.append(CalculationResult(
                    value=phi,
                    method=CalculationMethod.DIRECT_SHEAR,
                    confidence=0.90,
                    source_data={'direct_shear_tests': direct_shear},
                    references=['ASTM D3080'],
                    notes=f"Calculated from {len(direct_shear)} direct shear tests"
                ))
        
        # Triaxial test (drained)
        triaxial_tests = strength_tests.get('triaxial_tests', [])
        drained_tests = [t for t in triaxial_tests if 'friction_angle' in t]
        
        if drained_tests:
            # Average friction angle from multiple tests
            avg_phi = sum(t['friction_angle'] for t in drained_tests) / len(drained_tests)
            results.append(CalculationResult(
                value=avg_phi,
                method=CalculationMethod.TRIAXIAL_DRAINED,
                confidence=0.95,
                source_data={'triaxial_tests': drained_tests},
                references=['ASTM D4767'],
                notes=f"Average of {len(drained_tests)} drained triaxial tests"
            ))
        
        return results
    
    def get_available_methods(self, inputs: CalculationInput) -> List[CalculationMethod]:
        """Get available friction angle calculation methods."""
        methods = []
        
        # Check for SPT data
        field_tests = inputs.test_data.get('field_tests', {})
        if (field_tests.get('spt_n_value') is not None and 
            self._is_granular(inputs.uscs_classification)):
            methods.append(CalculationMethod.SPT_CORRELATION)
        
        # Check for direct shear data
        strength_tests = inputs.test_data.get('strength_tests', {})
        if len(strength_tests.get('direct_shear', [])) >= 2:
            methods.append(CalculationMethod.DIRECT_SHEAR)
        
        # Check for triaxial data
        triaxial_tests = strength_tests.get('triaxial_tests', [])
        if any('friction_angle' in t for t in triaxial_tests):
            methods.append(CalculationMethod.TRIAXIAL_DRAINED)
        
        return methods
    
    def _is_granular(self, classification: USCSClassification) -> bool:
        """Check if soil is granular."""
        granular_types = {
            USCSClassification.GW, USCSClassification.GP, USCSClassification.GM,
            USCSClassification.GC, USCSClassification.SW, USCSClassification.SP,
            USCSClassification.SM, USCSClassification.SC
        }
        return classification in granular_types
    
    def _calculate_friction_angle_from_shear(self, normal_stresses: List[float], 
                                           shear_strengths: List[float]) -> Optional[float]:
        """Calculate friction angle from direct shear test data."""
        try:
            # Linear regression: τ = c + σ * tan(φ)
            n = len(normal_stresses)
            if n < 2:
                return None
            
            sum_x = sum(normal_stresses)
            sum_y = sum(shear_strengths)
            sum_xy = sum(x * y for x, y in zip(normal_stresses, shear_strengths))
            sum_x2 = sum(x * x for x in normal_stresses)
            
            # Calculate slope (tan φ)
            denominator = n * sum_x2 - sum_x * sum_x
            if abs(denominator) < 1e-10:
                return None
            
            slope = (n * sum_xy - sum_x * sum_y) / denominator
            phi = math.degrees(math.atan(slope))
            
            return max(0, min(phi, 50))  # Reasonable range
            
        except Exception as e:
            logger.error(f"Error calculating friction angle: {e}")
            return None

class UndrainedShearStrengthCalculator(ParameterCalculator):
    """Calculator for undrained shear strength."""
    
    def calculate(self, inputs: CalculationInput) -> List[CalculationResult]:
        """Calculate undrained shear strength using available data."""
        results = []
        
        strength_tests = inputs.test_data.get('strength_tests', {})
        
        # Unconfined compression test
        unconfined = strength_tests.get('unconfined_compression')
        if unconfined is not None:
            # Su = qu / 2
            su = unconfined / 2
            results.append(CalculationResult(
                value=su,
                method=CalculationMethod.UNCONFINED_COMPRESSION,
                confidence=0.85,
                source_data={'unconfined_compression': unconfined},
                references=['ASTM D2166'],
                notes=f"Su = qu/2 = {unconfined}/2"
            ))
        
        # Triaxial undrained test
        triaxial_tests = strength_tests.get('triaxial_tests', [])
        undrained_tests = [t for t in triaxial_tests if 'peak_strength' in t]
        
        if undrained_tests:
            # Average undrained strength
            avg_su = sum(t['peak_strength'] for t in undrained_tests) / len(undrained_tests)
            results.append(CalculationResult(
                value=avg_su,
                method=CalculationMethod.TRIAXIAL_UNDRAINED,
                confidence=0.90,
                source_data={'triaxial_tests': undrained_tests},
                references=['ASTM D4767'],
                notes=f"Average of {len(undrained_tests)} undrained triaxial tests"
            ))
        
        return results
    
    def get_available_methods(self, inputs: CalculationInput) -> List[CalculationMethod]:
        """Get available undrained shear strength calculation methods."""
        methods = []
        
        strength_tests = inputs.test_data.get('strength_tests', {})
        
        if strength_tests.get('unconfined_compression') is not None:
            methods.append(CalculationMethod.UNCONFINED_COMPRESSION)
        
        triaxial_tests = strength_tests.get('triaxial_tests', [])
        if any('peak_strength' in t for t in triaxial_tests):
            methods.append(CalculationMethod.TRIAXIAL_UNDRAINED)
        
        return methods

class ModulusElasticityCalculator(ParameterCalculator):
    """Calculator for modulus of elasticity."""
    
    def calculate(self, inputs: CalculationInput) -> List[CalculationResult]:
        """Calculate modulus of elasticity using correlations."""
        results = []
        
        # Empirical correlation with SPT
        field_tests = inputs.test_data.get('field_tests', {})
        spt_n_value = field_tests.get('spt_n_value')
        
        if spt_n_value is not None:
            # Correlation depends on soil type
            if self._is_granular(inputs.uscs_classification):
                # E = 500 * N (ksf) for granular soils
                modulus = 500 * spt_n_value
                confidence = 0.6
                note = "Empirical correlation for granular soils: E = 500*N"
            else:
                # E = 300 * N (ksf) for fine-grained soils  
                modulus = 300 * spt_n_value
                confidence = 0.5
                note = "Empirical correlation for fine-grained soils: E = 300*N"
            
            results.append(CalculationResult(
                value=modulus,
                method=CalculationMethod.EMPIRICAL_CORRELATION,
                confidence=confidence,
                source_data={'spt_n_value': spt_n_value},
                references=['Bowles (1996)'],
                notes=note
            ))
        
        # Correlation with unconfined compression
        strength_tests = inputs.test_data.get('strength_tests', {})
        unconfined = strength_tests.get('unconfined_compression')
        
        if unconfined is not None and not self._is_granular(inputs.uscs_classification):
            # E = 100 to 500 * qu for clay soils
            modulus = 300 * unconfined  # Use middle value
            results.append(CalculationResult(
                value=modulus,
                method=CalculationMethod.EMPIRICAL_CORRELATION,
                confidence=0.65,
                source_data={'unconfined_compression': unconfined},
                references=['Duncan and Buchignani (1976)'],
                notes=f"E = 300*qu for clay soils"
            ))
        
        return results
    
    def get_available_methods(self, inputs: CalculationInput) -> List[CalculationMethod]:
        """Get available modulus calculation methods."""
        methods = []
        
        field_tests = inputs.test_data.get('field_tests', {})
        if field_tests.get('spt_n_value') is not None:
            methods.append(CalculationMethod.EMPIRICAL_CORRELATION)
        
        strength_tests = inputs.test_data.get('strength_tests', {})
        if (strength_tests.get('unconfined_compression') is not None and
            not self._is_granular(inputs.uscs_classification)):
            methods.append(CalculationMethod.EMPIRICAL_CORRELATION)
        
        return methods
    
    def _is_granular(self, classification: USCSClassification) -> bool:
        """Check if soil is granular."""
        granular_types = {
            USCSClassification.GW, USCSClassification.GP, USCSClassification.GM,
            USCSClassification.GC, USCSClassification.SW, USCSClassification.SP,
            USCSClassification.SM, USCSClassification.SC
        }
        return classification in granular_types

class PermeabilityCalculator(ParameterCalculator):
    """Calculator for hydraulic conductivity/permeability."""
    
    def calculate(self, inputs: CalculationInput) -> List[CalculationResult]:
        """Calculate permeability using available data."""
        results = []
        
        # Laboratory permeability test
        permeability_tests = inputs.test_data.get('permeability_tests', {})
        
        lab_k_h = permeability_tests.get('horizontal_permeability')
        if lab_k_h is not None:
            results.append(CalculationResult(
                value=lab_k_h,
                method=CalculationMethod.LABORATORY_PERMEABILITY,
                confidence=0.90,
                source_data={'horizontal_permeability': lab_k_h},
                references=['ASTM D5084'],
                notes="Direct laboratory measurement (horizontal)"
            ))
        
        lab_k_v = permeability_tests.get('vertical_permeability')
        if lab_k_v is not None:
            results.append(CalculationResult(
                value=lab_k_v,
                method=CalculationMethod.LABORATORY_PERMEABILITY,
                confidence=0.90,
                source_data={'vertical_permeability': lab_k_v},
                references=['ASTM D5084'],
                notes="Direct laboratory measurement (vertical)"
            ))
        
        # Hazen formula for clean sands
        gradation = inputs.test_data.get('gradation', {})
        d10 = gradation.get('d10')
        cu = gradation.get('cu')
        
        if (d10 is not None and self._is_clean_sand(inputs.uscs_classification, gradation)):
            # k = C * d10² (cm/s), where C ≈ 100
            k_hazen = 100 * (d10 ** 2)  # d10 in mm, result in cm/s
            k_hazen = k_hazen / 10  # Convert to cm/s
            
            confidence = 0.7 if cu is not None and cu < 5 else 0.6
            results.append(CalculationResult(
                value=k_hazen,
                method=CalculationMethod.HAZEN_FORMULA,
                confidence=confidence,
                source_data={'d10': d10, 'cu': cu},
                references=['Hazen (1892)'],
                notes=f"k = 100*d10² for clean sand, d10={d10}mm"
            ))
        
        # Kozeny-Carman equation (more complex, requires porosity)
        if d10 is not None and self._has_gradation_data(gradation):
            # Simplified Kozeny-Carman for estimation
            porosity = self._estimate_porosity(inputs.uscs_classification)
            k_kc = self._kozeny_carman_estimate(d10, porosity)
            
            results.append(CalculationResult(
                value=k_kc,
                method=CalculationMethod.KOZENY_CARMAN,
                confidence=0.5,
                source_data={'d10': d10, 'estimated_porosity': porosity},
                references=['Kozeny (1927), Carman (1937)'],
                notes=f"Simplified Kozeny-Carman with estimated porosity={porosity:.2f}"
            ))
        
        return results
    
    def get_available_methods(self, inputs: CalculationInput) -> List[CalculationMethod]:
        """Get available permeability calculation methods."""
        methods = []
        
        permeability_tests = inputs.test_data.get('permeability_tests', {})
        if (permeability_tests.get('horizontal_permeability') is not None or
            permeability_tests.get('vertical_permeability') is not None):
            methods.append(CalculationMethod.LABORATORY_PERMEABILITY)
        
        gradation = inputs.test_data.get('gradation', {})
        if (gradation.get('d10') is not None and 
            self._is_clean_sand(inputs.uscs_classification, gradation)):
            methods.append(CalculationMethod.HAZEN_FORMULA)
        
        if gradation.get('d10') is not None and self._has_gradation_data(gradation):
            methods.append(CalculationMethod.KOZENY_CARMAN)
        
        return methods
    
    def _is_clean_sand(self, classification: USCSClassification, gradation: Dict) -> bool:
        """Check if soil is clean sand suitable for Hazen formula."""
        if classification not in [USCSClassification.SW, USCSClassification.SP]:
            return False
        
        fines = gradation.get('fines_percent', 100)
        return fines < 5  # Less than 5% fines
    
    def _has_gradation_data(self, gradation: Dict) -> bool:
        """Check if sufficient gradation data exists."""
        required_keys = ['gravel_percent', 'sand_percent', 'fines_percent']
        return all(key in gradation for key in required_keys)
    
    def _estimate_porosity(self, classification: USCSClassification) -> float:
        """Estimate porosity based on soil classification."""
        porosity_map = {
            USCSClassification.GW: 0.25, USCSClassification.GP: 0.30,
            USCSClassification.SW: 0.35, USCSClassification.SP: 0.40,
            USCSClassification.GM: 0.30, USCSClassification.GC: 0.25,
            USCSClassification.SM: 0.35, USCSClassification.SC: 0.30,
            USCSClassification.ML: 0.45, USCSClassification.CL: 0.40,
            USCSClassification.MH: 0.50, USCSClassification.CH: 0.45,
            USCSClassification.OL: 0.55, USCSClassification.OH: 0.60,
            USCSClassification.PT: 0.80
        }
        return porosity_map.get(classification, 0.40)
    
    def _kozeny_carman_estimate(self, d10: float, porosity: float) -> float:
        """Simplified Kozeny-Carman estimate."""
        # k = (d10² * n³) / (C * (1-n)²)
        # where C ≈ 180 for spherical particles
        C = 180
        n = porosity
        k = (d10 ** 2 * n ** 3) / (C * (1 - n) ** 2)
        return k * 1000  # Convert to appropriate units

class CalculationEngine:
    """Main calculation engine coordinating all parameter calculators."""
    
    def __init__(self):
        """Initialize calculation engine with all calculators."""
        self.calculators = {
            'unit_weight': UnitWeightCalculator(),
            'friction_angle': FrictionAngleCalculator(),
            'undrained_shear_strength': UndrainedShearStrengthCalculator(),
            'modulus_elasticity': ModulusElasticityCalculator(),
            'permeability': PermeabilityCalculator()
        }
    
    def calculate_all_parameters(self, inputs: CalculationInput) -> Dict[str, List[CalculationResult]]:
        """
        Calculate all available parameters.
        
        Args:
            inputs: Calculation input data
            
        Returns:
            Dictionary mapping parameter names to calculation results
        """
        results = {}
        
        for param_name, calculator in self.calculators.items():
            try:
                param_results = calculator.calculate(inputs)
                if param_results:
                    results[param_name] = param_results
            except Exception as e:
                logger.error(f"Error calculating {param_name}: {e}")
        
        return results
    
    def calculate_parameter(self, parameter_name: str, inputs: CalculationInput) -> List[CalculationResult]:
        """
        Calculate specific parameter.
        
        Args:
            parameter_name: Name of parameter to calculate
            inputs: Calculation input data
            
        Returns:
            List of calculation results
        """
        if parameter_name not in self.calculators:
            raise ValueError(f"Unknown parameter: {parameter_name}")
        
        calculator = self.calculators[parameter_name]
        return calculator.calculate(inputs)
    
    def get_available_methods(self, parameter_name: str, inputs: CalculationInput) -> List[CalculationMethod]:
        """
        Get available calculation methods for a parameter.
        
        Args:
            parameter_name: Name of parameter
            inputs: Calculation input data
            
        Returns:
            List of available calculation methods
        """
        if parameter_name not in self.calculators:
            return []
        
        calculator = self.calculators[parameter_name]
        return calculator.get_available_methods(inputs)
    
    def get_best_result(self, results: List[CalculationResult]) -> Optional[CalculationResult]:
        """
        Get the best calculation result based on confidence.
        
        Args:
            results: List of calculation results
            
        Returns:
            Best result or None if no results
        """
        if not results:
            return None
        
        # Sort by confidence (descending) then by method preference
        method_preference = {
            CalculationMethod.LABORATORY_PERMEABILITY: 10,
            CalculationMethod.TRIAXIAL_DRAINED: 9,
            CalculationMethod.TRIAXIAL_UNDRAINED: 9,
            CalculationMethod.DIRECT_SHEAR: 8,
            CalculationMethod.UNCONFINED_COMPRESSION: 7,
            CalculationMethod.DRY_UNIT_WEIGHT: 8,
            CalculationMethod.SATURATED_UNIT_WEIGHT: 7,
            CalculationMethod.SPT_CORRELATION: 6,
            CalculationMethod.EMPIRICAL_CORRELATION: 5,
            CalculationMethod.HAZEN_FORMULA: 4,
            CalculationMethod.KOZENY_CARMAN: 3
        }
        
        def sort_key(result):
            return (result.confidence, method_preference.get(result.method, 0))
        
        return max(results, key=sort_key)

# Global calculation engine instance
calculation_engine = CalculationEngine()