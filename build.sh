#!/usr/bin/env bash
set -euo pipefail

if command -v apt-get >/dev/null 2>&1; then
  apt-get update
  apt-get install -y --no-install-recommends default-libmysqlclient-dev build-essential
fi

pip install -r requirements.txt

npm install
npm run build:css

python manage.py collectstatic --noinput
