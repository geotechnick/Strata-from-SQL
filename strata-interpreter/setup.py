#!/usr/bin/env python3
"""
Setup script for Strata Interpreter application.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the contents of README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text() if (this_directory / "README.md").exists() else ""

# Read requirements
requirements = []
if (this_directory / "requirements.txt").exists():
    with open(this_directory / "requirements.txt", 'r') as f:
        requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

dev_requirements = []
if (this_directory / "requirements-dev.txt").exists():
    with open(this_directory / "requirements-dev.txt", 'r') as f:
        dev_requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

setup(
    name="strata-interpreter",
    version="0.1.0",
    author="Geotechnical Engineering Team",
    author_email="info@geotechnick.com",
    description="Professional geotechnical strata interpretation and design parameter assignment tool",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/geotechnick/strata-interpreter",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: Microsoft :: Windows",
    ],
    python_requires=">=3.9",
    install_requires=requirements,
    extras_require={
        "dev": dev_requirements,
        "test": [
            "pytest>=7.4.0",
            "pytest-qt>=4.2.0",
            "pytest-benchmark>=4.0.0",
            "coverage>=7.2.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "strata-interpreter=main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["resources/**/*", "*.json", "*.yaml", "*.yml"],
    },
    zip_safe=False,
)