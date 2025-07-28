"""
JSON import engine for soil profile data.

This module handles importing soil profiles from JSON format with full
validation and data integrity checks.
"""

import json
import logging
import gzip
from typing import Dict, List, Optional, Any, Union, Tuple
from datetime import datetime
from pathlib import Path
import jsonschema

from core.models import SoilProfile, StrataLayer, Exploration, Sample
from core.database import DatabaseManager, get_database_manager
from utils.constants import CURRENT_JSON_VERSION, SUPPORTED_JSON_VERSIONS, SOIL_PROFILE_SCHEMA_PATH
from core.validators import GeotechnicalValidator, ValidationResult, validate_project_data

logger = logging.getLogger(__name__)

class SoilProfileImporter:
    """Handles importing soil profile data from JSON format."""
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """
        Initialize importer.
        
        Args:
            db_manager: Database manager instance
        """
        self.db_manager = db_manager or get_database_manager()
        self.validator = GeotechnicalValidator()
        self.schema = self._load_json_schema()
    
    def import_complete_project(self, input_path: Union[str, Path],
                               validate_schema: bool = True,
                               merge_existing: bool = False) -> Optional[int]:
        """
        Import complete project from JSON file.
        
        Args:
            input_path: Input JSON file path
            validate_schema: Whether to validate against JSON schema
            merge_existing: Whether to merge with existing project
            
        Returns:
            Project ID if successful, None otherwise
        """
        try:
            # Load JSON data
            json_data = self._load_json_file(input_path)
            if not json_data:
                return None
            
            # Version compatibility check
            if not self._check_version_compatibility(json_data):
                return None
            
            # Schema validation
            if validate_schema and not self._validate_json_schema(json_data):
                return None
            
            # Business logic validation
            is_valid, validation_results = validate_project_data(json_data)
            if not is_valid:
                logger.error("Project data validation failed")
                self._log_validation_results(validation_results)
                return None
            
            # Import to database
            project_id = self._import_project_to_database(json_data, merge_existing)
            
            if project_id:
                logger.info(f"Project imported successfully with ID: {project_id}")
            
            return project_id
            
        except Exception as e:
            logger.error(f"Project import failed: {e}")
            return None
    
    def import_strata_layers(self, input_path: Union[str, Path],
                           project_id: int,
                           replace_existing: bool = False) -> bool:
        """
        Import strata layers into existing project.
        
        Args:
            input_path: Input JSON file path
            project_id: Target project ID
            replace_existing: Whether to replace existing layers
            
        Returns:
            True if import successful, False otherwise
        """
        try:
            json_data = self._load_json_file(input_path)
            if not json_data:
                return False
            
            # Extract strata layers
            strata_layers = json_data.get('interpreted_strata', [])
            if not strata_layers:
                logger.error("No strata layers found in import file")
                return False
            
            # Validate strata data
            if not self._validate_strata_data(strata_layers):
                return False
            
            # Import layers to database
            return self._import_strata_layers_to_database(strata_layers, project_id, replace_existing)
            
        except Exception as e:
            logger.error(f"Strata layers import failed: {e}")
            return False
    
    def validate_import_schema(self, input_path: Union[str, Path]) -> Tuple[bool, List[str]]:
        """
        Validate JSON file against schema without importing.
        
        Args:
            input_path: Input JSON file path
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        try:
            json_data = self._load_json_file(input_path)
            if not json_data:
                return False, ["Failed to load JSON file"]
            
            # Schema validation
            if not self.schema:
                return False, ["JSON schema not available"]
            
            try:
                jsonschema.validate(json_data, self.schema)
                return True, []
            except jsonschema.ValidationError as e:
                return False, [f"Schema validation error: {e.message}"]
            except jsonschema.SchemaError as e:
                return False, [f"Schema error: {e.message}"]
                
        except Exception as e:
            return False, [f"Validation failed: {str(e)}"]
    
    def merge_projects(self, input_paths: List[Union[str, Path]],
                      output_path: Union[str, Path]) -> bool:
        """
        Merge multiple JSON profiles into a single project.
        
        Args:
            input_paths: List of input JSON file paths
            output_path: Output merged JSON file path
            
        Returns:
            True if merge successful, False otherwise
        """
        try:
            merged_data = None
            
            for input_path in input_paths:
                json_data = self._load_json_file(input_path)
                if not json_data:
                    continue
                
                if merged_data is None:
                    # First file becomes the base
                    merged_data = json_data.copy()
                else:
                    # Merge subsequent files
                    merged_data = self._merge_project_data(merged_data, json_data)
            
            if merged_data is None:
                logger.error("No valid data found in input files")
                return False
            
            # Update merge metadata
            merged_data['project_metadata']['date_created'] = datetime.now().isoformat()
            merged_data['project_metadata']['version'] = CURRENT_JSON_VERSION
            
            # Add merge metadata
            merged_data['merge_metadata'] = {
                'merge_date': datetime.now().isoformat(),
                'source_files': [str(p) for p in input_paths],
                'merged_explorations': len(merged_data.get('explorations', {})),
                'merged_strata': len(merged_data.get('interpreted_strata', []))
            }
            
            # Write merged data
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(merged_data, f, indent=2)
            
            logger.info(f"Projects merged successfully to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Project merge failed: {e}")
            return False
    
    def handle_version_compatibility(self, json_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle version compatibility and migrate data if needed.
        
        Args:
            json_data: JSON data to migrate
            
        Returns:
            Migrated JSON data
        """
        export_meta = json_data.get('export_metadata', {})
        version = export_meta.get('exporter_version', '1.0.0')
        
        if version == CURRENT_JSON_VERSION:
            return json_data
        
        # Version migration logic would go here
        # For now, we only support current version
        logger.warning(f"Data version {version} may need migration to {CURRENT_JSON_VERSION}")
        
        return json_data
    
    def _load_json_file(self, input_path: Union[str, Path]) -> Optional[Dict[str, Any]]:
        """Load JSON data from file, handling compression."""
        try:
            input_path = Path(input_path)
            
            if input_path.suffix == '.gz':
                with gzip.open(input_path, 'rt', encoding='utf-8') as f:
                    return json.load(f)
            else:
                with open(input_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
                    
        except FileNotFoundError:
            logger.error(f"Import file not found: {input_path}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON format in {input_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to load {input_path}: {e}")
            return None
    
    def _load_json_schema(self) -> Optional[Dict[str, Any]]:
        """Load JSON schema for validation."""
        try:
            if SOIL_PROFILE_SCHEMA_PATH.exists():
                with open(SOIL_PROFILE_SCHEMA_PATH, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                logger.warning(f"JSON schema not found: {SOIL_PROFILE_SCHEMA_PATH}")
                return None
        except Exception as e:
            logger.error(f"Failed to load JSON schema: {e}")
            return None
    
    def _check_version_compatibility(self, json_data: Dict[str, Any]) -> bool:
        """Check if JSON data version is compatible."""
        export_meta = json_data.get('export_metadata', {})
        version = export_meta.get('exporter_version', '1.0.0')
        
        if version not in SUPPORTED_JSON_VERSIONS:
            logger.error(f"Unsupported JSON version: {version}")
            return False
        
        return True
    
    def _validate_json_schema(self, json_data: Dict[str, Any]) -> bool:
        """Validate JSON data against schema."""
        if not self.schema:
            logger.warning("No schema available for validation")
            return True
        
        try:
            jsonschema.validate(json_data, self.schema)
            return True
        except jsonschema.ValidationError as e:
            logger.error(f"Schema validation failed: {e.message}")
            return False
        except jsonschema.SchemaError as e:
            logger.error(f"Schema error: {e.message}")
            return False
    
    def _validate_strata_data(self, strata_layers: List[Dict]) -> bool:
        """Validate strata layer data."""
        for layer in strata_layers:
            required_keys = ['strata_id', 'top_elevation', 'bottom_elevation', 
                           'soil_type', 'uscs_classification']
            if not all(key in layer for key in required_keys):
                logger.error(f"Strata layer missing required keys: {layer.get('strata_id', 'unknown')}")
                return False
        
        return True
    
    def _import_project_to_database(self, json_data: Dict[str, Any], 
                                   merge_existing: bool = False) -> Optional[int]:
        """Import project data to database."""
        try:
            with self.db_manager.get_session() as session:
                from core.database import Project, Borehole, Sample, TestResult, StrataLayer, TestMethod
                
                project_meta = json_data['project_metadata']
                
                # Check if project exists
                existing_project = None
                if merge_existing:
                    existing_project = session.query(Project).filter(
                        Project.project_number == project_meta['project_number']
                    ).first()
                
                if existing_project:
                    project = existing_project
                    logger.info(f"Merging with existing project {project.id}")
                else:
                    # Create new project
                    project = Project(
                        project_name=project_meta['project_name'],
                        project_number=project_meta['project_number'],
                        client=project_meta.get('client'),
                        location=project_meta.get('location'),
                        description=project_meta.get('description'),
                        coordinate_system=project_meta.get('coordinate_system', 'State Plane'),
                        date_created=datetime.fromisoformat(project_meta['date_created']) if 'date_created' in project_meta else datetime.now(),
                        created_by=project_meta.get('created_by'),
                        version=project_meta.get('version', CURRENT_JSON_VERSION)
                    )
                    session.add(project)
                    session.flush()  # Get project ID
                
                # Import explorations
                explorations = json_data.get('explorations', {})
                for borehole_id, borehole_data in explorations.items():
                    self._import_borehole(session, project.id, borehole_id, borehole_data)
                
                # Import strata layers
                strata_layers = json_data.get('interpreted_strata', [])
                for layer_data in strata_layers:
                    self._import_strata_layer(session, project.id, layer_data)
                
                return project.id
                
        except Exception as e:
            logger.error(f"Database import failed: {e}")
            return None
    
    def _import_borehole(self, session, project_id: int, borehole_id: str, 
                        borehole_data: Dict[str, Any]):
        """Import single borehole with samples."""
        from core.database import Borehole, Sample, TestResult, TestMethod
        
        location = borehole_data['location']
        drilling_info = borehole_data['drilling_info']
        
        # Create borehole
        borehole = Borehole(
            borehole_id=borehole_id,
            project_id=project_id,
            x_coordinate=location['x'],
            y_coordinate=location['y'],
            elevation=location['elevation'],
            drilling_method=drilling_info.get('method'),
            drilling_date=datetime.fromisoformat(drilling_info['date']) if drilling_info.get('date') else None,
            drilling_contractor=drilling_info.get('contractor')
        )
        session.add(borehole)
        session.flush()
        
        # Import samples
        samples = borehole_data.get('samples', [])
        for sample_data in samples:
            self._import_sample(session, borehole.id, sample_data)
    
    def _import_sample(self, session, borehole_id: int, sample_data: Dict[str, Any]):
        """Import single sample with test results."""
        from core.database import Sample, TestResult, TestMethod
        
        # Create sample
        sample = Sample(
            sample_id=sample_data['sample_id'],
            borehole_id=borehole_id,
            depth_top=sample_data['depth_top'],
            depth_bottom=sample_data['depth_bottom'],
            field_description=sample_data['field_description'],
            uscs_classification=sample_data.get('uscs_classification'),
            spt_n_value=sample_data.get('field_tests', {}).get('spt_n_value'),
            field_moisture=sample_data.get('field_tests', {}).get('field_moisture'),
            penetration_resistance=sample_data.get('field_tests', {}).get('penetration_resistance')
        )
        session.add(sample)
        session.flush()
        
        # Import laboratory test results
        lab_tests = sample_data.get('laboratory_tests', {})
        for test_type, test_data in lab_tests.items():
            if test_data:  # Only import non-empty test data
                # Get or create test method
                test_method = session.query(TestMethod).filter(
                    TestMethod.method_name == test_type
                ).first()
                
                if not test_method:
                    test_method = TestMethod(
                        method_name=test_type,
                        description=f"Imported {test_type} test"
                    )
                    session.add(test_method)
                    session.flush()
                
                # Create test result
                test_result = TestResult(
                    sample_id=sample.id,
                    test_method_id=test_method.id,
                    test_type=test_type,
                    test_data=json.dumps(test_data)
                )
                session.add(test_result)
    
    def _import_strata_layer(self, session, project_id: int, layer_data: Dict[str, Any]):
        """Import single strata layer."""
        from core.database import StrataLayer
        
        layer = StrataLayer(
            strata_id=layer_data['strata_id'],
            project_id=project_id,
            top_elevation=layer_data['top_elevation'],
            bottom_elevation=layer_data['bottom_elevation'],
            soil_type=layer_data['soil_type'],
            uscs_classification=layer_data['uscs_classification'],
            design_parameters=json.dumps(layer_data.get('design_parameters', {})),
            samples_used=json.dumps(layer_data.get('supporting_data', {}).get('samples_used', [])),
            calculation_details=json.dumps(layer_data.get('supporting_data', {}).get('calculation_details', {})),
            references=json.dumps(layer_data.get('supporting_data', {}).get('references', [])),
            interpreted_by=layer_data.get('metadata', {}).get('interpreted_by'),
            interpretation_date=datetime.fromisoformat(layer_data.get('metadata', {}).get('interpretation_date')) if layer_data.get('metadata', {}).get('interpretation_date') else datetime.now(),
            confidence_level=layer_data.get('metadata', {}).get('confidence_level', 0.8)
        )
        session.add(layer)
    
    def _import_strata_layers_to_database(self, strata_layers: List[Dict], 
                                        project_id: int, replace_existing: bool) -> bool:
        """Import strata layers to database."""
        try:
            with self.db_manager.get_session() as session:
                from core.database import StrataLayer
                
                if replace_existing:
                    # Delete existing layers
                    session.query(StrataLayer).filter(
                        StrataLayer.project_id == project_id
                    ).delete()
                
                # Import new layers
                for layer_data in strata_layers:
                    self._import_strata_layer(session, project_id, layer_data)
                
                logger.info(f"Imported {len(strata_layers)} strata layers")
                return True
                
        except Exception as e:
            logger.error(f"Strata layer import failed: {e}")
            return False
    
    def _merge_project_data(self, base_data: Dict[str, Any], 
                           merge_data: Dict[str, Any]) -> Dict[str, Any]:
        """Merge two project data dictionaries."""
        # Merge explorations
        base_explorations = base_data.get('explorations', {})
        merge_explorations = merge_data.get('explorations', {})
        
        for borehole_id, borehole_data in merge_explorations.items():
            if borehole_id not in base_explorations:
                base_explorations[borehole_id] = borehole_data
            else:
                # Merge samples if borehole exists
                base_samples = base_explorations[borehole_id].get('samples', [])
                merge_samples = borehole_data.get('samples', [])
                
                # Add samples that don't exist (by sample_id)
                existing_sample_ids = {s['sample_id'] for s in base_samples}
                for sample in merge_samples:
                    if sample['sample_id'] not in existing_sample_ids:
                        base_samples.append(sample)
                
                base_explorations[borehole_id]['samples'] = base_samples
        
        # Merge strata layers
        base_strata = base_data.get('interpreted_strata', [])
        merge_strata = merge_data.get('interpreted_strata', [])
        
        # Add strata that don't exist (by strata_id)
        existing_strata_ids = {s['strata_id'] for s in base_strata}
        for strata in merge_strata:
            if strata['strata_id'] not in existing_strata_ids:
                base_strata.append(strata)
        
        base_data['explorations'] = base_explorations
        base_data['interpreted_strata'] = base_strata
        
        return base_data
    
    def _log_validation_results(self, results: List[ValidationResult]):
        """Log validation results."""
        for result in results:
            if result.severity.value == 'error':
                logger.error(f"Validation error: {result.message}")
            elif result.severity.value == 'warning':
                logger.warning(f"Validation warning: {result.message}")
            else:
                logger.info(f"Validation info: {result.message}")

# Convenience functions
def import_project_from_json(input_path: Union[str, Path], 
                           validate_schema: bool = True) -> Optional[int]:
    """
    Import project from JSON file.
    
    Args:
        input_path: Input JSON file path
        validate_schema: Whether to validate against schema
        
    Returns:
        Project ID if successful, None otherwise
    """
    importer = SoilProfileImporter()
    return importer.import_complete_project(input_path, validate_schema)

def validate_json_file(input_path: Union[str, Path]) -> Tuple[bool, List[str]]:
    """
    Validate JSON file against schema.
    
    Args:
        input_path: Input JSON file path
        
    Returns:
        Tuple of (is_valid, error_messages)
    """
    importer = SoilProfileImporter()
    return importer.validate_import_schema(input_path)

def merge_json_projects(input_paths: List[Union[str, Path]], 
                       output_path: Union[str, Path]) -> bool:
    """
    Merge multiple JSON projects.
    
    Args:
        input_paths: List of input JSON file paths
        output_path: Output merged JSON file path
        
    Returns:
        True if merge successful, False otherwise
    """
    importer = SoilProfileImporter()
    return importer.merge_projects(input_paths, output_path)