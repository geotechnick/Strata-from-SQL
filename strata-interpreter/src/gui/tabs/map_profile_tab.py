"""
Map and profile tab for exploration locations and subsurface profiles.

This tab provides an interactive map showing exploration locations and
cross-section generation between selected boreholes.
"""

import logging
from typing import List, Dict, Optional, Tuple
import numpy as np
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QPushButton,
    QLabel, QComboBox, QCheckBox, QSpinBox, QGroupBox, QListWidget,
    QListWidgetItem, QMessageBox, QProgressBar
)
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot, QThread, QObject
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtGui import QPixmap, QPainter, QColor
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import folium
from folium import plugins
import tempfile
import os

from core.database import get_database_manager
from utils.color_schemes import get_uscs_color, is_fine_grained, is_granular
from core.models import USCSClassification

logger = logging.getLogger(__name__)

class ProfileGeneratorWorker(QObject):
    """Worker thread for generating cross-section profiles."""
    
    finished = pyqtSignal(object)  # Emits the generated profile data
    progress = pyqtSignal(int)     # Progress percentage
    error = pyqtSignal(str)        # Error message
    
    def __init__(self, borehole_ids: List[str], project_id: int):
        super().__init__()
        self.borehole_ids = borehole_ids
        self.project_id = project_id
    
    def run(self):
        """Generate cross-section profile."""
        try:
            db_manager = get_database_manager()
            self.progress.emit(10)
            
            # Get borehole data
            boreholes = []
            with db_manager.get_session() as session:
                from core.database import Borehole
                
                for i, borehole_id in enumerate(self.borehole_ids):
                    borehole = session.query(Borehole).filter(
                        Borehole.borehole_id == borehole_id,
                        Borehole.project_id == self.project_id
                    ).first()
                    
                    if borehole:
                        boreholes.append(borehole)
                    
                    self.progress.emit(10 + (i + 1) * 30 // len(self.borehole_ids))
            
            if len(boreholes) < 2:
                self.error.emit("At least 2 boreholes required for cross-section")
                return
            
            # Generate profile data
            profile_data = self._generate_profile_data(boreholes)
            self.progress.emit(80)
            
            # Calculate distances and elevations
            profile_data = self._calculate_profile_geometry(profile_data)
            self.progress.emit(100)
            
            self.finished.emit(profile_data)
            
        except Exception as e:
            logger.error(f"Profile generation failed: {e}")
            self.error.emit(str(e))
    
    def _generate_profile_data(self, boreholes) -> Dict:
        """Generate profile data from boreholes."""
        profile_data = {
            'boreholes': [],
            'distances': [],
            'elevations': [],
            'samples': []
        }
        
        db_manager = get_database_manager()
        
        with db_manager.get_session() as session:
            from core.database import Sample
            
            for borehole in boreholes:
                borehole_data = {
                    'id': borehole.borehole_id,
                    'x': borehole.x_coordinate,
                    'y': borehole.y_coordinate,
                    'elevation': borehole.elevation,
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
                        'elevation_top': borehole.elevation - sample.depth_top,
                        'elevation_bottom': borehole.elevation - sample.depth_bottom,
                        'description': sample.field_description,
                        'uscs': sample.uscs_classification,
                        'spt_n': sample.spt_n_value
                    }
                    borehole_data['samples'].append(sample_data)
                
                profile_data['boreholes'].append(borehole_data)
        
        return profile_data
    
    def _calculate_profile_geometry(self, profile_data: Dict) -> Dict:
        """Calculate distances and elevations for profile."""
        boreholes = profile_data['boreholes']
        
        if len(boreholes) < 2:
            return profile_data
        
        # Sort boreholes by distance along profile line
        # For simplicity, sort by X coordinate (can be enhanced to follow actual profile line)
        boreholes.sort(key=lambda b: b['x'])
        
        # Calculate cumulative distances
        distances = [0.0]
        for i in range(1, len(boreholes)):
            dx = boreholes[i]['x'] - boreholes[i-1]['x']
            dy = boreholes[i]['y'] - boreholes[i-1]['y']
            distance = np.sqrt(dx**2 + dy**2)
            distances.append(distances[-1] + distance)
        
        profile_data['distances'] = distances
        profile_data['elevations'] = [b['elevation'] for b in boreholes]
        
        return profile_data

class MapProfileTab(QWidget):
    """Tab for map visualization and profile generation."""
    
    # Signals
    boreholes_selected = pyqtSignal(list)  # Emitted when boreholes are selected
    profile_generated = pyqtSignal(object)  # Emitted when profile is generated
    
    def __init__(self, project_id: int):
        super().__init__()
        self.project_id = project_id
        self.selected_boreholes: List[str] = []
        self.borehole_data: Dict = {}
        self.current_profile = None
        
        self._setup_ui()
        self._load_project_data()
    
    def _setup_ui(self):
        """Setup the user interface."""
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # Create main splitter (horizontal)
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(main_splitter)
        
        # Left panel: Map and controls
        left_panel = self._create_left_panel()
        main_splitter.addWidget(left_panel)
        
        # Right panel: Profile view
        right_panel = self._create_right_panel()
        main_splitter.addWidget(right_panel)
        
        # Set splitter proportions
        main_splitter.setSizes([600, 400])
        
        # Status bar
        self.status_label = QLabel("Ready")
        main_layout.addWidget(self.status_label)
    
    def _create_left_panel(self) -> QWidget:
        """Create left panel with map and controls."""
        left_widget = QWidget()
        layout = QVBoxLayout(left_widget)
        
        # Map controls
        controls_group = QGroupBox("Map Controls")
        controls_layout = QHBoxLayout(controls_group)
        
        # Refresh map button
        self.refresh_btn = QPushButton("Refresh Map")
        self.refresh_btn.clicked.connect(self._refresh_map)
        controls_layout.addWidget(self.refresh_btn)
        
        # Show labels checkbox
        self.show_labels_cb = QCheckBox("Show Borehole Labels")
        self.show_labels_cb.setChecked(True)
        self.show_labels_cb.toggled.connect(self._refresh_map)
        controls_layout.addWidget(self.show_labels_cb)
        
        controls_layout.addStretch()
        layout.addWidget(controls_group)
        
        # Map view
        self.map_view = QWebEngineView()
        self.map_view.setMinimumHeight(400)
        layout.addWidget(self.map_view)
        
        # Borehole selection
        selection_group = QGroupBox("Borehole Selection")
        selection_layout = QVBoxLayout(selection_group)
        
        selection_info = QLabel("Select boreholes on the map or from the list below:")
        selection_layout.addWidget(selection_info)
        
        self.borehole_list = QListWidget()
        self.borehole_list.setMaximumHeight(120)
        self.borehole_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.borehole_list.itemSelectionChanged.connect(self._on_list_selection_changed)
        selection_layout.addWidget(self.borehole_list)
        
        # Selection buttons
        button_layout = QHBoxLayout()
        
        self.select_all_btn = QPushButton("Select All")
        self.select_all_btn.clicked.connect(self._select_all_boreholes)
        button_layout.addWidget(self.select_all_btn)
        
        self.clear_selection_btn = QPushButton("Clear Selection")
        self.clear_selection_btn.clicked.connect(self._clear_selection)
        button_layout.addWidget(self.clear_selection_btn)
        
        selection_layout.addLayout(button_layout)
        layout.addWidget(selection_group)
        
        return left_widget
    
    def _create_right_panel(self) -> QWidget:
        """Create right panel with profile view and controls."""
        right_widget = QWidget()
        layout = QVBoxLayout(right_widget)
        
        # Profile controls
        profile_group = QGroupBox("Cross-Section Profile")
        profile_layout = QVBoxLayout(profile_group)
        
        # Generate profile button and settings
        button_layout = QHBoxLayout()
        
        self.generate_profile_btn = QPushButton("Generate Profile")
        self.generate_profile_btn.clicked.connect(self._generate_profile)
        self.generate_profile_btn.setEnabled(False)
        button_layout.addWidget(self.generate_profile_btn)
        
        # Vertical exaggeration
        exag_label = QLabel("V. Exag:")
        button_layout.addWidget(exag_label)
        
        self.v_exag_spin = QSpinBox()
        self.v_exag_spin.setRange(1, 20)
        self.v_exag_spin.setValue(5)
        self.v_exag_spin.setSuffix("x")
        button_layout.addWidget(self.v_exag_spin)
        
        button_layout.addStretch()
        profile_layout.addLayout(button_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.hide()
        profile_layout.addWidget(self.progress_bar)
        
        # Profile plot
        self.profile_figure = Figure(figsize=(8, 6))
        self.profile_canvas = FigureCanvas(self.profile_figure)
        self.profile_canvas.setMinimumHeight(300)
        profile_layout.addWidget(self.profile_canvas)
        
        layout.addWidget(profile_group)
        
        # Profile information
        info_group = QGroupBox("Profile Information")
        info_layout = QVBoxLayout(info_group)
        
        self.profile_info_label = QLabel("No profile generated")
        self.profile_info_label.setWordWrap(True)
        info_layout.addWidget(self.profile_info_label)
        
        layout.addWidget(info_group)
        
        return right_widget
    
    def _load_project_data(self):
        """Load project borehole data."""
        try:
            db_manager = get_database_manager()
            boreholes = db_manager.get_boreholes_for_project(self.project_id)
            
            self.borehole_data = {}
            self.borehole_list.clear()
            
            for borehole in boreholes:
                self.borehole_data[borehole.borehole_id] = {
                    'id': borehole.borehole_id,
                    'x': borehole.x_coordinate,
                    'y': borehole.y_coordinate,
                    'elevation': borehole.elevation,
                    'method': borehole.drilling_method,
                    'date': borehole.drilling_date
                }
                
                # Add to list widget
                item = QListWidgetItem(f"{borehole.borehole_id} (El. {borehole.elevation:.1f})")
                item.setData(Qt.ItemDataRole.UserRole, borehole.borehole_id)
                self.borehole_list.addItem(item)
            
            logger.info(f"Loaded {len(boreholes)} boreholes for project {self.project_id}")
            
            # Generate initial map
            self._refresh_map()
            
        except Exception as e:
            logger.error(f"Failed to load project data: {e}")
            QMessageBox.critical(self, "Data Error", f"Failed to load project data:\n{e}")
    
    def _refresh_map(self):
        """Refresh the map display."""
        try:
            if not self.borehole_data:
                return
            
            # Calculate map center
            lats = [data['y'] for data in self.borehole_data.values()]
            lons = [data['x'] for data in self.borehole_data.values()]
            
            center_lat = sum(lats) / len(lats)
            center_lon = sum(lons) / len(lons)
            
            # Create folium map
            m = folium.Map(
                location=[center_lat, center_lon],
                zoom_start=15,
                tiles='OpenStreetMap'
            )
            
            # Add borehole markers
            for borehole_id, data in self.borehole_data.items():
                # Determine marker color based on selection
                color = 'red' if borehole_id in self.selected_boreholes else 'blue'
                
                # Create popup content
                popup_content = f"""
                <b>{borehole_id}</b><br>
                Elevation: {data['elevation']:.1f} ft<br>
                Coordinates: ({data['x']:.1f}, {data['y']:.1f})<br>
                Method: {data.get('method', 'Unknown')}<br>
                Date: {data.get('date', 'Unknown')}
                """
                
                marker = folium.Marker(
                    location=[data['y'], data['x']],
                    popup=folium.Popup(popup_content, max_width=200),
                    tooltip=borehole_id,
                    icon=folium.Icon(color=color, icon='info-sign')
                )
                marker.add_to(m)
                
                # Add label if enabled
                if self.show_labels_cb.isChecked():
                    folium.map.Marker(
                        location=[data['y'], data['x']],
                        icon=folium.DivIcon(
                            html=f'<div style="font-size: 10pt; font-weight: bold; '
                                 f'color: black; background: white; padding: 2px; '
                                 f'border-radius: 3px;">{borehole_id}</div>',
                            icon_size=(60, 20),
                            icon_anchor=(30, 10)
                        )
                    ).add_to(m)
            
            # Add selected boreholes connection line
            if len(self.selected_boreholes) >= 2:
                selected_coords = []
                for borehole_id in self.selected_boreholes:
                    if borehole_id in self.borehole_data:
                        data = self.borehole_data[borehole_id]
                        selected_coords.append([data['y'], data['x']])
                
                if len(selected_coords) >= 2:
                    folium.PolyLine(
                        selected_coords,
                        color='red',
                        weight=3,
                        opacity=0.8,
                        popup='Profile Line'
                    ).add_to(m)
            
            # Save map to temporary file and load
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
                m.save(f.name)
                self.map_view.load(f"file://{f.name}")
            
            self.status_label.setText(f"Map updated - {len(self.borehole_data)} boreholes")
            
        except Exception as e:
            logger.error(f"Failed to refresh map: {e}")
            self.status_label.setText(f"Map error: {e}")
    
    @pyqtSlot()
    def _on_list_selection_changed(self):
        """Handle borehole list selection changes."""
        selected_items = self.borehole_list.selectedItems()
        self.selected_boreholes = []
        
        for item in selected_items:
            borehole_id = item.data(Qt.ItemDataRole.UserRole)
            if borehole_id:
                self.selected_boreholes.append(borehole_id)
        
        # Update generate button state
        self.generate_profile_btn.setEnabled(len(self.selected_boreholes) >= 2)
        
        # Refresh map to show selected boreholes
        self._refresh_map()
        
        # Emit signal
        self.boreholes_selected.emit(self.selected_boreholes)
        
        self.status_label.setText(f"Selected {len(self.selected_boreholes)} boreholes")
    
    @pyqtSlot()
    def _select_all_boreholes(self):
        """Select all boreholes."""
        self.borehole_list.selectAll()
    
    @pyqtSlot()
    def _clear_selection(self):
        """Clear borehole selection."""
        self.borehole_list.clearSelection()
    
    @pyqtSlot()
    def _generate_profile(self):
        """Generate cross-section profile."""
        if len(self.selected_boreholes) < 2:
            QMessageBox.information(self, "Profile Generation", 
                                  "Please select at least 2 boreholes for cross-section")
            return
        
        try:
            # Show progress
            self.progress_bar.show()
            self.progress_bar.setRange(0, 100)
            self.generate_profile_btn.setEnabled(False)
            
            # Create worker thread
            self.profile_worker = ProfileGeneratorWorker(self.selected_boreholes, self.project_id)
            self.profile_thread = QThread()
            
            # Move worker to thread
            self.profile_worker.moveToThread(self.profile_thread)
            
            # Connect signals
            self.profile_thread.started.connect(self.profile_worker.run)
            self.profile_worker.progress.connect(self.progress_bar.setValue)
            self.profile_worker.finished.connect(self._on_profile_generated)
            self.profile_worker.error.connect(self._on_profile_error)
            self.profile_worker.finished.connect(self.profile_thread.quit)
            self.profile_worker.finished.connect(self.profile_worker.deleteLater)
            self.profile_thread.finished.connect(self.profile_thread.deleteLater)
            
            # Start thread
            self.profile_thread.start()
            
        except Exception as e:
            logger.error(f"Failed to start profile generation: {e}")
            self._reset_profile_ui()
            QMessageBox.critical(self, "Profile Error", f"Failed to generate profile:\n{e}")
    
    @pyqtSlot(object)
    def _on_profile_generated(self, profile_data):
        """Handle completed profile generation."""
        try:
            self.current_profile = profile_data
            self._plot_profile(profile_data)
            self._update_profile_info(profile_data)
            
            self.profile_generated.emit(profile_data)
            self.status_label.setText("Profile generated successfully")
            
        except Exception as e:
            logger.error(f"Failed to display profile: {e}")
            QMessageBox.critical(self, "Profile Error", f"Failed to display profile:\n{e}")
        finally:
            self._reset_profile_ui()
    
    @pyqtSlot(str)
    def _on_profile_error(self, error_message):
        """Handle profile generation error."""
        logger.error(f"Profile generation error: {error_message}")
        QMessageBox.critical(self, "Profile Error", f"Profile generation failed:\n{error_message}")
        self._reset_profile_ui()
    
    def _reset_profile_ui(self):
        """Reset profile UI after generation."""
        self.progress_bar.hide()
        self.generate_profile_btn.setEnabled(len(self.selected_boreholes) >= 2)
    
    def _plot_profile(self, profile_data):
        """Plot the cross-section profile."""
        try:
            self.profile_figure.clear()
            ax = self.profile_figure.add_subplot(111)
            
            boreholes = profile_data['boreholes']
            distances = profile_data['distances']
            
            if not boreholes or not distances:
                ax.text(0.5, 0.5, 'No data to display', 
                       transform=ax.transAxes, ha='center', va='center')
                self.profile_canvas.draw()
                return
            
            # Plot ground surface
            elevations = [b['elevation'] for b in boreholes]
            ax.plot(distances, elevations, 'k-', linewidth=2, label='Ground Surface')
            
            # Plot boreholes and soil layers
            for i, (borehole, distance) in enumerate(zip(boreholes, distances)):
                # Draw borehole line
                if borehole['samples']:
                    max_depth = max(s['depth_bottom'] for s in borehole['samples'])
                    bottom_elevation = borehole['elevation'] - max_depth
                    ax.plot([distance, distance], [borehole['elevation'], bottom_elevation], 
                           'k-', linewidth=1, alpha=0.5)
                
                # Draw soil layers
                for sample in borehole['samples']:
                    layer_top = sample['elevation_top']
                    layer_bottom = sample['elevation_bottom']
                    
                    # Get color based on USCS classification
                    if sample['uscs']:
                        try:
                            uscs_enum = USCSClassification(sample['uscs'])
                            color = get_uscs_color(uscs_enum)
                            face_color = color.name()
                        except (ValueError, KeyError):
                            face_color = 'lightgray'
                    else:
                        face_color = 'lightgray'
                    
                    # Draw layer rectangle
                    width = distances[-1] * 0.02  # 2% of total distance
                    rect = plt.Rectangle(
                        (distance - width/2, layer_bottom),
                        width,
                        layer_top - layer_bottom,
                        facecolor=face_color,
                        edgecolor='black',
                        linewidth=0.5,
                        alpha=0.8
                    )
                    ax.add_patch(rect)
                
                # Add borehole label
                ax.text(distance, borehole['elevation'] + 2, borehole['id'],
                       ha='center', va='bottom', fontsize=8, fontweight='bold')
            
            # Formatting
            ax.set_xlabel('Distance (ft)')
            ax.set_ylabel('Elevation (ft)')
            ax.set_title(f'Cross-Section Profile - {len(boreholes)} Boreholes')
            ax.grid(True, alpha=0.3)
            ax.legend()
            
            # Apply vertical exaggeration
            v_exag = self.v_exag_spin.value()
            if v_exag > 1:
                # Calculate current aspect ratio
                x_range = max(distances) - min(distances) if distances else 1
                y_range = max(elevations) - min(elevations) if elevations else 1
                
                if x_range > 0 and y_range > 0:
                    current_ratio = x_range / y_range
                    new_ratio = current_ratio / v_exag
                    ax.set_aspect(new_ratio)
            
            self.profile_figure.tight_layout()
            self.profile_canvas.draw()
            
        except Exception as e:
            logger.error(f"Failed to plot profile: {e}")
            ax.text(0.5, 0.5, f'Plot error: {e}', 
                   transform=ax.transAxes, ha='center', va='center')
            self.profile_canvas.draw()
    
    def _update_profile_info(self, profile_data):
        """Update profile information display."""
        try:
            boreholes = profile_data['boreholes']
            distances = profile_data['distances']
            
            if not boreholes:
                self.profile_info_label.setText("No profile data available")
                return
            
            total_distance = distances[-1] if distances else 0
            elevation_range = (
                max(b['elevation'] for b in boreholes) - 
                min(b['elevation'] for b in boreholes)
            )
            
            # Count samples
            total_samples = sum(len(b['samples']) for b in boreholes)
            
            # Get soil types
            soil_types = set()
            for borehole in boreholes:
                for sample in borehole['samples']:
                    if sample['uscs']:
                        soil_types.add(sample['uscs'])
            
            info_text = f"""
<b>Profile Statistics:</b><br>
• Total Distance: {total_distance:.1f} ft<br>
• Elevation Range: {elevation_range:.1f} ft<br>
• Boreholes: {len(boreholes)}<br>
• Total Samples: {total_samples}<br>
• Soil Types: {', '.join(sorted(soil_types)) if soil_types else 'None classified'}
            """.strip()
            
            self.profile_info_label.setText(info_text)
            
        except Exception as e:
            logger.error(f"Failed to update profile info: {e}")
            self.profile_info_label.setText(f"Info error: {e}")

if __name__ == "__main__":
    # Test the tab independently
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # Mock project ID for testing
    tab = MapProfileTab(project_id=1)
    tab.show()
    
    sys.exit(app.exec())