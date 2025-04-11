#!/usr/bin/env bash
# Exit on error
set -o errexit

echo "Upgrading pip..."
pip install --upgrade pip

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Ensuring media directory exists..."
mkdir -p /opt/render/project/src/media
chmod -R 775 /opt/render/project/src/media

echo "Creating superuser if needed..."
python manage.py create_admin 