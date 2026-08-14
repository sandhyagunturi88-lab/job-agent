FROM python:3.12-slim

WORKDIR /srv
ENV PYTHONUNBUFFERED=1 PYTHONPATH=/srv/apps/worker/src

COPY packages/schemas /srv/packages/schemas
COPY apps/worker /srv/apps/worker

RUN pip install --no-cache-dir /srv/packages/schemas /srv/apps/worker

CMD ["arq", "worker.main.WorkerSettings"]
