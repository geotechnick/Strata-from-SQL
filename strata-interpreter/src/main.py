#!/usr/bin/env python3
"""
Strata Interpreter - Main Application Entry Point

A professional geotechnical engineering application for soil strata interpretation
and design parameter assignment using DIGGS SQL database format.
"""

import sys
import logging
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('strata_interpreter.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Main application entry point."""
    try:
        # Enable high DPI scaling
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
        
        app = QApplication(sys.argv)
        app.setApplicationName("Strata Interpreter")
        app.setApplicationVersion("0.1.0")
        app.setOrganizationName("Geotechnical Engineering")
        
        # Import main window (delayed import for faster startup)
        from gui.main_window import MainWindow
        
        window = MainWindow()
        window.show()
        
        logger.info("Strata Interpreter application started successfully")
        
        return app.exec()
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())