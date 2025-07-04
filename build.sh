#!/usr/bin/env bash
# exit on error
set -o errexit

# Install system dependencies
apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    python3-pip \
    python3-setuptools \
    python3-wheel \
    gcc \
    libpq-dev

# Upgrade pip
python -m pip install --upgrade pip

# Install python dependencies
pip install -r requirements.txt

# Create necessary directories and files with proper permissions
mkdir -p logs
touch logs/rey_vogue.log logs/security.log logs/performance.log
chmod 666 logs/rey_vogue.log logs/security.log logs/performance.log

# Collect static files
python manage.py collectstatic --no-input

# Run migrations
python manage.py migrate

# Create superuser if not exists
python manage.py shell << END
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(email='$DJANGO_SUPERUSER_EMAIL').exists():
    User.objects.create_superuser('$DJANGO_SUPERUSER_USERNAME', '$DJANGO_SUPERUSER_EMAIL', '$DJANGO_SUPERUSER_PASSWORD')
END 