#!/usr/bin/env bash
set -o errexit
pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate
python manage.py migrate --database=bot_eda
chmod +x build.sh
git update-index --chmod=+x build.sh || true