#!/usr/bin/env python3
"""
Script to install necessary packages for document import functionality
"""
import os
import sys
import subprocess
import importlib.util

def check_package(package_name):
    """Check if a package is installed"""
    return importlib.util.find_spec(package_name) is not None

def install_package(package_name, version=None):
    """Install a package using pip"""
    pkg = package_name if version is None else f"{package_name}=={version}"
    print(f"Installing {pkg}...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])
        return True
    except subprocess.CalledProcessError:
        return False

def main():
    """Main function to check and install required packages"""
    print("Checking and installing required packages for document import functionality...")
    
    # Check for python-docx
    if check_package('docx'):
        print("✓ python-docx is already installed")
    else:
        if install_package('python-docx', '0.8.11'):
            print("✓ python-docx has been installed successfully")
        else:
            print("✗ Failed to install python-docx")
            print("  Please try to install it manually with:")
            print("  pip install python-docx==0.8.11")
    
    print("\nSetup complete!")
    
    if os.path.exists('venv') or os.path.exists('.venv'):
        print("\nNote: If you're using a virtual environment, make sure it's activated.")
        print("      Otherwise, the packages will be installed in the global Python environment.")

if __name__ == "__main__":
    main() 