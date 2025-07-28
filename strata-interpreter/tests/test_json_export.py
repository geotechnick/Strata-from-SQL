"""
Tests for JSON export functionality.
"""

import pytest
import json
import tempfile
import os
from datetime import datetime
from core.json_export import SoilProfileExporter, export_project_to_json
from core.database import DatabaseManager, Project, Borehole, Sample, StrataLayer

class TestSoilProfileExporter:
    """Test JSON export functionality."""
    
    @pytest.fixture
    def temp_db_with_data(self):
        """Create temporary database with test data."""
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        temp_file.close()
        
        db_manager = DatabaseManager(temp_file.name)
        
        # Create test project with data
        project = db_manager.create_project({
            'project_name': 'Export Test Project',
            'project_number': 'EXPORT-001',
            'client': 'Test Client',
            'location': 'Test Site',
            'created_by': 'Test Engineer'
        })
        
        with db_manager.get_session() as session:
            # Create borehole
            borehole = Borehole(
                borehole_id='EXPORT-B1',
                project_id=project.id,
                x_coordinate=1000.0,
                y_coordinate=2000.0,
                elevation=100.0,
                drilling_method='Hollow Stem Auger',
                drilling_contractor='Test Drilling Co.'
            )
            session.add(borehole)
            session.flush()
            
            # Create sample with test data
            sample = Sample(
                sample_id='EXPORT-B1-S1',
                borehole_id=borehole.id,
                depth_top=2.0,
                depth_bottom=4.0,
                field_description='Brown silty clay',
                uscs_classification='CL',
                spt_n_value=12,
                field_moisture=18.5
            )
            session.add(sample)
            session.flush()
            
            # Create strata layer
            layer = StrataLayer(
                strata_id='EXPORT-L1',
                project_id=project.id,
                top_elevation=100.0,
                bottom_elevation=95.0,
                soil_type='Silty Clay',
                uscs_classification='CL',
                design_parameters=json.dumps({
                    'unit_weight': {
                        'value': 120.0,
                        'method': 'laboratory_test',
                        'source': 'manual',
                        'confidence': 0.9
                    }
                }),
                samples_used=json.dumps(['EXPORT-B1-S1']),
                interpreted_by='Test Engineer'
            )
            session.add(layer)
        
        yield db_manager, project.id
        
        # Cleanup
        os.unlink(temp_file.name)
    
    def test_export_complete_project(self, temp_db_with_data):
        """Test exporting complete project to JSON."""
        db_manager, project_id = temp_db_with_data
        exporter = SoilProfileExporter(db_manager)
        
        # Create temporary output file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            output_path = temp_file.name
        
        try:
            # Export project
            success = exporter.export_complete_project(project_id, output_path)
            assert success
            assert os.path.exists(output_path)
            
            # Verify JSON structure
            with open(output_path, 'r') as f:
                data = json.load(f)
            
            # Check required top-level keys
            assert 'project_metadata' in data
            assert 'explorations' in data
            assert 'interpreted_strata' in data
            assert 'export_metadata' in data
            
            # Check project metadata
            project_meta = data['project_metadata']
            assert project_meta['project_name'] == 'Export Test Project'
            assert project_meta['project_number'] == 'EXPORT-001'
            assert project_meta['client'] == 'Test Client'
            
            # Check explorations
            explorations = data['explorations']
            assert 'EXPORT-B1' in explorations
            
            borehole_data = explorations['EXPORT-B1']
            assert 'location' in borehole_data
            assert 'samples' in borehole_data
            assert len(borehole_data['samples']) == 1
            
            # Check sample data
            sample_data = borehole_data['samples'][0]
            assert sample_data['sample_id'] == 'EXPORT-B1-S1'
            assert sample_data['depth_top'] == 2.0
            assert sample_data['depth_bottom'] == 4.0
            assert sample_data['uscs_classification'] == 'CL'
            
            # Check strata layers
            strata_layers = data['interpreted_strata']
            assert len(strata_layers) == 1
            
            layer_data = strata_layers[0]
            assert layer_data['strata_id'] == 'EXPORT-L1'
            assert layer_data['top_elevation'] == 100.0
            assert layer_data['soil_type'] == 'Silty Clay'
            assert 'design_parameters' in layer_data
            
            # Check design parameters
            design_params = layer_data['design_parameters']
            assert 'unit_weight' in design_params
            assert design_params['unit_weight']['value'] == 120.0
            
        finally:
            # Cleanup
            if os.path.exists(output_path):
                os.unlink(output_path)
    
    def test_export_with_compression(self, temp_db_with_data):
        """Test exporting with compression."""
        db_manager, project_id = temp_db_with_data
        exporter = SoilProfileExporter(db_manager)
        
        # Create temporary output file
        with tempfile.NamedTemporaryFile(suffix='.json.gz', delete=False) as temp_file:
            output_path = temp_file.name
        
        try:
            # Export with compression
            success = exporter.export_complete_project(project_id, output_path, compress=True)
            assert success
            assert os.path.exists(output_path)
            
            # Verify compressed file can be read
            import gzip
            with gzip.open(output_path, 'rt') as f:
                data = json.load(f)
            
            assert 'project_metadata' in data
            assert data['export_metadata']['compression'] == True
            
        finally:
            # Cleanup
            if os.path.exists(output_path):
                os.unlink(output_path)
    
    def test_export_strata_layer(self, temp_db_with_data):
        """Test exporting individual strata layer."""
        db_manager, project_id = temp_db_with_data
        exporter = SoilProfileExporter(db_manager)
        
        # Create temporary output file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            output_path = temp_file.name
        
        try:
            # Export single layer
            success = exporter.export_strata_layer('EXPORT-L1', output_path)
            assert success
            assert os.path.exists(output_path)
            
            # Verify JSON structure
            with open(output_path, 'r') as f:
                data = json.load(f)
            
            assert data['strata_id'] == 'EXPORT-L1'
            assert data['soil_type'] == 'Silty Clay'
            assert 'design_parameters' in data
            assert 'export_metadata' in data
            assert data['export_metadata']['export_type'] == 'single_layer'
            
        finally:
            # Cleanup
            if os.path.exists(output_path):
                os.unlink(output_path)
    
    def test_export_parameter_set(self, temp_db_with_data):
        """Test exporting parameter set."""
        db_manager, project_id = temp_db_with_data
        exporter = SoilProfileExporter(db_manager)
        
        # Create temporary output file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            output_path = temp_file.name
        
        try:
            # Export unit weight parameters
            success = exporter.export_parameter_set(project_id, 'unit_weight', output_path)
            assert success
            assert os.path.exists(output_path)
            
            # Verify JSON structure
            with open(output_path, 'r') as f:
                data = json.load(f)
            
            assert data['project_id'] == project_id
            assert data['parameter_type'] == 'unit_weight'
            assert 'layers' in data
            assert len(data['layers']) == 1
            
            layer_data = data['layers'][0]
            assert layer_data['strata_id'] == 'EXPORT-L1'
            assert 'parameter_data' in layer_data
            
        finally:
            # Cleanup
            if os.path.exists(output_path):
                os.unlink(output_path)
    
    def test_validate_export_data(self, temp_db_with_data):
        """Test export data validation."""
        db_manager, project_id = temp_db_with_data
        exporter = SoilProfileExporter(db_manager)
        
        # Valid data
        valid_data = {
            'project_metadata': {
                'project_name': 'Test',
                'project_number': 'TEST-001',
                'date_created': datetime.now().isoformat(),
                'created_by': 'Test User',
                'version': '1.0.0'
            },
            'explorations': {
                'B-1': {
                    'location': {'x': 1000, 'y': 2000, 'elevation': 100},
                    'drilling_info': {'method': 'Auger', 'date': '2023-01-01', 'contractor': 'Test'},
                    'samples': [
                        {
                            'sample_id': 'B-1-S1',
                            'depth_top': 0,
                            'depth_bottom': 2,
                            'field_description': 'Test'
                        }
                    ]
                }
            },
            'interpreted_strata': [
                {
                    'strata_id': 'L-1',
                    'top_elevation': 100,
                    'bottom_elevation': 98,
                    'soil_type': 'Clay',
                    'uscs_classification': 'CL',
                    'design_parameters': {},
                    'supporting_data': {'samples_used': []}
                }
            ]
        }
        
        assert exporter.validate_export_data(valid_data) == True
        
        # Invalid data - missing required keys
        invalid_data = {
            'project_metadata': {
                'project_name': 'Test'
                # Missing required keys
            },
            'explorations': {},
            'interpreted_strata': []
        }
        
        assert exporter.validate_export_data(invalid_data) == False
    
    def test_convenience_function(self, temp_db_with_data):
        """Test convenience export function."""
        db_manager, project_id = temp_db_with_data
        
        # Create temporary output file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            output_path = temp_file.name
        
        try:
            # Test convenience function
            success = export_project_to_json(project_id, output_path)
            assert success
            assert os.path.exists(output_path)
            
            # Verify content
            with open(output_path, 'r') as f:
                data = json.load(f)
            
            assert 'project_metadata' in data
            assert data['project_metadata']['project_name'] == 'Export Test Project'
            
        finally:
            # Cleanup
            if os.path.exists(output_path):
                os.unlink(output_path)

if __name__ == "__main__":
    pytest.main([__file__])