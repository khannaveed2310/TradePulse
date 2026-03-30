#!/usr/bin/env bash
set -e

echo "=== Installing Python dependencies ==="
pip install --upgrade pip
pip install -r requirements.txt

echo "=== Running migrations ==="
python manage.py migrate --no-input

echo "=== Collecting static files ==="
python manage.py collectstatic --no-input

echo "=== Build complete ==="