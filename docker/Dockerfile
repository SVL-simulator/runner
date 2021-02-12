# As of 2021-02-16, 3.6-slim == 3.6.13-slim-buster
FROM python:3.6.13-slim-buster AS builder

RUN set -ex \
    && apt-get update -qq \
    && DEBIAN_FRONTEND=noninteractive apt-get install --no-install-recommends -q -y \
        gcc \
        libc-dev

ADD externals /app/externals
WORKDIR /apps

# numpy-1.20 requires python 3.7

RUN python -m pip install \
    environs \
    numpy\<1.20 \
    scipy\<1.6.0 \
    pandas\<1.2.0

RUN cd /app/externals/PythonApi && python setup.py install

ADD runner /app/runner
RUN cd /app/runner && python setup.py install

FROM python:3.6.13-slim-buster

COPY --from=builder /usr/local/lib/python3.6/site-packages /usr/local/lib/python3.6/site-packages
COPY --from=builder /usr/local/bin/run* /usr/local/bin/

COPY \
    scripts/install-testcase-runtime.sh \
    scripts/scenario_runner.sh \
    /usr/share/scenarios-runner/scripts/

RUN set -ex \
    && apt-get update -qq \
    && DEBIAN_FRONTEND=noninteractive apt-get install --no-install-recommends -q -y \
        jq \
        libglib2.0-0 \
        libsm6 \
        libxrender1 \
        libxext6 \
        libgl1 \
        netcat-openbsd \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
