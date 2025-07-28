"""
Index values tab for displaying tabular data and elevation plots.

This tab shows N-values, plasticity index, and % passing #200 sieve
with interactive tables and elevation-based plotting.
"""

import logging
from typing import List, Dict, Optional, Any, Tuple
import numpy as np
import pandas as pd
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QTableWidget, QTableWidgetItem,
    QHeaderView, QPushButton, QLabel, QComboBox, QCheckBox, QSpinBox, QGroupBox,
    QTabWidget, QMessageBox, QFileDialog, QProgressBar, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot, QThread, QObject, QAbstractTableModel, QModelIndex
from PyQt6.QtGui import QAction, QColor, QBrush
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import pyqtgraph as pg

from core.database import get_database_manager
from utils.color_schemes import get_uscs_color, is_fine_grained, is_granular
from core.models import USCSClassification

logger = logging.getLogger(__name__)

class IndexDataModel(QAbstractTableModel):
    """Table model for index values data."""
    
    def __init__(self, data: List[Dict[str, Any]]):
        super().__init__()
        self.data = data
        self.headers = [
            'Borehole', 'Sample ID', 'Depth Top', 'Depth Bottom', 'Elevation Top', 'Elevation Bottom',
            'USCS', 'N-Value', 'Plasticity Index', '% Passing #200', 'Description'
        ]
    
    def rowCount(self, parent=QModelIndex()):
        return len(self.data)
    
    def columnCount(self, parent=QModelIndex()):
        return len(self.headers)
    
    def data(self, index, role):
        if not index.isValid():
            return None
        
        row = index.row()
        col = index.column()
        
        if row >= len(self.data):
            return None
        
        item = self.data[row]
        
        if role == Qt.ItemDataRole.DisplayRole:
            if col == 0:  # Borehole
                return item.get('borehole_id', '')
            elif col == 1:  # Sample ID
                return item.get('sample_id', '')
            elif col == 2:  # Depth Top
                return f"{item.get('depth_top', 0):.1f}"
            elif col == 3:  # Depth Bottom
                return f"{item.get('depth_bottom', 0):.1f}"
            elif col == 4:  # Elevation Top
                return f"{item.get('elevation_top', 0):.1f}"
            elif col == 5:  # Elevation Bottom
                return f"{item.get('elevation_bottom', 0):.1f}"
            elif col == 6:  # USCS
                return item.get('uscs_classification', '')
            elif col == 7:  # N-Value
                n_val = item.get('spt_n_value')
                return f"{n_val}" if n_val is not None else ''
            elif col == 8:  # Plasticity Index
                pi = item.get('plasticity_index')
                return f"{pi}" if pi is not None else ''
            elif col == 9:  # % Passing #200
                passing = item.get('fines_percent')
                return f"{passing}" if passing is not None else ''
            elif col == 10:  # Description
                return item.get('field_description', '')
        
        elif role == Qt.ItemDataRole.BackgroundRole:
            # Color code by USCS classification
            uscs = item.get('uscs_classification')
            if uscs:
                try:
                    uscs_enum = USCSClassification(uscs)
                    color = get_uscs_color(uscs_enum)
                    # Make color lighter for background
                    color.setAlpha(100)
                    return QBrush(color)
                except (ValueError, KeyError):
                    pass
        
        return None
    
    def headerData(self, section, orientation, role):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self.headers[section]
        return None
    
    def sort(self, column, order):
        """Sort data by column."""
        reverse = order == Qt.SortOrder.DescendingOrder
        
        def sort_key(item):
            if column == 0:  # Borehole
                return item.get('borehole_id', '')
            elif column == 1:  # Sample ID
                return item.get('sample_id', '')
            elif column == 2:  # Depth Top
                return item.get('depth_top', 0)
            elif column == 3:  # Depth Bottom
                return item.get('depth_bottom', 0)
            elif column == 4:  # Elevation Top
                return item.get('elevation_top', 0)
            elif column == 5:  # Elevation Bottom
                return item.get('elevation_bottom', 0)
            elif column == 6:  # USCS
                return item.get('uscs_classification', '')
            elif column == 7:  # N-Value
                return item.get('spt_n_value') or 0
            elif column == 8:  # Plasticity Index
                return item.get('plasticity_index') or 0
            elif column == 9:  # % Passing #200
                return item.get('fines_percent') or 0
            elif column == 10:  # Description
                return item.get('field_description', '')
            return ''
        
        self.beginResetModel()
        self.data.sort(key=sort_key, reverse=reverse)
        self.endResetModel()

