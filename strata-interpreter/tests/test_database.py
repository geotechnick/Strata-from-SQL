"""
Tests for database operations and models.
"""

import pytest
import tempfile
import os
from datetime import datetime
from core.database import DatabaseManager, Project, Borehole, Sample, TestResult, StrataLayer

class TestDatabaseManager:
    """Test database manager functionality."""
    
    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing."""
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        temp_file.close()
        
        db_manager = DatabaseManager(temp_file.name)
        yield db_manager
        
        # Cleanup
        os.unlink(temp_file.name)
    
    def test_create_project(self, temp_db):
        """Test project creation."""
        project_data = {
            'project_name': 'Test Project',
            'project_number': 'TEST-001',
            'client': 'Test Client',
            'location': 'Test Location',
            'created_by': 'Test User'
        }
        
        project = temp_db.create_project(project_data)
        
        assert project.id is not None
        assert project.project_name == 'Test Project'
        assert project.project_number == 'TEST-001'
    
    def test_get_project(self, temp_db):
        """Test project retrieval."""
        # Create project first
        project_data = {
            'project_name': 'Test Project',
            'project_number': 'TEST-002',
            'created_by': 'Test User'
        }
        
        created_project = temp_db.create_project(project_data)
        
        # Retrieve project
        retrieved_project = temp_db.get_project(created_project.id)
        
        assert retrieved_project is not None
        assert retrieved_project.project_name == 'Test Project'
        assert retrieved_project.id == created_project.id
    
    def test_create_borehole_with_samples(self, temp_db):
        """Test creating borehole with samples."""
        # Create project first
        project = temp_db.create_project({
            'project_name': 'Test Project',
            'project_number': 'TEST-003',
            'created_by': 'Test User'
        })
        
        # Create borehole
        with temp_db.get_session() as session:
            borehole = Borehole(
                borehole_id='B-1',
                project_id=project.id,
                x_coordinate=1000.0,
                y_coordinate=2000.0,
                elevation=100.0,
                drilling_method='Hollow Stem Auger'
            )
            session.add(borehole)
            session.flush()
            
            # Create sample
            sample = Sample(
                sample_id='B-1-S1',
                borehole_id=borehole.id,
                depth_top=2.0,
                depth_bottom=4.0,
                field_description='Brown silty clay',
                uscs_classification='CL',
                spt_n_value=8
            )
            session.add(sample)
            session.flush()
            
            # Verify relationships
            assert len(borehole.samples) == 1
            assert borehole.samples[0].sample_id == 'B-1-S1'
    
    def test_create_strata_layer(self, temp_db):
        """Test strata layer creation."""
        # Create project first
        project = temp_db.create_project({
            'project_name': 'Test Project',
            'project_number': 'TEST-004',
            'created_by': 'Test User'
        })
        
        layer_data = {
            'strata_id': 'Layer-1',
            'project_id': project.id,
            'top_elevation': 100.0,
            'bottom_elevation': 90.0,
            'soil_type': 'Silty Clay',
            'uscs_classification': 'CL',
            'design_parameters': '{"unit_weight": {"value": 120, "method": "laboratory"}}',
            'samples_used': '["B-1-S1", "B-1-S2"]',
            'interpreted_by': 'Test Engineer'
        }
        
        layer = temp_db.create_strata_layer(layer_data)
        
        assert layer.id is not None
        assert layer.strata_id == 'Layer-1'
        assert layer.top_elevation == 100.0
        assert layer.bottom_elevation == 90.0
    
    def test_get_boreholes_for_project(self, temp_db):
        """Test retrieving boreholes for a project."""
        # Create project
        project = temp_db.create_project({
            'project_name': 'Test Project',
            'project_number': 'TEST-005',
            'created_by': 'Test User'
        })
        
        # Create multiple boreholes
        with temp_db.get_session() as session:
            for i in range(3):
                borehole = Borehole(
                    borehole_id=f'B-{i+1}',
                    project_id=project.id,
                    x_coordinate=1000.0 + i * 100,
                    y_coordinate=2000.0,
                    elevation=100.0 - i * 5
                )
                session.add(borehole)
        
        # Retrieve boreholes
        boreholes = temp_db.get_boreholes_for_project(project.id)
        
        assert len(boreholes) == 3
        assert all(b.project_id == project.id for b in boreholes)
    
    def test_backup_database(self, temp_db):
        """Test database backup functionality."""
        # Create some data
        project = temp_db.create_project({
            'project_name': 'Backup Test',
            'project_number': 'BACKUP-001',
            'created_by': 'Test User'
        })
        
        # Create backup
        backup_path = tempfile.mktemp(suffix='.db')
        success = temp_db.backup_database(backup_path)
        
        assert success
        assert os.path.exists(backup_path)
        
        # Verify backup contains data
        backup_db = DatabaseManager(backup_path)
        backup_project = backup_db.get_project(project.id)
        assert backup_project is not None
        assert backup_project.project_name == 'Backup Test'
        
        # Cleanup
        os.unlink(backup_path)

class TestDatabaseModels:
    """Test database model relationships and constraints."""
    
    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing."""
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        temp_file.close()
        
        db_manager = DatabaseManager(temp_file.name)
        yield db_manager
        
        # Cleanup
        os.unlink(temp_file.name)
    
    def test_project_borehole_relationship(self, temp_db):
        """Test project-borehole relationship."""
        project = temp_db.create_project({
            'project_name': 'Relationship Test',
            'project_number': 'REL-001',
            'created_by': 'Test User'
        })
        
        with temp_db.get_session() as session:
            # Create borehole
            borehole = Borehole(
                borehole_id='REL-B1',
                project_id=project.id,
                x_coordinate=500.0,
                y_coordinate=1000.0,
                elevation=75.0
            )
            session.add(borehole)
            session.flush()
            
            # Test relationship
            assert borehole.project.project_name == 'Relationship Test'
            
            # Test reverse relationship
            project_from_db = session.query(Project).filter(Project.id == project.id).first()
            assert len(project_from_db.boreholes) == 1
            assert project_from_db.boreholes[0].borehole_id == 'REL-B1'
    
    def test_borehole_sample_relationship(self, temp_db):
        """Test borehole-sample relationship."""
        project = temp_db.create_project({
            'project_name': 'Sample Test',
            'project_number': 'SAMPLE-001',
            'created_by': 'Test User'
        })
        
        with temp_db.get_session() as session:
            # Create borehole
            borehole = Borehole(
                borehole_id='SAMPLE-B1',
                project_id=project.id,
                x_coordinate=600.0,
                y_coordinate=1200.0,
                elevation=80.0
            )
            session.add(borehole)
            session.flush()
            
            # Create multiple samples
            for i in range(3):
                sample = Sample(
                    sample_id=f'SAMPLE-B1-S{i+1}',
                    borehole_id=borehole.id,
                    depth_top=i * 2.0,
                    depth_bottom=(i + 1) * 2.0,
                    field_description=f'Sample {i+1} description'
                )
                session.add(sample)
            
            session.flush()
            
            # Test relationships
            assert len(borehole.samples) == 3
            assert all(s.borehole.borehole_id == 'SAMPLE-B1' for s in borehole.samples)
    
    def test_sample_depth_ordering(self, temp_db):
        """Test that samples are ordered by depth."""
        project = temp_db.create_project({
            'project_name': 'Depth Test',
            'project_number': 'DEPTH-001',
            'created_by': 'Test User'
        })
        
        with temp_db.get_session() as session:
            borehole = Borehole(
                borehole_id='DEPTH-B1',
                project_id=project.id,
                x_coordinate=700.0,
                y_coordinate=1400.0,
                elevation=85.0
            )
            session.add(borehole)
            session.flush()
            
            # Create samples in random order
            depths = [(4.0, 6.0), (0.0, 2.0), (2.0, 4.0), (6.0, 8.0)]
            for i, (top, bottom) in enumerate(depths):
                sample = Sample(
                    sample_id=f'DEPTH-B1-S{i+1}',
                    borehole_id=borehole.id,
                    depth_top=top,
                    depth_bottom=bottom,
                    field_description=f'Depth {top}-{bottom}'
                )
                session.add(sample)
            
            session.commit()
            
            # Retrieve samples ordered by depth
            samples = temp_db.get_samples_for_borehole(borehole.id)
            
            # Should be ordered by depth_top
            expected_order = [0.0, 2.0, 4.0, 6.0]
            actual_order = [s.depth_top for s in samples]
            
            assert actual_order == expected_order

if __name__ == "__main__":
    pytest.main([__file__])