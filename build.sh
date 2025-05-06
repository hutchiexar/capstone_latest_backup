#!/usr/bin/env bash
# Exit on error
set -o errexit

echo "Upgrading pip..."
pip install --upgrade pip

echo "Installing dependencies..."
# First try: Use requirements-fixed.txt
if [ -f requirements-fixed.txt ]; then
    echo "Using requirements-fixed.txt for dependencies..."
    pip install -r requirements-fixed.txt || {
        echo "Error installing from requirements-fixed.txt. Trying without problematic packages..."
        # Create a temporary requirements file without the problematic packages
        grep -v "pyHanko\|pyhanko-certvalidator" requirements-fixed.txt > requirements-temp.txt
        pip install -r requirements-temp.txt || {
            echo "Still having issues. Trying minimal requirements file..."
            # Try the minimal requirements file if available
            if [ -f requirements-minimal.txt ]; then
                pip install -r requirements-minimal.txt
            else
                # Last resort: install core packages directly
                echo "Using core dependencies only..."
                pip install Django==5.1.6 \
                    djangorestframework==3.15.2 \
                    dj-database-url==2.1.0 \
                    gunicorn==22.0.0 \
                    psycopg2-binary==2.9.9 \
                    whitenoise==6.7.0 \
                    python-dotenv==1.0.1
            fi
        }
        rm -f requirements-temp.txt
        echo "Will attempt to install problematic packages individually..."
        # Try to install problematic packages one by one with error suppression
        pip install pyHanko==0.17.0 || echo "Failed to install pyHanko, skipping..."
        pip install pyhanko-certvalidator==0.19.5 || echo "Failed to install pyhanko-certvalidator, skipping..."
    }
else
    echo "requirements-fixed.txt not found, attempting to use requirements.txt..."
    # Fall back to the original requirements if the fixed version isn't available
    pip install -r requirements.txt || {
        echo "Error installing from requirements.txt. Trying minimal requirements..."
        # Try the minimal requirements file if available
        if [ -f requirements-minimal.txt ]; then
            pip install -r requirements-minimal.txt
        else
            # Last resort: install core packages directly
            echo "Using core dependencies only..."
            pip install Django==5.1.6 \
                djangorestframework==3.15.2 \
                dj-database-url==2.1.0 \
                gunicorn==22.0.0 \
                psycopg2-binary==2.9.9 \
                whitenoise==6.7.0 \
                python-dotenv==1.0.1
        fi
    }
fi

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

echo "Creating log directory..."
mkdir -p /opt/render/project/src/logs
touch /opt/render/project/src/app.log
chmod 664 /opt/render/project/src/app.log

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Creating superuser if needed..."
python manage.py create_admin

echo "Setting up media and static files..."
python manage.py check --deploy

echo "Build process completed successfully" 