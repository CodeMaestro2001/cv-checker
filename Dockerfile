FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
COPY requirements-ui.txt .
COPY requirements-ml.txt .
RUN pip install --no-cache-dir -r requirements-ui.txt

COPY app app
COPY ui ui
COPY data data
COPY models models

EXPOSE 8000 8501
