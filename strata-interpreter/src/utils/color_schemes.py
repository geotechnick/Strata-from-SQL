"""
USCS Color Coding Scheme for Soil Classification

Implements professional color coding for USCS soil types:
- Cool colors (blues/purples) for fine-grained materials
- Warm colors (reds/oranges) for granular materials  
- Greys for rock materials
- Greens for organic materials
"""

from typing import Dict, Tuple
from PyQt6.QtGui import QColor
from core.models import USCSClassification

# RGB color tuples (R, G, B)
USCS_COLORS: Dict[USCSClassification, Tuple[int, int, int]] = {
    # Granular materials - warm colors
    USCSClassification.GW: (255, 165, 0),    # Orange
    USCSClassification.GP: (255, 140, 0),    # Dark orange  
    USCSClassification.GM: (255, 69, 0),     # Red orange
    USCSClassification.GC: (220, 20, 60),    # Crimson
    USCSClassification.SW: (255, 215, 0),    # Gold
    USCSClassification.SP: (255, 185, 15),   # Dark goldenrod
    USCSClassification.SM: (255, 105, 180),  # Hot pink
    USCSClassification.SC: (205, 92, 92),    # Indian red
    
    # Fine-grained materials - cool colors
    USCSClassification.ML: (135, 206, 235),  # Sky blue
    USCSClassification.CL: (70, 130, 180),   # Steel blue
    USCSClassification.OL: (25, 25, 112),    # Midnight blue
    USCSClassification.MH: (138, 43, 226),   # Blue violet
    USCSClassification.CH: (75, 0, 130),     # Indigo
    USCSClassification.OH: (72, 61, 139),    # Dark slate blue
    
    # Organic materials - greens
    USCSClassification.PT: (34, 139, 34),    # Forest green
}

# Additional colors for rock and special materials
ROCK_COLORS = {
    'bedrock': (105, 105, 105),      # Dim gray
    'weathered_rock': (169, 169, 169),  # Dark gray
    'fill': (211, 211, 211),         # Light gray
}

def get_uscs_color(classification: USCSClassification) -> QColor:
    """
    Get QColor for USCS soil classification.
    
    Args:
        classification: USCS soil classification enum
        
    Returns:
        QColor object for the soil type
    """
    if classification in USCS_COLORS:
        r, g, b = USCS_COLORS[classification]
        return QColor(r, g, b)
    else:
        # Default to gray for unknown classifications
        return QColor(128, 128, 128)

def get_uscs_color_hex(classification: USCSClassification) -> str:
    """
    Get hex color string for USCS soil classification.
    
    Args:
        classification: USCS soil classification enum
        
    Returns:
        Hex color string (e.g., "#FF6A00")
    """
    color = get_uscs_color(classification)
    return color.name()

def get_rock_color(rock_type: str) -> QColor:
    """
    Get QColor for rock materials.
    
    Args:
        rock_type: Type of rock material
        
    Returns:
        QColor object for the rock type
    """
    if rock_type.lower() in ROCK_COLORS:
        r, g, b = ROCK_COLORS[rock_type.lower()]
        return QColor(r, g, b)
    else:
        # Default to medium gray
        return QColor(128, 128, 128)

def is_fine_grained(classification: USCSClassification) -> bool:
    """
    Check if soil classification is fine-grained (uses cool colors).
    
    Args:
        classification: USCS soil classification enum
        
    Returns:
        True if fine-grained material, False otherwise
    """
    fine_grained = {
        USCSClassification.ML, USCSClassification.CL, USCSClassification.OL,
        USCSClassification.MH, USCSClassification.CH, USCSClassification.OH
    }
    return classification in fine_grained

def is_granular(classification: USCSClassification) -> bool:
    """
    Check if soil classification is granular (uses warm colors).
    
    Args:
        classification: USCS soil classification enum
        
    Returns:
        True if granular material, False otherwise
    """
    granular = {
        USCSClassification.GW, USCSClassification.GP, USCSClassification.GM,
        USCSClassification.GC, USCSClassification.SW, USCSClassification.SP,
        USCSClassification.SM, USCSClassification.SC
    }
    return classification in granular

def is_organic(classification: USCSClassification) -> bool:
    """
    Check if soil classification is organic (uses green colors).
    
    Args:
        classification: USCS soil classification enum
        
    Returns:
        True if organic material, False otherwise
    """
    return classification == USCSClassification.PT

def get_color_legend() -> Dict[str, Tuple[str, str]]:
    """
    Get color legend information for display in UI.
    
    Returns:
        Dictionary mapping color category to (description, hex_color)
    """
    return {
        'Fine-grained': ('Cool colors (blues/purples)', '#4682B4'),
        'Granular': ('Warm colors (reds/oranges)', '#FFA500'),
        'Rock': ('Greys', '#808080'),
        'Organic': ('Greens', '#228B22')
    }

# Accessibility support - high contrast colors for colorblind users
HIGH_CONTRAST_COLORS: Dict[USCSClassification, Tuple[int, int, int]] = {
    # High contrast versions maintaining the same grouping logic
    USCSClassification.GW: (255, 0, 0),      # Pure red
    USCSClassification.GP: (255, 127, 0),    # Pure orange
    USCSClassification.GM: (255, 255, 0),    # Pure yellow
    USCSClassification.GC: (127, 255, 0),    # Yellow-green
    USCSClassification.SW: (0, 255, 0),      # Pure green
    USCSClassification.SP: (0, 255, 127),    # Green-cyan
    USCSClassification.SM: (0, 255, 255),    # Pure cyan
    USCSClassification.SC: (0, 127, 255),    # Cyan-blue
    
    USCSClassification.ML: (0, 0, 255),      # Pure blue
    USCSClassification.CL: (127, 0, 255),    # Blue-magenta
    USCSClassification.OL: (255, 0, 255),    # Pure magenta
    USCSClassification.MH: (255, 0, 127),    # Magenta-red
    USCSClassification.CH: (64, 64, 64),     # Dark gray
    USCSClassification.OH: (128, 128, 128),  # Medium gray
    
    USCSClassification.PT: (0, 0, 0),        # Black
}

def get_high_contrast_color(classification: USCSClassification) -> QColor:
    """
    Get high contrast QColor for accessibility.
    
    Args:
        classification: USCS soil classification enum
        
    Returns:
        High contrast QColor object
    """
    if classification in HIGH_CONTRAST_COLORS:
        r, g, b = HIGH_CONTRAST_COLORS[classification]
        return QColor(r, g, b)
    else:
        return QColor(0, 0, 0)  # Black default