class DataLoaderWorker(QObject):
    """Worker thread for loading index data."""
    
    finished = pyqtSignal(list)  # Emits loaded data
    progress = pyqtSignal(int)   # Progress percentage
    error = pyqtSignal(str)      # Error message
    
    def __init__(self, project_id: int):
        super().__init__()
        self.project_id = project_id
    
    def run(self):
        """Load index data from database."""
        try:
            db_manager = get_database_manager()
            self.progress.emit(10)
            
            data = []
            
            with db_manager.get_session() as session:
                from core.database import Borehole, Sample, TestResult
                import json
                
                # Get all boreholes for project
                boreholes = session.query(Borehole).filter(
                    Borehole.project_id == self.project_id
                ).all()
                
                self.progress.emit(20)
                
                total_boreholes = len(boreholes)
                
                for i, borehole in enumerate(boreholes):
                    # Get samples for this borehole
                    samples = session.query(Sample).filter(
                        Sample.borehole_id == borehole.id
                    ).order_by(Sample.depth_top).all()
                    
                    for sample in samples:
                        # Build sample data
                        sample_data = {
                            'borehole_id': borehole.borehole_id,
                            'sample_id': sample.sample_id,
                            'depth_top': sample.depth_top,
                            'depth_bottom': sample.depth_bottom,
                            'elevation_top': borehole.elevation - sample.depth_top,
                            'elevation_bottom': borehole.elevation - sample.depth_bottom,
                            'uscs_classification': sample.uscs_classification,
                            'field_description': sample.field_description,
                            'spt_n_value': sample.spt_n_value,
                            'plasticity_index': None,
                            'fines_percent': None
                        }
                        
                        # Get laboratory test results
                        test_results = session.query(TestResult).filter(
                            TestResult.sample_id == sample.id
                        ).all()
                        
                        for test_result in test_results:
                            test_data = json.loads(test_result.test_data) if test_result.test_data else {}
                            
                            # Extract relevant values
                            if test_result.test_type == 'atterberg_limits':
                                sample_data['plasticity_index'] = test_data.get('plasticity_index')
                            elif test_result.test_type == 'gradation':
                                sample_data['fines_percent'] = test_data.get('fines_percent')
                        
                        data.append(sample_data)
                    
                    # Update progress
                    progress = 20 + (i + 1) * 70 // total_boreholes
                    self.progress.emit(progress)
                
                self.progress.emit(100)
                self.finished.emit(data)
                
        except Exception as e:
            logger.error(f"Data loading failed: {e}")
            self.error.emit(str(e))

