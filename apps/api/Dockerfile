FROM python:3.12-slim

WORKDIR /srv
ENV PYTHONUNBUFFERED=1

COPY packages/schemas /srv/packages/schemas
COPY apps/api /srv/apps/api

RUN pip install --no-cache-dir /srv/packages/schemas "/srv/apps/api[postgres]"

EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--app-dir", "apps/api/src"]
