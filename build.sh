#!/usr/bin/env bash
set -euo pipefail

pip install -r requirements.txt

npm install
npm run build:css


echo "=== DJANGO DIAGNOSTIC ==="
python --version
python manage.py version
python manage.py help | grep collectstatic || true
python manage.py shell -c "from django.conf import settings; print('SETTINGS FILE:', settings.SETTINGS_MODULE); print('STATICFILES INSTALLED:', 'django.contrib.staticfiles' in settings.INSTALLED_APPS)"
echo "=== END DIAGNOSTIC ==="

python manage.py collectstatic --no-input
