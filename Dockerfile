# syntax=docker/dockerfile:1
FROM osgeo/gdal:alpine-normal-latest

WORKDIR /cloudtile

RUN \
    # Installing package dependencies
    apk add --update --no-cache \
        python3 \
        git \
        make \
        bash \
        curl \
        g++ \
        sqlite-dev \
        zlib-dev \
    && ln -sf python3 /usr/bin/python \
    && python3 -m ensurepip \
    && pip3 install --no-cache --upgrade pip setuptools
# Here we install tippecanoe
RUN \
    git clone https://github.com/felt/tippecanoe.git \
    && cd tippecanoe \
    && make -j \
    && make install

COPY src src
COPY requirements.txt requirements.txt
COPY pyproject.toml pyproject.toml
RUN pip3 install .

ENTRYPOINT ["cloudtile"]