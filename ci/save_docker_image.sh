#!/bin/bash

set -x
set -e
set -u

SRC_IMAGE=${1}
TAG=${2}
DST_IMAGE=${3:-${1}}
OUTPUT_FOLDER=${4:-$(pwd)/dist}

SOURCE_IMAGE=${SRC_IMAGE}:${TAG}

TARBALL_NAME=$(echo "${DST_IMAGE}:${TAG}" | tr ':/' '-')

TARBALL_PATH="${OUTPUT_FOLDER}/${TARBALL_NAME}.tar"

docker history ${SOURCE_IMAGE} > /dev/null 2>&1  || \
(
    set +x
    echo "E: Can't find source image '${SOURCE_IMAGE}'"
    echo "Pull it with 'docker pull ${SOURCE_IMAGE}'"
    echo "or build it";
    exit 1
)

if [ "${SRC_IMAGE}" != "${DST_IMAGE}" ]; then
    docker tag ${SRC_IMAGE}:${TAG} ${DST_IMAGE}:${TAG}
fi

mkdir -p ${OUTPUT_FOLDER}
docker save -o ${TARBALL_PATH} ${DST_IMAGE}:${TAG}
