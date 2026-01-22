#FROM tiangolo/uvicorn-gunicorn-fastapi:python3.9-slim
FROM python:3.14-slim

RUN mkdir /data
RUN mkdir -p /app/templates

COPY requirements.txt /app/

RUN pip install --no-cache-dir -r /app/requirements.txt

COPY templates/index.html /app/templates/
COPY main.py /app/

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]
