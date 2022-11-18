#FROM tiangolo/uvicorn-gunicorn-fastapi:python3.9-slim
FROM python:3.11-slim

RUN mkdir /data
RUN mkdir -p /app/templates

RUN pip install --no-cache-dir jinja2 fastapi uvicorn gunicorn

COPY templates/index.html /app/templates/
COPY main.py /app/

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]
