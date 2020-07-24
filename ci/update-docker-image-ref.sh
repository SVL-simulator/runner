#!/bin/sh

set -x
set -e
set -u

SCRIPT=$1
DOCKER_IMAGE=$2

test -f "${SCRIPT}"

sed "s|^\(SCENARIO_RUNNER_IMAGE_DEFAULT\)=.*|\1=${DOCKER_IMAGE} \# Updated by CI|" -i "${SCRIPT}"
