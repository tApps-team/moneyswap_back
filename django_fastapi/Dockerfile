FROM python:3.10
# FROM python:3.10.0-alpine

WORKDIR /app

# EXPOSE 8000

COPY requirements.txt requirements.txt

RUN pip3 install --upgrade setuptools
RUN pip3 install -r requirements.txt

COPY . .

RUN mkdir -p /app/logs && \
    touch /app/logs/gunicorn-error.log && \
    chmod -R 777 /app/logs