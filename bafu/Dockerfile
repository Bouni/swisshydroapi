FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN mkdir -p /app
WORKDIR /app

COPY requirements.txt /app
RUN pip install -r requirements.txt

COPY bafu.py /app/
COPY check.py /app/

HEALTHCHECK --interval=1m --timeout=5s --start-period=1m \
  CMD python /app/check.py

