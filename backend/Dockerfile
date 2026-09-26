FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app/backend
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ /app/backend/
COPY shared/ /app/shared/
RUN DJANGO_SECRET_KEY=build DB_ENGINE=sqlite python manage.py collectstatic --noinput >/dev/null
EXPOSE 8000
ENTRYPOINT ["/app/backend/docker-entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "120"]
