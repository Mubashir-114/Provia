#!/usr/bin/env bash
set -euo pipefail

pip install -r requirements.txt

npm install
npm run build:css

python manage.py collectstatic --noinput
