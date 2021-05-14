# As of 2021-02-16, 3.6[-slim] == 3.6.13[-slim]-buster
# Use the non-slim image because it already has git pre-installed.
FROM python:3.6.13-buster AS builder

# The "git describe" done by get_version() in runner/setup.py needs .git (and the "git describe" done by get_version() in
# externals/PythonApi/setup.py needs its subdirectory .git/modules/externals/PythonApi):
ADD .git /app/.git

ADD externals /app/externals
RUN set -ex \
    && cd /app/externals/PythonApi \
    && python3 -m pip install . -r requirements.txt

ARG PYTHON_INSTALL_ENV
ADD runner /app/runner
RUN set -ex \
    && cd /app/runner \
    && eval ${PYTHON_INSTALL_ENV} python3 -m pip install .

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

ARG image_git_describe=(unknown)
ARG image_git_describe_submodules=(unknown)
ARG image_tag=(unset)
ARG image_uuidgen=(unset)

RUN set -ex \
  && echo "IMAGE_APP=scenarios/runner\n\
IMAGE_CREATED_BY=auto-jenkins\n\
IMAGE_CREATED_FROM=${image_git_describe}\n\
IMAGE_CREATED_FROM_SUBMODULES='${image_git_describe_submodules}'\n\
IMAGE_CREATED_ON=$(date --iso-8601=seconds --utc)\n\
IMAGE_TAG=${image_tag}\n\
# Increment IMAGE_INTERFACE_VERSION whenever changes to the image require that the launcher be updated.\n\
IMAGE_INTERFACE_VERSION=2\n\
IMAGE_UUID=${image_uuidgen}"\
  >> /etc/wise-image-info.source \
  && echo "Scenarios/runner wise-image-info.source:" \
  && cat /etc/wise-image-info.source
