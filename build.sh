#!/usr/bin/env bash
# Exit on error
set -o errexit

echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "Setting up database..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput 