#!/bin/bash
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Install MySQL client (needed for MySQL database connection)
apt-get update && apt-get install -y default-libmysqlclient-dev

# Set up django project
python manage.py migrate --noinput
python manage.py collectstatic --noinput 