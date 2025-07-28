"""
JSON export engine for soil profile data.

This module handles exporting complete soil profiles, individual layers,
and parameter sets to JSON format with full data preservation.
"""

import json
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from pathlib import Path
from dataclasses import asdict
import gzip

from core.models import SoilProfile, StrataLayer, Exploration, Sample, DesignParameters
from core.database import DatabaseManager, get_database_manager
from utils.constants import CURRENT_JSON_VERSION
from core.validators import GeotechnicalValidator, ValidationResult

logger = logging.getLogger(__name__)

class SoilProfileExporter:
    """Handles exporting soil profile data to JSON format."""
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """
        Initialize exporter.
        
        Args:
            db_manager: Database manager instance
        """
        self.db_manager = db_manager or get_database_manager()
        self.validator = GeotechnicalValidator()
    
    def export_complete_project(self, project_id: int, 
                              output_path: Union[str, Path],
                              compress: bool = False,
                              validate: bool = True) -> bool:
        """
        Export complete project with all data.
        
        Args:
            project_id: Project ID to export
            output_path: Output file path
            compress: Whether to compress the output
            validate: Whether to validate data before export
            
        Returns:
            True if export successful, False otherwise
        """
        try:
            # Get project data
            project_data = self._build_complete_project_data(project_id)
            
            if validate:
                if not self._validate_export_data(project_data):
                    logger.error("Export validation failed")
                    return False
            
            # Add export metadata
            project_data['export_metadata'] = {
                'export_date': datetime.now().isoformat(),
                'exporter_version': CURRENT_JSON_VERSION,
                'export_type': 'complete_project',
                'compression': compress
            }
            
            # Write to file
            output_path = Path(output_path)
            if compress:
                with gzip.open(output_path.with_suffix('.json.gz'), 'wt', encoding='utf-8') as f:
                    json.dump(project_data, f, indent=2, default=self._json_serializer)
            else:
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(project_data, f, indent=2, default=self._json_serializer)
            
            logger.info(f"Project {project_id} exported to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Export failed: {e}")
            return False
    
    def export_strata_layer(self, strata_id: str, 
                           output_path: Union[str, Path]) -> bool:
        """
        Export individual strata layer with supporting data.
        
        Args:
            strata_id: Strata layer ID to export
            output_path: Output file path
            
        Returns:
            True if export successful, False otherwise
        """
        try:
            with self.db_manager.get_session() as session:
                from core.database import StrataLayer
                
                layer = session.query(StrataLayer).filter(
                    StrataLayer.strata_id == strata_id
                ).first()
                
                if not layer:
                    logger.error(f"Strata layer {strata_id} not found")
                    return False
                
                # Build layer data with supporting information
                layer_data = self._build_layer_data(layer)
                
                # Add export metadata
                layer_data['export_metadata'] = {
                    'export_date': datetime.now().isoformat(),
                    'exporter_version': CURRENT_JSON_VERSION,
                    'export_type': 'single_layer',
                    'strata_id': strata_id
                }
                
                # Write to file
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(layer_data, f, indent=2, default=self._json_serializer)
                
                logger.info(f"Strata layer {strata_id} exported to {output_path}")
                return True
                
        except Exception as e:
            logger.error(f"Layer export failed: {e}")
            return False
    
    def export_parameter_set(self, project_id: int, parameter_type: str,
                           output_path: Union[str, Path]) -> bool:
        """
        Export specific parameter across all layers.
        
        Args:
            project_id: Project ID
            parameter_type: Type of parameter (e.g., 'unit_weight', 'friction_angle')
            output_path: Output file path
            
        Returns:
            True if export successful, False otherwise
        """
        try:
            with self.db_manager.get_session() as session:
                from core.database import StrataLayer
                
                layers = session.query(StrataLayer).filter(
                    StrataLayer.project_id == project_id
                ).order_by(StrataLayer.top_elevation.desc()).all()
                
                if not layers:
                    logger.error(f"No strata layers found for project {project_id}")
                    return False
                
                # Extract parameter data from all layers
                parameter_data = {
                    'project_id': project_id,
                    'parameter_type': parameter_type,
                    'layers': []
                }
                
                for layer in layers:
                    layer_params = json.loads(layer.design_parameters) if layer.design_parameters else {}
                    if parameter_type in layer_params:
                        parameter_data['layers'].append({
                            'strata_id': layer.strata_id,
                            'top_elevation': layer.top_elevation,
                            'bottom_elevation': layer.bottom_elevation,
                            'soil_type': layer.soil_type,
                            'uscs_classification': layer.uscs_classification,
                            'parameter_data': layer_params[parameter_type]
                        })
                
                # Add export metadata
                parameter_data['export_metadata'] = {
                    'export_date': datetime.now().isoformat(),
                    'exporter_version': CURRENT_JSON_VERSION,
                    'export_type': 'parameter_set',
                    'parameter_count': len(parameter_data['layers'])
                }
                
                # Write to file
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(parameter_data, f, indent=2, default=self._json_serializer)
                
                logger.info(f"Parameter set {parameter_type} exported to {output_path}")
                return True
                
        except Exception as e:
            logger.error(f"Parameter set export failed: {e}")
            return False
    
    def validate_export_data(self, data: Dict[str, Any]) -> bool:
        """
        Validate export data before writing.
        
        Args:
            data: Data to validate
            
        Returns:
            True if data is valid, False otherwise
        """
        return self._validate_export_data(data)
    
    def _build_complete_project_data(self, project_id: int) -> Dict[str, Any]:
        """Build complete project data structure."""
        with self.db_manager.get_session() as session:
            from core.database import Project, Borehole, Sample, TestResult, StrataLayer
            
            # Get project
            project = session.query(Project).filter(Project.id == project_id).first()
            if not project:
                raise ValueError(f"Project {project_id} not found")
            
            # Build project metadata
            project_data = {
                'project_metadata': {
                    'project_name': project.project_name,
                    'project_number': project.project_number,
                    'date_created': project.date_created.isoformat(),
                    'created_by': project.created_by,
                    'version': project.version,
                    'coordinate_system': project.coordinate_system,
                    'client': project.client,
                    'location': project.location,
                    'description': project.description
                },
                'explorations': {},
                'interpreted_strata': [],
                'calculation_methods': {
                    'equations_used': {},
                    'validation_results': {},
                    'quality_metrics': {}
                }
            }
            
            # Get boreholes and samples
            boreholes = session.query(Borehole).filter(Borehole.project_id == project_id).all()
            
            for borehole in boreholes:
                borehole_data = {
                    'location': {
                        'x': borehole.x_coordinate,
                        'y': borehole.y_coordinate,
                        'elevation': borehole.elevation,
                        'coordinate_system': project.coordinate_system
                    },
                    'drilling_info': {
                        'method': borehole.drilling_method,
                        'date': borehole.drilling_date.date().isoformat() if borehole.drilling_date else None,
                        'contractor': borehole.drilling_contractor
                    },
                    'samples': []
                }
                
                # Get samples for this borehole
                samples = session.query(Sample).filter(
                    Sample.borehole_id == borehole.id
                ).order_by(Sample.depth_top).all()
                
                for sample in samples:
                    sample_data = {
                        'sample_id': sample.sample_id,
                        'depth_top': sample.depth_top,
                        'depth_bottom': sample.depth_bottom,
                        'field_description': sample.field_description,
                        'uscs_classification': sample.uscs_classification,
                        'field_tests': {},
                        'laboratory_tests': {}
                    }
                    
                    # Add field test data
                    if sample.spt_n_value is not None:
                        sample_data['field_tests']['spt_n_value'] = sample.spt_n_value
                    if sample.field_moisture is not None:
                        sample_data['field_tests']['field_moisture'] = sample.field_moisture
                    if sample.penetration_resistance is not None:
                        sample_data['field_tests']['penetration_resistance'] = sample.penetration_resistance
                    
                    # Get test results
                    test_results = session.query(TestResult).filter(
                        TestResult.sample_id == sample.id
                    ).all()
                    
                    for test_result in test_results:
                        test_data = json.loads(test_result.test_data) if test_result.test_data else {}
                        sample_data['laboratory_tests'][test_result.test_type] = test_data
                    
                    borehole_data['samples'].append(sample_data)
                
                project_data['explorations'][borehole.borehole_id] = borehole_data
            
            # Get strata layers
            strata_layers = session.query(StrataLayer).filter(
                StrataLayer.project_id == project_id
            ).order_by(StrataLayer.top_elevation.desc()).all()
            
            for layer in strata_layers:
                layer_data = {
                    'strata_id': layer.strata_id,
                    'top_elevation': layer.top_elevation,
                    'bottom_elevation': layer.bottom_elevation,
                    'soil_type': layer.soil_type,
                    'uscs_classification': layer.uscs_classification,
                    'design_parameters': json.loads(layer.design_parameters) if layer.design_parameters else {},
                    'supporting_data': {
                        'samples_used': json.loads(layer.samples_used) if layer.samples_used else [],
                        'calculation_details': json.loads(layer.calculation_details) if layer.calculation_details else {},
                        'references': json.loads(layer.references) if layer.references else []
                    }
                }
                
                project_data['interpreted_strata'].append(layer_data)
            
            return project_data
    
    def _build_layer_data(self, layer) -> Dict[str, Any]:
        """Build data for a single strata layer."""
        return {
            'strata_id': layer.strata_id,
            'top_elevation': layer.top_elevation,
            'bottom_elevation': layer.bottom_elevation,
            'soil_type': layer.soil_type,
            'uscs_classification': layer.uscs_classification,
            'design_parameters': json.loads(layer.design_parameters) if layer.design_parameters else {},
            'supporting_data': {
                'samples_used': json.loads(layer.samples_used) if layer.samples_used else [],
                'calculation_details': json.loads(layer.calculation_details) if layer.calculation_details else {},
                'references': json.loads(layer.references) if layer.references else []
            },
            'metadata': {
                'interpreted_by': layer.interpreted_by,
                'interpretation_date': layer.interpretation_date.isoformat() if layer.interpretation_date else None,
                'confidence_level': layer.confidence_level
            }
        }
    
    def _validate_export_data(self, data: Dict[str, Any]) -> bool:
        """Validate export data against schema and business rules."""
        try:
            # Basic structure validation
            required_keys = ['project_metadata', 'explorations', 'interpreted_strata']
            if not all(key in data for key in required_keys):
                logger.error("Missing required top-level keys in export data")
                return False
            
            # Validate project metadata
            project_meta = data['project_metadata']
            required_meta_keys = ['project_name', 'project_number', 'date_created']
            if not all(key in project_meta for key in required_meta_keys):
                logger.error("Missing required project metadata")
                return False
            
            # Validate explorations structure
            explorations = data['explorations']
            for borehole_id, borehole_data in explorations.items():
                if not self._validate_borehole_data(borehole_id, borehole_data):
                    return False
            
            # Validate strata layers
            strata_layers = data['interpreted_strata']
            if not self._validate_strata_data(strata_layers):
                return False
            
            logger.info("Export data validation passed")
            return True
            
        except Exception as e:
            logger.error(f"Export data validation failed: {e}")
            return False
    
    def _validate_borehole_data(self, borehole_id: str, borehole_data: Dict) -> bool:
        """Validate individual borehole data."""
        # Check required structure
        required_keys = ['location', 'drilling_info', 'samples']
        if not all(key in borehole_data for key in required_keys):
            logger.error(f"Borehole {borehole_id} missing required keys")
            return False
        
        # Validate location
        location = borehole_data['location']
        location_keys = ['x', 'y', 'elevation']
        if not all(key in location for key in location_keys):
            logger.error(f"Borehole {borehole_id} missing location data")
            return False
        
        # Validate samples
        samples = borehole_data['samples']
        for sample in samples:
            if not self._validate_sample_data(sample):
                logger.error(f"Invalid sample data in borehole {borehole_id}")
                return False
        
        return True
    
    def _validate_sample_data(self, sample_data: Dict) -> bool:
        """Validate individual sample data."""
        required_keys = ['sample_id', 'depth_top', 'depth_bottom', 'field_description']
        if not all(key in sample_data for key in required_keys):
            return False
        
        # Check depth order
        if sample_data['depth_top'] >= sample_data['depth_bottom']:
            return False
        
        return True
    
    def _validate_strata_data(self, strata_layers: List[Dict]) -> bool:
        """Validate strata layer data."""
        if not strata_layers:
            return True
        
        # Check individual layers
        for layer in strata_layers:
            required_keys = ['strata_id', 'top_elevation', 'bottom_elevation', 
                           'soil_type', 'uscs_classification']
            if not all(key in layer for key in required_keys):
                logger.error(f"Strata layer missing required keys")
                return False
            
            # Check elevation order
            if layer['top_elevation'] <= layer['bottom_elevation']:
                logger.error(f"Invalid elevation order in layer {layer['strata_id']}")
                return False
        
        # Check for overlaps/gaps
        sorted_layers = sorted(strata_layers, key=lambda x: x['top_elevation'], reverse=True)
        for i in range(len(sorted_layers) - 1):
            current_bottom = sorted_layers[i]['bottom_elevation']
            next_top = sorted_layers[i + 1]['top_elevation']
            
            if abs(current_bottom - next_top) > 0.01:  # Allow small tolerance
                if current_bottom < next_top:
                    logger.warning(f"Gap between strata layers: {current_bottom} to {next_top}")
                else:
                    logger.error(f"Overlap between strata layers: {current_bottom} to {next_top}")
                    return False
        
        return True
    
    def _json_serializer(self, obj):
        """Custom JSON serializer for non-standard types."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        else:
            return str(obj)

# Convenience functions
def export_project_to_json(project_id: int, output_path: Union[str, Path], 
                          compress: bool = False) -> bool:
    """
    Export project to JSON file.
    
    Args:
        project_id: Project ID to export
        output_path: Output file path
        compress: Whether to compress the output
        
    Returns:
        True if export successful, False otherwise
    """
    exporter = SoilProfileExporter()
    return exporter.export_complete_project(project_id, output_path, compress)

def export_layer_to_json(strata_id: str, output_path: Union[str, Path]) -> bool:
    """
    Export strata layer to JSON file.
    
    Args:
        strata_id: Strata layer ID to export
        output_path: Output file path
        
    Returns:
        True if export successful, False otherwise
    """
    exporter = SoilProfileExporter()
    return exporter.export_strata_layer(strata_id, output_path)

def export_parameters_to_json(project_id: int, parameter_type: str, 
                             output_path: Union[str, Path]) -> bool:
    """
    Export parameter set to JSON file.
    
    Args:
        project_id: Project ID
        parameter_type: Type of parameter to export
        output_path: Output file path
        
    Returns:
        True if export successful, False otherwise
    """
    exporter = SoilProfileExporter()
    return exporter.export_parameter_set(project_id, parameter_type, output_path)