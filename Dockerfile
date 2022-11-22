# syntax=docker/dockerfile:1
FROM osgeo/gdal:alpine-small-latest

RUN apk add --update --no-cache python3 && ln -sf python3 /usr/bin/python
RUN python3 -m ensurepip
RUN pip3 install --no-cache --upgrade pip setuptools

WORKDIR /cloudtile
COPY src src
COPY setup.py setup.py
COPY requirements.txt requirements.txt
COPY dev-requirements.txt dev-requirements.txt
COPY pyproject.toml pyproject.toml
RUN pip install .

CMD ["cloudtile", "cloudtile"]