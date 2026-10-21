FROM python:3.11-slim

WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend backend
COPY data data

WORKDIR /app/backend
ENV PYTHONUTF8=1
CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}
