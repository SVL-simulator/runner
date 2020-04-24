#!/bin/bash

set -u

if [ "${#@}" == "0" ]; then
    echo $(basename $0) DOCKER_TAG [DOCKER_IMAGE_PREFIX]
    exit 1
fi

set -e
set -x
set -o pipefail

R=$(readlink -f $(dirname $0))

DOCKER_TAG=${1}
DOCKER_IMAGE_PREFIX=${2:-auto-gitlab.lgsvl.net:4567/hdrp/scenarios}

DIST_IMAGES='runner'
DIST_NAME=lgsvlsimulator-scenarios-$DOCKER_TAG
DIST_PATH=$(pwd)/dist/$DIST_NAME

PUBLIC_IMAGE=lgsvl/simulator-scenarios-runner

function save_docker_images {
    mkdir -p $DIST_PATH/docker
    ${R}/save_docker_image.sh ${DOCKER_IMAGE_PREFIX}/runner $DOCKER_TAG $PUBLIC_IMAGE $DIST_PATH/docker
}

function export_runner_script {
    cp ./scripts/scenic_lgsvl.sh $DIST_PATH/scenic_lgsvl.sh
    ${R}/update-docker-image-ref.sh $DIST_PATH/scenic_lgsvl.sh lgsvl/simulator-scenarios-runner:$DOCKER_TAG
}

function copy_scenarios {
    test -d scenarios || (echo "E: Can't find scenarios"; exit 1)
    cp -r scenarios $DIST_PATH
}

function copy_docs {
    cp -r docs $DIST_PATH
}

function show_tree() {
    TREE=$(which tree || true)

    if [ -x "${TREE}" ]; then
        ${TREE} -a $DIST_NAME | tee $DIST_NAME-content.txt
    else
        echo "W: Can't generate dist content list: tree is not installed"
    fi
}

function make_zip() {
    rm $DIST_NAME.zip || true
    zip -r $DIST_NAME.zip $DIST_NAME
}

rm -Rf $DIST_PATH || true
mkdir -p $DIST_PATH


save_docker_images
export_runner_script
copy_scenarios
copy_docs

# Some housekeeping
find $DIST_PATH -name '.git*' | xargs rm -rf

pushd $DIST_PATH/..

make_zip
show_tree

