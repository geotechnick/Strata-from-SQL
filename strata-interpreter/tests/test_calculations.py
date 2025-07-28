"""
Tests for parameter calculation engine.
"""

import pytest
import numpy as np
from core.calculations import (
    CalculationEngine, CalculationInput, UnitWeightCalculator,
    FrictionAngleCalculator, UndrainedShearStrengthCalculator,
    ModulusElasticityCalculator, PermeabilityCalculator
)
from core.models import USCSClassification

class TestUnitWeightCalculator:
    """Test unit weight calculations."""
    
    def test_dry_unit_weight_calculation(self):
        """Test dry unit weight from direct measurement."""
        calculator = UnitWeightCalculator()
        
        inputs = CalculationInput(
            test_data={
                'moisture_density': {
                    'dry_density': 110.0
                }
            },
            sample_depth=10.0,
            uscs_classification=USCSClassification.SM
        )
        
        results = calculator.calculate(inputs)
        
        assert len(results) > 0
        dry_weight_result = next(r for r in results if 'dry' in r.method.value.lower())
        assert dry_weight_result.value == 110.0
        assert dry_weight_result.confidence > 0.9
    
    def test_saturated_unit_weight_calculation(self):
        """Test saturated unit weight calculation."""
        calculator = UnitWeightCalculator()
        
        inputs = CalculationInput(
            test_data={
                'moisture_density': {
                    'dry_density': 100.0,
                    'natural_moisture': 15.0
                }
            },
            sample_depth=10.0,
            uscs_classification=USCSClassification.CL
        )
        
        results = calculator.calculate(inputs)
        
        # Should calculate wet density as dry_density * (1 + moisture/100)
        expected_wet = 100.0 * (1 + 15.0/100)
        saturated_result = next(r for r in results if 'saturated' in r.method.value.lower())
        assert abs(saturated_result.value - expected_wet) < 0.1

class TestFrictionAngleCalculator:
    """Test friction angle calculations."""
    
    def test_spt_correlation(self):
        """Test SPT correlation for granular soils."""
        calculator = FrictionAngleCalculator()
        
        inputs = CalculationInput(
            test_data={
                'field_tests': {
                    'spt_n_value': 20
                }
            },
            sample_depth=10.0,
            uscs_classification=USCSClassification.SW
        )
        
        results = calculator.calculate(inputs)
        
        spt_result = next(r for r in results if 'spt' in r.method.value.lower())
        # φ = 28 + 15*log10(20) = 28 + 15*1.301 = 47.5, capped at 45
        assert abs(spt_result.value - 45.0) < 1.0
    
    def test_direct_shear_analysis(self):
        """Test direct shear test analysis."""
        calculator = FrictionAngleCalculator()
        
        # Mock direct shear data
        inputs = CalculationInput(
            test_data={
                'strength_tests': {
                    'direct_shear': [
                        {'normal_stress': 1000, 'shear_strength': 577},  # tan(30°) = 0.577
                        {'normal_stress': 2000, 'shear_strength': 1155},
                        {'normal_stress': 3000, 'shear_strength': 1732}
                    ]
                }
            },
            sample_depth=10.0,
            uscs_classification=USCSClassification.SM
        )
        
        results = calculator.calculate(inputs)
        
        shear_result = next(r for r in results if 'shear' in r.method.value.lower())
        # Should calculate approximately 30 degrees
        assert abs(shear_result.value - 30.0) < 2.0

class TestCalculationEngine:
    """Test main calculation engine."""
    
    def test_calculate_all_parameters(self):
        """Test calculating all available parameters."""
        engine = CalculationEngine()
        
        inputs = CalculationInput(
            test_data={
                'moisture_density': {
                    'dry_density': 105.0,
                    'natural_moisture': 12.0
                },
                'field_tests': {
                    'spt_n_value': 15
                },
                'strength_tests': {
                    'unconfined_compression': 2000
                }
            },
            sample_depth=8.0,
            uscs_classification=USCSClassification.CL
        )
        
        results = engine.calculate_all_parameters(inputs)
        
        # Should have results for multiple parameters
        assert 'unit_weight' in results
        assert 'modulus_elasticity' in results
        assert 'undrained_shear_strength' in results
        
        # Check unit weight results
        unit_weight_results = results['unit_weight']
        assert len(unit_weight_results) > 0
        
        # Check undrained shear strength (Su = qu/2)
        undrained_results = results['undrained_shear_strength']
        assert len(undrained_results) > 0
        assert abs(undrained_results[0].value - 1000.0) < 1.0  # 2000/2 = 1000
    
    def test_get_best_result(self):
        """Test getting best result from multiple calculations."""
        engine = CalculationEngine()
        
        # Create mock results with different confidence levels
        from core.calculations import CalculationResult, CalculationMethod
        
        results = [
            CalculationResult(
                value=25.0,
                method=CalculationMethod.SPT_CORRELATION,
                confidence=0.6,
                source_data={'spt_n_value': 10},
                references=['Test']
            ),
            CalculationResult(
                value=30.0,
                method=CalculationMethod.DIRECT_SHEAR,
                confidence=0.9,
                source_data={'direct_shear': []},
                references=['Test']
            )
        ]
        
        best_result = engine.get_best_result(results)
        
        # Should select the direct shear result due to higher confidence
        assert best_result.value == 30.0
        assert best_result.confidence == 0.9

class TestPermeabilityCalculator:
    """Test permeability calculations."""
    
    def test_hazen_formula(self):
        """Test Hazen formula for clean sand."""
        calculator = PermeabilityCalculator()
        
        inputs = CalculationInput(
            test_data={
                'gradation': {
                    'fines_percent': 2.0,  # Clean sand
                    'd10': 0.2,  # mm
                    'cu': 3.0
                }
            },
            sample_depth=5.0,
            uscs_classification=USCSClassification.SW
        )
        
        results = calculator.calculate(inputs)
        
        hazen_result = next(r for r in results if 'hazen' in r.method.value.lower())
        # k = 100 * d10² = 100 * 0.2² = 4.0, then convert to cm/s
        assert hazen_result.value > 0
        assert hazen_result.confidence > 0.5

if __name__ == "__main__":
    pytest.main([__file__])