class IndexValuesTab(QWidget):
    """Tab for displaying index values with tables and plots."""
    
    # Signals
    data_loaded = pyqtSignal(list)  # Emitted when data is loaded
    selection_changed = pyqtSignal(list)  # Emitted when table selection changes
    
    def __init__(self, project_id: int):
        super().__init__()
        self.project_id = project_id
        self.data: List[Dict[str, Any]] = []
        self.table_model: Optional[IndexDataModel] = None
        
        self._setup_ui()
        self._load_data()
    
    def _setup_ui(self):
        """Setup the user interface."""
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # Control panel
        controls_group = QGroupBox("Display Controls")
        controls_layout = QHBoxLayout(controls_group)
        
        # Refresh data button
        self.refresh_btn = QPushButton("Refresh Data")
        self.refresh_btn.clicked.connect(self._load_data)
        controls_layout.addWidget(self.refresh_btn)
        
        # Filter controls
        filter_label = QLabel("Filter by:")
        controls_layout.addWidget(filter_label)
        
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(['All', 'Fine-grained', 'Granular', 'Organic'])
        self.filter_combo.currentTextChanged.connect(self._apply_filter)
        controls_layout.addWidget(self.filter_combo)
        
        # Show only samples with data
        self.data_only_cb = QCheckBox("Show only samples with index data")
        self.data_only_cb.toggled.connect(self._apply_filter)
        controls_layout.addWidget(self.data_only_cb)
        
        controls_layout.addStretch()
        
        # Export button
        self.export_btn = QPushButton("Export Data")
        self.export_btn.clicked.connect(self._export_data)
        controls_layout.addWidget(self.export_btn)
        
        main_layout.addWidget(controls_group)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.hide()
        main_layout.addWidget(self.progress_bar)
        
        # Main content splitter
        content_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(content_splitter)
        
        # Left panel: Data table
        left_panel = self._create_table_panel()
        content_splitter.addWidget(left_panel)
        
        # Right panel: Plots
        right_panel = self._create_plot_panel()
        content_splitter.addWidget(right_panel)
        
        # Set splitter proportions
        content_splitter.setSizes([600, 400])
        
        # Status label
        self.status_label = QLabel("Ready")
        main_layout.addWidget(self.status_label)
    
    def _create_table_panel(self) -> QWidget:
        """Create left panel with data table."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Table info
        self.table_info_label = QLabel("No data loaded")
        layout.addWidget(self.table_info_label)
        
        # Data table
        self.data_table = QTableWidget()
        self.data_table.setSortingEnabled(True)
        self.data_table.setAlternatingRowColors(True)
        self.data_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.data_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.data_table.customContextMenuRequested.connect(self._show_table_context_menu)
        self.data_table.itemSelectionChanged.connect(self._on_table_selection_changed)
        
        # Configure headers
        header = self.data_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(True)
        
        layout.addWidget(self.data_table)
        
        return panel
    
    def _create_plot_panel(self) -> QWidget:
        """Create right panel with plots."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Plot tabs
        self.plot_tabs = QTabWidget()
        layout.addWidget(self.plot_tabs)
        
        # N-Value plot
        self.n_value_tab = self._create_plot_tab("N-Value vs Elevation")
        self.plot_tabs.addTab(self.n_value_tab, "N-Value")
        
        # Plasticity Index plot
        self.pi_tab = self._create_plot_tab("Plasticity Index vs Elevation")
        self.plot_tabs.addTab(self.pi_tab, "Plasticity Index")
        
        # Fines Content plot
        self.fines_tab = self._create_plot_tab("% Passing #200 vs Elevation")
        self.plot_tabs.addTab(self.fines_tab, "% Fines")
        
        # Combined plot
        self.combined_tab = self._create_combined_plot_tab()
        self.plot_tabs.addTab(self.combined_tab, "Combined")
        
        # Plot controls
        plot_controls = QGroupBox("Plot Controls")
        controls_layout = QHBoxLayout(plot_controls)
        
        # Update plots button
        self.update_plots_btn = QPushButton("Update Plots")
        self.update_plots_btn.clicked.connect(self._update_plots)
        controls_layout.addWidget(self.update_plots_btn)
        
        # Show statistics
        self.show_stats_cb = QCheckBox("Show Statistics")
        self.show_stats_cb.setChecked(True)
        self.show_stats_cb.toggled.connect(self._update_plots)
        controls_layout.addWidget(self.show_stats_cb)
        
        # Grid lines
        self.show_grid_cb = QCheckBox("Grid Lines")
        self.show_grid_cb.setChecked(True)
        self.show_grid_cb.toggled.connect(self._update_plots)
        controls_layout.addWidget(self.show_grid_cb)
        
        controls_layout.addStretch()
        layout.addWidget(plot_controls)
        
        return panel
    
    def _create_plot_tab(self, title: str) -> QWidget:
        """Create individual plot tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Plot canvas
        figure = Figure(figsize=(6, 8))
        canvas = FigureCanvas(figure)
        layout.addWidget(canvas)
        
        # Store references
        widget.figure = figure
        widget.canvas = canvas
        widget.title = title
        
        return widget
    
    def _create_combined_plot_tab(self) -> QWidget:
        """Create combined plot tab with all parameters."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Plot canvas with subplots
        figure = Figure(figsize=(12, 8))
        canvas = FigureCanvas(figure)
        layout.addWidget(canvas)
        
        # Store references
        widget.figure = figure
        widget.canvas = canvas
        widget.title = "Combined Index Values"
        
        return widget
    
    def _load_data(self):
        """Load index data from database."""
        try:
            # Show progress
            self.progress_bar.show()
            self.progress_bar.setRange(0, 100)
            self.refresh_btn.setEnabled(False)
            
            # Create worker thread
            self.data_worker = DataLoaderWorker(self.project_id)
            self.data_thread = QThread()
            
            # Move worker to thread
            self.data_worker.moveToThread(self.data_thread)
            
            # Connect signals
            self.data_thread.started.connect(self.data_worker.run)
            self.data_worker.progress.connect(self.progress_bar.setValue)
            self.data_worker.finished.connect(self._on_data_loaded)
            self.data_worker.error.connect(self._on_data_error)
            self.data_worker.finished.connect(self.data_thread.quit)
            self.data_worker.finished.connect(self.data_worker.deleteLater)
            self.data_thread.finished.connect(self.data_thread.deleteLater)
            
            # Start thread
            self.data_thread.start()
            
        except Exception as e:
            logger.error(f"Failed to start data loading: {e}")
            self._reset_loading_ui()
            QMessageBox.critical(self, "Data Error", f"Failed to load data:\n{e}")
    
    @pyqtSlot(list)
    def _on_data_loaded(self, data):
        """Handle completed data loading."""
        try:
            self.data = data
            self._populate_table()
            self._update_plots()
            self._update_info_labels()
            
            self.data_loaded.emit(data)
            self.status_label.setText(f"Loaded {len(data)} samples")
            
        except Exception as e:
            logger.error(f"Failed to process loaded data: {e}")
            QMessageBox.critical(self, "Data Error", f"Failed to process data:\n{e}")
        finally:
            self._reset_loading_ui()
    
    @pyqtSlot(str)
    def _on_data_error(self, error_message):
        """Handle data loading error."""
        logger.error(f"Data loading error: {error_message}")
        QMessageBox.critical(self, "Data Error", f"Data loading failed:\n{error_message}")
        self._reset_loading_ui()
    
    def _reset_loading_ui(self):
        """Reset loading UI after data operation."""
        self.progress_bar.hide()
        self.refresh_btn.setEnabled(True)
    
    def _populate_table(self):
        """Populate the data table."""
        if not self.data:
            return
        
        # Create table model
        self.table_model = IndexDataModel(self.data)
        
        # Setup table widget manually (since we're using QTableWidget)
        headers = self.table_model.headers
        self.data_table.setRowCount(len(self.data))
        self.data_table.setColumnCount(len(headers))
        self.data_table.setHorizontalHeaderLabels(headers)
        
        # Populate data
        for row, item in enumerate(self.data):
            for col in range(len(headers)):
                # Get display data
                display_data = self.table_model.data(
                    self.table_model.index(row, col), 
                    Qt.ItemDataRole.DisplayRole
                )
                
                # Create table item
                table_item = QTableWidgetItem(str(display_data) if display_data else "")
                
                # Set background color
                bg_color = self.table_model.data(
                    self.table_model.index(row, col),
                    Qt.ItemDataRole.BackgroundRole
                )
                if bg_color:
                    table_item.setBackground(bg_color)
                
                self.data_table.setItem(row, col, table_item)
        
        # Resize columns
        self.data_table.resizeColumnsToContents()
    
    def _apply_filter(self):
        """Apply current filter settings."""
        if not self.data:
            return
        
        filter_type = self.filter_combo.currentText()
        data_only = self.data_only_cb.isChecked()
        
        # Filter data
        filtered_data = []
        for item in self.data:
            # Apply USCS filter
            uscs = item.get('uscs_classification')
            if filter_type != 'All' and uscs:
                try:
                    uscs_enum = USCSClassification(uscs)
                    if filter_type == 'Fine-grained' and not is_fine_grained(uscs_enum):
                        continue
                    elif filter_type == 'Granular' and not is_granular(uscs_enum):
                        continue
                    elif filter_type == 'Organic' and uscs_enum != USCSClassification.PT:
                        continue
                except (ValueError, KeyError):
                    continue
            
            # Apply data-only filter
            if data_only:
                has_data = any([
                    item.get('spt_n_value') is not None,
                    item.get('plasticity_index') is not None,
                    item.get('fines_percent') is not None
                ])
                if not has_data:
                    continue
            
            filtered_data.append(item)
        
        # Update table with filtered data
        self.table_model = IndexDataModel(filtered_data)
        self._populate_table()
        self._update_info_labels()
        self._update_plots()
    
    def _update_plots(self):
        """Update all plots with current data."""
        if not self.data:
            return
        
        try:
            # Get filtered data
            visible_data = self._get_visible_data()
            
            # Update individual plots
            self._plot_n_values(visible_data)
            self._plot_plasticity_index(visible_data)
            self._plot_fines_content(visible_data)
            self._plot_combined(visible_data)
            
        except Exception as e:
            logger.error(f"Failed to update plots: {e}")
    
    def _get_visible_data(self) -> List[Dict[str, Any]]:
        """Get currently visible data based on filters."""
        if not self.table_model:
            return self.data
        return self.table_model.data
    
    def _plot_n_values(self, data: List[Dict[str, Any]]):
        """Plot N-values vs elevation."""
        tab = self.n_value_tab
        tab.figure.clear()
        ax = tab.figure.add_subplot(111)
        
        # Extract data
        elevations = []
        n_values = []
        colors = []
        
        for item in data:
            if item.get('spt_n_value') is not None:
                elevations.append(item['elevation_top'])
                n_values.append(item['spt_n_value'])
                
                # Get color
                uscs = item.get('uscs_classification')
                if uscs:
                    try:
                        uscs_enum = USCSClassification(uscs)
                        color = get_uscs_color(uscs_enum)
                        colors.append(color.name())
                    except (ValueError, KeyError):
                        colors.append('gray')
                else:
                    colors.append('gray')
        
        if elevations and n_values:
            # Create scatter plot
            for i, (elev, n_val, color) in enumerate(zip(elevations, n_values, colors)):
                ax.scatter(n_val, elev, c=color, s=50, alpha=0.7, edgecolors='black', linewidth=0.5)
            
            # Add statistics if enabled
            if self.show_stats_cb.isChecked() and n_values:
                mean_n = np.mean(n_values)
                ax.axvline(mean_n, color='red', linestyle='--', alpha=0.7, label=f'Mean: {mean_n:.1f}')
                ax.legend()
            
            ax.set_xlabel('SPT N-Value (blows/ft)')
            ax.set_ylabel('Elevation (ft)')
            ax.set_title('SPT N-Value vs Elevation')
            ax.grid(self.show_grid_cb.isChecked(), alpha=0.3)
            
        else:
            ax.text(0.5, 0.5, 'No N-value data available', 
                   transform=ax.transAxes, ha='center', va='center')
        
        tab.figure.tight_layout()
        tab.canvas.draw()
    
    def _plot_plasticity_index(self, data: List[Dict[str, Any]]):
        """Plot plasticity index vs elevation."""
        tab = self.pi_tab
        tab.figure.clear()
        ax = tab.figure.add_subplot(111)
        
        # Extract data
        elevations = []
        pi_values = []
        colors = []
        
        for item in data:
            if item.get('plasticity_index') is not None:
                elevations.append(item['elevation_top'])
                pi_values.append(item['plasticity_index'])
                
                # Get color
                uscs = item.get('uscs_classification')
                if uscs:
                    try:
                        uscs_enum = USCSClassification(uscs)
                        color = get_uscs_color(uscs_enum)
                        colors.append(color.name())
                    except (ValueError, KeyError):
                        colors.append('gray')
                else:
                    colors.append('gray')
        
        if elevations and pi_values:
            # Create scatter plot
            for i, (elev, pi, color) in enumerate(zip(elevations, pi_values, colors)):
                ax.scatter(pi, elev, c=color, s=50, alpha=0.7, edgecolors='black', linewidth=0.5)
            
            # Add statistics if enabled
            if self.show_stats_cb.isChecked() and pi_values:
                mean_pi = np.mean(pi_values)
                ax.axvline(mean_pi, color='red', linestyle='--', alpha=0.7, label=f'Mean: {mean_pi:.1f}')
                ax.legend()
            
            ax.set_xlabel('Plasticity Index (%)')
            ax.set_ylabel('Elevation (ft)')
            ax.set_title('Plasticity Index vs Elevation')
            ax.grid(self.show_grid_cb.isChecked(), alpha=0.3)
            
        else:
            ax.text(0.5, 0.5, 'No plasticity index data available', 
                   transform=ax.transAxes, ha='center', va='center')
        
        tab.figure.tight_layout()
        tab.canvas.draw()
    
    def _plot_fines_content(self, data: List[Dict[str, Any]]):
        """Plot fines content vs elevation."""
        tab = self.fines_tab
        tab.figure.clear()
        ax = tab.figure.add_subplot(111)
        
        # Extract data
        elevations = []
        fines_values = []
        colors = []
        
        for item in data:
            if item.get('fines_percent') is not None:
                elevations.append(item['elevation_top'])
                fines_values.append(item['fines_percent'])
                
                # Get color
                uscs = item.get('uscs_classification')
                if uscs:
                    try:
                        uscs_enum = USCSClassification(uscs)
                        color = get_uscs_color(uscs_enum)
                        colors.append(color.name())
                    except (ValueError, KeyError):
                        colors.append('gray')
                else:
                    colors.append('gray')
        
        if elevations and fines_values:
            # Create scatter plot
            for i, (elev, fines, color) in enumerate(zip(elevations, fines_values, colors)):
                ax.scatter(fines, elev, c=color, s=50, alpha=0.7, edgecolors='black', linewidth=0.5)
            
            # Add 50% line (coarse vs fine boundary)
            ax.axvline(50, color='orange', linestyle='-', alpha=0.5, label='Coarse/Fine Boundary')
            
            # Add statistics if enabled
            if self.show_stats_cb.isChecked() and fines_values:
                mean_fines = np.mean(fines_values)
                ax.axvline(mean_fines, color='red', linestyle='--', alpha=0.7, label=f'Mean: {mean_fines:.1f}%')
            
            ax.legend()
            ax.set_xlabel('% Passing #200 Sieve')
            ax.set_ylabel('Elevation (ft)')
            ax.set_title('Fines Content vs Elevation')
            ax.grid(self.show_grid_cb.isChecked(), alpha=0.3)
            
        else:
            ax.text(0.5, 0.5, 'No fines content data available', 
                   transform=ax.transAxes, ha='center', va='center')
        
        tab.figure.tight_layout()
        tab.canvas.draw()
    
    def _plot_combined(self, data: List[Dict[str, Any]]):
        """Plot combined view of all parameters."""
        tab = self.combined_tab
        tab.figure.clear()
        
        # Create 3 subplots side by side
        ax1 = tab.figure.add_subplot(131)
        ax2 = tab.figure.add_subplot(132)
        ax3 = tab.figure.add_subplot(133)
        
        # Plot N-values
        self._plot_parameter_on_axis(ax1, data, 'spt_n_value', 'SPT N-Value', 'blows/ft')
        
        # Plot Plasticity Index
        self._plot_parameter_on_axis(ax2, data, 'plasticity_index', 'Plasticity Index', '%')
        
        # Plot Fines Content
        self._plot_parameter_on_axis(ax3, data, 'fines_percent', '% Passing #200', '%')
        
        # Add 50% line to fines plot
        if any(item.get('fines_percent') is not None for item in data):
            ax3.axvline(50, color='orange', linestyle='-', alpha=0.5, linewidth=1)
        
        tab.figure.tight_layout()
        tab.canvas.draw()
    
    def _plot_parameter_on_axis(self, ax, data: List[Dict[str, Any]], param_key: str, 
                               title: str, units: str):
        """Plot a parameter on a given axis."""
        elevations = []
        values = []
        colors = []
        
        for item in data:
            if item.get(param_key) is not None:
                elevations.append(item['elevation_top'])
                values.append(item[param_key])
                
                # Get color
                uscs = item.get('uscs_classification')
                if uscs:
                    try:
                        uscs_enum = USCSClassification(uscs)
                        color = get_uscs_color(uscs_enum)
                        colors.append(color.name())
                    except (ValueError, KeyError):
                        colors.append('gray')
                else:
                    colors.append('gray')
        
        if elevations and values:
            # Create scatter plot
            for i, (elev, val, color) in enumerate(zip(elevations, values, colors)):
                ax.scatter(val, elev, c=color, s=30, alpha=0.7, edgecolors='black', linewidth=0.3)
            
            ax.set_xlabel(f'{title} ({units})')
            ax.set_ylabel('Elevation (ft)')
            ax.set_title(title)
            ax.grid(self.show_grid_cb.isChecked(), alpha=0.3)
            
        else:
            ax.text(0.5, 0.5, f'No {title.lower()} data', 
                   transform=ax.transAxes, ha='center', va='center')
    
    def _update_info_labels(self):
        """Update information labels."""
        if not self.data:
            self.table_info_label.setText("No data loaded")
            return
        
        visible_data = self._get_visible_data()
        
        # Count data types
        n_value_count = sum(1 for item in visible_data if item.get('spt_n_value') is not None)
        pi_count = sum(1 for item in visible_data if item.get('plasticity_index') is not None)
        fines_count = sum(1 for item in visible_data if item.get('fines_percent') is not None)
        
        info_text = (f"Showing {len(visible_data)} of {len(self.data)} samples | "
                    f"N-values: {n_value_count} | "
                    f"PI: {pi_count} | "
                    f"Fines: {fines_count}")
        
        self.table_info_label.setText(info_text)
    
    @pyqtSlot()
    def _on_table_selection_changed(self):
        """Handle table selection changes."""
        selected_rows = set()
        for item in self.data_table.selectedItems():
            selected_rows.add(item.row())
        
        selected_data = []
        if self.table_model:
            for row in selected_rows:
                if row < len(self.table_model.data):
                    selected_data.append(self.table_model.data[row])
        
        self.selection_changed.emit(selected_data)
    
    @pyqtSlot()
    def _show_table_context_menu(self, position):
        """Show context menu for table."""
        if not self.data_table.itemAt(position):
            return
        
        menu = QMenu(self)
        
        # Copy action
        copy_action = QAction("Copy Selection", self)
        copy_action.triggered.connect(self._copy_selection)
        menu.addAction(copy_action)
        
        # Export selection
        export_action = QAction("Export Selection", self)
        export_action.triggered.connect(self._export_selection)
        menu.addAction(export_action)
        
        menu.exec(self.data_table.mapToGlobal(position))
    
    @pyqtSlot()
    def _copy_selection(self):
        """Copy selected table data to clipboard."""
        # TODO: Implement clipboard copy
        QMessageBox.information(self, "Copy", "Copy functionality coming soon!")
    
    @pyqtSlot()
    def _export_selection(self):
        """Export selected data."""
        # TODO: Implement selection export
        QMessageBox.information(self, "Export", "Selection export functionality coming soon!")
    
    @pyqtSlot()
    def _export_data(self):
        """Export current data to file."""
        if not self.data:
            QMessageBox.information(self, "Export", "No data to export")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Index Values",
            f"index_values_project_{self.project_id}.csv",
            "CSV Files (*.csv);;Excel Files (*.xlsx);;All Files (*)"
        )
        
        if file_path:
            try:
                # Convert to DataFrame
                df = pd.DataFrame(self._get_visible_data())
                
                # Export based on file extension
                if file_path.endswith('.csv'):
                    df.to_csv(file_path, index=False)
                elif file_path.endswith('.xlsx'):
                    df.to_excel(file_path, index=False)
                else:
                    df.to_csv(file_path, index=False)
                
                QMessageBox.information(self, "Export", f"Data exported successfully to:\n{file_path}")
                logger.info(f"Index values exported to: {file_path}")
                
            except Exception as e:
                logger.error(f"Export failed: {e}")
                QMessageBox.critical(self, "Export Error", f"Failed to export data:\n{e}")

if __name__ == "__main__":
    # Test the tab independently
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # Mock project ID for testing
    tab = IndexValuesTab(project_id=1)
    tab.show()
    
    sys.exit(app.exec())