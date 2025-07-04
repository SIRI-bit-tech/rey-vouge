#!/usr/bin/env bash
# exit on error
set -o errexit

# Start Gunicorn
gunicorn rey_vogue.wsgi:application --bind 0.0.0.0:$PORT --workers 4 --threads 4 --timeout 120 