#!/bin/sh

set -x
set -e
set -u

DOCKER_IMAGE=$1

sed "s|^\(SCENIC_LGSVL_IMAGE_DEFAULT\)=.*|\1=${DOCKER_IMAGE} \# Updated by CI|" -i ./scripts/scenic_lgsvl.sh
