#!/usr/bin/env bash
# Starts a throw-away backend for the end-to-end test: fresh database, Excel import, demo users.
set -euo pipefail
cd "$(dirname "$0")/../backend"
export POSTGRES_DB="${POSTGRES_DB:-ymejibu_e2e}"
export DJANGO_DEBUG=1
python3 manage.py migrate --noinput >/dev/null
python3 manage.py flush --noinput >/dev/null
python3 manage.py import_excel --report /tmp/ymejibu-e2e-report.md >/dev/null
python3 manage.py create_demo_users --password demo-2026 >/dev/null
DJANGO_SUPERUSER_PASSWORD="Goma-Ouest-2026!" python3 manage.py createsuperuser --noinput --username superadmin --email admin@example.org >/dev/null
exec python3 manage.py runserver 127.0.0.1:${E2E_BACKEND_PORT:-8001} --noreload
