#!/bin/sh
# Waits for PostgreSQL, applies migrations and, on first start only, imports the Excel workbooks.
set -e
python - <<'PY'
import os, time, psycopg
for i in range(60):
    try:
        psycopg.connect(host=os.environ.get("POSTGRES_HOST", "db"), dbname=os.environ.get("POSTGRES_DB", "ymejibu"),
                        user=os.environ.get("POSTGRES_USER", "ymejibu"), password=os.environ.get("POSTGRES_PASSWORD", "ymejibu")).close()
        break
    except Exception:
        time.sleep(1)
else:
    raise SystemExit("PostgreSQL injoignable")
PY
python manage.py migrate --noinput
if [ "${IMPORT_ON_START:-1}" = "1" ]; then
  if python manage.py shell -c "from core.models import Site; import sys; sys.exit(0 if Site.objects.exists() else 1)"; then
    echo "Données déjà présentes : import Excel ignoré (lancer « python manage.py import_excel » pour le refaire)."
  else
    python manage.py import_excel
  fi
fi
if [ -n "${DEMO_PASSWORD:-}" ]; then
  python manage.py create_demo_users --password "$DEMO_PASSWORD"
fi
exec "$@"
