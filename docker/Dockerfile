FROM python:3.6-slim as builder

RUN apt-get update && apt-get install -y \
    gcc

ADD externals /app/externals
WORKDIR /apps

RUN cd /app/externals/Scenic && python setup.py install
RUN cd /app/externals/VerifAI && python setup.py install
RUN cd /app/externals/PythonApi && python setup.py install

ADD runner /app/runner
RUN cd /app/runner && python setup.py install

FROM python:3.6-slim

COPY --from=builder /usr/local/lib/python3.6/site-packages /usr/local/lib/python3.6/site-packages
COPY --from=builder /usr/local/bin/run* /usr/local/bin/

RUN apt-get update \
    && apt-get install -y \
        libglib2.0-0 \
        libsm6 \
        libxrender1 \
        libxext6 \
        libgl1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
