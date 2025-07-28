"""
Main application window for Strata Interpreter.

This module provides the primary user interface with menu bar, toolbar,
status bar, and tabbed interface for different functionality areas.
"""

import logging
import sys
from typing import Optional, Dict, Any
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QTabWidget, QMenuBar, QToolBar, QStatusBar, QWidget,
    QVBoxLayout, QHBoxLayout, QSplitter, QMessageBox, QFileDialog,
    QProgressBar, QLabel, QApplication, QUndoStack, QAction
)
from PyQt6.QtCore import Qt, QSettings, QTimer, pyqtSignal, QThread, pyqtSlot
from PyQt6.QtGui import QIcon, QKeySequence, QPixmap

from core.database import initialize_database, get_database_manager
from core.json_export import export_project_to_json
from core.json_import import import_project_from_json
from utils.constants import (
    APP_NAME, APP_VERSION, DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT,
    MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT, AUTO_SAVE_INTERVAL
)
from utils.color_schemes import get_color_legend

logger = logging.getLogger(__name__)

class MainWindow(QMainWindow):
    """Main application window with tabbed interface."""
    
    # Signals
    project_loaded = pyqtSignal(int)  # Emitted when project is loaded
    project_changed = pyqtSignal()    # Emitted when project data changes
    
    def __init__(self):
        """Initialize main window."""
        super().__init__()
        
        # Application state
        self.current_project_id: Optional[int] = None
        self.project_modified = False
        self.settings = QSettings(APP_NAME, APP_VERSION)
        self.undo_stack = QUndoStack(self)
        
        # Initialize database
        try:
            initialize_database()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            QMessageBox.critical(self, "Database Error", 
                               f"Failed to initialize database:\n{e}")
            sys.exit(1)
        
        # Setup UI
        self._setup_ui()
        self._create_menus()
        self._create_toolbars()
        self._create_status_bar()
        self._setup_auto_save()
        self._restore_settings()
        
        # Connect signals
        self._connect_signals()
        
        logger.info("Main window initialized")
    
    def _setup_ui(self):
        """Setup the main user interface."""
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setMinimumSize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)
        self.resize(DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT)
        
        # Central widget with main splitter
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # Create main splitter (horizontal)
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(self.main_splitter)
        
        # Create tab widget for main functionality
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.TabPosition.North)
        self.tab_widget.setMovable(True)
        self.tab_widget.setDocumentMode(True)
        
        # Add tab widget to splitter
        self.main_splitter.addWidget(self.tab_widget)
        
        # Create sidebar for project info (initially hidden)
        self.sidebar = self._create_sidebar()
        self.main_splitter.addWidget(self.sidebar)
        self.sidebar.hide()
        
        # Set splitter proportions
        self.main_splitter.setSizes([800, 200])
        
        # Initialize tabs (will be created when needed)
        self.tabs = {}
        self._create_initial_tabs()
    
    def _create_sidebar(self) -> QWidget:
        """Create sidebar with project information."""
        sidebar = QWidget()
        sidebar.setMaximumWidth(250)
        sidebar.setMinimumWidth(200)
        
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Project info section
        self.project_info_label = QLabel("No project loaded")
        self.project_info_label.setWordWrap(True)
        layout.addWidget(self.project_info_label)
        
        # Color legend
        legend_label = QLabel("USCS Color Legend:")
        legend_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(legend_label)
        
        color_legend = get_color_legend()
        for category, (description, color) in color_legend.items():
            legend_item = QLabel(f"● {category}: {description}")
            legend_item.setStyleSheet(f"color: {color}; margin-left: 10px;")
            layout.addWidget(legend_item)
        
        layout.addStretch()
        return sidebar
    
    def _create_initial_tabs(self):
        """Create initial tabs that are always available."""
        # Import placeholder tabs (actual implementation will be added later)
        self._add_welcome_tab()
    
    def _add_welcome_tab(self):
        """Add welcome tab with basic project operations."""
        welcome_widget = QWidget()
        layout = QVBoxLayout(welcome_widget)
        
        welcome_label = QLabel(f"Welcome to {APP_NAME}")
        welcome_label.setStyleSheet("font-size: 18px; font-weight: bold; margin: 20px;")
        welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(welcome_label)
        
        info_label = QLabel(
            "This application helps geotechnical engineers interpret soil strata "
            "and assign design parameters based on laboratory test data.\n\n"
            "To get started:\n"
            "1. Create a new project or import existing DIGGS SQL database\n"
            "2. Review and interpret soil strata\n"
            "3. Assign design parameters using calculated or manual values\n"
            "4. Export results for use in design software"
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("margin: 20px; font-size: 12px;")
        layout.addWidget(info_label)
        
        layout.addStretch()
        
        self.tab_widget.addTab(welcome_widget, "Welcome")
        self.tabs["welcome"] = welcome_widget
    
    def _create_menus(self):
        """Create application menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&File")
        
        # New project
        new_action = QAction("&New Project", self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.setStatusTip("Create a new project")
        new_action.triggered.connect(self.new_project)
        file_menu.addAction(new_action)
        
        # Open project
        open_action = QAction("&Open Project", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.setStatusTip("Open existing project")
        open_action.triggered.connect(self.open_project)
        file_menu.addAction(open_action)
        
        file_menu.addSeparator()
        
        # Import DIGGS database
        import_diggs_action = QAction("Import &DIGGS Database", self)
        import_diggs_action.setStatusTip("Import data from DIGGS SQL database")
        import_diggs_action.triggered.connect(self.import_diggs_database)
        file_menu.addAction(import_diggs_action)
        
        # Import JSON profile
        import_json_action = QAction("Import &JSON Profile", self)
        import_json_action.setShortcut(QKeySequence("Ctrl+I"))
        import_json_action.setStatusTip("Import soil profile from JSON file")
        import_json_action.triggered.connect(self.import_json_profile)
        file_menu.addAction(import_json_action)
        
        file_menu.addSeparator()
        
        # Save project
        save_action = QAction("&Save Project", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.setStatusTip("Save current project")
        save_action.triggered.connect(self.save_project)
        file_menu.addAction(save_action)
        
        # Export submenu
        export_menu = file_menu.addMenu("Export")
        
        # Export JSON profile
        export_json_action = QAction("Soil Profile (&JSON)", self)
        export_json_action.setShortcut(QKeySequence("Ctrl+E"))
        export_json_action.setStatusTip("Export soil profile to JSON file")
        export_json_action.triggered.connect(self.export_json_profile)
        export_menu.addAction(export_json_action)
        
        file_menu.addSeparator()
        
        # Exit
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.setStatusTip("Exit application")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Edit menu
        edit_menu = menubar.addMenu("&Edit")
        
        # Undo/Redo
        undo_action = self.undo_stack.createUndoAction(self, "&Undo")
        undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        edit_menu.addAction(undo_action)
        
        redo_action = self.undo_stack.createRedoAction(self, "&Redo")
        redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        edit_menu.addAction(redo_action)
        
        # View menu
        view_menu = menubar.addMenu("&View")
        
        # Toggle sidebar
        sidebar_action = QAction("Show &Sidebar", self)
        sidebar_action.setCheckable(True)
        sidebar_action.setChecked(False)
        sidebar_action.triggered.connect(self._toggle_sidebar)
        view_menu.addAction(sidebar_action)
        
        # Tools menu
        tools_menu = menubar.addMenu("&Tools")
        
        # Validate project
        validate_action = QAction("&Validate Project", self)
        validate_action.setStatusTip("Validate current project data")
        validate_action.triggered.connect(self.validate_project)
        tools_menu.addAction(validate_action)
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        
        # About
        about_action = QAction("&About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def _create_toolbars(self):
        """Create application toolbars."""
        # Main toolbar
        main_toolbar = self.addToolBar("Main")
        main_toolbar.setMovable(False)
        
        # Add common actions to toolbar
        new_action = QAction("New", self)
        new_action.setStatusTip("Create new project")
        new_action.triggered.connect(self.new_project)
        main_toolbar.addAction(new_action)
        
        open_action = QAction("Open", self)
        open_action.setStatusTip("Open project")
        open_action.triggered.connect(self.open_project)
        main_toolbar.addAction(open_action)
        
        save_action = QAction("Save", self)
        save_action.setStatusTip("Save project")
        save_action.triggered.connect(self.save_project)
        main_toolbar.addAction(save_action)
        
        main_toolbar.addSeparator()
        
        import_action = QAction("Import", self)
        import_action.setStatusTip("Import data")
        import_action.triggered.connect(self.import_diggs_database)
        main_toolbar.addAction(import_action)
        
        export_action = QAction("Export", self)
        export_action.setStatusTip("Export data")
        export_action.triggered.connect(self.export_json_profile)
        main_toolbar.addAction(export_action)
    
    def _create_status_bar(self):
        """Create application status bar."""
        self.status_bar = self.statusBar()
        
        # Project status label
        self.project_status_label = QLabel("No project loaded")
        self.status_bar.addWidget(self.project_status_label)
        
        # Progress bar (initially hidden)
        self.progress_bar = QProgressBar()
        self.progress_bar.hide()
        self.status_bar.addPermanentWidget(self.progress_bar)
        
        # Database status
        self.db_status_label = QLabel("Database: Ready")
        self.status_bar.addPermanentWidget(self.db_status_label)
    
    def _setup_auto_save(self):
        """Setup automatic saving timer."""
        self.auto_save_timer = QTimer()
        self.auto_save_timer.timeout.connect(self._auto_save)
        self.auto_save_timer.start(AUTO_SAVE_INTERVAL * 1000)  # Convert to milliseconds
    
    def _connect_signals(self):
        """Connect application signals."""
        self.project_loaded.connect(self._on_project_loaded)
        self.project_changed.connect(self._on_project_changed)
        self.tab_widget.currentChanged.connect(self._on_tab_changed)
    
    def _restore_settings(self):
        """Restore application settings."""
        # Restore window geometry
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        
        # Restore window state
        state = self.settings.value("windowState")
        if state:
            self.restoreState(state)
        
        # Restore splitter state
        splitter_state = self.settings.value("splitterState")
        if splitter_state:
            self.main_splitter.restoreState(splitter_state)
    
    def _save_settings(self):
        """Save application settings."""
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("windowState", self.saveState())
        self.settings.setValue("splitterState", self.main_splitter.saveState())
    
    # Slots for menu actions
    @pyqtSlot()
    def new_project(self):
        """Create new project."""
        if self._check_save_changes():
            # TODO: Implement new project dialog
            QMessageBox.information(self, "New Project", "New project functionality coming soon!")
    
    @pyqtSlot()
    def open_project(self):
        """Open existing project."""
        if self._check_save_changes():
            # TODO: Implement project selection dialog
            QMessageBox.information(self, "Open Project", "Open project functionality coming soon!")
    
    @pyqtSlot()
    def save_project(self):
        """Save current project."""
        if self.current_project_id is not None:
            try:
                # TODO: Implement project saving
                self.project_modified = False
                self.status_bar.showMessage("Project saved", 2000)
                logger.info(f"Project {self.current_project_id} saved")
            except Exception as e:
                logger.error(f"Failed to save project: {e}")
                QMessageBox.critical(self, "Save Error", f"Failed to save project:\n{e}")
        else:
            QMessageBox.information(self, "Save Project", "No project to save")
    
    @pyqtSlot()
    def import_diggs_database(self):
        """Import DIGGS SQL database."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import DIGGS Database",
            "",
            "SQLite Database (*.db *.sqlite);;All Files (*)"
        )
        
        if file_path:
            try:
                # TODO: Implement DIGGS import
                QMessageBox.information(self, "Import DIGGS", 
                                      f"DIGGS import functionality coming soon!\nSelected: {file_path}")
            except Exception as e:
                logger.error(f"DIGGS import failed: {e}")
                QMessageBox.critical(self, "Import Error", f"Failed to import DIGGS database:\n{e}")
    
    @pyqtSlot()
    def import_json_profile(self):
        """Import JSON soil profile."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import JSON Profile",
            "",
            "JSON Files (*.json);;Compressed JSON (*.json.gz);;All Files (*)"
        )
        
        if file_path:
            try:
                self.progress_bar.show()
                self.progress_bar.setRange(0, 0)  # Indeterminate progress
                
                project_id = import_project_from_json(file_path)
                
                self.progress_bar.hide()
                
                if project_id:
                    self.current_project_id = project_id
                    self.project_loaded.emit(project_id)
                    self.status_bar.showMessage(f"JSON profile imported successfully", 3000)
                    logger.info(f"JSON profile imported: {file_path}")
                else:
                    QMessageBox.warning(self, "Import Warning", "Failed to import JSON profile")
                    
            except Exception as e:
                self.progress_bar.hide()
                logger.error(f"JSON import failed: {e}")
                QMessageBox.critical(self, "Import Error", f"Failed to import JSON profile:\n{e}")
    
    @pyqtSlot()
    def export_json_profile(self):
        """Export current project to JSON."""
        if self.current_project_id is None:
            QMessageBox.information(self, "Export", "No project to export")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export JSON Profile",
            f"project_{self.current_project_id}.json",
            "JSON Files (*.json);;Compressed JSON (*.json.gz);;All Files (*)"
        )
        
        if file_path:
            try:
                self.progress_bar.show()
                self.progress_bar.setRange(0, 0)  # Indeterminate progress
                
                compress = file_path.endswith('.gz')
                success = export_project_to_json(self.current_project_id, file_path, compress)
                
                self.progress_bar.hide()
                
                if success:
                    self.status_bar.showMessage(f"Project exported successfully", 3000)
                    logger.info(f"Project exported: {file_path}")
                else:
                    QMessageBox.warning(self, "Export Warning", "Failed to export project")
                    
            except Exception as e:
                self.progress_bar.hide()
                logger.error(f"JSON export failed: {e}")
                QMessageBox.critical(self, "Export Error", f"Failed to export project:\n{e}")
    
    @pyqtSlot()
    def validate_project(self):
        """Validate current project data."""
        if self.current_project_id is None:
            QMessageBox.information(self, "Validate", "No project to validate")
            return
        
        # TODO: Implement project validation
        QMessageBox.information(self, "Validate Project", "Project validation functionality coming soon!")
    
    @pyqtSlot()
    def show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            f"About {APP_NAME}",
            f"""<h3>{APP_NAME} v{APP_VERSION}</h3>
            <p>Professional geotechnical strata interpretation and design parameter assignment tool.</p>
            <p>Built with PyQt6 and SQLAlchemy for reliable data management and analysis.</p>
            <p>© 2025 Geotechnical Engineering Team</p>"""
        )
    
    @pyqtSlot(bool)
    def _toggle_sidebar(self, checked: bool):
        """Toggle sidebar visibility."""
        if checked:
            self.sidebar.show()
        else:
            self.sidebar.hide()
    
    @pyqtSlot(int)
    def _on_project_loaded(self, project_id: int):
        """Handle project loaded signal."""
        try:
            db_manager = get_database_manager()
            project = db_manager.get_project(project_id)
            
            if project:
                self.project_status_label.setText(f"Project: {project.project_name}")
                self.project_info_label.setText(
                    f"<b>{project.project_name}</b><br>"
                    f"Number: {project.project_number}<br>"
                    f"Created: {project.date_created.strftime('%Y-%m-%d')}<br>"
                    f"Version: {project.version}"
                )
                self.sidebar.show()
                
                # TODO: Load project-specific tabs
                self._load_project_tabs(project_id)
                
            logger.info(f"Project {project_id} loaded successfully")
            
        except Exception as e:
            logger.error(f"Error loading project {project_id}: {e}")
    
    @pyqtSlot()
    def _on_project_changed(self):
        """Handle project changed signal."""
        self.project_modified = True
        if self.current_project_id:
            title = self.windowTitle()
            if not title.endswith("*"):
                self.setWindowTitle(title + "*")
    
    @pyqtSlot(int)
    def _on_tab_changed(self, index: int):
        """Handle tab change."""
        if index >= 0:
            tab_name = self.tab_widget.tabText(index)
            logger.debug(f"Switched to tab: {tab_name}")
    
    def _load_project_tabs(self, project_id: int):
        """Load project-specific tabs."""
        # TODO: Implement loading of project tabs
        # This will include:
        # - Map & Profile tab
        # - Index Values tab  
        # - Design Parameter tabs
        pass
    
    def _check_save_changes(self) -> bool:
        """Check if user wants to save changes before proceeding."""
        if self.project_modified:
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                "The current project has unsaved changes. Do you want to save them?",
                QMessageBox.StandardButton.Save | 
                QMessageBox.StandardButton.Discard | 
                QMessageBox.StandardButton.Cancel
            )
            
            if reply == QMessageBox.StandardButton.Save:
                self.save_project()
                return True
            elif reply == QMessageBox.StandardButton.Discard:
                return True
            else:
                return False
        
        return True
    
    @pyqtSlot()
    def _auto_save(self):
        """Perform automatic save if project is modified."""
        if self.project_modified and self.current_project_id is not None:
            try:
                # TODO: Implement auto-save
                logger.debug("Auto-save triggered")
            except Exception as e:
                logger.error(f"Auto-save failed: {e}")
    
    def closeEvent(self, event):
        """Handle application close event."""
        if self._check_save_changes():
            self._save_settings()
            event.accept()
            logger.info("Application closed")
        else:
            event.ignore()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())