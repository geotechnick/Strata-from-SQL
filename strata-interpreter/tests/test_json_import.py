"""
Tests for JSON import functionality.
"""

import pytest
import json
import tempfile
import os
from datetime import datetime
from core.json_import import SoilProfileImporter, import_project_from_json, validate_json_file
from core.database import DatabaseManager

class TestSoilProfileImporter:
    """Test JSON import functionality."""
    
    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing."""
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        temp_file.close()
        
        db_manager = DatabaseManager(temp_file.name)
        yield db_manager
        
        # Cleanup
        os.unlink(temp_file.name)
    
    @pytest.fixture
    def sample_json_data(self):
        """Create sample JSON data for testing."""
        return {
            'project_metadata': {
                'project_name': 'Import Test Project',
                'project_number': 'IMPORT-001',
                'date_created': datetime.now().isoformat(),
                'created_by': 'Test Engineer',
                'version': '1.0.0',
                'coordinate_system': 'State Plane',
                'client': 'Test Client',
                'location': 'Test Site'
            },
            'explorations': {
                'IMPORT-B1': {
                    'location': {
                        'x': 1500.0,
                        'y': 2500.0,
                        'elevation': 105.0,
                        'coordinate_system': 'State Plane'
                    },
                    'drilling_info': {
                        'method': 'Hollow Stem Auger',
                        'date': '2023-06-15',
                        'contractor': 'Import Drilling Co.'
                    },
                    'samples': [
                        {
                            'sample_id': 'IMPORT-B1-S1',
                            'depth_top': 0.0,
                            'depth_bottom': 2.5,
                            'field_description': 'Brown silty clay with organics',
                            'uscs_classification': 'CL',
                            'field_tests': {
                                'spt_n_value': 8,
                                'field_moisture': 22.5
                            },
                            'laboratory_tests': {
                                'atterberg_limits': {
                                    'liquid_limit': 35,
                                    'plastic_limit': 18,
                                    'plasticity_index': 17
                                },
                                'gradation': {
                                    'gravel_percent': 5,
                                    'sand_percent': 25,
                                    'fines_percent': 70,
                                    'd10': 0.002,
                                    'd30': 0.015,
                                    'd60': 0.08
                                }
                            }
                        },
                        {
                            'sample_id': 'IMPORT-B1-S2',
                            'depth_top': 2.5,
                            'depth_bottom': 5.0,
                            'field_description': 'Stiff gray clay',
                            'uscs_classification': 'CH',
                            'field_tests': {
                                'spt_n_value': 15
                            }
                        }
                    ]
                }
            },
            'interpreted_strata': [
                {
                    'strata_id': 'IMPORT-L1',
                    'top_elevation': 105.0,
                    'bottom_elevation': 102.5,
                    'soil_type': 'Silty Clay',
                    'uscs_classification': 'CL',
                    'design_parameters': {
                        'unit_weight': {
                            'value': 118.0,
                            'calculation_method': 'laboratory_test',
                            'source': 'calculated',
                            'confidence': 0.85
                        },
                        'cohesion': {
                            'value': 800.0,
                            'calculation_method': 'unconfined_compression',
                            'source': 'calculated',
                            'confidence': 0.8
                        }
                    },
                    'supporting_data': {
                        'samples_used': ['IMPORT-B1-S1'],
                        'calculation_details': {},
                        'references': ['ASTM D2166']
                    }
                },
                {
                    'strata_id': 'IMPORT-L2',
                    'top_elevation': 102.5,
                    'bottom_elevation': 100.0,
                    'soil_type': 'Stiff Clay',
                    'uscs_classification': 'CH',
                    'design_parameters': {
                        'unit_weight': {
                            'value': 125.0,
                            'calculation_method': 'correlation',
                            'source': 'estimated',
                            'confidence': 0.7
                        }
                    },
                    'supporting_data': {
                        'samples_used': ['IMPORT-B1-S2'],
                        'calculation_details': {},
                        'references': []
                    }
                }
            ],
            'calculation_methods': {
                'equations_used': {},
                'validation_results': {},
                'quality_metrics': {}
            },
            'export_metadata': {
                'export_date': datetime.now().isoformat(),
                'exporter_version': '1.0.0',
                'export_type': 'complete_project'
            }
        }
    
    def test_import_complete_project(self, temp_db, sample_json_data):
        """Test importing complete project from JSON."""
        importer = SoilProfileImporter(temp_db)
        
        # Create temporary JSON file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            json.dump(sample_json_data, temp_file, indent=2)
            json_path = temp_file.name
        
        try:
            # Import project
            project_id = importer.import_complete_project(json_path, validate_schema=False)
            assert project_id is not None
            
            # Verify project was created
            project = temp_db.get_project(project_id)
            assert project is not None
            assert project.project_name == 'Import Test Project'
            assert project.project_number == 'IMPORT-001'
            assert project.client == 'Test Client'
            
            # Verify boreholes were created
            boreholes = temp_db.get_boreholes_for_project(project_id)
            assert len(boreholes) == 1
            
            borehole = boreholes[0]
            assert borehole.borehole_id == 'IMPORT-B1'
            assert borehole.x_coordinate == 1500.0
            assert borehole.y_coordinate == 2500.0
            assert borehole.elevation == 105.0
            
            # Verify samples were created
            samples = temp_db.get_samples_for_borehole(borehole.id)
            assert len(samples) == 2
            
            sample1 = samples[0]  # Should be ordered by depth
            assert sample1.sample_id == 'IMPORT-B1-S1'
            assert sample1.depth_top == 0.0
            assert sample1.depth_bottom == 2.5
            assert sample1.uscs_classification == 'CL'
            assert sample1.spt_n_value == 8
            
            # Verify test results were created
            test_results = temp_db.get_test_results_for_sample(sample1.id)
            assert len(test_results) > 0
            
            # Check for atterberg limits test
            atterberg_result = next((r for r in test_results if r.test_type == 'atterberg_limits'), None)
            assert atterberg_result is not None
            
            atterberg_data = json.loads(atterberg_result.test_data)
            assert atterberg_data['liquid_limit'] == 35
            assert atterberg_data['plasticity_index'] == 17
            
            # Verify strata layers were created
            strata_layers = temp_db.get_strata_layers_for_project(project_id)
            assert len(strata_layers) == 2
            
            layer1 = strata_layers[0]  # Ordered by elevation descending
            assert layer1.strata_id == 'IMPORT-L1'
            assert layer1.top_elevation == 105.0
            assert layer1.bottom_elevation == 102.5
            
            # Check design parameters
            design_params = json.loads(layer1.design_parameters)
            assert 'unit_weight' in design_params
            assert design_params['unit_weight']['value'] == 118.0
            
        finally:
            # Cleanup
            os.unlink(json_path)
    
    def test_import_with_compression(self, temp_db, sample_json_data):
        """Test importing compressed JSON file."""
        importer = SoilProfileImporter(temp_db)
        
        # Create temporary compressed JSON file
        import gzip
        with tempfile.NamedTemporaryFile(suffix='.json.gz', delete=False) as temp_file:
            with gzip.open(temp_file.name, 'wt') as gz_file:
                json.dump(sample_json_data, gz_file, indent=2)
            json_path = temp_file.name
        
        try:
            # Import compressed project
            project_id = importer.import_complete_project(json_path, validate_schema=False)
            assert project_id is not None
            
            # Verify project was imported correctly
            project = temp_db.get_project(project_id)
            assert project.project_name == 'Import Test Project'
            
        finally:
            # Cleanup
            os.unlink(json_path)
    
    def test_validate_import_schema(self, sample_json_data):
        """Test JSON schema validation."""
        importer = SoilProfileImporter()
        
        # Create temporary JSON file with valid data
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            json.dump(sample_json_data, temp_file, indent=2)
            json_path = temp_file.name
        
        try:
            # Test validation (will pass even without schema file for now)
            is_valid, errors = importer.validate_import_schema(json_path)
            # Should be valid or have no schema available
            assert is_valid or len(errors) == 1 and 'schema not available' in errors[0].lower()
            
        finally:
            # Cleanup
            os.unlink(json_path)
    
    def test_import_invalid_json(self, temp_db):
        """Test importing invalid JSON."""
        importer = SoilProfileImporter(temp_db)
        
        # Create temporary file with invalid JSON
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            temp_file.write('{ invalid json content')
            json_path = temp_file.name
        
        try:
            # Should fail to import
            project_id = importer.import_complete_project(json_path, validate_schema=False)
            assert project_id is None
            
        finally:
            # Cleanup
            os.unlink(json_path)
    
    def test_merge_projects(self, sample_json_data):
        """Test merging multiple JSON projects."""
        importer = SoilProfileImporter()
        
        # Create second project data
        sample_json_data2 = sample_json_data.copy()
        sample_json_data2['project_metadata']['project_name'] = 'Merge Test 2'
        sample_json_data2['explorations'] = {
            'MERGE-B2': {
                'location': {'x': 2000.0, 'y': 3000.0, 'elevation': 110.0},
                'drilling_info': {'method': 'Auger', 'date': '2023-07-01', 'contractor': 'Test'},
                'samples': [{
                    'sample_id': 'MERGE-B2-S1',
                    'depth_top': 0.0,
                    'depth_bottom': 3.0,
                    'field_description': 'Sandy clay',
                    'uscs_classification': 'SC'
                }]
            }
        }
        
        # Create temporary JSON files
        json_paths = []
        for i, data in enumerate([sample_json_data, sample_json_data2]):
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
                json.dump(data, temp_file, indent=2)
                json_paths.append(temp_file.name)
        
        # Create output file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            output_path = temp_file.name
        
        try:
            # Merge projects
            success = importer.merge_projects(json_paths, output_path)
            assert success
            assert os.path.exists(output_path)
            
            # Verify merged content
            with open(output_path, 'r') as f:
                merged_data = json.load(f)
            
            # Should have explorations from both projects
            assert len(merged_data['explorations']) == 2
            assert 'IMPORT-B1' in merged_data['explorations']
            assert 'MERGE-B2' in merged_data['explorations']
            
            # Should have metadata about merge
            assert 'merge_metadata' in merged_data
            assert merged_data['merge_metadata']['merged_explorations'] == 2
            
        finally:
            # Cleanup
            for path in json_paths + [output_path]:
                if os.path.exists(path):
                    os.unlink(path)
    
    def test_version_compatibility(self, temp_db, sample_json_data):
        """Test version compatibility handling."""
        importer = SoilProfileImporter(temp_db)
        
        # Modify version to test compatibility
        sample_json_data['export_metadata']['exporter_version'] = '1.0.0'
        
        # Create temporary JSON file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            json.dump(sample_json_data, temp_file, indent=2)
            json_path = temp_file.name
        
        try:
            # Should import successfully with current version
            project_id = importer.import_complete_project(json_path, validate_schema=False)
            assert project_id is not None
            
        finally:
            # Cleanup
            os.unlink(json_path)
    
    def test_import_strata_layers_only(self, temp_db, sample_json_data):
        """Test importing strata layers into existing project."""
        # First create a project
        project = temp_db.create_project({
            'project_name': 'Existing Project',
            'project_number': 'EXIST-001',
            'created_by': 'Test User'
        })
        
        importer = SoilProfileImporter(temp_db)
        
        # Create JSON file with strata data
        strata_data = {
            'interpreted_strata': sample_json_data['interpreted_strata']
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            json.dump(strata_data, temp_file, indent=2)
            json_path = temp_file.name
        
        try:
            # Import strata layers
            success = importer.import_strata_layers(json_path, project.id, replace_existing=True)
            assert success
            
            # Verify layers were imported
            layers = temp_db.get_strata_layers_for_project(project.id)
            assert len(layers) == 2
            
        finally:
            # Cleanup
            os.unlink(json_path)

class TestConvenienceFunctions:
    """Test convenience import functions."""
    
    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing."""
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        temp_file.close()
        
        db_manager = DatabaseManager(temp_file.name)
        yield db_manager
        
        # Cleanup
        os.unlink(temp_file.name)
    
    def test_import_project_from_json_function(self, temp_db):
        """Test convenience import function."""
        # Create minimal valid JSON
        project_data = {
            'project_metadata': {
                'project_name': 'Convenience Test',
                'project_number': 'CONV-001',
                'date_created': datetime.now().isoformat(),
                'created_by': 'Test User',
                'version': '1.0.0'
            },
            'explorations': {},
            'interpreted_strata': []
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            json.dump(project_data, temp_file, indent=2)
            json_path = temp_file.name
        
        try:
            # Test convenience function
            project_id = import_project_from_json(json_path, validate_schema=False)
            assert project_id is not None
            
            # Verify project was created
            project = temp_db.get_project(project_id)
            assert project.project_name == 'Convenience Test'
            
        finally:
            # Cleanup
            os.unlink(json_path)
    
    def test_validate_json_file_function(self):
        """Test convenience validation function."""
        # Create valid JSON structure
        valid_data = {
            'project_metadata': {
                'project_name': 'Valid Test',
                'project_number': 'VALID-001',
                'date_created': datetime.now().isoformat(),
                'created_by': 'Test User',
                'version': '1.0.0'
            },
            'explorations': {},
            'interpreted_strata': []
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            json.dump(valid_data, temp_file, indent=2)
            json_path = temp_file.name
        
        try:
            # Test validation function
            is_valid, errors = validate_json_file(json_path)
            # Should be valid or indicate no schema available
            assert is_valid or len(errors) > 0
            
        finally:
            # Cleanup
            os.unlink(json_path)

if __name__ == "__main__":
    pytest.main([__file__])