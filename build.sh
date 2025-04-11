#!/usr/bin/env bash
# Exit on error
set -o errexit

echo "Upgrading pip..."
pip install --upgrade pip

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Ensuring media directories exist..."
# Create all necessary directories with proper permissions
mkdir -p /opt/render/project/src/media
mkdir -p /opt/render/project/src/media/avatars
mkdir -p /opt/render/project/src/media/signatures
mkdir -p /opt/render/project/src/media/driver_photos
mkdir -p /opt/render/project/src/media/vehicle_photos
mkdir -p /opt/render/project/src/media/secondary_photos
mkdir -p /opt/render/project/src/media/qr_codes
chmod -R 775 /opt/render/project/src/media

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Creating superuser if needed..."
python manage.py create_admin

echo "Validating and fixing media paths..."
python manage.py fix_media_paths

echo "Build process completed successfully" 