FROM python:3.11-slim

WORKDIR /app

COPY backend /app/backend
COPY frontend /app/frontend

RUN pip install --no-cache-dir -r /app/backend/requirements.txt

ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["bash", "-lc", "cd /app/backend && uvicorn app.main:app --host 0.0.0.0 --port 8000"]

