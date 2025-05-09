#!/bin/bash

# Enhanced build script for Traffic Violation System
# This script handles dependency installation with robust fallback mechanisms
# and applies patches for problematic imports

set -e
echo "Starting build process..."

# Ensure Python 3.10 is being used
python --version

# Make script directory available
export PYTHONPATH=$PYTHONPATH:$(pwd)

# Create logs and media directories if they don't exist
mkdir -p logs

# Ensure render permanent media directory exists and has proper permissions
if [ "$RENDER" = "True" ]; then
    echo "Setting up Render persistent media directory..."
    
    # Ensure the base media directory exists
    mkdir -p /opt/render/project/src/media
    chmod -R 755 /opt/render/project/src/media
    
    # Create required subdirectories if they don't exist
    mkdir -p /opt/render/project/src/media/avatars
    mkdir -p /opt/render/project/src/media/qr_codes
    mkdir -p /opt/render/project/src/media/vehicle_documents
    mkdir -p /opt/render/project/src/media/violation_evidence
    mkdir -p /opt/render/project/src/media/driver_documents
    mkdir -p /opt/render/project/src/media/signatures
    
    # Create symbolic link if needed
    if [ ! -L "media" ] && [ ! -d "media" ]; then
        echo "Creating symbolic link for media directory..."
        ln -sf /opt/render/project/src/media media
    fi
else
    # For local development, create the directories locally
    echo "Setting up local media directories..."
    mkdir -p media
    mkdir -p media/avatars
    mkdir -p media/qr_codes
    mkdir -p media/vehicle_documents
    mkdir -p media/violation_evidence
    mkdir -p media/driver_documents
    mkdir -p media/signatures
    chmod -R 755 media
fi

# Ensure handler files are in the source directory
echo "Copying handler files..."
cp -f handle_*.py /opt/render/project/src/ 2>/dev/null || echo "No handler files to copy (this is normal on first build)"

# Function to check if a package is installed
check_package() {
    python -c "import $1" 2>/dev/null
    return $?
}

# Function to install a specific package
install_package() {
    echo "Installing $1..."
    pip install $1
    if [ $? -ne 0 ]; then
        echo "Failed to install $1"
        return 1
    fi
    return 0
}

# Attempt to use the fixed requirements file first
echo "Attempting to install from requirements-fixed.txt..."
if [ -f "requirements-fixed.txt" ]; then
    pip install -r requirements-fixed.txt
    if [ $? -eq 0 ]; then
        echo "Successfully installed dependencies from requirements-fixed.txt"
    else
        echo "Error installing from requirements-fixed.txt, trying fallback methods..."
        
        # Fallback 1: Try using the original requirements
        echo "Attempting to install from original requirements.txt..."
        pip install -r requirements.txt
        
        # Fallback 2: Try the minimal requirements
        if [ $? -ne 0 ] && [ -f "requirements-minimal.txt" ]; then
            echo "Attempting to install from requirements-minimal.txt..."
            pip install -r requirements-minimal.txt
        fi
        
        # Manually install critical packages
        echo "Installing critical packages individually..."
        pip install Django==4.2 django-crispy-forms crispy-bootstrap5
        pip install django-cors-headers django-phonenumber-field phonenumbers
        
        # Ensure these specific packages are at compatible versions
        echo "Setting specific versions for known problematic packages..."
        pip install pyparsing==3.0.9
        pip install reportlab==3.6.13  # downgraded to satisfy xhtml2pdf requirements
        
        # Install packages that might be missing from requirements
        echo "Installing potentially missing packages..."
        pip install idanalyzer==1.2.2 django-sslserver xlsxwriter==3.1.9
    fi
else
    echo "requirements-fixed.txt not found, falling back to original requirements.txt"
    pip install -r requirements.txt
    
    # Install specific versions of problematic packages
    pip install pyparsing==3.0.9
    pip install reportlab==3.6.13  # downgraded to satisfy xhtml2pdf requirements
    pip install idanalyzer==1.2.2 django-sslserver xlsxwriter==3.1.9
fi

# Ensure critical packages are installed
echo "Verifying critical packages..."
for package in django django_crispy_forms crispy_bootstrap5 idanalyzer django_sslserver xlsxwriter
do
    if ! check_package "$package"; then
        echo "$package not installed, attempting to install individually..."
        install_package "$package"
    fi
done

# Apply patches for problematic imports
echo "Applying patches for problematic imports..."
python direct_import_patch.py
if [ $? -ne 0 ]; then
    echo "Warning: Some patches could not be applied. Check logs for details."
fi

# Run database migrations
echo "Running database migrations..."
python manage.py makemigrations
python manage.py migrate

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --no-input

echo "Build process completed successfully!" 