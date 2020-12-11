FROM python:3.8-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN mkdir -p /app/templates
WORKDIR /app

COPY requirements.txt /app
RUN pip install -r requirements.txt

COPY bafu.py /app/
COPY api.py /app/

EXPOSE 8000
