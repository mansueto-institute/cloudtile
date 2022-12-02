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
# Here we install pmtiles
RUN curl -LO  http://github.com/protomaps/go-pmtiles/releases/download/v1.6.2/go-pmtiles_1.6.2_Linux_x86_64.tar.gz \
    && tar -xvzf go-pmtiles_1.6.2_Linux_x86_64.tar.gz

COPY src src
COPY setup.py setup.py
COPY requirements.txt requirements.txt
COPY dev-requirements.txt dev-requirements.txt
COPY pyproject.toml pyproject.toml
COPY blocks_SLE.parquet blocks_SLE.parquet
RUN pip install .

ENTRYPOINT ["cloudtile"]