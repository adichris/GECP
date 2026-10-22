FROM node:22-bookworm-slim AS frontend
WORKDIR /build
COPY package.json package-lock.json ./
RUN npm ci
COPY frontend ./frontend
COPY templates ./templates
COPY apps ./apps
COPY static ./static
RUN npm run build

FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN groupadd --system gecp && useradd --system --gid gecp gecp
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY --chown=gecp:gecp . .
COPY --from=frontend --chown=gecp:gecp /build/static ./static
RUN mkdir -p /app/media /app/staticfiles && chown -R gecp:gecp /app/media /app/staticfiles
USER gecp
RUN DJANGO_SETTINGS_MODULE=config.settings.base python manage.py collectstatic --noinput
EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "60", "--access-logfile", "-", "--error-logfile", "-"]
