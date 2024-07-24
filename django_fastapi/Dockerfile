# FROM python:3.10
FROM python:3.10.0-alpine

WORKDIR /app

# EXPOSE 8000

COPY requirements.txt requirements.txt

RUN python3 -m pip install --upgrade pip
RUN pip3 install --upgrade setuptools
RUN pip3 install -r requirements.txt

COPY . .