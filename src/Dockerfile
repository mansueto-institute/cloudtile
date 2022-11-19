# syntax=docker/dockerfile:1
FROM ubuntu:latest

RUN apt-get update && \
    apt-get -y install \
        python3 \
        python3-pip

# Install AWSCLI
RUN python3 -m pip install --upgrade pip && \
    pip install --upgrade awscli

CMD echo 'Hello World!'