FROM python:3.13-slim

LABEL org.opencontainers.image.title="ArenaPass Backend" \
      org.opencontainers.image.version="3.1.0" \
      org.opencontainers.image.description="Django raw-SQL API for the ArenaPass sports ticketing project"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN addgroup --system app && adduser --system --ingroup app app

COPY requirements.txt /app/requirements.txt
COPY requirements-dev.txt /app/requirements-dev.txt

RUN python -m pip install --upgrade pip \
    && python -m pip install --requirement /app/requirements-dev.txt

COPY --chown=app:app . /app
RUN chmod +x /app/manage.py /app/worker.py /app/entrypoint.sh \
    /app/run_local.sh /app/run_worker_local.sh \
    /app/scripts/configure_gmail.py \
    /app/scripts/smtp_smoke.py

USER app
EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "--config", "gunicorn.conf.py", "wsgi:application"]
