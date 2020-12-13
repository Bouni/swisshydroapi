FROM tiangolo/uvicorn-gunicorn-fastapi:python3.8

RUN mkdir /data
RUN mkdir -p /app/templates

RUN pip install --no-cache-dir jinja2

COPY templates/index.j2 /app/templates/
COPY main.py /app/

