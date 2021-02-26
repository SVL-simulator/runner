# As of 2021-02-16, 3.6[-slim] == 3.6.13[-slim]-buster
# Use the non-slim image because it already has gcc, git, and libc-dev pre-installed.
FROM python:3.6.13-buster AS builder

# numpy-1.20 requires python 3.7
RUN python3 -m pip install \
    environs \
    numpy\<1.20 \
    scipy\<1.6.0 \
    pandas\<1.2.0

ADD externals /app/externals
# The "git describe" done by get_version() in externals/PythonApi/setup.py needs this directory:
ADD .git/modules/externals/PythonApi /app/.git/modules/externals/PythonApi
RUN set -ex \
    && cd /app/externals/PythonApi \
    && python3 -m pip install .

ADD runner /app/runner
# The "git describe" done by get_version() in runner/setup.py needs this directory:
ADD .git /app/.git
RUN set -ex \
    && cd /app/runner \
    && python3 -m pip install .

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
