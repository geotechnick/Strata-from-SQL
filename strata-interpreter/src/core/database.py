"""
Database layer for DIGGS SQL integration and data management.

This module provides SQLAlchemy ORM models that match the DIGGS database structure
and handles database connections, migrations, and data operations.
"""

import logging
from typing import List, Optional, Dict, Any
from pathlib import Path
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String, Float, DateTime, Text, 
    ForeignKey, Boolean, JSON, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from sqlalchemy.exc import SQLAlchemyError
from contextlib import contextmanager

logger = logging.getLogger(__name__)

Base = declarative_base()

class Project(Base):
    """Project metadata table matching DIGGS structure."""
    __tablename__ = 'projects'
    
    id = Column(Integer, primary_key=True)
    project_name = Column(String(255), nullable=False)
    project_number = Column(String(100), nullable=False)
    client = Column(String(255))
    location = Column(String(500))
    description = Column(Text)
    coordinate_system = Column(String(100), default='State Plane')
    date_created = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String(100))
    version = Column(String(20), default='1.0.0')
    
    # Relationships
    boreholes = relationship("Borehole", back_populates="project", cascade="all, delete-orphan")
    strata_layers = relationship("StrataLayer", back_populates="project", cascade="all, delete-orphan")

class Borehole(Base):
    """Borehole information table (HoleInfo in DIGGS)."""
    __tablename__ = 'boreholes'
    
    id = Column(Integer, primary_key=True)
    borehole_id = Column(String(50), nullable=False, unique=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    
    # Location data
    x_coordinate = Column(Float, nullable=False)
    y_coordinate = Column(Float, nullable=False)
    elevation = Column(Float, nullable=False)
    
    # Drilling information
    drilling_method = Column(String(100))
    drilling_date = Column(DateTime)
    drilling_contractor = Column(String(255))
    total_depth = Column(Float)
    groundwater_depth = Column(Float)
    
    # Relationships
    project = relationship("Project", back_populates="boreholes")
    samples = relationship("Sample", back_populates="borehole", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('ix_borehole_location', 'x_coordinate', 'y_coordinate'),
    )

class TestMethod(Base):
    """Test methods and standards table."""
    __tablename__ = 'test_methods'
    
    id = Column(Integer, primary_key=True)
    method_name = Column(String(100), nullable=False)
    standard = Column(String(50))  # e.g., 'ASTM D422'
    description = Column(Text)
    version = Column(String(20))
    
    # Relationships
    test_results = relationship("TestResult", back_populates="test_method")

class Sample(Base):
    """Sample data with depth and description."""
    __tablename__ = 'samples'
    
    id = Column(Integer, primary_key=True)
    sample_id = Column(String(50), nullable=False)
    borehole_id = Column(Integer, ForeignKey('boreholes.id'), nullable=False)
    
    # Depth information
    depth_top = Column(Float, nullable=False)
    depth_bottom = Column(Float, nullable=False)
    
    # Description and classification
    field_description = Column(Text)
    uscs_classification = Column(String(10))
    
    # Field tests
    spt_n_value = Column(Float)
    field_moisture = Column(Float)
    penetration_resistance = Column(Float)
    
    # Relationships
    borehole = relationship("Borehole", back_populates="samples")
    test_results = relationship("TestResult", back_populates="sample", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('ix_sample_depth', 'depth_top', 'depth_bottom'),
    )

class TestResult(Base):
    """Generic test results table for all laboratory tests."""
    __tablename__ = 'test_results'
    
    id = Column(Integer, primary_key=True)
    sample_id = Column(Integer, ForeignKey('samples.id'), nullable=False)
    test_method_id = Column(Integer, ForeignKey('test_methods.id'), nullable=False)
    test_type = Column(String(50), nullable=False)  # gradation, atterberg, strength, etc.
    
    # Test data stored as JSON for flexibility
    test_data = Column(JSON)
    
    # Test metadata
    test_date = Column(DateTime)
    laboratory = Column(String(255))
    technician = Column(String(100))
    
    # Relationships
    sample = relationship("Sample", back_populates="test_results")
    test_method = relationship("TestMethod", back_populates="test_results")

class StrataLayer(Base):
    """Interpreted strata layers with design parameters."""
    __tablename__ = 'strata_layers'
    
    id = Column(Integer, primary_key=True)
    strata_id = Column(String(50), nullable=False)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    
    # Layer geometry
    top_elevation = Column(Float, nullable=False)
    bottom_elevation = Column(Float, nullable=False)
    
    # Soil properties
    soil_type = Column(String(100), nullable=False)
    uscs_classification = Column(String(10), nullable=False)
    
    # Design parameters stored as JSON for flexibility
    design_parameters = Column(JSON)
    
    # Supporting data
    samples_used = Column(JSON)  # Array of sample IDs
    calculation_details = Column(JSON)
    references = Column(JSON)  # Array of citations
    
    # Metadata
    interpreted_by = Column(String(100))
    interpretation_date = Column(DateTime, default=datetime.utcnow)
    confidence_level = Column(Float)  # 0.0 to 1.0
    
    # Relationships
    project = relationship("Project", back_populates="strata_layers")
    
    __table_args__ = (
        Index('ix_strata_elevation', 'top_elevation', 'bottom_elevation'),
    )

class DatabaseManager:
    """Database connection and session management."""
    
    def __init__(self, database_path: Optional[str] = None):
        """
        Initialize database manager.
        
        Args:
            database_path: Path to SQLite database file
        """
        if database_path is None:
            database_path = "strata_project.db"
        
        self.database_path = Path(database_path)
        self.engine = None
        self.Session = None
        self._setup_database()
    
    def _setup_database(self):
        """Setup database engine and session factory."""
        try:
            # Create SQLite engine with connection pooling
            self.engine = create_engine(
                f"sqlite:///{self.database_path}",
                echo=False,
                pool_pre_ping=True,
                connect_args={'check_same_thread': False}
            )
            
            # Create session factory
            self.Session = sessionmaker(bind=self.engine)
            
            # Create tables if they don't exist
            Base.metadata.create_all(self.engine)
            
            logger.info(f"Database initialized: {self.database_path}")
            
        except SQLAlchemyError as e:
            logger.error(f"Database setup failed: {e}")
            raise
    
    @contextmanager
    def get_session(self):
        """
        Context manager for database sessions.
        
        Yields:
            Session: SQLAlchemy session
        """
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    def create_project(self, project_data: Dict[str, Any]) -> Project:
        """
        Create new project.
        
        Args:
            project_data: Project information dictionary
            
        Returns:
            Created project instance
        """
        with self.get_session() as session:
            project = Project(**project_data)
            session.add(project)
            session.flush()  # Get the ID
            return project
    
    def get_project(self, project_id: int) -> Optional[Project]:
        """
        Get project by ID.
        
        Args:
            project_id: Project ID
            
        Returns:
            Project instance or None
        """
        with self.get_session() as session:
            return session.query(Project).filter(Project.id == project_id).first()
    
    def import_diggs_database(self, diggs_db_path: str) -> bool:
        """
        Import data from existing DIGGS SQL database.
        
        Args:
            diggs_db_path: Path to DIGGS database file
            
        Returns:
            True if import successful, False otherwise
        """
        try:
            # Create engine for DIGGS database
            diggs_engine = create_engine(f"sqlite:///{diggs_db_path}")
            
            with self.get_session() as session:
                # Import logic will be implemented based on DIGGS schema
                # This is a placeholder for the actual import implementation
                logger.info(f"Starting import from DIGGS database: {diggs_db_path}")
                
                # TODO: Implement actual DIGGS data import mapping
                # This would involve:
                # 1. Reading DIGGS tables
                # 2. Mapping to our schema
                # 3. Creating corresponding records
                
                return True
                
        except Exception as e:
            logger.error(f"DIGGS import failed: {e}")
            return False
    
    def backup_database(self, backup_path: Optional[str] = None) -> bool:
        """
        Create database backup.
        
        Args:
            backup_path: Path for backup file
            
        Returns:
            True if backup successful, False otherwise
        """
        try:
            if backup_path is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = f"{self.database_path.stem}_backup_{timestamp}.db"
            
            # Simple file copy for SQLite
            import shutil
            shutil.copy2(self.database_path, backup_path)
            
            logger.info(f"Database backup created: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Database backup failed: {e}")
            return False
    
    def get_boreholes_for_project(self, project_id: int) -> List[Borehole]:
        """
        Get all boreholes for a project.
        
        Args:
            project_id: Project ID
            
        Returns:
            List of boreholes
        """
        with self.get_session() as session:
            return session.query(Borehole).filter(
                Borehole.project_id == project_id
            ).all()
    
    def get_samples_for_borehole(self, borehole_id: int) -> List[Sample]:
        """
        Get all samples for a borehole.
        
        Args:
            borehole_id: Borehole ID
            
        Returns:
            List of samples
        """
        with self.get_session() as session:
            return session.query(Sample).filter(
                Sample.borehole_id == borehole_id
            ).order_by(Sample.depth_top).all()
    
    def get_test_results_for_sample(self, sample_id: int) -> List[TestResult]:
        """
        Get all test results for a sample.
        
        Args:
            sample_id: Sample ID
            
        Returns:
            List of test results
        """
        with self.get_session() as session:
            return session.query(TestResult).filter(
                TestResult.sample_id == sample_id
            ).all()
    
    def create_strata_layer(self, layer_data: Dict[str, Any]) -> StrataLayer:
        """
        Create new strata layer.
        
        Args:
            layer_data: Layer information dictionary
            
        Returns:
            Created strata layer instance
        """
        with self.get_session() as session:
            layer = StrataLayer(**layer_data)
            session.add(layer)
            session.flush()
            return layer
    
    def update_strata_layer(self, layer_id: int, update_data: Dict[str, Any]) -> bool:
        """
        Update existing strata layer.
        
        Args:
            layer_id: Layer ID
            update_data: Data to update
            
        Returns:
            True if update successful, False otherwise
        """
        try:
            with self.get_session() as session:
                layer = session.query(StrataLayer).filter(
                    StrataLayer.id == layer_id
                ).first()
                
                if layer:
                    for key, value in update_data.items():
                        if hasattr(layer, key):
                            setattr(layer, key, value)
                    return True
                return False
                
        except Exception as e:
            logger.error(f"Strata layer update failed: {e}")
            return False
    
    def get_strata_layers_for_project(self, project_id: int) -> List[StrataLayer]:
        """
        Get all strata layers for a project.
        
        Args:
            project_id: Project ID
            
        Returns:
            List of strata layers ordered by elevation
        """
        with self.get_session() as session:
            return session.query(StrataLayer).filter(
                StrataLayer.project_id == project_id
            ).order_by(StrataLayer.top_elevation.desc()).all()

# Global database manager instance
db_manager: Optional[DatabaseManager] = None

def initialize_database(database_path: Optional[str] = None) -> DatabaseManager:
    """
    Initialize global database manager.
    
    Args:
        database_path: Path to database file
        
    Returns:
        Database manager instance
    """
    global db_manager
    db_manager = DatabaseManager(database_path)
    return db_manager

def get_database_manager() -> DatabaseManager:
    """
    Get global database manager instance.
    
    Returns:
        Database manager instance
        
    Raises:
        RuntimeError: If database not initialized
    """
    if db_manager is None:
        raise RuntimeError("Database not initialized. Call initialize_database() first.")
    return db_manager